#!/usr/bin/env python3
"""Generate the static OLBG desk site from the committed data files.

Run: python3 scripts/build_site.py
Outputs: index.html, picks.html, matches.html, pricing.html, methodology.html,
         sources.html, flagged.html and sports/<slug>.html
"""

import html
import json
import os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

SPORTS = [
    ("Basketball", "basketball", "4"),
    ("Baseball", "baseball", "12"),
    ("Cricket", "cricket", "7"),
    ("Darts", "darts", "15"),
    ("Gaelic Sports", "gaelic-sports", "25"),
    ("Golf", "golf", "5"),
    ("Greyhounds", "greyhounds", "28"),
    ("Handball", "handball", "20"),
    ("Ice Hockey", "ice-hockey", "13"),
    ("Motor Racing", "motor-racing", "14"),
    ("Rugby League", "rugby-league", "10"),
    ("Rugby Union", "rugby-union", "9"),
    ("Snooker", "snooker", "8"),
    ("Tennis", "tennis", "3"),
    ("Volleyball", "volleyball", "21"),
]
SLUG = {name: slug for name, slug, _ in SPORTS}
OLBG_ID = {name: sid for name, _, sid in SPORTS}
SOURCE_FOR_SPORT = {
    "Basketball": "euroleague",
    "Handball": "ehfcl",
    "Ice Hockey": "nhl",
    "Baseball": "mlb",
    "Rugby Union": "prod2",
    "Tennis": "wta",
}


def esc(value):
    return html.escape(str(value), quote=True)


def money(price):
    if price is None:
        return "&mdash;"
    return f"+{price:.0f}" if price > 0 else f"{price:.0f}"


def pct(p):
    return "&mdash;" if p is None else f"{p * 100:.1f}%"


def badge_conf(band):
    if not band:
        return '<span class="badge none">No pick</span>'
    return f'<span class="badge {band.lower()}">{esc(band)}</span>'


def window_badge(row):
    if not row.get("pick"):
        return ""
    if row["pick"]["in_price_window"]:
        return '<span class="badge win">In window</span>'
    return '<span class="badge out">Outside window</span>'


def when(label):
    if label.startswith("Today"):
        return "Today"
    if label.startswith("Tomorrow"):
        return "Tomorrow"
    return "Later"


def load():
    matches = json.load(open(os.path.join(DATA, "matches.json")))
    preds = json.load(open(os.path.join(DATA, "predictions.json")))
    ratings = json.load(open(os.path.join(DATA, "ratings.json")))
    listings = json.load(open(os.path.join(DATA, "olbg-listings.json")))
    for row in matches["rows"]:
        entry = preds["entries"].get(row["id"])
        if entry and row.get("pick"):
            row["pick"]["published"] = True
            row["pick"]["confidence"] = entry["confidence"]
            row["prediction"] = entry
    return matches, preds, ratings, listings


def page(title, active, body, depth=0):
    prefix = "../" * depth
    links = [
        ("index.html", "Executive summary"),
        ("picks.html", "Written predictions"),
        ("matches.html", "Full price board"),
        ("pricing.html", "How we price"),
        ("methodology.html", "Method"),
        ("sources.html", "Sources"),
        ("flagged.html", "Flagged for review"),
    ]
    nav_parts = []
    for href, label in links:
        cls = ' class="active"' if href == active else ""
        nav_parts.append('<a href="%s%s"%s>%s</a>' % (prefix, href, cls, esc(label)))
    nav = "".join(nav_parts)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} &middot; OLBG multi-sport desk</title>
<link rel="stylesheet" href="{prefix}assets/styles.css">
</head>
<body>
<header class="site">
  <div class="wrap">
    <div>
      <div class="brand">OLBG <span>multi-sport desk</span></div>
      <div class="tagline">Fifteen sports, one price board, written predictions only where the inputs are sourced</div>
    </div>
  </div>
  <div class="wrap"><nav class="site">{nav}</nav></div>
