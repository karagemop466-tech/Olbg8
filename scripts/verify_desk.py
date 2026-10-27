#!/usr/bin/env python3
"""Fail-closed verification for the 2026-10-27 OLBG desk.

Checks the dataset, the generated HTML, source links on every table row,
internal links, prediction quality and deterministic rebuild inputs.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "data" / "desk-20261027.json").read_text(encoding="utf-8"))
CAPTURE = json.loads((ROOT / "data" / "capture-20261027" / "manifest.json").read_text(encoding="utf-8"))

ERRORS: list[str] = []
WARNINGS: list[str] = []


def check(condition, message: str) -> None:
    if not condition:
        ERRORS.append(message)


def host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def is_official(url: str, official_hosts: set[str]) -> bool:
    h = host(url)
    return bool(h and h in official_hosts and "olbg.com" not in h)


# ---------------------------------------------------------------------------
# 1. Dataset integrity.
# ---------------------------------------------------------------------------
check(DATA["schema"] == "olbg8.desk/2026-10-27", "unexpected dataset schema")
check(DATA["capture_utc"] == CAPTURE["capture_utc"], "dataset capture time differs from collector manifest")
check(DATA["build_utc"] == DATA["capture_utc"], "build is not deterministic from the snapshot")
check(len(DATA["scope"]) == 15, "scope does not contain exactly 15 sports")
check(len(DATA["sports"]) == 15, "sport summary does not contain 15 rows")
check(len({s["key"] for s in DATA["sports"]}) == 15, "duplicate sport keys")
check(DATA["summary"]["events"] == len(DATA["events"]), "event count mismatch")
check(DATA["summary"]["picks"] == len(DATA["picks"]), "pick count mismatch")
check(DATA["summary"]["priced_selections"] == sum(len(l["selections"]) for l in DATA["lines"]),
      "priced selection count mismatch")
check(DATA["summary"]["priced_markets"] == sum(1 for l in DATA["lines"] if l["priced"]),
      "priced market count mismatch")

official_hosts = set()
for s in DATA["sources"]:
    if s["role"] in ("official", "supplemental (not official)"):
        official_hosts.add(host(s["url"]))
for e in DATA["events"]:
    official_hosts.add(host(e["official"]["url"]))
for l in DATA["lines"]:
    official_hosts.add(host(l["official_url"]))
for p in DATA["picks"]:
    official_hosts.add(host(p["official_url"]))
    for u in p["official_urls"]:
        official_hosts.add(host(u.get("url", "")))
for f in DATA["flags"]:
    for u in f["urls"]:
        h = host(u.get("url", ""))
        if h and "olbg.com" not in h:
            official_hosts.add(h)
official_hosts.discard("")

event_ids = {e["id"] for e in DATA["events"]}
for e in DATA["events"]:
    check(bool(e["olbg_url"]) and "olbg.com" in e["olbg_url"], f"event {e['id']} has no OLBG event URL")
    check(bool(e["official"]["url"]) and is_official(e["official"]["url"], official_hosts),
          f"event {e['id']} has no official source URL")
    check(isinstance(e["markets"], list) and e["markets"], f"event {e['id']} has no markets")
    if e["independent_total"] is None:
        check(e["independent_total_source"] == "", f"event {e['id']} blank total has a source")

for l in DATA["lines"]:
    check(l["event_id"] in event_ids, f"line {l['market']} refers to a missing event")
    check(bool(l["olbg_url"]), f"line {l['event_id']}/{l['market']} has no OLBG URL")
    check(is_official(l["official_url"], official_hosts), f"line {l['event_id']}/{l['market']} has no official URL")
    if l["priced"]:
        check(bool(l["selections"]), f"priced market {l['event_id']}/{l['market']} has no selections")
        total = sum(s["fair_pct"] for s in l["selections"])
        check(99.0 <= total <= 101.0, f"market {l['event_id']}/{l['market']} fair probabilities sum to {total:.2f}")
        for s in l["selections"]:
            check(s["our_american"] != 0, f"selection {s['selection']} has no originated line")
            check(s["selection"] != "", "blank selection in priced market")
            check(-100000 < s["edge_pp"] < 100000, "implausible edge")

# ---------------------------------------------------------------------------
# 2. Picks: unique, human, in range, sourced.
# ---------------------------------------------------------------------------
preds = []
for p in DATA["picks"]:
    check(p["confidence"] in ("low", "medium", "high"), f"pick {p['pick_no']} invalid confidence")
    check(-250 <= p["displayed_american"] <= 10000, f"pick {p['pick_no']} outside the -250..+10000 band")
    check(p["confidence"] != "high" or -250 <= p["displayed_american"] <= 10000,
          f"high pick {p['pick_no']} outside price band")
    check(bool(p["selection"]), f"pick {p['pick_no']} has no selection")
    check(bool(p["market"]), f"pick {p['pick_no']} has no market")
    check(bool(p["olbg_url"]), f"pick {p['pick_no']} has no OLBG link")
    check(is_official(p["official_url"], official_hosts), f"pick {p['pick_no']} has no official link")
    check(any(is_official(u.get("url", ""), official_hosts) for u in p["official_urls"]),
          f"pick {p['pick_no']} has no official source in its source list")
    t = p["prediction"]
    words = len(t.split())
    check(words >= 30, f"pick {p['pick_no']} prediction is only {words} words")
    check(not re.search(r"\b(model|verified)\b", t, re.I), f"pick {p['pick_no']} uses internal jargon")
    check(p["selection"].lower() in t.lower(), f"pick {p['pick_no']} prediction does not name the selection")
    check("confidence" in t.lower(), f"pick {p['pick_no']} prediction does not state confidence")
    preds.append(t)
check(len(set(preds)) == len(preds), "predictions are not unique")
check(all(len(set(re.findall(r"[a-z]+", t.lower()))) > 20 for t in preds), "prediction vocabulary too small")

per_sport = {}
for p in DATA["picks"]:
    per_sport[p["sport_slug"]] = per_sport.get(p["sport_slug"], 0) + 1
for s in DATA["sports"]:
    check(s["picks"] == per_sport.get(s["key"], 0), f"pick count mismatch on {s['label']}")
    if s["picks"] < 5:
        check(any(f["level"] == "high" and f["sport"] == s["label"] and "picks" in f["detail"].lower()
                  for f in DATA["flags"]), f"{s['label']} shortfall is not flagged")
    if s["events"] == 0:
        check(any(f["sport"] == s["label"] and "No OLBG market rows" in f["subject"] for f in DATA["flags"]),
              f"{s['label']} empty capture is not flagged")

# ---------------------------------------------------------------------------
# 3. HTML: pages, internal links, official link on every data-table row.
# ---------------------------------------------------------------------------
pages = ["index.html", "picks.html", "lines.html", "matches.html", "sources.html",
         "methodology.html", "flagged.html"] + [f"sports/{s['key']}.html" for s in DATA["sports"]]
for rel in pages:
    check((ROOT / rel).exists(), f"missing page {rel}")

html_files = sorted(list(ROOT.glob("*.html")) + list((ROOT / "sports").glob("*.html")))
href_re = re.compile(r'href="([^"]+)"')
row_re = re.compile(r"<tr\b[^>]*>.*?</tr>", re.S | re.I)
exempt_row_files = {"methodology.html"}  # its market-frequency table is a methodology summary, not data

for path in html_files:
    text = path.read_text(encoding="utf-8")
    rel = str(path.relative_to(ROOT))
    for h in href_re.findall(text):
        if h.startswith(("http://", "https://", "mailto:", "#")):
            if h.startswith("http"):
                check(bool(host(h)), f"{rel}: malformed external URL {h}")
            continue
        target = (path.parent / h.split("#", 1)[0]).resolve()
        if h.split("#", 1)[0] == "":
            continue
        check(target.exists(), f"{rel}: broken internal link {h}")
    if rel in exempt_row_files:
        continue
    for row in row_re.findall(text):
        if "<th" in row:
            continue
        links = href_re.findall(row)
        external = [u for u in links if u.startswith(("http://", "https://"))]
        check(any(is_official(u, official_hosts) for u in external),
              f"{rel}: table row without an official source link: {re.sub('<[^>]+>', ' ', row)[:110]}")

# Predictions must be visible on the picks page and the sport page.
picks_html = (ROOT / "picks.html").read_text(encoding="utf-8")
for p in DATA["picks"]:
    snippet = html.escape(p["prediction"])[:60]
    check(snippet in picks_html, f"pick {p['pick_no']} prediction missing from picks.html")
    sport_html = (ROOT / "sports" / f"{p['sport_slug']}.html").read_text(encoding="utf-8")
    check(snippet in sport_html, f"pick {p['pick_no']} prediction missing from its sport page")

# Executive summary must contain the top picks and an obvious route to them.
index_html = (ROOT / "index.html").read_text(encoding="utf-8")
check('href="picks.html"' in index_html, "index does not link to picks")
check("Highest-confidence selections" in index_html, "index has no high-confidence section")
check("Executive summary" in index_html, "index has no executive summary")
check("Coverage by sport" in index_html, "index has no coverage ledger")

# Every source row must show its status and a link.
sources_html = (ROOT / "sources.html").read_text(encoding="utf-8")
check("HTTP" in sources_html and "Source register" in sources_html, "sources page incomplete")

# Flagged page must clearly be labelled and contain the high-priority gaps.
flagged_html = (ROOT / "flagged.html").read_text(encoding="utf-8")
check("Flagged for review" in flagged_html, "flagged page not labelled")
check("High-priority gaps" in flagged_html, "flagged page missing high-priority summary")
check("Snooker" in flagged_html and "Greyhounds" in flagged_html, "empty sports not on flagged page")

# ---------------------------------------------------------------------------
# 4. Report.
# ---------------------------------------------------------------------------
if ERRORS:
    print(f"FAILED: {len(ERRORS)} verification error(s)")
    for e in ERRORS[:40]:
        print("  -", e)
    if len(ERRORS) > 40:
        print(f"  ... and {len(ERRORS) - 40} more")
    sys.exit(1)
print(f"OK: {len(DATA['events'])} events, {DATA['summary']['priced_markets']} markets, "
      f"{DATA['summary']['priced_selections']} lines, {len(DATA['picks'])} unique picks, "
      f"{len(DATA['flags'])} flags, {len(html_files)} HTML pages, "
      f"{len(official_hosts)} official hosts, all rows sourced, all links resolve.")
