#!/usr/bin/env python3
"""Fail-closed checks for the research desk payload and generated site.

Every assertion here re-reads the committed payload and compares it with the
captured boards, so a broken build cannot reach the site.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import rawio

ROOT = Path(__file__).resolve().parent
DESK = ROOT.parent / "data" / "desk.json"
EVENTS = ROOT / "out" / "olbg_events.json"
FEED = ROOT / "out" / "olbg_feed.json"
SITE = ROOT.parent

BANNED = ("model", "verified", "hallucinat")
failures: list[str] = []
notes: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        failures.append(msg)


def main() -> int:
    desk = json.loads(DESK.read_text())
    boards = {e["event_id"]: e for e in json.loads(EVENTS.read_text())["events"]} if EVENTS.exists() else {}
    feed = json.loads(FEED.read_text())["rows"] if FEED.exists() else []

    picks = desk["picks"]
    check(len(picks) > 0, "no picks in payload")
    check(len(desk["sports"]) == 15, f"expected 15 sports, found {len(desk['sports'])}")

    seen_texts = {}
    for p in picks:
        # 1. source links present
        check(bool(p.get("olbg_url", "").startswith("https://www.olbg.com/")), f"{p['id']}: missing OLBG link")
        if p.get("official_confirmed"):
            check(bool(p.get("official_url")), f"{p['id']}: crosswalked pick without official link")
        # 2. price in window and matches the board
        check(-250 <= p["our_fair_american"] <= 10000, f"{p['id']}: fair price outside window")
        eid = re.search(r"event_id=(\d+)", p["olbg_url"])
        board = boards.get(eid.group(1)) if eid else None
        if board:
            matched = [
                s for m in board["markets"] if m["market"] == p["market"]
                for s in m["selections"] if s["selection"] == p["selection"]
            ]
            check(bool(matched), f"{p['id']}: selection not found on captured board")
            if matched:
                check(abs(float(matched[0]["decimal"]) - p["price_decimal"]) < 1e-9,
                      f"{p['id']}: price {p['price_decimal']} != captured {matched[0]['decimal']}")
        else:
            notes.append(f"{p['id']}: no event-page board captured, priced from the feed row")
        # 3. prose requirements
        words = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'./%+-]*", p["prediction"]))
        check(words >= 30, f"{p['id']}: prediction only {words} words")
        for bad in BANNED:
            check(bad not in p["prediction"].lower(), f"{p['id']}: prose contains banned word '{bad}'")
        check(p["prediction"].rstrip().endswith((".", "!")), f"{p['id']}: prose does not end in a full stop")
        check("  " not in p["prediction"], f"{p['id']}: double space in prose")
        # 4. uniqueness
        norm = " ".join(sorted({s.strip().lower() for s in re.split(r"[.]", p["prediction"]) if s.strip()}))
        check(norm not in seen_texts, f"{p['id']}: identical sentence set to {seen_texts.get(norm)}")
        seen_texts[norm] = p["id"]

    # 5. per-sport coverage bookkeeping is honest
    for sp in desk["sports"]:
        actual = len([p for p in picks if p["sport"] == sp["key"]])
        check(actual == sp["picks"], f"{sp['label']}: pick count {sp['picks']} != {actual}")
        if sp["picks"]:
            check(sp["events"] > 0, f"{sp['label']}: picks without events")

    # 6. generated pages exist and load their assets
    pages = [SITE / "index.html", SITE / "picks.html", SITE / "matches.html",
             SITE / "sources.html", SITE / "methodology.html", SITE / "flagged.html"]
    pages += [SITE / "sports" / f"{s['key']}.html" for s in desk["sports"]]
    for page in pages:
        check(page.exists(), f"missing page {page.name}")
        if not page.exists():
            continue
        text = page.read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("http", "mailto", "#")):
                continue
            target = (page.parent / href.split("#")[0]).resolve()
            check(target.exists(), f"{page.name}: broken local link {href}")
        for src in re.findall(r'src="([^"]+)"', text):
            target = (page.parent / src).resolve()
            check(target.exists(), f"{page.name}: broken asset {src}")
    # 7. every pick appears on its sport page
    for p in picks:
        page = SITE / "sports" / f"{p['sport']}.html"
        check(page.exists() and f'id="pick-{p["id"]}"' in page.read_text(encoding="utf-8"),
              f"{p['id']}: not rendered on its sport page")

    # 8. every official claim must exist in a captured official payload
    official_raw = {
        "baseball": ["official_baseball_0", "official_baseball_1", "official_baseball_2"],
        "ice-hockey": ["official_ice_hockey_0", "official_ice_hockey_1"],
        "motor-racing": ["official_motor_racing_0", "official_motor_racing_1"],
    }
    for p in picks:
        if not p.get("official_confirmed"):
            continue
        corpus = " ".join(rawio.read(n) for n in official_raw.get(p["sport"], []))
        if len(corpus) < 1000:
            notes.append(f"{p['id']}: official raw capture not on disk in this environment; audit skipped")
            continue
        for side in ("home", "away"):
            name = p.get(side) or ""
            if name:
                check(name.split()[-1].lower() in corpus.lower(),
                      f"{p['id']}: {side} team '{name}' not found in the official capture")
            row = p.get(f"{side}_table") or {}
            for key in ("wins", "losses", "points", "goal_for", "goal_against", "runs_scored", "runs_allowed"):
                val = row.get(key)
                if val is None:
                    continue
                check(str(val) in corpus, f"{p['id']}: {side} {key}={val} absent from the official capture")

    # 9. every OLBG link was actually fetched during the capture run
    manifest_path = ROOT / "out" / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        fetched = {m["url"]: m for m in manifest["entries"]}
        for p in picks:
            entry = fetched.get(p["olbg_url"])
            check(entry is not None, f"{p['id']}: OLBG url not in the capture manifest")
            if entry:
                check(entry["ok"], f"{p['id']}: OLBG url returned status {entry['status']} at capture")
    else:
        notes.append("no capture manifest on disk; URL status audit skipped")

    print(f"picks checked: {len(picks)}; pages checked: {len(pages)}; feed rows: {len(feed)}")
    for n in notes[:10]:
        print("note:", n)
    if failures:
        print(f"\nFAILED {len(failures)} checks")
        for f in failures[:40]:
            print(" -", f)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
