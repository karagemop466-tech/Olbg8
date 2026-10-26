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

## Supplementary session arena-352da32b (parallel integration)

# Coordination

Session: arena-352da32b. Required session branch: `arena/352da32b-olbg8` (platform restriction overrides requested session branch naming).

| Task | Status | Owner | File scope |
|---|---|---|---|
| Audit sources, build evidence-first dashboard and pricing specifications, integrate and deploy | in progress | arena-352da32b | COORDINATION.md, README.md, index.html, assets/, data/, scripts/, .github/ |

## Log
- 2026-10-26: Repository inspected: only README.md; no existing application, data, or task claims. Claiming initial integration scope. No other session claims found. Will not represent inaccessible sources as checked or manufacture fixtures/picks.
- 2026-10-26: Built 20 static pages and transcribed 75 partial OLBG event observations across 15 sports (Snooker excerpt empty; Gaelic includes Hurling). Sources and exact limitations: data/SOURCES.md. Checked official MLB, ICC, F1 fixture information; ATP, NBA and PDC extraction limitations recorded. Every research row links to an observed OLBG event URL. Missing official facts/odds/lines/predictions remain null. Row-level issues published on Flagged for Review.
- Verification: Python build succeeds; 3 automated tests pass covering internal links across 20 pages, row source/identity/null-prediction constraints, odds/EV/push arithmetic. Python compilation succeeds. External event HTTP status not exhaustively checked. No full completeness claim, fitted pricing engines or completed daily prediction quota. These are needs-review items, not hidden completion claims.
- Automation: dependency-free daily public-link discovery saves unverified artifacts; does not auto-promote facts or fabricate predictions. Static snapshot is not a live feed. Main Pages workflow builds/tests before deploying.
- Integration conflict avoidance: remote main advanced with sessions arena-f68c2262 and 53f44a7c after initial claim. Their root site and build tooling are now owned/published. Relocated this session's work to `research-desk/` (all files beneath it) plus own workflows pages.yml/discovery.yml. Their root assets/data/scripts and README will be preserved on integration. Request to root-site owner: optionally link `research-desk/index.html` as expanded evidence inventory. Permission to switch Pages to Actions returned HTTP 403, so retain legacy main/root publication and check generated supplementary HTML into research-desk/.
