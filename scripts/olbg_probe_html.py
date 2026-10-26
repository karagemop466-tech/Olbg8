#!/usr/bin/env python3
"""Save raw OLBG HTML + a DOM outline so selectors can be designed from real markup."""
import json
import os
import re
import time

import requests
from bs4 import BeautifulSoup

BASE = "https://www.olbg.com"
OUT = "data/olbg/html"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9"})

PAGES = {
    "tennis_sport": f"{BASE}/betting-tips/Tennis/3",
    "tennis_event": f"{BASE}/betting-tips/Tennis/All_Tennis/All_Events/Aliaksandra_Sasnovich_vs_Nikola_Bartunkova/3?event_id=902381",
    "snooker_sport": f"{BASE}/betting-tips/Snooker/8",
    "nba_event": f"{BASE}/betting-tips/Basketball/NBA/NBA/PHX_Suns_@_OKC_Thunder/4?event_id=536205",
    "tennis_hub": f"{BASE}/betting-tips/Tennis/All_Tennis/All_Events",
    "golf_event": f"{BASE}/betting-tips/Golf/All_Golf/All_Events/Mexico_Open/5?event_id=101915",
}


def outline(html):
    """Print compact context windows around structurally interesting tokens."""
    out = []
    for token in ["Win Match", "Win Tips", "event_id", "odds", "__NEXT_DATA__",
                  "application/ld+json", "data-testid", "Value Rating", "Add to Betslip"]:
        for m in list(re.finditer(re.escape(token), html))[:3]:
            a, b = max(0, m.start() - 450), min(len(html), m.end() + 450)
            out.append(f"### {token}\n{html[a:b]}\n")
    # class inventory
    soup = BeautifulSoup(html, "html.parser")
    classes = {}
    for el in soup.find_all(attrs={"class": True}):
        for c in el.get("class", []):
            classes[c] = classes.get(c, 0) + 1
    top = sorted(classes.items(), key=lambda kv: -kv[1])[:80]
    out.append("### classes\n" + "\n".join(f"{c} x{n}" for c, n in top))
    # scripts with json-ish payloads
    for sc in soup.find_all("script"):
        txt = sc.string or ""
        if len(txt) > 2000 and ("event" in txt.lower() or "odds" in txt.lower()):
            out.append(f"### script {sc.get('id')} {sc.get('type')} len={len(txt)}\n{txt[:1200]}")
    return "\n".join(out)


def main():
    os.makedirs(OUT, exist_ok=True)
    log = {}
    for name, url in PAGES.items():
        try:
            r = S.get(url, timeout=30)
            log[name] = {"url": url, "status": r.status_code, "bytes": len(r.text)}
            if r.status_code == 200:
                with open(f"{OUT}/{name}.html", "w") as fh:
                    fh.write(r.text)
                with open(f"{OUT}/{name}.outline.txt", "w") as fh:
                    fh.write(outline(r.text))
        except Exception as exc:  # noqa: BLE001
            log[name] = {"url": url, "error": str(exc)[:200]}
        time.sleep(1)
    with open(f"{OUT}/_index.json", "w") as fh:
        json.dump(log, fh, indent=1)
    print(json.dumps(log, indent=1))


if __name__ == "__main__":
    main()
