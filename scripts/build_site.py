#!/usr/bin/env python3
"""Build the static research dashboard (GitHub Pages root) from the data files."""
import json, html, datetime, collections, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONTENT = ROOT / "content"

SNAPSHOT = "2026-10-26 20:41 UTC"

SPORTS = [
    ("golf", "Golf", "⛳", "https://www.olbg.com/betting-tips/Golf/5", ["Golf"]),
    ("volleyball", "Volleyball", "🏐", "https://www.olbg.com/betting-tips/Volleyball/21", ["Volleyball"]),
    ("rugby-union", "Rugby Union", "🏉", "https://www.olbg.com/betting-tips/Rugby_Union/9", ["Rugby Union"]),
    ("cricket", "Cricket", "🏏", "https://www.olbg.com/betting-tips/Cricket/7", ["Cricket"]),
    ("snooker", "Snooker", "🎱", "https://www.olbg.com/betting-tips/Snooker/8", ["Snooker"]),
    ("darts", "Darts", "🎯", "https://www.olbg.com/betting-tips/Darts/15", ["Darts"]),
    ("baseball", "Baseball", "⚾", "https://www.olbg.com/betting-tips/Baseball/12", ["Baseball"]),
    ("gaelic-sports", "Gaelic Sports", "🏑", "https://www.olbg.com/betting-tips/Gaelic_Football/25", ["Gaelic Football", "Hurling"]),
    ("greyhounds", "Greyhounds", "🐕", "https://www.olbg.com/betting-tips/Greyhounds/28", ["Greyhounds"]),
    ("tennis", "Tennis", "🎾", "https://www.olbg.com/betting-tips/Tennis/3", ["Tennis"]),
    ("motor-racing", "Motor Racing", "🏎️", "https://www.olbg.com/betting-tips/Motor_Racing/14", ["Motor Racing"]),
    ("handball", "Handball", "🤾", "https://www.olbg.com/betting-tips/Handball/20", ["Handball"]),
    ("ice-hockey", "Ice Hockey", "🏒", "https://www.olbg.com/betting-tips/Ice_Hockey/13", ["Ice Hockey"]),
    ("basketball", "Basketball", "🏀", "https://www.olbg.com/betting-tips/Basketball/4", ["Basketball"]),
    ("rugby-league", "Rugby League", "🏉", "https://www.olbg.com/betting-tips/Rugby_League/10", ["Rugby League"]),
]

GLOBAL_FLAGS = [
    ("Snooker inventory is empty", "OLBG's snooker page returned zero listings at snapshot (no markets, no tips), so no snooker pick can be published without inventing a fixture.", "https://www.olbg.com/betting-tips/Snooker/8"),
    ("Sports below the five-pick target", "OLBG listed fewer supported markets than five picks in snooker (0), baseball (1 event), darts (2), motor racing (2), gaelic football/hurling (4), rugby league (3) and golf (3). No fixture was invented to fill the gap.", "https://www.olbg.com/betting-tips"),
    ("Form and injury feeds missing for most sports", "Official injury/lineup feeds were captured only for the NHL and MLB (and the F1 classification). For tennis, cricket, rugby, handball, volleyball, basketball, darts, golf, gaelic games and greyhounds no official team-news source was retrievable in this snapshot, so those notes are blank and marked unconfirmed per row.", "https://www.olbg.com/betting-tips"),
    ("NBA, ATP, EHF, GBGB and URC endpoints blocked", "Requests to cdn.nba.com (403), atptour.com (403), ehfcl.eurohandball.com (404), gbgb.org.uk (404) and unitedrugby.com (404) returned no usable data, so no official facts are claimed for those competitions.", "https://www.olbg.com/betting-tips"),
    ("Greyhound races have no tipster consensus and no date", "Greyhound race pages embed the full field and prices but the listing shows a time only (for example 9:46 Nottingham). Our greyhound lines are single-market and the picks sit in the Low tier.", "https://www.olbg.com/betting-tips/Greyhounds/28"),
    ("Draw-heavy three-way markets", "OLBG tipsters pile onto the draw in handball and gaelic football (Tie was the most-tipped selection in ten handball matches). Our line caps any draw deviation from the market at three percentage points so a small tip sample cannot manufacture a draw probability.", "https://www.olbg.com/betting-tips/Handball/20"),
    ("Four markets withheld", "Markets whose displayed prices summed to an overround below 0.90 (an incomplete outcome set) were not priced at all rather than priced on partial information.", "https://www.olbg.com/betting-tips"),
    ("Prices are a snapshot, not a live quote", "Every price on this site is the decimal/ American/ fractional figure OLBG displayed at capture time. Our own offered price adds a 3% margin to the fair line and is not a market quote.", "https://www.olbg.com/betting-tips"),
    ("Long-dated outrights", "Several picks settle in 2027 (PDC World Championship, All-Ireland championships, State of Origin, Super League, NRL). Squads and fields cannot be confirmed yet.", "https://www.olbg.com/betting-tips"),
    ("No bet placement or live odds re-check", "The dashboard does not connect to a bookmaker. Prices must be re-checked on OLBG before any bet, and a moved price invalidates the stated edge.", "https://www.olbg.com/betting-tips"),
]


