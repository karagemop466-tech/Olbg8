#!/usr/bin/env python3
"""Official-source collector.

Every sport we cover needs a primary feed for fixtures, results, form and
availability. This module probes a registry of league / federation endpoints,
stores what actually answers, and normalises the ones with a stable schema into
`data/official/`.

The probe output (`data/official/_probe.json`) is what the site quotes when a
source is unreachable: the exact URL, HTTP status and byte count. Nothing is
inferred from a failed request.
"""

from __future__ import annotations

import argparse
import gzip
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "official"

UA = "OLBG8-research/1.0 (+https://github.com/karagemop466-tech/Olbg8)"
NOW = datetime.now(timezone.utc)


def day(offset: int) -> str:
    return (NOW + timedelta(days=offset)).strftime("%Y-%m-%d")


def probe_registry() -> list[dict[str, str]]:
    """Sources, grouped by the sport they support."""
    entries: list[dict[str, str]] = []

    def add(sport: str, name: str, url: str, kind: str = "json") -> None:
        entries.append({"sport": sport, "name": name, "url": url, "kind": kind})

    # Baseball - MLB Stats API (official, no key)
    add("Baseball", "mlb-schedule", f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate={day(-7)}&endDate={day(8)}&hydrate=team,linescore,probablePitcher,venue", )
    add("Baseball", "mlb-standings", f"https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season={NOW.year}&standingsTypes=regularSeason&hydrate=team")
    add("Baseball", "mlb-teams", "https://statsapi.mlb.com/api/v1/teams?sportId=1")

    # Ice hockey - NHL API (official, no key)
    add("Ice Hockey", "nhl-standings", "https://api-web.nhle.com/v1/standings/now")
    for offset in (-3, 0, 1, 2, 3, 4, 5, 6):
        add("Ice Hockey", f"nhl-schedule-{day(offset)}", f"https://api-web.nhle.com/v1/schedule/{day(offset)}")

    # Basketball - NBA CDN (official)
    add("Basketball", "nba-scoreboard", "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json")
    add("Basketball", "nba-schedule", "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json")

    # Motor racing - Jolpica F1 (Ergast successor) + official calendar
    add("Motor Racing", "f1-races", f"https://api.jolpi.ca/ergast/f1/{NOW.year}/races.json?limit=100")
    add("Motor Racing", "f1-driver-standings", f"https://api.jolpi.ca/ergast/f1/{NOW.year}/driverStandings.json?limit=100")
    add("Motor Racing", "f1-constructor-standings", f"https://api.jolpi.ca/ergast/f1/{NOW.year}/constructorStandings.json?limit=100")
    add("Motor Racing", "f1-results", f"https://api.jolpi.ca/ergast/f1/{NOW.year}/results.json?limit=200")

    # Golf - ESPN golf scoreboard (PGA + LPGA) and official schedule pages
    add("Golf", "espn-pga-scoreboard", "https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard")
    add("Golf", "espn-lpga-scoreboard", "https://site.api.espn.com/apis/site/v2/sports/golf/lpga/scoreboard")
    add("Golf", "espn-pga-leaderboard", "https://site.api.espn.com/apis/site/v2/sports/golf/pga/leaderboard")

    # Tennis - ESPN ATP/WTA scoreboards
    add("Tennis", "espn-atp-scoreboard", "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard")
    add("Tennis", "espn-wta-scoreboard", "https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard")
    add("Tennis", "espn-atp-rankings", "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/rankings")

    # Rugby union - ESPN leagues
    for league in ("289", "270", "244", "272", "164205"):
        add("Rugby Union", f"espn-rugby-{league}", f"https://site.api.espn.com/apis/site/v2/sports/rugby/{league}/scoreboard")

    # Rugby league - ESPN + NRL
    for league in ("3", "111"):
        add("Rugby League", f"espn-rugby-league-{league}", f"https://site.api.espn.com/apis/site/v2/sports/rugby-league/{league}/scoreboard")

    # Cricket - ESPNcricinfo consumer API + ESPN
    add("Cricket", "cricinfo-current", "https://hs-consumer-api.espncricinfo.com/v1/pages/matches/current?lang=en&start=0&size=50")
    add("Cricket", "cricinfo-news", "https://hs-consumer-api.espncricinfo.com/v1/pages/news?lang=en&size=20")
    add("Cricket", "espn-cricket-scoreboard", "https://site.api.espn.com/apis/site/v2/sports/cricket/scoreboard")
    add("Cricket", "icc-fixtures", "https://www.icc-cricket.com/fixtures-results", "html")

    # Snooker - snooker.org public API (fixtures, rankings)
    add("Snooker", "snooker-matches", f"https://api.snooker.org/?t=5&s={NOW.year}")
    add("Snooker", "snooker-ranking", "https://api.snooker.org/?rt=MoneyRankings&s=2026")
    add("Snooker", "snooker-events", "https://api.snooker.org/?t=2&s=2026")

    # Darts - PDC / dartconnect style feeds
    add("Darts", "pdc-tournaments", "https://www.pdc.tv/tournaments", "html")
    add("Darts", "espn-darts", "https://site.api.espn.com/apis/site/v2/sports/darts/pdc/scoreboard")

    # Volleyball / handball / gaelic / greyhounds - official pages
    add("Volleyball", "cev-match-centres", "https://www.cev.eu/match-centres/", "html")
    add("Handball", "ehf-matches", "https://ehfcl.eurohandball.com/men/2026-27/matches/", "html")
    add("Gaelic Football", "gaa-fixtures", "https://www.gaa.ie/fixtures-results", "html")
    add("Greyhounds", "gbgb-racing", "https://www.gbgb.org.uk/racing/", "html")

    # Generic cross-sport ratings that publish licence-free data
    add("Tennis", "espn-atp-athletes", "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/athletes")
    return entries


def fetch(url: str, tries: int = 2) -> tuple[int, bytes, str]:
    last = ""
    for attempt in range(tries):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": UA,
                    "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
                    "Accept-Encoding": "gzip",
                },
            )
            with urllib.request.urlopen(request, timeout=40) as response:
                body = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return response.status, body, response.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}"
            if exc.code == 429:
                time.sleep(4)
        except Exception as exc:  # pragma: no cover - network
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(1 + attempt)
    return 0, b"", last


