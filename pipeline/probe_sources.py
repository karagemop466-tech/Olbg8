#!/usr/bin/env python3
"""Reachability sweep for candidate official / primary result feeds.

Runs on the Actions runner (full internet). Writes out/probe.json with one
record per URL: status, byte count, content type and a short snippet, so the
local pipeline can decide which feeds are worth a parser.
"""
from __future__ import annotations

import gzip
import io
import json
import urllib.error
import urllib.request
import zlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
OUT.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")
HEAD = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Cache-Control": "no-cache",
}

ESPN = "https://site.api.espn.com/apis/site/v2/sports"
CORE = "https://sports.core.api.espn.com/v2/sports"

URLS = [
    # ESPN scoreboard surface (independent primary feed)
    ("espn_mlb", f"{ESPN}/baseball/mlb/scoreboard?dates=20261027&limit=50"),
    ("espn_nhl", f"{ESPN}/hockey/nhl/scoreboard?dates=20261027&limit=50"),
    ("espn_nba", f"{ESPN}/basketball/nba/scoreboard?dates=20261027&limit=50"),
    ("espn_wnba", f"{ESPN}/basketball/wnba/scoreboard?dates=20261027"),
    ("espn_cricket", f"{ESPN}/cricket/8039/scoreboard?dates=20261027"),
    ("espn_cricket_all", f"{CORE}/cricket/leagues?limit=100"),
    ("espn_rugby", f"{ESPN}/rugby/270557/scoreboard?dates=20261027"),
    ("espn_rugby_leagues", f"{CORE}/rugby/leagues?limit=100"),
    ("espn_golf", f"{ESPN}/golf/pga/scoreboard?dates=20261027"),
    ("espn_golf_lb", f"{ESPN}/golf/pga/leaderboard"),
    ("espn_f1", f"{ESPN}/racing/f1/scoreboard?dates=20261027"),
    ("espn_f1_racelog", f"{ESPN}/racing/f1/scoreboard?dates=20261101"),
    ("espn_tennis_atp", f"{ESPN}/tennis/atp/scoreboard"),
    ("espn_tennis_wta", f"{ESPN}/tennis/wta/scoreboard"),
    ("espn_volleyball", f"{ESPN}/volleyball/volleyball/scoreboard?dates=20261027"),
    ("espn_handball", f"{ESPN}/handball/.../scoreboard"),
    ("espn_leagues", "https://site.api.espn.com/apis/site/v2/sports"),
    ("espn_nhl_inj", f"{ESPN}/hockey/nhl/teams/BOS/injuries"),
    ("espn_mlb_inj", f"{ESPN}/baseball/mlb/teams/30/injuries"),
    ("espn_nba_inj", f"{ESPN}/basketball/nba/teams/BOS/injuries"),
    ("espn_nhl_news", f"{ESPN}/hockey/nhl/news?limit=20"),
    # Official leagues known good, extra depth
    ("mlb_probables", "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=2026-10-27&hydrate=probablePitcher,team,linescore"),
    ("mlb_rosters", "https://statsapi.mlb.com/api/v1/teams/139/roster?rosterType=active&hydrate=person"),
    ("mlb_stats_leaders", "https://statsapi.mlb.com/api/v1/stats/leaders?leaderCategories=homeRuns&season=2026&sportId=1"),
    ("nhl_schedule_week", "https://api-web.nhle.com/v1/schedule/2026-10-27"),
    ("nhl_standings", "https://api-web.nhle.com/v1/standings/2026-10-27"),
    ("nhl_club_stats", "https://api-web.nhle.com/v1/club-stats/BOS/now"),
    ("nba_odds", "https://cdn.nba.com/static/json/liveData/odds/odds_todaysGames.json"),
    ("nba_box", "https://cdn.nba.com/static/json/liveData/boxscore/boxscore_0022500001.json"),
    ("f1_races", "https://api.jolpi.ca/ergast/f1/current/races.json"),
    ("f1_drv", "https://api.jolpi.ca/ergast/f1/current/driverStandings.json"),
    ("wta_ranks", "https://www.wtatennis.com/rankings/singles"),
    ("wta_scores", "https://www.wtatennis.com/scores"),
    ("itf_cal", "https://www.itftennis.com/en/tournament-calendar/"),
    # Cricket official
    ("icc_fixtures", "https://www.icc-cricket.com/fixtures-results"),
    ("ecb_fixtures", "https://www.ecb.co.uk/matches"),
    ("cricketaustralia", "https://www.cricketaustralia.com.au/"),
    ("bcci", "https://www.bcci.tv/"),
    ("cricbuzz_live", "https://www.cricbuzz.com/cricket-match/live-scores"),
    # Rugby union / league official
    ("nrl_draw", "https://www.nrl.com/draw/data?competition=111&season=2026&round=27"),
    ("nrl_ladder", "https://www.nrl.com/ladder/data?competition=111&season=2026"),
    ("superleague", "https://www.superleague.co.uk/fixtures"),
    ("rugbyleague_com", "https://www.rugby-league.com/"),
    ("epcr", "https://www.epcrugby.com/fixtures"),
    ("unitedrugby", "https://www.unitedrugby.com/fixtures"),
    ("top14", "https://top14.lnr.fr/calendrier-et-resultats"),
    ("premiership", "https://www.premiershiprugby.com/fixtures"),
    # Volleyball / handball
    ("cev", "https://www.cev.eu/"),
    ("legavolley", "https://www.legavolley.it/"),
    ("volleyballworld", "https://en.volleyballworld.com/volleyball/competitions/"),
    ("ehfcl", "https://ehfcl.eurohandball.com/en/matches/"),
    ("hbl", "https://www.handball-bundesliga.de/spielplan/"),
    ("ehf_ec", "https://www.eurohandball.com/en/"),
    # Darts / snooker / greyhounds / gaelic
    ("pdc", "https://www.pdc.tv/"),
    ("pdc_om", "https://www.pdc.tv/order-of-merit"),
    ("wst", "https://www.wst.tv/"),
    ("wst_matches", "https://www.wst.tv/matches"),
    ("gbgb", "https://www.gbgb.org.uk/"),
    ("gbgb_results", "https://www.gbgb.org.uk/results"),
    ("gaa", "https://www.gaa.ie/fixtures-results/"),
    ("gaa_api", "https://www.gaa.ie/api/"),
    # Golf official
    ("pga_sched", "https://www.pgatour.com/schedule"),
    ("pga_leaderboard", "https://www.pgatour.com/leaderboard"),
    ("dpwt", "https://www.europeantour.com/dpworld-tour/schedule/"),
    ("lpga", "https://www.lpga.com/tournaments"),
    # Motor racing official
    ("f1_site", "https://www.formula1.com/en/racing/2026"),
    ("motogp", "https://www.motogp.com/en/calendar"),
    ("nascar", "https://www.nascar.com/schedule/"),
    # Basketball official
    ("euroleague", "https://www.euroleaguebasketball.net/euroleague/games/"),
    ("bbl_de", "https://www.basketball-bundesliga.de/spielplan/"),
    ("acb", "https://www.acb.com/calendario"),
    # Greyhound / misc
    ("sportinglife_grey", "https://www.sportinglife.com/greyhounds"),
    ("olbg_grey", "https://www.olbg.com/betting-tips/Greyhounds/28"),
]


