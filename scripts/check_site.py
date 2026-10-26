#!/usr/bin/env python3
"""Quality gate: internal links, per-pick requirements, and data integrity."""
import json, re, sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
errors, warnings = [], []

pages = [ROOT / "index.html", ROOT / "markets.html", ROOT / "methodology.html",
         ROOT / "sources.html", ROOT / "review.html"] + sorted((ROOT / "sports").glob("*.html"))

# 1. internal links exist
for pg in pages:
    text = pg.read_text()
    for m in re.finditer(r'(?:href|src)="([^"]+)"', text):
        url = m.group(1)
        if url.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = url.split("#")[0]
        if not target:
            continue
        dest = (pg.parent / target).resolve()
        if not dest.exists():
            errors.append(f"{pg.relative_to(ROOT)}: broken internal link -> {url}")
    if "<main>" not in text or "</html>" not in text:
        errors.append(f"{pg.relative_to(ROOT)}: malformed page shell")

# 2. picks: every pick needs a >=30 word prediction, a selection and an OLBG link
picks = json.loads((ROOT / "data/picks.json").read_text())
preds = {}
for f in sorted((ROOT / "content").glob("predictions_*.json")):
    preds.update(json.loads(f.read_text()))
missing = [p["pick_id"] for p in picks if p["pick_id"] not in preds]
if missing:
    errors.append(f"picks without a prediction: {missing}")
for p in picks:
    pr = preds.get(p["pick_id"], {})
    words = len((pr.get("prediction") or "").split())
    if words < 30:
        errors.append(f"{p['pick_id']}: prediction only {words} words")
    for banned in ("model", "verified"):
        if banned in (pr.get("prediction") or "").lower():
            errors.append(f"{p['pick_id']}: prediction contains banned word '{banned}'")
    if not p.get("olbg_url") or "olbg.com" not in p["olbg_url"]:
        errors.append(f"{p['pick_id']}: no OLBG source link")
    page = (ROOT / "sports" / f"{p['sport_slug']}.html").read_text()
    if p["pick_id"] not in page:
        errors.append(f"{p['pick_id']}: missing from {p['sport_slug']} page")
    if not (-250 <= (p.get("olbg_american") or 0) <= 10000):
        errors.append(f"{p['pick_id']}: price outside the requested band")

# 3. coverage: all 15 sports have a page
expected = ["golf", "volleyball", "rugby-union", "cricket", "snooker", "darts", "baseball",
            "gaelic-sports", "greyhounds", "tennis", "motor-racing", "handball", "ice-hockey",
            "basketball", "rugby-league"]
for slug in expected:
    if not (ROOT / "sports" / f"{slug}.html").exists():
        errors.append(f"missing sport page: {slug}")

# 4. data sanity
lines = json.loads((ROOT / "data/lines.json").read_text())
for e in lines:
    for m in e["markets"]:
        s = sum(o["p_market"] for o in m["outcomes"])
        if abs(s - 1) > 0.02:
            errors.append(f"{e['event']} / {m['market']}: market probabilities sum to {s:.3f}")
        for o in m["outcomes"]:
            if not (0 < o["p_fair"] < 1):
                errors.append(f"{e['event']} / {o['selection']}: impossible fair probability")
            if not o.get("olbg_decimal"):
                errors.append(f"{e['event']} / {o['selection']}: missing OLBG price")

# 5. visible word checks
for pg in pages:
    t = pg.read_text()
    if "lorem" in t.lower():
        errors.append(f"{pg.name}: placeholder text")

print(f"pages checked: {len(pages)}")
print(f"picks checked: {len(picks)} · predictions: {len(preds)}")
print(f"errors: {len(errors)} · warnings: {len(warnings)}")
for e in errors[:40]:
    print("  ERROR", e)
for w in warnings[:20]:
    print("  WARN", w)
sys.exit(1 if errors else 0)
