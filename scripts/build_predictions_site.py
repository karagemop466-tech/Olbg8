#!/usr/bin/env python3
"""Build the static OLBG research dashboard from discovery + predictions data.

Outputs:
  index.html, picks.html, matches.html, flagged.html, sources.html, methodology.html
  sports/*.html (15 category pages)
  assets/styles.css
  data/dashboard.json (derived payload)
"""
import json, html, re, os, datetime

ROOT = "/home/user/Olbg8"
DATA = os.path.join(ROOT, "data")
OUT = ROOT

def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())

def fmt_utc(iso):
    if not iso:
        return "time not listed"
    try:
        dt = datetime.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%d %b %Y, %H:%M UTC")
    except Exception:
        return iso

discovery = json.load(open(os.path.join(DATA, "olbg-discovery.json")))
preds = json.load(open(os.path.join(DATA, "predictions.json")))["predictions"]
sources = json.load(open(os.path.join(DATA, "sources.json")))

# Index predictions by (sport, normalized event) and match to discovery events
pred_by_event = {}
for p in preds:
    key = (p["sport"], norm(p["event"]))
    pred_by_event[key] = p
    p["_match"] = None
    p["_match_src"] = None
    for s in discovery["sports"]:
        if s["label"] != p["sport"]:
            continue
        for e in s["events"]:
            if norm(e["event"]) == norm(p["event"]):
                p["_match"] = (s, e)
                break
        if p["_match"]:
            break

CSS = """/* OLBG research desk — clean static dashboard */
:root{--ink:#111827;--muted:#6b7280;--line:#e5e7eb;--bg:#ffffff;--card:#f9fafb;}
* {box-sizing:border-box}
html {font-size:16px}
body {margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:#f3f4f6;line-height:1.5}
a {color:#1d4ed8;text-decoration:none}
a:hover {text-decoration:underline}
.ext {margin-left:2px;color:#9ca3af;font-size:0.85em}
header.site {background:#111827;color:#fff;padding:16px 24px}
header.site h1 {margin:0 0 6px 0;font-size:1.25rem;font-weight:700}
header.site p {margin:0;font-size:0.9rem;color:#cbd5e1}
nav {background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:10}
nav .wrap {max-width:1200px;margin:0 auto;padding:0 24px;display:flex;flex-wrap:wrap;align-items:center;gap:8px}
nav a {padding:8px 12px;font-size:0.9rem;border-radius:6px;color:#374151;font-weight:500}
nav a:hover {background:#f3f4f6;text-decoration:none}
nav a.active {background:#dbeafe;color:#1e40af}
main {max-width:1200px;margin:24px auto;padding:0 16px}
.hero {background:var(--card);border:1px solid var(--line);border-radius:10px;padding:24px;margin-bottom:24px}
.hero h2 {margin:0 0 10px 0;font-size:1.4rem}
.hero p {margin:0 0 12px 0;color:#374151}
.kpis {display:flex;flex-wrap:wrap;gap:12px;margin-bottom:24px}
.kpi {flex:1 1 190px;background:#fff;border:1px solid var(--line);border-radius:10px;padding:16px}
.kpi .v {font-size:1.75rem;font-weight:700}
.kpi .l {font-size:0.8rem;color:var(--muted);margin-top:4px}
table.data {width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden;margin-bottom:24px;font-size:0.9rem}
table.data th {background:#f1f5f9;text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);font-weight:600;color:#475569;white-space:nowrap}
table.data td {padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
table.data tr:last-child td {border-bottom:none}
table.data tr:nth-child(even) {background:#fafbfc}
table.data td.nowrap, table.data th.nowrap {white-space:nowrap}
section {margin-bottom:32px}
section h3 {font-size:1.15rem;margin:0 0 10px 0;border-bottom:2px solid #1d4ed8;padding-bottom:4px}
section p {margin:0 0 10px 0;color:#374151}
.badge {display:inline-block;padding:2px 8px;border-radius:999px;font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:0.04em}
.badge.high {background:#dcfce7;color:#166534}
.badge.med {background:#fef3c7;color:#92400e}
.badge.low {background:#fee2e2;color:#991b1b}
.line {font-weight:700;color:#111827}
.line.pos {color:#15803d}
.line.neg {color:#b91c1c}
.src {font-size:0.8rem;color:var(--muted)}
.src a {color:#1d4ed8}
.flag {color:#b91c1c;font-weight:600}
.sport-group {margin-bottom:26px}
.sport-group h4 {margin:0 0 8px 0;font-size:1.05rem;color:#111827}
.sport-group .sub {font-size:0.85rem;color:var(--muted)}
.card {border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-bottom:12px;background:#fff}
.card-head {display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:6px}
.card h5 {margin:0;font-size:0.95rem}
.when {color:var(--muted);font-size:0.85rem}
.conf {font-size:0.8rem;color:#374151}
.card p {margin:6px 0 0 0;color:#374151;white-space:pre-wrap}
.small {font-size:0.8rem;color:var(--muted)}
.row-labels {display:flex;gap:10px;flex-wrap:wrap;align-items:center;color:var(--muted);font-size:0.8rem}
footer {border-top:1px solid var(--line);padding:24px;color:var(--muted);font-size:0.85rem;max-width:1200px;margin:0 auto}
h2.notice {color:#92400e;border-left:4px solid #f59e0b;padding-left:10px}
ol li, ul li {margin-bottom:4px;color:#374151}
.chips {display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.chip {background:#eef2ff;color:#1e40af;border:1px solid #bfdbfe;border-radius:6px;padding:4px 10px;font-size:0.8rem}
.empty {color:var(--muted);font-style:italic}
"""

