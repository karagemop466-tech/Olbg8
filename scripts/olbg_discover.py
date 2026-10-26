#!/usr/bin/env python3
"""Discovery pass: understand OLBG page structure, pagination, odds markup, hub pages."""
import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

BASE = "https://www.olbg.com"
OUT = "data/olbg"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9"})

SPORTS = [("Tennis", 3), ("Basketball", 4), ("Golf", 5), ("Cricket", 7), ("Snooker", 8),
          ("Rugby_Union", 9), ("Rugby_League", 10), ("Baseball", 12), ("Ice_Hockey", 13),
          ("Motor_Racing", 14), ("Darts", 15), ("Handball", 20), ("Volleyball", 21),
          ("Gaelic_Football", 25), ("Greyhounds", 28)]


def get(url):
    try:
        r = S.get(url, timeout=30)
        return r
    except Exception as exc:  # noqa: BLE001
        return exc


def save(name, r, limit=400000):
    os.makedirs(f"{OUT}/html", exist_ok=True)
    if isinstance(r, Exception):
        open(f"{OUT}/html/{name}.txt", "w").write(f"ERROR {r}")
        return
    open(f"{OUT}/html/{name}.html", "w").write(r.text[:limit])


def hrefs(r):
    soup = BeautifulSoup(r.text, "html.parser")
    return [a["href"] for a in soup.find_all("a", href=True)]


def main():
    os.makedirs(f"{OUT}/html", exist_ok=True)
    report = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "sports": {}, "probes": {}}

    # 1. raw samples for structural analysis
    for slug, sid in [("Tennis", 3), ("Snooker", 8), ("Golf", 5), ("Greyhounds", 28)]:
        r = get(f"{BASE}/betting-tips/{slug}/{sid}")
        save(f"sport_{slug}", r)
        time.sleep(1)

    # 2. per-sport: pagination behaviour + link inventory
    for slug, sid in SPORTS:
        info = {"id": sid}
        base_url = f"{BASE}/betting-tips/{slug}/{sid}"
        counts = {}
        for q in ["", "?page=2", "?page=3", "?p=2", "?show_expired=1"]:
            r = get(base_url + q)
            if isinstance(r, Exception):
                counts[q or "base"] = f"ERR {str(r)[:60]}"
                continue
            ev = set(re.findall(r"event_id=(\d+)", r.text))
            counts[q or "base"] = {"status": r.status_code, "events": len(ev),
                                   "len": len(r.text)}
            info.setdefault("event_ids", set()).update(ev)
            time.sleep(1)
        info["variants"] = counts
        # hub links: /betting-tips/<slug>/<comp>/<comp> patterns
        r = get(base_url)
        if not isinstance(r, Exception):
            hs = hrefs(r)
            comps = sorted({h for h in hs if re.match(rf"/betting-tips/{slug}/[^/]+/?$", h)
                            or re.match(rf"/betting-tips/{slug}/[^/]+/[^/]+/?$", h)})
            info["hub_links"] = comps[:60]
            info["total_links"] = len(hs)
        if "event_ids" in info:
            info["event_ids"] = sorted(info["event_ids"])
        report["sports"][slug] = info
        time.sleep(1)

    # 3. event page structure (odds markup) — grab one known tennis event
    r = get(f"{BASE}/betting-tips/Tennis/3")
    if not isinstance(r, Exception):
        m = re.search(r'href="([^"]*event_id=\d+[^"]*)"', r.text)
        if m:
            ev_url = urljoin(BASE, m.group(1))
            report["event_probe"] = ev_url
            er = get(ev_url)
            save("event_sample", er)
            if not isinstance(er, Exception):
                # look for odds-like payloads
                pats = {
                    "decimal_like": re.findall(r'"odds"\s*:\s*"?([0-9.]+)', er.text)[:20],
                    "fractional_like": re.findall(r">\s*(\d{1,3}/\d{1,3})\s*<", er.text)[:20],
                    "jsonld": er.text.count("application/ld+json"),
                    "market_terms": sorted({t for t in ["Win Match", "Match Odds", "Handicap",
                                                       "Total", "Over/Under", "Correct Score",
                                                       "Set Betting", "Money Line", "Spread"]
                                            if t.lower() in er.text.lower()}),
                }
                report["event_markup"] = pats

    # 4. probe likely JSON endpoints
    for u in ["/api/sports", "/api/events", "/api/odds", "/graphql", "/api/v1/events",
              "/betting-odds", "/fixtures", "/sportsbook"]:
        r = get(BASE + u)
        report["probes"][u] = (f"ERR {str(r)[:50]}" if isinstance(r, Exception)
                               else {"status": r.status_code, "ctype": r.headers.get("content-type", ""),
                                     "len": len(r.text)})
        time.sleep(0.5)

    with open(f"{OUT}/_run_discovery.json", "w") as fh:
        json.dump(report, fh, indent=1, default=list)
    print("done", {k: v.get("variants") for k, v in report["sports"].items()})
    print("probes", report["probes"])


if __name__ == "__main__":
    main()
