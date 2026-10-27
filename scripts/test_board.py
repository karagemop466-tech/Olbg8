#!/usr/bin/env python3
"""Offline validation for the picks board data and generated site."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "board"
BOARD = ROOT / "board"
EXPECTED = {
    "golf", "volleyball", "rugby-union", "cricket", "snooker", "darts",
    "baseball", "gaelic-sports", "greyhounds", "tennis", "motor-racing",
    "handball", "ice-hockey", "basketball", "rugby-league",
}
BANNED = ("model", "verified")


def load():
    sports = {}
    for path in sorted(DATA.glob("board-data-*.json")):
        for sport in json.loads(path.read_text())["sports"]:
            sports[sport["key"]] = sport
    return sports


def check_data(sports):
    assert set(sports) == EXPECTED, set(sports) ^ EXPECTED
    errors, n_rows, n_picks = [], 0, 0
    for key, sport in sports.items():
        for row in sport["rows"]:
            n_rows += 1
            if not row.get("olbg_url", "").startswith("https://www.olbg.com/"):
                errors.append((row["id"], "missing OLBG event link"))
            if not row.get("official_url", "").startswith("https://"):
                errors.append((row["id"], "missing official source link"))
            if row.get("our_line_blank"):
                if not row.get("flags"):
                    errors.append((row["id"], "blank line without explanation flag"))
                continue
            if not row.get("tips_total"):
                errors.append((row["id"], "priced row without tip sample"))
            if not (0 < row["tips_for"] <= row["tips_total"]):
                errors.append((row["id"], "bad tip counts"))
            pred = row.get("prediction")
            if pred:
                n_picks += 1
                words = len(pred.split())
                if words < 30:
                    errors.append((row["id"], f"prediction only {words} words"))
                low = pred.lower()
                for word in BANNED:
                    if re.search(rf"\b{word}\b", low):
                        errors.append((row["id"], f"banned word {word!r} in prediction"))
                if row.get("our_selection_override") or row.get("olbg_selection"):
                    sel = row.get("our_selection_override") or row.get("olbg_selection")
                    if sel and sel not in pred:
                        errors.append((row["id"], "prediction does not name its selection"))
    return errors, n_rows, n_picks


def check_site():
    errors = []
    html_files = list(BOARD.rglob("*.html"))
    assert len(html_files) >= 20, f"only {len(html_files)} pages"
    href_re = re.compile(r'href="([^"]+)"')
    for f in html_files:
        text = f.read_text()
        for href in href_re.findall(text):
            parsed = urlparse(href)
            if parsed.scheme or href.startswith("#") or href.startswith("mailto:"):
                continue
            target = (f.parent / parsed.path).resolve()
            if not target.exists():
                errors.append((str(f.relative_to(ROOT)), href))
        for word in BANNED:
            if re.search(rf"\b{word}\b", text.lower()):
                errors.append((str(f.relative_to(ROOT)), f"banned word {word!r} on page"))
    return errors, len(html_files)


def main():
    sports = load()
    data_errors, n_rows, n_picks = check_data(sports)
    subprocess.run([sys.executable, str(ROOT / "scripts/build_board.py")], check=True)
    site_errors, n_pages = check_site()
    all_errors = [f"data: {e}" for e in data_errors] + [f"site: {e}" for e in site_errors]
    if all_errors:
        for e in all_errors:
            print("FAIL", e)
        raise SystemExit(1)
    print(f"board audit ok: 15 sports, {n_rows} rows, {n_picks} predictions, {n_pages} html pages, all links resolve")


if __name__ == "__main__":
    main()
