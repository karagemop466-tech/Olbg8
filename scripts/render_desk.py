#!/usr/bin/env python3
"""Render the static OLBG desk dashboard from data/desk-20261027.json.

Everything is generated as plain HTML so the executive summary, picks and tables
are visible without JavaScript and every row can be checked against its source
links. JavaScript only adds filtering.
"""
from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "data" / "desk-20261027.json").read_text(encoding="utf-8"))
ASSETS = ROOT / "assets"
SPORTS_DIR = ROOT / "sports"
SPORTS_DIR.mkdir(exist_ok=True)

S = DATA["summary"]
SPORTS = DATA["sports"]
EVENTS = DATA["events"]
LINES = DATA["lines"]
PICKS = DATA["picks"]
FLAGS = DATA["flags"]
SOURCES = DATA["sources"]

NAV = [
    ("home", "Overview", "index.html"),
    ("picks", "Today's picks", "picks.html"),
    ("lines", "Our lines", "lines.html"),
    ("matches", "Matches", "matches.html"),
    ("sources", "Sources", "sources.html"),
    ("methodology", "Methodology", "methodology.html"),
    ("flagged", "Flagged for review", "flagged.html"),
]


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def safe(url: str) -> str:
    return url if isinstance(url, str) and url.startswith(("http://", "https://")) else ""


def link(url: str, label: str, css: str = "src-link") -> str:
    u = safe(url)
    return f'<a class="{css}" href="{esc(u)}" target="_blank" rel="noopener noreferrer">{esc(label)}</a>' if u else '<span class="blank" title="No official link was captured">—</span>'


def us(value) -> str:
    if value in (None, "", 0):
        return "—"
    try:
        n = int(value)
    except Exception:
        return esc(value)
    return f"+{n}" if n > 0 else str(n)


def badge(conf: str) -> str:
    return f'<span class="badge {esc(conf)}">{esc((conf or "—").upper())}</span>'


def when(iso: str) -> str:
    if not iso:
        return "Not stated"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d %b %H:%M") + " UTC"
    except Exception:
        return esc(iso)


def source_cell(urls: list[dict], olbg: str = "") -> str:
    parts = []
    seen = set()
    for item in urls or []:
        u = safe(item.get("url", ""))
        if u and u not in seen:
            seen.add(u)
            parts.append(link(u, item.get("name") or "Official"))
    if olbg and olbg not in seen:
        parts.append(link(olbg, "OLBG event"))
    return '<div class="sources">' + "".join(parts) + "</div>" if parts else '<div class="sources"><span class="blank">—</span></div>'


def page(title: str, body: str, key: str, base: str = "", description: str = "") -> str:
    nav = "".join(
        f'<a class="{"active" if k == key else ""}" href="{base}{href}">{esc(label)}</a>'
        for k, label, href in NAV)
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{esc(description or 'OLBG multi-sport research desk: originated lines, picks and source links.')}">
<title>{esc(title)} · OLBG desk</title>
<link rel="stylesheet" href="{base}assets/desk.css">
</head>
<body data-page="{esc(key)}">
<header class="topbar"><div class="wrap topbar-inner">
<a class="brand" href="{base}index.html"><span class="brand-mark">O</span><span>OLBG desk</span></a>
<nav class="nav" aria-label="Primary navigation">{nav}</nav>
</div></header>
<main class="wrap">{body}</main>
<footer class="footer"><div class="wrap">
<p><strong>OLBG desk</strong> · snapshot {esc(DATA['capture_utc'])} · {S['events']} captured events · {S['picks']} written picks.</p>
<p>Independent research, not OLBG advice and not a bookmaker offer. Blank fields are deliberate. Check the linked official source and the live market before relying on anything here. Only bet where lawful and only what you can afford to lose.</p>
<p><a href="{base}data/desk-20261027.json">Download the full dataset (JSON)</a> · <a href="{base}previous-desk/index.html">Previous 05:26 UTC desk (archive)</a> · <a href="{base}research-desk/index.html">Earlier audit desk</a> · <a href="{base}evidence-lab/index.html">Evidence lab</a></p>
</div></footer>
<script src="{base}assets/desk.js" defer></script>
</body></html>'''


def hero(eyebrow: str, title: str, text: str, actions: str = "") -> str:
    return f'''<section class="hero"><p class="eyebrow">{esc(eyebrow)}</p>
<h1>{esc(title)}</h1><p class="lede">{esc(text)}</p>{actions}</section>'''


def kpi(value, label, note="") -> str:
    return f'<div class="kpi"><div class="kpi-value">{esc(value)}</div><div class="kpi-label">{esc(label)}</div><div class="kpi-note">{esc(note)}</div></div>'


def section_heading(title: str, sub: str = "", right: str = "") -> str:
    return f'<div class="section-head"><div><h2>{esc(title)}</h2>{f"<p>{esc(sub)}</p>" if sub else ""}</div>{right}</div>'


def pick_row(p: dict, show_sport: bool = True) -> str:
    return f'''<tr data-sport="{esc(p['sport_slug'])}" data-conf="{esc(p['confidence'])}" data-search="{esc((p['event'] + ' ' + p['selection'] + ' ' + p['sport']).lower())}">
