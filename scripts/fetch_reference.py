#!/usr/bin/env python3
"""Collect verified reference data (records, rankings, standings, fixtures) for the
15 covered sports from official / primary sources.

Two kinds of output:
  * structured adapters  (official JSON APIs)      -> data/reference/<sport>.json
  * page snapshots       (official HTML pages)     -> data/reference/pages/<name>.json
    A snapshot stores tables (as row arrays), headings and any embedded
    __NEXT_DATA__ payload, so extraction can be written against real content
    instead of guessed selectors. Nothing is inferred at fetch time.
"""
import json
import os
import re
import time
import traceback
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

OUT = "data/reference"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9",
                  "Accept": "application/json, text/html;q=0.9,*/*;q=0.8"})

SEASON = os.environ.get("SEASON", "2026")


def get(url, **kw):
    return S.get(url, timeout=30, **kw)


def save(name, obj):
    os.makedirs(f"{OUT}", exist_ok=True)
    with open(f"{OUT}/{name}.json", "w") as fh:
        json.dump(obj, fh, indent=1)


# ---------------------------------------------------------------- structured
def nhl():
    out = {"source": "https://api-web.nhle.com/v1", "fetched_utc": now(), "teams": []}
    st = get("https://api-web.nhle.com/v1/standings/now").json()
    for row in st.get("standings", []):
        out["teams"].append({
            "team": row.get("teamName", {}).get("default"),
            "abbrev": row.get("teamAbbrev", {}).get("default"),
            "conference": row.get("conferenceName"),
            "division": row.get("divisionName"),
            "games_played": row.get("gamesPlayed"),
            "wins": row.get("wins"), "losses": row.get("losses"),
            "ot_losses": row.get("otLosses"), "points": row.get("points"),
            "points_pct": row.get("pointPctg"),
            "goals_for": row.get("goalFor"), "goals_against": row.get("goalAgainst"),
            "goal_diff": row.get("goalDifferential"),
            "streak": f"{row.get('streakCode','')}{row.get('streakCount','')}",
            "l10_wins": row.get("l10Wins"), "l10_losses": row.get("l10Losses"),
            "l10_ot": row.get("l10OtLosses"),
            "home_wins": row.get("homeWins"), "home_losses": row.get("homeLosses"),
            "road_wins": row.get("roadWins"), "road_losses": row.get("roadLosses"),
            "source_url": "https://api-web.nhle.com/v1/standings/now",
        })
    try:
        sch = get("https://api-web.nhle.com/v1/schedule/now").json()
        games = []
        for week in sch.get("gameWeek", []):
            for g in week.get("games", []):
                games.append({
                    "id": g.get("id"), "date": week.get("date"),
                    "start_utc": g.get("startTimeUTC"),
                    "away": g.get("awayTeam", {}).get("abbrev"),
                    "home": g.get("homeTeam", {}).get("abbrev"),
                    "venue": g.get("venue", {}).get("default"),
                    "state": g.get("gameState"),
                })
        out["upcoming_games"] = games
    except Exception as exc:  # noqa: BLE001
        out["schedule_error"] = str(exc)[:150]
    save("ice_hockey", out)