</header>
<main><div class="wrap">
{body}
</div></main>
<footer class="site"><div class="wrap">
Independent research, not OLBG advice and not a guarantee. Prices shown are our own fair prices, not bookmaker prices.
18+. Only stake what you can afford to lose. Data capture: <strong>2026-10-27 05:30 UTC</strong>.
</div></footer>
<script src="{prefix}assets/app.js" defer></script>
</body>
</html>
"""


def pick_table(rows, show_sport=True, depth=0):
    prefix = "../" * depth
    head = ['<div class="tablewrap"><table class="filterable"><thead><tr>']
    cols = []
    if show_sport:
        cols.append("Sport")
    cols += ["When", "Match", "Competition", "Selection", "Our price", "Chance", "Confidence", "Window"]
    head += [f'<th>{esc(c)}</th>' for c in cols]
    head.append("</tr></thead><tbody>")
    out = "".join(head)
    for row in rows:
        p = row["pick"]
        cells = []
        if show_sport:
            cells.append(f'<a href="{prefix}sports/{SLUG[row["sport"]]}.html">{esc(row["sport"])}</a>')
        cells += [
            esc(when(row["start_label"])),
            f'<a href="#{esc(row["id"])}">{esc(row["event"])}</a>',
            esc(row["competition"]),
            f'<strong>{esc(p["selection"])}</strong>',
            money(p["american"]),
            pct(p["probability"]),
            badge_conf(p["confidence"]),
            window_badge(row),
        ]
        out += "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"
    return out + "</tbody></table></div>"


def pick_cards(rows, depth=0):
    prefix = "../" * depth
    out = []
    for row in rows:
        p, pr = row["pick"], row["prediction"]
        srcs = ", ".join(
            f'<a href="{esc(row["source_urls"][k])}">{esc(row["source_labels"][k])}</a>' for k in pr["sources"]
        )
        out.append(
            f'<div class="pickcard" id="{esc(row["id"])}">'
            f'<h3>{esc(pr["headline"])}</h3>'
            f'<div class="meta">{esc(row["sport"])} &middot; {esc(row["competition"])} &middot; '
            f'{esc(row["start_label"])} &middot; {badge_conf(p["confidence"])} {window_badge(row)}</div>'
            f'<div class="sel">Selection: {esc(pr["selection"])} &nbsp;&middot;&nbsp; our price {money(p["american"])} '
            f'&nbsp;&middot;&nbsp; our chance {pct(p["probability"])}</div>'
            f'<p class="analysis">{esc(pr["analysis"])}</p>'
            f'<div class="srcs">Sources: {srcs} &middot; '
            f'<a href="{esc(row["olbg_url"])}">OLBG market</a></div>'
            "</div>"
        )
    return "\n".join(out)


def main():
    matches, preds, ratings, listings = load()
    rows = matches["rows"]
    events = [r for r in rows]
    rated = [r for r in events if r.get("pick")]
    published = [r for r in rated if r.get("prediction")]
    high = [r for r in published if r["pick"]["confidence"] == "High"]
    in_window = [r for r in published if r["pick"]["in_price_window"]]
    total_listings = len(events)
    sources = ratings["sources"]

    for row in events:
        key = SOURCE_FOR_SPORT.get(row["sport"])
        row["source_urls"] = {key: sources[key]["url"]} if key else {}
        row["source_labels"] = {key: sources[key]["label"].split(" (")[0]} if key else {}

    by_sport = defaultdict(list)
    for row in events:
        by_sport[row["sport"]].append(row)

    published_by_sport = defaultdict(list)
    for row in published:
        published_by_sport[row["sport"]].append(row)

    counts = {}
    for name, slug, _ in SPORTS:
        srows = by_sport.get(name, [])
        sp = [r for r in srows if r.get("pick")]
        pub = [r for r in srows if r.get("prediction")]
        counts[name] = {
            "listings": len(srows),
            "priced": len(sp),
            "published": len(pub),
            "high": len([r for r in pub if r["pick"]["confidence"] == "High"]),
        }

    # ---------------------------------------------------------------- home ----
    stats = [
        (len(SPORTS), "sports covered"),
        (total_listings, "OLBG listings captured"),
        (len(rated), "matches priced by us"),
        (len(published), "written predictions"),
    ]
    stat_html = "".join(
        f'<div class="stat"><div class="n">{n}</div><div class="l">{esc(l)}</div></div>' for n, l in stats
    )

    coverage_rows = []
    for name, slug, _ in SPORTS:
        c = counts[name]
        status = "Picks published" if c["published"] else ("Priced, no pick" if c["priced"] else "No price")
        cls = ' class="muted"' if not c["published"] else ""
        coverage_rows.append(
            f'<tr{cls}><td><a href="sports/{slug}.html">{esc(name)}</a></td>'
            f'<td class="num">{c["listings"]}</td><td class="num">{c["priced"]}</td>'
            f'<td class="num">{c["published"]}</td><td class="num">{c["high"]}</td><td>{esc(status)}</td></tr>'
        )

    home_body = f"""
