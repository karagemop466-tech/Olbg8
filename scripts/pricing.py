#!/usr/bin/env python3
"""Originator: turn every OLBG outcome into our own fair line + offered price.

Method (documented on methodology.html, reproducible from this file):
 1. Market probability  p_mkt = (1/decimal) / sum(1/decimal) over the market
    (proportional de-vig of the prices OLBG displayed).
 2. Tipster probability  p_tip = (win_tips + k*p_mkt) / (sum(win_tips) + k)
    (Bayesian shrinkage so small tip samples cannot dominate).
 3. Our fair probability  p_fair = (1-w)*p_mkt + w*p_tip,  w = min(0.35, N/(N+12))
    where N = number of win tips in that market.
 4. Our offered price = fair decimal * (1 - MARGIN), MARGIN = 3%.
 5. Value at the displayed OLBG price = p_fair * decimal_olbg - 1.
Confidence: HIGH p_fair >= 0.70, MEDIUM 0.55-0.70, LOW < 0.55.
Eligibility band (requested): displayed American odds between -250 and +10000.

Only inputs observed on the cited OLBG event page are used. No outside numbers.
"""
import json, math, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
K = 6.0
W_CAP = 0.35
MARGIN = 0.03
BAND_LOW, BAND_HIGH = -250, 10000

WIN_MARKETS = [
    "Win Match", "Money Line", "To Win", "FT Result", "Win Tournament",
    "Outright Winner", "Win Race", "Win Hurling", "Win Football",
    "Grand Final Winner", "Daily Races",
]


def fair_american(p):
    if p is None or p <= 0 or p >= 1:
        return None
    if p >= 0.5:
        return int(round(-100.0 * p / (1.0 - p)))
    return int(round(100.0 * (1.0 - p) / p))


def dec_to_american(d):
    if d is None or d <= 1:
        return None
    return int(round((d - 1) * 100)) if d >= 2.0 else int(round(-100.0 / (d - 1)))


def confidence(p):
    if p is None:
        return None
    if p >= 0.70:
        return "High"
    if p >= 0.55:
        return "Medium"
    return "Low"


def in_band(a):
    return a is not None and BAND_LOW <= a <= BAND_HIGH


def build_lines():
    events = json.loads((ROOT / "data" / "markets.json").read_text())
    out_events, n_lines, n_incomplete = [], 0, 0
    for ev in events:
        ev_out = {
            "sport": ev["sport_name"],
            "event_id": ev["event_id"],
            "event": ev["event"],
            "tournament": ev.get("tournament"),
            "event_date": ev.get("event_date"),
            "olbg_url": "https://www.olbg.com/betting-tips/" + (ev.get("olbg_slug") or "") + f"?event_id={ev['event_id']}",
            "markets": [],
        }
        for mk in ev["markets"]:
            outs = [o for o in mk["outcomes"] if o.get("decimal") and o["decimal"] > 1.01]
            if len(outs) < 2:
                n_incomplete += 1
                continue
            raw = [1.0 / o["decimal"] for o in outs]
            over = sum(raw)
            if over < 0.90:  # market shown incomplete -> refuse to price
                n_incomplete += 1
                continue
            tips_total = sum((o.get("win_tips") or 0) for o in outs)
            n_tips_field = max((o.get("win_tips_count") or 0) for o in outs)
            N = tips_total if tips_total > 0 else 0
            w = min(W_CAP, N / (N + 12.0)) if N else 0.0
            priced = []
            for o, r in zip(outs, raw):
                p_mkt = r / over
                tips = o.get("win_tips") or 0
                if N:
                    p_tip = (tips + K * p_mkt) / (N + K)
                else:
                    p_tip = p_mkt
                p_fair = (1 - w) * p_mkt + w * p_tip
                # OLBG tipsters concentrate on the draw in 3-way markets (handball,
                # Gaelic football); cap any draw deviation from the market at 3pp so a
                # small tip sample cannot invent a draw probability.
                if str(o.get("selection", "")).strip().lower() in ("tie", "draw"):
                    p_fair = min(max(p_fair, p_mkt - 0.03), p_mkt + 0.03)
                d_fair = 1.0 / p_fair if p_fair > 0 else None
                d_ours = d_fair * (1 - MARGIN) if d_fair else None
                priced.append({
                    "selection": o["selection"],
                    "olbg_decimal": o["decimal"],
                    "olbg_american": o.get("american"),
                    "p_market": round(p_mkt, 4),
                    "p_tipster_smoothed": round(p_tip, 4),
                    "tip_weight": round(w, 3),
                    "tips_on_selection": tips,
                    "tips_in_market": N,
                    "p_fair": round(p_fair, 4),
                    "fair_decimal": round(d_fair, 2) if d_fair else None,
                    "fair_american": fair_american(p_fair),
                    "our_decimal": round(d_ours, 2) if d_ours else None,
                    "our_american": dec_to_american(d_ours),
                    "value_at_olbg_price": round(p_fair * o["decimal"] - 1, 3),
                    "confidence": confidence(p_fair),
                    "in_requested_band": in_band(o.get("american")),
                })
                n_lines += 1
            # completeness of the market as displayed
            ev_out["markets"].append({
                "market": mk["name"],
                "overround": round(over, 4),
                "outcome_count": len(outs),
                "tips_in_market": N,
                "field_tips": n_tips_field,
                "is_win_market": mk["name"] in WIN_MARKETS,
                "outcomes": priced,
            })
        if ev_out["markets"]:
            out_events.append(ev_out)
    return out_events, n_lines, n_incomplete


