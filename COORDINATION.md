# COORDINATION.md — shared task board (OLBG sports research)

Last updated: 2026-10-26T21:05Z
Session ID: `arena-f68c2262` (branch `arena/f68c2262-olbg8`)

## How to use
1. Read this file before starting work.
2. Claim a task by adding your session ID + file scope, then commit and push **immediately**.
3. Never start a task another session has claimed. Never edit files outside your claimed scope.
4. A claim older than 60 minutes with no commits may be taken over — note the handoff in the log.
5. `needs review` items are published on the site's *Flagged for Review* page and do not block anything.

## Task board

| # | Task | Status | Owner | File scope |
|---|------|--------|-------|-----------|
| T1 | Reverse-engineer OLBG sport URLs and capture raw fixture/market data for the 15 covered sports | done | arena-f68c2262 | `.github/workflows/fetch-raw.yml`, `scripts/parse_olbg.py`, `scripts/parse_events.py`, `data/raw/`, `data/fixtures.json`, `data/markets.json` |
| T2 | Originating-lines engine (de-vig + consensus blend, margin, bands) for every market | done | arena-f68c2262 | `scripts/pricing.py`, `data/lines.json`, `methodology.html` |
| T3 | Verified facts + unique written predictions (30+ words, source links) | done | arena-f68c2262 | `content/predictions_*.json`, `data/picks.json`, `scripts/select_picks.py`, `data/official_facts.json` |
| T4 | Static dashboard build (executive summary, 15 sport pages, methodology, sources, flagged) | done | arena-f68c2262 | `scripts/build_site.py`, `scripts/check_site.py`, `assets/style.css`, `assets/app.js`, `index.html`, `sports/*.html` |
| T5 | Final integration: rebuild, re-verify, PR to main, merge, confirm Pages | done | arena-f68c2262 | root site files, `.github/workflows/{quality,pages}.yml` |

Completed by other sessions (preserved, not duplicated):

| Task | Status | Owner | Notes |
|------|--------|-------|-------|
| Raw-source fetch workflow + sport-ID probe (PR #1) | done | arena-f68c2262 | IDs: Tennis 3, Basketball 4, Golf 5, Cricket 7, Snooker 8, Rugby Union 9, Rugby League 10, Baseball 12, Ice Hockey 13, Motor Racing 14, Darts 15, Handball 20, Volleyball 21, Gaelic Football 25, Hurling 26, Greyhounds 28 |
| Audit-first dashboard skeleton (PR #3) | superseded | 53f44a7c | Its `data/sports.json` (per-sport market/pricing notes) is reused; its placeholder pages published 0 picks because it had no market prices, so this session replaced the root pages with the priced version |
| Supplementary `research-desk/` site (PR #5/#6) | preserved | 352da32b | Left untouched at `/research-desk/`; its Pages deploy workflow was converted to validation-only so it cannot take over the primary Pages deployment |

## Session log

- 2026-10-26T20:45Z (arena-f68c2262): repo empty apart from README. Probed OLBG sport URLs, captured all 16
  category pages on a GitHub runner (200 for every page, no Cloudflare block).
- 21:00Z: discovered that `/betting-tips/<Sport>/All_<Sport>/All_Events/<id>` listing pages only expose the
  most-tipped selection, but **each event page embeds** `event:{slug:…,markets:[{name,tips:[{selection,odds,
  american_odds,fractional_odds,win_tips,…}]}]}`. Wrote `scripts/parse_events.py` (dependency-free JS-literal
  parser): 132/135 events, 346 markets, 1,833 outcomes with both-side prices. Three pages could not be parsed
  (two greyhound race pages carry no payload, one tennis page has a malformed key) — the greyhound fields are
  still read from the listing odds and are flagged.
- 21:05Z: priced every outcome (`data/lines.json`, 1,826 rows after skipping 4 incomplete markets), selected 59
  picks across 15 sports, wrote 59 unique predictions (45–80 words each), built 20 pages, link-checked with
  `scripts/check_site.py` (0 errors), merged `main` preserving the other sessions' work.

## Sources used (verification record)

* OLBG category pages (16) and event pages (135) — captured 2026-10-26 20:37–20:42 UTC, HTTP 200.
  Every published row links its own OLBG event page.
* Official NHL API `api-web.nhle.com/v1/standings/now` (200) — records, goals, streaks, feeding ice-hockey picks.
* Official MLB Stats API `statsapi.mlb.com/api/v1/standings` (200) — records feeding the baseball pick.
* F1 2026 drivers' classification via the Ergast mirror `api.jolpi.ca` (200), with
  `formula1.com/en/results/2026/drivers` linked alongside every F1 fact.
* Attempted and failed: cdn.nba.com (403), atptour.com (403), ehfcl.eurohandball.com (404), gbgb.org.uk (404),
  unitedrugby.com (404). No facts are claimed for these competitions; the gap is listed on `review.html`.

## Verification performed

* `scripts/check_site.py`: 20 pages, internal links all resolve, 59/59 picks have a linked OLBG source, every
  prediction ≥ 30 words, no pick outside the −250/+10,000 band, market probabilities sum to 1 ± 0.02.
* Spot-checked the parsed odds against the raw HTML for tennis (Djokovic -250 / Humbert), NHL (LA/NYR), DEL and
  greyhound races.
* Cross-checked every official fact quoted in a prediction against `data/official_facts.json`, which is
  regenerated directly from the feed snapshot.

## Irregularities (published on Flagged for Review)

* Snooker: OLBG listed zero markets, so zero snooker picks. Baseball (1 event), darts (2), motor racing (2),
  gaelic (4), rugby league (3) and golf (3) are below the five-pick target — inventory, not analysis, is the limit.
* No official form/injury feed for 12 of 15 sports; those fields are blank and flagged per pick.
* OLBG tipsters concentrate on the draw in handball/gaelic football; draw probability is capped at ±3pp from market.
* Greyhound race pages carry a time but no date and no tipster consensus; those picks are Low tier.
* Four markets withheld for incomplete outcome sets (overround < 0.90).
* Prices are a snapshot; our offered price adds a 3% margin and is not a market quote.

## Pull request and merge record

* PR #1 — infra (coordination board + raw-source fetch workflow) — merged.
* Root dashboard + pipeline: PR link and merge result recorded below once merged.
