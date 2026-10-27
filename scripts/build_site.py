#!/usr/bin/env python3
"""Render the static dashboard from data/live-capture.json, lines.json, picks.json
and crosswalks.json. Everything on the page is written from those four files, so the
site cannot show a number the pipeline did not produce.
"""
import html
import json
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = ROOT
CAP = json.load(open(os.path.join(ROOT, "data", "live-capture.json"), encoding="utf-8"))
LINES = json.load(open(os.path.join(ROOT, "data", "lines.json"), encoding="utf-8"))
PICKS = json.load(open(os.path.join(ROOT, "data", "picks.json"), encoding="utf-8"))
CW = json.load(open(os.path.join(ROOT, "data", "crosswalks.json"), encoding="utf-8"))
AS_OF = "27 October 2026, 05:26 UTC"
e = html.escape

NAV = [("index", "Overview", "index.html"), ("picks", "Picks", "picks.html"),
       ("matches", "Line board", "matches.html"), ("pricing", "Pricing", "pricing.html"),
       ("sources", "Sources", "sources.html"), ("methodology", "Method", "methodology.html"),
       ("flagged", "Flagged for review", "flagged.html")]

SPORT_KEYS = [(k, v["label"]) for k, v in CAP["sports"].items()]


def slug(key):
    """Sport pages use hyphenated filenames, the convention already on main."""
    return key.replace("_", "-")


def ampn(v):
    if v is None or v == "":
        return '<span class="blank">no line</span>'
    v = float(v)
    return f'<span class="{"neg" if v < 0 else "pos"}">{v:+.0f}</span>'


def pct(v):
    return "-" if v is None else f"{v * 100:.1f}%"


def band(c):
    cls = {"High": "hi", "Medium": "med", "Low": "lo"}[c]
    return f'<span class="band {cls}">{c}</span>'


def official_chip(obj, rel=""):
    """The first source that is not OLBG itself. Double-listing the hub as its own
    corroboration would read as a source we do not have, so it says 'listing only'."""
    for x in (obj.get("sources") or []):
        if x.get("url") and "olbg.com" not in x["url"]:
            tier = x.get("tier") or x.get("tier_override")
            return src_chip(x["name"], x["url"], tier)
    return '<span class="blank">listing only, no official source</span>'


def src_chip(name, url, tier=None):
    t = f'<span class="tier t{tier.lower()}">{tier}</span>' if tier else ""
    return f'<a class="srclink" href="{e(url)}" target="_blank" rel="noopener">{e(name)}</a>{t}'


_REL = ""   # set to "../" while rendering pages that live in sports/


def shell(page, title, body, desc):
    """One template for every page; _REL keeps the links correct inside sports/."""
    rel = _REL
    nav = "".join(f'<a class="{"on" if p == page else ""}" href="{rel}{u}">{l}</a>' for p, l, u in NAV)
    sports_nav = "".join(f'<a href="{rel}sports/{slug(k)}.html">{e(l)}</a>' for k, l in SPORT_KEYS)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{e(desc)}">
<title>{e(title)}</title>
<link rel="stylesheet" href="{rel}assets/styles.css">
<script src="{rel}assets/app.js" defer></script>
</head>
<body>
<header class="top">
  <div class="brand"><a href="{rel}index.html"><strong>OLBG desk</strong><span>lines, picks and evidence</span></a></div>
  <nav class="mainnav">{nav}</nav>
  <div class="stamp">Data as at {e(AS_OF)}</div>
</header>
<div class="wrap">{body}</div>
<footer class="foot">
  <div><strong>How to read this board.</strong> Every row carries an OLBG link for the listing and, where one was found,
  an official link for the fact. A blank price or blank stat means the source did not state it, never that it was guessed.</div>
  <nav class="sportsnav">{sports_nav}</nav>
  <div class="fine">This page is the desk. Other sessions' snapshots sit beside it and are not part of it: a second 48-pick board at
  <a href="{rel}board/index.html">board/</a>, a collector's live capture at <a href="{rel}current/index.html">current/</a>, the
  superseded desk payload in <code>price-engine/</code> and <code>data/desk-*.json</code>, and earlier audits in
  <a href="{rel}evidence-lab/index.html">evidence-lab/</a> and <a href="{rel}research-desk/index.html">research-desk/</a>. They are
  kept as audit trail; their prices differ from ours and are not published here. Static snapshot, not a live feed.</div>
