#!/usr/bin/env python3
"""Probe official competition pages and discover ESPN league ids.

Writes trimmed page bodies to out/probe3/ so parsers can be written against the
real markup, plus out/probe3.json with a per-URL reachability record.
"""
from __future__ import annotations

import gzip
import io
import json
import re
import urllib.error
import urllib.request
import zlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
DEST = OUT / "probe3"
DEST.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")
HEAD = {"User-Agent": UA, "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9", "Accept-Encoding": "gzip, deflate"}

OFFICIAL = [
    ("icc_fixtures", "https://www.icc-cricket.com/fixtures-results"),
    ("ecb", "https://www.ecb.co.uk/"),
    ("nrl_draw", "https://www.nrl.com/draw/"),
    ("nrl_ladder", "https://www.nrl.com/ladder/"),
    ("superleague", "https://www.superleague.co.uk/matches"),
    ("rugby_league_com", "https://www.rugby-league.com/matches"),
    ("epcr", "https://www.epcrugby.com/"),
    ("unitedrugby", "https://www.unitedrugby.com/"),
    ("top14", "https://top14.lnr.fr/"),
    ("prod2", "https://prod2.lnr.fr/"),
    ("premiership", "https://www.premiershiprugby.com/"),
    ("cev", "https://www.cev.eu/"),
    ("cev_comp", "https://www.cev.eu/club/"),
    ("volleyballworld", "https://en.volleyballworld.com/volleyball/competitions/"),
    ("legavolley", "https://www.legavolley.it/"),
    ("ehf", "https://www.eurohandball.com/en/"),
    ("ehfcl", "https://ehfcl.eurohandball.com/en/"),
    ("hbl", "https://www.handball-bundesliga.de/"),
    ("pdc", "https://www.pdc.tv/"),
    ("pdc_tv", "https://www.pdc.tv/tournaments"),
    ("wst", "https://www.wst.tv/"),
    ("wst_matches", "https://www.wst.tv/matches"),
    ("gbgb_racecard", "https://www.gbgb.org.uk/race-card/"),
    ("gbgb_results", "https://www.gbgb.org.uk/results"),
    ("gaa_fixtures", "https://www.gaa.ie/fixtures-results/"),
    ("pga", "https://www.pgatour.com/"),
    ("lpga", "https://www.lpga.com/"),
    ("f1", "https://www.formula1.com/en/racing/2026"),
    ("motogp", "https://www.motogp.com/en/calendar"),
    ("atp", "https://www.atptour.com/en/scores/current"),
    ("wta_scores", "https://www.wtatennis.com/scores"),
    ("nba_games", "https://www.nba.com/games"),
    ("nba_cdn2", "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"),
    ("euroleague", "https://www.euroleaguebasketball.net/euroleague/games/"),
    ("acb", "https://www.acb.com/calendario"),
]

CORE = "https://sports.core.api.espn.com/v2/sports"
ESPN_LEAGUE_SPORTS = ["rugby", "cricket", "volleyball", "handball", "rugby-league", "basketball"]


def fetch(url: str, timeout: int = 25) -> tuple[dict, str]:
    rec = {"url": url, "status": 0, "bytes": 0, "ok": False, "error": ""}
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
            rec.update(status=resp.status, bytes=len(raw), ok=True,
                       ctype=resp.headers.get_content_type())
            return rec, body
    except urllib.error.HTTPError as exc:
        rec.update(status=exc.code, error=f"HTTP {exc.code}")
        try:
            return rec, exc.read().decode("utf-8", "replace")
        except Exception:
            return rec, ""
    except Exception as exc:  # noqa: BLE001
        rec["error"] = f"{type(exc).__name__}: {exc}"[:160]
        return rec, ""


def main() -> int:
    out = {"started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "official": [], "espn": []}

    for tag, url in OFFICIAL:
        rec, body = fetch(url)
        rec["tag"] = tag
        title = (re.search(r"<title>(.*?)</title>", body, re.S) or [None, ""])[1]
        rec["title"] = re.sub(r"\s+", " ", title)[:100]
        # a crude signal for "does this page carry fixture rows"
        rec["date_hits"] = len(re.findall(r"\b\d{1,2}[:.]\d{2}\b", body))
        rec["vs_hits"] = len(re.findall(r"\bv(?:s)?\.?\s", body, re.I))
        out["official"].append(rec)
        (DEST / f"{tag}.html").write_text(body[:60000], encoding="utf-8")
        print(f"{rec['status']:>4} {rec['bytes']:>8} {tag:<16} d={rec['date_hits']:<5} "
              f"vs={rec['vs_hits']:<5} {rec['title'][:60]}", flush=True)

    for sport in ESPN_LEAGUE_SPORTS:
        rec, body = fetch(f"{CORE}/{sport}/leagues?limit=200")
        refs = []
        try:
            data = json.loads(body)
            for item in data.get("items", []):
                refs.append(item.get("$ref", ""))
        except Exception:
            rec["error"] = rec.get("error") or "unparsable league list"
        rec["sport"] = sport
        leagues = []
        for ref in refs[:40]:
            lrec, lb = fetch(ref.replace("http://", "https://"))
            try:
                ld = json.loads(lb)
            except Exception:
                continue
            leagues.append({"id": ld.get("id"), "name": ld.get("name"),
                            "slug": ld.get("slug"), "abbr": ld.get("abbreviation")})
        rec["leagues"] = leagues
        out["espn"].append(rec)
        print(f"{rec['status']:>4} {sport:<14} leagues={len(leagues)} "
              f"{[l['slug'] for l in leagues][:12]}", flush=True)

    out["finished_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (OUT / "probe3.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