def esc(s):
    return html.escape("" if s is None else str(s))


def am(v):
    if v is None:
        return "—"
    return f"+{v}" if v > 0 else str(v)


def dec(v):
    return "—" if v is None else f"{v:.2f}"


def pct(v):
    return "—" if v is None else f"{v*100:.1f}%"


def load(name, default=None):
    p = DATA / name
    if not p.exists():
        return default if default is not None else []
    return json.loads(p.read_text())


def predictions():
    out = {}
    for f in sorted(CONTENT.glob("predictions_*.json")):
        out.update(json.loads(f.read_text()))
    return out


def nav(active, base=""):
    items = [(f"{base}index.html", "⌂", "Executive summary", "home"),
             (f"{base}markets.html", "▦", "All market lines", "markets"),
             (f"{base}methodology.html", "◈", "Pricing method", "method"),
             (f"{base}sources.html", "②", "Sources", "sources"),
             (f"{base}review.html", "⚑", "Flagged for review", "review")]
    html_nav = "".join(
        f'<a class="navlink{" active" if active==k else ""}" href="{h}"><span class="ico">{i}</span>{t}</a>'
        for h, i, t, k in items)
    sports = "".join(
        f'<a class="navlink{" active" if active==slug else ""}" href="{base}sports/{slug}.html">'
        f'<span class="ico">{icon}</span>{name}</a>'
        for slug, name, icon, _u, _n in SPORTS)
    return (f'<aside class="sidebar"><a class="brand" href="{base}index.html">'
            f'<span class="mark">O</span><span><strong>OLBG Research Desk</strong>'
            f'<small>15-sport market monitor</small></span></a>'
            f'<div class="nav-label">Workspace</div>{html_nav}'
            f'<div class="nav-label">Covered sports</div>{sports}'
            f'<div class="nav-label">Data</div>'
            f'<a class="navlink" href="{base}data/picks.json"><span class="ico">↧</span>Picks (JSON)</a>'
            f'<a class="navlink" href="{base}data/lines.json"><span class="ico">↧</span>Every line (JSON)</a>'
            f'</aside>')


def page(title, body, active="", base="", desc="OLBG sports research dashboard"):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="stylesheet" href="{base}assets/style.css">
</head><body><div class="layout">{nav(active, base)}<main>
<div class="topbar"><span class="eyebrow">Independent sports market research · OLBG snapshot</span>
<span class="snapshot"><i class="dot"></i>Data captured {esc(SNAPSHOT)}</span></div>
{body}
<footer>Research only · 18+ · No outcome is guaranteed. Every row links to the OLBG page it was read from;
official-source facts are linked separately. Blank means not confirmed — never inferred.</footer>
</main></div></body></html>"""


def confidence_badge(c):
    cls = {"High": "high", "Medium": "medium", "Low": "low"}.get(c, "masked")
    return f'<span class="badge {cls}">{esc(c)}</span>'


def build():
    picks = load("picks.json")
    lines = load("lines.json")
    fixtures = load("fixtures.json")
    markets = load("markets.json")
    facts = load("official_facts.json", {})
    preds = predictions()
    sports_meta = {s["slug"]: s for s in load("sports.json", [])}

    # ---- derived stats -------------------------------------------------
    n_events = len(lines)
    n_markets = sum(len(e["markets"]) for e in lines)
    n_outcomes = sum(len(m["outcomes"]) for e in lines for m in e["markets"])
    by_sport_lines = collections.defaultdict(list)
    for e in lines:
        for s in SPORTS:
            if e["sport"] in s[4]:
                by_sport_lines[s[0]].append(e)
    picks_by_sport = collections.defaultdict(list)
    for p in picks:
        picks_by_sport[p["sport_slug"]].append(p)
    conf_counts = collections.Counter(p["confidence"] for p in picks)

    # ---- index ---------------------------------------------------------
    today_picks = [p for p in picks if (p.get("event_date") or "") in ("2026-10-26", "2026-10-27")]
    today_picks.sort(key=lambda p: ({"High": 2, "Medium": 1, "Low": 0}[p["confidence"]], p["p_fair"]), reverse=True)
    rows = ""
    for p in today_picks[:8]:
        rows += (f'<tr><td><a href="sports/{p["sport_slug"]}.html#{p["pick_id"]}"><strong>{esc(p["selection"])}</strong></a>'
                 f'<div class="small">{esc(p["sport"])} · {esc(p["market"])}</div></td>'
                 f'<td>{esc(p["event"])}<div class="small">{esc(p.get("tournament") or "")}</div></td>'
                 f'<td class="num">{am(p["olbg_american"])}</td><td class="num">{am(p["fair_american"])}</td>'
                 f'<td class="num">{pct(p["p_fair"])}</td><td>{confidence_badge(p["confidence"])}</td>'
                 f'<td><a href="{esc(p["olbg_url"])}" target="_blank" rel="noopener">OLBG</a></td></tr>')

    upcoming = [p for p in picks if p not in today_picks]
    upcoming.sort(key=lambda p: (p.get("event_date") or "9999", -p["p_fair"]))
    up_rows = ""
    for p in upcoming[:20]:
        up_rows += (f'<tr><td class="num">{esc(p.get("event_date") or "—")}</td>'
                    f'<td><a href="sports/{p["sport_slug"]}.html#{p["pick_id"]}"><strong>{esc(p["selection"])}</strong></a>'
                    f'<div class="small">{esc(p["sport"])} · {esc(p["market"])}</div></td>'
                    f'<td>{esc(p["event"])}</td><td class="num">{am(p["olbg_american"])}</td>'
                    f'<td class="num">{pct(p["p_fair"])}</td><td>{confidence_badge(p["confidence"])}</td>'
                    f'<td><a href="{esc(p["olbg_url"])}" target="_blank" rel="noopener">OLBG</a></td></tr>')
    coverage = ""
    for slug, name, icon, url, names in SPORTS:
        ev = by_sport_lines.get(slug, [])
        mk = sum(len(e["markets"]) for e in ev)
        ps = picks_by_sport.get(slug, [])
        tiers = collections.Counter(p["confidence"] for p in ps)
        status = ('<span class="badge ok">Live picks</span>' if len(ps) >= 5
                  else f'<span class="badge {"flag" if ps else "low"}">{"Partial" if ps else "No market"}</span>')
        coverage += (f'<tr><td><a href="sports/{slug}.html">{icon} {esc(name)}</a></td>'
                     f'<td class="num">{len(ev)}</td><td class="num">{mk}</td><td class="num">{len(ps)}</td>'
                     f'<td class="num">{tiers.get("High",0)}</td><td class="num">{tiers.get("Medium",0)}</td>'
                     f'<td class="num">{tiers.get("Low",0)}</td><td>{status}</td></tr>')

    body = f"""