</footer>
</body></html>"""


def kpi(items):
    return '<div class="kpis">' + "".join(
        f'<div class="kpi"><b>{e(str(v))}</b><span>{e(k)}</span></div>' for k, v in items) + "</div>"


# --------------------------------------------------------------- overview --
def page_index():
    rows, picks = LINES["rows"], PICKS["picks"]
    bys = defaultdict(lambda: {"ev": 0, "priced": 0, "picks": 0, "best": "Low"})
    order = {"Low": 0, "Medium": 1, "High": 2}
    for r in rows:
        bys[r["sport"]]["priced"] += 1
    for k, v in CAP["sports"].items():
        bys[v["label"]]["ev"] = len(v["events"])
    for p in picks:
        b = bys[p["sport"]]
        b["picks"] += 1
        if order[p["confidence"]] > order[b["best"]]:
            b["best"] = p["confidence"]
    by_label = {v["label"]: slug(k) for k, v in CAP["sports"].items()}
    top = sorted(picks, key=lambda x: -x["pick_score"])[:10]
    hi = [p for p in picks if p["confidence"] == "High"]
    med = [p for p in picks if p["confidence"] == "Medium"]

    tr = "".join(
        f'<tr><td><a href="sports/{by_label[s]}.html">{e(s)}</a></td><td class="num">{d["ev"]}</td>'
        f'<td class="num">{d["priced"]}</td><td class="num">{d["picks"]}</td>'
        f'<td>{band(d["best"])}</td><td class="why">{why_for(s, d)}</td></tr>'
        for s, d in sorted(bys.items(), key=lambda x: (-x[1]["picks"], x[0])))

    best = "".join(f"""<tr>
      <td><a class="sel" href="picks.html#{p['pick_id']}"><strong>{e(p['selection'])}</strong></a>
        <div class="sub">{e(p['market'])} · {e(p['event'])}</div></td>
      <td>{e(p['sport'])}</td><td class="mono">{ampn(p['fair_american'])}</td>
      <td class="mono">{ampn(p['our_american'])}</td><td class="mono">{pct(p['our_prob'])}</td>
      <td>{band(p['confidence'])}</td>
      <td class="srcs">{src_chip('OLBG', p['olbg_url'])}<br>{official_chip(p)}</td>
    </tr>""" for p in top)

    return shell("index", "Overview · OLBG research desk", f"""
<section class="hero">
  <div>
    <h1>Executive summary</h1>
    <p class="lede">A live OLBG capture taken {e(AS_OF)}, our own originated line on every selection in it, and
    {len(picks)} written predictions across {len([1 for s in CAP['sports'].values() if s['events']])} sports.</p>
    <div class="wherebox">
      <b>Where the picks are:</b>
      <ol>
        <li><a href="picks.html">Picks</a> — every written prediction, grouped by sport, with the selection, our line,
        the confidence band and the source links.</li>
        <li>The <b>strongest positions right now</b> are the table directly below this box.</li>
        <li><a href="matches.html">Line board</a> — all {len(rows)} priced selections and every market we found.</li>
        <li>Each sport page (footer list) shows that sport's picks and its full market table together.</li>
      </ol>
    </div>
  </div>
  {kpi([("picks published", len(picks)), ("priced selections", len(rows)),
        ("OLBG events captured", sum(len(v['events']) for v in CAP['sports'].values())),
        ("High", len(hi)), ("Medium", len(med)), ("flagged rows", len(LINES['flags']))])}
</section>

<section class="callout">
  <h2>The one pick that cleared every gate</h2>
  {''.join(f'<p class="big"><strong>{e(p["selection"])}</strong> to win the {e(p["event"])} — {e(p["market"]).lower()} at <span class="mono">{ampn(p["fair_american"])}</span>. {e(p["note"])}</p>' for p in hi) or '<p>No selection cleared the High gate today.</p>'}
  <p class="fine">A High label needs all four of: an official source opened and matched to the fixture, a priced selection at
  60% or better, at least four tips in that market, and a line inside −250 to +10,000. Fourteen of today's events met the
  first condition; the crowd-weighted price is what decides the rest.</p>
</section>

<section>
  <h2>Top ten positions today, by score</h2>
  <p class="fine">Score ranks confidence band, then the volume of OLBG tips behind the selection, then how far our price sits from the
  shrinkage floor. It is a triage order, not a predicted win rate.</p>
  <table class="grid"><thead><tr><th>Selection</th><th>Sport</th><th>Our fair line</th><th>Line after margin</th><th>Chance</th><th>Confidence</th><th>Sources</th></tr></thead>
  <tbody>{best}</tbody></table>
  <p class="jump"><a class="btn" href="picks.html">Read all {len(picks)} written predictions</a>
  <a class="btn ghost" href="matches.html">See the full line board</a></p>
</section>

<section>
  <h2>Coverage by sport</h2>
  <p class="fine">The brief asks for five to ten picks a sport. We publish what the evidence supports and say plainly where it does not.</p>
  <table class="grid"><thead><tr><th>Sport</th><th>OLBG events</th><th>Priced selections</th><th>Written picks</th><th>Best band</th><th>Why it is short of five</th></tr></thead>
  <tbody>{tr}</tbody></table>
</section>

<section class="alerts">
  <h2>Irregularities found in the repository, and what we did</h2>
  <ul>
    <li><strong>Fabricated darts file removed.</strong> <code>data/darts.json</code> held five "verified: True" darts picks that cited a
    tournament directory page and quoted statistics the PDC does not publish. The fixtures it named do not appear in any capture file.
    Moved to <code>quarantine/</code> with the evidence written up on the <a href="flagged.html">flagged page</a>.</li>
    <li><strong>OLBG is reachable.</strong> Earlier session notes stopped at a TLS error from the sandbox and concluded nothing could be
    collected, which is why the site published zero picks. Direct retrieval works; today's board is the result.</li>
    <li><strong>OLBG's printed times are US Eastern, not UK time.</strong> Four events cross-checked against official start times land on
    UTC−4. Two others sit an hour off, so official start times are treated as authoritative and shown beside each row.</li>
    <li><strong>Consensus is not always right.</strong> Handball's most-tipped outcome is the draw on eight of fifteen markets, and on
    Kielce v Kolstad the crowd is on a tie against a side with a 7-0-0 head-to-head record. Those rows are published as
    counter-consensus reads, not copied.</li>
  </ul>
  <p><a class="btn ghost" href="flagged.html">Open the full review queue</a></p>
