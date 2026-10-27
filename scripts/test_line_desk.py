#!/usr/bin/env python3
"""Retained gate for the JS-rendered line desk (session 438bbe65, PR #30).

Copied verbatim from scripts/test_site.py as it stood on main, so that desk's payload stays
validated by its own author's rules. It is no longer wired to scripts/test_site.py: that path
gates the pre-rendered static desk at root (session 0d9bd3c1), and one filename cannot be two
different gates. The root surface is rendered at build time; this one validates the shell and
data/dashboard.json. Keep both green.
"""
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
BANNED = ("model", "verified")


def main() -> None:
    dashboard = json.loads((ROOT / "data" / "dashboard.json").read_text())
    errors: list[str] = []

    present = {s["requested"] for s in dashboard["sports"]}
    if present != EXPECTED:
        errors.append(f"sport scope mismatch: missing {EXPECTED - present}, extra {present - EXPECTED}")
    if len(dashboard["sports"]) != 15:
        errors.append(f"expected 15 requested sports, found {len(dashboard['sports'])}")

    for pick in dashboard["picks"]:
        tag = f"{pick.get('sport')}::{pick.get('event')}::{pick.get('selection')}"
        for field in ("event", "market", "selection", "decimal", "american", "confidence", "prediction", "olbg_url"):
            if pick.get(field) in (None, "", []):
                errors.append(f"{tag}: missing {field}")
        if pick.get("confidence") not in ("low", "medium", "high"):
            errors.append(f"{tag}: bad confidence {pick.get('confidence')!r}")
        words = len((pick.get("prediction") or "").split())
        if words < 30:
            errors.append(f"{tag}: prediction only {words} words")
        lowered = (pick.get("prediction") or "").lower()
        for banned in BANNED:
            if banned in lowered:
                errors.append(f"{tag}: prediction contains {banned!r}")
        if "None" in (pick.get("prediction") or ""):
            errors.append(f"{tag}: prediction contains a None value")
        if not pick.get("olbg_url"):
            errors.append(f"{tag}: no OLBG link")
        official = pick.get("official") or {}
        if pick.get("route") == "primary" and not official.get("source"):
            errors.append(f"{tag}: primary route without a primary source")

    for event in dashboard["events"]:
        if not event.get("olbg_url"):
            errors.append(f"event {event.get('id')}: no OLBG link")
        for market in event.get("markets", []):
            if not market.get("selections"):
                errors.append(f"event {event.get('id')}: empty market {market.get('name')}")
            for selection in market["selections"]:
                if not selection.get("decimal") or selection["decimal"] <= 1.0:
                    errors.append(f"event {event.get('id')}: selection without a captured price")

    shells = list(ROOT.glob("*.html")) + list((ROOT / "sports").glob("*.html"))
    href_re = re.compile(r'href="([^"]+)"')
    for html in shells:
        for href in href_re.findall(html.read_text()):
            parsed = urlparse(href)
            if parsed.scheme or href.startswith("#") or href.startswith("mailto:"):
                continue
            target = (html.parent / parsed.path).resolve()
            if not target.exists():
                errors.append(f"{html.relative_to(ROOT)}: broken link {href}")

    sports_pages = {p.stem for p in (ROOT / "sports").glob("*.html")}
    expected_pages = {s["page"] for s in dashboard["sports"]}
    if sports_pages != expected_pages:
        errors.append(f"sport page mismatch: missing {expected_pages - sports_pages}, extra {sports_pages - expected_pages}")

    if errors:
        raise SystemExit("VALIDATION FAILED\n - " + "\n - ".join(errors[:40]))

    print(
        f"site audit ok: {len(shells)} pages, {len(dashboard['events'])} events, "
        f"{dashboard['counts']['markets']} markets, {len(dashboard['picks'])} picks "
        f"({dashboard['counts']['high']} high), {len(EXPECTED)} requested sports"
    )


if __name__ == "__main__":
    main()
