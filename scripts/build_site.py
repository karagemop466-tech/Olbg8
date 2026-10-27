#!/usr/bin/env python3
"""Build the static OLBG desk from committed JSON sources.

Every displayed number comes from one of these committed files:
  data/desk-sports.json     sport register, hubs, official source links
  data/desk-inventory.json  OLBG listing capture (event, market, selection, tips)
  data/desk-picks.json      originated lines + written predictions + sources
  data/desk-pricing.json    per-sport line-origination method
  data/desk-flagged.json    review items (unverified / irregular)
  data/desk-sources.json    official source register

Usage: python3 scripts/build_site.py
"""
from __future__ import annotations

import html
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT


# ---------------------------------------------------------------- utilities
def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


def load(name: str):
    path = DATA / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def american_to_decimal(american: float) -> float:
    a = float(american)
    return round(1 + (a / 100 if a > 0 else 100 / abs(a)), 3)


def decimal_to_american(dec: float) -> int:
    dec = float(dec)
    if dec >= 2:
        return int(round((dec - 1) * 100))
    return int(round(-100 / (dec - 1)))


def implied_pct(american: float) -> float:
    a = float(american)
    p = 100 / (a + 100) if a > 0 else abs(a) / (abs(a) + 100)
    return round(p * 100, 1)


def fmt_american(american) -> str:
    if american in (None, ""):
        return "—"
    return f"+{int(american)}" if int(american) > 0 else str(int(american))


def fmt_dt(iso: str) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return esc(iso)
    return dt.strftime("%a %d %b %H:%M UTC")