def summarise(body: bytes) -> dict[str, Any]:
    """Shape summary so a parser can be written without the raw payload."""
    text = body.decode("utf-8", "replace")
    stripped = text.lstrip()
    if stripped[:1] in "{[":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return {"format": "json-broken", "excerpt": stripped[:300]}
        if isinstance(data, dict):
            return {
                "format": "json",
                "top_keys": list(data)[:25],
                "counts": {k: len(v) for k, v in data.items() if isinstance(v, (list, dict))},
                "excerpt": json.dumps(data)[:600],
            }
        return {"format": "json-list", "length": len(data), "excerpt": json.dumps(data[:2])[:600]}
    return {"format": "html", "excerpt": text[:400]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    registry = probe_registry()
    if args.limit:
        registry = registry[: args.limit]
    results: dict[str, Any] = {"probed_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "entries": []}
    for entry in registry:
        status, body, content_type = fetch(entry["url"])
        record = {
            "sport": entry["sport"],
            "name": entry["name"],
            "url": entry["url"],
            "status": status,
            "bytes": len(body),
            "content_type": content_type,
        }
        if status == 200 and body:
            record.update(summarise(body))
            # keep the raw official payload for deterministic local parsing
            safe = entry["name"].replace("/", "-")
            suffix = "json" if record.get("format", "").startswith("json") else "txt"
            (OUT / f"{safe}.{suffix}").write_bytes(body)
        results["entries"].append(record)
        time.sleep(0.5)
    (OUT / "_probe.json").write_text(json.dumps(results, indent=1))
    ok = sum(1 for e in results["entries"] if e["status"] == 200)
    print(f"probed {len(results['entries'])} official endpoints, {ok} answered 200")
    for entry in results["entries"]:
        print(f"{entry['status']:>4} {entry['bytes']:>8}B {entry['sport']:<16} {entry['name']}")


if __name__ == "__main__":
    main()