<td class="num">{p['pick_no']}</td>
{f'<td>{esc(p["sport"])}</td>' if show_sport else ''}
<td><strong>{esc(p['event'])}</strong><br><span class="muted">{esc(p['competition'])} · {when(p['start_utc'])}</span></td>
<td><strong class="selection">{esc(p['selection'])}</strong><br><span class="muted">{esc(p['market'])}</span></td>
<td class="mono">{us(p['displayed_american'])}</td>
<td class="mono">{us(p['our_american'])}<br><span class="muted">edge {p['edge_pp']:+.1f} pp</span></td>
<td>{badge(p['confidence'])}</td>
<td>{source_cell([dict(name=p['official_name'], url=p['official_url'])], p['olbg_url'])}</td>
</tr>'''


def pick_card(p: dict) -> str:
    facts = p["facts"]
    fact_rows = []
    for label, values in (("Fixture / identity", facts.get("identity") or []),
                          ("Official statistics", facts.get("stats") or []),
                          ("Recent official results", facts.get("form") or [])):
        if isinstance(values, str):
            values = [values] if values else []
        for v in values[:3]:
            fact_rows.append(f'<li><span>{esc(label)}:</span> {esc(v)}</li>')
    if facts.get("selection"):
        fact_rows.append(f'<li><span>Selection-specific official data:</span> {esc(facts["selection"])}</li>')
    if facts.get("availability"):
        fact_rows.append(f'<li><span>Availability:</span> {esc(facts["availability"])}</li>')
    else:
        fact_rows.append('<li><span>Availability:</span> <em>Not published in the captured official sources — left blank and flagged.</em></li>')
    flags = "".join(f'<span class="flag-chip">{esc(f)}</span>' for f in p["official_flags"][:3])
    return f'''<article class="pick-card" id="pick-{p['pick_no']}">
<div class="pick-top"><span class="pick-index">PICK #{p['pick_no']} · {esc(p['sport'])}</span>{badge(p['confidence'])}</div>
<h3>{esc(p['selection'])} <span class="pick-market">— {esc(p['market'])}</span></h3>
<p class="pick-event">{esc(p['event'])} · <span class="muted">{esc(p['competition'])} · {when(p['start_utc'])}</span></p>
<div class="pick-prices"><div><span>OLBG shows</span><strong>{us(p['displayed_american'])}</strong><small>decimal {esc(p['decimal'])} · fractional {esc(p['fractional'] or '—')}</small></div>
<div><span>Our fair line</span><strong>{us(p['our_american'])}</strong><small>{p['fair_pct']:.1f}% fair probability · edge {p['edge_pp']:+.1f} pp</small></div>
<div><span>Tip support</span><strong>{p['win_tips']}/{p['total_tips'] or '—'}</strong><small>{p['consensus_pct']:.0f}% consensus on this side</small></div></div>
<p class="prediction">{esc(p['prediction'])}</p>
<ul class="facts">{''.join(fact_rows)}</ul>
<div class="pick-sources"><strong>Sources:</strong> {source_cell(p['official_urls'], p['olbg_url'])}</div>
{('<div class="pick-flags">' + flags + '</div>') if flags else ''}
</article>'''


def line_rows(subset) -> str:
    out = []
    for l in subset:
        if not l["selections"]:
            # An OLBG market with no displayed price is still a row: blank cells
            # are intentional and the absence is flagged for review.
            out.append(f'''<tr data-sport="{esc(l['sport_slug'])}" data-family="{esc(l['family'])}" data-unpriced="1" data-search="{esc((l['event'] + ' ' + l['market'] + ' ' + l['sport'] + ' unpriced').lower())}">
<td>{esc(l['sport'])}</td>
<td><strong>{esc(l['event'])}</strong><br><span class="muted">{when(l['start_utc'])} · {esc(l['competition'])}</span></td>
<td>{esc(l['market'])}<br><span class="muted">{esc(l['family'])}</span></td>
<td><em>No priced selection published</em></td>
<td class="mono">—</td><td class="mono">—</td><td class="mono">—</td><td class="mono">—</td>
<td>{source_cell([dict(name=l['official_name'], url=l['official_url'])], l['olbg_url'])}</td>
</tr>''')
            continue
        for sel in l["selections"]:
            out.append(f'''<tr data-sport="{esc(l['sport_slug'])}" data-family="{esc(l['family'])}" data-search="{esc((l['event'] + ' ' + l['market'] + ' ' + sel['selection'] + ' ' + l['sport']).lower())}">
<td>{esc(l['sport'])}</td>
<td><strong>{esc(l['event'])}</strong><br><span class="muted">{when(l['start_utc'])} · {esc(l['competition'])}</span></td>
<td>{esc(l['market'])}<br><span class="muted">{esc(l['family'])}</span></td>
<td><strong>{esc(sel['selection'])}</strong></td>
<td class="mono">{us(sel['displayed_american'])}<br><span class="muted">{esc(sel['decimal'])} dec</span></td>
<td class="mono">{us(sel['our_american'])}<br><span class="muted">{sel['fair_pct']:.1f}%</span></td>
<td class="mono">{sel['edge_pp']:+.1f}</td>
<td class="mono">{sel['win_tips']}/{sel['total_tips'] or '—'}</td>
<td>{source_cell([dict(name=l['official_name'], url=l['official_url'])], l['olbg_url'])}</td>
</tr>''')
    return "".join(out)


def lines_table(subset, table_id: str) -> str:
    return f'''<div class="table-tools"><input type="search" class="filter-input" data-filter="{table_id}" placeholder="Search event, market or selection…" aria-label="Filter lines"><select class="filter-select" data-filter-sport="{table_id}"><option value="">All sports</option>{''.join(f'<option value="{esc(s["key"])}">{esc(s["label"])}</option>' for s in SPORTS)}</select><span class="filter-count" data-count="{table_id}"></span></div>
