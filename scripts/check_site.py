#!/usr/bin/env python3
"""Dependency-free consistency checks for the static dashboard."""
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
    "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
    "Basketball", "Rugby League",
}

class LocalLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for name in ("href", "src"):
            if name in attrs:
                self.links.append(attrs[name])


def fail(message):
    raise SystemExit(f"ERROR: {message}")

try:
    sports = json.loads((ROOT / "data/sports.json").read_text())
    snapshot = json.loads((ROOT / "data/events.json").read_text())
except (OSError, json.JSONDecodeError) as exc:
    fail(f"cannot read dashboard JSON: {exc}")

if len(sports) != 15 or {s["name"] for s in sports} != EXPECTED:
    fail("sport directory must contain exactly the 15 requested categories")
slugs = [s["slug"] for s in sports]
if len(slugs) != len(set(slugs)):
    fail("sport slugs must be unique")
for sport in sports:
    for key in ("olbg", "authorityUrl"):
        if not sport.get(key, "").startswith("https://"):
            fail(f"{sport['name']} is missing an HTTPS {key} source link")
    page = ROOT / "sports" / f"{sport['slug']}.html"
    if not page.is_file():
        fail(f"missing sport page: {page.relative_to(ROOT)}")

if not snapshot.get("snapshotDate") or not snapshot.get("snapshotSource", "").startswith("https://"):
    fail("snapshot date/source is required")
for event in snapshot.get("events", []):
    if event.get("sport") not in slugs:
        fail(f"unknown event sport: {event.get('sport')}")
    if not event.get("olbgUrl", "").startswith("https://www.olbg.com/"):
        fail(f"event missing OLBG source: {event.get('name')}")
    if not event.get("name") or not event.get("olbgTime"):
        fail("each snapshot sighting must include its observed label and relative time")
    forbidden = {"selection", "price", "confidence", "prediction", "officialStats", "injuries"}
    if forbidden.intersection(event):
        fail(f"unsubstantiated pick/price/research fields found on {event.get('name')}")

static_pages = [ROOT / "index.html", ROOT / "flagged-for-review.html", *sorted((ROOT / "sports").glob("*.html"))]
for page in static_pages:
    if not page.is_file():
        fail(f"missing page: {page}")
    parser = LocalLinks()
    parser.feed(page.read_text())
    for url in parser.links:
        if not url or url.startswith(("https://", "http://", "mailto:", "tel:", "#", "data:")):
            continue
        relative = url.split("#", 1)[0].split("?", 1)[0]
        if not relative:
            continue
        target = (page.parent / relative).resolve()
        if not target.is_file():
            fail(f"broken local link in {page.relative_to(ROOT)}: {url}")

# Ensure the data paths used by the client exist and the JS file parses when Node is present.
if not (ROOT / "app.js").is_file() or not (ROOT / "styles.css").is_file():
    fail("missing application script or stylesheet")
if not re.search(r"data/sports\.json", (ROOT / "app.js").read_text()) or not re.search(r"data/events\.json", (ROOT / "app.js").read_text()):
    fail("client application is missing its data sources")

print(f"OK: {len(sports)} sport pages, {len(snapshot.get('events', []))} sourced OLBG sightings, and all static local links checked.")
print("NOTE: checks validate structure and source-link presence, not live source availability or event facts.")
