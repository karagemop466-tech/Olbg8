#!/usr/bin/env python3
"""Parse captured OLBG event pages into a full market board.

Each event page groups selections under market headings. The markup gives us:
  * market name   - <h4 class="rw slct ..."> under the market button
  * selection     - <div class="rw slct"><h4>
  * tip record    - <b>4 / 5 Win Tips</b> and the consensus bar percentage
  * price         - data-decimal / data-american / data-fractional attributes
  * event meta    - itemprop name / startDate / location
Every value is read from the page; nothing is estimated.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

import rawio

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
OUT = ROOT / "out"

MARKET_SPLIT = re.compile(r'<li class="!border-0 group/market">')
SEL_SPLIT = re.compile(r'<div id="\d+" class="block w-full text-left grd')


def clean(s: str | None) -> str:
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def one(pattern, block, group=1, flags=re.S):
    m = re.search(pattern, block, flags)
    return clean(m.group(group)) if m else ""


def parse_event(text: str) -> dict:
    h1 = one(r"<h1[^>]*>(.*?)</h1>", text)
    name = re.sub(r"\s+Tips$", "", h1) if h1 else one(r'itemprop="name"[^>]*>(.*?)</h5>', text)
    crumbs = []
    m = re.search(r'itemtype="https://schema.org/BreadcrumbList"(.*?)</ol>', text, re.S)
    if m:
        crumbs = [clean(x) for x in re.findall(r'<span itemprop="name">(.*?)</span>', m.group(1), re.S)]
    competition = ""
    for c in reversed(crumbs[2:-1] if len(crumbs) > 2 else []):
        if c and not c.lower().startswith("all ") and c != name:
            competition = c
            break
    start = one(r'itemprop="startDate" datetime="([^"]+)"', text)
    comp = competition or one(r'<p class="text-sm truncate">(.*?)</p>', text, flags=re.S)
    title = one(r"<title>(.*?)</title>", text)
    markets = []
    for mblock in MARKET_SPLIT.split(text)[1:]:
        mname = one(r'<h4 class="rw slct[^"]*"[^>]*>(.*?)</h4>', mblock)
        if not mname:
            continue
        sels = []
        for sblock in SEL_SPLIT.split(mblock)[1:]:
            sel = one(r"<h4[^>]*>(.*?)</h4>", sblock)
            dec = one(r'data-decimal="([^"]+)"', sblock)
            if not sel or not dec:
                continue
            sels.append({
                "selection": sel,
                "decimal": dec,
                "american": one(r'data-american="([^"]+)"', sblock),
                "fractional": one(r'data-fractional="([^"]+)"', sblock),
                "tip_record": one(r"<b[^>]*>([^<]*?Win Tips)</b>", sblock),
                "consensus": one(r"--confidence:\s*(\d+)%", sblock),
                "comments": one(r"([\d,]+)\s*comments", sblock),
            })
        if sels:
            markets.append({"market": mname, "selections": sels})
    return {"event": name, "title": title, "competition": comp, "breadcrumb": crumbs,
            "start_utc": start, "markets": markets}


def main() -> int:
    events = []
    status = []
    for p in rawio.glob("olbgev_"):
        parsed = parse_event(rawio.read_text(p))
        m = re.match(r"olbgev_(.+?)_(\d+)$", p.name.split(".txt")[0])
        if m:
            parsed["sport_key"] = m.group(1)
            parsed["event_id"] = m.group(2)
        parsed["raw_file"] = p.name
        total = sum(len(x["selections"]) for x in parsed["markets"])
        status.append({"file": p.name, "event": parsed["event"], "market_count": len(parsed["markets"]),
                       "selections": total})
        events.append(parsed)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "olbg_events.json").write_text(json.dumps({"events": events}, indent=1), encoding="utf-8")
    for s in status:
        print(f"{s['market_count']:>2} markets {s['selections']:>3} sels  {s['event'][:60]}")
    print(f"total {len(events)} events")
    return 0


if __name__ == "__main__":
    sys.exit(main())
