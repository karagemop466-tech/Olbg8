#!/usr/bin/env python3
"""Probe candidate official / primary data sources for every covered sport.

Runs on GitHub Actions (open egress). Records HTTP status, content type, payload
size and a short snippet so adapters can be written against what actually works.
Nothing is inferred: a source that fails is simply recorded as unavailable.
"""
import json
import os
import time

import requests

OUT = "data/sources"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept": "application/json, text/html;q=0.9,*/*;q=0.8",
                  "Accept-Language": "en-GB,en;q=0.9"})

SOURCES = {
    "tennis": [
        "https://www.atptour.com/en/rankings/singles",
        "https://www.wtatennis.com/rankings/singles",
        "https://www.itftennis.com/en/rankings/",
    ],
    "cricket": [
        "https://hs-consumer-api.espncricinfo.com/v1/pages/matches/current?lang=en",
        "https://www.icc-cricket.com/rankings/mens/team-rankings/odi",
        "https://www.espncricinfo.com/series",
    ],
    "basketball": [
        "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
        "https://stats.nba.com/stats/leaguestandingsv3?LeagueID=00&Season=2025-26&SeasonType=Regular%20Season",
        "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
    ],
    "ice_hockey": [
        "https://api-web.nhle.com/v1/schedule/now",
        "https://api-web.nhle.com/v1/standings/now",
        "https://api-web.nhle.com/v1/club-schedule-season/TOR/now",
    ],
    "baseball": [
        "https://statsapi.mlb.com/api/v1/schedule?sportId=1",
        "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026",
        "https://statsapi.mlb.com/api/v1/teams?sportId=1",
    ],
    "rugby_league": [
        "https://www.nrl.com/draw/data?competition=111&season=2026&round=1",
        "https://www.rugby-league.com/",
        "https://www.superleague.co.uk/fixtures",
        "https://site.api.espn.com/apis/site/v2/sports/rugby-league/scoreboard",
    ],
    "rugby_union": [
        "https://www.premiershiprugby.com/fixtures/",
        "https://www.unitedrugby.com/",
        "https://www.sixnationsrugby.com/",
        "https://site.api.espn.com/apis/site/v2/sports/rugby/scoreboard",
    ],
    "handball": [
        "https://www.ihf.info/competitions",
        "https://ehfcl.eurohandball.com/en/matches/",
        "https://www.eurohandball.com/",
    ],
    "volleyball": [
        "https://en.volleyballworld.com/volleyball/competitions/",
        "https://www.fivb.com/",
        "https://site.api.espn.com/apis/site/v2/sports/volleyball/scoreboard",
    ],
    "golf": [
        "https://www.owgr.com/ranking",
        "https://www.pgatour.com/",
        "https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard",
        "https://www.europeantour.com/dpworld-tour/schedule/",
    ],
    "darts": [
        "https://www.pdc.tv/",
        "https://www.pdc.tv/tournaments",
        "https://www.dartconnect.com/",
    ],
    "snooker": [
        "http://api.snooker.org/?t=5&s=2026",
        "https://api.snooker.org/?t=5&s=2026",
        "https://wst.tv/",
        "https://www.snooker.org/",
    ],
    "motor_racing": [
        "https://api.jolpi.ca/ergast/f1/2026/races.json",
        "https://www.formula1.com/en/results",
        "https://www.motogp.com/",
    ],
    "gaelic": [
        "https://www.gaa.ie/fixtures-results/",
        "https://www.gaa.ie/hurling/",
        "https://site.api.espn.com/apis/site/v2/sports/gaelic-games/scoreboard",
    ],
    "greyhounds": [
        "https://www.gbgb.org.uk/results",
        "https://www.gbgb.org.uk/",
        "https://www.britishgreyhoundracing.co.uk/",
    ],
}


def probe(url, sport):
    rec = {"url": url, "sport": sport}
    try:
        r = S.get(url, timeout=25)
        rec["status"] = r.status_code
        rec["ctype"] = r.headers.get("content-type", "")[:80]
        rec["bytes"] = len(r.content)
        body = r.text[:4000] if "json" not in rec["ctype"] else r.text[:1500]
        rec["snippet"] = " ".join(body.split())[:700]
        if r.status_code == 200:
            os.makedirs(f"{OUT}/samples", exist_ok=True)
            safe = "".join(c if c.isalnum() else "_" for c in url)[:120]
            with open(f"{OUT}/samples/{sport}_{safe}.txt", "w") as fh:
                fh.write(f"URL: {url}\nCTYPE: {rec['ctype']}\n\n")
                fh.write(r.text[:20000])
    except Exception as exc:  # noqa: BLE001
        rec["error"] = str(exc)[:160]
    return rec


def main():
    os.makedirs(OUT, exist_ok=True)
    results = []
    for sport, urls in SOURCES.items():
        for u in urls:
            results.append(probe(u, sport))
            time.sleep(1)
    with open(f"{OUT}/_probe.json", "w") as fh:
        json.dump(results, fh, indent=1)
    for r in results:
        print(f"{r['sport']:13s} {str(r.get('status', r.get('error')))[:30]:32s} "
              f"{r.get('ctype','')[:28]:30s} {r['url']}")


if __name__ == "__main__":
    main()
