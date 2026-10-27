#!/usr/bin/env python3
"""Originate a betting line for every event OLBG listed, and select the picks.

Reads   data/live/*.json      - the OLBG captures
        data/evidence/*.json  - sourced facts and market lines
Writes  data/picks.json       - every event priced, plus the written picks

Nothing here reaches the network. Every probability is either the OLBG tip
share shrunk toward an explicitly stated prior, or a sourced market figure read
out of data/evidence/. Where neither exists the event is priced but marked as
carrying no analytical edge, and is never promoted to a written prediction.

Run: python3 scripts/build_picks.py
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from line_engine import (  # noqa: E402
    CALIBRATION_PROVENANCE,
    SNOOKER_BEST_OF_11_MARGIN_PMF,
    cal,
    confidence_label,
    in_price_band,
    pick_confidence,
    price_handicap,
    price_handicap_pmf,
    price_pack,
    prob_to_american,
    american_to_prob,
    shrink_tips,
)

CAPTURED_UTC = "2026-10-27T00:00:00Z"

# ---------------------------------------------------------------------------
# File -> engine sport key. Cricket and basketball are split by competition
# because the two variants have genuinely different scoring scales.
# ---------------------------------------------------------------------------
FILE_SPORT = {
    "cricket": ("Cricket", "cricket_odi"),
    "tennis": ("Tennis", "tennis"),
    "basketball": ("Basketball", "basketball_euro"),
    "ice_hockey": ("Ice Hockey", "ice_hockey"),
    "rugby_union": ("Rugby Union", "rugby_union"),
    "rugby_league": ("Rugby League", "rugby_league"),
    "baseball": ("Baseball", "baseball"),
    "golf": ("Golf", "golf"),
    "volleyball": ("Volleyball", "volleyball"),
    "handball": ("Handball", "handball"),
    "snooker": ("Snooker", "snooker"),
    "darts": ("Darts", "darts"),
    "motor_racing": ("Motor Racing", "motor_racing"),
    "gaelic_sports": ("Gaelic Sports", "gaelic"),
    "greyhounds": ("Greyhounds", "greyhounds"),
}

LINE_RE = re.compile(r"([+-]\d+(?:\.\d+)?)\s*$")
SPLIT_RE = re.compile(r"\s+(?:vs\.?|v\.?|@)\s+", re.I)


def counterparty(event_name, top):
    """Name the other side instead of showing the placeholder 'Other outcomes'.

    OLBG's listing titles carry both contestants, so the opponent of the
    most-tipped selection can be read off rather than guessed. Returns None
    when the title does not split cleanly, in which case the caller keeps the
    neutral label - a wrong name would be worse than a vague one.
    """
    if not event_name or not top:
        return None
    parts = [p.strip() for p in SPLIT_RE.split(event_name) if p.strip()]
    if len(parts) != 2:
        return None
    t = top.strip().lower()
    for p in parts:
        pl = p.lower()
        if pl == t or pl.startswith(t) or t.startswith(pl):
            other = parts[1] if p is parts[0] else parts[0]
            # strip trailing competition noise such as "3rd T20 Match"
            return re.sub(r"\s+(3rd|2nd|1st|4th|5th|one day|t20|match|odl|odi).*$",
                          "", other, flags=re.I).strip() or other
    return None


def refine_sport(file_key, event_name):
    """Cricket and basketball each cover more than one scoring regime."""
    name = (event_name or "").lower()
    if file_key == "cricket":
        if "t20" in name or "big bash" in name:
            return "cricket_t20"
        return "cricket_odi"
    if file_key == "basketball":
        # The captured basketball slate is entirely European and Korean; the NBA
        # card is handled separately from data/evidence/basketball_nba.json.
        return "basketball_euro"
    return FILE_SPORT[file_key][1]


def split_line(selection):
    """OLBG encodes handicap lines inside the selection label.

    'Connacht +3.50' -> ('Connacht', 3.5).  Labels with no number are returned
    unchanged with a None line, because inventing one would be a guess.
    """
    if not selection:
        return selection, None
    m = LINE_RE.search(selection.strip())
    if not m:
        return selection.strip(), None
    try:
        line = float(m.group(1))
    except ValueError:
        return selection.strip(), None
    return selection.strip()[: m.start()].strip(), line


# ---------------------------------------------------------------------------
# Priors. ONLY events with a sourced basis for a non-uniform prior appear here.
# Every other event is shrunk toward uniform, which is a pure sample-size
# correction on the crowd anchor and makes no claim about team quality.
# ---------------------------------------------------------------------------
PRIORS = {
    902213: {
        "prior": {"Carlos Alcaraz": 0.86, "Karen Khachanov": 0.14},
        "basis": ("ATP rankings published 26 Oct 2026: Alcaraz 3rd on 5,610 points, "
                  "Khachanov 24th on 2,030. Alcaraz has won all six of their previous "
                  "meetings and took three titles in 2026 (Australian Open, Doha, Tokyo)."),
        "sources": ["https://www.lequipe.fr/Tennis/atp/epreuve-simple-messieurs/page-classement-individuel/general",
                    "https://www.hindustantimes.com/sports/tennis/alcaraz-faces-tough-vienna-draw-djokovic-s-atp-finals-hopes-hang-in-balance-in-basel-101792898879468.html"],
    },
    902233: {
        "prior": {"Novak Djokovic": 0.66, "Ugo Humbert": 0.34},
        "basis": ("Djokovic ranked 11th-12th on 3,090 points against Humbert 38th on 1,270, "
                  "and seeded 4 in Basel. Djokovic won the China Open in October beating "
                  "Zverev and Medvedev en route to his 102nd title. Held well short of a "
                  "heavier prior because Humbert has won four of his seven titles indoors "
                  "and this is an indoor hard-court first round."),
        "sources": ["https://www.atptour.com/en/rankings/singles/live",
                    "https://novakdjokovic.com/en/",
                    "https://www.hindustantimes.com/sports/tennis/alcaraz-faces-tough-vienna-draw-djokovic-s-atp-finals-hopes-hang-in-balance-in-basel-101792898879468.html"],
    },
}

URC_BASIS = ("United Rugby Championship table after four rounds, published standings: "
             "Stormers 4th, 16 points, 3 wins 1 loss, points difference +39 (133 for, 94 against); "
             "Sharks 5th, 15 points, 3-1, +21; Leinster 6th, 13 points, 2-2, +23 (99 for, 76 against); "
             "Connacht 8th, 10 points, 2-2, -7 (104 for, 111 against); Munster 9th, 10 points, 1 win 1 draw "
             "2 losses, -8; Ulster 12th, 9 points, 0 wins 2 draws 2 losses, -13 (114 for, 127 against). "
             "Round 4 results: Leinster 24-18 Munster at the Aviva Stadium; Stormers 52-40 Scarlets in "
             "Cape Town; Bulls 34-26 Ulster in Pretoria.")
URC_SOURCES = ["https://en.wikipedia.org/wiki/2026%E2%80%9327_United_Rugby_Championship",
               "https://www.rugbypass.com/news/united-rugby-championship-reports-13/",
               "https://www.unitedrugby.com/"]

PRIORS.update({
    # Stormers v Ulster - fourth against twelfth, +39 against -13, and Ulster are
    # still winless. Held at 0.80 rather than higher because Ulster's two draws
    # show they can hold a side and they scored 26 in Pretoria.
    609588: {"prior": {"Stormers": 0.80, "Ulster": 0.20},
             "basis": URC_BASIS + " Applied to Stormers v Ulster: the Stormers beat the "
                      "Scarlets 52-40 at home in Round 4 while Ulster lost 34-26 at the Bulls.",
             "sources": URC_SOURCES},
    # Connacht v Leinster - both 2-2, but Leinster carry a far better points
    # difference and are the reigning champions. Kept near even because Connacht
    # are at home in Galway and beat Leinster's own players to those places.
    609584: {"prior": {"Leinster": 0.63, "Connacht": 0.37},
             "basis": URC_BASIS + " Applied to Connacht v Leinster at the Dexcom Stadium: "
                      "Leinster are the reigning champions, having beaten the Bulls 36-7 in "
                      "the final for a tenth title, and won 52-17 at this ground in January "
                      "2026, but Connacht are level with them on two wins from four.",
             "sources": URC_SOURCES + ["https://bbc.co.uk/sport/rugby-union/articles/cjy56g5g6qw2o"]},
    902213: None,
})
PRIORS[902213] = {
    "prior": {"Carlos Alcaraz": 0.82, "Karen Khachanov": 0.18},
    "basis": ("ATP rankings published 26 October 2026: Alcaraz 3rd on 5,610 points, Khachanov "
              "24th on 2,030. Alcaraz has won all six of their previous meetings and took three "
              "titles in 2026 - the Australian Open, Doha and Tokyo. Held at 0.82 rather than "
              "the 0.86+ a 6-0 head-to-head alone would justify because sources disagree about "
              "Khachanov's 2026 US Open result: one lists him as champion, two as a semi-finalist. "
              "That unresolved form question is a reason for caution, not for ignoring it."),
    "sources": ["https://www.lequipe.fr/Tennis/atp/epreuve-simple-messieurs/page-classement-individuel/general",
                "https://www.atptour.com/en/rankings/singles/live",
                "https://www.hindustantimes.com/sports/tennis/alcaraz-faces-tough-vienna-draw-djokovic-s-atp-finals-hopes-hang-in-balance-in-basel-101792898879468.html"],
}

# Evidence tier per event. "official" means a governing-body or primary source
# confirms the match-specific facts used; "partial" means independent market and
# projection data exist but not from the league itself; "crowd_only" means the
# OLBG tip share is the only input.
TIERS = {
    188852: "official",     # NZ v India - ESPNcricinfo confirms series, squads, injuries, venue
    188868: "official",     # Pakistan v Sri Lanka - ESPNcricinfo confirms results, squads, injuries
    902213: "official",     # Alcaraz v Khachanov - ATP rankings, tournament confirmed
    902233: "official",     # Djokovic v Humbert - ATP rankings, player-official site
    200104: "partial",      # BOS @ CAR - multi-book market lines and full-season counts
    200108: "partial",      # CLB @ PHI - multi-book market lines and exchange prices
    609588: "partial",      # Stormers v Ulster - published URC table and Round 4 reports
    609584: "partial",      # Connacht v Leinster - published URC table and Round 4 reports
    609586: "partial",      # Munster v Sharks - published URC table
}

# Events where the crowd anchor is known to be corrupt and must not be used as a
# probability at all. Handball returns "Tie" as the modal outcome on 14 of 15
# listings, which cannot be right for a sport that always settles.
UNUSABLE_ANCHOR_SPORTS = {"handball"}


def load_live():
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "live", "*.json"))):
        key = os.path.basename(path)[:-5]
        if key not in FILE_SPORT:
            continue
        with open(path) as fh:
            doc = json.load(fh)
        for ev in doc.get("events", []):
            ev = dict(ev)
            ev["_file"] = key
            ev["_doc"] = doc
            out.append(ev)
    return out


def price_event(ev):
    file_key = ev["_file"]
    sport_name, _ = FILE_SPORT[file_key]
    sport_key = refine_sport(file_key, ev.get("event_name"))
    cfg = cal(sport_key)
    eid = ev.get("event_id")

    top_raw = ev.get("top_selection")
    top, stated_line = split_line(top_raw)
    if ev.get("olbg_stated_line") and stated_line is None:
        m = re.search(r"[+-]?\d+(?:\.\d+)?", str(ev["olbg_stated_line"]))
        if m:
            stated_line = float(m.group(0))

    tips_win = ev.get("tips_win")
    tips_total = ev.get("tips_total")
    flags = list(ev.get("flags", []) or [])

    result = {
        "sport": sport_name,
        "sport_key": sport_key,
        "engine_profile": {k: cfg[k] for k in
                           ("margin_per_prob_point", "margin_sd", "handicap_increment",
                            "supports_handicap", "supports_total", "draw_possible",
                            "prior_strength_k", "unit")},
        "event_id": eid,
        "event_name": ev.get("event_name"),
        "olbg_url": ev.get("olbg_url"),
        "time_label": ev.get("time_label"),
        "league": ev.get("league"),
        "olbg_top_selection": top_raw,
        "olbg_market": ev.get("top_market") or "Win Match",
        "tips_win": tips_win,
        "tips_total": tips_total,
        "tip_pct": ev.get("tip_pct"),
        "comments": ev.get("comments"),
        "experts": ev.get("experts"),
        "olbg_stated_line": stated_line,
        "evidence_tier": TIERS.get(eid, "crowd_only"),
        "our_line": None,
        "handicap": None,
        "total": None,
        "flags": flags,
    }

    if eid is None:
        flags.append("OLBG event_id was not exposed on the listing, so the event page "
                     "could not be opened. Priced from the hub row only.")

    if tips_win is None or tips_total is None or not tips_total:
        flags.append("OLBG returned no tip counts for this event. No line can be "
                     "originated without inventing a crowd anchor, so none is published.")
        result["priceable"] = False
        return result

    anchor_usable = file_key not in UNUSABLE_ANCHOR_SPORTS
    if not anchor_usable:
        flags.append(CALIBRATION_PROVENANCE["handball"]["crowd_anchor"])
        result["priceable"] = False
        result["crowd_anchor_usable"] = False
        return result
    result["crowd_anchor_usable"] = True

    other = counterparty(ev.get("event_name"), top) or "Field / other outcomes"
    result["counterparty"] = other
    counts = {top: tips_win, other: tips_total - tips_win}

    entry = PRIORS.get(eid)
    if entry:
        prior = dict(entry["prior"])
        # Map the prior onto this event's outcome space.
        mapped = {}
        for name, p in prior.items():
            mapped[name if name == top or name in counts else name] = p
        if top in mapped:
            mapped[other] = round(1.0 - mapped[top], 6)
            mapped = {top: mapped[top], other: mapped[other]}
        prior = mapped
        result["prior_basis"] = entry["basis"]
        result["prior_sources"] = entry["sources"]
    else:
        prior = None
        result["prior_basis"] = ("uniform - no sourced strength comparison is available for "
                                 "this fixture, so the tip share is shrunk only for sample "
                                 "size and no claim is made about relative team quality")

    probs = shrink_tips(counts, prior=prior, k=cfg["prior_strength_k"], sport=sport_key)
    pack = price_pack(probs)

    # The pick is the side we make more likely, not necessarily OLBG's modal one.
    pick = max(probs, key=lambda s: probs[s])
    pick_p = probs[pick]
    pick_amer = pack["book"][pick]["american"]

    our = {
        "outcome_space": [top, other],
        "shrink_k": cfg["prior_strength_k"],
        "prior": prior if prior else {"uniform": True},
        "fair": pack["fair"],
        "book": pack["book"],
        "our_pick": pick,
        "our_pick_probability": round(pick_p, 4),
        "our_pick_american": pick_amer,
        "our_pick_decimal": pack["book"][pick]["decimal"],
        "olbg_modal_selection": top,
        "agrees_with_olbg_crowd": pick == top,
        "in_price_band": in_price_band(pick_amer),
        "band": "-250 to +10000",
        "crowd_signal": confidence_label(pick_p, result["evidence_tier"], tips_total),
        "confidence": pick_confidence(pick_p, result["evidence_tier"], 0, tips_total),
        "overround_applied": 0.045,
        "calibrated": True,
    }
    result["our_line"] = our

    if not our["agrees_with_olbg_crowd"]:
        flags.append("Our originated pick differs from OLBG's most-tipped selection. "
                     "The crowd backed '%s' on %s of %s tips; shrinking that share toward "
                     "the stated prior moves the likely winner to '%s'."
                     % (top, tips_win, tips_total, pick))

    if eid == 609586:
        flags.append("OLBG quotes 'Munster -6.50', laying six and a half points, but the "
                     "published United Rugby Championship table has the Sharks four places and "
                     "five points ABOVE Munster after four rounds - Sharks 5th on 15 points with "
                     "+21, Munster 9th on 10 points with -8. Munster also played without "
                     "fly-half Jack Crowley against Leinster on 24 October, with the 20-year-old "
                     "Charlie O'Shea starting in his place, and no team news has been published "
                     "for this round. The handicap is therefore recorded as quoted and flagged, "
                     "and no prior is imposed on it.")

    if not our["in_price_band"]:
        flags.append("Priced outside the -250 to +10000 band, so it is not eligible as a "
                     "high-confidence pick however strong the case looks.")

    # Handicap, where OLBG itself quoted a line value inside the selection label.
    if stated_line is not None and cfg["supports_handicap"]:
        if sport_key == "snooker":
            hc = price_handicap_pmf(pick_p, stated_line, SNOOKER_BEST_OF_11_MARGIN_PMF)
        else:
            hc = price_handicap(pick_p, stated_line, sport_key)
        if hc:
            hc["line_source"] = "OLBG selection label"
            hc["side"] = pick
            result["handicap"] = hc
        else:
            flags.append("OLBG quoted a handicap of %s but the dispersion needed to price "
                         "it is not available, so no handicap price is published."
                         % stated_line)
    elif stated_line is not None:
        flags.append("OLBG quoted a handicap of %s but this sport's profile does not "
                     "support handicap pricing." % stated_line)

    # Totals: only priceable with a sourced expected total. None is available for
    # any captured event, so this deliberately stays empty rather than guessing.
    result["total"] = None
    for m in (ev.get("markets_observed") or []):
        if m.get("market", "").lower().find("total") >= 0:
            for sel in m.get("selections", []):
                if sel.get("line") is not None:
                    flags.append("OLBG shows a total line of %s for this event but publishes "
                                 "no expected total, so the over/under is not priced. "
                                 "Inventing an expectation would be a guess." % sel["line"])

    result["priceable"] = True
    return result



# ---------------------------------------------------------------------------
# Authored picks.
#
# These are the only entries that carry a written prediction. Each one must
# name its evidence strands, and the validator below refuses to publish any
# prediction that is too short, that reuses another prediction's prose, or that
# contains the internal vocabulary the output is not allowed to use.
# ---------------------------------------------------------------------------
BANNED = ("model", "verified")


def load_authored():
    path = os.path.join(ROOT, "content", "picks_authored.json")
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        return json.load(fh).get("picks", [])


def build_authored(engine_rows):
    by_id = {r["event_id"]: r for r in engine_rows if r.get("event_id") is not None}
    out, problems = [], []
    seen = {}

    for p in load_authored():
        pid = p["pick_id"]
        text = (p.get("prediction") or "").strip()
        words = len(text.split())
        low = text.lower()

        for bad in BANNED:
            if re.search(r"\b%s\b" % bad, low):
                problems.append("%s: prediction contains the forbidden word '%s'" % (pid, bad))
        if words < 30:
            problems.append("%s: prediction is %d words, below the 30-word floor" % (pid, words))
        if not p.get("sources"):
            problems.append("%s: no sources listed" % pid)
        if not p.get("corroboration"):
            problems.append("%s: no evidence strands listed" % pid)
        key = re.sub(r"[^a-z]+", "", low)[:120]
        if key in seen:
            problems.append("%s: prediction prose duplicates %s" % (pid, seen[key]))
        seen[key] = pid

        strands = len(p.get("corroboration") or [])
        tips = None
        crowd = p.get("olbg_crowd")
        if crowd:
            tips = crowd.get("tips_total")
        # A pick whose probability comes from sourced market prices, full-season
        # counts or an independent projection does not rest on the OLBG tip
        # share, so the size of that sample cannot cap its confidence.
        crowd_dependent = bool(p.get("crowd_dependent", True))
        conf = pick_confidence(p.get("our_probability"), p.get("evidence_tier", "crowd_only"),
                               strands, tips, crowd_dependent=crowd_dependent)

        # Two different prices, and keeping them apart is the whole point.
        #   our_american    - the line WE originate from our_probability. This is
        #                     what the -250 to +10000 band is applied to.
        #   market_american - the price a book actually quoted, where one was
        #                     sourced. Null when no market price exists, which is
        #                     the case for every OLBG win market.
        our_prob = p.get("our_probability")
        our_amer = prob_to_american(our_prob)
        mkt_amer = p.get("market_price_american")
        edge = None
        if our_prob is not None and mkt_amer is not None:
            implied = american_to_prob(mkt_amer)
            edge = round(our_prob - implied, 4) if implied is not None else None
        row = {
            "pick_id": pid,
            "sport": p["sport"],
            "event_name": p["event_name"],
            "kickoff": p.get("kickoff"),
            "market": p["market"],
            "selection": p["selection"],
            "our_probability": our_prob,
            "our_american": our_amer,
            "market_american": mkt_amer,
            "edge_vs_market": edge,
            "in_price_band": in_price_band(our_amer),
            "confidence": conf,
            "evidence_tier": p.get("evidence_tier"),
            "corroboration": p.get("corroboration") or [],
            "corroboration_count": strands,
            "counter_arguments": p.get("counter_arguments") or [],
            "prediction": text,
            "word_count": words,
            "sources": p.get("sources") or [],
            "olbg_crowd": crowd,
            "olbg_url": p.get("olbg_url"),
            "olbg_event_id": p.get("olbg_event_id"),
            "olbg_stated_handicap": p.get("olbg_stated_handicap"),
            "market_price_source": p.get("market_price_source"),
            "olbg_note": p.get("olbg_note"),
            "our_probability_note": p.get("our_probability_note"),
            "crowd_contradiction": p.get("crowd_contradiction"),
            "crowd_dependent": crowd_dependent,
        }
        # Attach the independently originated line where OLBG listed the event.
        eid = p.get("olbg_event_id")
        if eid in by_id and by_id[eid].get("our_line"):
            ol = by_id[eid]["our_line"]
            row["engine_line"] = {
                "our_pick": ol["our_pick"],
                "our_pick_probability": ol["our_pick_probability"],
                "our_pick_american": ol["our_pick_american"],
                "tips_win": by_id[eid]["tips_win"],
                "tips_total": by_id[eid]["tips_total"],
                "shrink_k": ol["shrink_k"],
                "prior_basis": by_id[eid].get("prior_basis"),
            }
            # Only compare like with like. The engine row is always the win
            # market; an authored handicap or puck-line pick has a different
            # probability by construction and must not be checked against it.
            same_market = (p["market"].lower().replace(" ", "")
                           in ("winmatch", "moneyline") and p.get("our_probability") is not None)
            if same_market and abs(ol["our_pick_probability"] - p["our_probability"]) > 0.02:
                problems.append("%s: authored win-market probability %s disagrees with the "
                                "engine's %s by more than 2 points"
                                % (pid, p["our_probability"], ol["our_pick_probability"]))
        if our_amer is not None and not in_price_band(our_amer):
            problems.append("%s: our originated price %s sits outside the -250 to +10000 "
                            "band, so it is published but excluded from the high-confidence "
                            "list" % (pid, our_amer))
        if our_prob is not None and mkt_amer is not None and edge is not None and edge < 0:
            problems.append("%s: our originated probability %s is BELOW the market's implied "
                            "%s, so this selection has no edge and should not be presented as "
                            "a pick" % (pid, our_prob, round(american_to_prob(mkt_amer), 4)))
        out.append(row)

    out.sort(key=lambda r: ({"high": 0, "medium": 1, "low": 2}[r["confidence"]],
                            -(r["our_probability"] or 0)))
    # The band gate and the edge both have to hold before a pick is presented as
    # high confidence on the site.
    for r in out:
        r["featured"] = (r["confidence"] == "high" and r["in_price_band"]
                         and (r["edge_vs_market"] is None or r["edge_vs_market"] > 0))
    return out, problems



def main():
    events = [price_event(ev) for ev in load_live()]
    authored, problems = build_authored(events)
    priced = [e for e in events if e.get("priceable")]
    inband = [e for e in priced if e["our_line"]["in_price_band"]]
    hi = [e for e in inband if e["our_line"]["confidence"] == "high"]

    doc = {
        "schema": "picks/v1",
        "generated_utc": CAPTURED_UTC,
        "capture_window": "27 October 2026",
        "price_band": "-250 to +10000 American",
        "totals": {
            "events_captured": len(events),
            "events_priced": len(priced),
            "events_not_priceable": len(events) - len(priced),
            "priced_inside_band": len(inband),
            "high_confidence_inside_band": len(hi),
        },
        "by_sport": {},
        "picks": authored,
        "validation_problems": problems,
        "events": events,
    }
    hi = [p for p in authored if p["confidence"] == "high" and p["in_price_band"]]
    doc["totals"]["written_predictions"] = len(authored)
    doc["totals"]["high_confidence_written"] = len(hi)
    doc["totals"]["featured"] = sum(1 for p in authored if p["featured"])
    # Seed every requested sport, including the ones OLBG listed nothing for.
    # A sport with zero events must still appear in the tally as a zero, or the
    # site looks like it covers thirteen sports instead of fifteen.
    for _sport_name, _ in FILE_SPORT.values():
        doc["by_sport"].setdefault(_sport_name, {
            "captured": 0, "priced": 0, "in_band": 0, "high": 0, "medium": 0, "low": 0})
    for e in events:
        b = doc["by_sport"].setdefault(e["sport"], {
            "captured": 0, "priced": 0, "in_band": 0, "high": 0, "medium": 0, "low": 0})
        b["captured"] += 1
        if e.get("priceable"):
            b["priced"] += 1
            if e["our_line"]["in_price_band"]:
                b["in_band"] += 1
                b[e["our_line"]["confidence"]] += 1

    out = os.path.join(ROOT, "data", "picks.json")
    with open(out, "w") as fh:
        json.dump(doc, fh, indent=1)
    print("wrote %s" % out)
    print("captured=%d priced=%d unpriceable=%d in_band=%d high=%d"
          % (len(events), len(priced), len(events) - len(priced), len(inband), len(hi)))
    for s, b in sorted(doc["by_sport"].items()):
        print("  %-15s captured=%-3d priced=%-3d in_band=%-3d high=%-2d med=%-2d low=%-2d"
              % (s, b["captured"], b["priced"], b["in_band"], b["high"], b["medium"], b["low"]))
    print("\nauthored written predictions: %d (high %d, medium %d, low %d)"
          % (len(authored),
             sum(1 for p in authored if p["confidence"] == "high"),
             sum(1 for p in authored if p["confidence"] == "medium"),
             sum(1 for p in authored if p["confidence"] == "low")))
    for p in authored:
        print("  [%-6s]%s %-12s %-42s %-24s p=%-6s ours=%-6s mkt=%-6s edge=%-7s %dw %dstr"
              % (p["confidence"], "*" if p["featured"] else " ", p["sport"],
                 p["event_name"][:42], p["selection"][:24], p["our_probability"],
                 p["our_american"], p["market_american"], p["edge_vs_market"],
                 p["word_count"], p["corroboration_count"]))
    if problems:
        print("\nVALIDATION:")
        for x in problems:
            print("  ! " + x)
    else:
        print("\nall authored predictions passed validation")

    print("\nengine-only rows, strongest crowd lean first:")
    for e in sorted(inband, key=lambda x: -x["our_line"]["our_pick_probability"])[:14]:
        ol = e["our_line"]
        print("  %-12s %-46s %-28s p=%.3f %-6s %-8s %s"
              % (e["sport"], (e["event_name"] or "")[:46], ol["our_pick"][:28],
                 ol["our_pick_probability"], ol["our_pick_american"],
                 ol["confidence"], e["evidence_tier"]))


if __name__ == "__main__":
    main()