def mlb():
    out = {"source": "https://statsapi.mlb.com/api/v1", "fetched_utc": now(), "teams": []}
    st = get(f"https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season={SEASON}"
             "&standingsTypes=regularSeason").json()
    for rec in st.get("records", []):
        for tr in rec.get("teamRecords", []):
            splits = {s.get("type"): s for s in tr.get("records", {}).get("splitRecords", [])}
            out["teams"].append({
                "team": tr.get("team", {}).get("name"),
                "id": tr.get("team", {}).get("id"),
                "wins": tr.get("wins"), "losses": tr.get("losses"),
                "pct": tr.get("winningPercentage"),
                "gb": tr.get("gamesBack"),
                "runs_scored": tr.get("runsScored"),
                "runs_allowed": tr.get("runsAllowed"),
                "run_diff": tr.get("runDifferential"),
                "streak": tr.get("streak", {}).get("streakCode"),
                "last10": (splits.get("lastTen") or {}).get("wins"),
                "home": (splits.get("home") or {}).get("wins"),
                "away": (splits.get("away") or {}).get("wins"),
                "division": rec.get("division", {}).get("name"),
                "source_url": ("https://statsapi.mlb.com/api/v1/standings"
                               f"?leagueId=103,104&season={SEASON}"),
            })
    try:
        sch = get(f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate="
                  f"{datetime.now(timezone.utc).date()}&endDate="
                  f"{datetime.now(timezone.utc).date().replace(month=12)}&hydrate=probablePitcher"
                  ).json() if False else get(
            "https://statsapi.mlb.com/api/v1/schedule?sportId=1&hydrate=probablePitcher,team").json()
        games = []
        for d in sch.get("dates", [])[:5]:
            for g in d.get("games", []):
                pp = lambda side: (g.get(side, {}).get("probablePitcher") or {}).get("fullName")
                games.append({
                    "date": d.get("date"), "gamePk": g.get("gamePk"),
                    "away": g.get("teams", {}).get("away", {}).get("team", {}).get("name"),
                    "home": g.get("teams", {}).get("home", {}).get("team", {}).get("name"),
                    "away_pitcher": pp("away"), "home_pitcher": pp("home"),
                    "status": g.get("status", {}).get("detailedState"),
                })
        out["upcoming_games"] = games
    except Exception as exc:  # noqa: BLE001
        out["schedule_error"] = str(exc)[:200]
    try:
        ts = get(f"https://statsapi.mlb.com/api/v1/teams/stats?season={SEASON}"
                 "&group=hitting&stats=season&sportIds=1").json()
        out["team_hitting"] = [
            {"team": s.get("team", {}).get("name"), "runs": s.get("stat", {}).get("runs"),
             "ops": s.get("stat", {}).get("ops"), "avg": s.get("stat", {}).get("avg"),
             "homeRuns": s.get("stat", {}).get("homeRuns")}
            for s in ts.get("stats", [{}])[0].get("splits", [])] if ts.get("stats") else []
    except Exception as exc:  # noqa: BLE001
        out["hitting_error"] = str(exc)[:150]
    save("baseball", out)


def nba():
    """NBA: cdn.nba.com and stats.nba.com block datacenter traffic, so records come
    from ESPN's public scoreboard/standings feed (primary broadcaster data)."""
    out = {"source": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba",
           "fetched_utc": now(), "teams": []}
    try:
        st = get("https://site.api.espn.com/apis/v2/sports/basketball/nba/standings"
                 "?season=2027").json()
        for child in st.get("children", []):
            for entry in child.get("standings", {}).get("entries", []):
                stats = {s.get("name"): s.get("displayValue") for s in entry.get("stats", [])}
                team = entry.get("team", {})
                out["teams"].append({
                    "team": team.get("displayName"), "abbrev": team.get("abbreviation"),
                    "wins": stats.get("wins"), "losses": stats.get("losses"),
                    "win_pct": stats.get("winPercent"),
                    "points_for": stats.get("avgPointsFor"),
                    "points_against": stats.get("avgPointsAgainst"),
                    "diff": stats.get("differential"),
                    "streak": stats.get("streak"),
                    "group": child.get("name"),
                    "source_url": ("https://site.api.espn.com/apis/v2/sports/"
                                   "basketball/nba/standings?season=2027"),
                })
    except Exception as exc:  # noqa: BLE001
        out["standings_error"] = str(exc)[:200]
    try:
        sb = get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/"
                 "scoreboard").json()
        out["games"] = [{
            "espn_id": e.get("id"), "date": e.get("date"),
            "name": e.get("name"),
            "status": e.get("status", {}).get("type", {}).get("description"),
            "home_record": [c.get("records", [{}])[0].get("summary")
                            for c in e.get("competitions", [{}])[0].get("competitors", [])
                            if c.get("homeAway") == "home"][:1],
            "awayself": None,
        } for e in sb.get("events", [])]
    except Exception as exc:  # noqa: BLE001
        out["scoreboard_error"] = str(exc)[:150]
    save("basketball", out)


def f1():
    out = {"source": "https://api.jolpi.ca/ergast/f1 (Ergast-compatible mirror)",
           "fetched_utc": now()}
    try:
        races = get(f"https://api.jolpi.ca/ergast/f1/{SEASON}/races.json").json()
        out["races"] = [{"round": r.get("round"), "name": r.get("raceName"),
                         "date": r.get("date"), "time": r.get("time"),
                         "circuit": r.get("Circuit", {}).get("circuitName"),
                         "locality": r.get("Circuit", {}).get("Location", {}).get("locality"),
                         "country": r.get("Circuit", {}).get("Location", {}).get("country"),
                         "url": r.get("url")}
                        for r in races.get("MRData", {}).get("RaceTable", {}).get("Races", [])]
    except Exception as exc:  # noqa: BLE001
        out["races_error"] = str(exc)[:150]
    for kind, name in [("driverStandings", "drivers"), ("constructorStandings", "constructors")]:
        try:
            d = get(f"https://api.jolpi.ca/ergast/f1/{SEASON}/{kind}.json").json()
            lst = d.get("MRData", {}).get("StandingsTable", {}).get("StandingsLists", [{}])[0]
            out[name] = lst.get(kind, [])
        except Exception as exc:  # noqa: BLE001
            out[f"{name}_error"] = str(exc)[:150]
    save("motor_racing", out)


