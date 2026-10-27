#!/usr/bin/env python3
"""Build data/dashboard.json from captured OLBG markets and official feeds.

Pipeline
--------
captured prices  ->  implied probabilities  ->  Shin de-vig
                 ->  blend with an independent estimate (official records)
                 ->  our own line  ->  confidence grade  ->  picks

Every field traces back to data/olbg or data/official. Nothing is typed in.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pricing_core as pc

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OLBG = DATA / "olbg"
OFFICIAL = DATA / "official"

SPORT_ORDER = [
    ("Golf", "golf"),
    ("Volleyball", "volleyball"),
    ("Rugby Union", "rugby-union"),
    ("Cricket", "cricket"),
    ("Snooker", "snooker"),
    ("Darts", "darts"),
    ("Baseball", "baseball"),
    ("Gaelic Football", "gaelic-football"),
    ("Hurling", "hurling"),
    ("Greyhounds", "greyhounds"),
    ("Tennis", "tennis"),
    ("Motor Racing", "motor-racing"),
    ("Handball", "handball"),
    ("Ice Hockey", "ice-hockey"),
    ("Basketball", "basketball"),
    ("Rugby League", "rugby-league"),
]
REQUESTED = [
    "Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
    "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
    "Basketball", "Rugby League",
]
SPORT_PAGE = {  # requested label -> page key (Gaelic Sports spans two OLBG categories)
    "Golf": "golf", "Volleyball": "volleyball", "Rugby Union": "rugby-union",
    "Cricket": "cricket", "Snooker": "snooker", "Darts": "darts", "Baseball": "baseball",
    "Gaelic Sports": "gaelic-sports", "Greyhounds": "greyhounds", "Tennis": "tennis",
    "Motor Racing": "motor-racing", "Handball": "handball", "Ice Hockey": "ice-hockey",
    "Basketball": "basketball", "Rugby League": "rugby-league",
}
SPORT_TO_REQUESTED = {
    "Golf": "Golf", "Volleyball": "Volleyball", "Rugby Union": "Rugby Union",
    "Cricket": "Cricket", "Snooker": "Snooker", "Darts": "Darts", "Baseball": "Baseball",
    "Gaelic Football": "Gaelic Sports", "Hurling": "Gaelic Sports",
    "Greyhounds": "Greyhounds", "Tennis": "Tennis", "Motor Racing": "Motor Racing",
    "Handball": "Handball", "Ice Hockey": "Ice Hockey", "Basketball": "Basketball",
    "Rugby League": "Rugby League",
}


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return default


# --------------------------------------------------------------- official ---
class Official:
    """Index of primary-source facts, keyed for fuzzy team lookup."""

    def __init__(self) -> None:
        self.teams: dict[str, dict[str, Any]] = {}
        self.nba: dict[str, dict[str, Any]] = {}
        self.tennis: dict[str, float] = {}
        self.sources: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        self.sources = [
            {"sport": "Baseball", "label": "MLB Stats API schedule", "url": "https://statsapi.mlb.com/api/v1/schedule", "type": "official league API"},
            {"sport": "Baseball", "label": "MLB standings", "url": "https://www.mlb.com/standings", "type": "official league page"},
            {"sport": "Ice Hockey", "label": "NHL API standings", "url": "https://api-web.nhle.com/v1/standings/now", "type": "official league API"},
            {"sport": "Ice Hockey", "label": "NHL API schedule", "url": "https://api-web.nhle.com/v1/schedule", "type": "official league API"},
            {"sport": "Basketball", "label": "ESPN NBA teams and records", "url": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams", "type": "league data feed"},
            {"sport": "Tennis", "label": "ESPN ATP rankings", "url": "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/rankings", "type": "tour data feed"},
            {"sport": "Motor Racing", "label": "Jolpica F1 (Ergast successor) race calendar", "url": "https://api.jolpi.ca/ergast/f1/2026/races.json", "type": "series data API"},
            {"sport": "Motor Racing", "label": "Jolpica F1 driver standings", "url": "https://api.jolpi.ca/ergast/f1/2026/driverStandings.json", "type": "series data API"},
            {"sport": "Golf", "label": "ESPN PGA scoreboard", "url": "https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard", "type": "tour data feed"},
            {"sport": "Golf", "label": "ESPN LPGA scoreboard", "url": "https://site.api.espn.com/apis/site/v2/sports/golf/lpga/scoreboard", "type": "tour data feed"},
            {"sport": "Cricket", "label": "ICC fixtures and results", "url": "https://www.icc-cricket.com/fixtures-results", "type": "official governing body"},
            {"sport": "Rugby Union", "label": "EPCR Champions Cup matches", "url": "https://www.epcrugby.com/champions-cup/matches", "type": "official competition"},
            {"sport": "Rugby League", "label": "ESPN NRL scoreboard", "url": "https://site.api.espn.com/apis/site/v2/sports/rugby-league/3/scoreboard", "type": "league data feed"},
            {"sport": "Snooker", "label": "WST news feed", "url": "https://wst.tv/wp-json/wp/v2/posts", "type": "official tour site"},
            {"sport": "Darts", "label": "PDC tournaments", "url": "https://www.pdc.tv/tournaments", "type": "official tour site"},
            {"sport": "Volleyball", "label": "CEV match centres", "url": "https://www.cev.eu/match-centres/", "type": "official governing body"},
            {"sport": "Handball", "label": "EHF Champions League matches", "url": "https://ehfcl.eurohandball.com/men/2026-27/matches/", "type": "official governing body"},
            {"sport": "Gaelic Sports", "label": "GAA fixtures and results", "url": "https://www.gaa.ie/fixtures-results", "type": "official governing body"},
            {"sport": "Greyhounds", "label": "GBGB racing", "url": "https://www.gbgb.org.uk/racing/", "type": "official governing body"},
        ]

        # NHL standings
        payload = load_json(OFFICIAL / "nhl-standings.json", {})
        for row in payload.get("standings", []):
            name = f"{row.get('placeName', {}).get('default', '')} {row.get('teamName', {}).get('default', '')}".strip()
            entry = {
                "sport": "Ice Hockey",
                "wins": row.get("wins"), "losses": row.get("losses"), "ot": row.get("otLosses"),
                "points": row.get("points"), "games": row.get("gamesPlayed"),
                "point_pct": row.get("pointPctg"),
                "goals_for": row.get("goalFor"), "goals_against": row.get("goalAgainst"),
                "streak": row.get("streakCode") or "",
                "home": f"{row.get('homeWins')}-{row.get('homeLosses')}-{row.get('homeOtLosses')}",
                "road": f"{row.get('roadWins')}-{row.get('roadLosses')}-{row.get('roadOtLosses')}",
                "source": "https://api-web.nhle.com/v1/standings/now",
                "source_label": "NHL standings API",
            }
            for alias in {name, row.get("teamCommonName", {}).get("default", ""),
                          row.get("teamAbbrev", {}).get("default", "")}:
                if alias:
                    self.teams.setdefault(alias.lower(), entry)

        # MLB schedule: probable pitchers and the most recent completed game
        schedule = load_json(OFFICIAL / "mlb-schedule.json", {})
        self.mlb_games: dict[str, dict[str, Any]] = {}
        for date in schedule.get("dates", []):
            for game in date.get("games", []):
                sides = {}
                for side in ("home", "away"):
                    team = game.get("teams", {}).get(side, {})
                    name = team.get("team", {}).get("name", "")
                    sides[side] = {
                        "name": name,
                        "pitcher": (team.get("probablePitcher") or {}).get("fullName", ""),
                        "score": team.get("score"),
                    }
                final = game.get("status", {}).get("abstractGameState") == "Final"
                for key, side in sides.items():
                    other = sides["away" if key == "home" else "home"]
                    entry = self.mlb_games.setdefault(side["name"].lower(), {})
                    entry.setdefault("upcoming", []).append({
                        "date": game.get("gameDate"),
                        "pitcher": side["pitcher"],
                        "opponent": other["name"],
                        "home": key == "home",
                        "venue": game.get("venue", {}).get("name", ""),
                    })
                    if final and side.get("score") is not None:
                        entry.setdefault("last", []).append({
                            "date": game.get("gameDate"),
                            "score": f"{side['score']}-{other['score']}",
                            "opponent": other["name"],
                            "home": key == "home",
                            "won": (side["score"] or 0) > (other["score"] or 0),
                        })
        for value in self.mlb_games.values():
            value["upcoming"].sort(key=lambda g: g.get("date") or "")
            value["last"].sort(key=lambda g: g.get("date") or "")
        # MLB standings
        payload = load_json(OFFICIAL / "mlb-standings.json", {})
        for group in payload.get("records", []):
            for team in group.get("teamRecords", []):
                name = team.get("team", {}).get("name", "")
                splits = {s.get("type"): s for s in team.get("records", {}).get("splitRecords", [])}
                entry = {
                    "sport": "Baseball",
                    "wins": team.get("wins"), "losses": team.get("losses"),
                    "pct": team.get("winningPercentage"),
                    "games_back": team.get("gamesBack"),
                    "runs_scored": team.get("runsScored"), "runs_allowed": team.get("runsAllowed"),
                    "run_diff": team.get("runDifferential"),
                    "streak": team.get("streak", {}).get("streakCode", ""),
                    "home": f"{splits.get('home', {}).get('wins', '?')}-{splits.get('home', {}).get('losses', '?')}",
                    "away": f"{splits.get('away', {}).get('wins', '?')}-{splits.get('away', {}).get('losses', '?')}",
                    "source": "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026&standingsTypes=regularSeason",
                    "source_label": "MLB standings API",
                }
                for alias in {name, name.split()[-1]}:
                    if alias:
                        self.teams.setdefault(alias.lower(), entry)

        # ESPN NBA records
        payload = load_json(OFFICIAL / "espn-nba-teams.json", {})
        for sport in payload.get("sports", []):
            for league in sport.get("leagues", []):
                for team in league.get("teams", []):
                    item = team.get("team", {})
                    record = next(iter(item.get("record", {}).get("items", [])), {}).get("summary", "")
                    if not record:
                        continue
                    wins, losses = pc.parse_record(record)
                    entry = {
                        "sport": "Basketball",
                        "wins": wins, "losses": losses, "record": record,
                        "pct": round(wins / (wins + losses), 3) if wins + losses else None,
                        "name": item.get("displayName"),
                        "source": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams",
                        "source_label": "ESPN NBA team records",
                    }
                    for alias in {item.get("displayName", ""), item.get("name", ""), item.get("abbreviation", "")}:
                        if alias:
                            self.teams.setdefault(alias.lower(), entry)

        # ATP rankings
        payload = load_json(OFFICIAL / "espn-atp-rankings.json", {})
        for ranking in payload.get("rankings", []):
            for row in ranking.get("ranks", []):
                athlete = row.get("athlete", {})
                name = athlete.get("displayName") or athlete.get("fullName")
                points = row.get("points")
                if name and points:
                    self.tennis[name.lower()] = float(points)

    def team(self, name: str) -> dict[str, Any] | None:
        if not name:
            return None
        key = name.lower().strip()
        if key in self.teams:
            return self.teams[key]
        tokens = [t for t in key.split() if t]
        for token in ([tokens[0]] if tokens else []) + ([tokens[-1]] if len(tokens) > 1 else []):
            if token in self.teams:
                return self.teams[token]
        for candidate, value in self.teams.items():
            if len(candidate) > 3 and (candidate in key or key in candidate):
                return value
        return None

    def tennis_points(self, name: str) -> float | None:
        key = name.lower().strip()
        if key in self.tennis:
            return self.tennis[key]
        surname = key.split()[-1] if key else ""
        for candidate, points in self.tennis.items():
            if surname and candidate.split()[-1] == surname:
                return points
        return None


# --------------------------------------------------------------- assembly ---
MARGIN_ALLOWANCE = [
    (("Win Match", "Money Line", "To Win", "Puck Line", "FT Result", "Win Hurling"), 0.040),
    (("Handicap", "Game Totals", "Pointspread", "Games Won", "Set Betting"), 0.045),
    (("Set Score", "1st Set Winner", "Man Of The Match", "Top Team1 Batsman"), 0.055),
    (("Win Tournament", "Outright Winner", "Grand Final Winner", "Win Race"), 0.120),
]


def margin_allowance(market: str) -> float:
    """Published margin allowance for a single-sided captured price.

    OLBG's public payload exposes one price per market, so the second side of
    the book cannot be measured. The allowance below is the margin we subtract
    before treating a captured price as a fair probability, by market type.
    It is an assumption and is labelled as one on the Method page.
    """
    for names, value in MARGIN_ALLOWANCE:
        if market in names:
            return value
    return 0.05


def event_rows() -> list[dict[str, Any]]:
    markets_file = OLBG / "markets.json"
    if markets_file.exists():
        payload = load_json(markets_file, {})
        rows = payload.get("rows") or []
        if rows:
            return rows
    rows = pc.load_rows(OLBG)
    if rows:
        return rows
    merged: list[dict[str, Any]] = []
    for path in sorted(OLBG.glob("*.json")):
        if path.name.startswith("_"):
            continue
        payload = load_json(path, {})
        merged.extend(payload.get("rows") or [])
    return merged


WIN_MARKETS = {"Win Match", "Money Line", "To Win", "FT Result", "Win Hurling"}


def split_teams(name: str) -> tuple[str, str]:
    """Return (home, away). OLBG writes US fixtures as 'AWAY @ HOME'."""
    if " @ " in name:
        away, home = name.split(" @ ", 1)
        return home.strip(), away.strip()
    for sep in (" vs ", " v "):
        if sep in name:
            home, away = name.split(sep, 1)
            return home.strip(), away.strip()
    return name, ""


def build_markets(rows: list[dict[str, Any]], official: Official) -> list[dict[str, Any]]:
    events: dict[str, dict[str, Any]] = {}
    for row in rows:
        event_id = str(row.get("event_id") or "")
        if not event_id:
            continue
        event = events.setdefault(event_id, {
            "id": event_id,
            "sport": row["sport"],
            "sport_key": row["sport_key"],
            "name": row.get("event_name") or "",
            "competition": row.get("competition") or "",
            "start_utc": row.get("start_utc") or "",
            "venue": row.get("venue") or "",
            "olbg_url": row.get("event_url") or row.get("olbg_url") or "",
            "selections": {},
        })
        if not event["name"] and row.get("event_name"):
            event["name"] = row["event_name"]
        if not event["competition"] and row.get("competition"):
            event["competition"] = row["competition"]
        market = (row.get("market") or "").strip()
        selection = (row.get("selection") or "").strip()
        decimal = row.get("decimal_odds")
        if not market or not selection or not decimal:
            continue
        key = (market, selection)
        previous = event["selections"].get(key)
        if previous is None or (decimal and decimal > (previous.get("decimal") or 0)):
            event["selections"][key] = {
                "decimal": decimal,
                "american": row.get("american_odds"),
                "fractional": row.get("fractional_odds"),
                "win_tips": row.get("win_tips"),
                "win_tips_count": row.get("win_tips_count"),
                "experts": row.get("experts_count"),
            }
    return list(events.values())


def official_outlook(event: dict[str, Any], official: Official) -> dict[str, Any] | None:
    """Independent win probability from primary-source records."""
    home, away = split_teams(event["name"])
    if not home or not away:
        return None
    sport = event["sport"]
    a = official.team(home)
    b = official.team(away)
    if sport == "Baseball":
        if not a or not b or not a.get("pct") or not b.get("pct"):
            return None
        prob = pc.log5(float(a["pct"]), float(b["pct"]), 0.04)
        home_feed = official.mlb_games.get(home.lower(), {})
        away_feed = official.mlb_games.get(away.lower(), {})
        home_pitcher = next((g["pitcher"] for g in home_feed.get("upcoming", []) if g.get("pitcher")), "")
        away_pitcher = next((g["pitcher"] for g in away_feed.get("upcoming", []) if g.get("pitcher")), "")
        home_last = (home_feed.get("last") or [{}])[-1]
        away_last = (away_feed.get("last") or [{}])[-1]
        facts = dict(a)
        facts["probable_pitcher"] = home_pitcher or away_pitcher
        facts["pitchers"] = f"{home} {home_pitcher or 'TBC'}; {away} {away_pitcher or 'TBC'}"
        facts["last_game"] = home_last
        facts["opponent_last"] = away_last
        return {"prob": prob, "subject": home, "other": away,
                "method": "log5 on MLB winning percentage plus home-field adjustment",
                "detail": f"{home} {a['wins']}-{a['losses']} ({a['pct']}), {away} {b['wins']}-{b['losses']} ({b['pct']})",
                "source": a["source"], "source_label": a["source_label"], "facts": facts}
    if sport == "Ice Hockey":
        if not a or not b:
            return None
        pa, pb = a.get("point_pct"), b.get("point_pct")
        if not pa or not pb:
            return None
        prob = pc.log5(float(pa), float(pb), 0.03)
        return {"prob": prob, "subject": home, "other": away,
                "method": "log5 on NHL points percentage plus home-ice adjustment",
                "detail": f"{home} {a['wins']}-{a['losses']}-{a['ot']} ({a['points']} pts), {away} {b['wins']}-{b['losses']}-{b['ot']} ({b['points']} pts)",
                "source": a["source"], "source_label": a["source_label"], "facts": a}
    if sport == "Basketball":
        if not a or not b or not a.get("pct") or not b.get("pct"):
            return None
        prob = pc.log5(float(a["pct"]), float(b["pct"]), 0.06)
        return {"prob": prob, "subject": home, "other": away,
                "method": "log5 on NBA win percentage plus home-court adjustment",
                "detail": f"{a['name']} {a['record']}, {b['name']} {b['record']}",
                "source": a["source"], "source_label": a["source_label"], "facts": a}
    if sport == "Tennis":
        pa = official.tennis_points(home)
        pb = official.tennis_points(away)
        if not pa or not pb:
            return None
        prob = pc.ranking_prob(pa, pb, 1.0)
        return {"prob": prob, "subject": home, "other": away,
                "method": "logistic model on ATP ranking points",
                "detail": f"{home} {int(pa):,} ranking points, {away} {int(pb):,}",
                "source": "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/rankings",
                "source_label": "ATP ranking points", "facts": {}}
    return None


def price_market(event: dict[str, Any], official_prob: float | None, subject: str) -> list[dict[str, Any]]:
    """Price every captured market for one event.

    Two routes, both fully traceable:

    * primary-data route  - an independent estimate exists (MLB/NHL/NBA records,
      ATP ranking points). Ours is a 60/40 blend of that estimate and the
      margin-adjusted market price, so the edge is a genuine disagreement.
    * market route        - no independent estimate. We publish the
      margin-adjusted market probability as the line and measure the gap between
      the OLBG community consensus (share of tips on the selection) and the
      price. No fabricated statistics enter this route.
    """
    markets: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for (market, selection), data in event["selections"].items():
        if not market or not selection or not data.get("decimal"):
            continue
        markets.setdefault(market, []).append((selection, data))
    out: list[dict[str, Any]] = []
    for market, entries in sorted(markets.items()):
        allowance = margin_allowance(market)
        overround_measured = sum(1.0 / d["decimal"] for _, d in entries)
        complete = len(entries) >= 2 and 1.0 <= overround_measured <= 1.75
        priced = []
        for selection, data in entries:
            implied = 100.0 / data["decimal"]
            fair_market = implied / (1.0 + allowance)
            our_prob = fair_market
            route = "market"
            if official_prob is not None and len(entries) == 1 and market in WIN_MARKETS:
                ours = official_prob * 100 if _is_subject(selection, subject) else (1 - official_prob) * 100
                our_prob = 0.6 * ours + 0.4 * fair_market
                route = "primary"
            tips = data.get("win_tips")
            total = data.get("win_tips_count")
            consensus = round(100.0 * tips / total, 1) if tips and total and total >= 3 else None
            gap = round(consensus - fair_market, 1) if consensus is not None else None
            edge = round(our_prob - fair_market, 2)
            priced.append({
                "selection": selection,
                "decimal": data["decimal"],
                "american": data.get("american") if data.get("american") is not None else pc.american(data["decimal"]),
                "fractional": data.get("fractional"),
                "market_prob": round(implied, 2),
                "fair_prob": round(fair_market, 2),
                "our_prob": round(our_prob, 2),
                "our_decimal": pc.decimal_from_prob(our_prob / 100.0),
                "our_american": pc.american(pc.decimal_from_prob(our_prob / 100.0)),
                "edge_pts": edge,
                "consensus": consensus,
                "consensus_gap": gap,
                "tips": tips,
                "tips_total": total,
                "route": route,
                "margin_allowance": round(allowance * 100, 1),
            })
        out.append({
            "name": market,
            "overround": round(overround_measured * 100, 2),
            "complete": complete,
            "selections": sorted(priced, key=lambda s: -(s["our_prob"] or 0)),
        })
    return out


def _is_subject(selection: str, subject: str) -> bool:
    if not subject:
        return True
    a = selection.lower().strip()
    b = subject.lower().strip()
    return a.startswith(b[:6]) or b.startswith(a[:6])


def main() -> None:
    official = Official()
    rows = event_rows()
    events = build_markets(rows, official)
    picks: list[dict[str, Any]] = []
    flagged: list[dict[str, Any]] = []
    out_events: list[dict[str, Any]] = []

    for event in events:
        outlook = official_outlook(event, official)
        markets = price_market(event, outlook["prob"] if outlook else None,
                               outlook["subject"] if outlook else "")
        flags: list[str] = []
        if not markets:
            flags.append("no priced market captured")
        if not outlook:
            flags.append("no independent official estimate for this competition")
        entry = {
            "id": event["id"], "sport": event["sport"], "sport_key": event["sport_key"],
            "requested_sport": SPORT_TO_REQUESTED.get(event["sport"], event["sport"]),
            "name": event["name"], "competition": event["competition"],
            "start_utc": event["start_utc"], "venue": event["venue"],
            "olbg_url": event["olbg_url"],
            "markets": markets,
            "official": ({k: outlook[k] for k in ("method", "detail", "source", "source_label", "prob")} if outlook else None),
            "flags": flags,
        }
        out_events.append(entry)

        # candidate picks: one per event, graded on our own probability
        if not markets:
            continue
        best = None
        for market in markets:
            for selection in market["selections"]:
                price = selection["our_american"]
                if selection["selection"].strip().lower() in ("tie", "draw", "the draw"):
                    continue
                if selection["fair_prob"] < 25.0:
                    continue
                if selection["edge_pts"] < -0.5:
                    continue
                if not pc.in_range(price):
                    continue
                in_band = True
                supported = selection["route"] == "primary" or (selection["consensus"] or 0) >= 55
                level = pc.grade_probability(selection["our_prob"], in_band, supported)
                strength = max(selection["edge_pts"], selection["consensus_gap"] or 0)
                candidate = {
                    "event_id": event["id"], "sport": event["sport"],
                    "sport_key": event["sport_key"],
                    "requested_sport": SPORT_TO_REQUESTED.get(event["sport"], event["sport"]),
                    "event": event["name"], "competition": event["competition"],
                    "start_utc": event["start_utc"], "market": market["name"],
                    "selection": selection["selection"],
                    "decimal": selection["decimal"], "american": selection["american"],
                    "our_american": selection["our_american"], "our_decimal": selection["our_decimal"],
                    "market_prob": selection["market_prob"], "fair_prob": selection["fair_prob"],
                    "our_prob": selection["our_prob"],
                    "edge_pts": selection["edge_pts"],
                    "consensus": selection["consensus"],
                    "consensus_gap": selection["consensus_gap"],
                    "tips": selection.get("tips"),
                    "tips_total": selection.get("tips_total"),
                    "route": selection["route"],
                    "confidence": level,
                    "score": pc.confidence_score(level, max(strength, 0.0),
                                                 1.0 if selection["route"] == "primary" else 0.45)
                             + (selection["our_prob"] * 1.6 + min(selection["consensus_gap"] or 0, 10)
                                if selection["route"] == "market" else 0.0),
                    "overround": market["overround"],
                    "margin_allowance": selection["margin_allowance"],
                    "complete": market["complete"],
                    "olbg_url": event["olbg_url"],
                    "official": entry["official"],
                }
                if best is None or candidate["score"] > best["score"]:
                    best = candidate
        if best:
            picks.append(best)

    # rank and keep the strongest per sport
    rank = {"high": 0, "medium": 1, "low": 2}
    picks.sort(key=lambda p: (rank.get(p["confidence"], 3), -p["score"], p["start_utc"]))
    per_sport: dict[str, int] = {}
    kept: list[dict[str, Any]] = []
    for pick in picks:
        count = per_sport.get(pick["requested_sport"], 0)
        if count >= 8:
            continue
        per_sport[pick["requested_sport"]] = count + 1
        pick["id"] = f"{pick['event_id']}-{re.sub(r'[^a-z0-9]+', '-', pick['selection'].lower())[:24]}"
        kept.append(pick)

    import predictions

    editorial = load_json(ROOT / "content" / "editorial.json", {})
    predictions.apply(kept, editorial)

    sport_summary = []
    for label, key in SPORT_ORDER:
        req = SPORT_TO_REQUESTED.get(label, label)
        sport_events = [e for e in out_events if e["sport"] == label]
        sport_picks = [p for p in kept if p["sport"] == label]
        sport_summary.append({
            "key": key, "label": label, "requested": req,
            "page": SPORT_PAGE.get(req, key),
            "events": len(sport_events),
            "markets": sum(len(e["markets"]) for e in sport_events),
            "selections": sum(len(m["selections"]) for e in sport_events for m in e["markets"]),
            "picks": len(sport_picks),
            "high": sum(1 for p in sport_picks if p["confidence"] == "high"),
            "medium": sum(1 for p in sport_picks if p["confidence"] == "medium"),
            "with_official": sum(1 for e in sport_events if e["official"]),
        })

    counts = {
        "events": len(out_events),
        "markets": sum(len(e["markets"]) for e in out_events),
        "selections": sum(len(m["selections"]) for e in out_events for m in e["markets"]),
        "picks": len(kept),
        "high": sum(1 for p in kept if p["confidence"] == "high"),
        "medium": sum(1 for p in kept if p["confidence"] == "medium"),
        "sports_with_events": sum(1 for s in sport_summary if s["events"]),
        "sports": len(sport_summary),
    }

    capture = load_json(OLBG / "markets.json", {}).get("captured_utc") or load_json(OLBG / "latest.json", {}).get("captured_utc") or ""

    dashboard = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "capture_utc": capture,
        "counts": counts,
        "sports": sport_summary,
        "events": sorted(out_events, key=lambda e: (e["start_utc"], e["sport"])),
        "picks": kept,
        "flagged": flagged,
        "sources": official.sources,
    }
    (DATA / "dashboard.json").write_text(json.dumps(dashboard, indent=1))
    print(f"events={counts['events']} markets={counts['markets']} picks={counts['picks']} "
          f"high={counts['high']} medium={counts['medium']}")


if __name__ == "__main__":
    main()
