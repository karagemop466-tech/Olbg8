#!/usr/bin/env python3
"""Assemble the research desk payload from captured OLBG and official payloads."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pricing as P
import write as W

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
DATA = ROOT.parent / "data"
DATA.mkdir(exist_ok=True)

SPORTS = json.loads((ROOT / "sports.json").read_text())["sports"]
SPORT_LABEL = {s["key"]: s["label"] for s in SPORTS}
SPORT_ID = {s["key"]: s["sport_id"] for s in SPORTS}
SPORT_OFFICIAL = {s["key"]: {"name": s["official_name"], "url": s["official_url"]} for s in SPORTS}

PICKS_PER_SPORT = 7
MIN_PICKS_PER_SPORT = 5
MAX_PICKS_PER_EVENT = 3
MAX_LOW_PER_SPORT = 2


def _num(text: str):
    m = re.search(r"([+-]?\d+(?:\.\d+)?)\s*$", text or "")
    return float(m.group(1)) if m else None


def market_shape(markets: dict) -> dict:
    """Read the handicap and total lines off the captured board.

    Returns the implied per-side scoring frame that the two lines describe, or
    an empty dict when either line is missing.
    """
    spread = None
    total = None
    for name, sels in markets.items():
        low = name.lower()
        if spread is None and any(k in low for k in ("handicap", "spread", "pointspread", "run line", "puck line", "line")):
            priced = []
            for sel in sels:
                val = _num(sel.get("selection", ""))
                if val is not None:
                    priced.append((val, sel["selection"].rsplit(" ", 1)[0]))
            if priced:
                val, team = min(priced)  # the favourite carries the negative line
                spread = {"market": name, "team": team, "line": val}
        if total is None and "total" in low:
            for sel in sels:
                val = _num(sel.get("selection", ""))
                if val is not None:
                    total = {"market": name, "line": val}
                    break
    if spread is None or total is None:
        return {}
    margin = -spread["line"]  # a side laying -5.5 is expected to win by 5.5
    home = (total["line"] + margin) / 2
    away = (total["line"] - margin) / 2
    return {
        "spread_market": spread["market"], "spread_team": spread["team"], "spread_line": spread["line"],
        "total_market": total["market"], "total_line": total["line"],
        "frame_home": round(home, 1), "frame_away": round(away, 1),
    }


def money_or_blank(am):
    try:
        return W.money(int(float(am)))
    except Exception:
        return ""


def board_line(sel: dict) -> str:
    return f"{sel.get('selection','')} {money_or_blank(sel.get('american'))}".strip()


def load(name):
    p = OUT / name
    return json.loads(p.read_text()) if p.exists() else None


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def nickname(team: str) -> str:
    toks = [t for t in re.split(r"\s+", (team or "").strip()) if t]
    return toks[-1].lower() if toks else ""


def official_table_facts(table: dict, team_name: str, sport: str) -> dict:
    """Look a team up in an official standings table by nickname match."""
    if not table or not team_name:
        return {}
    target = nickname(team_name)
    for key, row in table.items():
        if nickname(row.get("name") or key) == target:
            out = dict(row)
            if sport == "baseball":
                l10 = out.get("l10") or {}
                gp = (l10.get("w") or 0) + (l10.get("l") or 0)
                if gp:
                    out["l10_pct"] = l10["w"] / gp
                gp_all = (out.get("wins") or 0) + (out.get("losses") or 0)
                if gp_all:
                    out["pct"] = (out.get("wins") or 0) / gp_all
                    if out.get("run_diff") is not None:
                        out["diff_per_game"] = out["run_diff"] / gp_all
            if sport == "ice-hockey":
                l10g = (out.get("l10_wins") or 0) + (out.get("l10_losses") or 0) + (out.get("l10_ot_losses") or 0)
                if l10g:
                    out["l10_pct"] = out["l10_wins"] / l10g
                    out["l10"] = {"w": out.get("l10_wins"), "l": (out.get("l10_losses") or 0) + (out.get("l10_ot_losses") or 0)}
                gp = out.get("games_played") or 0
                if gp and out.get("goal_diff") is not None:
                    out["diff_per_game"] = out["goal_diff"] / gp
            return out
    return {}


def split_event_name(name: str) -> tuple[str, str]:
    """Return (home, away) from an OLBG event name where possible."""
    if not name:
        return "", ""
    if " @ " in name:
        away, home = name.split(" @ ", 1)
        return home.strip(), away.strip()
    if " vs " in name:
        a, b = name.split(" vs ", 1)
        return a.strip(), b.strip()
    return "", ""


def match_official(sport: str, home: str, away: str, start_utc: str, facts: dict):
    fixtures = (facts.get("sports", {}).get(sport, {}) or {}).get("fixtures", [])
    if not fixtures:
        return None
    hn, an = nickname(home), nickname(away)
    if sport == "baseball":
        hn, an = nickname(home), nickname(away)
    best, best_score = None, 0
    date = (start_utc or "")[:10]
    for f in fixtures:
        fh, fa = nickname(f.get("home")), nickname(f.get("away"))
        score = 0
        if hn and fh and (hn == fh or hn in (f.get("home") or "").lower()):
            score += 2
        if an and fa and (an == fa or an in (f.get("away") or "").lower()):
            score += 2
        fdate = (f.get("start_utc") or "")[:10]
        if date and fdate and abs(_days(fdate, date)) <= 1:
            score += 1
        if score > best_score:
            best, best_score = f, score
    return best if best_score >= 4 else None


def _days(a: str, b: str) -> int:
    try:
        da = datetime.strptime(a, "%Y-%m-%d")
        db = datetime.strptime(b, "%Y-%m-%d")
        return (da - db).days
    except Exception:
        return 99


def construct_events(feed: dict, boards: dict, facts: dict) -> list[dict]:
    events = {}
    for row in feed.get("rows", []):
        url = row["olbg_event_url"]
        ev = events.setdefault(url, {
            "olbg_url": url,
            "sport": row["sport_key"],
            "sport_label": row["sport_label"],
            "event_name": row["event"],
            "competition": row.get("competition") or "",
            "start_utc": row.get("start_utc") or "",
            "feed_rows": [],
            "markets": {},
            "event_id": (re.search(r"event_id=(\d+)", url) or [None, ""])[1],
        })
        ev["feed_rows"].append(row)
        if not ev["competition"] and row.get("competition"):
            ev["competition"] = row["competition"]
        if not ev["start_utc"] and row.get("start_utc"):
            ev["start_utc"] = row["start_utc"]

    # attach market boards from event pages
    boards_by_id = {b.get("event_id"): b for b in (boards or {}).get("events", []) if b.get("event_id")}
    for url, ev in events.items():
        board = boards_by_id.get(ev["event_id"])
        if board:
            if not ev["competition"] and board.get("competition"):
                ev["competition"] = board["competition"]
            for m in board.get("markets", []):
                sels = [s for s in m.get("selections", []) if s.get("decimal")]
                if len(sels) >= 2:
                    ev["markets"][m["market"]] = sels
            if not ev["start_utc"] and board.get("start_utc"):
                ev["start_utc"] = board["start_utc"]
        if not ev["markets"]:
            # fall back to the single market the feed row carries
            for r in ev["feed_rows"]:
                if r.get("market") and r.get("decimal"):
                    ev["markets"].setdefault(r["market"], []).append({
                        "selection": r["selection"], "decimal": r["decimal"],
                        "american": r.get("american"), "tip_record": r.get("tip_record"),
                        "consensus": r.get("consensus_pct"),
                    })
    # official crosswalk
    for ev in events.values():
        home, away = split_event_name(ev["event_name"])
        ev["home"], ev["away"] = home, away
        if not home:
            continue
        off = match_official(ev["sport"], home, away, ev["start_utc"], facts)
        if off:
            ev["official"] = {k: off.get(k) for k in
                              ("competition", "start_utc", "venue", "source", "source_url",
                               "probable_home", "probable_away", "game_id", "official_date")}
            ev["official_confirmed"] = True
            ev["competition"] = off.get("competition") or ev["competition"]
            ev["venue"] = off.get("venue")
            ev["probable_home"] = off.get("probable_home")
            ev["probable_away"] = off.get("probable_away")
            if not ev["start_utc"]:
                ev["start_utc"] = off.get("start_utc") or ""
            table = (facts.get("sports", {}).get(ev["sport"], {}) or {}).get("table", {})
            ev["home_table"] = official_table_facts(table, off.get("home") or home, ev["sport"])
            ev["away_table"] = official_table_facts(table, off.get("away") or away, ev["sport"])
            ev["home"] = off.get("home") or home
            ev["away"] = off.get("away") or away
    return list(events.values())


def score_market(ev: dict, market: str, selections: list[dict]) -> list[dict]:
    fair = P.fair_board([{"selection": s["selection"], "decimal": float(s["decimal"])} for s in selections], ev["sport"])
    # optional independent tilt for two-way match markets with official form
    low = market.lower()
    two_way = len(fair) == 2
    if two_way and ev.get("official_confirmed") and any(k in low for k in ("money", "win match", "winner", "match")):
        tilt = P.form_tilt(ev.get("home_table") or {}, ev.get("away_table") or {}, ev["sport"])
        tilt += P.HOME_EDGE.get(ev["sport"], 0.0)
        probs = P.apply_tilt([f["fair_prob"] for f in fair], tilt)
        for f, p in zip(fair, probs):
            f["fair_prob"] = p
            f["fair_decimal"] = 1 / p
            f["fair_american"] = P.decimal_to_american(f["fair_decimal"])
    out = []
    for s, f in zip(selections, fair):
        row = {**s, **f}
        row["raw_implied"] = P.implied(float(s["decimal"]))
        row["edge_pts"] = (row["fair_prob"] - row["raw_implied"]) * 100
        row["market"] = market
        row["ev"] = P.expected_value(row["fair_prob"], float(s["decimal"]))
        out.append(row)
    return out


SUPPORTED = ("money", "win match", "win tournament", "match winner", "winner", "match betting",
             "run line", "pointspread", "handicap", "spread", "game totals", "total", "games won",
             "set betting", "1st set", "sets", "over/under", "match specials", "outright",
             "grand final", "fastest qualifier", "top ", "to win", "stage of elimination")
OUTRIGHT_MARKETS = ("win tournament", "outright", "grand final", "fastest qualifier", "top ", "to win")
MAX_SELECTIONS_PER_MARKET = 9


def candidate_picks(events: list[dict]) -> list[dict]:
    cands = []
    for ev in events:
        for market, sels in ev["markets"].items():
            low = market.lower()
            if not any(k in low for k in SUPPORTED):
                continue
            outright = any(k in low for k in OUTRIGHT_MARKETS)
            if len(sels) > (200 if outright else 4):
                continue
            try:
                scored = score_market(ev, market, sels)
            except Exception:
                continue
            if outright:
                scored = sorted(scored, key=lambda r: -r["fair_prob"])[:MAX_SELECTIONS_PER_MARKET]
            for s in scored:
                am = s.get("fair_american")
                if am is None or not P.in_price_window(am):
                    continue
                if s["fair_prob"] < (0.04 if outright else 0.45):
                    continue
                cands.append({
                    "sport": ev["sport"], "sport_label": ev["sport_label"],
                    "event_name": ev["event_name"], "competition": ev["competition"],
                    "start_utc": ev["start_utc"], "venue": ev.get("venue"),
                    "selection": s["selection"], "market": market,
                    "price_decimal": float(s["decimal"]),
                    "price_american": int(float(s["american"])) if s.get("american") not in (None, "") else P.decimal_to_american(float(s["decimal"])),
                    "tip_record": s.get("tip_record") or "", "consensus": s.get("consensus") or "",
                    "our_prob": s["fair_prob"], "our_fair_american": am, "our_fair_decimal": s["fair_decimal"],
                    "market_implied": s["raw_implied"], "edge_pts": s["edge_pts"], "ev": s["ev"],
                    "confidence": P.confidence_band(s["fair_prob"]),
                    "olbg_url": ev["olbg_url"],
                    "official_confirmed": bool(ev.get("official_confirmed")),
                    "official_url": (ev.get("official") or {}).get("source_url"),
                    "official_source": (ev.get("official") or {}).get("source"),
                    "venue": ev.get("venue"),
                    "home": ev.get("home"), "away": ev.get("away"),
                    "home_table": ev.get("home_table") or {}, "away_table": ev.get("away_table") or {},
                    "probable_home": ev.get("probable_home"), "probable_away": ev.get("probable_away"),
                    "basis": "official-feed + de-margined board" if ev.get("official_confirmed") else "de-margined OLBG board",
                    "board_extra": [
                        (m, ", ".join(board_line(x) for x in sels[:2] if x.get("selection")))
                        for m, sels in ev["markets"].items() if m != market
                    ][:3],
                    "shape": market_shape(ev["markets"]),
                    "market_size": len(sels),
                    "event_pick_index": 0,
                })
    return cands


def select_picks(cands: list[dict], events: list[dict]) -> list[dict]:
    by_sport: dict[str, list[dict]] = {}
    for c in cands:
        by_sport.setdefault(c["sport"], []).append(c)
    chosen = []
    for sport, rows in by_sport.items():
        def keyf(r):
            return (-r["our_prob"], -float(r["consensus"] or 0), abs(r["price_american"]))
        rows.sort(key=keyf)
        outright_events = {e["olbg_url"] for e in events if e["sport"] == sport
                           and any(len(v) >= 8 for v in e["markets"].values())}
        for low_cap in (MAX_LOW_PER_SPORT, 6):
            picked, per_event, low_used = [], {}, 0
            for r in rows:
                cap = 5 if r["olbg_url"] in outright_events else MAX_PICKS_PER_EVENT
                if per_event.get(r["olbg_url"], 0) >= cap:
                    continue
                if r["confidence"] == "low":
                    if low_used >= low_cap:
                        continue
                    low_used += 1
                picked.append(r)
                per_event[r["olbg_url"]] = per_event.get(r["olbg_url"], 0) + 1
                if len(picked) >= PICKS_PER_SPORT:
                    break
            if len(picked) >= MIN_PICKS_PER_SPORT or low_cap >= 6:
                break
        chosen.extend(picked)
    return chosen


def main() -> int:
    feed = load("olbg_feed.json") or {"rows": []}
    boards = load("olbg_events.json") or {"events": []}
    facts = load("official_facts.json") or {"sports": {}, "sources": {}}

    events = construct_events(feed, boards, facts)
    cands = candidate_picks(events)
    picks = select_picks(cands, events)

    seen_per_event = {}
    for i, p in enumerate(picks):
        seen_per_event[p["olbg_url"]] = seen_per_event.get(p["olbg_url"], 0) + 1
        p["event_pick_index"] = seen_per_event[p["olbg_url"]] - 1
        p["id"] = f"{p['sport']}-{i + 1:02d}"
        p["headline"] = W.headline(p)
        p["prediction"] = W.build_prediction(p, facts_available=bool(p["official_confirmed"]))
        p["words"] = W.word_count(p["prediction"])
    pick_ids = {p["olbg_url"] + "|" + p["selection"] + "|" + p["market"] for p in picks}
    for p in picks:
        p["flags"] = []
        if p["words"] < 30:
            p["flags"].append("prose under 30 words")
        if not p["official_confirmed"]:
            p["flags"].append("no official fixture crosswalk")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sport_rows = []
    for s in SPORTS:
        sp_picks = [p for p in picks if p["sport"] == s["key"]]
        sp_events = [e for e in events if e["sport"] == s["key"]]
        sport_rows.append({
            "key": s["key"], "label": s["label"], "sport_id": s["sport_id"],
            "olbg_hub": s["hub"], "official_name": s["official_name"], "official_url": s["official_url"],
            "events": len(sp_events), "listings": sum(len(e["feed_rows"]) for e in sp_events),
            "picks": len(sp_picks),
            "high": sum(1 for p in sp_picks if p["confidence"] == "high"),
            "official_confirmed": sum(1 for e in sp_events if e.get("official_confirmed")),
            "target_met": len(sp_picks) >= MIN_PICKS_PER_SPORT,
        })

    desk = {
        "built_utc": now,
        "sport_count": len(SPORTS),
        "summary": {
            "sports": len(SPORTS),
            "events": len(events),
            "listings": sum(len(e["feed_rows"]) for e in events),
            "markets_captured": sum(len(e["markets"]) for e in events),
            "selections_priced": sum(len(v) for e in events for v in e["markets"].values()),
            "picks": len(picks),
            "high": sum(1 for p in picks if p["confidence"] == "high"),
            "medium": sum(1 for p in picks if p["confidence"] == "medium"),
            "low": sum(1 for p in picks if p["confidence"] == "low"),
            "official_confirmed_events": sum(1 for e in events if e.get("official_confirmed")),
            "sports_with_picks": len({p["sport"] for p in picks}),
        },
        "sports": sport_rows,
        "picks": picks,
        "events": [{k: v for k, v in e.items() if k != "feed_rows"} | {"feed_count": len(e["feed_rows"])} for e in events],
        "sources": facts.get("sources", {}),
        "official_sports": list((facts.get("sports") or {}).keys()),
    }
    (DATA / "desk.json").write_text(json.dumps(desk, indent=1), encoding="utf-8")
    print(json.dumps(desk["summary"], indent=1))
    for row in sport_rows:
        print(f"{row['label']:<16} events={row['events']:>3} picks={row['picks']:>2} high={row['high']:>2} official={row['official_confirmed']:>2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
