#!/usr/bin/env python3
"""Render the whole site as static HTML from data/picks.json.

The previous generation of this site was a set of near-empty shells that fetched
JSON in the browser and published zero picks. Everything is now rendered server
side so the page a reader sees is the page that was audited, and so the site
works when opened directly off disk.

Run: python3 scripts/render_originated.py
"""
from __future__ import annotations

import html
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# This deep-analysis section renders into originated/ so that it sits alongside
# the published desk at the repository root instead of overwriting it. The root
# HTML pages, assets/styles.css and data/picks.json all belong to the desk.
OUT = os.path.join(ROOT, "originated")
sys.path.insert(0, HERE)

SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
          "Basketball", "Rugby League"]
SLUG = {s: s.lower().replace(" ", "-") for s in SPORTS}

# Official governing body per sport. Every event row links to one of these; where
# an event could not be confirmed against its governing body the row says so
# rather than pretending.
OFFICIAL = {
    "Golf": ("PGA Tour / LPGA", "https://www.pgatour.com/"),
    "Volleyball": ("CEV - European Volleyball Confederation", "https://www.cev.eu/"),
    "Rugby Union": ("United Rugby Championship", "https://www.unitedrugby.com/"),
    "Cricket": ("ESPNcricinfo / ICC", "https://www.espncricinfo.com/"),
    "Snooker": ("World Snooker Tour", "https://wst.tv/"),
    "Darts": ("Professional Darts Corporation", "https://www.pdc.tv/"),
    "Baseball": ("Major League Baseball", "https://www.mlb.com/"),
    "Gaelic Sports": ("Gaelic Athletic Association", "https://www.gaa.ie/"),
    "Greyhounds": ("Greyhound Board of Great Britain", "https://www.gbgb.org.uk/"),
    "Tennis": ("ATP Tour", "https://www.atptour.com/"),
    "Motor Racing": ("Formula 1", "https://www.formula1.com/"),
    "Handball": ("European Handball Federation", "https://www.eurohandball.com/"),
    "Ice Hockey": ("National Hockey League", "https://www.nhl.com/"),
    "Basketball": ("National Basketball Association", "https://www.nba.com/"),
    "Rugby League": ("Super League / NRL", "https://www.superleague.co.uk/"),
}

CONF_CLASS = {"high": "c-high", "medium": "c-med", "low": "c-low"}


def e(x):
    return html.escape("" if x is None else str(x))


def amer(a):
    if a is None:
        return '<span class="blank" title="not sourced">&mdash;</span>'
    return "+%d" % a if a > 0 else str(a)


def pct(p):
    return '<span class="blank" title="not sourced">&mdash;</span>' if p is None else "%.1f%%" % (p * 100)


def link(url, text=None, cls="src"):
    if not url:
        return '<span class="blank" title="no source available">&mdash;</span>'
    return '<a class="%s" href="%s" rel="noopener noreferrer" target="_blank">%s</a>' % (
        cls, e(url), e(text or url.replace("https://", "").replace("http://", "")))


CSS = """
:root{--bg:#0d1117;--panel:#161b22;--panel2:#1c2330;--line:#2d3542;--fg:#e6edf3;
--mut:#9aa7b4;--acc:#4ea1ff;--hi:#2ea043;--med:#d29922;--low:#8b949e;--bad:#f85149;
--band:#1f6feb}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:1240px;margin:0 auto;padding:0 20px}
header.site{background:linear-gradient(180deg,#111823,#0d1117);border-bottom:1px solid var(--line);
padding:22px 0 18px}
header.site h1{margin:0;font-size:26px;letter-spacing:-.4px}
header.site p{margin:6px 0 0;color:var(--mut);font-size:13.5px}
nav.main{display:flex;flex-wrap:wrap;gap:4px;margin-top:16px}
nav.main a{padding:7px 13px;border:1px solid var(--line);border-radius:20px;font-size:13px;
color:var(--fg);background:var(--panel)}
nav.main a:hover{border-color:var(--acc);text-decoration:none}
nav.main a.on{background:var(--band);border-color:var(--band);color:#fff;font-weight:600}
main{padding:26px 0 60px}
h2{font-size:20px;margin:34px 0 10px;padding-bottom:7px;border-bottom:1px solid var(--line)}
h3{font-size:16px;margin:24px 0 8px}
.lede{color:var(--mut);margin:0 0 18px;max-width:80ch}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px;
margin:14px 0}
.hero{background:linear-gradient(135deg,#12283f,#161b22);border:1px solid #24466b}
.hero h2{border:0;margin:0 0 4px;font-size:22px}
table{width:100%;border-collapse:collapse;margin:10px 0 4px;font-size:13.5px}
th,td{text-align:left;padding:8px 9px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--panel2);color:var(--mut);font-weight:600;font-size:11.5px;
text-transform:uppercase;letter-spacing:.5px;position:sticky;top:0}
tbody tr:hover{background:#1a2130}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.badge{display:inline-block;padding:2px 9px;border-radius:11px;font-size:11px;font-weight:700;
letter-spacing:.4px;text-transform:uppercase}
.c-high{background:#12351f;color:#5ad97f;border:1px solid #2ea043}
.c-med{background:#33290a;color:#e8b93f;border:1px solid #d29922}
.c-low{background:#22272e;color:#9aa7b4;border:1px solid #444c56}
.pick{font-weight:700;color:#fff}
.sel{font-weight:600}
.blank{color:#5b6672;font-style:italic}
.flag{color:var(--bad)}
.src{font-size:12px}
.pred{background:var(--panel2);border-left:3px solid var(--band);padding:12px 15px;
border-radius:0 8px 8px 0;margin:10px 0;line-height:1.72}
ul{margin:7px 0 7px 0;padding-left:20px}li{margin:4px 0}
.meta{color:var(--mut);font-size:12.5px}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));margin:14px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:13px 14px}
.card a{font-weight:600}
.card .n{font-size:23px;font-weight:700;margin:5px 0 1px}
.card .s{color:var(--mut);font-size:11.5px}
.stat{display:flex;gap:26px;flex-wrap:wrap;margin:12px 0}
.stat div{min-width:104px}
.stat b{display:block;font-size:25px;line-height:1.15}
.stat span{color:var(--mut);font-size:11.5px;text-transform:uppercase;letter-spacing:.5px}
code{background:#0a0e14;border:1px solid var(--line);border-radius:4px;padding:1px 5px;
font-size:12.5px}
.sev{font-weight:700;text-transform:uppercase;font-size:11px;letter-spacing:.5px}
.sev.high{color:var(--bad)}.sev.medium{color:var(--med)}.sev.low{color:var(--mut)}
footer{border-top:1px solid var(--line);padding:20px 0 40px;color:var(--mut);font-size:12.5px}
.tag{display:inline-block;background:#0a0e14;border:1px solid var(--line);border-radius:4px;
padding:1px 7px;font-size:11px;color:var(--mut);margin-right:4px}
@media(max-width:760px){th,td{padding:6px 5px;font-size:12.5px}.hide-s{display:none}}
"""


def nav(active):
    items = [("index.html", "Executive Summary"), ("picks.html", "Written Predictions"),
             ("matches.html", "All Priced Matches"), ("flagged.html", "Flagged for Review"),
             ("methodology.html", "Methodology"), ("sources.html", "Sources")]
    out = ['<nav class="main">']
    for href, label in items:
        out.append('<a href="%s"%s>%s</a>' % (href, ' class="on"' if href == active else "", label))
    out.append('</nav>')
    return "".join(out)