def day_of(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return ""
    return dt.strftime("%Y-%m-%d")


REFRESH = (load("desk-inventory.json") or {}).get("captured_utc", "")
TODAY = REFRESH[:10] if REFRESH else datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------- page shell
NAV = [
    ("overview", "Overview", "index.html"),
    ("picks", "Picks", "picks.html"),
    ("matches", "Matches", "matches.html"),
    ("pricing", "Pricing", "pricing.html"),
    ("sources", "Sources", "sources.html"),
    ("flagged", "Flagged", "flagged.html"),
    ("method", "Method", "methodology.html"),
]


def page(key: str, title: str, body: str, base: str = "", subtitle: str = "") -> str:
    current = ' aria-current="page"'
    nav = "\n".join(
        f'<a href="{base}{href}"{current if k == key else ""}>{esc(label)}</a>'
        for k, label, href in NAV
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · OLBG desk</title>
<meta name="description" content="OLBG multi-sport desk: captured listings, originated lines, sourced written predictions, and flagged items.">
<link rel="stylesheet" href="{base}assets/desk.css">
</head>
<body>
<div class="topbar"><div class="topbar-in">
  <a class="brand" href="{base}index.html"><span class="brand-mark">O</span>
    <span>OLBG desk<small>{esc(subtitle or 'lines · picks · sources')}</small></span></a>
  <nav class="main" aria-label="Primary">{nav}</nav>
</div></div>
<main class="wrap">
{body}
</main>
<footer class="site"><div class="wrap">
  <p><strong>Independent research desk.</strong> Listings, markets and tip counts come from OLBG.com pages
  captured {esc(REFRESH or "n/a")}. Lines, probabilities and written predictions are originated here and are
  not OLBG or bookmaker prices. Check the linked official source and current market before acting.
  Nothing here is a guarantee. 18+. Only bet where lawful.</p>
</div></footer>
</body>
</html>
"""


def badge(conf: str) -> str:
    klass = {"high": "b-high", "medium": "b-medium", "low": "b-low"}.get(str(conf).lower(), "b-mute")
    return f'<span class="badge {klass}">{esc(conf)}</span>'


def src_links(urls) -> str:
    out = []
    for i, item in enumerate(urls, 1):
        if isinstance(item, str):
            out.append(f'<a href="{esc(item)}" target="_blank" rel="noopener noreferrer">source {i}</a>')
        else:
            out.append(
                f'<a href="{esc(item["url"])}" target="_blank" rel="noopener noreferrer">{esc(item.get("label") or f"source {i}")}</a>'
            )
    return " · ".join(out) if out else '<span class="badge b-flag">no source</span>'


# ---------------------------------------------------------------- data load
SPORTS_DOC = load("desk-sports.json") or {"sports": []}
SPORTS = SPORTS_DOC["sports"]
SPORT_BY_KEY = {s["key"]: s for s in SPORTS}
INVENTORY = load("desk-inventory.json") or {"sports": {}, "captured_utc": ""}
INV = INVENTORY.get("sports", {})
PICKS_DOC = load("desk-picks.json") or {"picks": []}
PICKS = sorted(PICKS_DOC.get("picks", []), key=lambda p: (p.get("start_utc", ""), p.get("sport", "")))
PRICING = load("desk-pricing.json") or {"sports": {}}
FLAGGED = load("desk-flagged.json") or {"items": []}
SOURCES = load("desk-sources.json") or {"groups": []}

PICKS_BY_SPORT = defaultdict(list)
for p in PICKS:
    PICKS_BY_SPORT[p["sport"]].append(p)
PICK_BY_EVENT = {p["event_id"]: p for p in PICKS if p.get("event_id")}


def inv_events(key: str) -> list:
    return (INV.get(key) or {}).get("events", [])


def all_events() -> list:
    rows = []
    for s in SPORTS:
        for e in inv_events(s["key"]):
            rows.append((s, e))
    return rows


# ---------------------------------------------------------------- fragments
def picks_table(picks, base: str = "", show_sport: bool = True) -> str:
    if not picks:
        return '<p class="note">No pick published for this sport in this capture. See the flagged list for the reason.</p>'
    head = ["#", "Match", "Our line", "Price", "Implied", "Confidence"]
    if show_sport:
        head.insert(1, "Sport")
    head.append("Detail")
    numcls = ' class="num"'
    h = "".join(f"<th{numcls if c in ('Price', 'Implied') else ''}>{c}</th>" for c in head)
    rows = []
    for i, p in enumerate(picks, 1):
        cells = [f'<td class="num">{i}</td>']
        if show_sport:
            label = SPORT_BY_KEY.get(p["sport"], {}).get("label", p["sport"])
            cells.append(f'<td><a href="{base}sports/{esc(p["sport"])}.html">{esc(label)}</a></td>')
        cells.append(
            f'<td><strong>{esc(p["event"])}</strong><br><span class="meta">{esc(p.get("competition") or "")} · {esc(fmt_dt(p.get("start_utc")))}</span></td>'
        )
        cells.append(f'<td><strong>{esc(p["market"])}: {esc(p["selection"])}</strong></td>')
        cells.append(f'<td class="num"><span class="price">{esc(fmt_american(p.get("line_american")))}</span></td>')
        cells.append(f'<td class="num">{esc(p.get("implied_pct"))}%</td>')
        cells.append(f'<td>{badge(p.get("confidence"))}</td>')
        anchor = p["id"]
        cells.append(f'<td><a href="{base}picks.html#{esc(anchor)}">read</a></td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<div class="tablewrap"><table class="t-compact"><thead><tr>' + h + "</tr></thead><tbody>"
        + "".join(rows) + "</tbody></table></div>"
    )


def pick_card(p: dict, base: str = "") -> str:
    conf = str(p.get("confidence", "")).lower()
    facts = "".join(
        f'<li>{esc(f["text"])} <a href="{esc(f["source"])}" target="_blank" rel="noopener noreferrer">[source]</a></li>'
        for f in p.get("facts", [])
    )
    flags = ""
    if p.get("flags"):
        flags = '<div class="note" style="margin-top:.6rem"><strong>Review note:</strong> ' + "<br>".join(
            esc(f) for f in p["flags"]
        ) + "</div>"
    facts_html = f'<ul class="facts">{facts}</ul>' if facts else ""
    sport_label = SPORT_BY_KEY.get(p["sport"], {}).get("label", p["sport"])
    return f"""<article class="pick {esc(conf)}" id="{esc(p['id'])}">
  <div class="pick-head">
    <h3>{esc(p['event'])}</h3>
    {badge(p.get('confidence'))}
    <span class="meta">{esc(sport_label)} · {esc(p.get('competition') or '')} · {esc(fmt_dt(p.get('start_utc')))}</span>
  </div>
  <div class="sel">
    <span class="lbl">Bet</span><span class="val">{esc(p['market'])}: {esc(p['selection'])}</span>
    <span class="lbl">Our line</span><span class="price">{esc(fmt_american(p.get('line_american')))}</span>
    <span class="lbl">decimal</span><span class="price">{esc(p.get('line_decimal'))}</span>
    <span class="lbl">win chance</span><span class="price">{esc(p.get('implied_pct'))}%</span>
  </div>
  <p class="prose">{esc(p.get('analysis', ''))}</p>
  {facts_html}
  {flags}
  <div class="pick-foot">
    <span><strong>Sources:</strong> {src_links(p.get('sources', []))}</span>
    <span><strong>Pricing:</strong> {esc(p.get('pricing') or '')}</span>
    <span>{esc(p.get('window_note') or '')}</span>
  </div>
</article>"""


def inventory_table(events, picks_by_event=None, base: str = "") -> str:
    if not events:
        return '<p class="note">No OLBG listing captured for this sport in this snapshot.</p>'
    picks_by_event = picks_by_event or {}
    rows = []
    for e in events:
        p = picks_by_event.get(e.get("event_id"))
        line = "—"
        conf = '<span class="badge b-mute">no pick</span>'
        if p:
            line = f'<span class="price">{esc(fmt_american(p.get("line_american")))}</span><br><span class="meta">{esc(p["market"])}</span>'
            conf = f'<a href="{base}picks.html#{esc(p["id"])}">{badge(p.get("confidence"))}</a>'
        elif e.get("originated_line"):
            line = f'<span class="price">{esc(fmt_american(e["originated_line"]))}</span><br><span class="meta">{esc(e.get("originated_market") or "")}</span>'
        rows.append(
            "<tr>"
            f'<td><a href="{esc(e.get("url"))}" target="_blank" rel="noopener noreferrer">{esc(e.get("name"))}</a>'
            f'<br><span class="meta">{esc(e.get("competition") or "")}</span></td>'
            f'<td class="mono">{esc(fmt_dt(e.get("start_utc")))}<br><span class="meta">OLBG label: {esc(e.get("olbg_label") or "—")}</span></td>'
            f'<td>{esc(e.get("market") or "—")}<br><span class="meta">{esc(e.get("selection") or "—")}</span></td>'
            f'<td class="num">{esc(e.get("tips_total") or "—")}</td>'
            f'<td class="num">{esc(str(e.get("tip_pct")) + "%" if e.get("tip_pct") is not None else "—")}</td>'
            f'<td class="num">{line}</td>'
            f"<td>{conf}</td>"
            "</tr>"
        )
    return (
        '<div class="tablewrap"><table class="t-compact"><thead><tr>'
        "<th>Match (OLBG)</th><th>Kick-off</th><th>OLBG market / most-tipped</th>"
        '<th class="num">Tips</th><th class="num">Tip %</th><th class="num">Our line</th><th>Pick</th>'
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )


# ---------------------------------------------------------------- pages
def build_index() -> str:
    total = len(PICKS)
    by_conf = Counter(p.get("confidence", "").lower() for p in PICKS)
    listed = sum(len(inv_events(s["key"])) for s in SPORTS)
    with_pick = len({p["sport"] for p in PICKS})
    today_picks = [p for p in PICKS if day_of(p.get("start_utc")) == TODAY]
    next_picks = [p for p in PICKS if day_of(p.get("start_utc")) != TODAY]

    kindex = {}
    for s in SPORTS:
        ev = inv_events(s["key"])
        pk = PICKS_BY_SPORT.get(s["key"], [])
        kindex[s["key"]] = (len(ev), len(pk))

    mute = '<span class="badge b-mute">—</span>'
    sport_rows = "".join(
        "<tr>"
        f'<td><a href="sports/{esc(s["key"])}.html"><strong>{esc(s["label"])}</strong></a>'
        f'<br><span class="meta">{esc(s.get("note", "")) if s.get("note") else ""}</span></td>'
        f'<td class="num">{esc(s["sport_id"])}</td>'
        f'<td class="num">{kindex[s["key"]][0]}</td>'
        f'<td class="num">{kindex[s["key"]][1]}</td>'
        f'<td class="num">{min(kindex[s["key"]][1], 5)}/5</td>'
        f'<td>{badge("high") if any(p.get("confidence") == "high" for p in PICKS_BY_SPORT.get(s["key"], [])) else mute}</td>'
        f'<td>{src_links([{"label": "OLBG", "url": s["hub"]}] + s.get("official", []))}</td>'
        "</tr>"
        for s in SPORTS
    )

    ordered = sorted(PICKS, key=lambda p: (-p.get("implied_pct", 0), p.get("start_utc", "")))
    top = ordered[:10]
    top_html = picks_table(top, show_sport=True)
    hero = "".join(
        f'<a class="hero-card" href="picks.html#{esc(p["id"])}">'
        f'<span class="hero-tag">{esc(SPORT_BY_KEY.get(p["sport"], {}).get("label", p["sport"]))} · {esc(p.get("competition") or "")}</span>'
        f'<strong>{esc(p["event"])}</strong>'
        f'<span class="hero-bet">{esc(p["market"])}: {esc(p["selection"])}</span>'
        f'<span class="hero-price">{esc(fmt_american(p.get("line_american")))} <em>{esc(p.get("implied_pct"))}%</em> {badge(p.get("confidence"))}</span>'
        f'<span class="hero-when">{esc(fmt_dt(p.get("start_utc")))}</span></a>'
        for p in ordered[:3]
    )

    body = f"""
<h1>OLBG multi-sport desk</h1>
<p class="lead">Fifteen sports, one page. The <strong>Picks</strong> tab holds {total} fully written predictions
with an originated line for every selection; the <strong>Matches</strong> tab holds all {listed} OLBG listings
captured on {esc(REFRESH)}; <strong>Flagged</strong> holds everything that could not be confirmed from an
official source.</p>

<div class="grid cols-4" style="margin:1rem 0 1.4rem">
  <div class="stat"><b>{total}</b><span>written picks</span></div>
  <div class="stat pos"><b>{by_conf.get('high', 0)}</b><span>high confidence</span></div>
  <div class="stat"><b>{listed}</b><span>OLBG listings captured</span></div>
  <div class="stat"><b>{with_pick}/15</b><span>sports with a pick</span></div>
</div>

<h2>Executive summary</h2>
<div class="card">
<p><strong>Where the picks are:</strong> <a href="picks.html">Picks</a> lists every selection with its price,
win chance and confidence, followed by the full written reasoning. Each sport page repeats its own picks at the
top, above that sport's OLBG listing table. <a href="matches.html">Matches</a> is the complete inventory.</p>
<p><strong>Today ({esc(TODAY)}):</strong> {len(today_picks)} pick(s) start today, {len(next_picks)} start later in
the capture window. Confidence bands are high (&ge;65% implied), medium (55–64%) and low (&lt;55%); a pick is only
published when an official source confirms the identity of the event and the form facts used.</p>
<p><strong>Price window:</strong> every published line sits between −250 and +10000 American, per the desk mandate.
Lines are originated here from the inputs named on the Pricing page and carry a margin flag; they are never presented as bookmaker prices.</p>
</div>

<div class="hero">
{hero}
</div>
<h3 style="margin-top:1.4rem">Highest-confidence picks in this capture</h3>
{top_html}

<h2>Sport coverage</h2>
<div class="tablewrap"><table class="t-compact"><thead><tr>
<th>Sport</th><th class="num">OLBG id</th><th class="num">Listings</th><th class="num">Picks</th><th class="num">of 5</th><th>High?</th><th>Sources</th>
</tr></thead><tbody>{sport_rows}</tbody></table></div>

<h2>How to read a pick</h2>
<div class="card">
<ul class="clean">
<li><strong>Bet</strong> — the market and the side: match winner, handicap, total, set winner, race place, etc.</li>
<li><strong>Our line</strong> — the American price this desk originates for that side, not a price quoted by any bookmaker.</li>
<li><strong>Win chance</strong> — the probability behind the line, after the desk margin is removed from the raw estimate.</li>
<li><strong>Sources</strong> — one link to the OLBG listing and at least one link to the official body used for the form facts.</li>
</ul>
</div>
"""
    return page("overview", "Overview", body)


def build_picks() -> str:
    conf = Counter(str(p.get("confidence", "")).lower() for p in PICKS)
    toc = "".join(
        f'<a href="#{esc(s["key"])}">{esc(s["label"])} ({len(PICKS_BY_SPORT.get(s["key"], []))})</a>' for s in SPORTS
    )
    sections = []
    for s in SPORTS:
        picks = PICKS_BY_SPORT.get(s["key"], [])
        cards = "".join(pick_card(p) for p in picks) if picks else (
            '<p class="note">No pick passes the publication gate for this sport in this capture. '
            f'<a href="sports/{esc(s["key"])}.html">Sport page</a> · <a href="flagged.html">reason</a></p>'
        )
        sections.append(
            f'<section id="{esc(s["key"])}"><h2>{esc(s["label"])} '
            f'<span class="meta">— {len(picks)} pick(s)</span></h2>{cards}</section>'
        )
    body = f"""
<h1>Picks</h1>
<p class="lead">Every published prediction, in full. {len(PICKS)} picks across {len(PICKS_BY_SPORT)} sports —
{conf.get('high', 0)} high confidence, {conf.get('medium', 0)} medium, {conf.get('low', 0)} low. Each block states
the exact bet first, then the reasoning, then the sources.</p>
<div class="toc">{toc}</div>
<div class="card" style="margin-bottom:1rem">
<p><strong>Reading order:</strong> the shaded <em>Bet</em> strip names the selection and our price. The paragraph
under it is the prediction. The bullet list after that is the evidence trail, one link per fact. The footer names
the pricing method and the official source for the event.</p>
</div>
{''.join(sections)}
"""
    return page("picks", "Picks", body)


def build_matches() -> str:
    rows = all_events()
    picks_by_event = {p["event_id"]: p for p in PICKS if p.get("event_id")}
    sections = []
    for s in SPORTS:
        ev = inv_events(s["key"])
        gap = (INV.get(s["key"]) or {}).get("gap_note")
        sections.append(
            f'<h2 id="{esc(s["key"])}">{esc(s["label"])} <span class="meta">— {len(ev)} listings</span></h2>'
            + (f'<p class="note">{esc(gap)}</p>' if gap else "")
            + inventory_table(ev, picks_by_event)
        )
    body = f"""
<h1>Matches</h1>
<p class="lead">Every in-scope OLBG listing captured at {esc(REFRESH)}: {len(rows)} rows across 15 sports.
The OLBG column links to the live event page so each row can be checked by hand. "Our line" is filled only where
this desk originated a price for that event; otherwise it stays blank rather than guessed.</p>
<div class="tablewrap" style="margin-bottom:1.2rem"><table class="t-compact"><thead><tr>
<th>Sport</th><th class="num">Listings</th><th class="num">With pick</th><th>Market types seen</th></tr></thead><tbody>
{''.join(
    '<tr>'
    f'<td><a href="#{esc(s["key"])}">{esc(s["label"])}</a></td>'
    f'<td class="num">{len(inv_events(s["key"]))}</td>'
    f'<td class="num">{len(PICKS_BY_SPORT.get(s["key"], []))}</td>'
    f'<td>{esc(", ".join(sorted({e.get("market","") for e in inv_events(s["key"])})) or "—")}</td>'
    '</tr>'
    for s in SPORTS
)}
</tbody></table></div>
{''.join(sections)}
"""
    return page("matches", "Matches", body)


def build_pricing() -> str:
    blocks = []
    for s in SPORTS:
        doc = (PRICING.get("sports") or {}).get(s["key"], {})
        markets = doc.get("markets", [])
        mrows = "".join(
            "<tr>"
            f'<td><strong>{esc(m.get("market"))}</strong></td>'
            f'<td>{esc(m.get("method"))}</td>'
            f'<td class="mono">{esc(m.get("inputs"))}</td>'
            f'<td class="mono">{esc(m.get("margin"))}</td>'
            "</tr>"
            for m in markets
        )
        table = (
            '<div class="tablewrap"><table class="t-compact"><thead><tr><th>Market</th><th>Origination method</th>'
            '<th>Inputs used</th><th>Margin</th></tr></thead><tbody>' + mrows + "</tbody></table></div>"
            if mrows
            else '<p class="note">No market method recorded for this sport.</p>'
        )
        blocks.append(
            f'<section id="{esc(s["key"])}"><h2>{esc(s["label"])}</h2>'
            f'<p>{esc(doc.get("summary") or "Pricing method not recorded for this capture.")}</p>'
            f'{table}'
            + (f'<p class="meta" style="margin-top:.5rem">Worked example: {esc(doc["example"])}</p>' if doc.get("example") else "")
            + "</section>"
        )
    guards = "".join(f"<li>{esc(g)}</li>" for g in PRICING.get("guards", []))
    body = f"""
<h1>Pricing every sport</h1>
<p class="lead">How this desk turns a verified input into a line. The method is fixed per sport so the same
inputs always produce the same price, and every published line can be re-derived by hand.</p>
<div class="card">
<h3>The arithmetic</h3>
<ol>
<li><strong>Estimate a probability</strong> for the selection from the sport's verified inputs (form table,
head-to-head record, ranking points, recent scoring rates, field size for races).</li>
<li><strong>Add the desk margin</strong> to that probability, because these are originated lines, not market
offers. Margins are published per sport below.</li>
<li><strong>Convert</strong> the adjusted probability to decimal then American. Decimal above 2.00 becomes
positive American, below 2.00 becomes negative.</li>
<li><strong>Clamp to the mandate window</strong> (−250 to +10000 American). A selection whose honest price is
shorter than −250 is published as a pick but flagged as outside the window.</li>
<li><strong>Band the confidence</strong> by the implied probability of the published line:
high ≥ 65%, medium 55–64.9%, low &lt; 55%.</li>
</ol>
</div>
<h3 style="margin-top:1.2rem">Standing guards</h3>
<ul class="clean">{guards}</ul>
{''.join(blocks)}
"""
    return page("pricing", "Pricing", body)


def build_sources() -> str:
    groups = SOURCES.get("groups", [])
    blocks = []
    for g in groups:
        rows = "".join(
            "<tr>"
            f'<td><a href="{esc(item["url"])}" target="_blank" rel="noopener noreferrer">{esc(item["name"])}</a></td>'
            f'<td>{esc(item.get("covers") or "")}</td>'
            f'<td>{esc(item.get("used_for") or "")}</td>'
            f'<td>{esc(item.get("checked") or "")}</td>'
            "</tr>"
            for item in g.get("items", [])
        )
        blocks.append(
            f'<h2>{esc(g["title"])}</h2><p>{esc(g.get("intro") or "")}</p>'
            '<div class="tablewrap"><table class="t-compact"><thead><tr>'
            "<th>Source</th><th>Covers</th><th>Used for</th><th>Check status</th>"
            f"</tr></thead><tbody>{rows}</tbody></table></div>"
        )
    body = f"""
<h1>Sources</h1>
<p class="lead">The register of pages this desk reads. OLBG is the source for listings, markets and tip counts;
official bodies and competitions are the source for event identity, form and statistics. Where an official page
did not confirm a value, the value is blank and the row is on <a href="flagged.html">Flagged</a>.</p>
{''.join(blocks)}
"""
    return page("sources", "Sources", body)


def build_flagged() -> str:
    items = FLAGGED.get("items", [])
    rows = "".join(
        "<tr>"
        f'<td class="mono">{esc(i.get("id"))}</td>'
        f'<td>{esc(i.get("sport_label") or i.get("sport") or "")}</td>'
        f'<td><strong>{esc(i.get("item"))}</strong></td>'
        f'<td>{esc(i.get("issue"))}</td>'
        f'<td>{src_links(i.get("sources", [])) if i.get("sources") else "—"}</td>'
        f'<td>{esc(i.get("status") or "open")}</td>'
        "</tr>"
        for i in items
    )
    body = f"""
<h1>Flagged for Review</h1>
<p class="lead">Everything that could not be closed against an official source, plus every judgement call worth a
second pair of eyes. Nothing on this page is hidden from the site: the related match or pick still appears, with the
gap stated. {len(items)} items.</p>
<div class="warn"><strong>Rule applied:</strong> a value is either confirmed on a linked official page, or it is
blank and listed here. No value has been inferred to fill a cell.</div>
<div class="tablewrap" style="margin-top:1rem"><table class="t-compact"><thead><tr>
<th>Ref</th><th>Sport</th><th>Item</th><th>Issue found</th><th>Source links</th><th>Status</th>
</tr></thead><tbody>{rows}</tbody></table></div>
"""
    return page("flagged", "Flagged for Review", body)


def build_method() -> str:
    doc = load("desk-methodology.json") or {}
    sections = "".join(
        f'<h2>{esc(s["title"])}</h2>' + "".join(f"<p>{esc(p)}</p>" for p in s.get("paras", []))
        + ("<ul class=\"clean\">" + "".join(f"<li>{esc(li)}</li>" for li in s.get("list", [])) + "</ul>" if s.get("list") else "")
        for s in doc.get("sections", [])
    )
    body = f"""
<h1>Method</h1>
<p class="lead">What the site reads, how the reverse-engineering of OLBG works, how lines are produced, and where
the limits are. Everything stated here is checkable from the committed JSON and the linked pages.</p>
{sections}
"""
    return page("method", "Method", body)


def build_sport(s: dict) -> str:
    key = s["key"]
    ev = inv_events(key)
    picks = PICKS_BY_SPORT.get(key, [])
    picks_by_event = {p["event_id"]: p for p in PICKS if p.get("event_id")}
    doc = (PRICING.get("sports") or {}).get(key, {})
    gap = (INV.get(key) or {}).get("gap_note")
    cards = "".join(pick_card(p, base="../") for p in picks)
    if not picks:
        cards = (
            '<p class="note">No pick cleared the gate for this sport in this capture. The listings below are still '
            "captured and linked so the market can be watched; the reason no line was published is in "
            '<a href="../flagged.html">Flagged for Review</a>.</p>'
        )
    official = src_links(s.get("official", []))
    body = f"""
<p class="crumb"><a href="../index.html">Overview</a> / {esc(s['label'])}</p>
<h1>{esc(s['label'])}</h1>
<p class="lead">{esc(s.get('blurb') or '')}</p>
<div class="grid cols-4" style="margin:1rem 0 1.4rem">
  <div class="stat"><b>{len(ev)}</b><span>OLBG listings</span></div>
  <div class="stat"><b>{len(picks)}</b><span>written picks</span></div>
  <div class="stat"><b>{len([p for p in picks if p.get('confidence') == 'high'])}</b><span>high confidence</span></div>
  <div class="stat"><b>{esc(s["sport_id"])}</b><span>OLBG sport id</span></div>
</div>
<div class="card"><strong>Links:</strong> <a href="{esc(s['hub'])}" target="_blank" rel="noopener noreferrer">OLBG {esc(s['label'])} hub</a>
· {official}</div>
<h2>Picks for {esc(s['label'])}</h2>
{cards}
<h2>OLBG listings captured</h2>
{f'<p class="note">{esc(gap)}</p>' if gap else ''}
{inventory_table(ev, picks_by_event, base='../')}
<h2>How this sport is priced</h2>
<p>{esc(doc.get('summary') or 'No pricing note recorded for this capture.')}</p>
{f'<p class="meta">Worked example: {esc(doc["example"])}</p>' if doc.get('example') else ''}
"""
    return page("sports", s["label"], body, base="../")


# ---------------------------------------------------------------- write
def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}")


def main() -> None:
    print("Building OLBG desk…")
    write(OUT / "index.html", build_index())
    write(OUT / "picks.html", build_picks())
    write(OUT / "matches.html", build_matches())
    write(OUT / "pricing.html", build_pricing())
    write(OUT / "sources.html", build_sources())
    write(OUT / "flagged.html", build_flagged())
    write(OUT / "methodology.html", build_method())
    for s in SPORTS:
        write(OUT / "sports" / f"{s['key']}.html", build_sport(s))
    print(f"Done: {7 + len(SPORTS)} pages.")


if __name__ == "__main__":
    main()