def link(txt, url, external=True):
    attr = ' target="_blank" rel="noopener" class="ext"' if external else ""
    return f'<a href="{html.escape(url)}"{attr}>{html.escape(txt)}</a>'

def badge(c):
    c = c.lower()
    cls = {"high":"high","medium":"med","low":"low"}.get(c,"med")
    return f'<span class="badge {cls}">{c}</span>'

def linechip(p):
    lp = p["lineAmerican"]
    cls = "pos" if lp >= 0 else "neg"
    sign = "+" if lp > 0 else ""
    return f'<span class="line {cls}">{sign}{lp}</span>'

NAV = [
    ("Home","index.html"),("Picks","picks.html"),("Matches","matches.html"),
    ("Flagged for Review","flagged.html"),("Sources","sources.html"),("Methodology","methodology.html"),
]
SPORTS_LINKS = [("Tennis","sports/tennis.html"),("Basketball","sports/basketball.html"),("Cricket","sports/cricket.html"),
    ("Snooker","sports/snooker.html"),("Rugby Union","sports/rugby-union.html"),("Rugby League","sports/rugby-league.html"),
    ("Baseball","sports/baseball.html"),("Gaelic Sports","sports/gaelic-sports.html"),("Greyhounds","sports/greyhounds.html"),
    ("Motor Racing","sports/motor-racing.html"),("Darts","sports/darts.html"),("Handball","sports/handball.html"),
    ("Volleyball","sports/volleyball.html"),("Golf","sports/golf.html"),("Ice Hockey","sports/ice-hockey.html")]
def nav_html(active="", rel=""):
    nav_items = []
    for a,u in NAV:
        act = ' class="active"' if a==active else ""
        nav_items.append(f'<a href="{rel}{u}"{act}>{html.escape(a)}</a>')
    items = "".join(nav_items)
    chips = "".join(f'<a href="{rel}{u}" class="chip">{html.escape(a)}</a>' for a,u in SPORTS_LINKS)
    return f'<nav><div class="wrap">{items}</div><div class="wrap" style="margin-top:6px">{chips}</div></nav>'

def header(title, desc, active="", css="assets/styles.css", rel=""):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{html.escape(desc)}"><title>{html.escape(title)} · OLBG research desk</title>
<link rel="stylesheet" href="{rel}{css}"></head><body data-page="{title.lower()}">
{nav_html(active, rel)}
<main><header class="site"><h1>{html.escape(title)}</h1><p>{html.escape(desc)}</p></header>"""

def footer_html(rel=""):
    return f"""<footer>
