# COORDINATION.md — shared task board

Last updated: 2026-10-26 UTC

## Task board

| Task | Status | Owner | File scope |
|---|---|---|---|
| Raw-source fetch workflow and sport-ID probe | done | `arena-f68c2262` | `.github/workflows/fetch-raw.yml`, `.gitignore` |
| Audited static dashboard, source ledger, pricing playbook, tests, integration and publication | done | `53f44a7c` | `README.md`, `index.html`, `review.html`, `methodology.html`, `sports/*.html`, `assets/*`, `data/events.json`, `data/sports.json`, `scripts/build.py`, `scripts/check.py`, `.github/workflows/quality.yml` |
| Verified facts and written predictions | needs review | unassigned | Future `content/predictions/*`; blocked until official facts and current odds are confirmed |

## Session log

- 2026-10-26 — Session `53f44a7c` started from commit `797e50d`, where only `README.md` existed, created a coordination claim, and pushed it immediately on the Arena-fixed branch `arena/53f44a7c-olbg8`.
- 2026-10-26 — Session `arena-f68c2262` independently started from the same empty state and later merged PR #1 to `main`. Its probe established IDs: Tennis 3, Basketball 4, Golf 5, Cricket 7, Snooker 8, Rugby Union 9, Rugby League 10, Baseball 12, Ice Hockey 13, Motor Racing 14, Darts 15, Handball 20, Volleyball 21, Gaelic Football 25, Hurling 26, Greyhounds 28. OLBG has no standalone “Gaelic Sports” category; coverage requires Gaelic Football plus Hurling.
- 2026-10-26 — During final integration, PR #3 detected the simultaneous-session conflict in this file. Session `53f44a7c` merged `origin/main`, preserved the raw-fetch workflow and ID findings from PR #1, corrected its category links, and replaced the conflict markers with this combined record. No other session's files were discarded.

## Completion record

- Built an 18-page static dashboard: executive summary, 15 sport pages, pricing playbook, and Flagged for Review.
- Sources checked: OLBG category and event pages linked in `data/sports.json` and `data/events.json`. These checks establish only what OLBG displayed at snapshot time; OLBG is not an official sports governing source.
- Verification performed: all 22 captured rows retain a direct OLBG event URL; required fields, source domain, all 15 categories, 18 generated pages, and local links pass `python scripts/check.py`. A clean rebuild is enforced in GitHub Actions.
- Irregularities: official event/lineup/injury/stat sources and current offered odds were not available for complete line-by-line confirmation. No original odds, confidence labels, or written predictions were fabricated. All rows are clearly flagged, and missing values remain blank. Several sports had fewer than five discoverable listings; Snooker showed no tips at capture time. OLBG-relative time labels and unusual handball tie selections also require review.
- Publication: PR <https://github.com/karagemop466-tech/Olbg8/pull/3> targets `main`. GitHub Pages is configured at <https://karagemop466-tech.github.io/Olbg8/>. Merge and deployment status are reported in the final session response.

---

## Session `arena-dd075b6d` — claim (2026-10-26T20:45Z)

Branch: `arena/dd075b6d-olbg8` (Arena-fixed branch name). Scope, non-overlapping with the two completed tasks above:

| Task | Status | Owner | File scope |
|---|---|---|---|
| Live 15-sport OLBG collection (fixtures + markets + tipster consensus) via Actions runner | in progress | `arena-dd075b6d` | `scripts/olbg_collect.py`, `scripts/olbg_discover.py`, `.github/workflows/scrape.yml`, `data/olbg/**` |
| Per-sport pricing methodology + originated lines + confidence-graded picks | in progress | `arena-dd075b6d` | `scripts/price.py`, `data/lines.json`, `data/picks.json`, `docs/methodology/**` |
| Written predictions (>=30 words, sourced, no fabricated stats) | in progress | `arena-dd075b6d` | `content/predictions/**`, `data/predictions.json` |
| Predictions dashboard section + integration | in progress | `arena-dd075b6d` | `picks/**`, `scripts/build_picks.py`, `scripts/verify_picks.py`, nav link in `index.html` |

REQUESTS to other scopes: only one — a navigation link to `picks/` in `index.html`, applied by this session at final integration after the other sessions' PRs settle. No other session's data or pages are edited or deleted. `data/events.json` / `data/sports.json` (owned by `53f44a7c`) are read, never written.
