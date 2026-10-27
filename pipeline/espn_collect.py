#!/usr/bin/env python3
"""ESPN scoreboard + injury harvest.

Runs on the Actions runner. ESPN's public scoreboard endpoint is the one
structured, per-match feed that reaches the European volleyball, handball,
rugby and basketball competitions this desk prices, so it is harvested as a
*secondary* register: the payload records the publisher, and the site keeps
ESPN data visually separate from league-published data.

Output (committed, trimmed so the repository stays small):
  out/espn_raw.json       - one record per league with its events
  out/espn_injuries.json  - per-team injury entries for the big leagues
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import time
import urllib.error
import urllib.request
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")
HEAD = {"User-Agent": UA, "Accept": "application/json,text/plain;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate"}

SITE = "https://site.api.espn.com/apis/site/v2/sports"

# (desk sport key, espn sport path, espn league slug, label, link template)
LEAGUES = [
    ("basketball", "basketball/nba", "nba", "NBA"),
    ("basketball", "basketball/wnba", "wnba", "WNBA"),
    ("rugby-union", "rugby/270557", "270557", "United Rugby Championship"),
    ("rugby-union", "rugby/270559", "270559", "French Top 14"),
    ("rugby-union", "rugby/267979", "267979", "Gallagher Premiership"),
    ("rugby-union", "rugby/271937", "271937", "Investec Champions Cup"),
    ("rugby-league", "rugby-league/3", "3", "Rugby League"),
    ("tennis", "tennis/atp", "atp", "ATP"),
    ("tennis", "tennis/wta", "wta", "WTA"),
    ("golf", "golf/pga", "pga", "PGA Tour"),
    ("motor-racing", "racing/f1", "f1", "Formula 1"),
    ("baseball", "baseball/mlb", "mlb", "MLB"),
    ("ice-hockey", "hockey/nhl", "nhl", "NHL"),
]

INJURY_LEAGUES = [
    ("baseball", "baseball/mlb", "mlb"),
    ("ice-hockey", "hockey/nhl", "nhl"),
    ("basketball", "basketball/nba", "nba"),
]


def get(url: str, timeout: int = 30, tries: int = 2) -> str:
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=HEAD)
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
                return raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            if exc.code in (400, 404):
                return ""
        except Exception:
            pass
        time.sleep(1 + attempt)
    return ""


def team_of(comp: dict) -> dict:
    side = {}
    team = comp.get("team") or {}
    athlete = comp.get("athlete") or {}
    if team:
        side["name"] = team.get("displayName") or team.get("shortDisplayName") or team.get("name")
        side["short"] = team.get("shortDisplayName")
        side["abbr"] = team.get("abbreviation")
        side["id"] = str(team.get("id") or "")
        side["logo"] = (team.get("logos") or [{}])[0].get("href") if team.get("logos") else None
    elif athlete:
        side["name"] = athlete.get("displayName") or athlete.get("fullName")
        side["short"] = athlete.get("shortName")
        side["abbr"] = athlete.get("shortName")
        side["id"] = str(athlete.get("id") or "")
    else:
        return {}
    side["score"] = comp.get("score")
    side["winner"] = comp.get("winner")
    recs = []
    for r in comp.get("records") or []:
        recs.append({"summary": r.get("summary"), "type": r.get("type")})
    side["records"] = recs
    if comp.get("homeAway"):
        side["home_away"] = comp["homeAway"]
    return side


def trim_event(ev: dict, league_label: str) -> dict:
    comps = ev.get("competitions") or [{}]
    comp = comps[0]
    status = ((ev.get("status") or {}).get("type") or {})
    sides = [team_of(c) for c in comp.get("competitors") or []]
    sides = [s for s in sides if s]
    out = {
        "id": str(ev.get("id") or comp.get("id") or ""),
        "name": ev.get("name") or ev.get("shortName"),
        "short": ev.get("shortName"),
        "date": ev.get("date"),
        "league": league_label,
        "state": status.get("state"),
        "completed": bool(status.get("completed")),
        "detail": status.get("detail") or status.get("shortDetail"),
        "venue": ((comp.get("venue") or {}).get("fullName")),
        "note": ((comp.get("notes") or [{}])[0] or {}).get("headline"),
        "sides": sides,
        "link": ((ev.get("links") or [{}])[0] or {}).get("href"),
    }
    return out


def _shrink(obj) -> dict:
    """Keep a small structural sample so parsers can be written offline."""
    try:
        text = json.dumps(obj)[:6000]
        return json.loads(text if text.endswith("}") else text.rsplit(",", 1)[0] + "}")
    except Exception:
        return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--back", type=int, default=12)
    ap.add_argument("--forward", type=int, default=5)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    dates = [(now + timedelta(days=d)).strftime("%Y%m%d")
             for d in range(-args.back, args.forward + 1)]

    payload = {"fetched_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "leagues": {}}
    for sport_key, path, slug, label in LEAGUES:
        seen: dict[str, dict] = {}
        sample: dict = {}
        for d in dates:
            url = f"{SITE}/{path}/scoreboard?dates={d}&limit=200"
            body = get(url)
            if not body:
                continue
            try:
                data = json.loads(body)
            except Exception:
                continue
            for ev in data.get("events") or []:
                rec = trim_event(ev, label)
                if rec["id"] and rec["id"] not in seen:
                    seen[rec["id"]] = rec
                if sample.get("event") is None:
                    sample["event"] = ev
            time.sleep(0.15)
        payload["leagues"][f"{sport_key}|{slug}"] = {
            "sport": sport_key, "slug": slug, "label": label,
            "events": sorted(seen.values(), key=lambda e: e.get("date") or ""),
            "sample": json.loads(json.dumps(sample)[:0] or "{}") if False else _shrink(sample),
        }
        print(f"{label:<32} {len(seen):>4} events", flush=True)

    (OUT / "espn_raw.json").write_text(json.dumps(payload), encoding="utf-8")

    inj = {"fetched_utc": payload["fetched_utc"], "leagues": {}}
    for sport_key, path, slug in INJURY_LEAGUES:
        body = get(f"{SITE}/{path}/injuries")
        rows = []
        try:
            data = json.loads(body)
        except Exception:
            data = {}
        for item in (data.get("injuries") or data.get("items") or []):
            team = ((item.get("team") or {}).get("displayName")) or item.get("teamName")
            for ath in item.get("injuries") or item.get("athletes") or []:
                player = ((ath.get("athlete") or {}).get("displayName")) or ath.get("playerName")
                status = ((ath.get("status") or {}).get("name")) if isinstance(ath.get("status"), dict) else ath.get("status")
                detail = ath.get("longComment") or ath.get("shortComment") or ath.get("detail")
                rows.append({"team": team, "player": player, "status": status,
                             "detail": (detail or "")[:220],
                             "date": ath.get("date")})
        inj["leagues"][f"{sport_key}|{slug}"] = {"sport": sport_key, "slug": slug,
                                                 "count": len(rows), "rows": rows[:400],
                                                 "sample": _shrink({"item": (data.get("injuries") or data.get("items") or [None])[0]})}
        print(f"injuries {slug:<8} {len(rows)} rows", flush=True)
    (OUT / "espn_injuries.json").write_text(json.dumps(inj), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
