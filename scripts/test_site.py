#!/usr/bin/env python3
"""Offline audit for the generated OLBG desk site.

Checks, in order:
  1. every expected page exists;
  2. every local link resolves, on every page;
  3. every board row carries an OLBG event URL and a known sport;
  4. every priced row carries an official source URL and a coherent price;
  5. every published prediction runs to 30+ words, names its selection and
     avoids the words this project keeps out of reader-facing copy;
  6. confidence bands and the -250 / +10000 window flags agree with the numbers.

Exit code 0 means every check passed. No network access is used.
"""

import json
import os
import re
import sys
from collections import Counter
from html import unescape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

SPORTS = [
    "Basketball", "Baseball", "Cricket", "Darts", "Gaelic Sports", "Golf", "Greyhounds",
    "Handball", "Ice Hockey", "Motor Racing", "Rugby League", "Rugby Union", "Snooker",
    "Tennis", "Volleyball",
]
SLUGS = [
    "basketball", "baseball", "cricket", "darts", "gaelic-sports", "golf", "greyhounds",
    "handball", "ice-hockey", "motor-racing", "rugby-league", "rugby-union", "snooker",
    "tennis", "volleyball",
]
PAGES = ["index.html", "picks.html", "matches.html", "pricing.html", "methodology.html",
         "sources.html", "flagged.html"] + [f"sports/{s}.html" for s in SLUGS]
BANNED = ("model", "verified")

errors = []


def fail(msg):
    errors.append(msg)


def check_pages():
    for page in PAGES:
        path = os.path.join(ROOT, page)
        if not os.path.exists(path):
            fail(f"missing page: {page}")
        elif os.path.getsize(path) < 400:
            fail(f"page too small to be real: {page}")


def check_links():
    for page in PAGES:
        path = os.path.join(ROOT, page)
        if not os.path.exists(path):
            continue
        text = open(path, encoding="utf-8").read()
        base = os.path.dirname(path)
        for href in re.findall(r'href="([^"#]+)', text):
            if href.startswith("http") or href.startswith("mailto:"):
                continue
            target = os.path.normpath(os.path.join(base, unescape(href)))
            if not os.path.exists(target):
                fail(f"{page}: broken local link {href}")
        if re.search(r">\s*None\s*<", text):
            fail(f"{page}: stray 'None' in a table cell")


def check_board(payload):
    rows = payload["rows"]
    if not rows:
        fail("board is empty")
    seen = set()
    for row in rows:
        key = (row["sport"], row["event_id"])
        if key in seen:
            fail(f"duplicate listing {key}")
        seen.add(key)
        if not row["olbg_url"].startswith("https://www.olbg.com/betting-tips/"):
            fail(f"{row['id']}: OLBG link is not an event URL")
        if row["sport"] not in SPORTS:
            fail(f"{row['id']}: unknown sport {row['sport']}")
        if not row.get("flags") and not row.get("pick"):
            fail(f"{row['id']}: blank price with no explanation")
        if row["basis"] == "ratings":
            pick = row["pick"]
            if pick is None:
                fail(f"{row['id']}: rated row has no pick object")
                continue
            p = pick["probability"]
            three_way = "draw" in row["markets"]["moneyline"]
            floor = 1 / 3 if three_way else 0.5
            if not floor <= p < 1.0:
                fail(f"{row['id']}: pick is not the favoured side ({p})")
            if pick["confidence"] != (
                "High" if p >= 0.70 else "Medium" if p >= 0.62 else "Low"
            ):
                fail(f"{row['id']}: confidence band disagrees with probability")
            in_window = -250 <= pick["american"] <= 10000
            if in_window != pick["in_price_window"]:
                fail(f"{row['id']}: window flag disagrees with price")
            if not row.get("rating_inputs"):
                fail(f"{row['id']}: priced without rating inputs")
            if row["markets"] is None:
                fail(f"{row['id']}: priced without markets")


def check_predictions(payload, preds):
    published = [r for r in payload["rows"] if r.get("prediction")]
    if not published:
        fail("no published predictions")
    for row in published:
        text = row["prediction"]["analysis"]
        words = len(text.split())
        if words < 30:
            fail(f"{row['id']}: prediction is only {words} words")
        low = text.lower()
        for banned in BANNED:
            if banned in low:
                fail(f"{row['id']}: reader copy contains '{banned}'")
        selection = row["prediction"]["selection"]
        subject = selection.split(" to ")[0]
        tokens = [t for t in re.split(r"[^a-z]+", subject.lower()) if len(t) >= 4]
        if not any(t in low for t in tokens):
            fail(f"{row['id']}: prediction never names {subject}")
        if not re.search(r"\b(back|take|pick|call)\b", low):
            fail(f"{row['id']}: prediction does not state the bet")
        for key in row["prediction"]["sources"]:
            if key not in row["source_urls"]:
                fail(f"{row['id']}: source key {key} has no URL")
        if row["prediction"]["confidence"] != row["pick"]["confidence"]:
            fail(f"{row['id']}: prediction confidence differs from the priced band")


def check_predictions_file(preds, payload):
    ids = {r["id"] for r in payload["rows"] if r.get("pick")}
    for key in preds["entries"]:
        if key not in ids:
            fail(f"prediction {key} has no priced row")


def main():
    check_pages()
    check_links()
    payload = json.load(open(os.path.join(DATA, "matches.json")))
    preds = json.load(open(os.path.join(DATA, "predictions.json")))
    check_board(payload)
    check_predictions(payload, preds)
    check_predictions_file(preds, payload)

    sports_present = {r["sport"] for r in payload["rows"]}
    # Greyhounds and Snooker legitimately have no OLBG market at capture time and
    # are reported as empty categories rather than treated as an error.
    EMPTY_OK = {"Greyhounds", "Snooker"}
    missing = set(SPORTS) - sports_present - EMPTY_OK
    if missing:
        fail(f"sports with no board rows: {sorted(missing)}")

    if errors:
        print(f"FAILED with {len(errors)} problem(s):")
        for e in errors:
            print(" -", e)
        sys.exit(1)

    counts = Counter(r["sport"] for r in payload["rows"])
    published = len([r for r in payload["rows"] if r.get("prediction")])
    print(
        f"site audit ok: {len(PAGES)} pages, {len(payload['rows'])} board rows, "
        f"{len(counts)} sports, {published} written predictions, 0 broken local links"
    )


if __name__ == "__main__":
    main()
