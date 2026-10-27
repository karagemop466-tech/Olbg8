#!/usr/bin/env python3
"""Structured-API discovery for the sports with no readable HTML feed."""
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
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")
HEAD = {"User-Agent": UA, "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate", "Accept-Language": "en-GB,en;q=0.9"}

URLS = [
    # Greyhounds - official board API
    ("gbgb_swagger", "https://api.gbgb.org.uk/api/swagger/v1/swagger.json"),
    ("gbgb_swagger2", "https://api.gbgb.org.uk/swagger/v1/swagger.json"),
    ("gbgb_root", "https://api.gbgb.org.uk/api/"),
    ("gbgb_meetings", "https://api.gbgb.org.uk/api/meetings"),
    ("gbgb_racecards", "https://api.gbgb.org.uk/api/racecards"),
    # WTA structured
    ("wta_api_root", "https://api.wtatennis.com/"),
    ("wta_scores_api", "https://api.wtatennis.com/scores/current"),
    ("wta_rank_api", "https://api.wtatennis.com/tennis/players/ranked?page=0&pageSize=50&metric=SINGLES"),
    # ATP alternatives
    ("atp_api", "https://api.atptour.com/players/rankings?rankType=singles"),
    ("atp_website_api", "https://www.atptour.com/-/ajax/rankings/singles"),
    # Snooker / darts
    ("wst_api", "https://api.wst.tv/"),
    ("wst_api2", "https://www.wst.tv/api/matches"),
    ("pdc_api", "https://www.pdc.tv/api/tournaments"),
    ("pdc_api2", "https://pdc.tv/wp-json/wp/v2/posts?per_page=5"),
    ("wst_wp", "https://wst.tv/wp-json/wp/v2/posts?per_page=5"),
    # Volleyball / handball
    ("cev_api", "https://www.cev.eu/api/"),
    ("cev_live", "https://www.cev.eu/api/matches"),
    ("ehf_api", "https://www.eurohandball.com/api/"),
    ("ehf_comp", "https://www.eurohandball.com/en/api/competitions/"),
    ("hbl_api", "https://www.handball-bundesliga.de/api/"),
    ("legavolley_api", "https://www.legavolley.it/api/"),
    # Cricket
    ("icc_api", "https://www.icc-cricket.com/api/"),
    ("icc_wp", "https://www.icc-cricket.com/wp-json/wp/v2/posts?per_page=3"),
    ("cricapi", "https://cricketdata.org/"),
    # Gaelic
    ("gaa_api2", "https://www.gaa.ie/api/fixtures"),
    # Rugby league
    ("nrl_api", "https://www.nrl.com/api/draw?competition=111&season=2026"),
    ("sl_api", "https://www.superleague.co.uk/api/fixtures"),
    # Motorsport
    ("motogp_api", "https://api.pulselive.motogp.com/motogp/v1/results/events?seasonUuid=&isFinished=true"),
    ("f1_api", "https://api.formula1.com/svc/v2/whereami"),
    # Euroleague / basketball
    ("el_api", "https://api.euroleaguebasketball.net/v1/competitions"),
    ("el_stats", "https://www.euroleaguebasketball.net/api/v1/games"),
    # Golf
    ("pga_api", "https://www.pgatour.com/api/schedule"),
    ("lpga_api", "https://www.lpga.com/api/tournaments"),
    # Odds/format sanity check on OLBG json surface
    ("olbg_api", "https://www.olbg.com/api/tips?sport=3"),
]


def fetch(url: str, timeout: int = 25) -> dict:
    rec = {"url": url, "status": 0, "bytes": 0, "ok": False, "error": "", "snippet": ""}
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
            body = raw.decode("utf-8", "replace")
            rec.update(status=resp.status, bytes=len(raw), ok=True,
                       ctype=resp.headers.get_content_type(),
                       snippet=re.sub(r"\s+", " ", body[:400]))
    except urllib.error.HTTPError as exc:
        rec.update(status=exc.code, error=f"HTTP {exc.code}")
    except Exception as exc:  # noqa: BLE001
        rec["error"] = f"{type(exc).__name__}: {exc}"[:120]
    return rec


def main() -> int:
    out = {"when": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "results": []}
    for tag, url in URLS:
        rec = fetch(url)
        rec["tag"] = tag
        out["results"].append(rec)
        print(f"{rec['status']:>4} {rec['bytes']:>8} {tag:<16} {rec['snippet'][:90]}", flush=True)
    OUT.mkdir(exist_ok=True)
    (OUT / "probe4.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
