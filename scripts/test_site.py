#!/usr/bin/env python3
"""Small offline audit for the static site and its source-first payload."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
    "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
    "Basketball", "Rugby League",
}

def main() -> None:
    dashboard = json.loads((ROOT / "data/dashboard.json").read_text())
    assert set(dashboard["scope"]) == EXPECTED
    assert len(dashboard["sports"]) == 15
    events = dashboard["events"]
    assert events, "event inventory is empty"
    errors = []
    for event in events:
        if not event["olbg"].get("event"):
            errors.append((event["id"], "missing OLBG event link"))
        if not event["official"].get("url"):
            errors.append((event["id"], "missing official source link"))
        if not event.get("flags") and event["official"].get("status") != "event-confirmed":
            errors.append((event["id"], "unflagged row"))
        if not event.get("event") and not any("event name blank" in f for f in event["flags"]):
            errors.append((event["id"], "blank event not explained"))
        draft = event.get("draftPrediction")
        if draft:
            words = len(draft.get("text", "").split())
            if words < 30:
                errors.append((event["id"], f"draft has only {words} words"))
            lowered = draft["text"].lower()
            for banned in ("model", "verified"):
                if banned in lowered:
                    errors.append((event["id"], f"draft contains banned word {banned!r}"))
    assert not errors, errors

    # Check every relative href in the static HTML shells. External sources are
    # intentionally not fetched by this offline audit.
    html_files = list(ROOT.glob("*.html")) + list((ROOT / "sports").glob("*.html"))
    href_re = re.compile(r'href="([^"]+)"')
    missing = []
    for html in html_files:
        for href in href_re.findall(html.read_text()):
            parsed = urlparse(href)
            if parsed.scheme or href.startswith("#") or href.startswith("mailto:"):
                continue
            target = (html.parent / parsed.path).resolve()
            if not target.exists():
                missing.append((str(html.relative_to(ROOT)), href))
    assert not missing, missing
    print(f"site audit ok: {len(html_files)} html shells, {len(events)} rows, {len(dashboard['sports'])} sports")

if __name__ == "__main__":
    main()
