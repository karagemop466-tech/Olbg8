# OLBG desk — lines, picks and sources

A static dashboard for the fifteen OLBG sports in scope. Every page is generated from committed JSON by
`scripts/build_site.py` and gated by `scripts/check_site.py`, so the published site can be rebuilt and audited
line by line.

## Companion 2026-10-27 picks board

The **[Picks Board](board/index.html)** is the current working dashboard, built from a live re-collection of OLBG on 27 Oct 2026:

- Executive summary with all high-confidence picks, 15 sport subpages and a full 119-row market table with originated lines ([board/matches.html](board/matches.html)).
- 48 unique written predictions (30+ words each, explicit selections, no robotic templates), 9 high-confidence lines, every row linked to its OLBG event page and an official source.
- Deterministic line origination from OLBG consensus with Bayesian shrinkage and independently sourced market prices; see [board/methodology.html](board/methodology.html).
- Every gap, conflict and unconfirmed value is published on [board/flagged.html](board/flagged.html).
- Rebuild and validate with `python3 scripts/test_board.py` (also enforced in GitHub Actions).

The legacy source-first desk below, the research-desk and evidence-lab directories are retained as audit history.
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

Captured **2026-10-27 06:05 UTC**: 115 OLBG listings across 15 sports, **24 published picks** (10 high, 12 medium,
2 low confidence), every one inside the −250 to +10000 American window, and **19 flagged items**.

Seven sports carry picks: Basketball (9), Rugby Union (6), Handball (5), Volleyball (1), Baseball (1), Ice Hockey (1)
and Tennis (1). The other eight are priced on `pricing.html` but carry no pick, because the official table needed to
confirm a rate input was not reachable; each one is named, with the exact page that unblocks it, on `flagged.html`.
Nothing is filled in by inference.

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
python3 price-engine/add_picks.py   # rebuilds the handball, rugby union and tennis picks from price-engine/ratings.json
python3 scripts/build_site.py       # writes the 22 HTML pages from data/*.json
python3 scripts/check_site.py       # 645 assertions: rules, arithmetic, sources, links
python3 -m http.server 8000 --bind 0.0.0.0
```

`add_picks.py` is deterministic: it reads the captured ratings, prices each fixture, and writes the same twelve
picks into `data/desk-picks.json` on every run, de-duplicated on sport, event, market and selection.

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
| `price-engine/*` | Raw rate inputs, first-generation engine and the published add-on engine described below |

## The price engine

`price-engine/` holds the raw inputs and the origination code behind the twelve handball, rugby union and tennis
picks that were added to the desk on 27 October.

| File | Contents |
|---|---|
| `price-engine/ratings.json` | Captured rate inputs: EHF Champions League group tables, the LNR PRO D2 table, the WTA ranking points for the four ranked players in the tennis capture |
| `price-engine/olbg-listings.json` | The original 111-row listing capture, kept as the raw record |
| `price-engine/matches.json` | Every listing scored and priced, including the ones that fell outside the window |
| `price-engine/predictions.json` | The prose drafted for the twenty-two priced rows before the desk rewrite |
| `price-engine/originate.py` | The first-generation engine: normal-approximation margins per sport |
| `price-engine/add_picks.py` | The published engine: Poisson grid for handball, normal margin for rugby, ranking link for tennis, with the window and band guards applied |

Handball uses the attack-versus-defence product and Poisson grid that `pricing.html` documents for the sport; rugby
uses the documented normal margin with a 13.5-point deviation and a draw band; tennis uses the ranking-point gap in
log space. Each output carries a fact per figure with a link to the official table it came from.

The earlier capture tooling (`data/dashboard.json`, `data/olbg-capture.json`, `scripts/build_dashboard.py`,
`scripts/test_site.py`) is retained unchanged as the 26 October record, and `research-desk/` plus `evidence-lab/`
remain archived supplements.

## Limits

This is a static snapshot, not a live feed. OLBG shows no prices to a logged-out fetch, so no OLBG price is quoted
anywhere; every price is originated by this desk. Kick-off times are converted from OLBG's relative
Today/Tomorrow labels at UTC+4 and the original label is printed next to each row. Betting involves risk:
independent research, not advice, not a guarantee. 18+.
