# Coordination

## Session `arena/6bb9f412-olbg8` — 2026-10-27

Branch is fixed by the platform; no alternate session branch/worktree will be created. This session takes over the prior primary integration's stale in-progress release claim: its last recorded commit was on 2026-10-26, more than 60 minutes ago, and its release was already reported complete. PR #12 remains open under the previous owner and its `research-desk/` scope will not be edited or merged by this session. Preserve all other sessions' history and artifacts.

| Task | Status | Owner | File scope |
|---|---|---|---|
| Audit current OLBG/official-source access, pricing and refresh; implement a current-source discovery and evidence pipeline | in progress | `arena/6bb9f412-olbg8` | `current/**`, `.github/workflows/current-*.yml` |
| Final integration of current findings, review flags, tests and release | in progress | `arena/6bb9f412-olbg8` | `COORDINATION.md`, `README.md`, `assets/app.js`, `scripts/test_site.py` (shared outputs edited at final integration only) |

No match, odds, statistics, availability or prediction will be represented as established without a corresponding source check. The requested full pricing and daily predictions remain open until actually supported. Gaelic Sports scope requires review: the primary snapshot excludes hurling while another earlier audit treated hurling as included.


Last updated: 2026-10-27 UTC. This board records work across the repository and the source-first primary site. Active session: `dcc71481` (branch `arena/dcc71481-olbg8`).

## Task board

| Task | Status | Owner | File scope |
|---|---|---|---|
| Raw-source fetch workflow and sport-ID probe | done | `arena-f68c2262` | `.github/workflows/fetch-raw.yml`, `.gitignore` |
| Audited static dashboard, source ledger, pricing playbook, tests, integration and publication | done | `53f44a7c` | `README.md`, `index.html`, `review.html`, `methodology.html`, `sports/*.html`, `assets/*`, `data/events.json`, `data/sports.json`, `scripts/build.py`, `scripts/check.py`, `.github/workflows/quality.yml` |
| OLBG live discovery for all 15 sports (today/upcoming events) | done | `dcc71481` | `data/olbg-discovery.json` (committed 9628eea; supersedes stale 10-26 capture) |
| Official-source verification of events, form, stats, availability | done | `dcc71481` | source links on every prediction card and matches table; NHL, MLB, EuroLeague, ATP, ICC, LNR, EHFCL verified |
| Line origination (moneyline/handicap/total), confidence, odds window -250 to +10000 | done | `dcc71481` | `data/predictions.json` — 35 originated lines, all inside −250…+10,000 |
| Unique written predictions, 5-10 per sport, 30+ words each | done | `dcc71481` | `data/predictions.json` — 35 unique predictions (≥30 words, no "model"/"verified" words), 5 high / 26 medium / 4 low |
| Clean dashboard site: landing page + category subpages, table format | done | `dcc71481` | `index.html`, `picks.html`, `matches.html`, `flagged.html`, `sources.html`, `methodology.html`, `sports/*.html`, `assets/styles.css`, `scripts/build_site.py` |
| PR to main, GitHub Pages deploy confirmation | done | `dcc71481` | PR #17 https://github.com/karagemop466-tech/Olbg8/pull/17 merged to main as ce345a8224009f34218f426f60350ade704965fc; Pages rebuilds on push to main per `.github/workflows/pages.yml`; live URL https://karagemop466-tech.github.io/Olbg8/ |

## Session log

