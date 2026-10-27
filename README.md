# OLBG desk — lines, picks and sources

A static dashboard for the fifteen OLBG sports in scope. Every page is generated from committed JSON by
`scripts/build_site.py` and gated by `scripts/check_site.py`, so the published site can be rebuilt and audited
line by line.

**Live site:** <https://karagemop466-tech.github.io/Olbg8/>

## What is on the site

| Page | What it holds |
|---|---|
| `index.html` | Executive summary, the three strongest picks as cards, the highest-confidence picks table, and a coverage table for all 15 sports |
| `picks.html` | Every published prediction: the bet and our price first, then the written analysis, the evidence bullets with a link per fact, and the pricing method |
| `matches.html` | All 115 captured OLBG listings, one table per sport, each row linked to its live OLBG event page, with our line where one exists |
| `pricing.html` | How each of the 15 sports is priced, market by market, with the margin applied and a worked example |
| `sources.html` | Source register: OLBG for listings, official bodies for fixtures and form |
| `flagged.html` | Everything that could not be closed against an official source, with links |
| `methodology.html` | How OLBG is reverse-engineered, the publication gate, the price window and the known limits |
| `sports/<sport>.html` | One page per sport: its picks at the top, then its OLBG listing table, then how the sport is priced |

## Snapshot

Captured **2026-10-27 06:05 UTC**: 115 OLBG listings across 15 sports, **9 published picks** (2 high, 5 medium,
2 low confidence), all inside the −250 to +10000 American window, and **16 flagged items**.

Four sports carry picks: Basketball (6), Volleyball (1), Baseball (1) and Ice Hockey (1). The other eleven have no
pick because the official source needed to confirm the fixture or the form was not reachable in this session. Each
one is named, with the exact page that unblocks it, on `flagged.html` — nothing is filled in by inference.

## How a pick is built

1. **Capture** the OLBG hub row: event, market, most-tipped selection, tip count.
2. **Confirm** the fixture and the form facts on an official page (league table, standings feed, schedule API).
3. **Price** it with that sport's method and margin, then band it by the implied probability of the published line.
4. **Write** at least 30 words naming the bet, the form, the recent record and the match-specific numbers, with a
   source link per fact.
5. **Gate** it: `scripts/check_site.py` refuses a short prediction, a line outside the window, a mismatched
   confidence band, a missing source, an unknown event id, or a broken internal link.

## Local build

```bash
python3 scripts/build_site.py     # writes the 22 HTML pages from data/*.json
python3 scripts/check_site.py     # 399 assertions: rules, arithmetic, sources, links
python3 -m http.server 8000 --bind 0.0.0.0
```

## Data files

| File | Contents |
|---|---|
| `data/desk-sports.json` | The 15 sports, OLBG hub URLs, sport ids, official source links |
| `data/desk-inventory.json` | Captured OLBG listings with the original OLBG day/time label beside the converted UTC time |
| `data/desk-picks.json` | Published picks: line, decimal, implied %, confidence, analysis, facts, sources, pricing note |
| `data/desk-pricing.json` | Market-by-market origination method per sport, margins, and the standing guards |
| `data/desk-flagged.json` | Review items with source links |
| `data/desk-sources.json` | Source register rendered on `sources.html` |
| `data/desk-methodology.json` | Methodology sections rendered on `methodology.html` |

The earlier capture tooling (`data/dashboard.json`, `data/olbg-capture.json`, `scripts/build_dashboard.py`,
`scripts/test_site.py`) is retained unchanged as the 26 October record, and `research-desk/` plus `evidence-lab/`
remain archived supplements.

## Limits

This is a static snapshot, not a live feed. OLBG shows no prices to a logged-out fetch, so no OLBG price is quoted
anywhere; every price is originated by this desk. Kick-off times are converted from OLBG's relative
Today/Tomorrow labels at UTC+4 and the original label is printed next to each row. Betting involves risk:
independent research, not advice, not a guarantee. 18+.