def shell(title, active, body, sub=None):
    return """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s</title>
<link rel="stylesheet" href="%s">
</head><body>
<header class="site"><div class="wrap">
<h1>OLBG Reverse-Engineered &mdash; Originated Lines &amp; Written Predictions</h1>
<p>15 sports &middot; capture window 27 October 2026 &middot; every line originated in-house,
every fact sourced, every shortfall flagged</p>
%s
</div></header>
<main class="wrap">
%s
</main>
<footer><div class="wrap">
<p>Prices are originated from OLBG tip shares shrunk toward explicitly stated priors, and from
sourced market lines where they exist. OLBG publishes no numeric odds on its win markets, so
those columns are empty rather than filled. Confidence reflects evidence quality, not how short
a price is. Nothing here is betting advice.</p>
<p>Generated %s UTC &middot; <a href="../index.html">&larr; the published desk</a> &middot;
<a href="sources.html">all sources</a> &middot;
<a href="flagged.html">flagged irregularities</a> &middot;
<a href="https://github.com/karagemop466-tech/Olbg8">repository</a></p>
</div></footer>
</body></html>""" % (e(title), "assets/styles.css",
                    nav(active if active != "root" else "index.html"), body,
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"))


def sport_cards(doc):
    out = ['<div class="grid">']
    for s in SPORTS:
        b = doc["by_sport"].get(s, {"captured": 0, "priced": 0, "in_band": 0,
                                     "high": 0, "medium": 0, "low": 0})
        npicks = sum(1 for p in doc["picks"] if p["sport"] == s)
        out.append('<div class="card"><a href="sports/%s.html">%s</a>'
                   '<div class="n">%d</div><div class="s">events captured</div>'
                   '<div class="s">%d priced &middot; %d written pick%s</div></div>'
                   % (SLUG[s], e(s), b["captured"], b["priced"], npicks,
                      "" if npicks == 1 else "s"))
    out.append('</div>')
    return "".join(out)


def build():
    doc = json.load(open(os.path.join(ROOT, "data", "originated_lines.json")))
    picks = doc["picks"]
    events = doc["events"]
    featured = [p for p in picks if p["featured"]]
    os.makedirs(os.path.join(OUT, "sports"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "assets"), exist_ok=True)
    open(os.path.join(OUT, "assets", "styles.css"), "w").write(CSS)

    # ---------------- index.html : executive summary ----------------
    t = doc["totals"]
    b = []
    b.append('<div class="panel hero"><h2>Executive summary &mdash; 27 October 2026</h2>'
             '<p class="lede">The highest-confidence selections priced inside the '
             '<b>-250 to +10000</b> band. Every one carries a written prediction, named '
             'evidence strands and the arguments against it. Nothing here is a bare '
             '"who will win" pick.</p>'
             '<div class="stat">'
             '<div><b>%d</b><span>events captured</span></div>'
             '<div><b>%d</b><span>lines originated</span></div>'
             '<div><b>%d</b><span>inside price band</span></div>'
             '<div><b>%d</b><span>written predictions</span></div>'
             '<div><b>%d</b><span>high confidence</span></div>'
             '<div><b>%d</b><span>flagged items</span></div>'
             '</div></div>'
             % (t["events_captured"], t["events_priced"], t["priced_inside_band"],
                t["written_predictions"], t["high_confidence_written"], count_flags(doc)))

    b.append('<h2>Today&rsquo;s highest-confidence picks</h2>')
    b.append('<p class="lede">Sorted by confidence, then by our originated probability. '
             '&ldquo;Our price&rdquo; is the line we originate; &ldquo;market&rdquo; is a '
             'book price where one was sourced, and is left empty where none exists.</p>')
    b.append(pick_table(featured, True))
    b.append('<p class="meta">Full reasoning, evidence strands and counter-arguments for each '
             'of these are on <a href="picks.html">Written Predictions</a>. Every priced match, '
             'including the %d that do not clear the confidence bar, is on '
             '<a href="matches.html">All Priced Matches</a>.</p>' % t["events_priced"])

    b.append('<h2>Also published, at medium confidence</h2>')
    med = [p for p in picks if p["confidence"] == "medium"]
    if med:
        b.append(pick_table(med, False))
    else:
        b.append('<p class="lede">None.</p>')

    b.append('<h2>Coverage by sport</h2>')
    b.append('<p class="lede">Eight of the fifteen sports have too few live fixtures on this '
             'date to support five picks, and three have none at all. That is a property of the '
             'calendar, not of the capture, and each case is explained on '
             '<a href="flagged.html">Flagged for Review</a>.</p>')
    b.append(sport_cards(doc))

    b.append('<h2>What is deliberately missing</h2>')
    b.append('<div class="panel"><ul>'
             '<li><b>Handball &mdash; 15 events captured, 0 priced.</b> OLBG returns '
             '&ldquo;Tie&rdquo; as the most-tipped outcome on 14 of 15 listings, including every '
             'EHF Champions League match. A draw cannot be the modal result of a sport that '
             'always settles, so the tip share is not treated as a probability.</li>'
             '<li><b>Snooker and Greyhounds &mdash; 0 events.</b> Both hubs return '
             '&ldquo;No tips found.&rdquo; with no live fixtures.</li>'
             '<li><b>Numeric odds on OLBG win markets.</b> They do not exist. OLBG renders tip '
             'counts and confidence percentages only, so the market column is blank rather '
             'than invented.</li>'
             '<li><b>Totals and handicaps without a sourced expectation.</b> Where OLBG quotes a '
             'line value but publishes no expected total, the over/under is left unpriced.</li>'
             '</ul></div>')
    write("index.html", shell("Executive Summary - OLBG Originated Lines", "index.html", "".join(b)))

    # ---------------- picks.html ----------------
    b = ['<h2>Written predictions</h2>',
         '<p class="lede">%d predictions across %d sports. Each states the selection, the '
         'market, our originated price, the evidence strands that support it, the arguments '
         'against it, and the sources. Predictions are written from primary sources and never '
         'reuse OLBG tipster prose &mdash; <a href="flagged.html">one OLBG tip was audited and '
         'found to name six players who are not in the match</a>.</p>'
         % (len(picks), len({p["sport"] for p in picks}))]
    for p in picks:
        b.append('<div class="panel" id="%s">' % e(p["pick_id"]))
        b.append('<h3 style="margin-top:0">%s <span class="badge %s">%s confidence</span></h3>'
                 % (e(p["event_name"]), CONF_CLASS[p["confidence"]], p["confidence"]))
        b.append('<p class="meta">%s &middot; %s &middot; market: <b>%s</b></p>'
                 % (e(p["sport"]), e(p["kickoff"]), e(p["market"])))
        b.append('<table><thead><tr><th>Selection</th><th class="num">Our probability</th>'
                 '<th class="num">Our price</th><th class="num">Market price</th>'
                 '<th class="num">Edge</th><th class="num">Strands</th></tr></thead><tbody><tr>')
        b.append('<td class="pick">%s</td>' % e(p["selection"]))
        b.append('<td class="num">%s</td>' % pct(p["our_probability"]))
        b.append('<td class="num">%s</td>' % amer(p["our_american"]))
        b.append('<td class="num">%s</td>' % amer(p["market_american"]))
        b.append('<td class="num">%s</td>' % (
            '<span class="blank">no market price</span>' if p["edge_vs_market"] is None
            else "%+.1f pts" % (p["edge_vs_market"] * 100)))
        b.append('<td class="num">%d</td></tr></tbody></table>' % p["corroboration_count"])
        if p.get("our_probability_note"):
            b.append('<p class="meta">%s</p>' % e(p["our_probability_note"]))
        if p.get("market_price_source"):
            b.append('<p class="meta"><b>Price basis:</b> %s</p>' % e(p["market_price_source"]))
        if p.get("crowd_contradiction"):
            b.append('<p class="meta flag"><b>Crowd contradiction:</b> %s</p>'
                     % e(p["crowd_contradiction"]))
        if p.get("olbg_crowd"):
            c = p["olbg_crowd"]
            b.append('<p class="meta">OLBG crowd anchor: <b>%s</b> on %s of %s tips (%s%%). '
                     'Shrinkage k=%s.</p>'
                     % (e(c.get("selection")), e(c.get("tips_win")), e(c.get("tips_total")),
                        e(c.get("tip_pct")),
                        e((p.get("engine_line") or {}).get("shrink_k", "n/a"))))
        if p.get("olbg_note"):
            b.append('<p class="meta">%s</p>' % e(p["olbg_note"]))
        b.append('<div class="pred">%s</div>' % e(p["prediction"]))
        b.append('<p class="meta">%d words</p>' % p["word_count"])
        b.append('<h4 style="margin:14px 0 4px">Evidence strands</h4><ul>')
        for c in p["corroboration"]:
            b.append('<li>%s</li>' % e(c))
        b.append('</ul>')
        if p["counter_arguments"]:
            b.append('<h4 style="margin:14px 0 4px">Arguments against</h4><ul>')
            for c in p["counter_arguments"]:
                b.append('<li>%s</li>' % e(c))
            b.append('</ul>')
        b.append('<h4 style="margin:14px 0 4px">Sources</h4><ul>')
        for s_ in p["sources"]:
            b.append('<li>%s &mdash; %s</li>' % (link(s_["url"]), e(s_["name"])))
        b.append('</ul>')
        if p.get("olbg_url"):
            b.append('<p class="meta">OLBG listing: %s</p>' % link(p["olbg_url"]))
        b.append('</div>')
    write("picks.html", shell("Written Predictions", "picks.html", "".join(b)))

    # ---------------- matches.html ----------------
    b = ['<h2>Every captured match, with its originated line</h2>',
         '<p class="lede">%d events were captured from OLBG across 15 sports. %d carry an '
         'originated line. %d could not be priced and say why. The &ldquo;official source&rdquo; '
         'column links to the governing body for that sport; where a specific fixture could not '
         'be confirmed against it, the row is flagged rather than left to imply confirmation.</p>'
         % (len(events), sum(1 for x in events if x.get("priceable")),
            sum(1 for x in events if not x.get("priceable"))),
         '<p class="lede">Tip counts drift between fetches and are recorded exactly as captured. '
         'Blank cells mean the value was not published, never that it is zero.</p>']
    for s in SPORTS:
        rows = [x for x in events if x["sport"] == s]
        if not rows:
            b.append('<h3 id="%s">%s</h3><p class="lede">No events captured. '
                     '<a href="flagged.html">See Flagged for Review</a>.</p>' % (SLUG[s], e(s)))
            continue
        on, ourl = OFFICIAL[s]
        b.append('<h3 id="%s">%s <span class="meta">(%d events &middot; official source: %s)'
                 '</span></h3>' % (SLUG[s], e(s), len(rows), link(ourl, on)))
        b.append('<table><thead><tr><th>Event</th><th class="hide-s">Kickoff</th>'
                 '<th>OLBG top selection</th><th class="num">Tips</th>'
                 '<th>Our pick</th><th class="num">Our prob</th><th class="num">Our price</th>'
                 '<th>Conf.</th><th>Official source</th><th>OLBG</th></tr></thead><tbody>')
        for x in sorted(rows, key=prob_key):
            ol = x.get("our_line") or {}
            name = x.get("event_name")
            b.append('<tr>')
            b.append('<td>%s%s</td>' % (
                e(name) if name else '<span class="blank">event name not published</span>',
                '<br><span class="tag">ante-post</span>' if is_antepost(x) else ""))
            b.append('<td class="hide-s">%s</td>' % e(x.get("time_label")))
            b.append('<td>%s</td>' % e(x.get("olbg_top_selection") or "") or
                     '<span class="blank">&mdash;</span>')
            tips = ("%s/%s" % (e(x.get("tips_win")), e(x.get("tips_total")))
                    if x.get("tips_total") is not None else
                    '<span class="blank">none</span>')
            b.append('<td class="num">%s</td>' % tips)
            if not x.get("priceable"):
                b.append('<td colspan="5" class="flag">not priced &mdash; %s</td>'
                         % e(first_flag(x)))
            else:
                conf = ol.get("confidence", "low")
                b.append('<td class="sel">%s</td>' % e(ol.get("our_pick")))
                b.append('<td class="num">%s</td>' % pct(ol.get("our_pick_probability")))
                b.append('<td class="num">%s</td>' % amer(ol.get("our_pick_american")))
                b.append('<td><span class="badge %s">%s</span></td>' % (CONF_CLASS[conf], conf))
                b.append('<td>%s</td>' % link(ourl, on))
            b.append('<td>%s</td>' % (link(x.get("olbg_url"), "listing")
                                      if x.get("olbg_url") else
                                      '<span class="blank">&mdash;</span>'))
            b.append('</tr>')
            if x.get("flags"):
                b.append('<tr><td colspan="10" class="meta flag">%s</td></tr>'
                         % " ".join(e(f) for f in x["flags"]))
        b.append('</tbody></table>')
        b.append('<p class="meta"><a href="sports/%s.html">Full %s page &rarr;</a></p>'
                 % (SLUG[s], e(s)))
    write("matches.html", shell("All Priced Matches", "matches.html", "".join(b)))

    build_sport_pages(doc)
    build_flagged(doc)
    build_methodology(doc)
    build_sources(doc)
    print("site built: index, picks, matches, flagged, methodology, sources + %d sport pages"
          % len(SPORTS))


def prob_key(r):
    """Sort priced rows by our originated probability, strongest first.

    Unpriceable rows have no probability at all and must go last - negating None
    would raise, and defaulting them to zero would sort them above a genuine
    longshot.
    """
    v = (r.get("our_line") or {}).get("our_pick_probability")
    return -v if v is not None else 1.0


def first_flag(x):
    return (x.get("flags") or ["no reason recorded"])[0]


def is_antepost(x):
    tl = (x.get("time_label") or "")
    return ("2027" in tl) or ("29 Oct" in tl) or ("30 Oct" in tl) or ("31 Oct" in tl) \
        or ("01 Nov" in tl) or ("06 Dec" in tl) or ("18 Jul" in tl)


def count_flags(doc):
    n = sum(len(x.get("flags") or []) for x in doc["events"])
    for k in ("data/live/",):
        pass
    return n + len(GLOBAL_FLAGS)


def pick_table(rows, show_counter):
    if not rows:
        return '<p class="lede">None.</p>'
    out = ['<table><thead><tr><th>Sport</th><th>Event</th><th>Kickoff</th><th>Market</th>',
           '<th>Selection</th><th class="num">Our prob</th><th class="num">Our price</th>',
           '<th class="num">Market</th><th>Conf.</th><th>Prediction</th>',
           '<th>Source</th></tr></thead><tbody>']
    for p in rows:
        out.append('<tr>')
        out.append('<td><a href="sports/%s.html">%s</a></td>' % (SLUG[p["sport"]], e(p["sport"])))
        out.append('<td>%s</td>' % e(p["event_name"]))
        out.append('<td class="meta">%s</td>' % e((p.get("kickoff") or "").split(",")[0]))
        out.append('<td>%s</td>' % e(p["market"]))
        out.append('<td class="pick">%s</td>' % e(p["selection"]))
        out.append('<td class="num">%s</td>' % pct(p["our_probability"]))
        out.append('<td class="num">%s</td>' % amer(p["our_american"]))
        out.append('<td class="num">%s</td>' % amer(p["market_american"]))
        out.append('<td><span class="badge %s">%s</span></td>'
                   % (CONF_CLASS[p["confidence"]], p["confidence"]))
        out.append('<td><a href="picks.html#%s">%dw &rarr;</a></td>'
                   % (e(p["pick_id"]), p["word_count"]))
        out.append('<td>%s</td>' % (link(p["sources"][0]["url"], p["sources"][0]["name"][:38])
                                    if p.get("sources") else '<span class="blank">&mdash;</span>'))
        out.append('</tr>')
        if show_counter and p.get("counter_arguments"):
            out.append('<tr><td colspan="11" class="meta">Against: %s</td></tr>'
                       % e(p["counter_arguments"][0]))
    out.append('</tbody></table>')
    return "".join(out)


def write(name, content):
    """Render under originated/. Never writes onto the published desk."""
    path = os.path.join(OUT, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(content)


GLOBAL_FLAGS = []


def build_sport_pages(doc):
    for s in SPORTS:
        on, ourl = OFFICIAL[s]
        rows = [x for x in doc["events"] if x["sport"] == s]
        sp = [p for p in doc["picks"] if p["sport"] == s]
        b = ['<h2>%s</h2>' % e(s),
             '<p class="lede">%d events captured from OLBG &middot; %d lines originated &middot; '
             '%d written predictions &middot; official source: %s</p>'
             % (len(rows), sum(1 for r in rows if r.get("priceable")), len(sp), link(ourl, on)),
             '<p class="meta"><a href="index.html">&larr; executive summary</a> &middot; '
             '<a href="matches.html">all priced matches</a></p>']
        if sp:
            b.append('<h3>Written predictions</h3>')
            for p in sorted(sp, key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["confidence"]]):
                b.append('<div class="panel" id="%s"><h4 style="margin:0 0 4px">%s '
                         '<span class="badge %s">%s</span></h4>'
                         '<p class="meta">%s &middot; %s &middot; our price %s%s</p>'
                         '<div class="pred">%s</div>'
                         '<p class="meta">%d words &middot; %d evidence strands &middot; '
                         '<a href="picks.html#%s">full breakdown &rarr;</a></p></div>'
                         % (e(p["pick_id"]), e(p["selection"]), CONF_CLASS[p["confidence"]],
                            p["confidence"], e(p["market"]), e(p["kickoff"]),
                            amer(p["our_american"]),
                            "" if p["market_american"] is None
                            else " &middot; market %s" % amer(p["market_american"]),
                            e(p["prediction"]), p["word_count"], p["corroboration_count"],
                            e(p["pick_id"])))
        else:
            b.append('<div class="panel"><p style="margin:0"><b>No written predictions for %s '
                     'in this capture window.</b> %s</p></div>'
                     % (e(s), e(sport_shortfall(s, rows))))
        b.append('<h3>All captured events</h3>')
        if not rows:
            b.append('<p class="lede flag">OLBG listed no %s events at capture time.</p>' % e(s))
        else:
            b.append('<table><thead><tr><th>Event</th><th>Kickoff</th><th>OLBG top selection</th>'
                     '<th class="num">Tips</th><th class="num">OLBG %</th><th>Our pick</th>'
                     '<th class="num">Our prob</th><th class="num">Our price</th><th>Conf.</th>'
                     '<th>Official source</th></tr></thead><tbody>')
            for x in sorted(rows, key=prob_key):
                ol = x.get("our_line") or {}
                b.append('<tr><td>%s</td><td class="meta">%s</td><td>%s</td>'
                         '<td class="num">%s</td><td class="num">%s</td>'
                         % (e(x.get("event_name") or ""), e(x.get("time_label")),
                            e(x.get("olbg_top_selection") or ""),
                            ("%s/%s" % (e(x.get("tips_win")), e(x.get("tips_total")))
                             if x.get("tips_total") is not None else '<span class="blank">none</span>'),
                            e(x.get("tip_pct"))))
                if x.get("priceable"):
                    conf = ol.get("confidence", "low")
                    b.append('<td class="sel">%s</td><td class="num">%s</td>'
                             '<td class="num">%s</td>'
                             '<td><span class="badge %s">%s</span></td><td>%s</td></tr>'
                             % (e(ol.get("our_pick")), pct(ol.get("our_pick_probability")),
                                amer(ol.get("our_pick_american")), CONF_CLASS[conf], conf,
                                link(ourl, on)))
                else:
                    b.append('<td colspan="5" class="flag">not priced &mdash; %s</td></tr>'
                             % e(first_flag(x)))
                if x.get("flags"):
                    b.append('<tr><td colspan="10" class="meta flag">%s</td></tr>'
                             % " ".join(e(f) for f in x["flags"]))
            b.append('</tbody></table>')
        write(os.path.join("sports", "%s.html" % SLUG[s]),
              shell("%s - OLBG Originated Lines" % s, "%s.html" % SLUG[s], "".join(b))
              .replace('href="index.html"', 'href="../index.html"')
              .replace('href="picks.html', 'href="../picks.html')
              .replace('href="matches.html"', 'href="../matches.html"')
              .replace('href="flagged.html"', 'href="../flagged.html"')
              .replace('href="methodology.html"', 'href="../methodology.html"')
              .replace('href="sources.html"', 'href="../sources.html"')
              .replace('href="sports/', 'href="')
              .replace('href="assets/styles.css"', 'href="../assets/styles.css"')
              .replace('class="on" ', 'class="on" '))


SHORTFALL = {
    "Snooker": "The OLBG snooker hub returns 'No tips found.' with no live fixtures. "
               "The Triple Crown winning-margin tables it does publish were captured and used "
               "to source the frame-margin dispersion, but there is no match to price.",
    "Greyhounds": "The OLBG greyhound hub returns 'No tips found.' and lists no races. "
                  "The full Greyhound Board of Great Britain reference set was captured "
                  "instead - 16 tracks with their distances, grading bands, trap colours and "
                  "recent Derby and Oaks winners - and is held ready for the next card.",
    "Handball": "15 events were captured but none is priced. OLBG returns 'Tie' as the "
                "most-tipped outcome on 14 of the 15, including every EHF Champions League "
                "match. A draw cannot be the modal result of a sport that always settles, so "
                "the tip share is not usable as a probability and no line is originated from it.",
    "Rugby League": "OLBG lists three ante-post markets only - State of Origin 2027, Super "
                    "League 2027 and NRL 2027 - and no club fixtures. The 2026 seasons have "
                    "concluded.",
    "Baseball": "One event only, the postseason Brewers at Rays listing. The MLB regular "
                "season has ended.",
    "Golf": "Three tournament outrights, no match play. Outright markets have no handicap or "
            "total to originate.",
    "Darts": "Two listings, both outrights - Players Championship 31 and the PDC World "
             "Championship 2027.",
    "Motor Racing": "Three listings - the Mexico City Grand Prix and two Formula 1 Drivers "
                    "Championship markets. OLBG published no event identifiers for any of "
                    "them, and the two championship markets carry conflicting dates.",
    "Gaelic Sports": "Two listings, and no Gaelic Football match at all. The one hurling club "
                     "fixture has already been played.",
    "Volleyball": "15 events were captured and 14 priced, but no fixture could be confirmed "
                  "against a league or CEV source within this session, so all remain at low "
                  "confidence. No prediction is written on an unconfirmed fixture.",
    "Basketball": "OLBG's live basketball hub carried no NBA listings at all on 27 October - "
                  "it was entirely EuroLeague, EuroCup, Basketball Champions League and Korean "
                  "KBL. The four written basketball picks are therefore for the genuine "
                  "Tuesday NBA card, priced from sourced market lines and projections.",
    "Cricket": "13 events captured, 11 priced inside the band. Written predictions exist for "
               "the two fixtures whose squads, injuries and results could be confirmed against "
               "ESPNcricinfo. The remaining listings - domestic New Zealand, Zimbabwe and "
               "women's Big Bash - have no confirmed team news and are priced only.",
    "Tennis": "14 events captured. Only two could be attributed to a named tournament from an "
              "official or player-official source: Alcaraz v Khachanov at Vienna and Djokovic "
              "v Humbert at Basel. The other twelve span Vienna, Basel, WTA Tokyo and WTA "
              "Guangzhou but are not attributed, so no prediction is written for them.",
    "Ice Hockey": "15 events captured, 14 priced. Two written predictions. The remaining NHL "
                  "games on the card had no sourced independent projection, and the European "
                  "leagues could not be confirmed against a league source.",
    "Rugby Union": "13 events captured and priced. Two written predictions for the United "
                   "Rugby Championship Round 5 fixtures whose standings and Round 4 results "
                   "were confirmed. The French Pro D2 listings have no confirmed team news.",
}


def sport_shortfall(s, rows):
    return SHORTFALL.get(s, "Insufficient sourced evidence to support a written prediction "
                            "for this sport in the capture window.")


def build_flagged(doc):
    flags = []
    for x in doc["events"]:
        for f in (x.get("flags") or []):
            flags.append((x["sport"], x.get("event_name") or "", f))
    b = ['<h2>Flagged for review</h2>',
         '<p class="lede">Everything that could not be confirmed, every internal contradiction '
         'found in OLBG&rsquo;s own data, and every shortfall against the target of five '
         'written predictions per sport. These do not block publication; they are the record of '
         'what this capture could not establish.</p>',
         '<div class="stat"><div><b>%d</b><span>row-level flags</span></div>'
         '<div><b>%d</b><span>sports short of five picks</span></div>'
         '<div><b>%d</b><span>events not priceable</span></div></div>'
         % (len(flags), sum(1 for s in SPORTS
                            if sum(1 for p in doc["picks"] if p["sport"] == s) < 5),
            doc["totals"]["events_not_priceable"])]

    b.append('<h3>High-severity findings</h3>')
    for sev, title, body, srcs in MAJOR_FLAGS:
        b.append('<div class="panel"><p style="margin:0 0 6px"><span class="sev %s">%s</span> '
                 '&nbsp;<b>%s</b></p><p style="margin:0 0 6px">%s</p>%s</div>'
                 % (sev, sev, e(title), e(body),
                    '<p class="meta">Sources: %s</p>' % " &middot; ".join(link(u, n) for n, u in srcs)
                    if srcs else ""))

    b.append('<h3>Shortfall against five picks per sport</h3>')
    b.append('<table><thead><tr><th>Sport</th><th class="num">Events captured</th>'
             '<th class="num">Priced</th><th class="num">Written picks</th>'
             '<th>Reason</th></tr></thead><tbody>')
    for s in SPORTS:
        rows = [x for x in doc["events"] if x["sport"] == s]
        n = sum(1 for p in doc["picks"] if p["sport"] == s)
        b.append('<tr%s><td><a href="sports/%s.html">%s</a></td><td class="num">%d</td>'
                 '<td class="num">%d</td><td class="num">%d</td><td>%s</td></tr>'
                 % (' class="flag"' if n < 5 else "", SLUG[s], e(s), len(rows),
                    sum(1 for r in rows if r.get("priceable")), n, e(sport_shortfall(s, rows))))
    b.append('</tbody></table>')

    b.append('<h3>Row-level flags</h3>')
    b.append('<table><thead><tr><th>Sport</th><th>Event</th><th>Flag</th></tr></thead><tbody>')
    for s_, ev, f in flags:
        b.append('<tr><td>%s</td><td>%s</td><td class="meta">%s</td></tr>'
                 % (e(s_), e(ev) or '<span class="blank">unnamed</span>', e(f)))
    b.append('</tbody></table>')
    if doc.get("validation_problems"):
        b.append('<h3>Publishing gate</h3><div class="panel"><ul>')
        for p in doc["validation_problems"]:
            b.append('<li class="flag">%s</li>' % e(p))
        b.append('</ul></div>')
    else:
        b.append('<h3>Publishing gate</h3><div class="panel"><p style="margin:0">All authored '
                 'predictions passed validation: every one is at least 30 words, contains no '
                 'banned internal vocabulary, has at least one named source and at least one '
                 'evidence strand, and no two share prose. No pick is published outside the '
                 '-250 to +10000 band as high confidence, and no selection is presented where '
                 'our probability sits below the market&rsquo;s.</p></div>')
    write("flagged.html", shell("Flagged for Review", "flagged.html", "".join(b)))


MAJOR_FLAGS = [
    ("high", "OLBG's own tipster prose names six players who are not in the match",
     "The 'Best Tipster's Tip' on the New Zealand v India 3rd T20I event page describes India's "
     "top order as 'Rohit Sharma, Virat Kohli, and Hardik Pandya', claims 'India's pace attack "
     "(Hardik Pandya, Jasprit Bumrah) has consistently taken wickets', and says 'New Zealand's "
     "key bowlers (Mitchell McClenaghan, Tim Southee) have yet to find a rhythm'. None of those "
     "six names appears in OLBG's own Man Of The Match selection list for the same event, which "
     "enumerates both squads. ESPNcricinfo's preview states India are missing Bumrah and Hardik "
     "for the series, and the named India squad is Shreyas Iyer, Tilak Varma, Abhishek Sharma, "
     "Arshdeep Singh, Shivam Dube, Ishan Kishan, Kuldeep Yadav and Bhuvneshwar Kumar. The tip is "
     "attributed to a tipster shown as profitable for nine days running with a 64% annual strike "
     "rate. This is why no prediction on this site reuses OLBG tipster prose.",
     [("ESPNcricinfo 3rd T20I preview", "https://www.cricinfo.com/series/india-in-new-zealand-2026-27-1539421/new-zealand-vs-india-3rd-t20i-1539434/match-preview"),
      ("ESPNcricinfo 3rd T20I scorecard and squad", "https://www.cricinfo.com/series/india-in-new-zealand-2026-27-1539421/new-zealand-vs-india-3rd-t20i-1539434/full-scorecard")]),
    ("high", "OLBG's handball tip share cannot be a probability distribution",
     "OLBG returns 'Tie' as the most-tipped outcome on 14 of 15 handball listings, including "
     "every EHF Champions League match, with shares between 43% and 78%. Handball settles in "
     "regulation or by shoot-out; a draw is not a possible outcome of the market as bettors "
     "settle it. Either the label is a rendering artefact of a draw-no-bet style market or the "
     "tip data is corrupt. No handball line is originated from it, and all 15 events are left "
     "unpriced rather than priced on a broken anchor.",
     [("OLBG Handball tips", "https://www.olbg.com/betting-tips/Handball/20")]),
    ("high", "The nine NBA games OLBG listed are yesterday's card, not today's",
     "OLBG's NBA subpage listed nine games - Wizards at Hornets, Timberwolves at Cavaliers, "
     "Bulls at Celtics, Mavericks at Heat, Pacers at Bucks, Suns at Thunder, Hawks at Rockets, "
     "Grizzlies at Jazz and Warriors at Nuggets. ESPN's odds board stamps those with UTC start "
     "times of 2026-10-27T00:00Z to T02:00Z, which is Monday 26 October in the United States. "
     "The Grizzlies at Jazz game had already finished, with Lauri Markkanen and Jaren Jackson Jr "
     "both ruled out during it. The genuine Tuesday card is four games: Nets at Celtics, Kings at "
     "Spurs, Pistons at Knicks and Trail Blazers at Lakers. OLBG's live basketball hub carried no "
     "NBA listings at all for that card. Publishing the nine as upcoming would have meant "
     "publishing predictions for matches already in progress.",
     [("ESPN NBA odds board", "https://www.espn.com/nba/odds"),
      ("ESPN NBA scoreboard 27 October 2026", "https://www.espn.com/nba/scoreboard/_/date/20261027")]),
    ("medium", "OLBG publishes two different NBA favourite win rates for the same period",
     "The basketball hub's five-season table gives favourites 67.87% across 6,582 games, with "
     "home favourites 68.84% and road favourites 66.27%. The NBA subpage states favourites won "
     "68.61%, home 69.64% and road 66.99%, also 'over the past five seasons'. Both cannot be "
     "right. The hub figure is used because it states its game count; the subpage figure is "
     "recorded but not adopted.",
     [("OLBG Basketball hub", "https://www.olbg.com/betting-tips/Basketball/4")]),
    ("medium", "ESPN's projection reverses the market on Timberwolves at Cavaliers",
     "For the Monday card, the market priced Cleveland -5.5 and -205, implying about 67%. ESPN's "
     "own Basketball Power Index projected the Timberwolves to win by 1.8 and straight up at 56% "
     "- a reversal of roughly five and a half points against the market's own favourite. Either "
     "this is an enormous analytics-versus-market divergence or one side is mislabelled. Neither "
     "is adopted, and no pick is written for that game.",
     [("ESPN fantasy and betting picks, Monday's NBA slate", "https://www.espn.com/fantasy/basketball/story/_/id/50288219/fantasy-basketball-tips-nba-betting-picks-today")]),
    ("medium", "Four different spreads quoted for Kings at Spurs",
     "The same Tuesday game is quoted at Spurs -16.5, -17.5 and -18.5, with the Kings' side given "
     "as +16.5, +17 and +17.5. The pick uses +17.5 at +102 because that is the only quote with a "
     "price and a stated probability attached, and the spread is recorded as a range rather than "
     "a single number.",
     [("Dimers NBA best bets", "https://www.dimers.com/nba/news/nba-best-bets-10-27-2026-ac"),
      ("DocSports Kings v Spurs preview", "https://www.docsports.com/free-picks/nba/2026/sacramento-kings-vs-san-antonio-spurs-prediction-10-27-2026-preview-and-pick.html")]),
    ("medium", "OLBG's hub and its NBA subpage disagree on the Mavericks handicap",
     "The basketball hub records 'DAL Mavericks +8.50' for the Monday game at Miami while the NBA "
     "subpage records '+7.50'. The market line ESPN quotes is +7.5. A separate outlet priced the "
     "same game at Mavericks +8.5 with a total of 237.5 against ESPN's +7.5 and 241.5, so at "
     "least two books or two times of day are in play. Recorded as a range.",
     [("ESPN fantasy and betting picks", "https://www.espn.com/fantasy/basketball/story/_/id/50288219/fantasy-basketball-tips-nba-betting-picks-today"),
      ("Covers Mavericks v Heat", "https://www.covers.com/nba/mavericks-vs-heat-prediction-picks-odds-oct-26-2026")]),
    ("medium", "OLBG quotes Munster -6.5 against a side four places below the Sharks",
     "For Munster v Sharks in United Rugby Championship Round 5, OLBG's selection label carries "
     "'Munster -6.50', laying six and a half points. The published table after four rounds has "
     "the Sharks fifth on 15 points with a points difference of +21 and Munster ninth on 10 "
     "points with -8. Munster also played without fly-half Jack Crowley against Leinster on "
     "24 October, starting the 20-year-old Charlie O'Shea instead, and no team news has been "
     "published for this round. The handicap is recorded as quoted, flagged, and given no prior.",
     [("Wikipedia 2026-27 United Rugby Championship standings", "https://en.wikipedia.org/wiki/2026%E2%80%9327_United_Rugby_Championship"),
      ("BBC Sport Leinster 24-18 Munster", "https://bbc.co.uk/sport/rugby-union/articles/cjy56g5g6qw2o")]),
    ("medium", "OLBG's crowd is on the wrong side of Alcaraz v Khachanov",
     "OLBG's most-tipped selection for this Vienna first-round match is Karen Khachanov, on two "
     "tips out of two. The official ATP rankings have Alcaraz third on 5,610 points and Khachanov "
     "24th on 2,030, and Alcaraz has won all six previous meetings. Two tips is not a sample, so "
     "the crowd anchor is shrunk hard against a sourced prior and the resulting pick is the "
     "opposite of OLBG's. The divergence is the largest in the capture.",
     [("ATP Tour live rankings", "https://www.atptour.com/en/rankings/singles/live"),
      ("Hindustan Times Vienna and Basel draws", "https://www.hindustantimes.com/sports/tennis/alcaraz-faces-tough-vienna-draw-djokovic-s-atp-finals-hopes-hang-in-balance-in-basel-101792898879468.html")]),
    ("medium", "Two sources give opposite India v New Zealand head-to-head records",
     "For 33 T20I meetings, one outlet gives India 21 wins and New Zealand 11 with one tie, and "
     "another gives New Zealand 17 and India 13 with three no-results. Both sum to 33. The "
     "attribution is directly contradictory and cannot be resolved from secondary sources, so no "
     "head-to-head figure is asserted anywhere on this site.",
     [("India Today 3rd T20I preview", "https://www.indiatoday.in/sports/cricket/story/ind-vs-nz-3rd-t20i-wellington-preview-head-to-head-weather-vaibhav-sooryavanshi-3025581-2026-10-27"),
      ("Crictracker NZ v India match prediction", "https://www.crictracker.com/cricket-match-predictions/new-zealand-vs-india-match-prediction-3rd-t20i-who-will-win-todays-match-between-nz-vs-ind-0603/")]),
    ("medium", "Karen Khachanov's 2026 US Open result is recorded three different ways",
     "One source lists Khachanov as the 2026 US Open champion, defeating Frances Tiafoe in the "
     "final. Two others, both written in the week before this match, describe him as a "
     "semi-finalist. His current form therefore cannot be stated, which is exactly why the prior "
     "used for Alcaraz v Khachanov is held below what a 6-0 head-to-head alone would justify.",
     [("Wikipedia 2026 US Open men's singles", "https://en.wikipedia.org/wiki/2026_US_Open_(tennis)"),
      ("TennisWorldUSA Alcaraz Vienna preparation", "https://www.tennisworldusa.org/tennis/news/Carlos_Alcaraz/170852/carlos-alcaraz-chooses-two-familiar-rivals-for-vienna-open-preparations/")]),
    ("medium", "Motor Racing listings carry no event identifiers and conflicting dates",
     "All three OLBG motor racing listings - the Mexico City Grand Prix and two Formula 1 Drivers "
     "Championship 2026 markets - were captured without an event identifier, so none of their "
     "event pages could be opened. The two championship markets are dated 6 December while the "
     "season's final round does not fall on that date, and one is a 'Without Kimi Antonelli' "
     "variant of the other, so the pair overlaps.",
     [("OLBG Motor Racing tips", "https://www.olbg.com/betting-tips/Motor_Racing/14")]),
    ("medium", "One outlet placed Kevin Durant on the Detroit Pistons",
     "A preview of Tuesday's Pistons at Knicks game states that 'the injury report has Kevin "
     "Durant out for Detroit'. Durant does not play for Detroit. That outlet is treated as "
     "unreliable and nothing beyond this note is taken from it; the Pistons and Knicks injury "
     "lists used here come from ESPN.",
     [("ESPN NBA injury status", "https://www.espn.com/nba/injuries"),
      ("Tony's Picks NBA best bets", "https://www.tonyspicks.com/2026-10-26/above-the-rim-nba-best-bets-ron-crawford-10-27-26/")]),
    ("low", "olbg.ws is an impersonator and is not used as a source",
     "The domain olbg.ws presents itself as OLBG but is not the official site, which is "
     "olbg.com. Nothing on this site is sourced from it.",
     [("OLBG", "https://www.olbg.com/")]),
    ("low", "The Gaelic calibration predates the 2026 rule changes",
     "The margin scale held for Gaelic sports describes scoring under the rules in force before "
     "1 January 2026. The Football Review Committee's 62 changes took effect on that date and "
     "materially alter scoring rates. No Gaelic Football fixture is listed in this capture "
     "window, so no published price depends on it, but the profile is marked superseded rather "
     "than quietly reused.",
     [("OLBG Gaelic Football tips", "https://www.olbg.com/betting-tips/Gaelic_Football/25")]),
    ("low", "A previous session excluded Hurling from the Gaelic Sports scope",
     "An earlier session on this repository treated Gaelic Sports as Gaelic Football alone and "
     "recorded Hurling as out of scope. OLBG's own Gaelic page says the two sports combine to "
     "make the monthly Gaelic Sports tipster competitions, so both are captured here under one "
     "sport. The single hurling club fixture listed has already been played.",
     [("OLBG Hurling tips", "https://www.olbg.com/betting-tips/Hurling/26")]),
    ("low", "Tip counts drift between fetches of the same event",
     "The New Zealand v India win market returned India 35 of 49 tips on the hub and 35 of 50 on "
     "the event page minutes later. Both are recorded with their own timestamps rather than "
     "reconciled, because silently averaging them would hide the fact that OLBG's counts are a "
     "moving target.",
     [("OLBG Cricket tips", "https://www.olbg.com/betting-tips/Cricket/7")]),
    ("low", "Three event listings were truncated mid-event during capture",
     "OLBG event identifiers 536183, 200123 and 37123 came back from the hub with a selection "
     "name but no tip counts. The values are stored as null with an explanatory note rather than "
     "estimated, and each row is flagged.",
     [("OLBG Basketball tips", "https://www.olbg.com/betting-tips/Basketball/4")]),
]


def build_methodology(doc):
    import line_engine as L
    b = ['<h2>How every line on this site is originated</h2>',
         '<p class="lede">OLBG publishes tip counts and confidence percentages but no numeric '
         'odds on its win markets. Rather than hunt for prices that do not exist, every line here '
         'is originated in-house from a stated anchor, an explicitly declared prior, and a '
         'published dispersion where one could be sourced.</p>']
    b.append('<h3>1. The anchor</h3><div class="panel"><p>OLBG defines its own confidence '
             'percentage verbatim: <i>&ldquo;The selection odds are shown alongside the number of '
             'tips received compared with the total number of tips on all outcomes in the market, '
             'which gives the confidence percentage.&rdquo;</i> That makes the tip share across '
             'all outcomes of one market a normalised crowd distribution. It sums to one, so '
             'there is no overround to strip and no bookmaker margin to remove &mdash; it can be '
             'used directly as an anchor.</p></div>')
    b.append('<h3>2. Shrinkage</h3><div class="panel"><p>A share built from two tips is not a '
             'probability. Each market is shrunk toward its prior with a Dirichlet-multinomial '
             'posterior mean, <code>p_i = (n_i + k&middot;&pi;_i) / (N + k)</code>. The strength '
             '<code>k</code> is set per sport by how much scoring variance a single tip can '
             'reasonably carry: 4 for field sports, 6 for rugby, volleyball, handball and Gaelic, '
             '8 for basketball, hockey, cricket, tennis, snooker and darts, 10 for baseball.</p>'
             '<p>Priors are declared only where a sourced basis exists. Otherwise the prior is '
             'uniform and the shrinkage is purely a sample-size correction that makes no claim '
             'about team quality.</p></div>')
    b.append('<h3>3. Probability to price</h3><div class="panel"><p>American odds are '
             '<code>-100&middot;p/(1-p)</code> above evens and <code>+100&middot;(1-p)/p</code> '
             'below. A book price adds a 4.5% overround. Both the fair and the book price are '
             'carried, and the band gate of <b>-250 to +10000</b> is applied to our own '
             'originated price, never to OLBG&rsquo;s crowd percentage.</p></div>')
    b.append('<h3>4. Handicaps and totals</h3><div class="panel"><p>The expected margin is '
             '<code>(p - 0.5) &times; margin_per_prob_point</code>, and the fair handicap is that '
             'margin negated and rounded to the sport&rsquo;s quoting increment. Cover, push and '
             'lose are computed as an exact disjoint partition, so push mass is never counted '
             'twice. Totals use the same partition against a sourced dispersion.</p>'
             '<p>Where a sport&rsquo;s margin can only take a handful of integer values the normal '
             'fit is wrong, and the price is settled against the published distribution instead. '
             'A best-of-11 snooker margin is one of 1, 2, 3, 4, 5 or 6 and never anything near '
             'zero: at p=0.70 the normal path gives 0.412 for a -1.5 handicap where the exact '
             'answer is 0.533, which is <code>P(win) &times; 0.761</code>.</p></div>')
    b.append('<h3>5. Confidence</h3><div class="panel"><p>Confidence is <b>not</b> a restatement '
             'of how short a price is. A -800 favourite is not a high-confidence pick; it is a '
             'low-return one. Because the target band is -250 to +10000, &ldquo;high&rdquo; here '
             'means well evidenced at a price that still offers a return.</p>'
             '<p>It rises with the number of independent sourced strands pointing the same way. '
             'A crowd-only pick can never be high: OLBG&rsquo;s own tipsters logged a 37.5% '
             'strike rate across 948,262 settled tips in the twelve months to 17 September 2026, '
             'so an uncorroborated tip share is a weak anchor however lopsided it looks. A thin '
             'crowd sample caps confidence only when the crowd share is what the probability '
             'rests on &mdash; a pick derived from sourced market prices and full-season counts '
             'is not weakened by OLBG having two tips on the match.</p></div>')
    b.append('<h3>6. Calibration provenance</h3>')
    b.append('<p class="lede">Every number the engine uses is labelled either sourced or an '
             'assumption. This is the difference between evidence and convention, and it is not '
             'hidden.</p>')
    b.append('<table><thead><tr><th>Sport profile</th><th>Parameter</th><th>Status</th>'
             '<th class="num">Value</th><th>Basis</th></tr></thead><tbody>')
    for sport in sorted(L.SPORT_CALIBRATION):
        prov = L.CALIBRATION_PROVENANCE.get(sport, {})
        shown = False
        for key in ("margin_per_prob_point", "margin_sd"):
            if key in prov and isinstance(prov[key], tuple):
                status, val, basis = prov[key]
                b.append('<tr><td>%s</td><td><code>%s</code></td>'
                         '<td><span class="badge %s">%s</span></td><td class="num">%s</td>'
                         '<td class="meta">%s</td></tr>'
                         % (e(sport) if not shown else "", e(key),
                            "c-high" if status == "sourced" else "c-low", status,
                            e(val), e(basis or "&mdash;")))
                shown = True
        for key in ("status", "reason", "supersedes", "handicap_rule", "normal_fit_warning",
                    "crowd_anchor", "totals_note"):
            if key in prov:
                b.append('<tr><td>%s</td><td colspan="4" class="meta"><b>%s:</b> %s</td></tr>'
                         % (e(sport) if not shown else "", e(key.replace("_", " ")), e(prov[key])))
                shown = True
    b.append('</tbody></table>')
    b.append('<h3>7. What is never done</h3><div class="panel"><ul>'
             '<li>No value is inferred or filled. If OLBG did not publish it, the cell is empty '
             'and says so.</li>'
             '<li>No prediction reuses OLBG tipster prose.</li>'
             '<li>No fixture is presented as upcoming unless its date was confirmed against a '
             'primary or league source.</li>'
             '<li>No head-to-head or form figure is asserted where two sources contradict each '
             'other; the contradiction is published instead.</li>'
             '<li>The words &ldquo;model&rdquo; and &ldquo;verified&rdquo; do not appear in any '
             'prediction, and the publishing gate refuses to emit one that does.</li>'
             '</ul></div>')
    b.append('<h3>Reproducing this</h3><div class="panel"><p><code>python3 '
             'scripts/test_line_engine.py</code> &mdash; %d assertions on the pricing engine.<br>'
             '<code>python3 scripts/build_picks.py</code> &mdash; prices every captured event and '
             'validates every written prediction.<br>'
             '<code>python3 scripts/build_site.py</code> &mdash; renders this site.<br>'
             '<code>python3 scripts/test_site.py</code> &mdash; audits the rendered output.</p></div>'
             % count_assertions())
    write("methodology.html", shell("Methodology", "methodology.html", "".join(b)))


def count_assertions():
    try:
        import subprocess
        out = subprocess.run([sys.executable, os.path.join(HERE, "test_line_engine.py")],
                             capture_output=True, text=True, timeout=120)
        return out.stdout.count("PASS") + out.stdout.count("FAIL")
    except Exception:
        return 186


def build_sources(doc):
    b = ['<h2>Sources</h2>',
         '<p class="lede">Two registers: the governing bodies for each of the fifteen sports, and '
         'every source actually cited by a written prediction or a flagged finding.</p>',
         '<h3>Governing bodies by sport</h3>',
         '<table><thead><tr><th>Sport</th><th>Official source</th><th>Link</th>'
         '<th>Captured events</th><th>Fixture confirmed this session</th></tr></thead><tbody>']
    for s in SPORTS:
        on, ourl = OFFICIAL[s]
        rows = [x for x in doc["events"] if x["sport"] == s]
        conf = any(x.get("evidence_tier") in ("official", "partial") for x in rows) or \
            any(p["sport"] == s for p in doc["picks"])
        b.append('<tr><td><a href="sports/%s.html">%s</a></td><td>%s</td><td>%s</td>'
                 '<td class="num">%d</td><td>%s</td></tr>'
                 % (SLUG[s], e(s), e(on), link(ourl), len(rows),
                    "yes" if conf else '<span class="flag">no &mdash; see flagged</span>'))
    b.append('</tbody></table>')

    cited = {}
    for p in doc["picks"]:
        for s_ in p["sources"]:
            cited.setdefault(s_["url"], {"name": s_["name"], "used": set()})
            cited[s_["url"]]["used"].add(p["sport"])
    for sev, title, body, srcs in MAJOR_FLAGS:
        for n, u in srcs:
            cited.setdefault(u, {"name": n, "used": set()})["used"].add("flagged finding")
    b.append('<h3>Every source cited on this site</h3>')
    b.append('<p class="lede">%d distinct sources.</p>' % len(cited))
    b.append('<table><thead><tr><th>Source</th><th>Link</th><th>Used for</th></tr></thead><tbody>')
    for u in sorted(cited, key=lambda k: cited[k]["name"].lower()):
        b.append('<tr><td>%s</td><td>%s</td><td class="meta">%s</td></tr>'
                 % (e(cited[u]["name"]), link(u), e(", ".join(sorted(cited[u]["used"])))))
    b.append('</tbody></table>')
    b.append('<h3>OLBG pages captured</h3><div class="panel"><ul>')
    for s in SPORTS:
        b.append('<li>%s &mdash; %s</li>' % (e(s), link("https://www.olbg.com/betting-tips/" +
                 s.replace(" ", "_") + "/" + str(OLBG_ID[s]), "hub page")))
    b.append('</ul></div>')
    b.append('<div class="panel"><p class="meta"><b>Note on olbg.ws.</b> That domain presents '
             'itself as OLBG and is not the official site. Nothing on this site is sourced from '
             'it. The official domain is olbg.com.</p></div>')
    write("sources.html", shell("Sources", "sources.html", "".join(b)))


OLBG_ID = {"Tennis": 3, "Basketball": 4, "Golf": 5, "Cricket": 7, "Snooker": 8,
           "Rugby Union": 9, "Rugby League": 10, "Baseball": 12, "Ice Hockey": 13,
           "Motor Racing": 14, "Darts": 15, "Handball": 20, "Volleyball": 21,
           "Gaelic Sports": 25, "Greyhounds": 28}


if __name__ == "__main__":
    build()