<div class="table-wrap"><table class="data-table" id="{table_id}"><thead><tr><th>Sport</th><th>Event</th><th>Market</th><th>Selection</th><th>OLBG price</th><th>Our fair line</th><th>Edge pp</th><th>Tips</th><th>Sources</th></tr></thead><tbody>{line_rows(subset)}</tbody></table></div>'''


def match_row(e: dict) -> str:
    total = f'{e["independent_total"]:.2f}' if e.get("independent_total") else "—"
    return f'''<tr data-sport="{esc(e['sport_slug'])}" data-horizon="{esc(e['horizon'])}" data-search="{esc((e['name'] + ' ' + e['sport'] + ' ' + e['competition']).lower())}">
<td class="mono">{when(e['start_utc'])}<br><span class="badge neutral">{esc(e['horizon'])}</span></td>
<td>{esc(e['sport'])}</td>
<td><strong>{esc(e['name'])}</strong><br><span class="muted">{esc(e['competition'])}</span></td>
<td class="mono">{len(e['market_names'])}</td>
<td class="mono">{total}</td>
<td><span class="badge {'ok' if e['official']['level'] == 'event' else 'neutral'}">{esc(e['official']['level'])}</span></td>
<td>{'Upcoming' if e['upcoming'] else 'Started / closed'}</td>
<td>{source_cell([dict(name=e['official']['name'], url=e['official']['url'])], e['olbg_url'])}</td>
</tr>'''


def matches_table(events, table_id: str) -> str:
    return f'''<div class="table-tools"><input type="search" class="filter-input" data-filter="{table_id}" placeholder="Search event or sport…" aria-label="Filter matches"><span class="filter-count" data-count="{table_id}"></span></div>
<div class="table-wrap"><table class="data-table" id="{table_id}"><thead><tr><th>Start (UTC)</th><th>Sport</th><th>Event</th><th>Markets</th><th>Independent total</th><th>Official crosswalk</th><th>State</th><th>Sources</th></tr></thead><tbody>{''.join(match_row(e) for e in events)}</tbody></table></div>'''


def flag_row(f: dict) -> str:
    return f'''<tr data-level="{esc(f['level'])}" data-sport="{esc(f['sport'])}" data-search="{esc((f['sport'] + ' ' + f['subject'] + ' ' + f['detail']).lower())}">