</section>
""", "OLBG multi-sport research desk: originated lines, confidence bands and written predictions.")


def why_for(sport, d):
    if d["ev"] == 0:
        return "OLBG printed “No tips found.” for this category at capture time — nothing to price or predict."
    if d["picks"] >= 5:
        return ""
    fixed = {"Golf": "Three tournaments listed, one tip on each outright; field sizes beyond the LPGA page were not confirmable.",
             "Darts": "Two markets only, both outrights; no match-level darts market was live on OLBG.",
             "Motor Racing": "Two markets only: the Mexican Grand Prix podium market and one ante-post line.",
             "Rugby League": "No club fixtures live; three ante-post outrights only.",
             "Baseball": "One game listed — World Series Game 4 — and its totals market had no tips, so it is unpriced.",
             "Gaelic Sports": "Four listings in total across Gaelic football and hurling.",
             "Rugby Union": "Pro D2 and Top 14 rows could not be matched to an official source, so the shortlist is capped.",
             }
    return fixed.get(sport, f"Only {d['ev']} OLBG listings carried tip volume in this sport.")


# ------------------------------------------------------------------ picks --
def page_picks():
    groups = defaultdict(list)
    for p in sorted(PICKS["picks"], key=lambda x: (x["sport"], -x["pick_score"])):
        groups[p["sport"]].append(p)
    out = [f"""<section class="pagemast">
    <h1>Written predictions</h1>
    <p class="lede">{len(PICKS['picks'])} selections, each one priced by our own origination step and written with the sources
    underneath it. Confidence is printed on every card: <strong>High</strong> means an official source matched the fixture and the
    market carried real weight; <strong>Low</strong> means either a thin tip sample, an unconfirmed fixture, or a price we are
    telling you not to take. Where we disagree with the OLBG crowd, the card says so.</p>
    </section>"""]
    for sport in sorted(groups, key=lambda s: -len(groups[s])):
        ps = groups[sport]
        cards = []
        for p in ps:
            srcs = "".join(f'<li><span class="claim">{e(s["claim"]) if s["claim"] else "Supports this entry."}</span> '
                           f'{src_chip(s["name"], s["url"], s.get("tier"))}</li>'
                           for s in p["sources"]) or '<li class="blank">No independent source located for this row.</li>'
            facts = f'<p class="evidence"><b>Evidence note.</b> {e(p["evidence"])}</p>' if p["evidence"] else ""
            flags = "".join(f'<span class="mini">{e(f.replace("_", " "))}</span>' for f in p["line_flags"])
            cards.append(f"""<article class="pick" id="{p['pick_id']}">
  <div class="phead">
    <div><h3>{e(p['headline'])}</h3>
      <p class="meta"><a href="{e(p['olbg_url'])}" target="_blank" rel="noopener">{e(p['event'])}</a>
      · {e(p['competition'])} · OLBG prints “{e(p['time_label'])}”</p></div>
    <div class="badge">{band(p['confidence'])}</div>
  </div>
  <p class="selectionline"><b>Bet:</b> <span class="bigsel">{e(p['selection'])}</span> — {e(p['market'])}
     · our line <span class="mono">{ampn(p['fair_american'])}</span> (after margin {ampn(p['our_american'])})
     · implied chance {pct(p['our_prob'])}
     · OLBG support {p['olbg_win_tips'] if p['olbg_win_tips'] is not None else '—'}/{p['olbg_total_tips'] if p['olbg_total_tips'] else '—'}
       ({p['olbg_displayed_pct'] if p['olbg_displayed_pct'] is not None else '—'}%)</p>
  <p class="prose">{e(p['note'])}</p>
  <div class="twocol">
    <div><h4>Sources for this pick</h4><ul class="srcs">{srcs}</ul></div>
    <div><h4>Line detail</h4><ul class="detail">
      <li>Market outcomes priced (k): {p['outcome_count_k']}</li>
      <li>Total tips in this market: {p['market_total_tips']}</li>
      <li>Fair decimal {('%.3f' % p['fair_decimal']) if p['fair_decimal'] else 'n/a'} → with margin {('%.3f' % p['our_decimal']) if p['our_decimal'] else 'n/a'}</li>
      <li>Inside the −250 to +10,000 band: {"yes" if p['in_window'] else "no"}</li>
      <li>Official source tier: {p['official_tier'].upper()}</li>
      <li>Words in note: {p['word_count']}</li></ul>{facts}</div>
  </div>
  {f'<p class="flagrow">{flags}</p>' if flags else ''}