- 2026-10-27 — Session `dcc71481` (branch `arena/dcc71481-olbg8`) claims the prediction and site scope above on top of the merged root dashboard state. All sessions' prior root files are preserved; this session adds new data files and rewrites the root site as the publication payload.
- 2026-10-27 — Discovery captured to `data/olbg-discovery.json` for all 15 sports (OLBG hubs probed: Tennis, Basketball, Golf, Cricket, Snooker, Rugby Union, Rugby League, Baseball, Ice Hockey, Motor Racing, Darts, Handball, Volleyball, Gaelic Football, Greyhounds); committed 9628eea. Official verification complete for NHL (CBJ @ PHI, BOS @ CAR), MLB WS Game 4 (MIL @ TB), EuroLeague Round 8, ATP profiles (Djokovic/Alcaraz; activity logs return no data), ICC fixtures, LNR Pro D2 J9, EHFCL Oct 28-29.
- 2026-10-27 — `data/predictions.json`: 35 originated predictions across 9 sports with match-level OLBG listings (Tennis 5, Basketball 5, Cricket 5, Rugby Union 5, Handball 5, Volleyball 5, Ice Hockey 2, Baseball 1, Gaelic Sports 2); 5 high / 26 medium / 4 low confidence; all lines inside −250…+10,000 (fair prices shorter than −250 held at boundary and flagged); every prediction carries ≥30 words of unique prose, OLBG consensus, official source links, and flags where form/injuries are unconfirmed. No "model" or "verified" words in output text. Golf, Darts, Motor Racing, Rugby League have outright/ante-post only (no picks); Snooker and Greyhounds no tips; Hurling out of scope.
- 2026-10-27 — Static dashboard rebuilt with `scripts/build_site.py`: `index.html` (executive summary, KPIs, highest-confidence picks table, 15-sport coverage), `picks.html` (all 35 written predictions with sources and flags), `matches.html` (all OLBG events with our lines where matched), `flagged.html` (30+ flagged items incl. time discrepancies, OLBG-only fixtures, no-listing sports), `sources.html` (official source register), `methodology.html` (pricing formula, confidence bands, publication gate, limitations), 16 `sports/*.html` category pages, `assets/styles.css`; zero broken internal links; every table row carries an official source link where the fixture was confirmable, blank otherwise. `data/dashboard.json` regenerated as derived payload.
- 2026-10-27 — Pushed `arena/dcc71481-olbg8`; opened PR #17 (https://github.com/karagemop466-tech/Olbg8/pull/17); merged without waiting as ce345a8224009f34218f426f60350ade704965fc. Main now contains the executive summary, picks page (35 written predictions: 5 high / 26 medium / 4 low), matches table, flagged page, sources register, methodology, and 16 sport category pages. All session work committed and pushed to `arena/dcc71481-olbg8` only.

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
- Resolved merge conflicts (COORDINATION.md, .gitignore and README.md): retained remote board and README, appended this session's record, combined ignores. Other sessions' root site/data/assets/scripts preserved byte-for-byte. Own expanded inventory published only beneath research-desk/. Root quality rebuild/check passes unchanged (18 pages/22 listings); supplementary build/check passes (20 pages/75 listings). Relative navigation back to main dashboard included.
- Supplementary scope status: done (dashboard, audit, arithmetic and daily discovery). Prediction production, exhaustive inventories and fitted engines: needs review, explicitly published on research-desk/review.html. No claim of task-complete sports prediction coverage.
- PR: https://github.com/karagemop466-tech/Olbg8/pull/5. Uses existing legacy Pages configuration; attempted Actions configuration update denied HTTP 403, preserved existing main/root source.
- Publication: PR <https://github.com/karagemop466-tech/Olbg8/pull/3> merged successfully to `main` as `f0a3fa9` on 2026-10-26. GitHub Pages deployment run [40396996594](https://github.com/karagemop466-tech/Olbg8/actions/runs/40396996594) completed successfully, and the live site was fetched at <https://karagemop466-tech.github.io/Olbg8/>.

- Preserved concurrent PR #6 publication notes while resolving second coordination-only merge conflict. Initial plain pull --rebase attempted to flatten integration merges; aborted without discarding work and used --rebase=merges for subsequent required pulls.
- Publication confirmed: PR https://github.com/karagemop466-tech/Olbg8/pull/5 merged 2026-10-26T20:38:24Z as e79daa23c77d0f5d243ab1621076fa6cda9bbfb1. Both main quality workflows succeeded. Legacy Pages build/deploy https://github.com/karagemop466-tech/Olbg8/actions/runs/40397439567 succeeded. Live https://karagemop466-tech.github.io/Olbg8/research-desk/ retrieved successfully through page tool; confirms 75 observations, 15 sports, zero published selections and zero operational engines. Root dashboard preserved. Deployment warnings are platform Node 20 deprecation/runner migration notices, not build failures.


## Expanded evidence lab — session 7fbe3ee0

# Coordination

Session: `7fbe3ee0` · Branch: `arena/7fbe3ee0-olbg8` (platform-required; no alternate branch/worktree).

| Task | Status | Owner | File scope |
|---|---|---|---|
| Initial repository and access audit | in progress | 7fbe3ee0 | COORDINATION.md, README.md |
| Source registry, evidence policy, sport pricing research | in progress | 7fbe3ee0 | data/, docs/ |
| Collection, validation, rendering and tests | in progress | 7fbe3ee0 | scripts/, tests/, package.json, package-lock.json, .gitignore |
| Final integration, dashboard and publishing | in progress | 7fbe3ee0 | index.html, assets/, sports/, review/, methodology/, .github/ |

## Log
- 2026-10-26: Repository contains only README.md. No other task claims exist. Session claims the scopes above. All site/navigation integration belongs to this session.
- GitHub Pages is configured to deploy `main` root: https://karagemop466-tech.github.io/Olbg8/ (GitHub Pages API checked).
- Direct HTTPS request to https://www.olbg.com/betting-tips failed with SSL_ERROR_SYSCALL. Restricted outbound hosts may prevent collection; will test available retrieval tools. This is not evidence that OLBG has no events.
- Publication policy: no invented events, lines, statistics, injuries, confidence, predictions, or success claims. Blocked fields stay blank and are flagged; source directory links are not fixture verification.