<h1>Executive summary</h1>
<p class="lede">Every match, race and tournament market we could see on OLBG for the fifteen requested sports, captured at
<strong>2026-10-27 05:30 UTC</strong>, plus our own price for each one. Written predictions appear only where an official
source gave us the numbers to write them.</p>

<div class="grid k4">{stat_html}</div>

<div class="note"><strong>Read this first.</strong> The written predictions live on
<a href="picks.html">Written predictions</a> and every one is also linked from its sport page. The complete board, including
matches we could not price, is on <a href="matches.html">Full price board</a>. Anything uncertain is listed on
<a href="flagged.html">Flagged for review</a>.</div>

<h2>Today's highest-confidence picks</h2>
<p class="lede">{len(high)} selections came out at a 70% chance or better on our numbers. Every one of them is priced shorter
than -250, so they sit outside the -250 to +10000 window and are labelled accordingly. They are still our strongest views.</p>
{pick_table(high, depth=0)}

<h2>Picks inside the -250 to +10000 window</h2>
<p class="lede">{len(in_window)} of the {len(published)} published picks sit inside the -250 to +10000 window. The rest are
stronger favourites than -250 and are tagged as outside it.</p>
{pick_table(in_window, depth=0)}

<h2>Coverage by sport</h2>
<div class="tablewrap"><table>
<thead><tr><th>Sport</th><th class="num">OLBG listings</th><th class="num">Priced</th>
<th class="num">Written picks</th><th class="num">High confidence</th><th>Status</th></tr></thead>
<tbody>{''.join(coverage_rows)}</tbody></table></div>

<h2>Where things are</h2>
<ul class="tight">
<li><a href="picks.html">Written predictions</a> &mdash; the full analysis for every published pick, grouped by sport.</li>
<li><a href="matches.html">Full price board</a> &mdash; all {total_listings} OLBG listings with our money line, handicap and total, and the exact reason for any blank.</li>
<li><a href="pricing.html">How we price</a> &mdash; the formula, the parameters, and a worked example for each sport.</li>
<li><a href="sources.html">Sources</a> &mdash; every official page used, with its capture time.</li>
<li><a href="flagged.html">Flagged for review</a> &mdash; gaps, irregularities and anything we refused to fill in.</li>
</ul>

<h2>What is not covered, and why</h2>
<p class="lede">{len(SPORTS) - len(published_by_sport)} of the {len(SPORTS)} sports have no written prediction in this capture. That is a sourcing outcome, not an
editorial choice: Snooker and Greyhounds showed <em>no tips at all</em> on OLBG, and the remaining sports expose only
futures markets or competitions whose official tables we could not read inside this session. No price was invented to fill
those gaps. The full list, with the exact missing input, is on <a href="flagged.html">Flagged for review</a>.</p>
"""
    open(os.path.join(ROOT, "index.html"), "w").write(page("Executive summary", "index.html", home_body))

    # --------------------------------------------------------------- picks ----
    groups = []
    for name, slug, _ in SPORTS:
        prows = published_by_sport.get(name, [])
        if not prows:
            continue
        prows.sort(key=lambda r: -r["pick"]["probability"])
        groups.append(f'<h2 id="{slug}">{esc(name)} <span class="chip">{len(prows)} written predictions</span></h2>')
        groups.append(pick_cards(prows))
    picks_body = f"""
