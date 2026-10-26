# COORDINATION.md — shared task board (OLBG sports research)

Last updated: 2026-10-26 (UTC)

## How to use
1. Read this file before starting work.
2. Claim a task by adding your session ID + file scope, then commit and push **immediately**.
3. Never start a task another session has claimed. Never edit files outside your claimed scope.
4. A claim older than 60 minutes with no commits may be taken over — note the handoff in the log below.
5. `needs review` items are published on the site's *Flagged for Review* page and do not block anything.

## Task board

| # | Task | Status | Owner | File scope |
|---|------|--------|-------|-----------|
| T1 | Reverse-engineer OLBG sport URLs + capture raw fixture/tip data for the 15 covered sports | in progress | arena-f68c2262 | `scripts/fetch_*`, `data/raw/`, `data/fixtures.json` |
| T2 | Originating-lines model (de-vig + consensus pricing, markets: ML/handicap/totals) | in progress | arena-f68c2262 | `scripts/pricing.py`, `content/pricing_method.md` |
| T3 | Verified facts + 5 unique written predictions per sport (30+ words, source links) | in progress | arena-f68c2262 | `content/predictions/*.json` |
| T4 | Static site build (landing page, 15 sport subpages, methodology, sources, flagged) | in progress | arena-f68c2262 | `scripts/build_site.py`, `assets/`, `index.html`, `sports/*.html` |
| T5 | Final integration: re-verify rows, link check, PR to main, merge, confirm Pages | unclaimed | — | `main` merge |
| T6 | Initial source-first dashboard and transparent snapshot status; reconcile with T4 before integration | needs review | `673f9685-olbg8` | `README.md`, `app.js`, `styles.css`, `data/`, `flagged-for-review.html`, `.github/workflows/pages.yml`, `scripts/check_site.py`; overlapping branch outputs `index.html` and `sports/*.html` explicitly require T4/integration review |

## Session log

- 2026-10-26 (arena-f68c2262): Repo was empty (README only). Claimed T1–T4. Found OLBG sport IDs by probing: Tennis 3, Basketball 4, Golf 5, Cricket 7, Snooker 8, Rugby Union 9, Rugby League 10, Baseball 12, Ice Hockey 13, Motor Racing 14, Darts 15, Handball 20, Volleyball 21, Gaelic Football 25, Hurling 26, Greyhounds 28. Note: OLBG has no standalone "Gaelic Sports" sport slug — Gaelic Sports = Gaelic Football (25) + Hurling (26).
- 2026-10-26 (`673f9685-olbg8`): At the start of this checkout the coordination file was absent locally, so I created a board and claimed a static dashboard task; I later discovered the board committed to `origin/main` by `arena-f68c2262` after my initial inspection. My branch already contains a dashboard implementation and PR #2 (<https://github.com/karagemop466-tech/Olbg8/pull/2>). Its `index.html` and `sports/*.html` overlap T4's claimed paths. This overlap is disclosed for T4/final-integration review; I will make no further edits to those paths unless their scope is released. PR #2 is not ready to merge while T1–T4 remain in progress.
- Source reconnaissance: OLBG's current betting-tips page at <https://www.olbg.com/betting-tips> was read on 2026-10-26 UTC. It lists tipster selections and community counts; it does not establish bookmaker odds, official competition statistics, confirmed injury status, or complete event coverage.
- Dashboard snapshot: 12 event-name sightings visible in the OLBG landing-page content were recorded in `data/events.json`, with OLBG event-page links and relative Today/Tomorrow labels. Snapshot is explicitly non-exhaustive; event details are not independently verified. No selections, odds, lines, confidence ratings, player/team facts, injuries, or predictions are populated.
- Source-map caveat: sport directory links to PGA TOUR, Volleyball World, World Rugby, ICC, WST, PDC, MLB, GAA, GBGB, ATP, FIA, EHF, NHL, NBA and NRL schedule/competition starting points. These are not recorded as event-level checks; external source content and URLs were not checked line by line in this task.
- Verification: `python3 scripts/check_site.py` passed (15 sport pages, 12 sourced OLBG sightings, static local links); both JSON files parsed; `node --check app.js`, `git diff --check`, and local HTTP smoke checks passed. Structural checks do not verify live external links or sporting facts.
- Merge coordination: PR #2 merge was attempted per the request, but GitHub reported it cannot be cleanly merged because `origin/main` advanced with PR #1 (`98ddabd`, session `arena-f68c2262`) and introduced a `COORDINATION.md` add/add conflict. The branch is being rebased onto that mainline; preserve both task boards and all work. Do not force-merge or bypass the active T1–T4 work.
- Outstanding: complete official event/market checks, all sports' upcoming-event data, current stats/injuries, originated lines, original 30+ word predictions, external link checking, final integration, and Pages deployment. These omissions are shown on the dashboard's Flagged for Review page, not passed off as verified.
