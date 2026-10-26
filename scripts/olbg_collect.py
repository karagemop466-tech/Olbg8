#!/usr/bin/env python3
"""OLBG collector v2 — full listing + event-page markets for the 15 covered sports.

Runs on GitHub Actions (the agent sandbox cannot reach olbg.com) and commits
raw, unmodified parse output to data/olbg/.
"""
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from olbg_parse import parse_event_links, parse_event_page  # noqa: E402

BASE = "https://www.olbg.com"
OUT = "data/olbg"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")

SPORTS = [
    ("Tennis", 3), ("Basketball", 4), ("Golf", 5), ("Cricket", 7), ("Snooker", 8),
    ("Rugby_Union", 9), ("Rugby_League", 10), ("Baseball", 12), ("Ice_Hockey", 13),
    ("Motor_Racing", 14), ("Darts", 15), ("Handball", 20), ("Volleyball", 21),
    ("Gaelic_Football", 25), ("Greyhounds", 28),
]

MAX_EVENT_PAGES = int(os.environ.get("MAX_EVENT_PAGES", "30"))

S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9"})


def get(url, tries=3):
    last = None
    for i in range(tries):
        try:
            return S.get(url, timeout=30)
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(str(last)[:200])


def sort_key(ev):
    """Earliest fixtures with the most tipster interest first."""
    tips = 0
    if ev.get("listing_tips"):
        try:
            tips = int(ev["listing_tips"].split("/")[1])
        except Exception:  # noqa: BLE001
            tips = 0
    return (-tips, ev.get("listing_when", "z"))


def main():
    os.makedirs(OUT, exist_ok=True)
    run = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "sport_summary": [], "errors": []}

    for slug, sid in SPORTS:
        listing_url = f"{BASE}/betting-tips/{slug}/{sid}"
        sport_rec = {"sport": slug, "sport_id": sid, "listing_url": listing_url}
        try:
            r = get(listing_url)
            sport_rec["status"] = r.status_code
            if "No tips found" in r.text:
                sport_rec["listing_note"] = "OLBG displayed 'No tips found.' at collection time"
            events = parse_event_links(r.text, slug, sid)
            sport_rec["events_listed"] = len(events)
            events.sort(key=sort_key)
            detailed = []
            for ev in events[:MAX_EVENT_PAGES]:
                try:
                    er = get(ev["url"])
                    if er.status_code != 200:
                        ev["fetch_status"] = er.status_code
                        detailed.append(ev)
                        continue
                    parsed = parse_event_page(er.text)
                    ev2 = dict(ev)
                    ev2.update({
                        "fetch_status": 200,
                        "official_start_utc": parsed["start_utc"],
                        "name": parsed["name"] or ev.get("fixture_name", ""),
                        "competitors": parsed["competitors"],
                        "markets": parsed["markets"],
                        "market_headings": [h["market"] for h in parsed["market_headings"]],
                        "tip_total": parsed["tip_total"],
                        "canonical": parsed["canonical"],
                    })
                    detailed.append(ev2)
                except Exception as exc:  # noqa: BLE001
                    ev["fetch_error"] = str(exc)[:160]
                    detailed.append(ev)
                time.sleep(0.4)
            # events beyond the page cap keep their listing record (market data absent)
            for ev in events[MAX_EVENT_PAGES:]:
                ev["fetch_status"] = "not_fetched_page_cap"
                detailed.append(ev)
            sport_rec["events"] = detailed
            sport_rec["events_with_markets"] = sum(1 for e in detailed if e.get("markets"))
            with open(f"{OUT}/sport_{slug}.json", "w") as fh:
                json.dump(sport_rec, fh, indent=1)
            run["sport_summary"].append({
                "sport": slug, "sport_id": sid, "status": r.status_code,
                "events_listed": len(events),
                "events_with_markets": sport_rec["events_with_markets"],
                "note": sport_rec.get("listing_note", ""),
            })
        except Exception as exc:  # noqa: BLE001
            run["errors"].append({"sport": slug, "error": str(exc)[:300],
                                  "trace": traceback.format_exc()[-800:]})
            run["sport_summary"].append({"sport": slug, "sport_id": sid,
                                         "error": str(exc)[:200]})
        print(slug, run["sport_summary"][-1], flush=True)
        time.sleep(1)

    with open(f"{OUT}/_run.json", "w") as fh:
        json.dump(run, fh, indent=1)
    print(json.dumps(run["sport_summary"], indent=1))


if __name__ == "__main__":
    main()
