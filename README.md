# OLBG Research Desk — 15-sport market monitor

A static research dashboard that reverse-engineers how OLBG publishes its markets, prices **every** listed
outcome for the 15 requested sports with our own fair line, and publishes written predictions for the
strongest supported selections.

**Live site:** <https://karagemop466-tech.github.io/Olbg8/>

## Covered sports (OLBG category → sport id)

| Sport | OLBG page |
|---|---|
| Golf | `/betting-tips/Golf/5` |
| Volleyball | `/betting-tips/Volleyball/21` |
| Rugby Union | `/betting-tips/Rugby_Union/9` |
| Cricket | `/betting-tips/Cricket/7` |
| Snooker | `/betting-tips/Snooker/8` |
| Darts | `/betting-tips/Darts/15` |
| Baseball | `/betting-tips/Baseball/12` |
| Gaelic Sports | `/betting-tips/Gaelic_Football/25` + `/betting-tips/Hurling/26` |
| Greyhounds | `/betting-tips/Greyhounds/28` |
| Tennis | `/betting-tips/Tennis/3` |
| Motor Racing | `/betting-tips/Motor_Racing/14` |
| Handball | `/betting-tips/Handball/20` |
| Ice Hockey | `/betting-tips/Ice_Hockey/13` |
| Basketball | `/betting-tips/Basketball/4` |
| Rugby League | `/betting-tips/Rugby_League/10` |

OLBG has no standalone "Gaelic Sports" category: it is Gaelic Football (25) plus Hurling (26), and this
project publishes them as one sport.

## What the site contains

* `index.html` — executive summary, highest-confidence picks for today/tomorrow, upcoming picks, coverage by sport.
* `sports/<sport>.html` — 15 sport desks: the five published picks with full predictions, then every priced market.
* `markets.html` — all 1,826 priced outcomes in one filterable table.
* `methodology.html` — the pricing arithmetic (de-vig, consensus blend, margin, tiers, selection rules).
* `sources.html` — every OLBG category page and official feed with capture status.
* `review.html` — Flagged for Review: unconfirmed fields, missing inventory, blocked endpoints, judgement calls.

## Data pipeline

```
.github/workflows/fetch-raw.yml   # GitHub runner: captures OLBG pages + official feeds into data/raw/
scripts/parse_olbg.py             # data/raw/*.html           -> data/fixtures.json
scripts/parse_events.py           # data/raw/events/*.html    -> data/markets.json  (346 markets, 1,833 outcomes)
scripts/extract_official.py       # official feeds            -> data/official_facts.json
scripts/pricing.py                # data/markets.json         -> data/lines.json   (every outcome priced)
scripts/select_picks.py           # data/lines.json           -> data/picks.json
scripts/build_site.py             # -> index.html, sports/*.html, markets/methodology/sources/review.html
scripts/check_site.py             # link, pick and data integrity gate
```

The event pages embed a JS payload (`event:{slug:…,markets:[…]}`) which `parse_events.py` reads with a
small literal parser. That is where the full market list and both-side prices come from — the listing page
alone only shows the most-tipped selection.

## How a line is made

1. `p_market = (1/decimal) / Σ(1/decimal)` — proportional de-vig over the full outcome set.
2. `p_tip = (t + 6·p_market) / (N + 6)` — tipster share shrunk toward the market.
3. `p_fair = (1−w)·p_market + w·p_tip`, `w = min(0.35, N/(N+12))`.
4. Fair American price from `p_fair`; our offered price adds a 3% margin.
5. Confidence: High ≥ 70%, Medium 55–70%, Low < 55%; only prices from −250 to +10,000 are eligible.

## Verification status

Fixture, market, price and tip counts are read verbatim from the OLBG event page linked on every row.
Official-source facts (NHL standings, MLB standings, F1 classification) are linked separately. Everything
that could not be confirmed — team news, injuries, lineups for 12 of the 15 sports — is left blank and
listed on `review.html`. Nothing is inferred.

## Local build

```bash
python3 scripts/parse_olbg.py && python3 scripts/parse_events.py
python3 scripts/extract_official.py && python3 scripts/pricing.py
python3 scripts/select_picks.py && python3 scripts/build_site.py
python3 scripts/check_site.py      # must print "errors: 0"
python3 -m http.server 8000        # serve the repo root
```
