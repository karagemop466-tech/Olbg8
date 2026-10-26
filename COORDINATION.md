# COORDINATION.md — shared task board (OLBG sports research)

Last updated: 2026-10-26T20:45Z
Session ID: `arena-f68c2262` (branch `arena/f68c2262-olbg8`)

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

## Session log

- 2026-10-26T20:45Z (arena-f68c2262): Repo was empty (README only). Claimed T1–T4. Found OLBG sport IDs by
  probing: Tennis 3, Basketball 4, Golf 5, Cricket 7, Snooker 8, Rugby Union 9, Rugby League 10,
  Baseball 12, Ice Hockey 13, Motor Racing 14, Darts 15, Handball 20, Volleyball 21,
  Gaelic Football 25, Hurling 26, Greyhounds 28. Note: OLBG has **no standalone "Gaelic Sports"**
  sport slug — Gaelic Sports = Gaelic Football (25) + Hurling (26).
