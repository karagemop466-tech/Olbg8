#!/usr/bin/env python3
"""OLBG + official-source collector.

Runs on a GitHub Actions runner (full internet access). The development sandbox
that edits this repository can only reach allowlisted hosts, so every live
capture happens here and is committed back to the session branch.

Modes
  probe    - fetch a small sample set, record HTTP status and body samples
  harvest  - fetch all 15 OLBG sport feeds and official source pages, then
             store raw bodies plus a normalised index for the local pipeline
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
import zlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
OUT = ROOT / "out"
RAW.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "close",
}

CTX = ssl.create_default_context()


def fetch(url: str, timeout: int = 30, tries: int = 3) -> dict:
    last = {"url": url, "status": 0, "ok": False, "error": "", "body": "", "fetched_utc": ""}
    for attempt in range(1, tries + 1):
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
                raw = resp.read()
                enc = (resp.headers.get("Content-Encoding") or "").lower()
                if "gzip" in enc:
                    raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
                elif "deflate" in enc:
                    try:
                        raw = zlib.decompress(raw)
                    except zlib.error:
                        raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                charset = resp.headers.get_content_charset() or "utf-8"
                body = raw.decode(charset, "replace")
                last = {
                    "url": url,
                    "status": resp.status,
                    "ok": 200 <= resp.status < 300,
                    "error": "",
                    "body": body,
                    "fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "bytes": len(raw),
                }
                return last
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", "replace")
            except Exception:
                pass
            last = {
                "url": url,
                "status": exc.code,
                "ok": False,
                "error": f"HTTP {exc.code}",
                "body": body,
                "fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        except Exception as exc:  # noqa: BLE001 - network errors are recorded verbatim
            last = {
                "url": url,
                "status": 0,
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "body": "",
                "fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        if attempt < tries:
            time.sleep(2 * attempt)
    return last


def slug(url: str) -> str:
    s = re.sub(r"^https?://", "", url)
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return s[:150]


def save(tag: str, res: dict) -> dict:
    body = res.pop("body", "")
    p = RAW / f"{tag}.txt"
    p.write_text(body, encoding="utf-8")
    res["raw_file"] = str(p.relative_to(ROOT.parent))
    res["raw_chars"] = len(body)
    return res



PROBE2 = [
    # OLBG event pages - do they expose multiple markets and prices?
    ("olbg_ev_tennis", "https://www.olbg.com/betting-tips/Tennis/All_Tennis/All_Events/Novak_Djokovic_vs_Ugo_Humbert/3?event_id=902233"),
    ("olbg_ev_golf", "https://www.olbg.com/betting-tips/Golf/All_Golf/All_Events/Maybank_Championship/5?event_id=101913"),
    # Tennis official
    ("atp_rankings", "https://www.atptour.com/en/rankings/singles"),
    ("wta_scores", "https://www.wtatennis.com/scores"),
    ("itf", "https://www.itftennis.com/en/tournament-calendar/"),
    ("tennisexplorer", "https://www.tennisexplorer.com/matches/?type=atp-single&year=2026&month=10&day=27"),
    # Cricket
    ("icc_fixtures", "https://www.icc-cricket.com/fixtures-results"),
    ("icc_home", "https://www.icc-cricket.com/"),
    ("cricbuzz", "https://www.cricbuzz.com/cricket-match/live-scores"),
    # Darts
    ("pdc_home", "https://www.pdc.tv/"),
    ("pdc_tournaments", "https://www.pdc.tv/tournaments"),
    # Snooker
    ("wst_home", "https://www.wst.tv/"),
    ("wst_matches", "https://www.wst.tv/matches"),
    # Golf
    ("pgatour_sched", "https://www.pgatour.com/schedule"),
    ("lpga", "https://www.lpga.com/tournaments"),
    ("dpwt", "https://www.europeantour.com/dpworld-tour/schedule/"),
    # Volleyball
    ("cev", "https://www.cev.eu/competitions/"),
    ("volleyballworld", "https://en.volleyballworld.com/volleyball/competitions/"),
    # Handball
    ("ehf", "https://ehfcl.eurohandball.com/en/matches/"),
    ("ehf2", "https://www.eurohandball.com/en/matches/"),
    # Rugby union
    ("epcr", "https://www.epcrugby.com/fixtures"),
    ("unitedrugby", "https://www.unitedrugby.com/fixtures"),
    ("lnr", "https://prod2.lnr.fr/calendrier-et-resultats"),
    ("top14", "https://top14.lnr.fr/calendrier-et-resultats"),
    # Rugby league
    ("nrl_ladder", "https://www.nrl.com/ladder/data?competition=111&season=2026"),
    ("superleague", "https://www.superleague.co.uk/fixtures"),
    # Gaelic
    ("gaa", "https://www.gaa.ie/fixtures-results/"),
    # Greyhounds
    ("gbgb", "https://www.gbgb.org.uk/race-card/"),
    ("gbgb_results", "https://www.gbgb.org.uk/results"),
    # Motor racing
    ("f1_official", "https://www.formula1.com/en/racing/2026"),
    ("f1_standings", "https://api.jolpi.ca/ergast/f1/current/driverStandings.json"),
    ("motogp", "https://www.motogp.com/en/calendar"),
    ("nascar", "https://www.nascar.com/schedule/"),
    # Basketball
    ("nba_cdn_hdr", "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"),
    ("euroleague", "https://www.euroleaguebasketball.net/euroleague/games/"),
    ("nba_stats", "https://stats.nba.com/stats/scoreboardv3?GameDate=2026-10-27&LeagueID=00"),
    # Ice hockey
    ("nhl_clubs", "https://api-web.nhle.com/v1/standings/now"),
    ("shl", "https://www.shl.se/schedule"),
]

# ---------------------------------------------------------------- target sets
SPORTS = json.loads((ROOT / "sports.json").read_text())["sports"]

OFFICIAL_TARGETS = {
    "baseball": [
        "https://statsapi.mlb.com/api/v1/schedule?sportId=1&hydrate=probablePitcher,linescore,team,venue&startDate={today}&endDate={plus7}",
        "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season={season}&standingsTypes=regularSeason&hydrate=team",
    ],
    "ice-hockey": [
        "https://api-web.nhle.com/v1/schedule/now",
        "https://api-web.nhle.com/v1/standings/now",
    ],
    "basketball": [
        "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
        "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json",
    ],
    "cricket": [
        "https://www.icc-cricket.com/tournaments/calendar",
    ],
    "motor-racing": [
        "https://api.jolpi.ca/ergast/f1/current/races.json",
        "https://api.jolpi.ca/ergast/f1/current/driverStandings.json",
        "https://api.jolpi.ca/ergast/f1/current/constructorStandings.json",
    ],
    "rugby-league": [
        "https://www.nrl.com/draw/data?competition=111&season={season}&round={round}",
        "https://www.nrl.com/ladder/data?competition=111&season={season}",
    ],
    "rugby-union": [
        "https://www.epcrugby.com/fixtures",
        "https://www.unitedrugby.com/fixtures",
    ],
    "golf": [
        "https://api.sportsdata.io/golf/v2/json/tournaments",
        "https://www.pgatour.com/schedule",
    ],
    "tennis": [
        "https://www.atptour.com/en/scores/current",
        "https://api.sofascore.com/api/v1/sport/tennis/scheduled-events/2026-10-27",
    ],
    "darts": ["https://www.pdc.tv/tournaments"],
    "snooker": ["https://www.wst.tv/calendar"],
    "volleyball": ["https://www.cev.eu/competitions/"],
    "handball": ["https://ehfcl.eurohandball.com/en/matches/"],
    "greyhounds": ["https://www.gbgb.org.uk/race-card/"],
    "gaelic-sports": ["https://www.gaa.ie/fixtures-results/"],
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="harvest")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    plus7 = (now.replace(hour=0, minute=0, second=0, microsecond=0)).fromtimestamp(
        now.timestamp() + 7 * 86400, tz=timezone.utc
    ).strftime("%Y-%m-%d")
    fmt = {"today": today, "minus7": (now.timestamp() and today), "plus7": plus7,
           "season": str(now.year), "round": "27"}

    report = {
        "mode": args.mode,
        "startedUtc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "results": [],
    }

    targets = []
    for sp in SPORTS:
        targets.append(("olbg_" + sp["key"], sp["hub"]))
    if args.mode == "probe2":
        targets = PROBE2
    elif args.mode == "probe":
        targets = targets[:3] + [
            ("olbg_hub", "https://www.olbg.com/betting-tips"),
            ("mlb_sched", OFFICIAL_TARGETS["baseball"][0]),
            ("nhl_sched", OFFICIAL_TARGETS["ice-hockey"][0]),
            ("nba_today", OFFICIAL_TARGETS["basketball"][0]),
            ("f1_races", OFFICIAL_TARGETS["motor-racing"][0]),
            ("nrl_draw", OFFICIAL_TARGETS["rugby-league"][0]),
            ("atp", OFFICIAL_TARGETS["tennis"][0]),
            ("sofascore_tennis", OFFICIAL_TARGETS["tennis"][1]),
        ]
    else:
        for key, urls in OFFICIAL_TARGETS.items():
            for i, u in enumerate(urls):
                targets.append((f"official_{key}_{i}", u))

    for tag, url in targets:
        u = url.format(**fmt)
        res = fetch(u)
        res = save(slug(tag), res)
        res["tag"] = tag
        report["results"].append(res)
        print(f"{res['status']:>4} {res['raw_chars']:>8} {tag} {u}", flush=True)

    report["finishedUtc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (OUT / f"{args.mode}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    ok = sum(1 for r in report["results"] if r["ok"])
    print(f"done: {ok}/{len(report['results'])} ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