<section>
<h1>Executive summary</h1>
<p class="lede">Every sport you asked for, priced from the markets OLBG actually displayed: {n_events} events,
{n_markets} markets and {n_outcomes:,} individual outcomes carry our own fair line, and {len(picks)} picks
are published with written analysis. Each pick states the selection, the price we took from OLBG, our fair price and the confidence tier.</p>
</section>

<div class="grid kpis" style="margin-top:16px">
  <div class="kpi"><span>Events priced</span><strong>{n_events}</strong><em>across 15 sports</em></div>
  <div class="kpi"><span>Markets priced</span><strong>{n_markets}</strong><em>win, handicap, totals, outright</em></div>
  <div class="kpi"><span>Outcomes with a line</span><strong>{n_outcomes:,}</strong><em>de-vigged + consensus</em></div>
  <div class="kpi"><span>Picks published</span><strong>{len(picks)}</strong><em>{conf_counts.get("High",0)} high · {conf_counts.get("Medium",0)} medium · {conf_counts.get("Low",0)} low</em></div>
</div>

<h2>Highest-confidence picks for today and tomorrow</h2>
<p class="section-note">Only selections priced between −250 and +10,000 with a written prediction are listed. Sorted by confidence tier, then by our fair probability.</p>
<div class="tablewrap" style="max-height:none"><table>
<thead><tr><th>Selection</th><th>Event</th><th class="num">OLBG price</th><th class="num">Our fair price</th><th class="num">Our probability</th><th>Confidence</th><th>Source</th></tr></thead>
<tbody>{rows or '<tr><td colspan="7">No picks dated today.</td></tr>'}</tbody></table></div>
<p class="notes">{conf_counts.get("High",0)} selection clears the 70% high-confidence bar inside the requested price band. With a −250 floor the
maximum possible implied chance is 71.4%, so the high tier is deliberately narrow; the medium tier carries the bulk of the card and is labelled as such.</p>

<h2>Upcoming picks (after tomorrow)</h2>
<p class="section-note">Every remaining published pick, ordered by start date. Long-dated outrights settle in 2027 and are flagged as such.</p>
<div class="tablewrap" style="max-height:none"><table>
<thead><tr><th class="num">Date</th><th>Selection</th><th>Event</th><th class="num">OLBG price</th><th class="num">Our probability</th><th>Confidence</th><th>Source</th></tr></thead>
<tbody>{up_rows or '<tr><td colspan="7">No further picks.</td></tr>'}</tbody></table></div>

<h2>Coverage by sport</h2>
<div class="tablewrap" style="max-height:none"><table>
<thead><tr><th>Sport</th><th class="num">Events priced</th><th class="num">Markets</th><th class="num">Picks</th>
<th class="num">High</th><th class="num">Medium</th><th class="num">Low</th><th>Status</th></tr></thead>
<tbody>{coverage}</tbody></table></div>
<p class="notes">"Partial" means OLBG listed fewer supported markets than the five-pick target. Nothing has been invented to fill a gap —
see <a href="review.html">Flagged for review</a> for the per-sport inventory limits.</p>

