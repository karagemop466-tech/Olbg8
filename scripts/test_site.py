#!/usr/bin/env python3
"""Publication checks for the static desk. Run after build_site.py.

These tests are the contract between the data files and the published pages: a page may not
display a number the pipeline did not produce, a pick may not be short, hedged with forbidden
words, priced outside the agreed band, or missing a source, and no link may dangle.
"""
import json
import os
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAIL = []
WARN = []


def check(cond, msg):
    if not cond:
        FAIL.append(msg)


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def load(rel):
    return json.loads(read(rel))


CAP = load("data/live-capture.json")
LINES = load("data/lines.json")
PICKS = load("data/picks.json")
CW = load("data/crosswalks.json")
PAGES = [f for f in sorted(os.listdir(ROOT)) if f.endswith(".html")] + \
        [f"sports/{f}" for f in sorted(os.listdir(os.path.join(ROOT, "sports"))) if f.endswith(".html")]

# 1. structural integrity of the data ---------------------------------------------------------
ids = [p["pick_id"] for p in PICKS["picks"]]
check(len(ids) == len(set(ids)), "pick_id values are not unique")
idx = {(r["event_id"], r["market"], r["selection"]): r for r in LINES["rows"]}
for p in PICKS["picks"]:
    key = (p["event_id"], p["market"], p["selection"])
    check(key in idx, f"{p['pick_id']}: resolves to no priced row in lines.json")
    if key in idx:
        r = idx[key]
        for fld in ("fair_american", "our_american", "our_prob", "confidence", "official_tier"):
            check(p[fld] == r[fld], f"{p['pick_id']}: {fld} disagrees with lines.json "
                                    f"({p[fld]!r} vs {r[fld]!r})")
check(not any(p["confidence"] == "High" and p["market"].startswith(("Premiership", "Championship", "Six Nations"))
              for p in PICKS["picks"]), "an outright reached the High band")

# 2. the brief's quality bars ------------------------------------------------------------------
FORBIDDEN = ("model", "verified")
for p in PICKS["picks"]:
    note = p["note"]
    words = len(re.findall(r"[\w'/&.%+-]+", note))
    check(words >= 30, f"{p['pick_id']}: note is {words} words, minimum is 30")
    low = note.lower()
    for w in FORBIDDEN:
        check(re.search(rf"\b{w}\b", low) is None, f"{p['pick_id']}: note uses the word '{w}'")
    fa = p["fair_american"]
    check(fa is not None, f"{p['pick_id']}: published pick with no line")
    if fa is not None:
        check(-250 <= fa <= 10000, f"{p['pick_id']}: fair line {fa} is outside −250 to +10,000")
    # A note has to be about *this* fixture. OLBG abbreviates team names ("BOS Bruins"),
    # so the vocabulary it may draw on is the selection, the event label, the market name and
    # the claim text attached to its sources ("Boston Bruins 9-2-1" gives it Boston and Bruins).
    stop = {"over", "under", "tie", "win", "match", "line", "market", "total", "totals", "handicap",
            "the", "and", "for", "with", "from", "this", "that", "own", "league", "list", "page",
            "series", "game", "games", "side", "sides", "official", "source", "tips", "tipped"}
    vocab = " ".join([p["selection"], p["event"], p["market"]] +
                     [f'{s.get("claim") or ""} {s["name"]}' for s in p["sources"]])
    toks = {t for t in re.findall(r"[A-Za-z][A-Za-z'.-]{3,}", vocab)}
    toks = {t for t in toks if t.lower() not in stop and len(t) > 4}
    hits = {t for t in toks if t.lower() in low}
    specific = p["selection"].strip().lower() in low or p["event"].lower() in low
    check(specific or len(hits) >= 2,
          f"{p['pick_id']}: note is too generic — it names neither the selection nor two of the "
          f"participants or facts its own sources state ({sorted(hits)})")
    check(bool(p["sources"]), f"{p['pick_id']}: no source attached")
    for s in p["sources"]:
        check(s["url"].startswith("https://"), f"{p['pick_id']}: source not https: {s['url']}")
        check("olbg.com" not in s["url"] or "betting-tips" in s["url"],
              f"{p['pick_id']}: OLBG source should point at the tips listing")

# 3. prose must not be a template ---------------------------------------------------------------
notes = {p["pick_id"]: p["note"] for p in PICKS["picks"]}


def shingles(text, k=9):
    w = re.findall(r"[A-Za-z0-9'.-]+", text.lower())
    return {tuple(w[i:i + k]) for i in range(max(0, len(w) - k + 1))}


shared = {}
for pid, note in notes.items():
    for sh in shingles(note):
        shared.setdefault(sh, []).append(pid)
dupes = {k: v for k, v in shared.items() if len(set(v)) > 1}
check(not dupes, "two picks share a 9-word run of prose (copy-paste writing): "
                 + "; ".join(f"{' '.join(k)} -> {sorted(set(v))}" for k, v in list(dupes.items())[:3]))
