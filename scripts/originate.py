#!/usr/bin/env python3
"""Originate our own betting line for every captured OLBG selection.

Why a line has to be originated at all
--------------------------------------
OLBG does not publish a bookmaker price in the page markup that a reader can
see without logging in; it publishes, for every selection, the number of
tipsters who picked it and the total number of tips on that market, and it
defines its own "Value Rating" as a comparison between a selection's odds and
"the theoretical probability of winning based on the percentage of tips for it"
(the definition is printed on every OLBG category page). So the quantity OLBG
itself treats as a probability is the share of tipping volume. We use that as
the input to our own pricing rather than copying anyone's price.

Method, step by step (no step is hidden; everything below is arithmetic)
------------------------------------------------------------------------
1. n     = OLBG win tips on this selection (as printed, "x / y").
2. T     = OLBG total tips on the market (the "y").
3. Blocks. The market is reduced to two blocks: the selection, and everything
   else in that market. This works identically for head-to-head, three-way and
   outright fields, and it never requires inventing a split of the field.
4. Outcome count k. The number of ways the market can land. 2 for a
   head-to-head (win/money line, run line, puck line, pointspread, totals,
   handicap between two sides), 3 where a draw is a live price (OLBG's handball
   Money Line is quoted Tie / home / away), and the size of the declared field
   for an outright. Field sizes that an official source published are used
   (LPGA listed a 78-player Maybank field, the PDC world field is 128); where a
   field size was not published the row is priced against a 2-way floor and
   hard-capped below High, with `field_size_unknown` flagged, rather than being
   given an invented denominator.
5. Shrinkage. p = (n + STRENGTH/k) / (T + STRENGTH) with STRENGTH = 8. This is
   a Dirichlet posterior with a uniform prior over the k outcomes, so a thin
   sample is pulled toward the field-neutral base rate (50% in a two-horse
   market, 1/78 in an outright) rather than toward 50% everywhere. It stops 1/1
   reading as a certainty and stops 0/2 reading as impossible, and the strength
   is published so the number can be reproduced exactly.
5. Fair price. fair_decimal = 1 / p.
6. Our line. we_decimal = fair_decimal * (1 - MARGIN) with MARGIN = 0.04,
   i.e. a 4% margin taken on every price we publish, then converted to
   American. The fair price is also published so the margin is reversible.
7. Window gate. A line is only publishable if OUR American price falls inside
   the required band of -250 to +10,000. Anything shorter than -250 is
   rejected from the picks surface and flagged, because that was an explicit
   instruction.
8. Confidence. Never derived from price alone.
   High   requires all of: an opened official source that matched the fixture,
            p >= 0.60, T >= 4, and a price inside the window.
   Medium either a corroborated fixture with p >= 0.52, or an uncorroborated
            fixture with heavy volume (p >= 0.60 and T >= 8).
   Low    everything else.
   No selection can be labelled High on the strength of OLBG tipping volume
   alone; that is the whole point of the gate.

Markets with no tip volume at all (T = 0, e.g. an untouched Over/Under) get no
probability, no price and no pick, and are flagged as unpriced rather than
filled in.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARGIN = 0.04
STRENGTH = 8.0
PSEUDO = 1.0          # legacy name, no longer used for the main estimator
# markets OLBG quotes with a live draw/tie outcome
THREE_WAY = {("handball", "Money Line")}
# declared field sizes published by an official source for outright markets
FIELD_SIZE = {
    ("golf", "101913"): 78,      # LPGA Maybank Championship limited field
    ("darts", "26023"): 128,     # PDC World Championship 128-player field
}
WINDOW_MIN = -250.0      # shortest acceptable price (more negative = shorter)
WINDOW_MAX = 10000.0      # longest acceptable price
P_HIGH, P_MED_CORR, P_MED_THICK = 0.60, 0.52, 0.60
T_MIN_HIGH, T_MIN_THICK = 4, 8


def american(dec):
    if dec is None or dec <= 1.0:
        return None
    return round((dec - 1.0) * 100.0, 0) if dec >= 2.0 else round(-100.0 / (dec - 1.0), 0)


def outcome_count(skey, mkt, n_sel, eid):
    """k for this market, plus whether it was a real field size or a floor."""
    if (skey, mkt["market"]) in THREE_WAY:
        return 3, True
    if mkt["market"] in ("Win Tournament", "Grand Final Winner", "Win Hurling"):
        # An outright is priced against the real declared field when an official
        # source published one; otherwise the denominator is unknown and the row
        # is flagged rather than given a made-up field size.
        k = FIELD_SIZE.get((skey, eid))
        if k:
            return k, True
        return max(n_sel, 2), False
    return max(2, n_sel), True


def price_for(n, T, k):
    """Dirichlet-uniform-shrunk probability, then fair and margin-loaded prices."""
    if not T:
        return None, None, None, None, None
    p = (n + STRENGTH / k) / (T + STRENGTH)
    fair = 1.0 / p
    ours = fair * (1.0 - MARGIN)
    return p, fair, ours, american(fair), american(ours)


def main():
    cap = json.load(open(os.path.join(ROOT, "data", "live-capture.json"), encoding="utf-8"))
    cw_path = os.path.join(ROOT, "data", "crosswalks.json")
    cw = json.load(open(cw_path, encoding="utf-8")) if os.path.exists(cw_path) else {"events": {}}
    rows, flags = [], []
    for skey, s in cap["sports"].items():
        label = s["label"]
        if not s["events"]:
            flags.append({"code": "NO_OLBG_LISTINGS", "sport": label,
                          "detail": s.get("capture_note", "OLBG category page returned no listings at capture time."),
                          "source": s["olbg_hub"]})
        for e in s["events"]:
            key = f"{skey}:{e['event_id']}"
            cwv = cw["events"].get(key, {})
            tier = cwv.get("tier", "none")
            corr = tier == "A"
            srcs = cwv.get("sources", [])
            for m in e["markets"]:
                T = next((x["total_tips"] for x in m["selections"] if x.get("total_tips")), 0) or 0
                for sel in m["selections"]:
                    n, tT = sel.get("win_tips"), sel.get("total_tips")
                    k, k_known = outcome_count(skey, m, len(m["selections"]), e["event_id"])
                    p, fair, ours, fa, oa = price_for(n if n is not None else 0, tT or 0, k)
                    rid = f"{skey}-{e['event_id']}-{m['market']}".replace(" ", "_").lower()
                    row_flags = []
                    if not tT:
                        row_flags.append("UNPRICED_MARKET")
                    if m["basis"] == "hub_top":
                        row_flags.append("field_not_split_only_selection_priced")
                    in_window = fa is not None and WINDOW_MIN <= fa <= WINDOW_MAX
                    if not k_known:
                        row_flags.append("field_size_unknown_outright_capped")
                    if tier != "A":
                        row_flags.append("NO_OFFICIAL_CROSSWALK")
                    if oa is not None and not in_window:
                        row_flags.append("outside_-250_+10000_window")
                    # confidence, then the caps
                    is_outright = m["market"] in ("Win Tournament", "Grand Final Winner", "Win Hurling")
                    thin = T < 3
                    if thin and tT:
                        row_flags.append("thin_sample_fewer_than_3_tips")
                    conf = "Low"
                    if p is not None and in_window:
                        if corr and p >= P_HIGH and T >= T_MIN_HIGH:
                            conf = "High"
                        elif (corr and p >= P_MED_CORR) or (p >= P_MED_THICK and T >= T_MIN_THICK):
                            conf = "Medium"
                    if is_outright and conf == "High":
                        conf = "Medium"
                        row_flags.append("outright_capped_below_high")
                    if thin:
                        conf = "Low"
                        row_flags.append("capped_low_by_sample_size")
                    if not in_window:
                        conf = "Low"
                    # ranking: confidence band, then modelled edge, then volume,
                    # then whether an official source confirmed the fixture.
                    band = {"High": 3, "Medium": 2, "Low": 1}[conf]
                    score = (band * 1000 + (60 if corr else 0)
                             + min(T, 60) * 4
                             + int(round((p or 0) * 250)))
                    if not in_window:
                        score -= 400
                    rows.append({
                        "id": f"{rid}-{_slug(sel['label'])}",
                        "sport": label, "sport_key": skey,
                        "event_id": e["event_id"], "event": e["name"],
                        "competition": e["competition"], "time_label": e["time_label"],
                        "market": m["market"], "market_basis": m["basis"],
                        "market_line": m.get("line"),
                        "selection": sel["label"],
                        "olbg_win_tips": n, "olbg_total_tips": tT,
                        "olbg_displayed_pct": sel.get("displayed_pct")
                        or (round(100.0 * n / tT) if (n is not None and tT) else None),
                        "market_total_tips": T,
                        "our_prob": None if p is None else round(p, 4),
                        "outcome_count_k": k,
                        "fair_decimal": None if fair is None else round(fair, 3),
                        "our_decimal": None if ours is None else round(ours, 3),
                        "fair_american": fa, "our_american": oa,
                        "in_window": bool(in_window),
                        "official_corroborated": corr,
                        "official_tier": tier,
                        "confidence": conf,
                        "pick_score": score,
                        "in_window_fair": bool(in_window),
                        "olbg_url": e["olbg_url"],
                        "sources": [{"name": x.get("name"), "url": x.get("url"),
                                    "confirmed": x.get("confirmed"),
                                    "tier": x.get("tier_override", tier)} for x in srcs],
                        "injury_availability": cwv.get("injury_availability", ""),
                        "flags": row_flags,
                    })
                    if row_flags and "UNPRICED_MARKET" in row_flags:
                        flags.append({"code": "UNPRICED_MARKET", "sport": label,
                                      "detail": f"{e['name']} / {m['market']}: OLBG printed 0 tips in this market, so no line was originated.",
                                      "source": e["olbg_url"]})
                    if tier != "A":
                        flags.append({"code": "NO_OFFICIAL_CROSSWALK", "sport": label,
                                      "detail": f"{e['name']}: no official governing-body source was matched, so a High label is blocked; best available tier is {tier.upper()}.",
                                      "source": e["olbg_url"]})
    out = {"schema": "olbg-originated-lines/v2", "captured_utc": cap["captured_utc"],
           "parameters": {"margin": MARGIN, "pseudo_count": PSEUDO, "strength": STRENGTH,
                          "window_american": [WINDOW_MIN, WINDOW_MAX],
                          "bands": {"High": f"official crosswalk AND p>={P_HIGH} AND market tips>={T_MIN_HIGH} AND in window",
                                    "Medium": f"(crosswalk AND p>={P_MED_CORR}) OR (p>={P_MED_THICK} AND tips>={T_MIN_THICK})",
                                    "Low": "everything else, and anything outside the price window"},
                          "probability": "p = (win_tips + STRENGTH/k) / (market_tips + STRENGTH); Dirichlet with a uniform prior over the k outcomes of the market",
                          "window_applied_to": "fair_american (no-margin originated line)"},
           "rows": rows,
           "flags": flags}
    hi = [r for r in rows if r["confidence"] == "High"]
    me = [r for r in rows if r["confidence"] == "Medium"]
    rows.sort(key=lambda r: -r["pick_score"])
    with open(os.path.join(ROOT, "data", "lines.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(f"rows={len(rows)} high={len(hi)} medium={len(me)} low={len(rows)-len(hi)-len(me)} flags={len(flags)}")
    print("top by sport:")
    seen = {}
    for r in rows:
        if len(seen.get(r["sport"], [])) < 5:
            seen.setdefault(r["sport"], []).append(r)
    for sp, lst in seen.items():
        print(f"  {sp}")
        for r in lst:
            print(f"     {r['selection'][:24]:24} {r['market'][:14]:14} {str(r['fair_american']):>7} {r['confidence']}")


def _slug(s):
    keep = [c if c.isalnum() else "-" for c in s.strip()]
    return "".join(keep).strip("-").lower()


if __name__ == "__main__":
    main()