<div class="grid sportgrid" style="margin-top:18px">
  {''.join(f'<div class="sportcard"><h3>{icon} {esc(name)}</h3><div class="m">{len(by_sport_lines.get(slug,[]))} events · {len(picks_by_sport.get(slug,[]))} picks</div><a href="sports/{slug}.html">Open {esc(name)} desk →</a></div>' for slug, name, icon, _u, _n in SPORTS)}
</div>

<h2>How the lines are made</h2>
<div class="card">
<p>Every displayed price is de-vigged across the full outcome set to give a market probability, blended with the OLBG tipster
consensus using a Bayesian shrinkage term, then republished as our fair American price and a 3% margin offered price.
Confidence: High ≥ 70%, Medium 55–70%, Low &lt; 55%. The exact formulas, thresholds and edge cases are on the
<a href="methodology.html">pricing method</a> page; the raw inputs are in
<a href="data/lines.json">data/lines.json</a> and <a href="data/picks.json">data/picks.json</a>.</p>
</div>

<div class="alert info" style="margin-top:16px"><span class="ic">ℹ</span>
<div><strong>What is confirmed and what is not.</strong> Fixture, market, price and tip counts are read directly from the linked OLBG event page.
Recent form and injury data are only stated where an official feed (NHL, MLB, F1) supplied them; for the other sports those fields are
left blank and the pick is marked unconfirmed in <a href="review.html">Flagged for review</a>.</div></div>
"""
    (ROOT / "index.html").write_text(page("OLBG Research Desk — executive summary", body, "home"))

    # ---- sport pages ---------------------------------------------------
    (ROOT / "sports").mkdir(exist_ok=True)
    for slug, name, icon, url, names in SPORTS:
        ev = by_sport_lines.get(slug, [])
        ps = picks_by_sport.get(slug, [])
        meta = sports_meta.get(slug, {})
        mk_count = sum(len(e["markets"]) for e in ev)
        out_count = sum(len(m["outcomes"]) for e in ev for m in e["markets"])
        tiers = collections.Counter(p["confidence"] for p in ps)

        cards = ""
        for p in ps:
            pr = preds.get(p["pick_id"], {})
            flags = pr.get("flags") or []
            facts_list = pr.get("official_facts") or []
            srcs = pr.get("sources") or []
            flags_html = "".join(f'<span class="badge flag">{esc(f)}</span> ' for f in flags) or '<span class="badge ok">No open flag on this pick</span>'
            facts_html = ""
            if facts_list:
                facts_html = '<div class="evidence"><strong>Official-source facts used</strong><ul>' + "".join(
                    f'<li>{esc(f)} — <a href="{esc(s)}" target="_blank" rel="noopener">{esc(re.sub(r"^https?://", "", s))}</a></li>'
                    for f, s in zip(facts_list, srcs)) + '</ul></div>'
            cards += f"""
<article class="pick" id="{p['pick_id']}">
 <div class="pick-head">
  <div><h3>Pick {p['rank']} · {esc(pr.get('headline') or p['selection'])}</h3>
  <div class="meta">{esc(p['event'])}{' · ' + esc(p['tournament']) if p.get('tournament') else ''} · starts {esc(p.get('event_date') or 'date not published')}</div></div>
  <div>{confidence_badge(p['confidence'])}</div>
 </div>
 <div class="sel">Selection: {esc(p['selection'])} — {esc(p['market'])}</div>
 <div class="pricegrid">
  <div><span>OLBG price</span><b>{am(p['olbg_american'])}</b><div class="small">{dec(p['olbg_decimal'])} decimal</div></div>
  <div><span>Our fair price</span><b>{am(p['fair_american'])}</b><div class="small">{dec(p['fair_decimal'])} decimal</div></div>
  <div><span>Our offered price</span><b>{am(p['our_american'])}</b><div class="small">{dec(p['our_decimal'])} decimal · 3% margin</div></div>
  <div><span>Our probability</span><b>{pct(p['p_fair'])}</b><div class="small">market {pct(p['p_market'])}</div></div>
  <div><span>Tip support</span><b>{p['tips_on_selection'] if p['tips_on_selection'] is not None else '—'}/{p['tips_in_market'] if p['tips_in_market'] is not None else '—'}</b><div class="small">tips on selection / in market</div></div>
  <div><span>Value at OLBG price</span><b>{(p['value_at_olbg_price'] or 0)*100:+.1f}%</b><div class="small">our probability × price − 1</div></div>
 </div>
 <p class="pred">{esc(pr.get('prediction') or 'Prediction pending.')}</p>
 <div class="notes"><strong>Form &amp; availability:</strong> {esc(pr.get('injury_note') or 'No official team-news source was available in this snapshot; left blank and flagged.')}</div>
 {facts_html}
 <div class="evidence"><strong>Source trail</strong><ul>
   <li><a href="{esc(p['olbg_url'])}" target="_blank" rel="noopener">OLBG event page</a> — the market, prices, tip counts and start time above are reproduced from this page.</li>
   <li>{esc(p['data_status'])}</li>
 </ul></div>
 <div class="taglist" style="margin-top:8px">{flags_html}</div>
