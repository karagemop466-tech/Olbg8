# Coordination

Last updated: 2026-10-26 UTC. This board records work across the repository and the source-first primary site on `arena/40c30722-olbg8`.

## Task board

| Task | Status | Owner | File scope |
|---|---|---|---|
| Raw-source fetch workflow and sport-ID probe | done | `arena-f68c2262` | `.github/workflows/fetch-raw.yml`, `.gitignore` |
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

- 2026-10-26: Built and committed the source-first primary dashboard. No unsupported recommendation is published.
- 2026-10-26: PR for earlier supplementary work #4 was merged and its Pages run was recorded by the concurrent integration: https://github.com/karagemop466-tech/Olbg8/actions/runs/40397819651
- 2026-10-26: Opened PR [#8](https://github.com/karagemop466-tech/Olbg8/pull/8) from `arena/40c30722-olbg8`; merge and Pages deployment status will be recorded here after release.