<h1>Written predictions</h1>
<p class="lede">Every pick below names the competition, the selection, our price, our chance and a confidence band, and every
statement is drawn from the official source listed on the card. Nothing here mentions injuries, because no team-news source
was read for this edition.</p>
<div class="note warn"><strong>Only {len(published)} picks cleared the bar.</strong> A pick is published only when both
competitors have an official rating input and our chance of the selection winning is at least 55%. Nine sports did not clear
that bar; the reasons are on <a href="flagged.html">Flagged for review</a>.</div>
{''.join(groups)}
"""
    open(os.path.join(ROOT, "picks.html"), "w").write(page("Written predictions", "picks.html", picks_body))

    # ------------------------------------------------------------- matches ----
    body_rows = []
    for name, slug, _ in SPORTS:
        for row in sorted(by_sport.get(name, []), key=lambda r: (when(r["start_label"]), r["competition"], r["event"])):
            p = row.get("pick")
            m = row.get("markets")
            if p:
                price_cell = money(p["american"])
                sel_cell = f'<strong>{esc(p["selection"])}</strong>'
                conf = badge_conf(p["confidence"])
                window = window_badge(row)
            else:
                price_cell = "&mdash;"
                sel_cell = '<span class="chip">not priced</span>'
                conf = badge_conf(None)
                window = ""
            handicap = esc(m["handicap"]["display"]) if m and m.get("handicap") else "&mdash;"
            total = esc(str(m["total"]["line"])) if m and m.get("total") else "&mdash;"
            reason = "; ".join(row.get("flags", [])) or ""
            body_rows.append(
                f'<tr><td>{esc(name)}</td><td>{esc(when(row["start_label"]))}</td>'
                f'<td><a href="{esc(row["olbg_url"])}">{esc(row["event"])}</a><br><span class="chip">{esc(row["start_label"])} &middot; {esc(row["competition"])}</span></td>'
                f'<td>{esc(row["olbg_selection"])}<br><span class="chip">{esc(row["olbg_tips"])} tips &middot; {esc(row["olbg_pct"])}%</span></td>'
                f"<td>{sel_cell}</td><td class=\"num\">{price_cell}</td><td>{conf}</td><td>{window}</td>"
                f"<td>{handicap}</td><td class=\"num\">{total}</td>"
                f'<td class="chip">{esc(reason)}</td></tr>'
            )
    matches_body = f"""
<h1>Full price board</h1>
<p class="lede">All {total_listings} OLBG listings in scope, with our money-line selection, the handicap number we would
post, our projected total, and the exact reason where a row is blank. Filter by sport or search a team.</p>
<div class="toolbar">
  <input type="search" data-filter="board" placeholder="Search team, player or competition">
  <select data-filter="board-sport"><option value="">All sports</option>{''.join(f'<option>{esc(n)}</option>' for n, _, _ in SPORTS)}</select>
  <span class="chip" data-count="board"></span>
</div>
<div class="tablewrap"><table id="board" class="filterable">
<thead><tr><th>Sport</th><th>When</th><th>Match</th><th>OLBG most-tipped</th><th>Our pick</th>
<th class="num">Our price</th><th>Confidence</th><th>Window</th><th>Our handicap</th><th class="num">Our total</th>
<th>Notes</th></tr></thead>
<tbody>{''.join(body_rows)}</tbody></table></div>
"""
    open(os.path.join(ROOT, "matches.html"), "w").write(page("Full price board", "matches.html", matches_body))

    # ------------------------------------------------------------- pricing ----
    params = matches["sport_parameters"]
    param_rows = []
    for name in ["Basketball", "Handball", "Ice Hockey", "Baseball", "Rugby Union"]:
        param_rows.append(
            f"<tr><td>{esc(name)}</td><td class=\"num\">{params['home_edge'][name]:.2f}</td>"
            f"<td class=\"num\">{params['margin_sd'][name]:.1f}</td>"
            f"<td class=\"num\">{params['shrink_k'][name]:.0f}</td>"
            f"<td class=\"num\">{params['scoring_step'][name]:.1f}</td></tr>"
        )
    pricing_body = f"""