</article>"""

        if not ps:
            cards = f"""<div class="alert bad"><span class="ic">⚑</span><div><strong>No publishable pick for {esc(name)} at this snapshot.</strong>
            {'OLBG returned zero listings for this sport, so there is no fixture, market or price to originate a line from.' if not ev else 'OLBG listed markets, but none of the selections passed the price-band and probability filters, so nothing is published rather than publishing an unsupported favourite.'}
            This is recorded on <a href="../review.html">Flagged for review</a>.</div></div>"""

        line_rows = ""
        for e in ev:
            for m in e["markets"]:
                first = True
                for o in m["outcomes"]:
                    band = '<span class="badge ok">in band</span>' if o["in_requested_band"] else '<span class="badge masked">out of band</span>'
                    conf = o.get("confidence")
                    ev_cell = ""
                    if first:
                        small = '<div class="small">' + esc(e.get("event_date") or "") + '</div>'
                        ev_cell = ('<a href="' + esc(e["olbg_url"]) + '" target="_blank" rel="noopener"><strong>'
                                   + esc(e["event"]) + "</strong></a>" + small)
                    mk_cell = esc(m["market"]) if first else ""
                    line_rows += (f'<tr><td>{ev_cell}</td>'
                                  f'<td>{mk_cell}</td><td>{esc(o["selection"])}</td>'
                                  f'<td class="num">{dec(o["olbg_decimal"])}<div class="small">{am(o["olbg_american"])}</div></td>'
                                  f'<td class="num">{pct(o["p_market"])}</td><td class="num">{pct(o["p_fair"])}</td>'
                                  f'<td class="num">{am(o["fair_american"])}</td><td class="num">{am(o["our_american"])}</td>'
                                  f'<td>{band}</td></tr>')
                    first = False

        method_note = esc(meta.get("pricing") or "")
        markets_covered = esc(meta.get("markets") or "")
        body = f"""
<section>
<div class="small"><a href="../index.html">Executive summary</a> / {esc(name)}</div>
<h1>{icon} {esc(name)}</h1>
<p class="lede">{esc(name)} on OLBG: {len(ev)} events priced, {mk_count} markets, {out_count} outcomes, {len(ps)} published picks
({tiers.get("High",0)} high, {tiers.get("Medium",0)} medium, {tiers.get("Low",0)} low).
Category page: <a href="{url}" target="_blank" rel="noopener">olbg.com</a>.</p>
</section>

<h2>Picks</h2>
{cards}

<h2>Every priced market in {esc(name)}</h2>
<p class="section-note">Our fair price removes the bookmaker margin from the displayed prices and blends in the tipster consensus.
"Out of band" rows are priced but excluded from picks because the requested range is −250 to +10,000.</p>
<div class="filters">
  <input type="search" data-filter placeholder="Filter selection, event or market…" aria-label="Filter market rows">
  <span class="pill">{len(ev)} events</span><span class="pill">{mk_count} markets</span><span class="pill">{out_count} outcomes</span>
</div>
<div class="tablewrap"><table data-table>
<thead><tr><th>Event / date</th><th>Market</th><th>Selection</th><th class="num">OLBG price</th><th class="num">Market probability</th>
<th class="num">Our probability</th><th class="num">Our fair price</th><th class="num">Our price</th><th>Band</th></tr></thead>
<tbody>{line_rows or '<tr><td colspan="9">No markets captured for this sport at snapshot time.</td></tr>'}</tbody></table></div>

<h2>How this sport is priced</h2>
<div class="card"><p><strong>Markets covered:</strong> {markets_covered or 'as listed by OLBG'}.</p>
<p>{method_note or 'Same universal method as every other sport on this site.'}</p>
<p class="small">Universal method: proportional de-vig across the full outcome set, Bayesian tipster-consensus blend
(weight capped at 0.35), 3% offered-price margin, and the −250 to +10,000 eligibility band. See <a href="../methodology.html">pricing method</a>.</p></div>
"""
        (ROOT / "sports" / f"{slug}.html").write_text(page(f"{name} — OLBG research desk", body, slug, base="../"))

    # ---- markets page --------------------------------------------------
    blocks = ""
    for slug, name, icon, url, names in SPORTS:
        ev = by_sport_lines.get(slug, [])
        if not ev:
            continue
        rows = ""
        for e in ev:
            for m in e["markets"]:
                for i, o in enumerate(m["outcomes"]):
                    ev_name = ('<a href="' + esc(e["olbg_url"]) + '" target="_blank" rel="noopener">'
                               + esc(e["event"]) + '</a>') if i == 0 else ""
                    rows += (f'<tr><td>{ev_name}</td>'
                             f'<td>{esc(m["market"]) if i==0 else ""}</td><td>{esc(o["selection"])}</td>'
                             f'<td class="num">{am(o["olbg_american"])}</td><td class="num">{pct(o["p_market"])}</td>'
                             f'<td class="num">{pct(o["p_fair"])}</td><td class="num">{am(o["fair_american"])}</td>'
                             f'<td class="num">{am(o["our_american"])}</td>'
                             f'<td>{"✓" if o["in_requested_band"] else "—"}</td></tr>')
        blocks += (f'<h2 id="{slug}">{icon} {esc(name)} <span class="pill">{len(ev)} events</span></h2>'
                   f'<div class="tablewrap"><table data-table><thead><tr><th>Event</th><th>Market</th><th>Selection</th>'
                   f'<th class="num">OLBG</th><th class="num">Market p</th><th class="num">Our p</th><th class="num">Fair price</th>'
                   f'<th class="num">Our price</th><th>Band</th></tr></thead><tbody>{rows}</tbody></table></div>')

    body = f"""