def fetch(url: str, timeout: int = 25) -> dict:
    rec = {"url": url, "status": 0, "bytes": 0, "ctype": "", "ok": False, "error": "", "snippet": ""}
    req = urllib.request.Request(url, headers=HEAD)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            enc = (resp.headers.get("Content-Encoding") or "").lower()
            if "gzip" in enc:
                raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
            elif "deflate" in enc:
                try:
                    raw = zlib.decompress(raw)
                except zlib.error:
                    raw = zlib.decompress(raw, -zlib.MAX_WBITS)
            body = raw.decode(resp.headers.get_content_charset() or "utf-8", "replace")
            rec.update(status=resp.status, bytes=len(raw), ctype=resp.headers.get_content_type(),
                       ok=True, snippet=body[:300].replace("\n", " "))
    except urllib.error.HTTPError as exc:
        rec.update(status=exc.code, error=f"HTTP {exc.code}")
        try:
            rec["snippet"] = exc.read()[:200].decode("utf-8", "replace").replace("\n", " ")
        except Exception:
            pass
    except Exception as exc:  # noqa: BLE001
        rec["error"] = f"{type(exc).__name__}: {exc}"[:200]
    return rec


def main() -> int:
    out = {"started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "results": []}
    for tag, url in URLS:
        rec = fetch(url)
        rec["tag"] = tag
        out["results"].append(rec)
        print(f"{rec['status']:>4} {rec['bytes']:>8} {tag:<20} {url}", flush=True)
    out["finished_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (OUT / "probe.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    ok = sum(1 for r in out["results"] if r["ok"])
    print(f"reachable: {ok}/{len(out['results'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