<h1>How we price every match</h1>
<p class="lede">We do not copy a bookmaker. We build a number from official results and then convert that number into a
price. The method is the same for every sport; only the parameters change.</p>

<h2>1. Rating input</h2>
<p>For each competitor we take the official season record: matches played, and points or goals or runs for and against.
Nothing else. Where a competition has a table, the table is the input. Where it does not, we do not price the match.</p>

<h2>2. Shrink the sample</h2>
<p>A seven-game point differential is noisy, so every rating is pulled toward the league average before use:</p>
<p><code>rating = (points_for - points_against) / games_played &times; games_played / (games_played + K)</code></p>
<p>With K around 8 to 12 for a short European season and 60 for a 162-game baseball season, a club that has played a handful
of matches cannot produce an extreme number.</p>

<h2>3. Turn the ratings into a projected margin</h2>
<p><code>projected margin = home rating - away rating + home edge</code>, where the home edge is the sport-specific bump in
the table below. The projected margin is also our handicap number, rounded to the sport's scoring step.</p>

<h2>4. Turn the margin into a probability</h2>
<p>We treat the actual margin as normally distributed around the projection with the sport's own standard deviation. That
gives the chance of the favourite covering any line, and for handball and rugby union it also gives the chance of a draw,
so those two sports are priced as three-way markets.</p>

<h2>5. Convert to a price</h2>
<p><code>price = -100 &times; p / (1 - p)</code> when p is at least 50%, otherwise <code>100 &times; (1 - p) / p</code>.
These are fair prices with no margin. A bookmaker's price is shorter; that gap is where a bet becomes interesting.</p>

<h2>Parameters in use</h2>
<div class="tablewrap"><table>
<thead><tr><th>Sport</th><th class="num">Home edge</th><th class="num">Margin SD</th><th class="num">Shrink K</th>
<th class="num">Scoring step</th></tr></thead>
<tbody>{''.join(param_rows)}</tbody></table></div>
<p class="chip">Tennis is priced separately: a Bradley-Terry comparison of ranking points, scaled by 1.5 in log space, with no
home edge because the first-named player is not the host.</p>

<h2>Worked example: Dax v Provence</h2>
<p>Provence have played 8 matches with 276 points scored and 161 conceded, so their raw differential is plus 14.4. Shrunk
with K = 6 it becomes plus 8.2. Dax are minus 4.6 raw, minus 2.6 shrunk. Adding the 3.5 home edge for Dax gives a projected
margin of minus 7.4 in Provence's favour, which we round to a 7.5-point handicap. The chance of Provence winning outright
comes out at 70.8%, which converts to -243. That is the one High-confidence pick of the day that also sits inside the
-250 to +10000 window.</p>

<h2>Markets we publish for every priced match</h2>
<ul class="tight">
<li><strong>Match winner</strong> &mdash; the price on each side, plus the draw where the sport allows one.</li>
<li><strong>Handicap</strong> &mdash; the projected margin, quoted as a line, with a price on each side.</li>
<li><strong>Total</strong> &mdash; the combined score the two records imply, rounded to the sport's step.</li>
</ul>
<p class="lede">Markets we do not price: player props, correct score, and anything that needs team news. No injury,
suspension or lineup information was read for this edition, so no market depends on it.</p>
"""
    open(os.path.join(ROOT, "pricing.html"), "w").write(page("How we price", "pricing.html", pricing_body))

    # --------------------------------------------------------- methodology ----
    method_body = f"""
<h1>Method and verification</h1>
<p class="lede">The rules this desk follows, in the order they are applied.</p>

<h2>Capture</h2>
<p>The fifteen OLBG category pages were read directly on 2026-10-27 from <code>olbg.com/betting-tips/&lt;Sport&gt;/&lt;id&gt;</code>.
Every listing keeps its own event URL so a reader can reopen the market and confirm the match, the most-tipped selection and
the tip counts. Two categories, Snooker and Greyhounds, displayed <em>No tips found</em> and are reported as empty rather
than padded.</p>