<h1>All market lines</h1>
<p class="lede">{n_outcomes:,} outcomes across {n_markets} markets on {n_events} events, each with the displayed OLBG price,
the de-vigged market probability, our fair probability, our fair American price and our offered price.</p>
<div class="filters"><input type="search" data-filter placeholder="Filter any column…" aria-label="Filter all lines"></div>
<p class="section-note">Table rows are wide by nature; the sport pages carry the same data with the picks on top.</p>
{blocks}
"""
    (ROOT / "markets.html").write_text(page("All market lines — OLBG research desk", body, "markets"))

    # ---- methodology ---------------------------------------------------
    body = """
<h1>Pricing method</h1>
<p class="lede">One arithmetic pipeline creates every line on this site. It is deliberately simple, deterministic and reproducible from
<code>scripts/pricing.py</code> — no black box, no discretionary tweaks per match.</p>

<div class="card">
<h3>1. Market probability (de-vig)</h3>
<p>For each market we read every displayed decimal price. The raw implied probability of an outcome is <span class="mono">1 / decimal</span>.
The overround is the sum of those values. Our market probability is <span class="mono">p_market = (1 / decimal) / overround</span>, so the
bookmaker's margin is removed proportionally across the outcome set. Markets whose overround falls below 0.90 (an incomplete outcome set)
are not priced at all.</p>

<h3>2. Tipster consensus</h3>
<p>OLBG publishes the number of win tips on each outcome. With <span class="mono">N</span> tips in the market and
<span class="mono">t</span> on an outcome, we shrink the raw share toward the market probability:
<span class="mono">p_tip = (t + 6·p_market) / (N + 6)</span>. Six pseudo-tips is enough to stop a one-tip market from moving a price
materially, while still letting a 20-tip consensus register.</p>

<h3>3. Our fair probability</h3>
<p><span class="mono">p_fair = (1 − w)·p_market + w·p_tip</span> with <span class="mono">w = min(0.35, N / (N + 12))</span>.
With no tips w is zero and the line is the pure de-vigged market. With 20 tips w reaches the 0.35 cap. This is why a pick can differ
from the displayed price without ever ignoring it.</p>

<h3>4. Our prices</h3>
<p>Fair American price: for <span class="mono">p ≥ 0.5</span>, <span class="mono">−100p/(1−p)</span>; otherwise
<span class="mono">+100(1−p)/p</span>. Our offered price is the fair decimal price reduced by a 3% margin. The offered price is what we
would need to be paid; it is not a market quote.</p>

<h3>5. Confidence tiers</h3>
<p><strong>High</strong> = our probability ≥ 70% · <strong>Medium</strong> = 55–70% · <strong>Low</strong> = below 55%. The requested price
band is −250 to +10,000 on the displayed price. Note the arithmetic consequence: −250 implies 71.4%, so a high-confidence pick inside the
band can only exist between 70.0% and 71.4%. That is why the board carries one high-confidence pick and a large medium tier, rather than
labelling 60% favourites as high confidence.</p>

<h3>6. Selection rules</h3>
<ul>
<li>Only selections inside the −250 to +10,000 band are eligible.</li>
<li>Match markets need a fair probability of at least 45%; outright markets (tournament, race, championship) at least 8%.</li>
<li>One pick per event, except golf, darts and motor racing outrights where two selections per event are allowed.</li>
<li>OLBG's "Gaelic Sports" category is published as a single sport (Gaelic football and hurling together).</li>
<li>Ranking is by confidence tier, then fair probability, then value at the displayed price.</li>
</ul>

<h3>7. What we do not do</h3>
<ul>
<li>We do not invent a fixture, participant, injury, statistic or lineup. If a field is blank, it was not confirmed.</li>
<li>We do not price a market with an incomplete outcome set.</li>
<li>We do not treat a draw-heavy tipster consensus as a draw probability: any draw selection is capped at three percentage points from
its market probability.</li>
<li>We do not claim our offered price is available anywhere; the displayed OLBG price is the reference for value.</li>
</ul>
</div>

