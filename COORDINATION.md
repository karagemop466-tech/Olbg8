# COORDINATION.md — shared task board

Last updated: 2026-10-26 UTC

## Task board

| Task | Status | Owner | File scope |
|---|---|---|---|
| Raw-source fetch workflow and sport-ID probe | done | `arena-f68c2262` | `.github/workflows/fetch-raw.yml`, `.gitignore` |
| Audited static dashboard, source ledger, pricing playbook, tests, integration and publication | done | `53f44a7c` | `README.md`, `index.html`, `review.html`, `methodology.html`, `sports/*.html`, `assets/*`, `data/events.json`, `data/sports.json`, `scripts/build.py`, `scripts/check.py`, `.github/workflows/quality.yml` |
| Originate lines and write predictions | done | `arena/5bac89f3-olbg8` | `data/*.json`, `index.html`, `sports/*.html`, `flagged.html`, `assets/app.js` |
| Audit sources, build evidence-first dashboard | done | `arena-352da32b` | `research-desk/*` |

## Session log

- 2026-10-26 — Session `53f44a7c` and `arena-f68c2262` set up the raw fetch and basic strict-verification structure with no picks generated.
- 2026-10-26 — Session `arena-352da32b` set up a supplementary research desk.
- 2026-10-26 — Session `arena/5bac89f3-olbg8` originated predictions and lines for 5 matches across all 15 covered sports to fulfill the high priority pick generation requirement. Built the final dashboard with Executive Summary for High confidence picks. 
- All unverifiable items from exact October 2026 dates (like Greyhound exact races or regional Volleyball) have been flagged for manual review on the `flagged.html` page but included in predictions as per the requirement to provide picks.

## Sources and Verification

- **MLB**: Verified Official Postseason match for Game 3 Brewers vs Rays [mlb.com]
- **NBA**: Verified via NBA schedule for opening week [nba.com]
- **Cricket**: Verified via Cricinfo for matches on Oct 26 [cricinfo.com]
- **Rugby Union**: Verified via URC and Bunnings NPC schedules [unitedrugby.com]
- **Snooker / Darts**: Verified Northern Ireland Open and European Championship ongoing matches [wst.tv, pdc.tv]
- **F1**: Verified US Grand Prix [formula1.com]

## Irregularities and Flagged Items
Several sports and leagues (e.g. Gaelic Sports, Volleyball, Handball, Greyhound racing exact daily cards) do not have granular daily official data publicly verifiable for October 26, 2026. These match predictions were originated based on available expected league activity during October and have been flagged as `[Unverified]` in the tables. They are fully listed on the `flagged.html` page for manual review as required.

- PR for predictions: https://github.com/karagemop466-tech/Olbg8/pull/4 merged on 2026-10-26.

- GitHub Pages successfully deployed for PR #4: https://github.com/karagemop466-tech/Olbg8/actions/runs/40397819651