<td><span class="badge {'danger' if f['level'] == 'high' else 'warn' if f['level'] == 'medium' else 'neutral'}">{esc(f['level'])}</span></td>
<td>{esc(f['sport'])}</td>
<td><strong>{esc(f['subject'])}</strong></td>
<td>{esc(f['detail'])}</td>
<td>{source_cell(f['urls'])}</td>
</tr>'''


# ---------------------------------------------------------------------------
# CSS and JS
# ---------------------------------------------------------------------------
CSS = r'''
:root{--ink:#132038;--muted:#5d6b83;--line:#dde5ef;--bg:#f5f8fc;--card:#fff;--accent:#0b63ce;--accent-soft:#e8f1ff;--high:#0a7d5a;--medium:#a46800;--low:#5c6b80;--danger:#a12626;--shadow:0 2px 12px rgba(20,40,80,.06)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}.wrap{max-width:1220px;margin:0 auto;padding:0 22px}
.topbar{background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:20}.topbar-inner{display:flex;align-items:center;gap:24px;min-height:64px;flex-wrap:wrap}.brand{display:flex;align-items:center;gap:9px;font-weight:750;font-size:17px;color:var(--ink)}.brand-mark{display:grid;place-items:center;width:30px;height:30px;border-radius:9px;background:var(--accent);color:#fff;font-weight:800}
.nav{display:flex;gap:4px;flex-wrap:wrap;margin-left:auto}.nav a{padding:8px 11px;border-radius:8px;color:var(--muted);font-size:13.5px;font-weight:600;white-space:nowrap}.nav a:hover,.nav a.active{background:var(--accent-soft);color:var(--accent);text-decoration:none}
main{padding-top:28px;padding-bottom:48px}.hero{background:linear-gradient(135deg,#0b2d5c,#0b63ce);color:#fff;border-radius:18px;padding:34px 36px;margin-bottom:22px}.hero h1{font-size:31px;line-height:1.2;margin:6px 0 12px;letter-spacing:-.5px}.hero .lede{max-width:900px;color:#dce9fb;font-size:16px;margin:0}.eyebrow{text-transform:uppercase;letter-spacing:.13em;font-size:11.5px;font-weight:700;color:#9dc3f5;margin:0}.hero .actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}.button{display:inline-block;padding:11px 17px;border-radius:9px;background:#fff;color:var(--accent);font-weight:700;font-size:14px}.button.primary{background:#fff;color:#0b3f86}.button.ghost{background:rgba(255,255,255,.14);color:#fff;border:1px solid rgba(255,255,255,.45)}.meta-line{color:#bcd5f5;font-size:12.5px;margin:16px 0 0}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:18px 0 26px}.kpi{background:var(--card);border:1px solid var(--line);border-radius:13px;padding:16px 18px;box-shadow:var(--shadow)}.kpi-value{font-size:28px;font-weight:800;letter-spacing:-1px}.kpi-label{font-weight:700;font-size:13px;margin-top:2px}.kpi-note{font-size:12px;color:var(--muted)}
section{margin-bottom:30px}.section-head{display:flex;align-items:flex-end;justify-content:space-between;gap:14px;margin:0 0 12px}.section-head h2{font-size:21px;margin:0;letter-spacing:-.3px}.section-head p{color:var(--muted);margin:3px 0 0;font-size:14px}.section-head a{font-weight:700;font-size:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:13px;box-shadow:var(--shadow)}.pad{padding:18px}.grid{display:grid;gap:14px}.grid.two{grid-template-columns:repeat(auto-fit,minmax(290px,1fr))}.grid.three{grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}.card h3{margin:0 0 8px;font-size:16px}.card p{margin:0;font-size:14px;color:var(--muted)}
.table-wrap{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:13px;box-shadow:var(--shadow)}table{width:100%;border-collapse:collapse;font-size:13.5px}th{text-align:left;background:#f0f5fb;color:#334765;font-size:12px;text-transform:uppercase;letter-spacing:.05em;padding:11px 12px;border-bottom:1px solid var(--line);white-space:nowrap}td{padding:11px 12px;border-bottom:1px solid #edf2f8;vertical-align:top}tbody tr:last-child td{border-bottom:0}tbody tr:hover{background:#f8fbff}.mono{font-variant-numeric:tabular-nums;white-space:nowrap}.num{font-weight:700;color:var(--muted)}.muted{color:var(--muted);font-size:12px}.selection{color:#0b3f86}.sources{display:flex;flex-wrap:wrap;gap:6px}.src-link{display:inline-block;padding:3px 8px;border:1px solid #cfe0f5;border-radius:6px;background:#f4f9ff;font-size:11.5px;font-weight:600;white-space:nowrap}.blank{color:#9aa8bb}
.badge{display:inline-block;padding:3px 8px;border-radius:20px;font-size:10.5px;font-weight:800;letter-spacing:.04em;background:#eef2f7;color:#42536b}.badge.high{background:#d9f5e9;color:var(--high)}.badge.medium{background:#fff0d2;color:var(--medium)}.badge.low{background:#eceff4;color:var(--low)}.badge.ok{background:#d9f5e9;color:var(--high)}.badge.neutral{background:#eaf0f8;color:#4b6281}.badge.danger{background:#fde4e4;color:var(--danger)}.badge.warn{background:#fff0d2;color:var(--medium)}
.table-tools{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:0 0 11px}.filter-input,.filter-select{padding:9px 12px;border:1px solid var(--line);border-radius:9px;background:#fff;font-size:14px;min-width:230px}.filter-select{min-width:160px}.filter-count{color:var(--muted);font-size:13px;font-weight:600}
.pick-card{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:13px;padding:20px 22px;margin:0 0 15px;box-shadow:var(--shadow)}.pick-top{display:flex;justify-content:space-between;align-items:center;gap:10px}.pick-index{font-size:11.5px;text-transform:uppercase;letter-spacing:.1em;font-weight:800;color:var(--accent)}.pick-card h3{font-size:20px;margin:8px 0 2px;letter-spacing:-.3px}.pick-market{font-size:14px;font-weight:500;color:var(--muted)}.pick-event{margin:0 0 14px;font-size:14px}.pick-prices{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:12px 0 14px}.pick-prices>div{background:#f5f9ff;border:1px solid #e1ecfb;border-radius:10px;padding:10px 12px}.pick-prices span{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:700}.pick-prices strong{display:block;font-size:21px;letter-spacing:-.5px}.pick-prices small{display:block;color:var(--muted);font-size:11.5px}.prediction{font-size:15px;line-height:1.72;background:#fbfdff;border:1px solid #e7eef8;border-radius:10px;padding:14px 16px;margin:0 0 12px}.facts{margin:0 0 12px;padding-left:18px;font-size:13px;color:#334765}.facts li{margin:3px 0}.facts span{font-weight:700}.pick-sources{font-size:13px}.pick-flags{margin-top:10px;display:flex;gap:6px;flex-wrap:wrap}.flag-chip{background:#fff6e6;border:1px solid #f3dfb5;color:#805a12;border-radius:6px;padding:3px 8px;font-size:11px}
.callout{background:#fff8e8;border:1px solid #f0dcae;border-radius:11px;padding:13px 16px;margin:0 0 18px;font-size:14px}.callout.blue{background:#eef6ff;border-color:#cfe0f5}.callout.red{background:#fff1f1;border-color:#f2cccc}.callout strong{color:var(--ink)}
.sport-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:11px}.sport-card{display:block;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:15px 16px;color:var(--ink);box-shadow:var(--shadow)}.sport-card:hover{text-decoration:none;border-color:#9cc3f2;transform:translateY(-1px)}.sport-card h3{margin:0 0 6px;font-size:15px}.sport-card .count{font-size:25px;font-weight:800;letter-spacing:-1px}.sport-card .count-label{font-size:11.5px;color:var(--muted)}.sport-card .mini{display:flex;gap:8px;font-size:12px;color:var(--accent);margin-top:8px;font-weight:700}
.coverage td:first-child{font-weight:700}.prose{max-width:900px}.prose h3{margin-top:22px}.prose p,.prose li{font-size:14.5px}.prose code{background:#eef3fa;padding:2px 5px;border-radius:4px;font-size:13px}.formula{background:#0d2647;color:#d8e9ff;border-radius:10px;padding:16px 18px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;line-height:1.7;overflow-x:auto}.jump{display:flex;flex-wrap:wrap;gap:7px;margin:0 0 16px}.jump a{padding:6px 11px;border:1px solid var(--line);border-radius:20px;background:#fff;font-size:12.5px;font-weight:600}
.footer{border-top:1px solid var(--line);background:#fff;margin-top:30px;padding:24px 0;font-size:12.5px;color:var(--muted)}.footer p{margin:4px 0}.footer a{font-weight:600}
@media(max-width:760px){.hero{padding:24px 20px}.hero h1{font-size:24px}.nav{width:100%;margin:0 0 8px}.nav a{padding:6px 8px;font-size:12.5px}.wrap{padding:0 14px}table{font-size:12.5px}th,td{padding:9px 8px}}
'''

JS = r'''
/* Progressive enhancement: table filters only. All content is in the HTML. */
(() => {
  "use strict";
  const tables = [...document.querySelectorAll("table.data-table")];
  const wire = (table) => {
    const id = table.id;
    const search = document.querySelector(`[data-filter="${id}"]`);
    const sport = document.querySelector(`[data-filter-sport="${id}"]`);
    const count = document.querySelector(`[data-count="${id}"]`);
    const rows = [...table.querySelectorAll("tbody tr")];
    if (!search && !sport) return;
    const update = () => {
      const q = (search?.value || "").trim().toLowerCase();
      const sp = sport?.value || "";
      let shown = 0;
      for (const row of rows) {
        const ok = (!q || (row.dataset.search || "").includes(q)) &&
                    (!sp || row.dataset.sport === sp);
        row.hidden = !ok;
        if (ok) shown++;
      }
      if (count) count.textContent = `${shown} of ${rows.length} rows`;
    };
    search?.addEventListener("input", update);
    sport?.addEventListener("change", update);
    update();
  };
  tables.forEach(wire);
  // Flagged page severity filter.
  const sev = document.getElementById("severity-filter");
  if (sev) {
    sev.addEventListener("change", () => {
      for (const row of document.querySelectorAll("#flags-table tbody tr")) {
        row.hidden = Boolean(sev.value) && row.dataset.level !== sev.value;
      }
    });
  }
})();
'''


def render() -> int:
    (ASSETS / "desk.css").write_text(CSS, encoding="utf-8")
    (ASSETS / "desk.js").write_text(JS, encoding="utf-8")

    # ---------------- index ----------------
    top_picks = sorted(PICKS, key=lambda p: ({"high": 3, "medium": 2, "low": 1}[p["confidence"]],
                                             p["score"]), reverse=True)[:10]
    today_high = [p for p in PICKS if p["horizon"] == "today" and p["confidence"] == "high"]
    coverage = "".join(f'''<tr class="coverage">
<td><a href="sports/{esc(s['key'])}.html">{esc(s['label'])}</a></td>
<td>{s['events']}</td><td>{s['upcoming']}</td><td>{s['lines']}</td><td>{s['priced_selections']}</td>
<td><strong>{s['picks']}</strong></td><td>{s['high']}</td>
<td><span class="badge {'ok' if s['official_status'] == 200 else 'warn'}">official feed {esc(s['official_status'])}</span></td>
<td>{link(s['official_url'], s['official_name'])} {link(s['hub'], 'OLBG hub')}</td></tr>''' for s in SPORTS)
    hero_actions = ('<div class="actions"><a class="button primary" href="picks.html">See every written pick →</a>'
                    '<a class="button ghost" href="lines.html">See our originated lines</a>'
                    '<a class="button ghost" href="flagged.html">What needs review</a></div>')
    index_body = f'''
{hero("Executive summary · " + DATA["as_of"],
      f"{S['picks']} written picks across {S['sports_with_picks']} OLBG sports, with an originated line for every captured market.",
      f"OLBG's SvelteKit event feeds were captured at {DATA['capture_utc']}. Every one of the {S['priced_selections']} priced selections in {S['priced_markets']} markets has our own fair price, a source link, and a clear confidence label. The picks are on the Picks page and repeated on each sport page.",
      hero_actions)}
<div class="callout blue"><strong>Where are the picks?</strong> <a href="picks.html">Today's picks</a> lists every recommendation with a full written prediction. Each sport has its own page with the same picks at the top. <a href="lines.html">Our lines</a> shows the entire price book, not just the picks. <a href="flagged.html">Flagged for review</a> lists every gap.</div>
<section class="kpis">{kpi(S['picks'], "Written picks", "unique, ≥30 words")}{kpi(S['high'], "High confidence", "all inside −250 to +10000")}{kpi(S['priced_selections'], "Originated lines", f"across {S['priced_markets']} markets")}{kpi(S['upcoming'], "Upcoming OLBG events", f"{S['today_events']} start today")}{kpi(S['event_official_links'], "Official event pages", "identity-matched")}{kpi(S['flags'], "Flagged items", "published for review")}</section>
<section>{section_heading("Highest-confidence selections", "The shortlist for today and the coming week. All prices shown are OLBG quotes at snapshot time; our fair line is independent.", '<a href="picks.html">All picks →</a>')}
<div class="table-wrap"><table class="data-table"><thead><tr><th>#</th><th>Sport</th><th>Event</th><th>Selection</th><th>OLBG</th><th>Our line</th><th>Confidence</th><th>Sources</th></tr></thead><tbody>{''.join(pick_row(p) for p in top_picks)}</tbody></table></div>
{('<p class="muted" style="margin-top:10px">' + str(len(today_high)) + ' of the high-confidence picks start today (UTC).</p>') if today_high else ''}
</section>
<section>{section_heading("Coverage by sport", "Every requested sport is listed. A zero means OLBG had no tipped market in the capture, not that the sport has no fixtures.", '<a href="matches.html">Full inventory →</a>')}
<div class="table-wrap"><table class="data-table"><thead><tr><th>Sport</th><th>Events</th><th>Upcoming</th><th>Priced markets</th><th>Lines</th><th>Picks</th><th>High</th><th>Official feed</th><th>Sources</th></tr></thead><tbody>{coverage}</tbody></table></div></section>
<section>{section_heading("Browse by sport", "Each category page repeats the picks, lines, matches and flags for that sport.")}
<div class="sport-grid">{''.join(f'<a class="sport-card" href="sports/{esc(s["key"])}.html"><h3>{esc(s["label"])}</h3><div class="count">{s["picks"]}</div><div class="count-label">written picks</div><div class="mini"><span>{s["lines"]} markets priced</span><span>·</span><span>{s["upcoming"]} upcoming</span></div></a>' for s in SPORTS)}</div></section>
<section>{section_heading("What is verified and what is not", "The distinction is important: a market price and a governing-body fact are different things.")}
<div class="grid three"><div class="card pad"><h3>1 · Market facts</h3><p>Event names, start times, market names, selections, OLBG prices and tip counts come directly from the captured OLBG SvelteKit payloads. Every row links to its OLBG event page.</p></div>
<div class="card pad"><h3>2 · Official facts</h3><p>Form, standings, rankings, results and fixture identity come from official league/tour feeds captured at the same time. Where an official page was blocked, that is flagged rather than filled in.</p></div>
<div class="card pad"><h3>3 · Our calculations</h3><p>Fair prices, edges and confidence labels are our own transparent calculations, not bookmaker offers. <a href="methodology.html">Read the formula</a>.</p></div></div></section>
<section>{section_heading("Next upcoming events", "First 15 in the captured inventory. The Matches page has all of them.", '<a href="matches.html">All matches →</a>')}
{matches_table([e for e in EVENTS if e['upcoming']][:15], 'home-matches')}</section>
'''
    (ROOT / "index.html").write_text(page("Overview", index_body, "home", description="Executive summary of OLBG picks, originated lines and official sources."), encoding="utf-8")

    # ---------------- picks ----------------
    by_sport = defaultdict(list)
    for p in PICKS:
        by_sport[p["sport_slug"]].append(p)
    jump = '<div class="jump">' + "".join(
        f'<a href="#sport-{esc(s["key"])}">{esc(s["label"])} ({len(by_sport[s["key"]])})</a>' for s in SPORTS) + '</div>'
    groups = []
    for s in SPORTS:
        ps = by_sport[s["key"]]
        title = s["label"] + " · " + str(len(ps)) + " picks"
        right = '<a href="sports/' + esc(s["key"]) + '.html">Sport page &rarr;</a>'
        opening = '<section id="sport-' + esc(s["key"]) + '">' + section_heading(title, s["note"], right)
        if ps:
            content = "".join(pick_card(p) for p in ps)
        else:
            content = ('<div class="callout red"><strong>No OLBG market rows.</strong> The OLBG hub and All Events '
                       'feed returned zero tipped events for this sport at capture, so no selection could be priced '
                       'or written. Official sources are linked on the sport page and every gap is listed on '
                       'Flagged for Review.</div>')
        groups.append(opening + content + "</section>")
    picks_body = f'''{hero("Picks · " + DATA["as_of"], f"{S['picks']} fully written selections, grouped by sport.",
      "Each pick names the selection and market, shows the OLBG price beside our originated fair line, labels confidence as low / medium / high, and includes a unique prediction with official-source facts and links.")}
<div class="callout"><strong>Price band:</strong> every published pick sits between −250 and +10000. Shorter prices are still priced in <a href="lines.html">Our lines</a> but are not promoted as high-confidence picks.</div>
{jump}
<section>{section_heading("All picks at a glance", "One line per pick; the full written prediction is below in the same order.")}
<div class="table-wrap"><table class="data-table"><thead><tr><th>#</th><th>Sport</th><th>Event</th><th>Selection</th><th>OLBG</th><th>Our line</th><th>Confidence</th><th>Sources</th></tr></thead><tbody>{''.join(pick_row(p) for p in PICKS)}</tbody></table></div></section>
{''.join(groups)}'''
    (ROOT / "picks.html").write_text(page("Today's picks", picks_body, "picks", description="All written OLBG picks with confidence, prices and sources."), encoding="utf-8")

    # ---------------- lines ----------------
    lines_body = f'''{hero("Originated lines · " + DATA["as_of"], f"An independent fair price for all {S['priced_selections']} priced selections.",
      f"We de-vig every OLBG market, blend in tip consensus and (where available) official strength data, then publish our own American price. This is a research line, not a bookmaker offer.")}
<div class="callout blue"><strong>How to read this table:</strong> “OLBG price” is the price displayed in the captured event payload. “Our fair line” is our calculated no-margin price. “Edge pp” is our fair probability minus the de-vigged market probability, in percentage points. Every row links to an official source and the OLBG event.</div>
{section_heading("Market coverage", "One row per selection. Filter by sport or search for a team, player or market.")}
{lines_table(LINES, 'all-lines')}
<section class="prose" style="margin-top:26px"><h3>Independent totals and spreads</h3><p>Where an official scoring feed covered both sides of a fixture, an independent total was calculated from official goals/runs per game. It appears on the <a href="matches.html">Matches</a> page in the “Independent total” column. Where no official scoring feed was captured, that cell is left blank and flagged — no number is inferred.</p></section>'''
    (ROOT / "lines.html").write_text(page("Our lines", lines_body, "lines", description="Originated fair prices for every captured OLBG market selection."), encoding="utf-8")

    # ---------------- matches ----------------
    matches_body = f'''{hero("Matches & events · " + DATA["as_of"], f"All {S['events']} captured OLBG event pages, {S['upcoming']} still upcoming.",
      "OLBG publishes tipped events rather than a complete fixture database. Each row shows the number of markets captured, the official-source crosswalk level and a direct source link.")}
<div class="callout"><strong>Time note:</strong> {esc(DATA['timezone_note'])} Where OLBG and the official feed disagree on a start time, the row is flagged on the review page.</div>
{section_heading("Full inventory", "Includes events that have already started; those are kept for audit but are not eligible for picks.")}
{matches_table(EVENTS, 'all-matches')}'''
    (ROOT / "matches.html").write_text(page("Matches", matches_body, "matches", description="Complete OLBG event inventory with official crosswalks."), encoding="utf-8")

    # ---------------- sources ----------------
    sport_by_key = {s["key"]: s for s in SPORTS}
    src_row_parts = []
    for s in SOURCES:
        extra = ""
        if s["role"] == "discovery" and s["key"].startswith("olbg-"):
            sport = sport_by_key.get(s["key"][5:])
            if sport:
                extra = " " + link(sport["official_url"], "Official directory")
        src_row_parts.append(f'''<tr data-search="{esc((s['key'] + ' ' + s['name'] + ' ' + s['role']).lower())}">
<td><strong>{esc(s['name'])}</strong><br><span class="muted">{esc(s['key'])}</span></td>
<td>{esc(s['role'])}</td><td>{esc(s['kind'])}</td>
<td><span class="badge {'ok' if s['status'] == 200 else 'warn'}">{esc(s['status'])}</span></td>
<td class="mono">{esc(s['bytes'])}</td><td>{esc(s['error'] or '—')}</td>
<td>{link(s['url'], 'Open source')}{extra}</td></tr>''')
    src_rows = "".join(src_row_parts)
    sources_body = f'''{hero("Sources · " + DATA["as_of"], f"{S['official_sources']} official snapshots plus {len([x for x in SOURCES if x['role'] == 'discovery'])} OLBG discovery hubs.",
      "Only sources that returned HTTP 200 are used for facts. Failures stay listed with their status so a reviewer can check them manually.")}
<div class="callout"><strong>Source hierarchy:</strong> governing-body / league feeds for identity, form and statistics; OLBG event payloads for market names, selections, prices and tip counts; our own calculation for fair lines and confidence. A third-party F1 results mirror is labelled supplemental and is not used as an official fact.</div>
{section_heading("Source register", "Every table row on this site links back to one of these sources (or to the specific official event page derived from them).")}
<div class="table-tools"><input type="search" class="filter-input" data-filter="sources-table" placeholder="Search source…" aria-label="Filter sources"><span class="filter-count" data-count="sources-table"></span></div>
<div class="table-wrap"><table class="data-table" id="sources-table"><thead><tr><th>Source</th><th>Role</th><th>Type</th><th>HTTP</th><th>Bytes</th><th>Note</th><th>Link</th></tr></thead><tbody>{src_rows}</tbody></table></div>
<section class="prose"><h3>Official sport directories</h3><p>{'; '.join(link(s['official_url'], s['label']) for s in SPORTS)}.</p></section>'''
    (ROOT / "sources.html").write_text(page("Sources", sources_body, "sources", description="Official and discovery source register with capture status."), encoding="utf-8")

    # ---------------- methodology ----------------
    m = DATA["methodology"]
    market_counts = defaultdict(int)
    for l in LINES:
        market_counts[l["market"]] += 1
    market_list = "".join(f'<tr><td>{esc(k)}</td><td class="mono">{v}</td><td class="mono">{sum(len(l["selections"]) for l in LINES if l["market"] == k)}</td></tr>' for k, v in sorted(market_counts.items(), key=lambda x: -x[1]))
    methodology_body = f'''{hero("Methodology", "How the OLBG feed was reverse-engineered, how lines are originated, and what was checked.",
      "Every step is reproducible from the committed snapshots and scripts. No fixture, price, statistic, injury or prediction is invented.")}
<section class="prose">
<h3>1 · Reverse engineering OLBG</h3>
<p>OLBG's sport hubs are SvelteKit pages. Appending <code>/__data.json</code> to a hub URL (for example <a href="https://www.olbg.com/betting-tips/Tennis/3/__data.json">the Tennis hub</a>) returns the flattened server payload. The same endpoint exists on each event page and exposes every market, selection, decimal/American/fractional price, tip count, confidence value, event schema and start time. The collector fetches 16 hubs, 16 “All Events” pages and {MANIFEST_EVENTS} individual event payloads, then decodes the flattened devalue arrays without loss.</p>
<h3>2 · Originating a price for every market</h3>
<div class="formula">{esc(m['price_formula'])}</div>
<p>The blend is deliberately conservative. A market with no tips produces a pure de-vigged price; a market with many tips moves toward consensus but never more than 28% of the weight. On two-sided result markets where an official standings feed covers both teams, a small documented strength tilt is added. The result is normalised back to 100% and converted to an American price. Where only one side of a market has a price, or the displayed overround is unusually high, that is flagged on the row.</p>
<h3>3 · Confidence and the price band</h3>
<p>{esc(m['confidence'])} All high-confidence picks are therefore in the requested −250 to +10000 band rather than being short-priced favourites above 70% implied probability.</p>
<h3>4 · Official evidence</h3>
<p>Official NHL, MLB, WTA, EHF, Formula 1, ICC, Cricket Australia, CEV, EPCR, LNR, GAA, GBGB, PDC, WST, PGA TOUR, LPGA, NBA, NRL and Super League endpoints were captured at the same time. Team/player names were normalised and matched against those snapshots. Event-specific game-centre links were created for NHL and MLB fixtures; other sports use competition-level official pages. Where a match was not present in an official capture, the official link is a directory and the row is flagged. Injury and lineup sheets were not published in these captures, so those fields are blank.</p>
<h3>5 · Verification performed</h3>
<ul><li>Re-decoded every captured OLBG payload and confirmed each event has a source URL and a start time.</li><li>Checked that every generated table row carries an official-source link and an OLBG link.</li><li>Checked every written prediction for uniqueness, length (≥30 words), a named selection, a confidence label, an in-band price, and the absence of internal jargon.</li><li>Rebuilt the site from scratch and checked every internal link resolves.</li><li>Compared official NHL/MLB/NBA game times with OLBG times and flagged the differences.</li></ul>
<h3>6 · Markets found in this capture</h3>
<div class="table-wrap"><table class="data-table"><thead><tr><th>Market</th><th>Events</th><th>Priced selections</th></tr></thead><tbody>{market_list}</tbody></table></div>
<h3>7 · Limitations</h3>
<p>{esc(m['limitations'])}</p>
</section>'''
    (ROOT / "methodology.html").write_text(page("Methodology", methodology_body, "methodology", description="Pricing formula, confidence rules, market coverage and verification."), encoding="utf-8")

    # ---------------- flagged ----------------
    high_flags = [f for f in FLAGS if f["level"] == "high"]
    flagged_body = f'''{hero("Flagged for review · " + DATA["as_of"], f"{len(FLAGS)} items, {len(high_flags)} high priority.",
      "This page is the review queue. It does not block the site. Every item links to the source page so a human can check it. Blank fields are never filled with guesses.")}
<div class="callout red"><strong>High-priority gaps:</strong> OLBG returned no tipped event for Snooker or Greyhounds; several sports have fewer than five distinct upcoming matches; some official endpoints returned HTTP 403/429/500; and official injury sheets were not published in the captured sources. Picks were not invented to fill those gaps.</div>
<div class="table-tools"><input type="search" class="filter-input" data-filter="flags-table" placeholder="Search sport or issue…" aria-label="Filter flags"><select id="severity-filter" class="filter-select" aria-label="Filter severity"><option value="">All severities</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select><span class="filter-count" data-count="flags-table"></span></div>
<div class="table-wrap"><table class="data-table" id="flags-table"><thead><tr><th>Severity</th><th>Sport</th><th>Issue</th><th>Detail</th><th>Sources</th></tr></thead><tbody>{''.join(flag_row(f) for f in FLAGS)}</tbody></table></div>'''
    (ROOT / "flagged.html").write_text(page("Flagged for review", flagged_body, "flagged", description="Unverified values, missing official data and coverage gaps."), encoding="utf-8")

    # ---------------- sport pages ----------------
    for s in SPORTS:
        slug = s["key"]
        evs = [e for e in EVENTS if e["sport_slug"] == slug]
        ls = [l for l in LINES if l["sport_slug"] == slug]
        ps = by_sport[slug]
        fs = [f for f in FLAGS if f["sport"] == s["label"]]
        official_links = [dict(name=s["official_name"], url=s["official_url"]),
                          dict(name=s["secondary_name"], url=s["secondary_url"]),
                          dict(name="OLBG hub", url=s["hub"])]
        body = f'''{hero(s["label"] + " · " + DATA["as_of"], f"{len(ps)} written picks · {len(ls)} priced markets · {len(evs)} OLBG event rows",
          s["note"])}
<div class="callout blue"><strong>Fast links:</strong> <a href="../picks.html#sport-{esc(slug)}">all picks</a> · <a href="../lines.html">all lines</a> · <a href="../matches.html">all matches</a> · <a href="../flagged.html">flagged items</a> · official sources: {source_cell(official_links)}</div>
<section class="kpis">{kpi(len(ps), "Picks", "with written predictions")}{kpi(s['high'], "High confidence", "in the −250 to +10000 band")}{kpi(len(ls), "Markets priced", f"{s['priced_selections']} lines")}{kpi(s['upcoming'], "Upcoming events", f"of {s['events']} captured")}</section>
<section>{section_heading("Executive summary · " + s["label"], "The highest-confidence selections for this sport, with the full written prediction for each.")}
{''.join(pick_card(p) for p in ps) if ps else '<div class="callout red"><strong>No picks.</strong> OLBG published no tipped event for this sport in the captured feeds. Official sources are linked below and the gap is on Flagged for Review.</div>'}
</section>
<section>{section_heading("Originated lines", "Every priced selection in every OLBG market for this sport.")}
{lines_table(ls, 'lines-' + slug) if ls else '<div class="callout">No market rows were captured, so there is nothing to price.</div>'}</section>
<section>{section_heading("Matches and events", "All captured OLBG event rows for this sport.")}
{matches_table(evs, 'matches-' + slug) if evs else '<div class="callout">No OLBG event row was captured for this sport.</div>'}</section>
<section>{section_heading("Official sources", "Links used for identity, form, statistics and calendar checks.")}
<div class="table-wrap"><table class="data-table"><thead><tr><th>Source</th><th>Status</th><th>Link</th></tr></thead><tbody>
<tr><td>{esc(s['official_name'])}</td><td>HTTP {esc(s['official_status'])}</td><td>{link(s['official_url'], 'Open')}</td></tr>
<tr><td>{esc(s['secondary_name'])}</td><td>Secondary</td><td>{link(s['secondary_url'], 'Open')}</td></tr>
<tr><td>OLBG {esc(s['label'])} hub</td><td>Discovery</td><td>{link(s['hub'], 'Open')} {link(s['official_url'], 'Official directory')}</td></tr>
</tbody></table></div></section>
<section>{section_heading("Flagged for this sport", f"{len(fs)} review items.")}
<div class="table-wrap"><table class="data-table"><thead><tr><th>Severity</th><th>Sport</th><th>Issue</th><th>Detail</th><th>Sources</th></tr></thead><tbody>{''.join(flag_row(f) for f in fs)}</tbody></table></div></section>'''
        (SPORTS_DIR / f"{slug}.html").write_text(page(s["label"], body, "sport", base="../", description=f"{s['label']} OLBG picks, originated lines, matches and official sources."), encoding="utf-8")

    print(f"rendered {6 + 2 + len(SPORTS)} pages: 8 root pages + {len(SPORTS)} sport pages")
    return 0


MANIFEST_EVENTS = len(DATA["events"])

if __name__ == "__main__":
    raise SystemExit(render())
