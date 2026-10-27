#!/usr/bin/env python3
"""Static site generator for the OLBG research desk.

Reads data/desk.json and writes plain HTML files into the repository root so
GitHub Pages can serve them without a build step.
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "desk.json"

SPORT_KEYS = ["golf", "volleyball", "rugby-union", "cricket", "snooker", "darts", "baseball",
              "gaelic-sports", "greyhounds", "tennis", "motor-racing", "handball", "ice-hockey",
              "basketball", "rugby-league"]


def e(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def money(am) -> str:
    if am is None:
        return "-"
    try:
        am = int(am)
    except Exception:
        return e(am)
    return f"+{am}" if am > 0 else str(am)


def plural(n: int, word: str, suffix: str = "s") -> str:
    return f"{n} {word}" + ("" if n == 1 else suffix)


def day(iso: str) -> str:
    if not iso:
        return "-"
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    try:
        return f"{int(iso[8:10])} {months[int(iso[5:7]) - 1]} {iso[11:16]}"
    except Exception:
        return e(iso)


def conf_badge(c: str) -> str:
    cls = {"high": "high", "medium": "medium", "low": "low"}.get(c, "low")
    return f'<span class="badge {cls}">{e(c.upper())}</span>'


def nav(active: str, sports: list[dict]) -> str:
    links = [("index.html", "Overview", "home"), ("picks.html", "Picks", "picks"),
             ("matches.html", "Matches", "matches"), ("sources.html", "Sources", "sources"),
             ("methodology.html", "Method", "method"), ("flagged.html", "Flagged for Review", "flagged")]
    items = "".join(
        '<a href="%s"%s>%s</a>' % (href, ' class="active"' if key == active else "", e(label))
        for href, label, key in links)
    return f'''<header class="site-header"><div class="header-inner">
<a class="brand" href="index.html"><span class="brand-mark">OL</span>OLBG Research Desk</a>
<nav class="nav">{items}</nav>
</div></header>'''


def sport_nav(active: str, sports: list[dict], prefix: str = "") -> str:
    items = []
    for s in sports:
        cls = ' class="sp-pill active"' if s["key"] == active else ' class="sp-pill"'
        items.append(f'<a href="{prefix}sports/{s["key"]}.html"{cls}>{e(s["label"])}'
                     f'<span>{s["picks"]}</span></a>')
    return f'<div class="sport-pills">{"".join(items)}</div>'


def footer(built: str) -> str:
    return f'''<footer class="site-footer"><div class="footer-inner">
<p><strong>Independent research.</strong> Built {e(built)} from live OLBG listings and published official competition sources.
Prices move; re-check the linked market before acting. Not betting advice and no outcome is guaranteed.
Bet only where lawful and only what you can afford to lose.</p>
<p class="muted">Every row links to the OLBG market it came from. Where an official competition source could not be reached the row says so and appears on the Flagged for Review page.</p>
</div></footer>'''


def page(title: str, active: str, body: str, sports: list[dict], built: str, prefix: str = "") -> str:
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · OLBG research desk</title>
<meta name="description" content="Independent research desk for 15 OLBG sports: current listings, originated lines, confidence-rated picks and flagged gaps.">
<link rel="stylesheet" href="{prefix}assets/styles.css">
</head>
<body>
{nav(active, sports).replace('href="', 'href="' + prefix)}
<main>
{body}
</main>
{footer(built).replace('href="', 'href="' + prefix)}
<script src="{prefix}assets/app.js" defer></script>
</body>
</html>'''


def pick_card(p: dict, prefix: str = "", show_sport: bool = True) -> str:
    ev = p.get("event_name") or ""
    src = [f'<a href="{e(p["olbg_url"])}" target="_blank" rel="noopener">OLBG market</a>']
    if p.get("official_url"):
        src.append(f'<a href="{e(p["official_url"])}" target="_blank" rel="noopener">{e(p.get("official_source") or "Official source")}</a>')
    flags = ""
    if p.get("flags"):
        flags = '<ul class="flags">' + "".join(f"<li>{e(f)}</li>" for f in p["flags"]) + "</ul>"
    sport_line = f'<a href="{prefix}sports/{p["sport"]}.html">{e(p["sport_label"])}</a> · ' if show_sport else ""
    return f'''<article class="pick" id="pick-{e(p["id"])}">
<div class="pick-top">
<div class="pick-head">
<p class="pick-meta">{sport_line}{e(p["competition"] or "Competition not stated")} · {e(day(p["start_utc"]))} UTC</p>
<h3>{e(p.get("headline"))}</h3>
<p class="pick-event">{e(ev)}</p>
</div>
<div class="pick-numbers">
<div><span class="lbl">Price</span><strong>{e(money(p["price_american"]))}</strong></div>
<div><span class="lbl">Our fair</span><strong>{e(money(p["our_fair_american"]))}</strong></div>
<div><span class="lbl">Chance</span><strong>{p["our_prob"] * 100:.1f}%</strong></div>
<div>{conf_badge(p["confidence"])}</div>
</div>
</div>
<p class="prediction">{e(p["prediction"])}</p>
<div class="pick-foot">
<span class="basis">Line basis: {e(p.get("basis"))}</span>
<span class="srcs">{' · '.join(src)}</span>
</div>
{flags}
</article>'''


def picks_table(picks: list[dict], prefix: str = "") -> str:
    rows = []
    for p in picks:
        off = ""
        if p.get("official_url"):
            off = ' · <a href="%s" target="_blank" rel="noopener">Official</a>' % e(p["official_url"])
        rows.append(f'''<tr>
<td class="nowrap">{e(day(p["start_utc"]))}</td>
<td><a href="{prefix}sports/{p["sport"]}.html">{e(p["sport_label"])}</a></td>
<td>{e(p["event_name"])}<div class="sub">{e(p["competition"] or "")}</div></td>
<td><strong>{e(p["selection"])}</strong><div class="sub">{e(p["market"])}</div></td>
<td class="num">{e(money(p["price_american"]))}</td>
<td class="num">{e(money(p["our_fair_american"]))}</td>
<td class="num">{p["our_prob"] * 100:.1f}%</td>
<td>{conf_badge(p["confidence"])}</td>
<td class="links"><a href="{e(p["olbg_url"])}" target="_blank" rel="noopener">OLBG</a>{off}</td>
</tr>''')
    return f'''<div class="table-wrap"><table class="data">
<thead><tr><th>Start (UTC)</th><th>Sport</th><th>Match</th><th>Selection &amp; market</th><th>Price</th><th>Our fair</th><th>Chance</th><th>Confidence</th><th>Sources</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>'''


def build_index(desk: dict) -> str:
    s, sports, picks = desk["summary"], desk["sports"], desk["picks"]
    top = sorted(picks, key=lambda p: (-p["our_prob"], p["start_utc"]))[:8]
    gaps = [x for x in sports if x["picks"] == 0]
    cards = "".join(
        f'''<a class="sport-card" href="sports/{x["key"]}.html">
<div class="sc-head"><h3>{e(x["label"])}</h3><span class="sc-count">{x["picks"]}</span></div>
<p class="sc-sub">{x["events"]} events · {x["listings"]} listings</p>
<p class="sc-status">{'<span class="ok">picks published</span>' if x["picks"] else '<span class="gap">no qualifying pick</span>'}</p>
</a>''' for x in sports)
    body = f'''
<section class="hero">
<p class="eyebrow">Executive summary · {e(desk["built_utc"][:10])}</p>
<h1>15 OLBG sports, priced and written up</h1>
<p class="lede">This desk captures the live OLBG boards for the fifteen sports in scope, strips the bookmaker margin to produce its own fair line for every selection, then publishes confidence-rated picks with written reasoning. Each pick links to the exact OLBG market and, where one exists, the official competition source behind the numbers.</p>
<div class="kpis">
<div class="kpi"><div class="kpi-value">{s["sports"]}</div><div class="kpi-label">sports covered</div></div>
<div class="kpi"><div class="kpi-value">{s["events"]}</div><div class="kpi-label">upcoming events</div></div>
<div class="kpi"><div class="kpi-value">{s["markets_captured"]}</div><div class="kpi-label">markets priced</div></div>
<div class="kpi"><div class="kpi-value">{s["selections_priced"]}</div><div class="kpi-label">selections in board</div></div>
<div class="kpi"><div class="kpi-value">{s["picks"]}</div><div class="kpi-label">published picks</div></div>
<div class="kpi"><div class="kpi-value">{s["high"]}</div><div class="kpi-label">high confidence</div></div>
</div>
</section>

<section class="block">
<div class="block-head">
<h2>Highest-confidence picks right now</h2>
<p class="muted">Ranked by our fair probability. Filtered to fair prices between -250 and +10,000.</p>
</div>
{picks_table(top) if top else '<p class="empty">No selection cleared the confidence and price filters in this capture.</p>'}
<p class="cta-row"><a class="button primary" href="picks.html">See all {s["picks"]} picks with full write-ups</a></p>
</section>

<section class="block">
<div class="block-head"><h2>Top write-ups</h2><p class="muted">Full reasoning for the strongest four picks. The rest sit on the Picks page.</p></div>
<div class="pick-grid">{''.join(pick_card(p) for p in top[:4])}</div>
</section>

<section class="block">
<div class="block-head"><h2>Sports coverage</h2><p class="muted">Number on each card is picks published for that sport in this capture.</p></div>
<div class="sport-grid">{cards}</div>
</section>

<section class="block notice">
<h2>What this capture covers, and what it does not</h2>
<div class="two-col">
<div>
<h3>Covered</h3>
<ul>
<li>{s["events"]} upcoming events read from OLBG sport and competition feeds.</li>
<li>{s["markets_captured"]} markets, including match winner, handicap and match total where OLBG lists them.</li>
<li>{s["official_confirmed_events"]} events cross-checked against an official competition feed (MLB, NHL, Formula 1).</li>
<li>{s["picks"]} picks, each with the OLBG price, our fair line, a confidence band and written reasoning.</li>
</ul>
</div>
<div>
<h3>Not covered</h3>
<ul>
<li>{len(gaps)} sports produced no qualifying pick in this capture: {", ".join(e(g["label"]) for g in gaps) if gaps else "none"}.</li>
<li>Injury and availability reports are only used where the official source publishes them. Nothing is guessed.</li>
<li>Commissions outside the official feeds are priced from the de-margined OLBG board, not from a ratings table.</li>
</ul>
<p><a class="button" href="flagged.html">Open Flagged for Review</a></p>
</div>
</div>
</section>

<section class="block">
<h2>How a pick gets published</h2>
<div class="steps">
<div class="step"><span>1</span><h3>Capture</h3><p>Every sport feed and competition page in scope is read hourly from OLBG, then each event page is fetched for its full market board.</p></div>
<div class="step"><span>2</span><h3>Price</h3><p>The bookmaker margin is removed with the power method to get a fair probability, then nudged by official form where a feed exists.</p></div>
<div class="step"><span>3</span><h3>Filter</h3><p>Only selections priced between -250 and +10,000 with a fair chance above 45% reach the shortlist, ranked by probability.</p></div>
<div class="step"><span>4</span><h3>Write</h3><p>Each pick gets original reasoning built only from captured numbers, plus links to the OLBG market and official source.</p></div>
</div>
<p class="cta-row"><a class="button" href="methodology.html">Read the full method</a></p>
</section>
'''
    return page("Overview", "home", body, sports, desk["built_utc"])


def build_picks(desk: dict) -> str:
    picks = desk["picks"]
    sports = desk["sports"]
    blocks = []
    for sp in sports:
        rows = [p for p in picks if p["sport"] == sp["key"]]
        if not rows:
            continue
        blocks.append(f'''<section class="block" id="{sp["key"]}">
<div class="block-head"><h2>{e(sp["label"])} <span class="count">{len(rows)} picks</span></h2>
<p class="muted">{sp["events"]} events captured · {sp["high"]} high confidence · official crosswalk on {sp["official_confirmed"]} events</p></div>
<div class="pick-grid">{''.join(pick_card(p, show_sport=False) for p in rows)}</div>
</section>''')
    empty = [sp["label"] for sp in sports if not any(p["sport"] == sp["key"] for p in picks)]
    body = f'''
<section class="hero compact">
<p class="eyebrow">Picks</p>
<h1>Every published pick, with its reasoning</h1>
<p class="lede">{len(picks)} picks across {len({p["sport"] for p in picks})} sports. Each card states the selection, the OLBG price, our fair price, the confidence band and the sources behind the numbers.</p>
{sport_nav("", sports)}
</section>
<section class="block">
<div class="block-head"><h2>All picks at a glance</h2><p class="muted">Every published selection with its price, our fair price and confidence band.</p></div>
{picks_table(sorted(picks, key=lambda p: (-p["our_prob"], p["start_utc"])))}
</section>
<div class="picks-layout">
<aside class="side">
<h3>Jump to</h3>
<ul class="jump">{''.join(f'<li><a href="#{sp["key"]}">{e(sp["label"])} ({len([p for p in picks if p["sport"] == sp["key"]])})</a></li>' for sp in sports)}</ul>
</aside>
<div class="picks-main">
{"".join(blocks) if blocks else '<p class="empty">No picks in this capture.</p>'}
{f'<section class="block notice"><h3>Sports without a qualifying pick</h3><p>{", ".join(e(x) for x in empty)}.</p><p>These sports either had no OLBG listing at capture time or no selection inside the -250 to +10,000 window with a high enough fair chance. Every case is itemised on <a href="flagged.html">Flagged for Review</a>.</p></section>' if empty else ''}
</div>
</div>
'''
    return page("Picks", "picks", body, sports, desk["built_utc"])


def offlink(ev: dict) -> str:
    url = (ev.get("official") or {}).get("source_url")
    return ' · <a href="%s" target="_blank" rel="noopener">Official</a>' % e(url) if url else ""


def build_sport(desk: dict, sp: dict) -> str:
    picks = [p for p in desk["picks"] if p["sport"] == sp["key"]]
    events = [x for x in desk["events"] if x["sport"] == sp["key"]]
    rows = []
    for ev in events:
        markets = ev.get("markets") or {}
        mnames = ", ".join(sorted(markets)) or "none captured"
        rows.append(f'''<tr>
<td class="nowrap">{e(day(ev.get("start_utc")))}</td>
<td>{e(ev.get("event_name"))}<div class="sub">{e(ev.get("competition") or "")}</div></td>
<td>{len(markets)}<div class="sub">{e(mnames)}</div></td>
<td>{'<span class="ok">crosswalked</span>' if ev.get("official_confirmed") else '<span class="warn">board only</span>'}</td>
<td class="links"><a href="{e(ev["olbg_url"])}" target="_blank" rel="noopener">OLBG</a>{offlink(ev)}</td>
</tr>''')
    body = f'''
<section class="hero compact">
<p class="eyebrow">Sport</p>
<h1>{e(sp["label"])}</h1>
<p class="lede">{sp["events"]} upcoming events and {sp["listings"]} OLBG listings captured. {sp["picks"]} picks published, {sp["high"]} of them high confidence. Official crosswalk available on {sp["official_confirmed"]} events.</p>
<div class="kpis">
<div class="kpi"><div class="kpi-value">{sp["events"]}</div><div class="kpi-label">events</div></div>
<div class="kpi"><div class="kpi-value">{sp["listings"]}</div><div class="kpi-label">listings</div></div>
<div class="kpi"><div class="kpi-value">{sp["picks"]}</div><div class="kpi-label">picks</div></div>
<div class="kpi"><div class="kpi-value">{sp["high"]}</div><div class="kpi-label">high confidence</div></div>
</div>
{sport_nav(sp["key"], desk["sports"], prefix="../")}
</section>
<section class="block">
<div class="block-head"><h2>Picks</h2><p class="muted">Selections priced between -250 and +10,000 on our fair line, ranked by our probability.</p></div>
{''.join(pick_card(p, prefix="../", show_sport=False) for p in picks) if picks else '<p class="empty">No selection in this sport cleared the confidence and price filters. See <a href="../flagged.html">Flagged for Review</a> for the reason.</p>'}
</section>
<section class="block">
<div class="block-head"><h2>Every captured event</h2><p class="muted">Each row links to the OLBG page it was read from, and to the official source when one was matched.</p></div>
{'<div class="table-wrap"><table class="data"><thead><tr><th>Start (UTC)</th><th>Event</th><th>Markets</th><th>Official</th><th>Sources</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>' if rows else '<p class="empty">No OLBG listing for this sport in this capture.</p>'}
</section>
<section class="block">
<h2>Sources for this sport</h2>
<p>OLBG category hub: <a href="{e(sp["olbg_hub"])}" target="_blank" rel="noopener">{e(sp["olbg_hub"])}</a><br>
Official source: <a href="{e(sp["official_url"])}" target="_blank" rel="noopener">{e(sp["official_name"])}</a></p>
</section>
'''
    return page(sp["label"], "", body, desk["sports"], desk["built_utc"], prefix="../")


def build_matches(desk: dict) -> str:
    rows = []
    for ev in sorted(desk["events"], key=lambda x: (x["sport"], x.get("start_utc") or "")):
        markets = ev.get("markets") or {}
        sels = sum(len(v) for v in markets.values())
        rows.append(f'''<tr>
<td class="nowrap">{e(day(ev.get("start_utc")))}</td>
<td><a href="sports/{e(ev["sport"])}.html">{e(ev.get("sport_label") or ev["sport"])}</a></td>
<td>{e(ev.get("event_name"))}</td>
<td>{e(ev.get("competition") or "-")}</td>
<td class="num">{len(markets)}</td>
<td class="num">{sels}</td>
<td>{'<span class="ok">official</span>' if ev.get("official_confirmed") else '<span class="warn">board only</span>'}</td>
<td class="links"><a href="{e(ev["olbg_url"])}" target="_blank" rel="noopener">OLBG</a></td>
</tr>''')
    body = f'''
<section class="hero compact">
<p class="eyebrow">Matches</p>
<h1>Every upcoming event in scope</h1>
<p class="lede">{desk["summary"]["events"]} events captured across {desk["sport_count"]} sports, with {desk["summary"]["markets_captured"]} markets and {desk["summary"]["selections_priced"]} priced selections. Filter the table with the box below.</p>
<input id="filter" class="filter" type="search" placeholder="Filter by sport, event or competition…" aria-label="Filter matches">
</section>
<section class="block">
{'<div class="table-wrap"><table class="data" id="match-table"><thead><tr><th>Start (UTC)</th><th>Sport</th><th>Event</th><th>Competition</th><th>Markets</th><th>Selections</th><th>Official</th><th>Source</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>'}
</section>
'''
    return page("Matches", "matches", body, desk["sports"], desk["built_utc"])


def build_sources(desk: dict) -> str:
    blocks = []
    for sp in desk["sports"]:
        srcs = (desk.get("sources") or {}).get(sp["key"], [])
        rows = "".join(
            f'''<tr><td>{e(s["label"])}</td><td class="links"><a href="{e(s["url"])}" target="_blank" rel="noopener">{e(s["url"])}</a></td>
<td>{'<span class="ok">captured</span>' if s.get("ok") else '<span class="warn">blocked or empty</span>'}</td><td class="num">{s.get("chars", 0):,}</td></tr>''' for s in srcs)
        blocks.append(f'''<section class="block">
<h2>{e(sp["label"])}</h2>
<p class="muted">OLBG hub: <a href="{e(sp["olbg_hub"])}" target="_blank" rel="noopener">{e(sp["olbg_hub"])}</a> · Official: <a href="{e(sp["official_url"])}" target="_blank" rel="noopener">{e(sp["official_name"])}</a></p>
{'<div class="table-wrap"><table class="data"><thead><tr><th>Official source</th><th>URL</th><th>Capture</th><th>Bytes</th></tr></thead><tbody>' + rows + '</tbody></table></div>' if rows else '<p class="empty">No official source configured for this sport.</p>'}
</section>''')
    body = f'''
<section class="hero compact">
<p class="eyebrow">Sources</p>
<h1>Where every number comes from</h1>
<p class="lede">OLBG is the market of record for prices and listings. Official competition bodies supply fixture, table and result data. A source that returned nothing is listed as blocked rather than quietly dropped.</p>
</section>
{"".join(blocks)}
'''
    return page("Sources", "sources", body, desk["sports"], desk["built_utc"])


def build_method(desk: dict) -> str:
    body = f'''
<section class="hero compact">
<p class="eyebrow">Method</p>
<h1>How the prices and the prose are produced</h1>
<p class="lede">No price on this site is copied from a tipster. Every fair line is computed from the captured market board, and every sentence in a write-up is assembled from a captured field.</p>
</section>
<section class="block">
<h2>1. Reverse-engineering the OLBG board</h2>
<p>OLBG renders its tips feed server side. Each row carries the event name, an ISO start time, the selection, the market label, the price in decimal, fractional and American form, the tip record and a consensus percentage. Event pages add the rest of the market board: match winner, handicap or line, match total, set betting and period markets where the sport has them. This desk reads those fields directly; it does not infer a market from a page title.</p>
</section>
<section class="block">
<h2>2. Turning a price into a fair line</h2>
<p>A quoted price contains the bookmaker margin. We remove it with the power method: find the exponent k so that the sum of each implied probability raised to k equals one. That is stricter on longshots than proportional de-vigging and leaves the fair probabilities summing to exactly 100%.</p>
<pre class="code">p_i = 1 / decimal_i        solve  Σ p_i^k = 1        fair_i = p_i^k / Σ p_j^k</pre>
<p>Worked example from the captured board: a two-way market at 1.77 and 2.25 de-vigs to 56.1% and 43.9%, which is a fair line of -128 and +128 on a 1.77/2.25 quote.</p>
</section>
<section class="block">
<h2>3. Adding independent information</h2>
<p>Where an official feed exists (MLB, NHL, Formula 1) the fair price is nudged by official form: last-ten record, points percentage, scoring differential and a home-advantage term. The nudge is capped at 3.5 percentage points and the caveat is printed on each row. Where no official feed is reachable, the fair line is the de-margined board and the row is labelled "de-margined OLBG board" so the reader can see the difference.</p>
</section>
<section class="block">
<h2>4. Confidence bands and the price window</h2>
<div class="table-wrap"><table class="data">
<thead><tr><th>Band</th><th>Our fair chance</th><th>Typical fair price</th><th>What it means</th></tr></thead>
<tbody>
<tr><td>{conf_badge("high")}</td><td>70% and above</td><td>about -233 or shorter</td><td>A strong edge survives one bad result.</td></tr>
<tr><td>{conf_badge("medium")}</td><td>60% to 70%</td><td>about -175 to -233</td><td>Solid favourite with real risk of variance.</td></tr>
<tr><td>{conf_badge("low")}</td><td>below 60%</td><td>longer than -150</td><td>Published for completeness, not as a banker.</td></tr>
</tbody></table></div>
<p>Picks are restricted to fair prices between <strong>-250</strong> and <strong>+10,000</strong>, which is the band where a stake has a defensible shape. Anything shorter than -250 is excluded even when the chance is high, because the return does not compensate for the risk.</p>
</section>
<section class="block">
<h2>5. Writing the prediction</h2>
<p>Each write-up is at least thirty words and contains, in varying order: the fixture and venue, the two sides' official record and recent results where a feed exists, the relevant scoring numbers, the market price next to our fair price, and an explicit statement of the bet. A missing field produces no sentence rather than a guess, which is why some write-ups are shorter and carry a flag.</p>
</section>
<section class="block">
<h2>6. What the desk deliberately does not do</h2>
<ul>
<li>It does not restate a tipster's reasoning as its own.</li>
<li>It does not fill an injury or lineup gap with an inference; unavailable stays blank and is flagged.</li>
<li>It does not present a market-anchored line as an independent rating.</li>
<li>It does not publish a pick outside the price window, however confident the board looks.</li>
</ul>
</section>
'''
    return page("Method", "method", body, desk["sports"], desk["built_utc"])


def build_flagged(desk: dict) -> str:
    s = desk["summary"]
    sports = desk["sports"]
    no_pick = [x for x in sports if x["picks"] == 0]
    no_events = [x for x in sports if x["events"] == 0]
    thin = [x for x in sports if 0 < x["picks"] < 5]
    no_official = [x for x in sports if x["events"] and not x["official_confirmed"]]
    pick_flags = [p for p in desk["picks"] if p.get("flags")]
    blocked = []
    for sport, rows in (desk.get("sources") or {}).items():
        for r in rows:
            if not r.get("ok"):
                blocked.append((sport, r))
    rows = "".join(
        f'''<tr><td>{e(p["sport_label"])}</td><td>{e(p["event_name"])}</td><td>{e(p["selection"])}</td>
<td>{e(p["market"])}</td><td>{e("; ".join(p["flags"]))}</td>
<td class="links"><a href="{e(p["olbg_url"])}" target="_blank" rel="noopener">OLBG</a></td></tr>''' for p in pick_flags)
    label_of = {x["key"]: x["label"] for x in sports}
    src_rows = "".join(
        f'''<tr><td>{e(label_of.get(sp, sp))}</td><td>{e(r["label"])}</td><td class="links"><a href="{e(r["url"])}" target="_blank" rel="noopener">{e(r["url"])}</a></td><td>Returned no usable payload at capture.</td></tr>'''
        for sp, r in blocked)
    body = f'''
<section class="hero compact">
<p class="eyebrow">Flagged for review</p>
<h1>Gaps, caveats and anything unconfirmed</h1>
<p class="lede">Nothing here is hidden or silently smoothed over. Each item below either lacks an official source, falls outside the published price window, or is a sport where this capture could not produce the target number of picks.</p>
</section>
<section class="block">
<h2>Sports with no qualifying pick ({len(no_pick)})</h2>
{'<ul class="flag-list">' + "".join(f'<li><strong>{e(x["label"])}</strong> — {plural(x["events"], "event")} captured, {plural(x["listings"], "listing")}. ' + ('OLBG returned its literal "No tips found." message and carried no event link on the category page, so no market could be priced. ' if x["events"] == 0 else 'Listings existed but every selection fell outside the -250 to +10,000 fair-price window or below the chance floor. ') + f'<a href="sports/{x["key"]}.html">Sport page</a> · <a href="{e(x["olbg_hub"])}" target="_blank" rel="noopener">OLBG hub</a></li>' for x in no_pick) + '</ul>' if no_pick else '<p class="empty">None.</p>'}
</section>
<section class="block">
<h2>Sports below the five-pick target ({len(thin)})</h2>
{'<ul class="flag-list">' + "".join(f'<li><strong>{e(x["label"])}</strong> — {x["picks"]} picks from {plural(x["events"], "event")}. <a href="sports/{x["key"]}.html">Sport page</a></li>' for x in thin) + '</ul>' if thin else '<p class="empty">None.</p>'}
</section>
<section class="block">
<h2>Sports with no official fixture crosswalk ({len(no_official)})</h2>
<p>For these sports the picks are priced from the de-margined OLBG board only. No official form table, injury report or lineup was reachable, so the write-ups deliberately avoid those claims.</p>
{'<ul class="flag-list">' + "".join(f'<li><strong>{e(x["label"])}</strong> — {x["events"]} events, {x["picks"]} picks, 0 crosswalked.</li>' for x in no_official) + '</ul>' if no_official else '<p class="empty">None.</p>'}
</section>
<section class="block">
<h2>Individual picks carrying a flag ({len(pick_flags)})</h2>
{'<div class="table-wrap"><table class="data"><thead><tr><th>Sport</th><th>Event</th><th>Selection</th><th>Market</th><th>Flag</th><th>Source</th></tr></thead><tbody>' + rows + '</tbody></table></div>' if pick_flags else '<p class="empty">None.</p>'}
</section>
<section class="block">
<h2>Official sources that returned nothing ({len(blocked)})</h2>
<p>These URLs were requested during capture and did not return a usable payload. They are recorded so the gap is auditable rather than assumed away.</p>
{'<div class="table-wrap"><table class="data"><thead><tr><th>Sport</th><th>Source</th><th>URL</th><th>Result</th></tr></thead><tbody>' + src_rows + '</tbody></table></div>' if blocked else '<p class="empty">None.</p>'}
</section>
<section class="block">
<h2>Standing caveats</h2>
<ul class="flag-list">
<li><strong>Prices are a snapshot.</strong> OLBG prices are captured at build time and move continuously. The linked market is the authority, not this page.</li>
<li><strong>Coverage follows OLBG.</strong> OLBG lists events that carry tipster activity, not every fixture in world sport. A sport with no listing here is not a sport with no fixtures.</li>
<li><strong>Market-anchored lines.</strong> Where no official feed exists, the fair line is the de-margined board. That is a price calculation, not an independent ratings judgement, and it is labelled as such on every affected row.</li>
<li><strong>Injuries and lineups.</strong> Only published official information is used. Where none was published the write-up is silent on availability.</li>
<li><strong>Gaelic Sports.</strong> OLBG splits Gaelic Football and Hurling into separate categories. This desk reads the Gaelic Football category only.</li>
</ul>
</section>
'''
    return page("Flagged for Review", "flagged", body, desk["sports"], desk["built_utc"])


def main() -> int:
    desk = json.loads(DATA.read_text())
    ROOT.joinpath("sports").mkdir(exist_ok=True)
    (ROOT / "index.html").write_text(build_index(desk), encoding="utf-8")
    (ROOT / "picks.html").write_text(build_picks(desk), encoding="utf-8")
    (ROOT / "matches.html").write_text(build_matches(desk), encoding="utf-8")
    (ROOT / "sources.html").write_text(build_sources(desk), encoding="utf-8")
    (ROOT / "methodology.html").write_text(build_method(desk), encoding="utf-8")
    (ROOT / "flagged.html").write_text(build_flagged(desk), encoding="utf-8")
    for sp in desk["sports"]:
        (ROOT / "sports" / f"{sp['key']}.html").write_text(build_sport(desk, sp), encoding="utf-8")
    print("wrote index, picks, matches, sources, methodology, flagged and", len(desk["sports"]), "sport pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