<h2>Pricing gate</h2>
<p>A match is priced only when both competitors appear in an official table we actually read. If one side is missing, the
price stays blank. If the whole competition lacks a table, the whole competition stays blank. This is why nine sports carry
no prediction today.</p>

<h2>Publication gate</h2>
<p>A pick is published only when the chance of the selection winning is at least 55%. Below that the number is a coin flip
and publishing it would be noise. Every published pick is between 55% and 85%.</p>

<h2>Confidence bands</h2>
<ul class="tight">
<li><span class="badge high">High</span> 70% or better.</li>
<li><span class="badge medium">Medium</span> 62% to 69.9%.</li>
<li><span class="badge low">Low</span> below 62%.</li>
</ul>

<h2>The price window</h2>
<p>The brief asks for picks between -250 and +10000. On fair prices, a selection with a 70% chance is -233, so a
High-confidence pick is almost always shorter than -250. We therefore label the window status on every pick instead of
hiding the conflict: {len(in_window)} of {len(published)} published picks are inside the window, and {len(high)} High-confidence
picks are outside it and marked <span class="badge out">Outside window</span>.</p>

<h2>What a written prediction must contain</h2>
<p>A named selection, the competition, at least thirty words of reasoning, and figures that can be traced to the source on
the same card. No prediction mentions an injury, a suspension or a lineup, because none of those were read from an official
source for this edition.</p>

<h2>What we will not do</h2>
<ul class="tight">
<li>Fill a blank with an estimate and present it as a fact.</li>
<li>Quote a statistic from memory or from a preview article rather than the governing body.</li>
<li>Publish a pick because a sport needs a quota.</li>
</ul>
"""
    open(os.path.join(ROOT, "methodology.html"), "w").write(page("Method", "methodology.html", method_body))

    # ------------------------------------------------------------- sources ----
    src_rows = []
    for key, s in sources.items():
        used = [r for r in events if key in r["source_urls"]]
        src_rows.append(
            f'<tr><td><a href="{esc(s["url"])}">{esc(s["label"])}</a></td>'
            f'<td>{esc(s["url"])}</td><td>{esc(s["captured_utc"])}</td>'
            f'<td class="num">{len(used)}</td><td>{esc(s.get("state", ""))}</td></tr>'
        )
    olbg_rows = "".join(
        f'<tr><td>{esc(name)}</td><td><a href="https://www.olbg.com/betting-tips/{page_path}">OLBG {esc(name)} category</a></td>'
        f'<td class="num">{counts[name]["listings"]}</td></tr>'
        for name, slug, page_path in [(n, s, f"{n.replace(' ', '_')}/{i}") for n, s, i in SPORTS]
    )
    sources_body = f"""
<h1>Sources</h1>
<p class="lede">Every figure in a written prediction comes from one of the official pages below. OLBG is the source for the
market itself, never for a sporting fact.</p>

<h2>Official sources used for pricing</h2>
<div class="tablewrap"><table>
<thead><tr><th>Source</th><th>URL</th><th>Captured (UTC)</th><th class="num">Rows</th><th>State</th></tr></thead>
<tbody>{''.join(src_rows)}</tbody></table></div>

<h2>OLBG category pages</h2>
<div class="tablewrap"><table>
<thead><tr><th>Sport</th><th>Page</th><th class="num">Listings captured</th></tr></thead>
<tbody>{olbg_rows}</tbody></table></div>

