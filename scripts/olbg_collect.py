#!/usr/bin/env python3
"""
OLBG collector (phase 1: taxonomy + upcoming events).

Runs on GitHub Actions (the agent sandbox cannot reach olbg.com).
Writes machine-readable output to data/olbg/ and commits it back to the branch.

Usage:
  python scripts/olbg_collect.py            # phase 1: sport pages + samples
  python scripts/olbg_collect.py --events   # phase 2: fetch queued event pages
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

BASE = "https://www.olbg.com"
OUT = "data/olbg"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")

# Sport slug -> OLBG sport id (ids confirmed from sitemap-betting-tips.xml)
SPORTS = [
    ("Tennis", 3),
    ("Basketball", 4),
    ("Golf", 5),
    ("Cricket", 7),
    ("Snooker", 8),
    ("Rugby_Union", 9),
    ("Rugby_League", 10),
    ("Baseball", 12),
    ("Ice_Hockey", 13),
    ("Motor_Racing", 14),
    ("Darts", 15),
    ("Handball", 20),
    ("Volleyball", 21),
    ("Gaelic_Football", 25),   # OLBG's Gaelic node
    ("Greyhounds", 28),
]

# Slugs probed to prove/disprove the "Gaelic Sports" mapping
PROBE_SLUGS = ["Gaelic_Sports", "Gaelic_Games", "Gaelic_Football", "Hurling", "Camogie"]

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9"})


def get(url, tries=3):
    last = None
    for i in range(tries):
        try:
            r = SESSION.get(url, timeout=30)
            return r
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 + 2 * i)
    raise RuntimeError(f"GET failed {url}: {last}")


def text_of(node, limit=600):
    t = node.get_text(" ", strip=True)
    t = re.sub(r"\s+", " ", t)
    return t[:limit]


def visible_text(html, limit=7000):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    txt = soup.get_text("\n", strip=True)
    lines, seen = [], None
    for ln in txt.split("\n"):
        ln = re.sub(r"\s+", " ", ln).strip()
        if not ln or ln == seen:
            continue
        seen = ln
        lines.append(ln)
    return "\n".join(lines)[:limit]


def parse_events(html, sport_slug):
    """Extract event links (href carrying event_id) with their local context."""
    soup = BeautifulSoup(html, "html.parser")
    events, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "event_id=" not in href:
            continue
        m = re.search(r"event_id=(\d+)", href)
        if not m:
            continue
        eid = m.group(1)
        if eid in seen:
            continue
        url = href if href.startswith("http") else BASE + ("" if href.startswith("/") else "/") + href
        name = text_of(a, 160)
        ctx = ""
        node = a
        for _ in range(4):
            node = node.parent
            if node is None:
                break
            ctx = text_of(node, 420)
            if len(ctx) > len(name) + 10:
                break
        parts = [p for p in url.split("/") if p]
        # competition path = between sport slug and event name
        events.append({
            "event_id": eid,
            "name": name,
            "url": url,
            "competition_path": "/".join(parts[2:-1]) if len(parts) > 4 else "",
            "context": ctx,
        })
        seen.add(eid)
    return events


def run_phase1():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(f"{OUT}/samples", exist_ok=True)
    run = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "sports": [], "probes": {}}

    for slug, sid in SPORTS:
        url = f"{BASE}/betting-tips/{slug}/{sid}"
        rec = {"slug": slug, "sport_id": sid, "url": url}
        try:
            r = get(url)
            rec.update({"status": r.status_code, "final_url": r.url})
            soup = BeautifulSoup(r.text, "html.parser")
            rec["title"] = text_of(soup.title, 200) if soup.title else ""
            events = parse_events(r.text, slug)
            rec["event_count"] = len(events)
            with open(f"{OUT}/sport_{slug}.json", "w") as fh:
                json.dump({"sport": rec, "events": events}, fh, indent=1)
            with open(f"{OUT}/samples/{slug}.txt", "w") as fh:
                fh.write(f"URL: {r.url}\nSTATUS: {r.status_code}\nTITLE: {rec['title']}\n\n")
                fh.write(visible_text(r.text))
            # sample a couple of event pages per sport so the parser can be designed
            for i, ev in enumerate(events[:2]):
                try:
                    er = get(ev["url"])
                    with open(f"{OUT}/samples/{slug}_event{i}.txt", "w") as fh:
                        fh.write(f"URL: {er.url}\nSTATUS: {er.status_code}\nEVENT: {ev['name']}\n\n")
                        fh.write(visible_text(er.text, 9000))
                    time.sleep(1)
                except Exception as exc:  # noqa: BLE001
                    rec.setdefault("event_sample_errors", []).append(str(exc)[:200])
        except Exception as exc:  # noqa: BLE001
            rec["error"] = str(exc)[:300]
        run["sports"].append(rec)
        time.sleep(1.5)

    for slug in PROBE_SLUGS:
        try:
            r = SESSION.get(f"{BASE}/betting-tips/{slug}", timeout=25)
            run["probes"][slug] = {"status": r.status_code, "final_url": r.url}
        except Exception as exc:  # noqa: BLE001
            run["probes"][slug] = {"error": str(exc)[:150]}
        time.sleep(1)

    with open(f"{OUT}/_run_phase1.json", "w") as fh:
        json.dump(run, fh, indent=1)
    print(json.dumps({"sports": [(s["slug"], s.get("status"), s.get("event_count")) for s in run["sports"]],
                      "probes": run["probes"]}, indent=1))


if __name__ == "__main__":
    if "--events" in sys.argv:
        print("phase 2 not implemented yet")
    else:
        run_phase1()