# ---------------------------------------------------------------- snapshots
def snapshot(name, url, sport, max_tables=40, max_rows=60):
    rec = {"name": name, "url": url, "sport": sport}
    try:
        r = get(url)
        rec["status"] = r.status_code
        rec["bytes"] = len(r.text)
        if r.status_code != 200:
            return rec
        soup = BeautifulSoup(r.text, "html.parser")
        tables = []
        for t in soup.find_all("table")[:max_tables]:
            rows = []
            for tr in t.find_all("tr")[:max_rows]:
                cells = [re.sub(r"\s+", " ", c.get_text(" ", strip=True))
                         for c in tr.find_all(["th", "td"])]
                if any(cells):
                    rows.append(cells)
            if rows:
                caption = t.get("class") or []
                tables.append({"class": caption[:3], "rows": rows})
        rec["tables"] = tables
        rec["headings"] = [re.sub(r"\s+", " ", h.get_text(" ", strip=True))[:120]
                           for h in soup.find_all(["h1", "h2", "h3"])][:25]
        nd = soup.find("script", id="__NEXT_DATA__")
        if nd and nd.string:
            rec["next_data_bytes"] = len(nd.string)
            rec["next_data_head"] = nd.string[:3000]
        # generic list items that may carry fixtures
        items = []
        for li in soup.find_all("li")[:400]:
            txt = re.sub(r"\s+", " ", li.get_text(" ", strip=True))
            if 12 < len(txt) < 220:
                items.append(txt)
        rec["items"] = items[:200]
        rec["text_head"] = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))[:2500]
    except Exception as exc:  # noqa: BLE001
        rec["error"] = str(exc)[:200]
    return rec


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


PAGES = [
    ("tennis_atp_rankings", "https://www.atptour.com/en/rankings/singles", "tennis"),
    ("tennis_wta_rankings", "https://www.wtatennis.com/rankings/singles", "tennis"),
    ("cricket_icc_odi_rankings",
     "https://www.icc-cricket.com/rankings/mens/team-rankings/odi", "cricket"),
    ("cricket_icc_t20_rankings",
     "https://www.icc-cricket.com/rankings/mens/team-rankings/t20i", "cricket"),
    ("golf_owgr", "https://www.owgr.com/ranking", "golf"),
    ("gaelic_fixtures", "https://www.gaa.ie/fixtures-results/", "gaelic"),
    ("greyhounds_gbgb", "https://www.gbgb.org.uk/results", "greyhounds"),
    ("darts_pdc", "https://www.pdc.tv/tournaments", "darts"),
    ("snooker_wst", "https://wst.tv/", "snooker"),
    ("snooker_org", "https://www.snooker.org/", "snooker"),
    ("rugby_union_premiership", "https://www.premiershiprugby.com/fixtures/", "rugby_union"),
    ("rugby_union_urc", "https://www.unitedrugby.com/", "rugby_union"),
    ("rugby_league_rfl", "https://www.rugby-league.com/", "rugby_league"),
    ("handball_ihf", "https://www.ihf.info/competitions", "handball"),
    ("volleyball_world", "https://en.volleyballworld.com/volleyball/competitions/",
     "volleyball"),
    ("motor_formula1_results", "https://www.formula1.com/en/results", "motor_racing"),
]


def main():
    os.makedirs(f"{OUT}/pages", exist_ok=True)
    log = {"fetched_utc": now(), "structured": [], "pages": []}
    for fn in (nhl, mlb, nba, f1):
        try:
            fn()
            log["structured"].append({"adapter": fn.__name__, "ok": True})
        except Exception as exc:  # noqa: BLE001
            log["structured"].append({"adapter": fn.__name__, "ok": False,
                                      "error": str(exc)[:200],
                                      "trace": traceback.format_exc()[-500:]})
        time.sleep(1)
    for name, url, sport in PAGES:
        rec = snapshot(name, url, sport)
        save(f"pages/{name}", rec)
        log["pages"].append({"name": name, "status": rec.get("status"),
                             "tables": len(rec.get("tables", [])),
                             "items": len(rec.get("items", [])),
                             "error": rec.get("error", "")})
        print(name, log["pages"][-1], flush=True)
        time.sleep(1.5)
    save("_index", log)
    print(json.dumps(log["structured"], indent=1))


if __name__ == "__main__":
    main()