openers = Counter(" ".join(n.split()[:2]).lower() for n in notes.values())
worst = {k: v for k, v in openers.items() if v > 2}
check(not worst, f"pick notes repeat an opening phrase {worst}")
formulaic = [pid for pid, n in notes.items() if re.match(r"^(All \w+|Both|\d+ of|Every one|One \w+ of) ", n)]
check(len(formulaic) <= 5, f"{len(formulaic)} notes open on the tip-count formula; vary the lead-ins")
for pid, n in notes.items():
    words = re.findall(r"[A-Za-z0-9'.-]+", n)
    check(len(shingles(n)) >= len(words) - 9, f"{pid}: repeats itself inside one note")

# 4. coverage ledger ---------------------------------------------------------------------------
per = Counter(p["sport"] for p in PICKS["picks"])
listed = {v["label"] for v in CAP["sports"].values() if v["events"]}
check(set(per) <= listed, "a pick exists for a sport with no OLBG listing")
for label in listed:
    check(per[label] >= 1, f"{label} has a listing but no written pick")
for key, v in CAP["sports"].items():
    if not v["events"]:
        check(v.get("capture_note"), f"{v['label']} has zero events and no capture note explaining it")
        check(per[v["label"]] == 0, f"{v['label']}: picks exist for an empty category")
check(len(PICKS["picks"]) >= 40, f"only {len(PICKS['picks'])} picks published; the desk target is 5 per sport")

# 5. unpriced and uncorroborated must stay visibly honest ---------------------------------------
for r in LINES["rows"]:
    if r["fair_american"] is None:
        check("UNPRICED_MARKET" in r["flags"], f"{r['event']} {r['market']}: unpriced row without a flag")
    if r["official_tier"] != "A":
        check("NO_OFFICIAL_CROSSWALK" in r["flags"],
              f"{r['event']}: tier {r['official_tier']} row missing its corroboration flag")

# 6. the rendered pages ------------------------------------------------------------------------
for page in PAGES:
    html = read(page)
    check(html.startswith("<!doctype html>"), f"{page}: missing doctype")
    for bad in ("None", "nan%", "TODO", "FIXME", "Lorem", "{e(", "{'", "&amp;amp;"):
        if bad in ("None", "nan%"):
            check(re.search(r">\s*" + re.escape(bad) + r"\s*<", html) is None,
                  f"{page}: renders a literal '{bad}' where a value was expected")
        else:
            check(bad not in html, f"{page}: contains '{bad}'")
    check(html.count("<table") == html.count("</table>"), f"{page}: unbalanced table markup")
    check(html.count("<tr") == html.count("</tr>"), f"{page}: unbalanced row markup")

# 7. links resolve ------------------------------------------------------------------------------
class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and d.get("href"):
            self.hrefs.append(d["href"])
        if tag in ("link", "script") and d.get("href" if tag == "link" else "src"):
            self.hrefs.append(d.get("href" if tag == "link" else "src"))


for page in PAGES:
    base = os.path.dirname(os.path.join(ROOT, page))
    lp = Links()
    lp.feed(read(page))
    for h in lp.hrefs:
        if h.startswith(("http://", "https://", "mailto:")):
            check(h.startswith("https://"), f"{page}: insecure link {h}")
            continue
        target = h.split("#")[0]
        if not target:
            continue
        check(os.path.exists(os.path.join(base, target)), f"{page}: broken relative link -> {h}")
    for h in [x for x in lp.hrefs if "#" in x and not x.startswith("http")]:
        frag = h.split("#")[1]
        fpage = os.path.join(base, h.split("#")[0] or page)
        if os.path.exists(fpage) and frag:
            check(f'id="{frag}"' in read(os.path.relpath(fpage, ROOT)),
                  f"{page}: anchor #{frag} does not exist in {h}")

# 8. no fabricated artefacts return ---------------------------------------------------------------
check(not os.path.exists(os.path.join(ROOT, "data", "darts.json")),
      "data/darts.json (fabricated) is back in the published data directory")
check(os.path.exists(os.path.join(ROOT, "quarantine", "FABRICATED-data-darts.json")),
      "quarantine note for the fabricated darts file is missing")

# 9. every row on the board carries a source -------------------------------------------------------
for page in ("picks.html", "matches.html"):
    html = read(page)
    n_rows = html.count("<tr") + html.count('<article class="pick"')
    n_links = html.count("srclink")
    check(n_links >= n_rows, f"{page}: {n_rows} rows but only {n_links} source links rendered")

if WARN:
    print("warnings:")
    for w in WARN:
        print("  !", w)
if FAIL:
    print(f"FAILED {len(FAIL)} check(s):")
    for f in FAIL[:60]:
        print("  x", f)
    sys.exit(1)
print(f"ok — {len(PAGES)} pages, {len(PICKS['picks'])} picks, {len(LINES['rows'])} priced selections, "
      f"{len(idx)} lines rows, all checks passed")
print("   picks per sport: " + ", ".join(f"{k} {v}" for k, v in sorted(per.items(), key=lambda x: -x[1])))
