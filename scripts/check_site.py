#!/usr/bin/env python3
"""Offline gate for the OLBG desk.

Fails (non-zero exit) if any published row breaks the desk rules:
  * a prediction shorter than 30 words, or containing a banned reader-facing word
  * a line outside -250 .. +10000 American
  * an implied percentage that does not match the published American price
  * a confidence label that does not match the implied percentage
  * a pick with no OLBG source or no independent official source
  * a pick whose event id is absent from the captured OLBG inventory
  * an inventory row without an OLBG event URL or a parseable UTC start time
  * a flag without a source link
  * any broken internal link or missing page (including missing sport pages)
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BANNED = ("model", "models", "modelled", "verified", "verification")
WINDOW = (-250, 10000)
MIN_WORDS = 30
errors: list[str] = []
checks = 0


def load(name):
    path = DATA / name
    if not path.exists():
        errors.append(f"missing data file: {name}")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def ok(condition, message):
    global checks
    checks += 1
    if not condition:
        errors.append(message)


def american_to_implied(a: float) -> float:
    return round((100 / (a + 100) if a > 0 else abs(a) / (abs(a) + 100)) * 100, 1)


def band(pct: float) -> str:
    return "high" if pct >= 65 else ("medium" if pct >= 55 else "low")


def main() -> int:
    sports = load("desk-sports.json").get("sports", [])
    inv = load("desk-inventory.json")
    picks = load("desk-picks.json").get("picks", [])
    flags = load("desk-flagged.json").get("items", [])
    pricing = load("desk-pricing.json")

    ok(len(sports) == 15, f"expected 15 sports, found {len(sports)}")
    keys = {s["key"] for s in sports}
    ok(len(keys) == 15, "sport keys are not unique")
    for s in sports:
        ok(bool(s.get("hub", "").startswith("https://www.olbg.com/")), f"{s['key']}: hub is not an OLBG URL")
        ok(isinstance(s.get("sport_id"), int), f"{s['key']}: missing OLBG sport id")
        ok((ROOT / "sports" / f"{s['key']}.html").exists(), f"{s['key']}: sport page not generated")

    inv_events = {}
    for key, doc in inv.get("sports", {}).items():
        ok(key in keys, f"inventory sport {key} is not in the sport register")
        for e in doc.get("events", []):
            inv_events.setdefault(key, set()).add(str(e["event_id"]))
            ok(bool(e.get("url", "").startswith("https://www.olbg.com/")), f"{key}/{e.get('event_id')}: event URL is not on OLBG")
            try:
                datetime.fromisoformat(str(e["start_utc"]).replace("Z", "+00:00"))
            except Exception:
                errors.append(f"{key}/{e.get('event_id')}: start_utc is not ISO-8601")
        ok("gap_note" in doc, f"{key}: inventory has no gap note")

    for p in picks:
        pid = p.get("id", "?")
        ok(p.get("sport") in keys, f"{pid}: sport not in register")
        ok(str(p.get("event_id")) in inv_events.get(p.get("sport"), set()), f"{pid}: event id not in the captured inventory")
        words = len(str(p.get("analysis", "")).split())
        ok(words >= MIN_WORDS, f"{pid}: prediction is {words} words, minimum is {MIN_WORDS}")
        text = " ".join([str(p.get("analysis", "")), str(p.get("pricing", ""))]).lower()
        hits = [w for w in BANNED if re.search(rf"\b{w}\b", text)]
        ok(not hits, f"{pid}: reader-facing text contains banned word(s) {hits}")
        a = p.get("line_american")
        ok(isinstance(a, int) and WINDOW[0] <= a <= WINDOW[1], f"{pid}: line {a} outside {WINDOW}")
        ok(p.get("implied_pct") == american_to_implied(a), f"{pid}: implied {p.get('implied_pct')} does not match {a}")
        ok(p.get("confidence") == band(p.get("implied_pct", 0)), f"{pid}: confidence {p.get('confidence')} does not match band")
        dec = p.get("line_decimal")
        ok(isinstance(dec, (int, float)) and dec > 1, f"{pid}: bad decimal price")
        srcs = p.get("sources", [])
        ok(any("olbg.com" in urlparse(s["url"]).netloc for s in srcs), f"{pid}: no OLBG source")
        ok(any("olbg.com" not in urlparse(s["url"]).netloc for s in srcs), f"{pid}: no independent official source")
        ok(len(srcs) >= 2, f"{pid}: fewer than two sources")
        ok(len(p.get("facts", [])) >= 1, f"{pid}: no cited facts")
        for f in p.get("facts", []):
            ok(bool(f.get("source", "").startswith("http")), f"{pid}: fact without a source link")
        for s in srcs:
            ok(bool(s.get("url", "").startswith("http")), f"{pid}: source without a URL")

    for f in flags:
        ok(bool(f.get("item")) and bool(f.get("issue")), f"flag {f.get('id')}: incomplete")
        ok(bool(f.get("sources")), f"flag {f.get('id')}: no source link")

    for key in keys:
        ok(key in pricing.get("sports", {}), f"{key}: no pricing method recorded")
        doc = pricing.get("sports", {}).get(key, {})
        ok(bool(doc.get("summary")), f"{key}: pricing summary is empty")

    # internal link integrity across every generated page
    # pricing.html was deliberately retired and archived under desk-v1/ by the
    # desk rebuild, so it is no longer a required page at the root. Requiring it
    # here made this audit fail on a tree that was otherwise correct.
    pages = [ROOT / n for n in ("index.html", "picks.html", "matches.html",
                                "sources.html", "flagged.html", "methodology.html")]
    pages += sorted((ROOT / "originated").glob("*.html"))
    pages += sorted((ROOT / "originated" / "sports").glob("*.html"))
    pages += sorted((ROOT / "sports").glob("*.html"))
    anchors: dict[Path, set] = {}
    for page in pages:
        if not page.exists():
            errors.append(f"page missing: {page.relative_to(ROOT)}")
            continue
        html = page.read_text(encoding="utf-8")
        anchors[page] = set(re.findall(r'id="([^"]+)"', html))
        for href in re.findall(r'href="([^"]+)"', html):
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            target, _, frag = href.partition("#")
            dest = (page.parent / target).resolve() if target else page
            if not dest.exists():
                errors.append(f"{page.relative_to(ROOT)}: broken link {href}")
                continue
            if frag:
                dest_anchors = anchors.get(dest) or set(re.findall(r'id="([^"]+)"', dest.read_text(encoding="utf-8")))
                if frag not in dest_anchors:
                    errors.append(f"{page.relative_to(ROOT)}: missing anchor #{frag} in {dest.relative_to(ROOT)}")

    # The desk at root is a static, server-rendered site: scripts/build_site.py
    # writes the executive summary straight into index.html, so assert on the
    # page the reader actually receives. (This check briefly targeted a
    # client-side renderer during a rebuild that has since been reverted; the
    # assertion has to follow whichever form the committed pages are in, or it
    # fails on a tree that is otherwise correct.)
    ok((ROOT / "index.html").read_text(encoding="utf-8").count("Executive summary") >= 1,
       "landing page has no executive summary")

    print(f"pages: {len(pages)} | sports: {len(sports)} | listings: {sum(len(v) for v in inv_events.values())} "
          f"| picks: {len(picks)} | flags: {len(flags)} | checks: {checks}")
    if errors:
        print(f"\n{len(errors)} problem(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
