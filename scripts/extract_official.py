#!/usr/bin/env python3
"""Pull verified, citable facts out of the official feeds captured by the crawler.

Sources (all fetched verbatim into data/raw/official|probe by the workflow):
  * NHL  : api-web.nhle.com/v1/standings/now   (official NHL API, nhl.com)
  * MLB  : statsapi.mlb.com/api/v1/standings    (official MLB Stats API, mlb.com)
  * F1   : api.jolpi.ca Ergast mirror of official F1 classification
Nothing here is estimated; fields the feed does not publish stay None.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OFF = ROOT / "data" / "raw" / "official"
PROBE = ROOT / "data" / "raw" / "probe"


def nhl():
    p = OFF / "nhl_standings.json"
    if not p.exists():
        return {}
    d = json.loads(p.read_text())
    out = {}
    for t in d.get("standings", []):
        ab = t.get("teamAbbrev", {}).get("default")
        out[ab] = {
            "team": t.get("teamCommonName", {}).get("default"),
            "place": t.get("teamName", {}).get("default"),
            "games_played": t.get("gamesPlayed"),
            "wins": t.get("wins"),
            "losses": t.get("losses"),
            "ot_losses": t.get("otLosses"),
            "points": t.get("points"),
            "point_pct": t.get("pointPctg"),
            "goals_for": t.get("goalFor"),
            "goals_against": t.get("goalAgainst"),
            "goal_diff": t.get("goalDifferential"),
            "l10": f"{t.get('l10Wins')}-{t.get('l10Losses')}-{t.get('l10OtLosses')}",
            "streak": f"{t.get('streakCode','')}{t.get('streakCount','')}",
            "source": "https://api-web.nhle.com/v1/standings/now",
            "source_page": "https://www.nhl.com/standings",
        }
    return out


def mlb():
    p = OFF / "mlb_standings.json"
    if not p.exists():
        return {}
    d = json.loads(p.read_text())
    out = {}
    for group in d.get("records", []):
        for t in group.get("teamRecords", []):
            name = t["team"]["name"]
            last10 = next((s for s in t.get("records", {}).get("splitRecords", [])
                           if s.get("type") == "lastTen"), None)
            out[name] = {
                "wins": t.get("wins"),
                "losses": t.get("losses"),
                "pct": t.get("winningPercentage"),
                "games_back": t.get("gamesBack"),
                "streak": (t.get("streak") or {}).get("streakCode"),
                "last10": f"{last10['wins']}-{last10['losses']}" if last10 else None,
                "source": "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026&standingsTypes=regularSeason",
                "source_page": "https://www.mlb.com/standings",
            }
    return out


def f1():
    p = PROBE / "jolpi_standings.json"
    if not p.exists():
        return []
    d = json.loads(p.read_text())
    rows = d["MRData"]["StandingsTable"]["StandingsLists"][0]["DriverStandings"]
    out = []
    for r in rows:
        out.append({
            "position": int(r["position"]),
            "driver": f"{r['Driver']['givenName']} {r['Driver']['familyName']}",
            "constructor": r["Constructors"][-1]["name"] if r.get("Constructors") else None,
            "points": float(r["points"]),
            "wins": int(r["wins"]),
            "source": "https://api.jolpi.ca/ergast/f1/2026/driverstandings/",
            "source_page": "https://www.formula1.com/en/results/2026/drivers",
        })
    return out


def main():
    facts = {
        "captured_utc": json.loads((OFF / "nhl_standings.json").read_text())["standingsDateTimeUtc"]
        if (OFF / "nhl_standings.json").exists() else None,
        "nhl": nhl(),
        "mlb": mlb(),
        "f1": f1(),
    }
    (ROOT / "data" / "official_facts.json").write_text(json.dumps(facts, indent=1) + "\n")
    print("nhl teams", len(facts["nhl"]), "mlb teams", len(facts["mlb"]), "f1 drivers", len(facts["f1"]))


if __name__ == "__main__":
    main()
