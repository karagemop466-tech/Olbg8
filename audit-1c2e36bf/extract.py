#!/usr/bin/env python3
"""Extract a compact, pinned review snapshot from a legacy pick payload.

This reads a specified file and refuses a mismatched SHA-256; it never fetches,
refreshes, edits, or promotes the legacy picks. Set --input to a copy of the
pinned historical data/picks.json if the current file has since changed.
"""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASELINE = "43c3c96d52b0f80bfc8c7e7eba114406805d9d57"
# Filled from the exact byte stream at the pinned commit, not a mutable URL.
PICKS_SHA256 = "22a93c5ce633fb7d9f3a728fdfe52ed0169a0f91c7fd79868cc8651e85b82a08"
KEYS = ("pick_id", "sport_key", "sport", "event_id", "event", "time_label", "market",
        "selection", "confidence", "note", "our_prob", "fair_american", "our_american",
        "in_window", "olbg_url", "sources")


def extract(path):
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != PICKS_SHA256:
        raise ValueError(f"input does not match pinned SHA-256: {digest}")
    data = json.loads(raw)
    picks = data.get("picks")
    if data.get("schema") != "olbg-picks/v2" or not isinstance(picks, list):
        raise ValueError("unexpected source schema")
    return {"schema": "source-review-snapshot/v1", "baseline_commit": BASELINE,
            "source_picks_sha256": digest, "olbg_capture_utc": "2026-10-27T05:26:00Z",
            "source_url": f"https://github.com/karagemop466-tech/Olbg8/blob/{BASELINE}/data/picks.json",
            "originator_url": f"https://github.com/karagemop466-tech/Olbg8/blob/{BASELINE}/scripts/originate.py",
            "note": "A dated historical audit, not a live offer or current prediction list.",
            "picks": [{k: p.get(k) for k in KEYS} for p in picks]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(HERE.parent / "data" / "picks.json"))
    parser.add_argument("--output", default=str(HERE / "snapshot.json"))
    args = parser.parse_args()
    document = extract(args.input)
    Path(args.output).write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(document['picks'])} historical records from {BASELINE[:7]}.")


if __name__ == "__main__":
    main()