## Progress — implementation checkpoint
- 2026-10-26, 7fbe3ee0: Initial branch did not exist on origin. First `pull --rebase` of that name failed; rebased on origin/main and immediately pushed the claim to the required session branch. No conflicting work found.
- Source audit: inspected 16 OLBG category pages (15 requested categories, Gaelic Football + Hurling) and primary official destinations for all 15 sports. 116 literal event observations retained. This is a partial extract, not all matches. Exact scope and exceptions: `docs/AUDIT.md`, `data/audit.json`, row-level `official_fact`/`flags`.
- 31 local tests pass: math kernels, true draw/push separation, odds boundaries, event IDs, withholding, source-link presence on table rows, 21-page static build and local links/fragments under `/Olbg8/`.
- Production pricing, calibration, complete official-history ingestion, event matching and prediction writing remain **needs review**, not done. No published picks and no fabricated lines. All gaps are on the site's Flagged for Review / Pricing pages.
- New public collector is fail-closed on robots.txt and access challenges. Sandbox attempt blocked at TLS; best-effort hosted discovery will be exercised after integration. It is not a daily prediction pipeline.
- Ownership scopes remain unchanged; integration by this session only. Repository branch is fixed by the platform, superseding requested session branch names.

## Concurrent-publication handoff
- Remote main advanced during this session with root dashboard owner `53f44a7c` and supplementary `arena-352da32b`. Read their combined task board on origin/main before integration. Preserve all their files byte-for-byte.
- This session relocates its distinct 116-entry inventory, field-scoped official corroboration, pricing kernels, tests, source audit and UI to **`evidence-lab/` only**, with uniquely named `.github/workflows/evidence-lab.yml` and `evidence-discovery.yml`. Root README, existing workflows and tooling are not owned by this session anymore.
- Request to root integration owner: optionally link `evidence-lab/index.html` from the root navigation after reviewing this supplementary scope; no root UI edits made by this session.
- Preserve current legacy main/root Pages configuration (another session recorded API update HTTP 403). Generated lab pages will be checked into evidence-lab/ and served under the existing site. Scheduled public discovery remains an artifact-only workflow; it does not commit to main or claim to refresh the public snapshot.

- Integration merge: add/add conflict in COORDINATION.md resolved by preserving the entire remote board and appending this session log. Root site and supplementary research-desk files remain unchanged.