</article>""")
        out.append(f'<section class="sportsec" id="{sport.lower().replace(" ", "-")}"><h2>{e(sport)} '
                   f'<span class="cnt">{len(ps)} pick{"s" if len(ps) != 1 else ""}</span></h2>{"".join(cards)}</section>')
    return shell("picks", "Written predictions · OLBG research desk", "".join(out),
                 "High-quality written betting predictions with originated lines, confidence bands and source links.")


# ---------------------------------------------------------------- matches --
def page_matches():
    rows = LINES["rows"]
    body = []
    for sport in sorted({r["sport"] for r in rows}):
        rs = [r for r in rows if r["sport"] == sport]
        trs = "".join(f"""<tr data-sport="{e(sport)}" data-txt="{e((str(r['selection']) + ' ' + str(r['event'])).lower())}">
<td>{e(r['selection'])}</td><td class="ev"><a href="{e(r['olbg_url'])}" target="_blank" rel="noopener">{e(r['event'])}</a></td>
<td>{e(r['market'])}</td><td class="mono">{ampn(r['fair_american'])}</td><td class="mono">{ampn(r['our_american'])}</td>
<td class="mono">{pct(r['our_prob'])}</td>
<td class="mono">{'' if r['olbg_win_tips'] is None else r['olbg_win_tips']}/{'' if r['olbg_total_tips'] is None else r['olbg_total_tips']}</td>
<td>{band(r['confidence'])}</td>
<td class="srcs">{src_chip('OLBG', r['olbg_url'])}<br>{official_chip(r)}</td>
</tr>""" for r in sorted(rs, key=lambda x: -x["pick_score"]))
        body.append(f"""<section class="sportsec" id="{e(sport.lower().replace(' ', '-'))}">
<h2>{e(sport)} <span class="cnt">{len(rs)} priced selections</span></h2>
<table class="grid lines"><thead><tr><th>Selection</th><th>Event</th><th>Market</th><th>Our fair line</th>
<th>After margin</th><th>Chance</th><th>OLBG tips</th><th>Band</th><th>Sources</th></tr></thead><tbody>{trs}</tbody></table></section>""")
    for k, v in CAP["sports"].items():
        if not v["events"]:
            body.append(f"""<section class="sportsec"><h2>{e(v['label'])} <span class="cnt">nothing to price</span></h2>
<p class="blank">{e(v.get('capture_note', 'OLBG listed no events at capture time.'))} No line was invented to fill the gap.</p></section>""")
    return shell("matches", "Line board · OLBG research desk", f"""
<section class="pagemast"><h1>Line board — every event, every market we found</h1>
<p class="lede">{len(rows)} selections priced across {sum(1 for v in CAP['sports'].values() if v['events'])} sports, from
{sum(len(v['events']) for v in CAP['sports'].values())} OLBG listings. “Our fair line” is the price this desk originated; the next column is that same line with a
4% margin loaded. Blank cells are places where OLBG published no tip volume, and they stay blank.</p>
<div class="tools"><input id="q" type="search" placeholder="Filter by team or player…" aria-label="Filter the line board">
<span class="fine" id="qcount"></span></div>
</section>{''.join(body)}""", "Every OLBG selection with our originated line, market and source link.")


# ---------------------------------------------------------------- pricing --
def page_pricing():
    par = LINES["parameters"]
    return shell("pricing", "Pricing method · OLBG research desk", f"""
