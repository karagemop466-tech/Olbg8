#!/usr/bin/env python3
"""Render a pinned, non-actionable review ledger. Does not modify root outputs."""
from __future__ import annotations

import argparse
from collections import Counter
from html import escape
import json
from pathlib import Path

from gate import assess_all, parse_utc, valid_url

HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def safe(value):
    return escape(str(value if value is not None else ""), quote=True)


def date_label(value):
    dt = parse_utc(value)
    if dt is None:
        raise ValueError(f"invalid timestamp: {value!r}")
    return dt.strftime("%d %b %Y, %H:%M:%S UTC")


def link(url, title):
    if not valid_url(url):
        raise ValueError(f"unsafe external link: {url!r}")
    return f'<a href="{safe(url)}" target="_blank" rel="noopener noreferrer">{safe(title)}</a>'


def adapt_legacy(row, catalog):
    """Adapt only fields actually recorded; missing structured evidence stays empty.

    The manually checked event crosswalk is shown separately in the ledger.
    The original payload lacks per-source observation timestamps, a structured
    quote and independent calibration; this adapter does not invent any of them
    or promote an unscoped source link into a reviewed evidence record.
    """
    sport = row.get("sport_key") or ""
    eid = str(row.get("event_id") or "")
    refs, claims = [], {}
    fair = row.get("fair_american")
    if isinstance(fair, float) and fair.is_integer():
        fair = int(fair)
    return {
        "id": row.get("pick_id"), "sport": sport,
        "event": {"id": eid, "name": row.get("event"), "start_utc": None},
        "market": {"name": row.get("market"), "selection": row.get("selection")},
        "sources": refs, "claim_sources": claims, "material_availability_reviewed": False,
        "analysis": row.get("note"),
        "pricing": {"win_probability": row.get("our_prob"), "push_probability": None,
                    "fair_american": fair, "independent_from_tip_shares": False,
                    "method": "Smoothed OLBG tip share in the pinned originator.",
                    "input_source_ids": [], "calibration": {}, "confidence": str(row.get("confidence") or "").lower()},
    }


def document():
    snapshot, catalog, findings = load("snapshot.json"), load("catalog.json"), load("findings.json")
    if snapshot["baseline_commit"] != findings["baseline"]:
        raise ValueError("finding and snapshot commits do not match")
    at = parse_utc(catalog["reviewed_utc"])
    if at is None:
        raise ValueError("review time must be zoned")
    rows = snapshot["picks"]
    results = assess_all([adapt_legacy(row, catalog) for row in rows], at)
    return snapshot, catalog, findings, results


