#!/usr/bin/env python3
"""Build the OLBG picks board (static HTML) from curated JSON in data/board/.

Line origination is fully deterministic and documented on methodology.html:
  consensus c = tips_for / tips_total (OLBG market share)
  sample weight w = n / (n + 4) (Bayesian shrinkage toward a coin flip)
  p_shrunk = 0.5 + w * (c - 0.5)
  where an independent hosted-market probability is recorded, that sourced
  market probability is used as p_fair (the OLBG consensus remains shown as
  confirmation); otherwise p_fair = p_shrunk.
American/decimal prices and confidence bands are then derived from p_fair.
Rows flagged our_line_blank are published without a price.
"""
from __future__ import annotations

import json
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "board"
OUT = ROOT / "board"
SPORT_ORDER = [
    ("golf", "Golf"), ("volleyball", "Volleyball"), ("rugby-union", "Rugby Union"),
    ("cricket", "Cricket"), ("snooker", "Snooker"), ("darts", "Darts"),
    ("baseball", "Baseball"), ("gaelic-sports", "Gaelic Sports"),
    ("greyhounds", "Greyhounds"), ("tennis", "Tennis"), ("motor-racing", "Motor Racing"),
    ("handball", "Handball"), ("ice-hockey", "Ice Hockey"),
    ("basketball", "Basketball"), ("rugby-league", "Rugby League"),
]
BANNED = ("model", "verified")


def load_sports() -> list[dict]:
    sports: dict[str, dict] = {}
    for path in sorted(DATA.glob("board-data-*.json")):
        payload = json.loads(path.read_text())
        for sport in payload["sports"]:
            sports[sport["key"]] = sport
    return [sports[k] for k, _ in SPORT_ORDER if k in sports]


def american(p: float) -> int:
    if p >= 0.5:
        return -round(100 * p / (1 - p))
    return round(100 * (1 - p) / p)


def confidence(p: float) -> str:
    if p >= 0.70:
        return "high"
    if p >= 0.55:
        return "medium"
    return "low"


def originate(row: dict) -> dict:
    out = dict(row)
    if row.get("our_line_blank") or not row.get("tips_total"):
        out["fair_prob"] = None
        out["us_odds"] = None
        out["decimal_odds"] = None
        out["confidence"] = None
        out["in_band"] = None
        out["our_selection"] = None
        return out
    n = row["tips_total"]
    c = row["tips_for"] / n
    w = n / (n + 4)
    p = 0.5 + w * (c - 0.5)
    if row.get("market_prob") is not None:
        # Independently sourced hosted-market probability takes precedence;
        # the shrunk OLBG consensus is still displayed on the row.
        p = row["market_prob"]
    p = round(p, 4)
    us = american(p)
    out["fair_prob"] = p
    out["us_odds"] = us
    out["decimal_odds"] = round(1 / p, 2)
    out["confidence"] = confidence(p)
    out["in_band"] = -250 <= us <= 10000
    out["our_selection"] = row.get("our_selection_override") or row["olbg_selection"]
    return out


def esc(s) -> str:
    return html.escape(str(s)) if s is not None else ""


def conf_badge(level: str | None) -> str:
    if not level:
        return '<span class="badge badge-none">no line</span>'
    return f'<span class="badge badge-{level}">{level}</span>'


def band_badge(in_band: bool | None) -> str:
    if in_band is None:
        return ""
    if in_band:
        return '<span class="badge badge-band">in -250..+10000 band</span>'
    return '<span class="badge badge-offband">outside target band</span>'


def source_links(row: dict) -> str:
    links = f'<a href="{esc(row["olbg_url"])}">OLBG event</a>'
    if row.get("official_url"):
        scope = row.get("official_scope", "register")
        label = "official (event)" if scope == "event" else "official (register)"
        links += f' &middot; <a href="{esc(row["official_url"])}">{label}</a>'
    return links


def flags_html(row: dict) -> str:
    flags = row.get("flags", [])
    if not flags:
        return ""
    return "<ul class='flags'>" + "".join(f"<li>{esc(f)}</li>" for f in flags) + "</ul>"