<h2>Edge cases handled in the data</h2>
<div class="tablewrap" style="max-height:none"><table>
<thead><tr><th>Case</th><th>Handling</th></tr></thead><tbody>
<tr><td>Market lists only some outcomes</td><td>Overround below 0.90 → market skipped, count reported on the review page.</td></tr>
<tr><td>"Tie" is the most-tipped selection (handball, gaelic football)</td><td>Draw probability capped at ±3pp from the market probability.</td></tr>
<tr><td>Event page carries no market payload (greyhounds)</td><td>The full field and prices are still read when embedded; where they are absent the pick is Low tier and marked unconfirmed.</td></tr>
<tr><td>No tips on the market</td><td>w = 0, so the line equals the de-vigged market price.</td></tr>
<tr><td>Team names abbreviated by OLBG ("NJ Devils")</td><td>Official facts are matched on the OLBG abbreviation and quoted in full in the pick evidence.</td></tr>
</tbody></table></div>
"""
    (ROOT / "methodology.html").write_text(page("Pricing method — OLBG research desk", body, "method"))

    # ---- sources -------------------------------------------------------
    def log_rows(path, label):
        p = ROOT / path
        if not p.exists():
            return f'<tr><td>{esc(label)}</td><td colspan="3">log not captured</td></tr>'
        out = ""
        for line in p.read_text().strip().splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            name, code, size = parts[0], parts[1], parts[2]
            url = parts[3] if len(parts) > 3 else ""
            cls = "ok" if code.startswith("2") else "flag"
            out += f'<tr><td class="mono">{esc(name)}</td><td><span class="badge {cls}">{esc(code)}</span></td><td class="num">{esc(size)}</td><td class="mono small">{esc(url)}</td></tr>'
        return out

    sport_src = "".join(f'<tr><td>{icon} {esc(name)}</td><td><a href="{url}" target="_blank" rel="noopener">{url}</a></td>'
                        f'<td class="num">{len(by_sport_lines.get(slug,[]))}</td></tr>'
                        for slug, name, icon, url, _n in SPORTS)
    body = f"""
<h1>Sources</h1>
<p class="lede">Two classes of source are used. OLBG supplies the fixture universe, markets, prices and tip counts. Official competition
sources supply form, standings and results where a usable feed exists. Nothing else is used.</p>

<h2>1. OLBG — discovery, markets and prices</h2>
<div class="tablewrap" style="max-height:none"><table>
<thead><tr><th>Sport</th><th>Category page</th><th class="num">Events priced</th></tr></thead>
<tbody>{sport_src}</tbody></table></div>
<p class="notes">Each event row on the sport pages links to its own OLBG event page, which is the exact page the price, market and tip count were read from.
The raw HTML snapshots are kept in <span class="mono">data/raw/</span> and the parsed output in
<a href="data/fixtures.json">data/fixtures.json</a>, <a href="data/markets.json">data/markets.json</a> and <a href="data/lines.json">data/lines.json</a>.</p>

<h2>2. Official sources — form, standings and results</h2>
<div class="tablewrap" style="max-height:none"><table>
<thead><tr><th>Feed</th><th>Status</th><th class="num">Bytes</th><th>URL</th></tr></thead>
<tbody>{log_rows("data/raw/official/_log.txt", "official feeds")}</tbody></table></div>
<p class="notes">NHL and MLB feeds returned complete standings. The F1 classification is taken from the Ergast-format mirror
(api.jolpi.ca) because formula1.com's own results page is script-rendered; the official page is linked alongside every F1 fact so it can be
checked by hand.</p>

<h2>3. Attempted sources that returned nothing usable</h2>
<div class="tablewrap" style="max-height:none"><table>
<thead><tr><th>Endpoint</th><th>Status</th><th class="num">Bytes</th><th>URL</th></tr></thead>
<tbody>{log_rows("data/raw/probe/_log.txt", "official probes")}</tbody></table></div>
<p class="notes">Blocked or missing endpoints are listed rather than hidden. Where no official feed exists, the corresponding form and
availability fields are left blank and flagged on <a href="review.html">Flagged for review</a>.</p>

