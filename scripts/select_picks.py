#!/usr/bin/env python3
"""Choose up to five published picks per covered sport from our originated lines.

Rules
  * Only selections whose OLBG price sits in the requested band (-250 .. +10000).
  * Match markets need fair probability >= 0.45; outright markets >= 0.08.
  * One pick per event, except outright markets where two selections are allowed.
  * Ranking: confidence tier, then fair probability, then value at the OLBG price.
  * OLBG's "Gaelic Sports" category is published as one sport (football + hurling).
"""
import json, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPORTS = [
    ("golf", "Golf", "⛳"),
    ("volleyball", "Volleyball", "🏐"),
    ("rugby-union", "Rugby Union", "🏉"),
    ("cricket", "Cricket", "🏏"),
    ("snooker", "Snooker", "🎱"),
    ("darts", "Darts", "🎯"),
    ("baseball", "Baseball", "⚾"),
    ("gaelic-sports", "Gaelic Sports", "🏐"),
    ("greyhounds", "Greyhounds", "🐕"),
    ("tennis", "Tennis", "🎾"),
    ("motor-racing", "Motor Racing", "🏎️"),
    ("handball", "Handball", "🤾"),
    ("ice-hockey", "Ice Hockey", "🏒"),
    ("basketball", "Basketball", "🏀"),
    ("rugby-league", "Rugby League", "🏉"),
]
ALIAS = {
    "Tennis": "tennis", "Basketball": "basketball", "Golf": "golf", "Cricket": "cricket",
    "Snooker": "snooker", "Rugby Union": "rugby-union", "Rugby League": "rugby-league",
    "Baseball": "baseball", "Ice Hockey": "ice-hockey", "Motor Racing": "motor-racing",
    "Darts": "darts", "Handball": "handball", "Volleyball": "volleyball",
    "Gaelic Football": "gaelic-sports", "Hurling": "gaelic-sports", "Greyhounds": "greyhounds",
}
OUTRIGHT = {"Win Tournament", "Outright Winner", "Win Race", "Grand Final Winner",
            "Daily Races", "Win Hurling", "Win Football"}
MIN_P_MATCH, MIN_P_OUTRIGHT, MIN_P_GREYHOUND = 0.45, 0.08, 0.0
CONF_RANK = {"High": 2, "Medium": 1, "Low": 0}
MAX_PER_SPORT = 5


def tier(p):
    return "High" if p >= 0.70 else ("Medium" if p >= 0.55 else "Low")


def candidates_from_lines(events):
    out = []
    for ev in events:
        for mk in ev["markets"]:
            floor = MIN_P_OUTRIGHT if mk["market"] in OUTRIGHT else MIN_P_MATCH
            for o in mk["outcomes"]:
                if not o["in_requested_band"] or o["p_fair"] < floor:
                    continue
                out.append({
                    "sport_key": ALIAS.get(ev["sport"]),
                    "olbg_sport": ev["sport"],
                    "event_id": ev["event_id"],
                    "event": ev["event"],
                    "tournament": ev["tournament"],
                    "event_date": ev["event_date"],
                    "market": mk["market"],
                    "selection": o["selection"],
                    "olbg_decimal": o["olbg_decimal"],
                    "olbg_american": o["olbg_american"],
                    "fair_decimal": o["fair_decimal"],
                    "fair_american": o["fair_american"],
                    "our_decimal": o["our_decimal"],
                    "our_american": o["our_american"],
                    "p_market": o["p_market"],
                    "p_fair": o["p_fair"],
                    "value_at_olbg_price": o["value_at_olbg_price"],
                    "confidence": tier(o["p_fair"]),
                    "tips_on_selection": o["tips_on_selection"],
                    "tips_in_market": o["tips_in_market"],
                    "is_outright": mk["market"] in OUTRIGHT,
                    "olbg_url": ev["olbg_url"],
                    "data_status": "priced from full market (proportional de-vig + consensus blend)",
                })
    return out


def greyhound_candidates():
    fx = json.loads((ROOT / "data" / "fixtures.json").read_text())
    out = []
    for r in fx:
        if r.get("sport") != "Greyhounds" or not r.get("decimal"):
            continue
        dec = r["decimal"]
        p_raw = round(1.0 / dec, 4)
        if not (-250 <= (r.get("american") and int(r["american"])) <= 10000):
            continue
        out.append({
            "sport_key": "greyhounds",
            "olbg_sport": "Greyhounds",
            "event_id": r["event_id"],
            "event": r["event"],
            "tournament": None,
            "event_date": (r.get("start_utc") or "")[:10],
            "market": r.get("market"),
            "selection": r.get("selection"),
            "olbg_decimal": dec,
            "olbg_american": int(r["american"]) if r.get("american") else None,
            "fair_decimal": dec,
            "fair_american": int(r["american"]) if r.get("american") else None,
            "our_decimal": round(dec * 0.97, 2),
            "our_american": None,
            "p_market": p_raw,
            "p_fair": p_raw,
            "value_at_olbg_price": 0.0,
            "confidence": "Low",
            "tips_on_selection": r.get("tips"),
            "tips_in_market": r.get("tips_total"),
            "is_outright": True,
            "olbg_url": r["olbg_url"],
            "data_status": "single tipped runner only: OLBG greyhound race pages do not embed a market payload, so no de-vig is possible (flagged)",
        })
    return out


def main():
    events = json.loads((ROOT / "data" / "lines.json").read_text())
    cands = candidates_from_lines(events) + greyhound_candidates()
    by_sport = collections.defaultdict(list)
    for c in cands:
        if c["sport_key"]:
            by_sport[c["sport_key"]].append(c)

    published = []
    for key, name, icon in SPORTS:
        pool = sorted(by_sport.get(key, []),
                      key=lambda c: (CONF_RANK[c["confidence"]], c["p_fair"], c["value_at_olbg_price"] or 0),
                      reverse=True)
        chosen, per_event = [], collections.Counter()
        for c in pool:
            cap = 2 if (c["is_outright"] and key in {"golf", "darts", "motor-racing"}) else 1
            if per_event[c["event_id"]] >= cap:
                continue
            per_event[c["event_id"]] += 1
            chosen.append(c)
            if len(chosen) >= MAX_PER_SPORT:
                break
        for i, c in enumerate(chosen, 1):
            c = dict(c)
            c["sport"] = name
            c["sport_icon"] = icon
            c["sport_slug"] = key
            c["rank"] = i
            c["pick_id"] = f"{key}-{i}"
            published.append(c)

    (ROOT / "data" / "picks.json").write_text(json.dumps(published, indent=1) + "\n")
    cnt = collections.Counter(p["sport"] for p in published)
    print("published picks:", len(published))
    for key, name, _ in SPORTS:
        print(f"  {name:16s} {cnt.get(name,0)}")
    missing = [n for _, n, _ in SPORTS if cnt.get(n, 0) < 5]
    print("sports below five:", missing)


if __name__ == "__main__":
    main()