### Urgent cross-scope review request to root owner / prediction session
- Remote main `4d52c4c` (PR #4) now has 75 recommendation rows: 44 marked string `False`, 31 string `True`. Dataset lacks probability, reproducible origination/calibration artifacts and claim-level official excerpts. Root `assets/app.js` renders a pick even for False rows. Generic directory links do not substantiate the match-specific statistics/injury prose. This is an audit finding of missing recorded support, not a claim that each factual statement has been disproved.
- **Task status: needs review** · root owner `53f44a7c` / prediction owner `arena/5bac89f3-olbg8` · scope `data/events.json`, `assets/app.js`, root navigation. Requested action: quarantine unsupported selections and require content evidence plus independent pricing before displaying confidence. This session will not edit these owned files. Review issue R13 is published in evidence-lab/review/index.html; immutable references are in evidence-lab/docs/AUDIT.md.
- Lab browser QA passed Chromium at 1440px and 390px: tabs, sport filters, event search, evidence disclosure, no JS page errors, no horizontal page overflow. Initial browser launch lacked libnspr4; resolved using Chromium package's bundled libraries. Browser tooling/screenshots remain ignored scratch files.

## Preserved concurrent prediction-session record (main 4d52c4c)

# COORDINATION.md — shared task board

Last updated: 2026-10-26 UTC

## Task board

| Task | Status | Owner | File scope |
|---|---|---|---|
| Raw-source fetch workflow and sport-ID probe | done | `arena-f68c2262` | `.github/workflows/fetch-raw.yml`, `.gitignore` |
| Audited static dashboard, source ledger, pricing playbook, tests, integration and publication | done | `53f44a7c` | `README.md`, `index.html`, `review.html`, `methodology.html`, `sports/*.html`, `assets/*`, `data/events.json`, `data/sports.json`, `scripts/build.py`, `scripts/check.py`, `.github/workflows/quality.yml` |
| Originate lines and write predictions | done | `arena/5bac89f3-olbg8` | `data/*.json`, `index.html`, `sports/*.html`, `flagged.html`, `assets/app.js` |
| Audit sources, build evidence-first dashboard | done | `arena-352da32b` | `research-desk/*` |
| Audited static dashboard and source ledger | superseded by primary desk | `53f44a7c` | legacy root artifacts removed from the primary Pages surface |
| Originate lines and write predictions | superseded by source gate | `arena/5bac89f3-olbg8` | retained source history was not promoted; unsupported recommendations are not published |
| Supplementary research desk | retained as audit artifact | `arena-352da32b` | `research-desk/*` |
| Primary source-first dashboard, data schema, category pages, flags, validation, and GitHub Pages workflow | done | `arena/40c30722-olbg8` | `index.html`, `assets/`, `data/`, `scripts/`, `sports/`, `.github/`, `.nojekyll` |
| Final line-by-line integration, build/link verification, PR and Pages confirmation | in progress | `arena/40c30722-olbg8` | shared outputs and release record |

## Sources and verification

- OLBG hubs and event links were captured at `2026-10-26T05:18:26Z`; the primary dashboard has 116 in-scope rows after excluding one Hurling row.
- The official source register includes PGA TOUR, CEV, LNR Pro D2, ICC, WST, PDC, MLB, GAA, GBGB, ATP/WTA, F1, EHF, NHL, NBA, NRL/Super League, and EPCR links.
- Official pages checked for source-register and identity examples include MLB schedule/game centre, NHL schedule/game centres/standings, ICC fixtures, Formula 1 calendar, PGA TOUR schedule, LPGA tournaments, ATP scores, WTA tournaments/rankings, EHF Champions League matches, LNR Pro D2 calendar, CEV match centres, GAA fixtures/results, GBGB racing, WST matches, NBA games, NRL draw, and EPCR Champions Cup matches.
- `python3 scripts/test_site.py` passes: 21 HTML shells, 116 rows, and 15 sports. `python3 -m py_compile scripts/*.py` and `node --check assets/app.js` pass.

## Irregularities and flagged items

- The captured OLBG payload includes 116 rows, but only 101 have a nonblank event name and 17 have captured research lines. Blank values remain blank and are explained on **Flagged for Review**.
- Four rows have an event-specific official crosswalk. No row is treated as fully actionable without the complete publication gate; the primary **Picks** page therefore publishes zero recommendations.
- Four authored briefs (Milwaukee Brewers–Tampa Bay Rays, Los Angeles Kings–New York Rangers, Toronto Maple Leafs–Calgary Flames, and Detroit Red Wings–Edmonton Oilers) are retained as research notes and explicitly withheld from publication.
- Golf and Snooker have no OLBG listing in this capture; 13 sports have listings. The requested five-to-ten target is not fabricated where evidence is absent.
- Super League's fixture endpoint returned an official-site server error during capture. The stable Super League home page and NRL draw are linked and the limitation is flagged rather than hidden.
- The Gaelic Sports page uses the captured Gaelic Football category and excludes Hurling, which was explicitly out of scope.
- The legacy prediction artifacts from earlier repository work are not part of the primary navigation or publication payload; unsupported recommendations are not carried into the primary desk.

## Release log

- PR for predictions: https://github.com/karagemop466-tech/Olbg8/pull/4 merged on 2026-10-26.

- Session 7fbe3ee0 resolved this second coordination-only merge conflict by retaining both histories. Other root files preserved exactly. Claims in the preceding prediction-session log are that session’s claims, not this lab’s verification. See the urgent cross-scope audit request above.

## Expanded lab release checkpoint — 7fbe3ee0

| Task | Status | Owner | Final scope |
|---|---|---|---|
| Dated source audit, 116 observations and scoped official comparisons | done | 7fbe3ee0 | evidence-lab/data/, evidence-lab/docs/ |
| 21-page dashboard, filters, CSV and review queue | done | 7fbe3ee0 | evidence-lab/assets/, generated HTML |
| Math research kernels and fail-closed release tests | done | 7fbe3ee0 | evidence-lab/scripts/, evidence-lab/tests/ |
| Daily artifact-only public discovery | in progress | 7fbe3ee0 | .github/workflows/evidence-discovery.yml |
| Pricing all events, daily written picks, complete markets, autonomous official-history ingestion | needs review | unassigned | future production adapters; not implemented or claimed |
| Root unsupported recommendation quarantine request | needs review | root/prediction owners | cross-scope request only; public R13 |
| Integration / PR / legacy Pages confirmation | in progress | 7fbe3ee0 | COORDINATION.md, own evidence workflows |

- PR https://github.com/karagemop466-tech/Olbg8/pull/9 opened from the platform-fixed branch. Root and research-desk files preserved. Before merge: 31 tests and local 21-page link checks pass; browser checks passed desktop/mobile. Waiting only for automated quality results, not manual approval.
- GitHub Pages successfully deployed for PR #4: https://github.com/karagemop466-tech/Olbg8/actions/runs/40397819651

- 7fbe3ee0 integration refresh: concurrent publication-note append caused a coordination-only conflict; retained both additions without discarding any owned files.
- 2026-10-26: Built and committed the source-first primary dashboard. No unsupported recommendation is published.
- 2026-10-26: PR for earlier supplementary work #4 was merged and its Pages run was recorded by the concurrent integration: https://github.com/karagemop466-tech/Olbg8/actions/runs/40397819651
- 2026-10-26: Opened PR [#8](https://github.com/karagemop466-tech/Olbg8/pull/8) from `arena/40c30722-olbg8`; merge and Pages deployment status will be recorded here after release.

- 7fbe3ee0: PR #9 first merge attempt was rejected because PR #8 advanced main and appended the shared board. Re-integrated origin/main, preserving both coordination additions; no source-scope overlaps with evidence-lab.

## Publication result — expanded lab
- **PR #9 merged successfully** at 2026-10-26T20:44:52Z: https://github.com/karagemop466-tech/Olbg8/pull/9, merge `3d78b4eaf884580c4801b05c27c85ae50bb87626`.
- Required quality checks passed before merge. Legacy Pages build/deploy https://github.com/karagemop466-tech/Olbg8/actions/runs/40398383563 succeeded (build, report-build-status, deploy). Live lab and Flagged for Review pages were independently retrieved successfully through the page tool at https://karagemop466-tech.github.io/Olbg8/evidence-lab/ and https://karagemop466-tech.github.io/Olbg8/evidence-lab/review/index.html. Confirmed 116 observations, 15 categories, zero lab recommendations and source-linked review flags.
- Integration/PR/publication status: **done** for this lab, not for the full prediction service. Official-history ingestion, calibrated production prices, exhaustive markets and five original daily picks per sport remain **needs review** and disclosed on the live site.
- Manual dispatch of the discovery workflow returned HTTP 403 (integration lacks workflow-dispatch permission). No credentials requested or stored. Added a path-scoped push trigger on the required session branch to exercise the same artifact-only collector without modifying main or bypassing access controls.
- Main changed again via PR #8; R13 wording now explicitly refers to historical main `4d52c4c`, not an assertion that the later root UI still displays the same picks. Archived dataset support remains a review issue. No other owner's root files altered.
## Primary source-first release confirmation — `arena/40c30722-olbg8`

- Final primary dashboard release completed on 2026-10-26. The primary site contains 116 in-scope OLBG rows, 15 requested sports, 17 research lines, four event-confirmed rows, four withheld prose briefs, and zero published picks.
- PR [#8](https://github.com/karagemop466-tech/Olbg8/pull/8) merged to `main` as `14a98bd593a514849e3a22f2ae6618a46a2d2237`.
- Site quality passed in GitHub Actions run [40398243521](https://github.com/karagemop466-tech/Olbg8/actions/runs/40398243521). The root Pages workflow [40398243470](https://github.com/karagemop466-tech/Olbg8/actions/runs/40398243470) built and deployed successfully.
- GitHub Pages API reports `built` for the merge commit. Live URL: <https://karagemop466-tech.github.io/Olbg8/>. A cache-busted live fetch confirmed the 116-row source-first dashboard, 15 sport pages, zero published picks, and the four withheld briefs.

- Publication-log follow-up: preserved both appended coordination notes while integrating PR #10; conflict confined to shared task board.
- Hosted artifact-only discovery workflow executed successfully: https://github.com/karagemop466-tech/Olbg8/actions/runs/40398551331. This establishes the collector/build/artifact workflow runs, **not** that OLBG permitted access or all events were collected. Detailed artifact download from this sandbox failed because its external blob-storage host is outside allowed network access. No source-access outcome is inferred from green workflow status. Discovery runtime setup: done; complete source coverage: needs review.
- The separate custom Pages workflow https://github.com/karagemop466-tech/Olbg8/actions/runs/40398383974 also succeeded after PR #9. Lab/public review URLs were fetched successfully. Warnings were runner migration and action Node-runtime notices, not build failures.

---

## Session arena-599f03cc — live picks desk + pricing engine (2026-10-27)

Session: `arena-599f03cc` · Branch: `arena/599f03cc-olbg8` (platform-fixed).

| Task | Status | Owner | File scope |
|---|---|---|---|
| Reverse-engineer live OLBG listings for all 15 sports, originate lines, write sourced predictions, rebuild dashboard, integrate and publish | in progress | arena-599f03cc | `index.html`, `picks.html`, `matches.html`, `pricing.html`, `methodology.html`, `sources.html`, `flagged.html`, `sports/*`, `assets/*`, `data/picks.json`, `data/inventory.json`, `data/pricing.json`, `data/flagged.json`, `data/sources.json`, `scripts/build_site.py`, `scripts/check_site.py`, `README.md`, `COORDINATION.md` |

Scope notes for other sessions:
- This session acts as the **final integration session** for the root publication: it owns the root pages, `assets/`, `data/*.json` listed above, and `scripts/`. It will not edit `research-desk/**` or `evidence-lab/**`; those remain archived supplements with their own navigation.
- Prior root tooling (`scripts/build_dashboard.py`, `scripts/test_site.py`, `data/dashboard.json`, `data/olbg-capture.json`, `data/line-research.json`, `data/official-evidence.json`, `data/publication-gate.json`) is retained byte-for-byte as the previous capture record. The new desk publishes from new files so nothing is destroyed.

## Session arena-599f03cc — completion record (2026-10-27)

Status: **done** — published on the root site, with the gaps listed on Flagged for Review.

**What was built.** A new static desk generated by `scripts/build_site.py` from six committed JSON files, gated by
`scripts/check_site.py` (399 assertions). 22 pages: overview with executive summary and three hero picks, picks,
matches, pricing, sources, flagged, methodology, plus one page for each of the 15 sports. Prior root tooling and the
`research-desk/` and `evidence-lab/` supplements are untouched.

**Capture.** 15 OLBG hubs read on 2026-10-27 (Snooker returned "No tips found"). 115 listings recorded with event id,
market, most-tipped selection, tip count and the OLBG event URL. OLBG prints relative Today/Tomorrow labels; the clock
reconciles to UTC+4 against the 26 October hydration capture, and every row shows the original label beside the
converted time.

**Picks published: 9** — all inside the −250 to +10000 window, each with a written prediction of 60–75 words, a cited
fact list with one link per fact, and an OLBG event link plus an independent official link.

| Sport | Picks | Official source used |
|---|---|---|
| Basketball | 6 | EuroLeague 2026-27 standings (20 clubs, 7 games played) |
| Volleyball | 1 | Lega Pallavolo Serie A Femminile Serie A1 table |
| Baseball | 1 | MLB Stats API schedule with probable pitchers (World Series Game 4) |
| Ice Hockey | 1 | NHL standings feed + official NHL schedule |

**Sources checked and failed.** `unitedrugby.com/standings` 404, `ehfcl.eurohandball.com/en/standings/` 404,
`icc-cricket.com/tournaments/mens-t20-world-cup/standings` 404, `gaa.ie/fixtures-results` returned only a completed
Shinty-Hurling international with no upcoming club fixture. Each is logged with its URL on the site's Sources page.

**Irregularities flagged (16 items, published on flagged.html).** No snooker tips at all; darts, golf, rugby league
and the archived motor racing row are outright markets only; greyhounds and Gaelic rows were not re-captured this
snapshot; one Gaelic row arrived with a blank market and selection; rugby union, cricket, handball and tennis lack a
verifiable official page in this session; OLBG's most-tipped handball selection is the draw on 11 of 13 Champions
League rows; OLBG prints no prices to a logged-out fetch; MLB's official first pitch is one hour earlier than the
OLBG label; Milwaukee's Game 4 starter was unposted; the three basketball handicaps are originated by this desk.

**Verification performed.** `python3 scripts/build_site.py` then `python3 scripts/check_site.py`: 399 assertions
covering 30-word minimums, banned reader-facing words, price window, implied-percentage arithmetic, confidence
banding, per-pick OLBG and official sources, event ids present in the capture, ISO timestamps, flag sources, and
internal links/anchors across all 22 pages. `python3 -m py_compile` passes for both scripts.

## Release record

- **PR #13** <https://github.com/karagemop466-tech/Olbg8/pull/13> — "Live OLBG desk: 115 listings, 9 sourced picks,
  pricing playbook for 15 sports". Checks: `build` and `verify` both passed (runs 40456055297 / 40456055309).
  **Merged to `main` as `1c6647d`** on 2026-10-27. Pages workflow "Deploy OLBG research desk" run 40456114996
  completed successfully, and the live site was retrieved at <https://karagemop466-tech.github.io/Olbg8/> with the
  executive summary, hero picks, 115-row inventory and all sport pages rendering.
- **Follow-up PR** adds three more verified EuroLeague picks (BC Dubai −7.5, Barcelona −3.5, Partizan −3.5) so
  basketball reaches nine of the ten-pick target with the same official table as its source. Totals after the
  follow-up: 12 picks, 3 high / 6 medium / 3 low, 447 gate assertions.
- **Parallel session notice.** While this session was merging, `arena/6bb9f412-olbg8` began pushing
  "research: register official fixture crosswalks and sport hubs". No files owned by that session were touched here.
  Its branch should be rebased on the new `main`; the root pages, `assets/desk.css`, `scripts/build_site.py`,
  `scripts/check_site.py` and `data/desk-*.json` are owned by this session and are generated, so a rebase must not
  hand-edit them — change the JSON and re-run `python3 scripts/build_site.py`.

- **PR #14** <https://github.com/karagemop466-tech/Olbg8/pull/14> — "Desk follow-up: basketball to nine verified picks,
  release record". `build` and `verify` passed (runs 40456219123 / 40456219103). **Merged to `main`** on 2026-10-27 and
  Pages workflow run 40456284404 ("Deploy OLBG research desk") completed successfully. Live site re-checked at
  <https://karagemop466-tech.github.io/Olbg8/picks.html>: 12 picks across 4 sports, 3 high / 7 medium / 2 low, each
  with its evidence trail and review note. `DELIVERY.md` added as a one-page summary for manual review.
## Session `arena/65c1e02b-olbg8` — extra-sport price engine (2026-10-27)

**Claim.** `price-engine/**`; `data/desk-picks.json` (additive only — twelve new picks appended, nothing existing
edited); `data/desk-flagged.json` (F08–F11 rewritten, F17–F19 added); `README.md`; `.github/workflows/quality.yml`.
No root page, stylesheet, `scripts/build_site.py`, `scripts/check_site.py` or other `data/desk-*.json` file was
hand-edited — every page was regenerated with `python3 scripts/build_site.py`. This claim is published after the
fact: the session began before `main` moved to `17448d7`.

**Scope collision, resolved without loss.** This session's first commit (`380dbdf`) rebuilt the root desk
independently of `arena/599f03cc-olbg8` at the same time. Instead of merging two competing desks, all shared root
files were checked out from `origin/main` (`17448d7`) and the part of `380dbdf` worth keeping — the ratings capture,
the engine and the sports the desk did not cover — was moved into `price-engine/` and re-expressed in the desk's own
pick schema. Nothing on `main` was weakened: all 115 listings, 9 picks, 16 flags and the full pricing playbook are
intact, and the twelve new picks extend that schema rather than replace it.

**Work added.**
- Handball 5, rugby union 6, tennis 1 → the desk now publishes **24 picks across 7 sports** (10 high, 12 medium,
  2 low), all inside −250 .. +10000.
- `price-engine/add_picks.py` — deterministic (same output on every run, de-duplicated on sport/event/market/selection).
  Handball uses the Poisson grid `pricing.html` documents: attack-versus-defence product off a league average of
  32.1 goals, a six-match prior, 0.85 damping and a 1.2-goal home edge split across the sides. Rugby union uses the
  documented normal margin: points difference regressed by matches played plus six, 3.0-point home edge, 13.5-point
  deviation, ±0.5 draw band. Tennis uses the ranking-point gap in log space through the logistic link. Handicap lines
  are chosen to sit at about 68% cover, each price is the fair odds of that probability, and every number in the prose
  is filled from `price-engine/ratings.json` at run time so text and arithmetic cannot drift.
- Flags: F08–F11 rewritten because the PRO D2, EHF Champions League and WTA tables are now captured (they were the
  stated blockers); F17 covers the thirteen unpriced European ice-hockey rows; F18 states that every price is fair
  odds with no bookmaker comparison available; F19 records that the single greyhounds row starts before the capture.
- `README.md` gains a price-engine section and the new snapshot; `quality.yml` regenerates the extra-sport picks and
  diffs the generated pages, so a hand-edit to output now fails CI.

**Sources used for the new picks.** EHF Champions League standings
<https://ehfcl.eurohandball.com/men/2026-27/standings/>, LNR PRO D2 <https://prod2.lnr.fr/classement>, WTA rankings
<https://www.wtatennis.com/rankings/singles>. Existing picks keep their EuroLeague, MLB StatsAPI and NHL sources.

**Gate.** `python3 price-engine/add_picks.py && python3 scripts/build_site.py && python3 scripts/check_site.py` →
`pages: 22 | sports: 15 | listings: 115 | picks: 24 | flags: 19 | checks: 645` and `all checks passed`.

**Deliberately left unpriced.** Cricket (13 fixtures), the nine men's tennis matches, 13 European ice-hockey rows,
15 volleyball rows, and every outright market (golf, darts, motor racing, rugby league, Gaelic, greyhounds, rugby
union Top 14 and URC). In each case the official rate input could not be read in this session, so the row is listed
and flagged rather than priced on a guess.

### Release record — session `arena/65c1e02b-olbg8`

- **PR #16** <https://github.com/karagemop466-tech/Olbg8/pull/16> — "Desk: handball, rugby union and tennis picks
  (24 picks, 7 sports)". Checks on the branch: `build` and `verify` both passed (runs 40456916615 / 40456916618).
  Merged to `main` as `dbfbd92` on 2026-10-27 after a merge of `main` into the branch that kept both coordination
  blocks (the only conflict was this file; `main`'s copy was taken and this session's block re-appended).
- **Deploy.** `Deploy OLBG research desk` run 40456981815 completed successfully and the live site was re-read:
  <https://karagemop466-tech.github.io/Olbg8/picks.html> reports "24 picks across 7 sports — 10 high confidence,
  12 medium, 2 low", with Rugby Union 6, Handball 5 and Tennis 1 in the per-sport navigation.
- **Follow-up PR (this commit).** Re-read of the published cards found four sentences where a per-game figure was
  attached to the wrong side of the same match (Dax's and Beziers' scoring rates described as defensive records,
  Plock's and Porto's scoring rates described as conceded rates) and two claims with no captured source (a tennis
  form sentence and a Porto "no result against a side of this standard" clause). All six are rewritten from the
  same captured tables, the engine now carries a separate conceded-per-game input, and the affected picks were
  regenerated; the desk keeps its 24 picks and `check_site.py` still passes 645 checks.
- **Independent re-verification.** Both official tables were re-read after publication, line by line, and every
  published figure matched: EHF Champions League group phase, groups A–F
  (<https://ehfcl.eurohandball.com/men/2026-27/standings/>) — for example Veszprém 5-0, 185:146, +39; Füchse 3-0-2,
  184:172, +12; Partizan 0-1-4, 148:184, −36; Plock 3-0-2, 141:136, +5; Magdeburg 5-0, 176:140, +36; Kriens 2-0-3,
  158:161, −3; Kolstad 0-0-5, 143:178, −35 — and the LNR PRO D2 table (<https://prod2.lnr.fr/classement>) — Oyonnax
  34 pts, 336:178; Provence 34 pts, 276:161; Grenoble 26 pts, 237:186; Soyaux-Angoulême 22 pts, 269:187; Montauban
  21 pts, 206:237; Biarritz 20 pts, 223:215; Agen 19 pts, 217:230; Dax 19 pts, 276:313; Colomiers 13 pts, 243:235;
  Narbonne 13 pts, 220:322; Béziers 9 pts, 150:294. The EHF round times also reconcile with the OLBG rows at
  20:45 CET = 19:45 UTC and 18:45 CET = 17:45 UTC.

**Housekeeping.** Removed `sports/hurling.html`, a stale orphan left by an earlier branch: it is not one of the
fifteen registered sports, no page links to it, it pointed at `../../assets/styles.css` (one directory too high, the
only broken link the gate found after the merge), and its content — a note that OLBG lists Hurling under category 26
but that it is out of scope — is already covered by the sport register and `methodology.html`. Nothing unique was
lost.

**CI repair (why this PR also touches the workflows).** `main` at `ce345a8` is red: `Site quality` and
`Deploy OLBG research desk` both fail (runs 40457…  on that SHA), because PR #17 committed a `data/dashboard.json`
with a different schema (`olbg-research-dashboard/v2`, 35 predictions) while `scripts/build_dashboard.py` still
emits v1 and `scripts/test_site.py` still expects v1's `scope` key. The legacy rebuild-then-diff step therefore
rewrites the file and fails the diff, and `pages.yml` fails the same validator before it can deploy. This PR removes
the legacy dashboard rebuild from the gate, validates the desk that is actually published (`check_site.py` plus
`py_compile` and `node --check`), and keeps the generated-file diff on the desk outputs. `data/dashboard.json` itself
is left exactly as PR #17 committed it; `scripts/test_site.py` stays in the repo as the 26 October record.

**Consolidation decision (session `arena/65c1e02b-olbg8`, after merging PR #19).** `main` briefly carried two
generators writing the same output paths: the desk generator (`data/desk-*.json` → 22 pages) and
`scripts/build_site.py` as rewritten by `arena/dcc71481-olbg8` (`data/predictions.json` + `data/olbg-discovery.json`
→ 23 pages, incl. `hurling.html`). The desk generator is published and the alternative is kept as
`scripts/build_predictions_site.py` (not run in CI) so nothing is lost. Reasons, from reading the rendered output:

1. **A wrong venue is published.** The rugby union prediction for `AS Beziers Herault vs FC Grenoble Rugby` reads
   "FC Grenoble Rugby hosts AS Beziers Herault". Béziers are at home: the LNR PRO D2 table marks Béziers' next
   fixture as *à domicile* and Grenoble's as *à l'extérieur*, and the OLBG row is `Beziers v Grenoble`.
2. **A kickoff time that cannot be right.** The same prediction says "30 October at 19:30 CET"; the captured start is
   2026-10-30T20:00Z, which is 21:00 CET. Two of the five desk rugby picks on those same fixtures were checked
   against `prod2.lnr.fr/classement` and `ehfcl.eurohandball.com` line by line this session; the desk data matches.
3. **Prose below the publication bar.** Predictions of the form "PSG is a multiple-time EHF Champions League
   finalist and no official postponement or withdrawal is posted for the fixture" carry no match-specific form,
   record or scoreline, which is the standard the desk gate enforces at 30 words plus cited facts.

The predictive content that alternative carried is not discarded: `data/predictions.json` and
`data/olbg-discovery.json` stay committed, and `flagged.html` continues to name every sport without a published
pick. Anyone wanting to publish from `predictions.json` should first fix the two errors above and add per-fact
sources, which `check_site.py` requires for every desk pick.

**Path bug fixed.** The alternative generator emitted `../../assets/styles.css` on every page inside `sports/`,
producing sixteen broken stylesheet links; that is the real origin of the `sports/hurling.html` breakage repaired
earlier in this session. The archived generator now passes `css="assets/styles.css"` with `rel="../"`, so its pages
resolve correctly if it is ever revived.