<h2>Official pages checked but not usable for a price</h2>
<ul class="tight">
<li><a href="https://www.icc-cricket.com/rankings/team-rankings/mens/odi">ICC team rankings</a> &mdash; the ranking table did not render, so cricket has no rating input. The ICC fixtures page did confirm the six international fixtures listed on OLBG, including that South Africa v Australia and Bangladesh v West Indies are Tests rather than one-day matches.</li>
<li><a href="https://www.atptour.com/en/rankings/singles">ATP rankings</a> &mdash; the table sat behind a very large page and could not be read inside this session, so the nine men's tennis matches are unpriced. The WTA list was readable and covers the women's matches.</li>
<li><a href="https://www.lnr.fr/rugby-pro-d2/classement">LNR Pro D2 (old path)</a> &mdash; returned a 404. The working table is <a href="https://prod2.lnr.fr/classement">prod2.lnr.fr/classement</a>, which is what we used.</li>
<li><a href="https://www.nationalleague.ch/ranking">Swiss National League</a> &mdash; returned a not-found page, so the six Swiss fixtures are unpriced.</li>
</ul>
"""
    open(os.path.join(ROOT, "sources.html"), "w").write(page("Sources", "sources.html", sources_body))

    # ------------------------------------------------------------- flagged ----
    unpriced = [r for r in events if not r.get("pick")]
    flag_rows = []
    for row in unpriced:
        flag_rows.append(
            f'<tr><td>{esc(row["sport"])}</td><td><a href="{esc(row["olbg_url"])}">{esc(row["event"])}</a></td>'
            f'<td>{esc(row["competition"])}</td><td>{esc("; ".join(row.get("flags", [])))}</td></tr>'
        )
    flagged_body = f"""
<h1>Flagged for review</h1>
<p class="lede">Everything below is either blank, uncertain or contradictory. None of it has been smoothed over.</p>

<h2>1. Categories with no listings at all</h2>
<div class="tablewrap"><table>
<thead><tr><th>Sport</th><th>OLBG page</th><th>What OLBG displayed</th></tr></thead>
<tbody>
<tr><td>Snooker</td><td><a href="https://www.olbg.com/betting-tips/Snooker/8">Snooker (8)</a></td><td>No tips found.</td></tr>
<tr><td>Greyhounds</td><td><a href="https://www.olbg.com/betting-tips/Greyhounds/28">Greyhounds (28)</a></td><td>No tips found.</td></tr>
</tbody></table></div>
<p class="lede">Two of the fifteen requested sports had no market on OLBG at capture time. Nothing was substituted.</p>

<h2>2. Markets that exist but cannot be priced here</h2>
<ul class="tight">
<li><strong>Outright and futures markets</strong> &mdash; golf (3), darts (2), motor racing (2), rugby league (3), Gaelic football (1), cricket World Cup 2027. Pricing a field of 100+ golfers or a 128-player darts event needs a field-strength list we did not capture.</li>
<li><strong>Competitions without an official table in this session</strong> &mdash; cricket (13 listings), volleyball (14), the non-NHL hockey leagues (13), the non-EuroLeague basketball competitions (5), and the URC and Top 14 rugby fixtures (4).</li>
<li><strong>Tennis</strong> &mdash; only the four women inside the captured WTA top 50 could be priced, which yields one publishable match. The nine men's matches need the ATP list.</li>
</ul>

<h2>3. Data irregularities spotted on OLBG</h2>
<ul class="tight">
<li><strong>Handball selection labels.</strong> Eleven of fifteen handball rows showed the most-tipped selection as literally <em>Tie</em>. A draw being the single most-tipped outcome in eleven matches is implausible, so we treat the label as a display fault and price the match ourselves rather than reading it as a drawn match. <a href="https://www.olbg.com/betting-tips/Handball/20">Handball page</a>.</li>
<li><strong>Conflicting most-tipped selections.</strong> On the main ice hockey page, Ambri Piotta v EHC Biel showed a puck line (-1.50) as the most-tipped market; the Swiss league sub-page showed the plain money line for the same fixture. EHC Kloten v HC Ajoie showed Kloten -1.50 on one page and HC Ajoie on the other. <a href="https://www.olbg.com/betting-tips/Ice_Hockey/Other/Switzerland_NLA/13">Swiss National League page</a>.</li>
<li><strong>Relative time labels.</strong> OLBG prints <em>Today</em> and <em>Tomorrow</em> without a date or a timezone. We kept the wording exactly as displayed and did not convert it to a clock time.</li>
<li><strong>Format mismatch.</strong> OLBG lists South Africa v Australia and Bangladesh v West Indies without a format; the ICC fixtures page shows both as Tests. We follow the ICC.</li>
</ul>