OUTRIGHT = {"Win Tournament", "Outright Winner", "Win Race", "Grand Final Winner",
            "Daily Races", "Win Hurling", "Win Football"}
MIN_P_MATCH = 0.45
MIN_P_OUTRIGHT = 0.08


def build_picks(events):
    picks = []
    for ev in events:
        cands = []
        for m in ev["markets"]:
            floor = MIN_P_OUTRIGHT if m["market"] in OUTRIGHT else MIN_P_MATCH
            for o in m["outcomes"]:
                if o["in_requested_band"] and o["p_fair"] >= floor:
                    cands.append((m, o))
        if not cands:
            continue
        # best supported selection in the event: highest fair probability, then value
        cands.sort(key=lambda mo: (-mo[1]["p_fair"], -(mo[1]["value_at_olbg_price"] or 0)))
        mk, o = cands[0]
        mk_name = mk["market"]
        picks.append({
            "sport": ev["sport"],
            "event_id": ev["event_id"],
            "event": ev["event"],
            "tournament": ev["tournament"],
            "event_date": ev["event_date"],
            "market": mk_name,
            "selection": o["selection"],
            "olbg_decimal": o["olbg_decimal"],
            "olbg_american": o["olbg_american"],
            "fair_decimal": o["fair_decimal"],
            "fair_american": o["fair_american"],
            "our_decimal": o["our_decimal"],
            "our_american": o["our_american"],
            "p_fair": o["p_fair"],
            "value_at_olbg_price": o["value_at_olbg_price"],
            "confidence": o["confidence"],
            "tips_on_selection": o["tips_on_selection"],
            "tips_in_market": o["tips_in_market"],
            "olbg_url": ev["olbg_url"],
            "market_count": len(ev["markets"]),
            "outcome_count": sum(m["outcome_count"] for m in ev["markets"]),
        })
    picks.sort(key=lambda p: ({"High": 2, "Medium": 1, "Low": 0}[p["confidence"]], p["p_fair"]), reverse=True)
    return picks


def main():
    events, n_lines, n_incomplete = build_lines()
    (ROOT / "data" / "lines.json").write_text(json.dumps(events, indent=1) + "\n")
    picks = build_picks(events)
    (ROOT / "data" / "picks.json").write_text(json.dumps(picks, indent=1) + "\n")
    by_sport = collections.Counter(p["sport"] for p in picks)
    conf = collections.Counter(p["confidence"] for p in picks)
    print(f"events priced={len(events)} lines={n_lines} markets skipped={n_incomplete} picks={len(picks)}")
    print("confidence:", dict(conf))
    print("picks by sport:", dict(by_sport))


if __name__ == "__main__":
    main()