def render():
    snapshot, catalog, findings, results = document()
    rows = snapshot["picks"]
    event_sources = catalog["event_sources"]
    directories = catalog["directories"]
    by_id = {item["id"]: item for item in results}
    matched = sum(f'{row["sport_key"]}:{row["event_id"]}' in event_sources for row in rows)
    held = sum(result["status"] == "withhold" for result in results)
    reasons = Counter(code for result in results for code in result["reasons"])
    events = len({(row["sport_key"], row["event_id"]) for row in rows})

    item_rows = []
    for item in findings["items"]:
        links = "<br>".join(link(src["url"], src["label"]) for src in item["links"])
        item_rows.append(
            f'<tr id="{safe(item["id"])}"><td><span class="sev {safe(item["severity"])}">{safe(item["severity"])}</span>'
            f'<br><span class="muted">{safe(item["id"])} · {safe(", ".join(item["records"]))}'
            f'{(" · revision " + safe(item["revision"][:7])) if item.get("revision") else ""}</span></td>'
            f'<td><strong>{safe(item["title"])}</strong><p>{safe(item["finding"])}</p>'
            f'<p class="action"><strong>Review action:</strong> {safe(item["action"])}</p></td>'
            f'<td class="sources">{links}</td></tr>'
        )

    sports = sorted({(r["sport_key"], r["sport"]) for r in rows}, key=lambda p: p[1])
    options = '<option value="">All sports</option>' + ''.join(
        f'<option value="{safe(key)}">{safe(label)}</option>' for key, label in sports)
    ledger_rows = []
    for row in rows:
        eid = str(row["event_id"])
        entry = event_sources.get(f'{row["sport_key"]}:{eid}')
        if entry:
            official = link(entry["url"], entry["label"]) + f'<small>Event identity only. {safe(entry["supports"])}</small>'
        else:
            # A directory is explicitly NOT represented as a fixture match.
            label, url = directories[row["sport_key"]]
            if row["sport_key"] == "ice_hockey" and eid == "200081":
                label, url = "Liiga (reference only)", "https://www.liiga.fi/"
            if row["sport_key"] == "ice_hockey" and eid == "200082":
                label, url = "SHL (reference only)", "https://www.shl.se/"
            official = link(url, label) + '<small>Reference only; event identity not established in this audit.</small>'
        result = by_id[row["pick_id"]]
        if result["status"] != "withhold":
            raise ValueError(f'{row["pick_id"]}: legacy record unexpectedly passed')
        searchable = " ".join(str(row.get(k) or "") for k in ("sport", "event", "market", "selection", "pick_id"))
        ledger_rows.append(
            f'<tr data-sport="{safe(row["sport_key"])}" data-search="{safe(searchable.casefold())}">'
            f'<td><span class="mono">{safe(row["pick_id"])}</span><br>{safe(row["sport"])}</td>'
            f'<td><strong>{safe(row["event"])}</strong><br><small>{link(row["olbg_url"], "OLBG event")}</small></td>'
            f'<td>{safe(row["market"])}<br><strong>{safe(row["selection"])}</strong><small>Historical label; not a recommendation.</small></td>'
            f'<td>{official}</td><td><span class="sev high">Withheld</span><small>Independent calibration and an attached, time-stamped offer are not recorded in the inspected pick payload.</small></td></tr>'
        )
    base = snapshot["baseline_commit"]
    hist = link(snapshot["source_url"], "pinned source data")
    origin = link(snapshot["originator_url"], "pinned origination code")
    fcount = len(findings["items"])
    template = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="A pinned source and settlement audit of a historical OLBG prediction snapshot.">
