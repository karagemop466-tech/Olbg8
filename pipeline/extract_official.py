#!/usr/bin/env python3
"""Normalise captured official-source payloads into one facts file.

Only values that appear in an official payload are written. Missing values stay
missing; every fixture and table row keeps the URL it came from so the site can
link it directly.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import rawio

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
OUT = ROOT / "out"
OUT.mkdir(parents=True, exist_ok=True)

SOURCES = {
    "baseball": [
        ("official_baseball_0", "MLB.com StatsAPI schedule (probable pitchers, venue)", "https://statsapi.mlb.com/api/v1/schedule?sportId=1&hydrate=probablePitcher,linescore,team,venue"),
        ("official_baseball_1", "MLB.com StatsAPI recent results", "https://statsapi.mlb.com/api/v1/schedule?sportId=1&hydrate=linescore,team"),
        ("official_baseball_2", "MLB.com StatsAPI standings", "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026&standingsTypes=regularSeason"),
        ("official_baseball_3", "MLB.com StatsAPI clubs", "https://statsapi.mlb.com/api/v1/teams?sportId=1&season=2026"),
    ],
    "ice-hockey": [
        ("official_ice_hockey_0", "NHL.com schedule API", "https://api-web.nhle.com/v1/schedule/now"),
        ("official_ice_hockey_1", "NHL.com standings API", "https://api-web.nhle.com/v1/standings/now"),
    ],
    "motor-racing": [
        ("official_motor_racing_0", "Ergast mirror of FIA Formula 1 race calendar (jolpi.ca)", "https://api.jolpi.ca/ergast/f1/current/races.json"),
        ("official_motor_racing_1", "Ergast mirror of FIA Formula 1 driver standings (jolpi.ca)", "https://api.jolpi.ca/ergast/f1/current/driverStandings.json"),
        ("official_motor_racing_2", "Ergast mirror of FIA Formula 1 constructor standings (jolpi.ca)", "https://api.jolpi.ca/ergast/f1/current/constructorStandings.json"),
        ("official_motor_racing_3", "Ergast mirror of last Formula 1 race result (jolpi.ca)", "https://api.jolpi.ca/ergast/f1/current/last/results.json"),
        ("official_motor_racing_4", "Formula1.com 2026 race calendar", "https://www.formula1.com/en/racing/2026"),
    ],
    "tennis": [
        ("official_tennis_0", "WTA Tour scores", "https://www.wtatennis.com/scores"),
        ("official_tennis_1", "WTA Tour singles rankings", "https://www.wtatennis.com/rankings/singles"),
    ],
    "golf": [
        ("official_golf_0", "PGA TOUR schedule", "https://www.pgatour.com/schedule"),
        ("official_golf_1", "LPGA tournament schedule", "https://www.lpga.com/tournaments"),
        ("official_golf_2", "PGA TOUR leaderboard", "https://www.pgatour.com/leaderboard"),
    ],
    "cricket": [
        ("official_cricket_0", "ICC fixtures and results", "https://www.icc-cricket.com/fixtures-results"),
        ("official_cricket_1", "ICC men's ODI team rankings", "https://www.icc-cricket.com/rankings/mens/team-rankings/odi"),
    ],
    "rugby-union": [
        ("official_rugby_union_0", "EPCR (Champions Cup) fixtures page", "https://www.epcrugby.com/"),
        ("official_rugby_union_2", "United Rugby Championship fixtures", "https://www.unitedrugby.com/"),
        ("official_rugby_union_3", "LNR Pro D2 calendar and results", "https://prod2.lnr.fr/calendrier-et-resultats"),
        ("official_rugby_union_4", "LNR Top 14 calendar and results", "https://top14.lnr.fr/calendrier-et-resultats"),
    ],
    "volleyball": [
        ("official_volleyball_0", "Volleyball World competitions", "https://en.volleyballworld.com/volleyball/competitions/"),
        ("official_volleyball_2", "CEV match centres", "https://www.cev.eu/match-centres/"),
    ],
    "handball": [
        ("official_handball_1", "EHF (eurohandball.com) matches", "https://www.eurohandball.com/en/"),
    ],
    "gaelic-sports": [
        ("official_gaelic_sports_0", "GAA fixtures and results", "https://www.gaa.ie/fixtures-results/"),
    ],
    "greyhounds": [
        ("official_greyhounds_0", "GBGB results", "https://www.gbgb.org.uk/results"),
        ("official_greyhounds_2", "GBGB race cards", "https://www.gbgb.org.uk/race-cards/"),
    ],
    "darts": [
        ("official_darts_0", "PDC (pdc.tv) tournaments", "https://www.pdc.tv/tournaments"),
    ],
    "snooker": [
        ("official_snooker_0", "World Snooker Tour matches", "https://www.wst.tv/matches"),
        ("official_snooker_1", "World Snooker Tour rankings", "https://www.wst.tv/rankings"),
    ],
    "basketball": [
        ("official_basketball_3", "NBA.com games", "https://www.nba.com/games"),
    ],
    "rugby-league": [],
}


def read(name: str) -> str:
    return rawio.read(name)


def load_json(name: str):
    t = read(name)
    try:
        return json.loads(t)
    except Exception:
        return None


def source_register() -> dict:
    reg = {}
    for sport, items in SOURCES.items():
        rows = []
        for name, label, url in items:
            t = read(name)
            rows.append({"capture": name, "label": label, "url": url, "chars": len(t), "ok": bool(t)})
        reg[sport] = rows
    return reg


# ------------------------------------------------------------------ baseball
def baseball() -> dict:
    sch = load_json("official_baseball_0") or {}
    recent = load_json("official_baseball_1") or {}
    stand = load_json("official_baseball_2") or {}
    clubs = load_json("official_baseball_3") or {}

    teams = {}
    for t in clubs.get("teams", []):
        teams[t["id"]] = {"name": t.get("name"), "abbrev": t.get("abbreviation"), "id": t["id"]}

    table = {}
    for rec in stand.get("records", []):
        for tr in rec.get("teamRecords", []):
            splits = {s["type"]: {"w": s["wins"], "l": s["losses"], "pct": s.get("pct")}
                      for s in tr.get("records", {}).get("splitRecords", [])}
            table[tr["team"]["id"]] = {
                "name": tr["team"]["name"],
                "wins": tr["wins"], "losses": tr["losses"], "pct": tr.get("winningPercentage"),
                "division_rank": tr.get("divisionRank"), "league_rank": tr.get("leagueRank"),
                "games_back": tr.get("gamesBack"),
                "runs_scored": tr.get("runsScored"), "runs_allowed": tr.get("runsAllowed"),
                "run_diff": tr.get("runDifferential"),
                "streak": (tr.get("streak") or {}).get("streakCode"),
                "l10": splits.get("lastTen"),
                "home": splits.get("home"), "away": splits.get("away"),
            }

    fixtures, results = [], []
    for payload, bucket in ((sch, fixtures), (recent, results)):
        for d in payload.get("dates", []):
            for g in d.get("games", []):
                home, away = g["teams"]["home"], g["teams"]["away"]
                st = (g.get("status") or {}).get("detailedState", "")
                row = {
                    "sport": "baseball",
                    "competition": "MLB",
                    "game_id": g.get("gamePk"),
                    "start_utc": g.get("gameDate"),
                    "official_date": g.get("officialDate"),
                    "status": st,
                    "home": teams.get(home["team"]["id"], {}).get("name", home["team"].get("name")),
                    "away": teams.get(away["team"]["id"], {}).get("name", away["team"].get("name")),
                    "home_id": home["team"]["id"], "away_id": away["team"]["id"],
                    "venue": (g.get("venue") or {}).get("name"),
                    "probable_home": (home.get("probablePitcher") or {}).get("fullName"),
                    "probable_away": (away.get("probablePitcher") or {}).get("fullName"),
                    "home_score": home.get("score"), "away_score": away.get("score"),
                    "source": "MLB.com StatsAPI",
                    "source_url": "https://www.mlb.com/gameday/" + str(g.get("gamePk")),
                    "feed_url": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&gamePk=" + str(g.get("gamePk")),
                }
                bucket.append(row)
    return {"fixtures": fixtures, "results": results, "table": table}


# ---------------------------------------------------------------- ice hockey
def ice_hockey() -> dict:
    sch = load_json("official_ice_hockey_0") or {}
    stand = load_json("official_ice_hockey_1") or {}
    table = {}
    for t in stand.get("standings", []):
        full = " ".join(x for x in [t.get("placeName", {}).get("default"), t.get("commonName", {}).get("default")] if x)
        table[t.get("teamAbbrev", {}).get("default") or full] = {
            "name": full,
            "abbrev": t.get("teamAbbrev", {}).get("default"),
            "points": t.get("points"), "games_played": t.get("gamesPlayed"),
            "wins": t.get("wins"), "losses": t.get("losses"), "ot_losses": t.get("otLosses"),
            "goal_for": t.get("goalFor"), "goal_against": t.get("goalAgainst"),
            "goal_diff": t.get("goalDifferential"), "point_pct": t.get("pointPctg"),
            "l10_wins": t.get("l10Wins"), "l10_losses": t.get("l10Losses"),
            "l10_ot_losses": t.get("l10OtLosses"), "l10_points": t.get("l10Points"),
            "home": {"w": t.get("homeWins"), "l": t.get("homeLosses"), "otl": t.get("homeOtLosses")},
            "road": {"w": t.get("roadWins"), "l": t.get("roadLosses"), "otl": t.get("roadOtLosses")},
            "streak": (t.get("streakCode") or ""),
            "conference": t.get("conferenceName"), "division": t.get("divisionName"),
        }
    fixtures, results = [], []
    for week in sch.get("gameWeek", []):
        for g in week.get("games", []):
            home, away = g.get("homeTeam", {}), g.get("awayTeam", {})
            def nm(t):
                return " ".join(x for x in [t.get("placeName", {}).get("default"), t.get("commonName", {}).get("default")] if x)
            row = {
                "sport": "ice-hockey", "competition": "NHL",
                "game_id": g.get("id"), "start_utc": g.get("startTimeUTC"),
                "status": g.get("gameState"),
                "home": nm(home), "away": nm(away),
                "home_abbrev": home.get("abbrev"), "away_abbrev": away.get("abbrev"),
                "venue": (g.get("venue") or {}).get("default"),
                "home_score": home.get("score"), "away_score": away.get("score"),
                "source": "NHL.com schedule API",
                "source_url": "https://www.nhl.com/gamecenter/" + str(g.get("id")),
                "feed_url": "https://api-web.nhle.com/v1/schedule/now",
            }
            (results if str(g.get("gameState")) in ("OFF", "FINAL") else fixtures).append(row)
    return {"fixtures": fixtures, "results": results, "table": table}


# --------------------------------------------------------------- motor racing
def motor_racing() -> dict:
    races = (load_json("official_motor_racing_0") or {}).get("MRData", {}).get("RaceTable", {}).get("Races", [])
    drv = (load_json("official_motor_racing_1") or {}).get("MRData", {}).get("StandingsTable", {}).get("StandingsLists", [])
    con = (load_json("official_motor_racing_2") or {}).get("MRData", {}).get("StandingsTable", {}).get("StandingsLists", [])
    last = (load_json("official_motor_racing_3") or {}).get("MRData", {}).get("RaceTable", {}).get("Races", [])
    fixtures = [{
        "sport": "motor-racing", "competition": "FIA Formula 1 World Championship",
        "round": r.get("round"), "name": r.get("raceName"),
        "circuit": (r.get("Circuit") or {}).get("circuitName"),
        "locality": (r.get("Circuit") or {}).get("Location", {}).get("locality"),
        "country": (r.get("Circuit") or {}).get("Location", {}).get("country"),
        "start_utc": (r.get("date") or "") + "T" + (r.get("time") or "00:00:00Z"),
        "source": "Ergast-compatible F1 feed (jolpi.ca)",
        "source_url": "https://api.jolpi.ca/ergast/f1/current/races.json",
        "official_url": "https://www.formula1.com/en/racing/2026",
    } for r in races]
    drivers = [{
        "position": s.get("position"), "points": s.get("points"), "wins": s.get("wins"),
        "driver": s.get("Driver", {}).get("familyName"), "given": s.get("Driver", {}).get("givenName"),
        "code": s.get("Driver", {}).get("code"), "nationality": s.get("Driver", {}).get("nationality"),
        "constructor": (s.get("Constructors") or [{}])[0].get("name"),
    } for sl in drv for s in sl.get("DriverStandings", [])]
    constructors = [{
        "position": s.get("position"), "points": s.get("points"), "wins": s.get("wins"),
        "constructor": s.get("Constructor", {}).get("name"),
    } for sl in con for s in sl.get("ConstructorStandings", [])]
    results = []
    for r in last:
        results.append({
            "sport": "motor-racing", "name": r.get("raceName"), "round": r.get("round"),
            "date": r.get("date"), "circuit": (r.get("Circuit") or {}).get("circuitName"),
            "winner": ((r.get("Results") or [{}])[0]).get("Driver", {}).get("familyName"),
            "source_url": "https://api.jolpi.ca/ergast/f1/current/last/results.json",
        })
    return {"fixtures": fixtures, "results": results, "drivers": drivers, "constructors": constructors}


# ------------------------------------------------------------ WTA singles ranks
def tennis_rankings() -> dict:
    t = read("official_tennis_1")
    if not t:
        return {}
    rows = re.findall(r'data-player-name="([^"]+)".*?player-row__rank[^>]*>\s*(\d+)\s*</span>', t, re.S)
    best: dict[str, int] = {}
    for name, rank in rows:
        n = name.strip()
        r = int(rank)
        if n and (n not in best or r < best[n]):
            best[n] = r
    return {"source": "WTA Tour official singles rankings", "url": "https://www.wtatennis.com/rankings/singles",
            "players": best}


# ----------------------------------------------------------------- json-ld aid
def jsonld_events(sport: str, capture: str, url: str) -> list[dict]:
    t = read(capture)
    out = []
    for block in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', t, re.S):
        try:
            data = json.loads(block)
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            item = stack.pop()
            if isinstance(item, list):
                stack.extend(item)
                continue
            if not isinstance(item, dict):
                continue
            if item.get("@graph"):
                stack.extend(item["@graph"])
            if item.get("@type") in ("SportsEvent", "Event"):
                out.append({
                    "sport": sport, "name": item.get("name"), "start": item.get("startDate"),
                    "end": item.get("endDate"), "location": str(item.get("location")),
                    "source": capture, "source_url": url,
                })
    return out


def main() -> int:
    facts = {
        "built_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": source_register(),
        "sports": {},
    }
    facts["sports"]["baseball"] = baseball()
    facts["sports"]["ice-hockey"] = ice_hockey()
    facts["sports"]["motor-racing"] = motor_racing()
    facts["sports"]["tennis"] = {"rankings": tennis_rankings()}

    ld = []
    for sport, items in SOURCES.items():
        for name, label, url in items:
            ld.extend(jsonld_events(sport, name, url))
    facts["jsonld_events"] = ld

    (OUT / "official_facts.json").write_text(json.dumps(facts, indent=1), encoding="utf-8")
    for k, v in facts["sports"].items():
        print(k, {kk: len(vv) if isinstance(vv, (list, dict)) else vv for kk, vv in v.items()})
    print("jsonld events", len(ld))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