def base_page(title: str, body: str, depth: str = "") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · OLBG Picks Board</title>
<link rel="stylesheet" href="{depth}assets/styles.css">
</head>
<body>
<header class="topbar">
  <div class="wrap topbar-inner">
    <a class="brand" href="{depth}index.html">OLBG Picks Board <span>27 Oct 2026</span></a>
    <nav>
      <a href="{depth}index.html">Executive summary</a>
      <a href="{depth}matches.html">All matches &amp; lines</a>
      <a href="{depth}flagged.html">Flagged for review</a>
      <a href="{depth}methodology.html">Methodology</a>
      <a href="{depth}sources.html">Sources</a>
    </nav>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="wrap footer">
  <p>Research dashboard generated 2026-10-27 from live OLBG listings and official sources listed per row. Tips are opinions for adults 18+. Every originated line is derived from the documented rule on the Methodology page; blank values could not be confirmed and are flagged rather than inferred.</p>
</footer>
</body>
</html>"""


def render_sport_page(sport: dict) -> str:
    rows = [originate(r) for r in sport["rows"]]
    picks = [r for r in rows if r.get("prediction")]
    high = [r for r in rows if r.get("confidence") == "high"]
    parts = [f"<h1>{esc(sport['label'])}</h1>"]
    parts.append(
        f"<div class='stat-row'><div class='stat'><b>{len(rows)}</b><span>OLBG markets</span></div>"
        f"<div class='stat'><b>{len(picks)}</b><span>written predictions</span></div>"
        f"<div class='stat'><b>{len(high)}</b><span>high-confidence lines</span></div></div>"
    )
    parts.append(
        f"<p class='note'><b>OLBG hub:</b> <a href='{esc(sport['olbg_hub'])}'>{esc(sport['olbg_hub'])}</a><br>"
        f"<b>Official register:</b> <a href='{esc(sport['official_register'])}'>{esc(sport['official_register'])}</a></p>"
    )
    if sport.get("official_register_note"):
        parts.append(f"<p class='note'>{esc(sport['official_register_note'])}</p>")
    if sport.get("empty_reason"):
        parts.append(f"<div class='callout'>{esc(sport['empty_reason'])}</div>")
    if picks:
        parts.append("<h2>Written predictions</h2>")
        for r in picks:
            independent = r.get("our_selection_override") is not None
            parts.append(
                "<article class='pick-card'>"
                f"<div class='pick-head'><h3>{esc(r['event'])}</h3>"
                f"{conf_badge(r['confidence'])}"
                f"{('<span class=' + chr(39) + 'badge badge-independent' + chr(39) + '>independent of OLBG consensus</span>') if independent else ''}</div>"
                f"<p class='pick-meta'>{esc(r.get('competition',''))} · {esc(r.get('when',''))} · {esc(r.get('market',''))}</p>"
                f"<p class='pick-selection'>Our selection: <b>{esc(r['our_selection'])}</b> "
                f"at fair price <b>{'+' if r['us_odds'] and r['us_odds'] > 0 else ''}{esc(r['us_odds'])}</b> "
                f"(fair probability {round(r['fair_prob']*100)}%, decimal {esc(r['decimal_odds'])}) "
                f"{band_badge(r['in_band'])}</p>"
                f"<p class='pick-text'>{esc(r['prediction'])}</p>"
                f"<p class='pick-sources'>{source_links(r)}</p>"
                f"{flags_html(r)}"
                "</article>"
            )
    if rows:
        parts.append("<h2>All markets and originated lines</h2>")
        parts.append(render_table(rows))
    return base_page(f"{sport['label']} · OLBG Picks Board", "".join(parts), depth="../")


def render_table(rows: list[dict]) -> str:
    head = ("<div class='table-scroll'><table class='data'><thead><tr>"
            "<th>Sport</th><th>Event</th><th>Competition</th><th>When (OLBG)</th><th>Market</th>"
            "<th>OLBG selection</th><th>Tips</th><th>Consensus</th><th>Our selection</th>"
            "<th>Fair prob.</th><th>Our price (US)</th><th>Conf.</th><th>Band</th><th>Sources</th>"
            "</tr></thead><tbody>")
    body = []
    for r in rows:
        if r.get("fair_prob") is None:
            prob = us = conf = band = sel = "—"
        else:
            prob = f"{round(r['fair_prob']*100)}%"
            us = f"{'+' if r['us_odds'] > 0 else ''}{r['us_odds']}"
            conf = conf_badge(r["confidence"])
            band = "yes" if r["in_band"] else "no"
            sel = esc(r["our_selection"])
            if r.get("our_selection_override"):
                sel += " <span class='badge badge-independent'>independent</span>"
        consensus = f"{r['tips_for']}/{r['tips_total']} ({round(100*r['tips_for']/r['tips_total'])}%)" if r.get("tips_total") else "no tips"
        body.append(
            "<tr>"
            f"<td>{esc(r.get('sport_label',''))}</td>"
            f"<td>{esc(r['event'])}</td><td>{esc(r.get('competition',''))}</td>"
            f"<td>{esc(r.get('when',''))}</td><td>{esc(r.get('market',''))}</td>"
            f"<td>{esc(r.get('olbg_selection') or '—')}</td><td>{consensus}</td>"
            f"<td>{sel}</td><td>{prob}</td><td>{us}</td><td>{conf}</td><td>{band}</td>"
            f"<td class='sources'>{source_links(r)}</td>"
            "</tr>"
        )
    return head + "".join(body) + "</tbody></table></div>"


def render_index(sports: list[dict]) -> str:
    all_rows = []
    for s in sports:
        for r in s["rows"]:
            r = originate(r)
            r["sport_label"] = s["label"]
            r["sport_key"] = s["key"]
            all_rows.append(r)
    priced = [r for r in all_rows if r.get("fair_prob") is not None]
    high = [r for r in priced if r["confidence"] == "high"]
    medium = [r for r in priced if r["confidence"] == "medium"]
    picks = [r for r in all_rows if r.get("prediction")]
    flagged = sum(len(r.get("flags", [])) for r in all_rows)
    parts = [
        "<h1>Executive summary</h1>",
        "<p class='lede'>Live OLBG listings across the 15 requested sports were collected on 27 Oct 2026, cross-checked against official league and governing-body sources, and re-priced with the documented origination rule. Every row below links to its OLBG event page and an official source; values that could not be confirmed are left blank and flagged.</p>",
        "<div class='stat-row'>"
        f"<div class='stat'><b>{len(all_rows)}</b><span>markets captured</span></div>"
        f"<div class='stat'><b>{len(priced)}</b><span>lines originated</span></div>"
        f"<div class='stat'><b>{len(picks)}</b><span>written predictions</span></div>"
        f"<div class='stat'><b>{len(high)}</b><span>high confidence</span></div>"
        f"<div class='stat'><b>{len(medium)}</b><span>medium confidence</span></div>"
        f"<div class='stat'><b>{flagged}</b><span>review flags raised</span></div>"
        "</div>",
        "<h2>Sports</h2>",
        "<div class='sport-grid'>",
    ]
    for s in sports:
        rows = [originate(r) for r in s["rows"]]
        n_pick = sum(1 for r in rows if r.get("prediction"))
        n_high = sum(1 for r in rows if r.get("confidence") == "high")
        pred_word = "prediction" if n_pick == 1 else "predictions"
        parts.append(
            f"<a class='sport-card' href='sports/{s['key']}.html'>"
            f"<b>{esc(s['label'])}</b>"
            f"<span>{len(rows)} markets · {n_pick} {pred_word} · {n_high} high</span></a>"
        )
    parts.append("</div>")
    parts.append("<h2>High-confidence picks</h2>")
    if high:
        parts.append(
            "<div class='table-scroll'><table class='data'><thead><tr><th>Sport</th><th>Event</th><th>Selection</th>"
            "<th>Fair prob.</th><th>Our price</th><th>Band</th><th>Page</th></tr></thead><tbody>"
        )
        for r in sorted(high, key=lambda x: -x["fair_prob"]):
            parts.append(
                "<tr>"
                f"<td>{esc(r['sport_label'])}</td><td>{esc(r['event'])}</td>"
                f"<td>{esc(r['our_selection'])}{(' <span class=' + chr(39) + 'badge badge-independent' + chr(39) + '>independent</span>') if r.get('our_selection_override') else ''}</td>"
                f"<td>{round(r['fair_prob']*100)}%</td>"
                f"<td>{'+' if r['us_odds'] > 0 else ''}{r['us_odds']}</td>"
                f"<td>{'yes' if r['in_band'] else 'no'}</td>"
                f"<td><a href='sports/{r['sport_key']}.html'>open</a></td></tr>"
            )
        parts.append("</tbody></table></div>")
    else:
        parts.append("<p class='note'>No row cleared the 70% high-confidence threshold after shrinkage in this capture.</p>")
    parts.append(
        "<h2>Coverage warnings</h2><ul class='flags'>"
        "<li>Snooker and Greyhounds show zero OLBG tips at capture; official bodies confirm no snooker tournament today and a live but unextractable greyhound database.</li>"
        "<li>Golf (3), Darts (2) and Motor Racing (2) offer only sparse outright markets; Rugby League match play is in off-season with the 2026 World Cup visible on NRL.com but not yet listed on OLBG.</li>"
        "<li>Handball OLBG 'Money Line' markets are dominated by Tie selections; independent match-winner lines were originated and the anomaly is flagged per row.</li>"
        "<li>Third-party World Series odds articles conflict with MLB.com on venue order; MLB.com is treated as authoritative.</li>"
        "</ul>"
    )
    return base_page("Executive summary", "".join(parts))


def render_matches(sports: list[dict]) -> str:
    all_rows = []
    for s in sports:
        for r in s["rows"]:
            r = originate(r)
            r["sport_label"] = s["label"]
            all_rows.append(r)
    body = "<h1>All matches and originated lines</h1>"
    body += f"<p class='note'>{len(all_rows)} markets from the 15 requested sports. Tip counts and consensus are OLBG values at capture; fair probability and price are originated here.</p>"
    body += render_table(all_rows)
    return base_page("All matches", body)


def render_flagged(sports: list[dict]) -> str:
    parts = ["<h1>Flagged for review</h1>",
             "<p class='note'>Every limitation, conflict and unconfirmed value encountered during the 27 Oct 2026 collection is published here with its source link. Nothing on this list blocks publication, but each item should be reviewed before treating the related row as actionable.</p>"]
    for s in sports:
        rows = [originate(r) for r in s["rows"]]
        flagged_rows = [r for r in rows if r.get("flags") or r.get("our_line_blank") or r.get("official_scope") != "event"]
        if not flagged_rows and not s.get("empty_reason"):
            continue
        parts.append(f"<h2>{esc(s['label'])}</h2>")
        if s.get("empty_reason"):
            parts.append(f"<div class='callout'>{esc(s['empty_reason'])} <a href='{esc(s['olbg_hub'])}'>OLBG hub</a></div>")
        for r in flagged_rows:
            parts.append(
                "<article class='flag-card'>"
                f"<h3>{esc(r['event'])} <span class='muted'>{esc(r.get('market',''))}</span></h3>"
                f"{flags_html(r) if r.get('flags') else ''}"
                f"<p class='pick-sources'>{source_links(r)}</p></article>"
            )
    return base_page("Flagged for review", "".join(parts))


def render_methodology() -> str:
    body = """<h1>Methodology and markets</h1>