<title>Source review · OLBG research desk</title>
<link rel="stylesheet" href="styles.css"><script src="filter.js" defer></script>
</head>
<body><header><div class="bar"><a class="brand" href="../index.html"><span class="mark">O</span><span>OLBG <b>source review</b><small>Evidence &amp; settlement audit</small></span></a><nav aria-label="Review navigation"><a href="../index.html">Main desk</a><a href="#findings">Findings</a><a href="#ledger">Record ledger</a><a href="method.html">Gate methodology</a></nav></div></header>
<main><div class="eyebrow">AUDIT SNAPSHOT <span>●</span> 27 OCT 2026</div>
<h1>What can we actually support?</h1>
<p class="lead">A source-linked review of an earlier published prediction snapshot. This page is a review queue—not a live feed and not a list of current bets.</p>
<div class="alert"><strong>Do not treat historical labels as current picks.</strong> The reviewed capture was taken at <strong>__CAPTURE__</strong>; event-source review was completed by <strong>__REVIEW__</strong>. Fixtures, offers, prices and lineups can change. The root site may have changed since this snapshot.</div>
<section class="metrics" aria-label="Audit summary">
<div class="metric"><span>Historical records</span><strong>__ROWS__</strong><small>__EVENTS__ distinct events</small></div>
<div class="metric"><span>Event identity references</span><strong>__MATCHED__</strong><small>record-level matches, not full validation</small></div>
<div class="metric"><span>Passed review gate</span><strong>__PASS__</strong><small>__HELD__ withheld from this audit</small></div>
<div class="metric"><span>Review findings</span><strong>__FINDINGS__</strong><small>linked for manual review</small></div>
</section>
<section class="intro"><div><h2>Executive summary</h2><p>Several factual statements in the pinned source conflict with a league or governing-body source, including the Namibia–Ireland series score and Lilli Tagger's age. The historical line method transforms tip-share counts into a probability without an identified out-of-sample validation; a source link or a small vote does not establish a reliable chance of winning.</p><p>None of these historical records is promoted by this review. The strict check also finds no attached, timestamped OLBG offer and no documented out-of-sample calibration in the inspected pick payload. This does <em>not</em> prove every underlying assertion wrong, and it does not assert that no offer existed elsewhere.</p></div><div class="side"><strong>Scope of this review</strong><p>Baseline <code>__BASE__</code> · __HIST__ · __ORIGIN__</p><p>Event identity checks cover only the named event. Where we found only a sport directory, the ledger says so. Some individual claims remain unchecked.</p><a class="button" href="#findings">See the findings ↓</a></div></section>
<section id="findings"><div class="sectionhead"><div><span class="eyebrow">01 / PRIORITY</span><h2>Flagged for review</h2></div><p>Findings A01–A14 cover the pinned root snapshot; A15–A18 cover a separate <a href="https://github.com/karagemop466-tech/Olbg8/pull/37">PR #37</a> snapshot reviewed at 06:42 UTC. Both may have changed since review.</p></div><div class="tablewrap"><table id="findings-table"><thead><tr><th scope="col">Priority / reference</th><th scope="col">Finding &amp; action</th><th scope="col">Sources</th></tr></thead><tbody>__FINDING_ROWS__</tbody></table></div></section>
<section id="ledger"><div class="sectionhead"><div><span class="eyebrow">02 / RECORDS</span><h2>Historical record ledger</h2></div><p>Search and filter the __ROWS__ archived records. An official directory is a reference, not proof of a specific event; every row retains both an OLBG link and an official or primary sporting-body link.</p></div><div class="filters"><label>Search <input id="query" type="search" placeholder="Team, event, market or ID" autocomplete="off"></label><label>Sport <select id="sport">__OPTIONS__</select></label><span id="result-count" aria-live="polite">__ROWS__ records</span></div><div class="tablewrap"><table id="ledger-table"><thead><tr><th scope="col">Reference / sport</th><th scope="col">Event</th><th scope="col">Archived selection</th><th scope="col">Official source scope</th><th scope="col">Review status</th></tr></thead><tbody>__LEDGER_ROWS__</tbody></table></div></section>
<section class="methodbox"><h2>Why the gate withheld this snapshot</h2><div class="reason-grid"><p><strong>__NOQUOTE__ / __ROWS__</strong><br>no time-stamped offer was attached to the inspected record</p><p><strong>__NOCAL__ / __ROWS__</strong><br>no out-of-sample calibration was recorded in the inspected record</p><p><strong>__MISSING__ / __ROWS__</strong><br>do not yet have an event-specific official crosswalk in this review</p></div><p>These counts describe the data available to this audit, not proof that sources do not exist. The optional gate checks metadata and arithmetic but cannot determine whether source excerpts are true; a pass is not an endorsement. <a href="method.html">Read methodology and limitations →</a></p></section>
</main><footer><div>Independent research · Snapshot __BASE_SHORT__ · 18+ · No wager is guaranteed.</div><div><a href="../index.html">Back to main desk</a> · <a href="../current/review.html">Current-source review</a></div></footer></body></html>'''
    replacements = {
        "__CAPTURE__": safe(date_label(snapshot["olbg_capture_utc"])), "__REVIEW__": safe(date_label(catalog["reviewed_utc"])),
        "__ROWS__": str(len(rows)), "__EVENTS__": str(events), "__MATCHED__": str(matched),
        "__PASS__": str(len(rows) - held), "__HELD__": str(held), "__FINDINGS__": str(fcount),
        "__BASE__": safe(base), "__BASE_SHORT__": safe(base[:7]), "__HIST__": hist, "__ORIGIN__": origin,
        "__FINDING_ROWS__": "\n".join(item_rows), "__OPTIONS__": options,
        "__LEDGER_ROWS__": "\n".join(ledger_rows),
        "__NOQUOTE__": str(reasons["offer_not_confirmed"]), "__NOCAL__": str(reasons["missing_out_of_sample_calibration"]),
        "__MISSING__": str(len(rows) - matched),
    }
    # Replace longer markers first so __BASE__ does not alter __BASE_SHORT__.
    for marker in sorted(replacements, key=len, reverse=True):
        template = template.replace(marker, replacements[marker])
    return template + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if checked-in report differs from source data")
    args = parser.parse_args()
    text = render()
    dest = HERE / "index.html"
    if args.check:
        if not dest.exists() or dest.read_text(encoding="utf-8") != text:
            raise SystemExit("report differs; run python3 audit-1c2e36bf/build_report.py")
        print("Pinned report matches its source files.")
    else:
        dest.write_text(text, encoding="utf-8")
        print(f"Built {dest.relative_to(HERE.parent)} from pinned snapshot.")


if __name__ == "__main__":
    main()