<h2>4. Reproduction</h2>
<div class="card"><p class="mono small">scripts/fetch-raw.yml (GitHub Action) → data/raw/*.html<br>
scripts/parse_olbg.py → data/fixtures.json<br>
scripts/parse_events.py → data/markets.json<br>
scripts/extract_official.py → data/official_facts.json<br>
scripts/pricing.py → data/lines.json<br>
scripts/select_picks.py → data/picks.json<br>
scripts/build_site.py → this site</p>
<p class="small">The crawler runs on a GitHub runner (manual or daily at 06:17 UTC); the parsing, pricing, selection and build steps run
locally or in the same runner and are deterministic given the snapshots.</p></div>
"""
    (ROOT / "sources.html").write_text(page("Sources — OLBG research desk", body, "sources"))

    # ---- review --------------------------------------------------------
    pick_flags = ""
    for p in picks:
        pr = preds.get(p["pick_id"], {})
        for f in (pr.get("flags") or []):
            pick_flags += (f'<tr><td>{esc(p["sport"])}</td><td><a href="sports/{p["sport_slug"]}.html#{p["pick_id"]}">'
                           f'{esc(p["selection"])}</a></td><td>{esc(f)}</td>'
                           f'<td><a href="{esc(p["olbg_url"])}" target="_blank" rel="noopener">OLBG</a></td></tr>')
    global_rows = "".join(f'<tr><td><strong>{esc(t)}</strong><div class="small">{esc(d)}</div></td>'
                          f'<td><a href="{esc(u)}" target="_blank" rel="noopener">source</a></td></tr>'
                          for t, d, u in GLOBAL_FLAGS)
    body = f"""
<h1>Flagged for review</h1>
<p class="lede">Everything that could not be confirmed, every gap in the source coverage, and every judgement call in the pricing
is listed here. These items do not block publication, but they are the first place to check before acting on a pick.</p>

<div class="alert bad"><span class="ic">⚑</span><div><strong>{len(picks)} picks are published, and
{sum(1 for p in picks for f in (preds.get(p["pick_id"],{}).get("flags") or []))} individual pick-level flags are open.</strong>
None of them is a fabricated value: where data was missing the field is blank.</div></div>

<h2>Site-wide findings</h2>
<div class="tablewrap" style="max-height:none"><table>
<thead><tr><th>Finding</th><th>Source</th></tr></thead><tbody>{global_rows}</tbody></table></div>

<h2>Pick-level flags</h2>
<div class="tablewrap"><table>
<thead><tr><th>Sport</th><th>Pick</th><th>Flag</th><th>Source</th></tr></thead>
<tbody>{pick_flags or '<tr><td colspan="4">No pick-level flags.</td></tr>'}</tbody></table></div>

<h2>Unconfirmed fields, by sport</h2>
<div class="tablewrap" style="max-height:none"><table>
<thead><tr><th>Sport</th><th>Form / recent results</th><th>Injuries &amp; team news</th><th>Why</th></tr></thead><tbody>
<tr><td>Tennis</td><td>Not captured</td><td>Not captured</td><td>ATP and WTA endpoints returned 403; no official feed ingested.</td></tr>
<tr><td>Cricket</td><td>Not captured</td><td>Not captured</td><td>No machine-readable official ICC or board feed was retrievable.</td></tr>
<tr><td>Rugby Union / League</td><td>Not captured</td><td>Not captured</td><td>URC fixtures endpoint 404; league pages script-rendered.</td></tr>
<tr><td>Handball</td><td>Not captured</td><td>Not captured</td><td>EHF match endpoint 404.</td></tr>
<tr><td>Volleyball</td><td>Not captured</td><td>Not captured</td><td>Only a schedule shell was retrievable, no per-match data.</td></tr>
<tr><td>Basketball</td><td>Not captured</td><td>Not captured</td><td>NBA CDN endpoints returned 403.</td></tr>
<tr><td>Ice Hockey</td><td><span class="badge ok">NHL standings</span></td><td>Not captured</td><td>NHL API supplies records, goal data and streaks; injury reports were unavailable.</td></tr>
<tr><td>Baseball</td><td><span class="badge ok">MLB standings</span></td><td>Not captured</td><td>MLB Stats API supplies records; no confirmed lineup.</td></tr>
<tr><td>Motor Racing</td><td><span class="badge ok">F1 classification</span></td><td>n/a</td><td>Driver points and wins after round 18.</td></tr>
<tr><td>Golf</td><td>Not captured</td><td>Not captured</td><td>Leaderboard page is script-rendered; fields not confirmed.</td></tr>
<tr><td>Darts / Snooker</td><td>Not captured</td><td>Not captured</td><td>PDC and WST pages are script-rendered; no entry list confirmed.</td></tr>
<tr><td>Gaelic Sports</td><td>Not captured</td><td>Not captured</td><td>GAA fixtures page retrieved but club panel data is not published there.</td></tr>
<tr><td>Greyhounds</td><td>Not captured</td><td>Not captured</td><td>GBGB endpoint 404; race fields come from the OLBG race market only.</td></tr>
</tbody></table></div>
<div class="notes">If you want any of these confirmed, the fastest route is to give this session access to a licensed data feed
(for example an official injury API) and the fields can be filled and re-verified row by row.</div>
"""
    (ROOT / "review.html").write_text(page("Flagged for review — OLBG research desk", body, "review"))

    (ROOT / ".nojekyll").write_text("")
    print(f"built index + {len(SPORTS)} sport pages + markets/methodology/sources/review")
    print(f"stats: events={n_events} markets={n_markets} outcomes={n_outcomes} picks={len(picks)}")


if __name__ == "__main__":
    build()