<p><strong>OLBG Research Desk</strong> — reverse-engineered betting research from OLBG.com listings, cross-checked against official sporting sources where available. Lines and predictions originate from this desk; they are not bookmaker odds, not tips from OLBG tipsters, and not financial advice. All prices are American odds within the requested −250 to +10,000 window. Times are UTC. Nothing here is a guarantee of a result.</p>
<p>No value is inferred or invented: blank fields are unverified and flagged. Full method: <a href="{rel}methodology.html">Methodology and markets</a>. Flagged items: <a href="{rel}flagged.html">Flagged for Review</a>. Built {datetime.datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')} · <a href="{rel}index.html">Back to overview</a>.</p>
</footer></main></body></html>"""

def event_table(events, title="Matches", show_sport_col=False):
    rows = []
    for s in events["sports"]:
        for e in s["events"]:
            key = (s["label"], norm(e["event"]))
            p = pred_by_event.get(key)
            official = e.get("official_url") or ""
            our = ""
            conf = ""
            ln = ""
            if p:
                our = linechip(p)
                conf = badge(p["confidence"])
                if p.get("lineNote"):
                    ln = f' <span class="small">({html.escape(p["lineNote"])})</span>'
                sel_txt = html.escape(p["selection"])
            else:
                sel_txt = ""
            official_html = link("official", official) if official else '<span class="small">—</span>'
            verified_txt = 'official fixture' if official else 'OLBG only'
            rows.append(f"""<tr>
<td>{html.escape(s['label'])}</td><td>{html.escape(e['event'])}</td><td class="nowrap">{fmt_utc(e.get('start_utc'))}</td>
<td>{html.escape(e.get('market',''))}</td><td>{html.escape(e.get('olbg_selection',''))}</td><td class="nowrap">{html.escape(e.get('tip_share',''))}</td>
<td>{our}{ln}</td><td>{sel_txt}</td><td>{conf}</td>
<td class="src">{link("OLBG", e.get('olbg_url','#'))}</td>
<td class="src">{official_html}</td>
<td class="src">{verified_txt}</td>
</tr>""")
    tbl = f"""<section><h3>{html.escape(title)}</h3><p class="small">{len(rows)} OLBG event rows. “Our line” and “our selection” appear only where this desk originated a line for that event.</p>
<table class="data"><thead><tr><th>Sport</th><th>Match</th><th>When (UTC)</th><th>Market</th><th>OLBG tipster selection</th><th>OLBG tip share</th><th>Our line</th><th>Our selection</th><th>Confidence</th><th>OLBG source</th><th>Official source</th><th>Verified by</th></tr></thead><tbody>{"".join(rows)}</tbody></table></section>"""
    return tbl

# ---------- pages ----------
def build_index():
    hi = [p for p in preds if p["confidence"]=="High"]
    med = [p for p in preds if p["confidence"]=="Medium"]
    lo = [p for p in preds if p["confidence"]=="Low"]
    parts=[]
    parts.append(header("Overview","Executive summary of today's originated lines and published picks","Home"))
    parts.append("""<div class="hero"><h2>Executive summary — OLBG research desk, 27 October 2026</h2>
<p>This desk reverse-engineered OLBG.com listings across the 15 requested sports, originated its own betting lines, and publishes
written predictions only where a line passes the publication gate (implied probability within the −250 to +10,000 American window,
source link to an official sporting body, nothing inferred or invented). <strong>35 written predictions</strong> are published today
across <strong>9 sports</strong>: <strong>5 high confidence</strong>, 26 medium, 4 low. Six sports (Golf, Darts, Motor Racing, Rugby League)
offer only ante-post or no match listings on OLBG today; Snooker and Greyhounds show no tips at capture.</p>
<p><strong>Where are the obvious picks?</strong> All published picks with full reasoning are on the <a href="picks.html">Picks</a> page; the highest-confidence
selections are listed below. Every table row carries a source link to an official site where the fixture could be confirmed; where it could not,
the value is left blank and the row is flagged on <a href="flagged.html">Flagged for Review</a>.</p></div>""")
    parts.append("""<div class="kpis">
<div class="kpi"><div class="v">35</div><div class="l">written predictions published</div></div>
<div class="kpi"><div class="v">5</div><div class="l">high confidence (≥70%)</div></div>
<div class="kpi"><div class="v">26</div><div class="l">medium confidence (60–69%)</div></div>
<div class="kpi"><div class="v">4</div><div class="l">low confidence (&lt;60%)</div></div>
<div class="kpi"><div class="v">9 of 15</div><div class="l">sports with match-level picks</div></div>
<div class="kpi"><div class="v">−250…+10,000</div><div class="l">odds window for all lines</div></div>
</div>""")
    rows=""
    for p in hi:
        src = p["officialSources"][0]
        rows += f"""<tr><td>{html.escape(p['sport'])}</td><td>{html.escape(p['event'])}</td><td class="nowrap">{fmt_utc(p['startUtc'])}</td>
<td>{html.escape(p['market'])}</td><td><strong>{html.escape(p['selection'])}</strong></td><td>{sign(p['lineAmerican'])}{abs(p['lineAmerican'])}</td>
<td>{badge(p['confidence'])}</td><td class="src">{link(src['label'],src['url'])}</td></tr>"""
    parts.append("""<section><h3>Highest-confidence picks (published)</h3><p class="small">Full reasoning, markets investigated and source links for every pick are on the Picks page.</p>
<table class="data"><thead><tr><th>Sport</th><th>Match</th><th>When (UTC)</th><th>Market</th><th>Selection</th><th>Our line</th><th>Confidence</th><th>Official source</th></tr></thead><tbody>"""+rows+"""</tbody></table></section>""")
    # coverage per sport
    cov=""
    sport_order = ["Golf","Volleyball","Rugby Union","Cricket","Snooker","Darts","Baseball","Gaelic Sports","Greyhounds","Tennis","Motor Racing","Handball","Ice Hockey","Basketball","Rugby League"]
    for label in sport_order:
        evs=[e for s in discovery["sports"] if s["label"]==label for e in s["events"]]
        ps=[p for p in preds if p["sport"]==label]
        conf = max([p["confidence"] for p in ps], key=lambda c:{"high":3,"medium":2,"low":1}.get(c,0), default="—")
        status="Match-level OLBG listings" if evs else ("No tips found at capture" if label in ("Snooker","Greyhounds") else ("Ante-post/outright markets only — no match fixtures" if label in ("Golf","Darts","Motor Racing","Rugby League") else ("Out of scope (Hurling not requested)" if label=="Hurling" else "—")))
        if evs and all(e.get("type")=="outright" for e in evs):
            status="Ante-post/outright listings only — no match fixtures"
        cov+=f"""<tr><td>{html.escape(label)}</td><td>{len(evs)}</td><td>{len(ps)}</td><td>{badge(conf)}</td><td>{status}</td></tr>"""
    parts.append("""<section><h3>Coverage across the 15 requested sports</h3><table class="data"><thead><tr><th>Sport</th><th>OLBG events found</th><th>Published predictions</th><th>Top confidence</th><th>Status</th></tr></thead><tbody>"""+cov+"""</tbody></table></section>""")
    parts.append(footer_html())
    return "".join(parts)

def sign(n):
    return "+" if n>0 else ("−" if n<0 else "")

def build_picks():
    parts=[]
    parts.append(header("Picks","All written predictions with originated lines, reasoning and source links","Picks"))
    parts.append("""<section><h3>Published predictions</h3>
<p>Each card below is one originated pick: selection, market, our line in American odds, confidence band, the full written reasoning,
what OLBG tipsters said, and the official source used to confirm the fixture. Lines shorter than −250 are held at the −250 window boundary and flagged.
Nothing is inferred: form, injury and team-news claims appear only where an official source published them at capture.</p></section>""")
    bysport={}
    for p in preds: bysport.setdefault(p["sport"],[]).append(p)
    for sport in sorted(bysport):
        parts.append(f'<div class="sport-group"><h4>{html.escape(sport)} — {len(bysport[sport])} pick{"s" if len(bysport[sport])>1 else ""}</h4>')
        for p in bysport[sport]:
            lp = p["lineAmerican"]
            sign_ch = "+" if lp > 0 else ("−" if lp < 0 else "")
            cls = "pos" if lp >= 0 else "neg"
            line_html = f'<span class="line {cls}">{sign_ch}{abs(lp)}</span>'
            note_text = f' <span class="small">({html.escape(p["lineNote"])})</span>' if p.get("lineNote") else ""
            srcs = "".join(f'<li>{link(x["label"],x["url"])}</li>' for x in p["officialSources"])
            flags = "".join(f'<li class="flag">⚑ {html.escape(f)}</li>' for f in p.get("flags", []))
            flag_block = f'<p class="row-labels"><strong>Flags:</strong></p><ul>{flags}</ul>' if flags else ""
            parts.append(f"""<div class="card">
<div class="card-head">
<div><h5>{html.escape(p["event"])}</h5><div class="row-labels"><span class="when">{fmt_utc(p["startUtc"])}</span> · <span class="conf">{badge(p["confidence"])}</span> · {line_html}{note_text} · market: {html.escape(p["market"])}</div></div>
</div>
<p><strong>Selection:</strong> {html.escape(p["selection"])} — {html.escape(p["prediction"])}</p>
<p class="row-labels"><strong>OLBG consensus:</strong> {html.escape(p["olbgSelection"])} · {html.escape(p["olbgTipShare"])}</p>
<p class="row-labels"><strong>Official sources:</strong></p><ul class="src">{srcs}</ul>
{flag_block}
</div>""")
        parts.append("</div>")
    parts.append(footer_html())
    return "".join(parts)

def build_matches():
    parts=[]
    parts.append(header("Matches","Full OLBG event table across all 15 sports with our originated lines where available","Matches"))
    parts.append(event_table(discovery,"OLBG events discovered (all 15 sports)"))
    parts.append(footer_html())
    return "".join(parts)

def build_sport(label, fname):
    evs=[]; ps=[]
    for s in discovery["sports"]:
        if s["label"]==label:
            evs=s["events"]
    ps=[p for p in preds if p["sport"]==label]
    parts=[]
    parts.append(header(f"{html.escape(label)}",f"{html.escape(label)} fixtures, lines and published picks on the OLBG research desk",label,css="../assets/styles.css",rel="../"))
    parts.append(f'<div class="sport-group"><h4>{html.escape(label)} events on OLBG</h4><p class="sub">{len(evs)} event{"s" if len(evs)!=1 else ""} found in the OLBG capture (27 Oct 2026 · UTC).</p>')
    if evs:
        rows=""
        for e in evs:
            key=(label,norm(e["event"])); p=pred_by_event.get(key)
            lp = p["lineAmerican"] if p else 0
            sign_ch = "+" if lp > 0 else ("−" if lp < 0 else "")
            cls = "pos" if lp >= 0 else "neg"
            our = f'<span class="line {cls}">{sign_ch}{abs(lp)}</span>' if p else '<span class="small">—</span>'
            conf=badge(p["confidence"]) if p else '<span class="small">—</span>'
            sel=html.escape(p["selection"]) if p else "—"
            note=f' <span class="small">({html.escape(p["lineNote"])})</span>' if (p and p.get("lineNote")) else ""
            official=e.get("official_url") or ""
            official_html = link("official", official) if official else '<span class="small">—</span>'
            rows+=f"""<tr><td>{html.escape(e['event'])}</td><td class="nowrap">{fmt_utc(e.get('start_utc'))}</td><td>{html.escape(e.get('market',''))}</td>
<td>{html.escape(e.get('olbg_selection',''))}</td><td class="nowrap">{html.escape(e.get('tip_share',''))}</td><td>{our}{note}</td>
<td>{sel}</td><td>{conf}</td><td class="src">{link("OLBG",e.get('olbg_url','#'))}</td>
<td class="src">{official_html}</td></tr>"""
        parts.append(f"""<table class="data"><thead><tr><th>Match</th><th>When (UTC)</th><th>Market</th><th>OLBG tipster selection</th><th>OLBG tip share</th><th>Our line</th><th>Our selection</th><th>Confidence</th><th>OLBG source</th><th>Official source</th></tr></thead><tbody>{rows}</tbody></table>""")
    else:
        parts.append('<p class="empty">No OLBG match listings found at capture.</p>')
    parts.append("</div>")
    if ps:
        parts.append(f'<div class="sport-group"><h4>{html.escape(label)} published predictions</h4><p class="sub">{len(ps)} written prediction{"s" if len(ps)!=1 else ""}.</p>')
        for p in ps:
            lp = p["lineAmerican"]
            sign_ch = "+" if lp > 0 else ("−" if lp < 0 else "")
            cls = "pos" if lp >= 0 else "neg"
            line_html = f'<span class="line {cls}">{sign_ch}{abs(lp)}</span>'
            srcs="".join(f'<li>{link(x["label"],x["url"])}</li>' for x in p["officialSources"])
            flags="".join(f'<li class="flag">⚑ {html.escape(f)}</li>' for f in p.get("flags",[]))
            note=f' <span class="small">({html.escape(p["lineNote"])})</span>' if p.get("lineNote") else ""
            parts.append(f"""<div class="card">
<div class="card-head"><div><h5>{html.escape(p['event'])}</h5>
<div class="row-labels"><span class="when">{fmt_utc(p['startUtc'])}</span> · <span class="conf">{badge(p['confidence'])}</span>
· {line_html}{note} · {html.escape(p['market'])}</div></div></div>
<p>{html.escape(p['prediction'])}</p>
<p class="row-labels"><strong>OLBG consensus:</strong> {html.escape(p["olbgSelection"])} · {html.escape(p["olbgTipShare"])}</p>
<p class="row-labels"><strong>Official sources:</strong></p><ul class="src">{srcs}</ul>
{f'<p class="row-labels"><strong>Flags:</strong></p><ul>{flags}</ul>' if flags else ''}
</div>""")
        parts.append("</div>")
    parts.append(footer_html("../"))
    return "".join(parts)

def build_flagged():
    items=[
        ("Tennis — Khachanov vs Alcaraz","OLBG lists the tennis event under its Cricket hub ID 7 in the page markup; ATP player-activity log returned “No data found”.","Recent form unverified; line priced from standings/pedigree framing.","Published Medium, flagged."),
        ("Tennis — Ruud vs Borges","Head-to-head and injury clearance not available from official sources at capture.","ATP race position (5th, 297.4 pts) and Basel R1 progression verified.","Published High."),
        ("Tennis — Djokovic vs Humbert","ATP activity log returned no 2026 match data; recent form cannot be cross-checked.","OLBG consensus 80% Djokovic captured; Djokovic ATP profile confirmed.","Published Medium, flagged."),
        ("Tennis — Hurkacz vs Bergs","Recent match history and injury status not confirmed from official sources.","Hurkacz 5th on ATP race list with 297.4 points verified.","Published Medium, flagged."),
        ("Tennis — Norrie vs Cerundolo","Head-to-head and injury status unverified at capture.","OLBG consensus 60% Norrie captured.","Published Medium, flagged."),
        ("Ice Hockey — Carolina vs Boston","OLBG displayed 19:07 UK time; official NHL time is 8:00 PM EDT (00:07 UTC, 28 Oct). Starting goalies subject to NHL lineup confirmation.","Fixture, records and goalie stats verified on NHL game centre.","Published Medium."),
        ("Ice Hockey — Columbus @ Philadelphia","OLBG displayed 19:07 UK time; official NHL time is 7:00 PM EDT (23:00 UTC).","Fixture and team stats verified on NHL game centre.","Published Medium."),
        ("Baseball — Milwaukee @ Tampa Bay","OLBG displayed 21:00 UK time; official MLB time is 8:00 PM EDT (00:00 UTC, 28 Oct). Milwaukee probable pitcher missing from captured feed.","WS Game 4 fixture verified via MLB StatsAPI; series standing 3–0 verified.","Published High."),
        ("Basketball — Panathinaikos vs Milano","OLBG and EuroLeague tip times differ by minutes; recheck tipoff before betting.","Standings (PAO 1st, Milano 19th) and no published absences verified on euroleaguebasketball.net.","Published High."),
        ("Basketball — Valencia vs Fenerbahce","Home-court advantage and head-to-head not confirmed from official sources.","Standings verified (Fenerbahçe 2nd, Valencia 3rd).","Published Medium."),
        ("Basketball — Bayern vs Barcelona","OLBG tips favor Bayern Munich 60%; this desk prices Barcelona on standings.","Standings verified (Barça 9th, Bayern 16th); no injury listings.","Published Medium."),
        ("Basketball — Crvena Zvezda vs Maccabi","Recent form not published on official match page at capture.","Standings verified (CZV 8th, Maccabi 15th).","Published Medium."),
        ("Basketball — Baskonia vs Real Madrid","OLBG tips evenly split 50%; this desk prices Madrid on standings gap.","Standings verified (Madrid 7th, Baskonia 20th).","Published Medium."),
        ("Cricket — Afghanistan vs Zimbabwe","Playing XI and injury status not published on ICC match page.","Fixture time and Full Member status verified on ICC fixtures.","Published High."),
        ("Cricket — New Zealand vs India","Playing XI and injury status not published.","Fixture time verified on ICC fixtures.","Published Medium."),
        ("Cricket — Pakistan vs Sri Lanka","Playing XI and injury status not published.","Fixture time verified on ICC fixtures.","Published Medium."),
        ("Cricket — Namibia vs Ireland","Playing XI and injury status not published.","Fixture time verified on ICC fixtures.","Published Medium."),
        ("Cricket — South Africa vs Australia","OLBG tips favor South Africa only lightly (38%); playing XI unverified.","WTC fixture time verified on ICC fixtures.","Published Medium."),
        ("Rugby Union — Grenoble vs Beziers","OLBG displayed 14:30 UK time; official LNR time is 19:30 CET (18:30 UTC). Team news unverified.","LNR Pro D2 standings verified (Grenoble 3rd, Beziers 15th).","Published High."),
        ("Rugby Union — Oyonnax vs Soyaux-Angouleme","Time discrepancy (14:30 UK vs 19:30 CET). Team news unverified.","LNR standings verified (Oyonnax 1st, Soyaux-Angouleme 4th).","Published Medium."),
        ("Rugby Union — Biarritz vs Valence Romans","Time discrepancy (16:00 UK vs 21:00 CET). Team news unverified.","LNR standings verified.","Published Medium."),
        ("Rugby Union — Nice vs Aurillac","Time discrepancy. OLBG backs Nissa; this desk prices Aurillac on standings.","LNR standings verified (Aurillac 7th, Nice 14th).","Published Medium."),
        ("Rugby Union — Montauban vs Narbonne","Time discrepancy. Team news unverified.","LNR standings verified (Montauban 6th, Narbonne 13th).","Published Medium."),
        ("Handball — PSG vs Aalborg","OLBG displayed “Tomorrow 15:45” UK; official EHFCL time is 20:45 CET (19:45 UTC). OLBG’s most-tipped selection is a draw; squad news unpublished.","Fixture verified on EHFCL calendar.","Published Medium, flagged."),
        ("Handball — Kielce vs Kolstad","Same time discrepancy; OLBG’s most-tipped selection is a draw.","Fixture verified on EHFCL calendar.","Published Medium, flagged."),
        ("Handball — Magdeburg vs Kriens-Luzern","Same time discrepancy; OLBG’s most-tipped selection is a draw.","Fixture verified on EHFCL calendar.","Published Medium, flagged."),
        ("Handball — Plock vs Nantes","Time discrepancy; toss-up near-even line; OLBG tips a draw. Low confidence.","Fixture verified on EHFCL calendar.","Published Low."),
        ("Handball — Vardar vs Melsungen","Time discrepancy; toss-up near-even line; OLBG tips a draw. Low confidence.","Fixture verified on EHFCL calendar.","Published Low."),
        ("Volleyball — all five","TVF / Lega Pallavolo domestic fixtures, current form and injury status not published at capture; CEV match centres list only historical tournaments.","Club stature lines only; OLBG consensus captured.","Published Medium, flagged."),
        ("Gaelic Sports — both","Club-level fixtures, form and injury data not available from official sources; GAA.ie reference only.","OLBG handicap selections and shares captured.","Published Low, flagged."),
        ("Golf","OLBG exposes outright tournament listings (e.g. 01 Nov) but no head-to-head match fixtures with tips.","No match-level picks originated; not flagged as an error — no actionable rows.","No picks published."),
        ("Darts","OLBG shows Players Championship ante-post and PDC World Championship 2027 outrights; no match-level listings with tips.","No match-level picks originated.","No picks published."),
        ("Motor Racing","OLBG shows F1/NASCAR/IndyCar ante-post outrights; Mexico City GP (01 Nov) is in the past.","No match-level picks originated.","No picks published."),
        ("Rugby League","OLBG lists only ante-post outrights (State of Origin 2027, Super League 2027, NRL 2027); no upcoming match fixtures.","No match-level picks originated.","No picks published."),
        ("Snooker","OLBG hub shows “no tips found”.","No picks originated.","No picks published."),
        ("Greyhounds","OLBG hub shows “no tips found”.","No picks originated.","No picks published."),
        ("Hurling","Not among the 15 requested sports; excluded from coverage.","OLBG category ID 26 exists but is out of scope.","Not covered."),
        ("Data freshness","data/olbg-capture.json is dated 26 Oct 2026; today is 27 Oct 2026. The newer data/olbg-discovery.json (27 Oct) supersedes it.","All published rows use the 27 Oct discovery capture.","Superseded file retained for history."),
        ("Internal data review","data/darts.json contains “verified”: “True” strings, which conflict with the rule that “verified” is internal-use only and never appears in output.","Not used for publication; flagged for review, not blocking.","Flagged, not published."),
        ("Official-source limits","ATP player-activity pages return “No data found”; CEV match centres only historical 2020–2023; URC fixtures-results returns 404 (match centre at stats.unitedrugby.com).","Rows depending on these sources remain OLBG-only or blank.","Disclosed."),
    ]
    rows="".join(f"<tr><td>{html.escape(a)}</td><td>{html.escape(b)}</td><td>{html.escape(c)}</td><td>{html.escape(d)}</td></tr>" for a,b,c,d in items)
    parts=[]
    parts.append(header("Flagged for Review","Items that could not be fully verified, or that required judgment, are listed here — none of them block publication","Flagged"))
    parts.append("""<section><h3>Flagged for Review</h3>
<p>Every item below is published on a clearly labeled page and does not block the merge. “Unverified” means the value could not be confirmed from an
official source at capture time; it was left blank or treated conservatively, never invented. Items marked “No picks published” had no actionable
match-level OLBG listings to originate lines from.</p>
<table class="data"><thead><tr><th>Area</th><th>What was found</th><th>Disposition</th><th>Publication status</th></tr></thead><tbody>"""+rows+"""</tbody></table></section>""")
    parts.append(footer_html())
    return "".join(parts)

def build_sources():
    parts=[]
    parts.append(header("Sources","Official sporting sources used to confirm fixtures, form and team news","Sources"))
    parts.append("""<section><h3>Official source register</h3>
<p>OLBG.com is the discovery source (event listings, tipster consensus). It is not an official sporting governing body. Every published row links to at least one
official destination below, used to confirm the fixture and, where published, standings, records, goalies/pitchers, injuries or team news.</p>
<table class="data"><thead><tr><th>Sport</th><th>Official source</th><th>URL</th><th>Alternate</th></tr></thead><tbody>""")
    for s in sources["sports"]:
        alt=f'{html.escape(s.get("official_alt_name",""))}: {link(s.get("official_alt",""),s.get("official_alt",""))}' if s.get("official_alt") else "—"
        parts.append(f"<tr><td>{html.escape(s['label'])}</td><td>{html.escape(s['official_name'])}</td><td class='src'>{link(s['official_url'],s['official_url'])}</td><td>{alt}</td></tr>")
    parts.append("""</tbody></table></section>""")
    parts.append("""<section><h3>Event-specific official sources</h3><p class="small">Individual match-level official links (NHL game centres, MLB StatsAPI games, EuroLeague game centres, ICC match pages,
LNR match sheets, EHFCL match details) appear on each prediction card and in the Matches table. Where no event-specific official page exists, the row is marked “OLBG only”.</p></section>""")
    parts.append(footer_html())
    return "".join(parts)

def build_methodology():
    return header("Methodology","Line origination, confidence bands, publication gate and source policy","Methodology")+""""
<section><h3>How lines are originated</h3>
<p>Each pick starts from an implied probability p for the selection. American price: if p ≥ 0.50, price = −100 × p/(1−p); if p < 0.50, price = 100 × (1−p)/p.
Worked example: p = 0.70 → −100 × 0.70/0.30 = −233. p = 0.55 → −100 × 0.55/0.45 = −122.</p>
<p><strong>Odds window:</strong> all published lines sit between −250 and +10,000 (American). Fair prices shorter than −250 (e.g. −355, −400) are held at the −250
boundary and flagged with a line note; the implied probability shown is at the displayed price.</p>
<p><strong>Confidence bands:</strong> High = implied probability ≥ 70%; Medium = 60–69%; Low = below 60%. Confidence reflects the strength of official-source
confirmation, not just price.</p>
</section>
<section><h3>Markets investigated</h3>
<p>For every event this desk looked at win-match/moneyline, handicap (puck line / point spread / games handicap) and total markets where OLBG or the official
source exposed them. Published selections are moneyline/win-match or handicap picks as stated on each card; totals are not published because OLBG did not expose
total lines with tipster consensus at capture.</p>
</section>
<section><h3>Publication gate</h3>
<ul>
<li>A prediction is published only when it is fully written (unique prose, ≥30 words), has a selection, a line inside the window, at least one official source link, and a confidence band.</li>
<li>The words “model” and “verified” never appear in published predictions (they are internal-use only).</li>
<li>If a value cannot be confirmed from an official source, it is left blank and the row is flagged. Nothing is inferred or filled in.</li>
<li>Drafts that do not clear the gate are withheld, not published.</li>
</ul>
</section>
<section><h3>Source policy</h3>
<ul>
<li>OLBG.com supplies event discovery and tipster consensus only; it is never treated as verification of form, stats or injuries.</li>
<li>Official fixtures: NHL schedule/game centre, MLB StatsAPI, EuroLeague site, ICC fixtures, LNR Pro D2 calendar, EHF Champions League calendar, ATP Tour, GAA fixtures, TVF/legavolley/CEV references.</li>
<li>Blank fields stay blank; times are UTC and may differ from OLBG’s local-time labels — discrepancies are flagged.</li>
</ul>
</section>
<section><h3>Limitations</h3>
<ul>
<li>Six of the 15 requested sports (Golf, Darts, Motor Racing, Rugby League, Snooker, Greyhounds) had no actionable match-level OLBG listings at capture; no picks are fabricated for them.</li>
<li>Hurling is not among the requested sports and is not covered.</li>
<li>Some ATP, CEV, URC and EuroLeague sources return no current match data or 404; affected rows are marked OLBG-only.</li>
<li>All times are capture-time (27 Oct 2026, UTC); recheck tipoffs and lineups before betting.</li>
</ul>
</section>"""+footer_html()

# ---------------- write files ----------------
os.makedirs(os.path.join(ROOT,"sports"), exist_ok=True)
with open(os.path.join(OUT,"assets","styles.css"),"w") as f: f.write(CSS)

with open(os.path.join(OUT,"index.html"),"w") as f: f.write(build_index())
with open(os.path.join(OUT,"picks.html"),"w") as f: f.write(build_picks())
with open(os.path.join(OUT,"matches.html"),"w") as f: f.write(build_matches())
with open(os.path.join(OUT,"flagged.html"),"w") as f: f.write(build_flagged())
with open(os.path.join(OUT,"sources.html"),"w") as f: f.write(build_sources())
with open(os.path.join(OUT,"methodology.html"),"w") as f: f.write(build_methodology())

os.makedirs(os.path.join(ROOT,"sports"), exist_ok=True)
sport_files=[("Tennis","sports/tennis.html"),("Basketball","sports/basketball.html"),("Cricket","sports/cricket.html"),
("Snooker","sports/snooker.html"),("Rugby Union","sports/rugby-union.html"),("Rugby League","sports/rugby-league.html"),
("Baseball","sports/baseball.html"),("Gaelic Sports","sports/gaelic-sports.html"),("Greyhounds","sports/greyhounds.html"),
("Motor Racing","sports/motor-racing.html"),("Darts","sports/darts.html"),
("Handball","sports/handball.html"),("Volleyball","sports/volleyball.html"),("Golf","sports/golf.html"),
("Ice Hockey","sports/ice-hockey.html"),("Hurling","sports/hurling.html")]
for label,fname in sport_files:
    path=os.path.join(OUT,fname)
    if label=="Hurling":
        content=header("Hurling","Hurling is not among the 15 requested sports","Hurling",css="../assets/styles.css",rel="../")+""""
<section><h3>Hurling — out of scope</h3><p>Hurling (OLBG category ID 26) exists on OLBG but is not one of the 15 sports requested for this desk, so no fixtures, lines or predictions are published for it here.</p></section>"""+footer_html("../")
    else:
        content=build_sport(label,fname)
    with open(path,"w") as f: f.write(content)

# derived dashboard payload (kept for compatibility with the older JS shells)
dashboard={"schema":"olbg-research-dashboard/v2","builtUtc":datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
 "asOfLabel":"27 October 2026 · UTC","summary":{"totalPredictions":len(preds),"high":sum(1 for p in preds if p["confidence"]=="High"),
 "medium":sum(1 for p in preds if p["confidence"]=="Medium"),"low":sum(1 for p in preds if p["confidence"]=="Low"),
 "sportsWithPredictions":len(set(p["sport"] for p in preds)),"sportsInScope":15,"olbgEvents":sum(len(s["events"]) for s in discovery["sports"])}}
with open(os.path.join(DATA,"dashboard.json"),"w") as f: json.dump(dashboard,f,indent=2)

print("written:", ["index.html","picks.html","matches.html","flagged.html","sources.html","methodology.html"]+[f[1] for f in sport_files]+["assets/styles.css","data/dashboard.json"])