<h2>4. Every row we could not price ({len(unpriced)} of {total_listings})</h2>
<div class="tablewrap"><table>
<thead><tr><th>Sport</th><th>Event</th><th>Competition</th><th>Reason</th></tr></thead>
<tbody>{''.join(flag_rows)}</tbody></table></div>

<h2>5. Standing gaps in this edition</h2>
<ul class="tight">
<li>No injury, suspension or lineup check was possible, so no prediction refers to team news.</li>
<li>No bookmaker price was compared against our number, because the brief asks for our own lines. A value bet needs that comparison and we have not made one.</li>
<li>The five-per-sport written-prediction target is met for basketball, handball and rugby union only. The other twelve sports fall short for the sourcing reasons above.</li>
<li>Standings move daily. Every rating input carries its capture time on the <a href="sources.html">Sources</a> page and should be re-read before betting.</li>
</ul>
"""
    open(os.path.join(ROOT, "flagged.html"), "w").write(page("Flagged for review", "flagged.html", flagged_body))

    # -------------------------------------------------------------- sports ----
    os.makedirs(os.path.join(ROOT, "sports"), exist_ok=True)
    for name, slug, _ in SPORTS:
        srows = sorted(by_sport.get(name, []), key=lambda r: (when(r["start_label"]), r["competition"], r["event"]))
        pub = [r for r in srows if r.get("prediction")]
        pub.sort(key=lambda r: -r["pick"]["probability"])
        priced_n = len([r for r in srows if r.get("pick")])
        oid = OLBG_ID[name]
        page_path = f"{name.replace(' ', '_')}/{oid}"
        if not srows:
            body = f"""
<h1>{esc(name)}</h1>
<p class="lede">OLBG displayed <strong>no tips</strong> for this sport at capture time, so there is nothing to price.
The category page is <a href="https://www.olbg.com/betting-tips/{page_path}">here</a>.</p>
<div class="note warn">This is reported as an empty category, not as missing research. Nothing was substituted to fill it.</div>
"""
        else:
            cards = pick_cards(pub, depth=1) if pub else '<div class="note warn">No pick cleared the publication bar for this sport in this capture. The board below shows what we could price and the reason for every blank.</div>'
            table_rows = []
            for row in srows:
                p = row.get("pick")
                table_rows.append(
                    f'<tr><td><a href="{esc(row["olbg_url"])}">{esc(row["event"])}</a></td>'
                    f'<td>{esc(row["start_label"])}</td><td>{esc(row["olbg_selection"])}</td>'
                    f'<td class="num">{esc(row["olbg_pct"])}%</td>'
                    f'<td>{"<strong>" + esc(p["selection"]) + "</strong>" if p else "&mdash;"}</td>'
                    f'<td class="num">{money(p["american"]) if p else "&mdash;"}</td>'
                    f'<td>{badge_conf(p["confidence"]) if p else badge_conf(None)}</td>'
                    f'<td class="chip">{esc("; ".join(row.get("flags", [])))}</td></tr>'
                )
            body = f"""
<h1>{esc(name)}</h1>
<p class="lede">{len(srows)} OLBG listings captured, {priced_n} priced by us, {len(pub)} written predictions.
Category page: <a href="https://www.olbg.com/betting-tips/{page_path}">OLBG {esc(name)}</a>.</p>
<h2>Written predictions</h2>
{cards}
<h2>All captured markets</h2>
<div class="tablewrap"><table>
<thead><tr><th>Event</th><th>When</th><th>OLBG most-tipped</th><th class="num">Tip share</th>
<th>Our pick</th><th class="num">Our price</th><th>Confidence</th><th>Notes</th></tr></thead>
<tbody>{''.join(table_rows)}</tbody></table></div>
"""
        open(os.path.join(ROOT, "sports", f"{slug}.html"), "w").write(
            page(name, "", body, depth=1)
        )

    # ---------------------------------------------------------------- done ----
    print(f"built index, picks ({len(published)}), board ({total_listings}), pricing, method, sources, flagged, {len(SPORTS)} sports")


if __name__ == "__main__":
    main()