<h2>Collection</h2>
<p>Each OLBG sport hub was fetched directly on 27 Oct 2026 and every visible event recorded with its event URL, competition, OLBG time label, market, selection and tip count. Fixture identity was then cross-checked against the official source registered per sport (NBA.com, NHL.com, MLB.com, ATP Tour, ICC, LNR, EHF, EuroLeague, Formula1.com, PGA/LPGA, PDC, WST, GAA, GBGB and NRL.com). A row whose fixture only appears on OLBG is marked with an official-register (not event) link and a flag.</p>
<h2>Line origination</h2>
<p>OLBG displays a tip consensus but no price in the captured markup. We originate our own price from that consensus with a shrinkage rule that regresses small samples toward a coin flip, so a two-tip unanimous market is never treated as a certainty:</p>
<ul class='flags'>
<li>consensus c = tips_for / tips_total</li>
<li>sample weight w = n / (n + 4), where n is the total number of tips (a two-outcome prior of two tips each side)</li>
<li>consensus-only fair probability p = 0.5 + w &times; (c &minus; 0.5)</li>
<li>where an independent hosted market probability was recorded and linked on the row, that sourced probability is used as the fair probability and the OLBG consensus is retained as a confirmation signal</li>
<li>American price: p &ge; 0.5 gives &minus;100p/(1&minus;p), otherwise +100(1&minus;p)/p; decimal price = 1/p</li>
</ul>
<h2>Confidence and target band</h2>
<ul class='flags'>
<li><b>high</b>: fair probability at or above 70%</li>
<li><b>medium</b>: 55% to 69.9%</li>
<li><b>low</b>: below 55%</li>
<li>The requested focus band is American prices from &minus;250 to +10000. Rows shorter than &minus;250 keep their high label but are marked 'outside target band'.</li>
</ul>
<h2>Independent overrides</h2>
<p>Where OLBG's single-tip or small-sample selection contradicts official standings (for example Detroit 3-0 being tipped against while visiting winless New York, or 10th-placed Dax being favoured over 2nd-placed Provence), the originated line follows the official data instead. These rows carry an 'independent of OLBG consensus' badge and explain the disagreement in the written prediction.</p>
<h2>Markets investigated</h2>
<p>Money line / match winner markets are priced for every event with tips. Handicap, puck line, run line, point spread, frame/set betting, totals and outright tournament markets appear where OLBG lists them; totals markets with zero tips are deliberately left unpriced rather than guessed.</p>
<h2>Publication gate and injury information</h2>
<p>Every written prediction is at least 30 words, states the betting selection explicitly, and cites only facts traceable to the linked OLBG event page or official source. No injury, lineup or statistic is asserted without a source; where no official injury bulletin was reviewed, the row simply makes no injury claim instead of inventing one. Unconfirmable values stay blank and appear on the Flagged for Review page.</p>
<h2>Known structural limitations</h2>
<ul class='flags'>
<li>OLBG times are displayed exactly as labelled on the hub and were not timezone-normalised.</li>
<li>The CEV live match-centre index and the GBGB race database are JavaScript-rendered; register links are provided and the affected rows flagged.</li>
<li>Media odds pages used as secondary market inputs are dated and linked per row; conflicting World Series articles are flagged in favour of MLB.com.</li>
<li>This is a point-in-time snapshot. Tip counts and prices move; re-run the collection before staking.</li>
</ul>"""
    return base_page("Methodology", body)


def render_sources(ledger_path: Path) -> str:
    ledger = json.loads(ledger_path.read_text())["source_ledger"]
    body = ["<h1>Source register</h1>",
            "<p class='note'>Official sources are league, tour or governing-body destinations. OLBG is the listing and consensus source and is not treated as an official sports body.</p>",
            "<div class='table-scroll'><table class='data'><thead><tr><th>Source</th><th>Role</th><th>Type</th><th>Link</th></tr></thead><tbody>"]
    for s in ledger:
        body.append(f"<tr><td>{esc(s['name'])}</td><td>{esc(s['role'])}</td><td>{esc(s['type'])}</td>"
                    f"<td><a href='{esc(s['url'])}'>{esc(s['url'])}</a></td></tr>")
    body.append("</tbody></table></div>")
    return base_page("Sources", "".join(body))


def main() -> None:
    sports = load_sports()
    assert len(sports) == 15, f"expected 15 sports, got {len(sports)}"
    (OUT / "sports").mkdir(parents=True, exist_ok=True)
    (OUT / "assets").mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(render_index(sports))
    (OUT / "matches.html").write_text(render_matches(sports))
    (OUT / "flagged.html").write_text(render_flagged(sports))
    (OUT / "methodology.html").write_text(render_methodology())
    (OUT / "sources.html").write_text(render_sources(DATA / "board-data-5.json"))
    for s in sports:
        (OUT / "sports" / f"{s['key']}.html").write_text(render_sport_page(s))
    rows = sum(len(s["rows"]) for s in sports)
    picks = sum(1 for s in sports for r in s["rows"] if r.get("prediction"))
    print(f"board built: 15 sports, {rows} market rows, {picks} written predictions -> {OUT}")


if __name__ == "__main__":
    main()
