# OLBG Predictions Project — Coordination Board

## Session information

- **Session ID:** `arena-8bf2f7eb` (Arena Agent Mode, branch `arena/8bf2f7eb-olbg8`)
- **Started:** 2026-10-26 (UTC)
- **Branch policy:** Arena requires all work on the fixed branch `arena/8bf2f7eb-olbg8`. Session-scoped branches from the generic coordination protocol are not permitted on this platform, so this session claims and executes all scopes below on the fixed branch and performs final integration itself.
- **Network note:** Direct egress is limited to GitHub/PyPI/npm hosts. The platform fetch tool can reach OLBG.com and external news/official sites (e.g. BBC Sport); reachability of each source is tested before use. Anything that cannot be confirmed against an official source is left blank and listed on the Flagged for Review page. No values are inferred.

## Task board

| # | Task | Status | Owner | File scope |
|---|------|--------|-------|------------|
| 1 | Reverse-engineer OLBG sport hubs and enumerate upcoming events for the 15 covered sports | in progress | arena-8bf2f7eb | `data/olbg/`, `data/events.json` |
| 2 | Originate lines (fair/no-vig probabilities, moneyline, handicap, totals where markets exist) for every enumerated event | unclaimed | arena-8bf2f7eb | `data/lines/`, `data/events.json` |
| 3 | Verify match facts (form, H2H, stats, injuries) from official sources; attach source links; flag unverified rows | unclaimed | arena-8bf2f7eb | `data/verification.md`, `data/flags.json` |
| 4 | Write 5 unique high-confidence predictions per sport (30+ words each, non-repetitive, no forbidden words) | unclaimed | arena-8bf2f7eb | `data/predictions/` |
| 5 | Build static GitHub Pages dashboard (executive summary, per-sport pages, tables, flagged page, methodology) | unclaimed | arena-8bf2f7eb | `site/` |
| 6 | Integration: re-verify combined data, check build/links, PR to main, merge, enable Pages, confirm deploy | unclaimed | arena-8bf2f7eb | repo root, GitHub settings |

## Handoff log

- 2026-10-26: Session `arena-8bf2f7eb` started; repo contained only initial README commit. Claimed all tasks (no other sessions present). Task 1 in progress.

## Verification rules (project-wide)

1. Every table row carries a source link to an official or primary source (OLBG event page for market data; official league/club/body or major reputable outlet for facts).
2. Values not confirmable from a source are stored as blank/null with an entry in `data/flags.json` and shown on the Flagged for Review page.
3. No inferred or hallucinated names, odds, stats, or injury claims.
4. Forbidden words inside published prediction prose: "model", "verified" (internal use only).
5. High-confidence band: priced probability > 70% with pick price inside -250 … +10000 (American odds).
