#!/usr/bin/env python3
"""Parse captured OLBG sport feed pages into a normalised listing index.

OLBG renders its tips feed server side, so every row carries the event name,
event URL, ISO start time, the selection, the market label, the displayed price
in three formats, the tipster win-record and the consensus bar. Nothing here is
inferred: each field is read from a named attribute or element in the markup,
and a row missing a field is written with that field blank.
"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
OUT = ROOT / "out"

ROW_SPLIT = re.compile(r'<li class="min-h-\[')
SPORTS = json.loads((ROOT / "sports.json").read_text())["sports"]


def clean(s: str | None) -> str:
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).replace("\u00a0", " ").strip()


def one(pattern: str, block: str, group: int = 1, flags: int = 0) -> str:
    m = re.search(pattern, block, flags)
    return clean(m.group(group)) if m else ""


def parse_feed(text: str, sport: dict) -> list[dict]:
    rows = []
    for block in ROW_SPLIT.split(text)[1:]:
        url = one(r'itemprop="url" href="([^"]+)"', block)
        name = one(r'itemprop="name">(.*?)</h5>', block, flags=re.S)
        if not url or not name:
            continue
        start = one(r'itemprop="startDate" datetime="([^"]+)"', block)
        selection = one(r"<h4[^>]*>(.*?)</h4>", block, flags=re.S)
        market = one(r'<p class="truncate text-sm">(.*?)</p>', block, flags=re.S)
        dec = one(r'data-decimal="([^"]+)"', block)
        amer = one(r'data-american="([^"]+)"', block)
        frac = one(r'data-fractional="([^"]+)"', block)
        tiprec = one(r'<b class="text-xs truncate">(.*?)</b>', block, flags=re.S)
        conf = one(r"--confidence:\s*(\d+)%", block)
        stars = one(r'<div class="filled" style="width:\s*(\d+)%', block)
        competition = one(r'<p class="text-sm truncate">(.*?)</p>', block, flags=re.S)
        rows.append({
            "sport_key": sport["key"],
            "sport_label": sport["label"],
            "sport_id": sport["sport_id"],
            "event": name,
            "olbg_event_url": url,
            "start_utc": start,
            "selection": selection,
            "market": market,
            "competition": competition,
            "decimal": dec,
            "american": amer,
            "fractional": frac,
            "tip_record": tiprec,
            "consensus_pct": conf,
            "value_stars_pct": stars,
            "capture": "feed",
        })
    return rows


def main() -> int:
    all_rows = []
    status = []
    for sp in SPORTS:
        prefix = "olbg_" + sp["key"].replace("-", "_")
        files = [p for p in sorted(RAW.glob("olbg_*.txt")) if p.name.startswith(prefix)]
        if not files:
            status.append({"sport": sp["label"], "files": [], "rows": 0, "note": "no capture"})
            continue
        rows = []
        for p in files:
            rows.extend(parse_feed(p.read_text(encoding="utf-8", errors="replace"), sp))
        dedup = {}
        for r in rows:
            dedup[(r["olbg_event_url"], r["selection"], r["market"])] = r
        rows = list(dedup.values())
        status.append({"sport": sp["label"], "files": [f.name for f in files], "rows": len(rows)})
        all_rows.extend(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "olbg_feed.json").write_text(json.dumps({
        "captured_utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "status": status,
        "rows": all_rows,
    }, indent=1), encoding="utf-8")
    for s in status:
        print(f"{s['sport']:<16} {s['rows']:>4} rows  {s.get('note','')}")
    print(f"total {len(all_rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
