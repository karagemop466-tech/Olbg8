#!/usr/bin/env python3
"""Targeted ESPN surface probe: which league ids expose a usable scoreboard,
what today's payload looks like, and whether injury feeds exist."""
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
        "Accept-Language": "en-GB,en;q=0.9", "Accept-Encoding": "gzip, deflate"}
S = "https://site.api.espn.com/apis/site/v2/sports"
C = "https://sports.core.api.espn.com/v2/sports"
W = "20261020-20261103"

CANDIDATES = [
    ("rugby_all", f"{S}/rugby/scoreboard?dates={W}"),
    ("rugby_wc", f"{S}/rugby/270557/scoreboard?dates={W}"),
    ("rugby_urc", f"{S}/rugby/8331/scoreboard?dates={W}"),
    ("rugby_league_all", f"{S}/rugby-league/scoreboard?dates={W}"),
    ("rugby_league_nrl", f"{S}/rugby-league/3/scoreboard?dates={W}"),
    ("rugby_league_sl", f"{S}/rugby-league/1000/scoreboard?dates={W}"),
    ("cricket_all", f"{S}/cricket/scoreboard?dates={W}"),
    ("cricket_wc", f"{S}/cricket/8039/scoreboard?dates={W}"),
    ("basketball_euro", f"{S}/basketball/euroleague/scoreboard?dates={W}"),
    ("basketball_euro2", f"{S}/basketball/44/scoreboard?dates={W}"),
    ("volleyball_all", f"{S}/volleyball/scoreboard?dates={W}"),
    ("handball_all", f"{S}/handball/scoreboard?dates={W}"),
    ("mlb_board", f"{S}/baseball/mlb/scoreboard?dates={W}"),
    ("nhl_board", f"{S}/hockey/nhl/scoreboard?dates={W}"),
    ("nba_board", f"{S}/basketball/nba/scoreboard?dates={W}"),
    ("pga_board", f"{S}/golf/pga/scoreboard"),
    ("f1_board", f"{S}/racing/f1/scoreboard?dates=20261001-20261130"),
    ("atp_board", f"{S}/tennis/atp/scoreboard?dates={W}"),
    ("wta_board", f"{S}/tennis/wta/scoreboard?dates={W}"),
    ("inj_nhl_a", f"{S}/hockey/nhl/injuries"),
    ("inj_nhl_b", "https://site.web.api.espn.com/apis/site/v2/sports/hockey/nhl/injuries"),
    ("inj_mlb_a", f"{S}/baseball/mlb/injuries"),
    ("inj_mlb_b", f"{C}/baseball/leagues/mlb/injuries?limit=50"),
    ("inj_nba_b", "https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"),
    ("espn_league_list", "https://site.api.espn.com/apis/site/v2/leagues?sport=rugby&limit=100"),
]


def fetch(url: str, timeout: int = 25) -> dict:
    rec = {"url": url, "status": 0, "bytes": 0, "ok": False, "error": "", "summary": None}
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
            rec.update(status=resp.status, bytes=len(raw), ok=True, summary=summary_of(body))
            return rec
    except urllib.error.HTTPError as exc:
        rec.update(status=exc.code, error=f"HTTP {exc.code}")
    except Exception as exc:  # noqa: BLE001
        rec["error"] = f"{type(exc).__name__}: {exc}"[:160]
    return rec


def summary_of(body: str):
    try:
        data = json.loads(body)
    except Exception:
        m = re.search(r"__NEXT_DATA__[^>]*>(\{.*?\})</script>", body, re.S)
        if not m:
            return {"kind": "html", "chars": len(body), "title": (re.search(r"<title>(.*?)</title>", body, re.S) or [None, ""])[1][:90]}
        try:
            data = json.loads(m.group(1))
        except Exception:
            return {"kind": "html", "chars": len(body)}
    if not isinstance(data, dict):
        return {"kind": "json-list", "n": len(data)}
    leagues = data.get("leagues") or []
    events = data.get("events") or []
    out = {"kind": "json", "keys": sorted(data.keys())[:8], "n_events": len(events),
           "leagues": [(l.get("id"), l.get("name"), l.get("slug")) for l in leagues][:4]}
    sample = []
    for ev in events[:4]:
        comp = (ev.get("competitions") or [{}])[0]
        sides = []
        for c in comp.get("competitors", [])[:2]:
            team = c.get("team") or {}
            sides.append({"name": team.get("displayName") or team.get("shortDisplayName"),
                          "score": c.get("score"), "record": [r.get("summary") for r in (c.get("records") or [])][:1],
                          "winner": c.get("winner")})
        sample.append({"name": ev.get("name"), "date": ev.get("date"),
                       "status": ((ev.get("status") or {}).get("type") or {}).get("name"),
                       "sides": sides,
                       "has_odds": bool(comp.get("odds"))})
    out["sample"] = sample
    if "athletes" in data:
        out["n_athletes"] = len(data.get("athletes") or [])
    if "items" in data:
        out["n_items"] = len(data["items"])
    return out


def main() -> int:
    out = {"started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "results": []}
    for tag, url in CANDIDATES:
        rec = fetch(url)
        rec["tag"] = tag
        out["results"].append(rec)
        s = rec.get("summary") or {}
        print(f"{rec['status']:>4} {rec['bytes']:>8} {tag:<20} {s.get('n_events', s.get('kind'))} "
              f"{s.get('leagues', '')}", flush=True)
    out["finished_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    OUT.mkdir(exist_ok=True)
    (OUT / "probe2.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
