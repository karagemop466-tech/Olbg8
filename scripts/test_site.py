#!/usr/bin/env python3
"""Offline audit of the rendered site and the payload behind it.

Everything here runs without a network. It fails loudly if a prediction is too
short, reuses another prediction's prose, contains the internal vocabulary the
output is not allowed to use, lacks a source, sits outside the price band while
claiming high confidence, or if any rendered page links to a file that does not
exist.

Run: python3 scripts/test_site.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from line_engine import PRICE_BAND, in_price_band  # noqa: E402

EXPECTED_SPORTS = {
    "Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
    "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
    "Basketball", "Rugby League",
}
BANNED = ("model", "verified")
WORD_FLOOR = 30
ERRORS = []


def err(msg):
    ERRORS.append(msg)


def check(cond, msg):
    if not cond:
        err(msg)


def main():
    picks_doc = json.loads((ROOT / "data/picks.json").read_text())
    events = picks_doc["events"]
    picks = picks_doc["picks"]

    # ---- scope ----------------------------------------------------------
    check(set(picks_doc["by_sport"]) <= EXPECTED_SPORTS,
          "picks.json covers a sport outside the 15 requested")
    check(len(picks_doc["by_sport"]) == 15,
          "expected all 15 sports in by_sport, got %d" % len(picks_doc["by_sport"]))

    # ---- every captured event is accounted for --------------------------
    check(events, "event inventory is empty")
    priced = [x for x in events if x.get("priceable")]
    check(len(priced) > 0, "no event carries an originated line")
    for x in events:
        name = x.get("event_name")
        if not name and not x.get("flags"):
            err("event %s has a blank name and no flag explaining it" % x.get("event_id"))
        if not x.get("priceable"):
            check(x.get("flags"),
                  "event %s is not priceable but carries no explanation" % x.get("event_name"))
        else:
            ol = x.get("our_line") or {}
            check(ol.get("our_pick") is not None,
                  "priced event %s has no pick" % x.get("event_name"))
            p = ol.get("our_pick_probability")
            check(p is not None and 0 < p < 1,
                  "priced event %s has an impossible probability %r" % (x.get("event_name"), p))
            check(ol.get("our_pick_american") is not None,
                  "priced event %s has no American price" % x.get("event_name"))
            fair = ol.get("fair") or {}
            if fair:
                tot = sum(v["p"] for v in fair.values() if isinstance(v, dict) and v.get("p"))
                check(abs(tot - 1.0) < 2e-3,
                      "event %s fair probabilities sum to %.4f" % (x.get("event_name"), tot))
            # a pick promoted above low confidence must not come from the crowd alone
            if ol.get("confidence") in ("high", "medium"):
                check(x.get("evidence_tier") in ("official", "partial"),
                      "event %s is %s confidence on crowd-only evidence"
                      % (x.get("event_name"), ol.get("confidence")))

    # ---- authored predictions ------------------------------------------
    check(picks, "no written predictions were produced")
    seen = {}
    for p in picks:
        pid = p["pick_id"]
        text = (p.get("prediction") or "").strip()
        words = len(text.split())
        check(words >= WORD_FLOOR,
              "%s: prediction is %d words, below the %d-word floor" % (pid, words, WORD_FLOOR))
        low = text.lower()
        for bad in BANNED:
            check(not re.search(r"\b%s\b" % bad, low),
                  "%s: prediction contains the forbidden word %r" % (pid, bad))
        check(p.get("sources"), "%s: no sources listed" % pid)
        check(p.get("corroboration"), "%s: no evidence strands listed" % pid)
        check(p.get("event_name"), "%s: no event name" % pid)
        check(p.get("selection"), "%s: no selection" % pid)
        check(p.get("market"), "%s: no market" % pid)
        for s_ in p.get("sources") or []:
            check(s_.get("url") and s_.get("name"),
                  "%s: a source is missing a name or a url" % pid)
        key = re.sub(r"[^a-z]+", "", low)[:120]
        check(key not in seen, "%s: prediction prose duplicates %s" % (pid, seen.get(key)))
        seen[key] = pid

        conf = p["confidence"]
        check(conf in ("high", "medium", "low"), "%s: unknown confidence %r" % (pid, conf))
        if conf == "high":
            check(p["evidence_tier"] in ("official", "partial"),
                  "%s: high confidence on crowd-only evidence" % pid)
            check(len(p["corroboration"]) >= 3,
                  "%s: high confidence on %d strands, needs at least 3"
                  % (pid, len(p["corroboration"])))
        if p["our_probability"] is not None:
            check(0 < p["our_probability"] < 1,
                  "%s: impossible probability %r" % (pid, p["our_probability"]))
        # The band gate applies to the price WE originate.
        if p["our_american"] is not None:
            check(in_price_band(p["our_american"]),
                  "%s: originated price %s is outside the %s..%s band"
                  % (pid, p["our_american"], PRICE_BAND["min_american"],
                     PRICE_BAND["max_american"]))
            if conf == "high":
                check(p["in_price_band"],
                      "%s: high confidence but outside the price band" % pid)
        # A selection we rate below the market is not a pick.
        if p.get("edge_vs_market") is not None:
            check(p["edge_vs_market"] > 0,
                  "%s: our probability is below the market's implied, so there is no edge" % pid)

    featured = [p for p in picks if p["featured"]]
    check(len(featured) >= 1, "no pick cleared the high-confidence in-band gate")
    for p in featured:
        check(p["confidence"] == "high" and p["in_price_band"],
              "%s: marked featured without clearing both gates" % p["pick_id"])

    # ---- the publishing gate must itself be clean -----------------------
    check(not picks_doc.get("validation_problems"),
          "build_picks reported validation problems: %s"
          % picks_doc.get("validation_problems"))

    # ---- rendered HTML --------------------------------------------------
    html_files = list(ROOT.glob("*.html")) + list((ROOT / "sports").glob("*.html"))
    check(len(html_files) >= 21, "expected at least 21 rendered pages, found %d" % len(html_files))
    for must in ("index.html", "picks.html", "matches.html", "flagged.html",
                 "methodology.html", "sources.html"):
        check((ROOT / must).exists(), "missing page %s" % must)

    index = (ROOT / "index.html").read_text()
    check("Executive summary" in index, "index.html has no executive summary")
    for p in featured:
        check(p["selection"].split("(")[0].strip()[:18] in index
              or p["selection"][:18] in index,
              "featured pick %s is not on the landing page" % p["pick_id"])

    # banned vocabulary must not appear inside any rendered prediction block
    pred_re = re.compile(r'<div class="pred">(.*?)</div>', re.S)
    strip_re = re.compile(r"<[^>]+>")
    for f in html_files:
        for block in pred_re.findall(f.read_text()):
            txt = strip_re.sub(" ", block).lower()
            for bad in BANNED:
                check(not re.search(r"\b%s\b" % bad, txt),
                      "%s: a rendered prediction contains %r" % (f.name, bad))
            check(len(txt.split()) >= WORD_FLOOR,
                  "%s: a rendered prediction is under %d words" % (f.name, WORD_FLOOR))

    # every sport has a page
    for s in EXPECTED_SPORTS:
        slug = s.lower().replace(" ", "-")
        check((ROOT / "sports" / ("%s.html" % slug)).exists(),
              "missing sport page sports/%s.html" % slug)

    # every rendered row links to an official source
    matches_html = (ROOT / "matches.html").read_text()
    check(matches_html.count("Official source") >= 1,
          "matches.html has no official-source column")
    for s in EXPECTED_SPORTS:
        slug = s.lower().replace(" ", "-")
        body = (ROOT / "sports" / ("%s.html" % slug)).read_text()
        rows = body.count("<tr>")
        if rows > 1:
            check("http" in body, "sports/%s.html has table rows but no source links" % slug)

    # no broken relative links anywhere
    href_re = re.compile(r'href="([^"]+)"')
    for f in html_files:
        for href in href_re.findall(f.read_text()):
            parsed = urlparse(href)
            if parsed.scheme or href.startswith("#") or href.startswith("mailto:"):
                continue
            target = (f.parent / parsed.path).resolve()
            check(target.exists(), "%s links to a missing file: %s" % (f.name, href))

    # anchors referenced from other pages must exist
    anchor_re = re.compile(r'href="(picks\.html|\.\./picks\.html)#([^"]+)"')
    picks_html = (ROOT / "picks.html").read_text()
    ids = set(re.findall(r'id="([^"]+)"', picks_html))
    for f in html_files:
        for _href, frag in anchor_re.findall(f.read_text()):
            check(frag in ids, "%s links to picks.html#%s which does not exist" % (f.name, frag))

    if ERRORS:
        print("SITE AUDIT FAILED - %d problem(s):" % len(ERRORS))
        for x in ERRORS:
            print("  ! " + x)
        sys.exit(1)

    print("site audit ok: %d html pages, %d events captured, %d priced, %d written predictions "
          "(%d high confidence in band), %d distinct sources cited"
          % (len(html_files), len(events), len(priced), len(picks), len(featured),
             len({s_["url"] for p in picks for s_ in p["sources"]})))


if __name__ == "__main__":
    main()