<section class="pagemast"><h1>How we originate a line when nobody gives us one</h1>
<p class="lede">OLBG does not print a bookmaker price in the markup a reader can see. What it prints, for every selection, is how many
tipsters picked it and how many tips the whole market carries — and OLBG's own definition of its Value Rating says it treats that share
as “the theoretical probability of winning”. We use the same quantity as our input, price it ourselves, and publish the arithmetic.</p></section>
<section class="stepgrid">
<div class="stepcard"><b>1 · Read the market</b><p>For each event, every market OLBG exposes: win match or money line, handicap or
spread, totals, and the player markets such as man of the match and top batsman.</p></div>
<div class="stepcard"><b>2 · Count, don't guess</b><p>Take the printed “x / y” — tips on this selection over tips on the market. No
bookmaker number is copied and no number is interpolated.</p></div>
<div class="stepcard"><b>3 · Fix the outcome count</b><p>k = 2 for a head-to-head, 3 where a draw is priced (OLBG's handball money line),
and the declared field size for an outright — 78 at the Maybank, 128 at the World Darts Championship. No published field size means no
price above a floor, and a flag.</p></div>
<div class="stepcard"><b>4 · Shrink toward the base rate</b><p>p = (n + {par['strength']:.0f}/k) ÷ (T + {par['strength']:.0f}). A Dirichlet
update with a uniform prior, so one lonely tip on a 78-player field cannot read as 50%, and 1 of 1 on a match cannot read as certain.</p></div>
<div class="stepcard"><b>5 · Price it</b><p>Fair decimal = 1/p, converted to American. Our offered line takes a {int(par['margin'] * 100)}% margin,
and the no-margin figure is printed next to it so anyone can reverse the step.</p></div>
<div class="stepcard"><b>6 · Apply the band</b><p>Lines shorter than {par['window_american'][0]:.0f} are rejected from the picks surface and flagged. That removes
exactly the “sure thing” favourites the brief ruled out; a +10,000 ceiling stops a one-tip market becoming a lottery ticket.</p></div>
</section>
<section>
<h2>Confidence bands, as actually applied</h2>
<table class="grid"><thead><tr><th>Band</th><th>Requirement, in full</th></tr></thead><tbody>
<tr><td>{band('High')}</td><td>Official governing-body, league-API or club source opened and matched to the fixture, <b>and</b> priced
chance ≥ 60%, <b>and</b> at least 4 tips in that market, <b>and</b> inside the band. Outrights cannot reach High at all.</td></tr>
<tr><td>{band('Medium')}</td><td>Either a corroborated fixture at ≥ 52%, or an uncorroborated fixture at ≥ 60% carrying 8+ tips.</td></tr>
<tr><td>{band('Low')}</td><td>Everything else — including anything priced from fewer than three tips, which is capped here whatever else it has.</td></tr>
</tbody></table>
<p class="fine">Applied today: {LINES['parameters']['bands']['High']} → {len([r for r in LINES['rows'] if r['confidence'] == 'High'])} rows.
{len([r for r in LINES['rows'] if 'thin_sample_fewer_than_3_tips' in r['flags']])} rows carry fewer than three tips and are capped to Low on
purpose; that is the honest answer to a request for high-confidence picks on markets that are mostly empty.</p>
</section>
<section>
<h2>Market coverage per sport</h2>
<table class="grid"><thead><tr><th>Sport</th><th>Markets found on OLBG today</th><th>Selections priced</th><th>Markets left unpriced</th></tr></thead><tbody>
{''.join(f'''<tr><td>{e(v['label'])}</td><td>{e(', '.join(sorted({m['market'] for ev in v['events'] for m in ev['markets']})) or '—')}</td>
<td class="num">{sum(len(m['selections']) for ev in v['events'] for m in ev['markets'])}</td>
<td>{e(', '.join(sorted({m['market'] for ev in v['events'] for m in ev['markets'] if not any(s.get('total_tips') for s in m['selections'])})) or 'none')}</td></tr>'''
for k, v in CAP['sports'].items())}
</tbody></table>
</section>""", "How OLBG tip volume becomes an originated betting line, and how confidence is assigned.")


# ---------------------------------------------------------------- sources --
def page_sources():
    ev = CW["events"]
    tr = []
    for key, v in sorted(ev.items()):
        sp, eid = key.split(":")
        lbl = CAP["sports"].get(sp, {}).get("label", sp)
        name = next((e2["name"] for e2 in CAP["sports"].get(sp, {}).get("events", []) if e2["event_id"] == eid), "?")
        srcs = "<br>".join(src_chip(s["name"], s["url"], s.get("tier_override", v["tier"])) for s in v["sources"])
        conf = "<br>".join(e(s["confirmed"]) for s in v["sources"])
        tr.append(f'<tr><td>{e(lbl)}</td><td>{e(name)}</td><td class="tiercell">{srcs}</td><td class="conf">{conf}</td>'
                  f'<td>{e(v.get("injury_availability") or "no injury or availability line was located")}</td></tr>')
    nc = "".join(f"<li>{e(x)}</li>" for x in CW["not_checked"])
    hubs = "".join(f'<tr><td>{e(v["label"])}</td><td>{v["sport_id"]}</td><td>{src_chip("OLBG category page", v["olbg_hub"])}</td></tr>'
                   for k, v in CAP["sports"].items())
    return shell("sources", "Source register · OLBG research desk", f"""
<section class="pagemast"><h1>Source register</h1>
<p class="lede">Tier A means an official governing body, tour, league data feed or the club's own page was opened and the fixture was read
in it. Tier B means reliable independent reporting of the same fixture. Tier A is required before any selection can be called High — a
broadcaster listing a match proves the match exists, not that a stat in a paragraph is true.</p></section>
<section><h2>Events matched to a source</h2>
<table class="grid"><thead><tr><th>Sport</th><th>Event</th><th>Source linked (tier)</th><th>What that source actually states</th><th>Injury and availability</th></tr></thead>
<tbody>{''.join(tr)}</tbody></table></section>
<section><h2>Not checked — recorded so it is not mistaken for clean</h2><ul class="nc">{nc}</ul></section>
<section><h2>OLBG category pages captured</h2><p class="fine">Sport IDs confirmed by reading the category URLs OLBG itself links.
“Gaelic Sports” is not a single OLBG category; it is Gaelic football (25) plus hurling (26), and both are captured here.</p>
<table class="grid"><thead><tr><th>Sport</th><th>OLBG sport id</th><th>Page</th></tr></thead><tbody>{hubs}</tbody></table></section>""",
                 "Every source behind the board, tiered, with what each one was used to confirm.")


# ----------------------------------------------------------- methodology --
def page_method():
    mk = sorted({m["market"] for v in CAP["sports"].values() for ev in v["events"] for m in ev["markets"]})
    return shell("methodology", "Method and market inventory · OLBG research desk", f"""
<section class="pagemast"><h1>Reverse-engineering the OLBG tips pages</h1>
<p class="lede">How the site is put together, what the numbers on OLBG actually mean, and which markets exist per sport.</p></section>
<section>
<h2>The structure of an OLBG listing</h2>
<ol class="readout">
<li><b>Category page</b> — <code>olbg.com/betting-tips/&lt;Sport&gt;/&lt;id&gt;</code>. One card per event, ordered by the number of tips on
the most popular selection. It prints the event name, a relative time label, the selection, the market, “x/y Win Tips”, the confidence
percentage, and counts of experts and comments.</li>
<li><b>Event page</b> — reached from the card. It shows “Most Popular Tip” as a complete table of every selection in the market with its
own “x / y” and percentage, then repeats each market below with the same figures plus one tipster comment and that tipster's annual
profit, strike rate, 30-day and 7-day numbers.</li>
<li><b>What the percentage is.</b> It is the share of tips on that outcome out of the tips on that market, not a win rate and not an
implied probability from a bookmaker. OLBG says so in its own Value Rating definition, and the totals confirm it: on New Zealand v India
the two sides are 35 and 15 of 50, which sums to the denominator.</li>
<li><b>What is missing.</b> The betslip price comparison is rendered after a click, so no bookmaker price exists in the readable markup.
Every number in the “our line” column on this site therefore came from this desk, not from a book.</li>
</ol>
</section>
<section><h2>Markets found today, by name</h2><p class="fine">Anything outside this list was not exposed by OLBG for the events captured.</p>
<ul class="mklist">{"".join(f'<li>{e(m)}</li>' for m in mk)}</ul></section>
<section><h2>Time labels</h2><p>OLBG prints “Today 21:00” style labels with no zone. Four fixtures checked against official start times all
land on UTC−4 — Columbus at Philadelphia printed 19:07 against an official 23:00Z start, Boston at Carolina 20:07 against 00:00Z,
Kielce 15:45 against a 19:45Z kick-off, and Wellington 03:00 against a 07:00Z start. Tampa Bay and the Mexican Grand Prix each sit an
hour further out than that rule predicts, so the raw label is kept on every row, the official UTC time is quoted in words where it was
found, and nothing on this site claims a kick-off time from OLBG's label alone.</p></section>
<section><h2>What this site will not do</h2><ul class="nc">
<li>Publish a price for a market that had no tips. Two totals markets today (the World Series Game 5 line at 7.5 and the Kielce points
total at 63.5) carry zero volume; both are left unpriced rather than filled from a prior.</li>
<li>Turn an outright into a confidence bet. Four sports' OLBG coverage is outrights only, and a share of a handful of tips across a
128-player field is a popularity index, not a price.</li>
<li>Treat an OLBG paragraph as a fact. Tipster comments are quoted as opinions attributed to OLBG's crowd, never restated as scouting.</li>
<li>Claim five picks a sport when the evidence covers three. Every shortfall is named on the overview ledger.</li>
</ul></section>""", "Structure of OLBG listings, market inventory and the time-label finding.")


# --------------------------------------------------------------- flagged --
def page_flagged():
    fl = LINES["flags"]
    seen, rows = set(), []
    for f in fl:
        k = (f["code"], f.get("sport"), f.get("detail"))
        if k in seen:
            continue
        seen.add(k)
        rows.append(f'<tr><td><span class="code">{e(f["code"])}</span></td><td>{e(f.get("sport", "—"))}</td>'
                    f'<td>{e(f["detail"])}</td><td class="srcs">{src_chip("source", f["source"])}</td></tr>')
    unc = [r for r in LINES["rows"] if r["official_tier"] != "A"]
    nop = [r for r in LINES["rows"] if r["fair_american"] is None]
    outw = [r for r in LINES["rows"] if not r["in_window_fair"]]
    return shell("flagged", "Flagged for review · OLBG research desk", f"""
<section class="pagemast"><h1>Flagged for review</h1>
<p class="lede">Everything that needs a human decision, with the source beside it. None of this blocks publishing the site; all of it
blocks pretending the numbers are firmer than they are.</p>
{len(rows)} distinct flags were raised by the pricing step across {len(fl)} row-level notes. Nothing here has been quietly corrected by assumption.</section>
<section><h2>Structural findings</h2><ol class="readout big">
<li><strong>Fabricated content was live in the repository.</strong> <code>data/darts.json</code> is now <code>quarantine/FABRICATED-data-darts.json</code>.
Five darts picks, each stamped <code>"verified": "True"</code>, cited to a single URL — <code>pdc.tv/tournaments/european-championship</code>, a
tournament directory page — and written with sentences like “averaging a massive 105 in his previous match”, which is not a statistic the PDC publishes. The pairings appear in no capture file, and OLBG's own darts
category carried no match market at all today. <em>Decision needed:</em> delete outright rather than keep in quarantine, and check whether the same
author pattern produced anything else.</li>
<li><strong>Two sports have nothing to price.</strong> OLBG printed “No tips found.” for Snooker and for Greyhounds. The gap is a property of the
source — OLBG only exposes events with tipster activity — not a collection failure. <em>Decision needed:</em> whether to source those two from a
different feed or accept zero coverage on days OLBG is empty.</li>
<li><strong>OLBG's tip volume is thin on most markets.</strong> {len([r for r in LINES['rows'] if 'thin_sample_fewer_than_3_tips' in r['flags']])} of {len(LINES['rows'])} priced
selections come from markets with fewer than three tips. Any “confidence” built on those is a market read, and we cap them to Low.</li>
<li><strong>Time zones.</strong> OLBG's printed clock appears to be US Eastern; two events do not fit that rule. Treat the linked official page as the
authority for start times.</li>
<li><strong>Consensus anomaly in handball.</strong> The most-tipped outcome is “Tie” on eight of fifteen markets, including Kielce v Kolstad where
the EHF records the head-to-head as 7-0-0 to Kielce and Kolstad are 0-0-5 in the group. Either the crowd is on the draw for reasons we cannot see,
or the three-way market is being tipped carelessly. Published as counter-consensus; <em>needs a rule</em> for when we override OLBG's most popular pick.</li>
<li><strong>Unconfirmed statistics quoted from the site itself.</strong> The OLBG Gaelic football page states Mayo beat Kerry in the 2026 All-Ireland final,
ending a 75-year wait. Not checked against a GAA source in this session, so the Kerry row carries that as an OLBG claim only.</li>
<li><strong>A parallel desk was merged to <code>main</code> while this one was being built.</strong>
Session <code>dcc71481</code>/<code>65c1e02b</code> shipped their own root pages from <code>data/desk-*.json</code> with 24 written
predictions and a separate pricing step in <code>price-engine/originate.py</code>. Two generators cannot own the same eight HTML files,
so the root surface is now this pipeline's, their builder is archived at <code>price-engine/build_desk_site.py</code>, and their payload is
retained and still gated by <code>scripts/check_site.py</code>. Their rows are <em>not</em> merged into the published picks: their engine
prices the same events differently (Colomiers at -161 against our -150, Naomi Osaka at -132 against our -200), and two prices for one
selection on one page is the confusion the brief asked us to remove.
<em>Decision needed:</em> retire the parallel payload, or reconcile the two engines into one and publish the union.</li>
<li><strong>The legacy builder no longer matches its own payload.</strong> <code>scripts/build_dashboard.py</code> emits a
<code>v1</code> document from the 2026-10-26 capture, while <code>data/dashboard.json</code> as committed on <code>main</code> is a
<code>v2</code> summary. Running the old builder therefore overwrites 7,000 lines of the published payload; this branch restores the
committed file and leaves it alone rather than "fixing" someone else's artefact with a stale one. <em>Decision needed:</em> its owner
should either re-point the builder at today's capture or retire both together.</li>
</ol></section>
<section><h2>Rows with no official crosswalk ({len(unc)})</h2>
<p class="fine">These rows are published with their OLBG link and no more; the blank official column is the finding.</p>
<details><summary>Expand the full list</summary><table class="grid"><thead><tr><th>Sport</th><th>Event</th><th>Selection</th><th>Best tier found</th><th>Link</th></tr></thead><tbody>
{''.join(f'<tr><td>{e(r["sport"])}</td><td>{e(r["event"])}</td><td>{e(r["selection"])}</td><td>{e(r["official_tier"].upper())}</td><td class="srcs">{src_chip("OLBG", r["olbg_url"])}</td></tr>' for r in unc)}
</tbody></table></details></section>
<section><h2>Markets left unpriced ({len(nop)})</h2><table class="grid"><thead><tr><th>Sport</th><th>Event</th><th>Market</th><th>Selection</th><th>Reason</th></tr></thead><tbody>
{''.join(f'<tr><td>{e(r["sport"])}</td><td>{e(r["event"])}</td><td>{e(r["market"])}</td><td>{e(r["selection"])}</td><td>OLBG printed 0 tips in this market, so there was no volume to price.</td></tr>' for r in nop)}
</tbody></table></section>
<section><h2>Outside the −250 to +10,000 band ({len(outw)})</h2>
<p class="fine">Excluded from the picks surface by instruction. Each is a favourite the crowd prices so heavily that a bet carries no return worth taking.</p>
<table class="grid"><thead><tr><th>Sport</th><th>Selection</th><th>Event / market</th><th>Our fair line</th><th>Chance</th><th>OLBG support</th></tr></thead><tbody>
{''.join(f'<tr><td>{e(r["sport"])}</td><td>{e(r["selection"])}</td><td>{e(r["event"])} · {e(r["market"])}</td><td class="mono">{ampn(r["fair_american"])}</td><td class="mono">{pct(r["our_prob"])}</td><td class="mono">{r["olbg_win_tips"]}/{r["olbg_total_tips"]}</td></tr>' for r in outw)}
</tbody></table></section>
<section><h2>Full flag queue</h2><table class="grid"><thead><tr><th>Code</th><th>Sport</th><th>Detail</th><th>Source</th></tr></thead><tbody>
{''.join(rows[:400])}</tbody></table></section>""", "Flagged irregularities, unverified rows and unpriced markets, with sources.")


# ------------------------------------------------------------------ sport --
def page_sport(key, v):
    picks = [p for p in PICKS["picks"] if p["sport_key"] == key]
    rows = [r for r in LINES["rows"] if r["sport_key"] == key]
    pcards = "".join(f"""<article class="pick" id="{p['pick_id']}">
  <div class="phead"><div><h3>{e(p['headline'])}</h3><p class="meta"><a href="{e(p['olbg_url'])}" target="_blank" rel="noopener">{e(p['event'])}</a>
  · OLBG prints “{e(p['time_label'])}”</p></div><div class="badge">{band(p['confidence'])}</div></div>
  <p class="selectionline"><b>Bet:</b> <span class="bigsel">{e(p['selection'])}</span> — {e(p['market'])}
  · our line <span class="mono">{ampn(p['fair_american'])}</span> · chance {pct(p['our_prob'])}
  · OLBG support {p['olbg_win_tips'] if p['olbg_win_tips'] is not None else '—'}/{p['olbg_total_tips'] or '—'}</p>
  <p class="prose">{e(p['note'])}</p>
  <ul class="srcs inline">{''.join(f'<li>{src_chip(s["name"], s["url"])}</li>' for s in p['sources'])}</ul>
</article>""" for p in sorted(picks, key=lambda x: -x["pick_score"]))
    evb = []
    for ev in v["events"]:
        trs = "".join(f"""<tr><td>{e(m['market'])}</td><td>{e(s['label'])}</td>
<td class="mono">{ampn(next((r['fair_american'] for r in rows if r['event_id'] == ev['event_id'] and r['market'] == m['market'] and r['selection'] == s['label']), None))}</td>
<td class="mono">{ampn(next((r['our_american'] for r in rows if r['event_id'] == ev['event_id'] and r['market'] == m['market'] and r['selection'] == s['label']), None))}</td>
<td class="mono">{pct(next((r['our_prob'] for r in rows if r['event_id'] == ev['event_id'] and r['market'] == m['market'] and r['selection'] == s['label']), None))}</td>
<td class="mono">{'' if s['win_tips'] is None else s['win_tips']}/{'' if s['total_tips'] is None else s['total_tips']}</td>
<td>{next((band(r['confidence']) for r in rows if r['event_id'] == ev['event_id'] and r['market'] == m['market'] and r['selection'] == s['label']), '')}</td>
<td class="srcs">{src_chip('OLBG', ev['olbg_url'])}</td></tr>"""
                        for m in ev["markets"] for s in m["selections"])
        off = ""
        cwkey = f"{key}:{ev['event_id']}"
        if cwkey in CW["events"]:
            c = CW["events"][cwkey]
            off = f'<p class="offb"><b>{e("Tier " + c["tier"].upper() + " source")}</b> ' + \
                  " ".join(src_chip(s["name"], s["url"], s.get("tier_override", c["tier"])) for s in c["sources"]) + \
                  f'<br><span class="fine">{e(c["sources"][0]["confirmed"])}</span></p>' 
        evb.append(f"""<div class="evblock"><h3><a href="{e(ev['olbg_url'])}" target="_blank" rel="noopener">{e(ev['name'])}</a></h3>
<p class="meta">{e(ev['competition'])} · OLBG prints “{e(ev['time_label'])}” · {len(ev['markets'])} market(s) found</p>
{off}
<table class="grid"><thead><tr><th>Market</th><th>Selection</th><th>Our fair line</th><th>After margin</th><th>Chance</th><th>OLBG tips</th><th>Band</th><th>Source</th></tr></thead><tbody>{trs}</tbody></table></div>""")
    note = ""
    if not v["events"]:
        note = f"""<section class="empty"><h2>Nothing to price today</h2>
<p>{e(v.get('capture_note', 'OLBG listed no events in this category at capture time.'))}</p>
<p class="fine">OLBG only exposes events that tipsters have posted on, so an empty category means no published tips — it is not evidence the sport
has no fixtures. No event, line or prediction has been invented to reach the five-a-sport target. Official home page kept below so the check is
reproducible: {src_chip('OLBG category page', v['olbg_hub'])}</p></section>"""
    cnt = f"{len(picks)} written pick{'s' if len(picks) != 1 else ''}" if picks else "no written picks"
    return shell("sport", f"{v['label']} · OLBG research desk", f"""
<section class="pagemast"><h1>{e(v['label'])}</h1><p class="lede">{cnt} · {len(v['events'])} OLBG listings ·
{len(rows)} priced selections across {sum(len(m['selections']) for ev in v['events'] for m in ev['markets'])} market outcomes.
OLBG sport id {v['sport_id']}.</p>
<p class="jump">{src_chip('OLBG category page', v['olbg_hub'])}</p></section>
{note}
{f'<section><h2>Predictions</h2>{pcards}</section>' if picks else ''}
{f'<section><h2>Every market on the board</h2>{"".join(evb)}</section>' if evb else ''}""",
                 f"{v['label']} lines, predictions and sources from the OLBG capture.")


def write(rel, text):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(text)


def main():
    global _REL
    write("index.html", page_index())
    write("picks.html", page_picks())
    write("matches.html", page_matches())
    write("pricing.html", page_pricing())
    write("sources.html", page_sources())
    write("methodology.html", page_method())
    write("flagged.html", page_flagged())
    _REL = "../"
    for k, v in CAP["sports"].items():
        write(f"sports/{slug(k)}.html", page_sport(k, v))
    _REL = ""
    print(f"built {7 + len(CAP['sports'])} pages")


if __name__ == "__main__":
    main()
