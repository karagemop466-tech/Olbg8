# COORDINATION.md — shared task board

Last updated: 2026-10-26 20:33 UTC by session `session-10e556c5`.

## Platform constraint (read first)

This Arena session is pinned to the single branch `arena/10e556c5-olbg8`. The environment
does not permit creating, switching to, or pushing any other branch, so the requested
`session-<id>/<task>` branches cannot be created here. All work below is claimed on the
pinned branch, with non-overlapping file scopes. Sessions should pull --rebase before
pushing and keep claims to the file scopes recorded below.

Session ID: `session-10e556c5`
Session branch: `arena/10e556c5-olbg8`
Claim timestamp: 2026-10-26 20:33 UTC

## Task board

| # | Task | Status | Owner | File scope | Notes |
|---|---|---|---|---|---|
| 1 | Repository audit and source inventory | in progress | session-10e556c5 | COORDINATION.md, README.md, docs/repo-audit.md | Initial repo has only README.md ("# OLBG"). |
| 2 | Reverse engineer OLBG upcoming-match/market surfaces | in progress | session-10e556c5 | docs/olbg-reverse-engineering.md, scripts/olbg_probe.* | Record endpoints actually reachable, HTTP status, and evidence. |
| 3 | Official-source research and data ledger (15 sports) | in progress | session-10e556c5 | data/*.json, docs/sources.md | Every row requires an official-source link; unverified cells remain blank. |
| 4 | Line origination and confidence methodology | in progress | session-10e556c5 | docs/methodology.md, scripts/originate_lines.py | All derived values must be reproducible from documented inputs. |
| 5 | Written predictions (5–10 per sport) | in progress | session-10e556c5 | data/predictions.json | Only high-confidence picks get 30+ word unique writeups. |
| 6 | Static dashboard site (landing + category subpages + tables) | in progress | session-10e556c5 | site/**, index.html, assets/**, .github/workflows/pages.yml | Plain static HTML/CSS/JS; no external runtime dependencies. |
| 7 | Verification, broken-link check, flagged-review page | in progress | session-10e556c5 | docs/verification.md, scripts/verify_site.py, data/flagged.json | Line-by-line source-link check; no inferred values. |
| 8 | Final integration, PR, merge, Pages deploy confirmation | in progress | session-10e556c5 | COORDINATION.md, docs/deploy-log.md | PR from `arena/10e556c5-olbg8` to `main`; merge after successful build. |

## Handoff / conflict log

- 2026-10-26 20:33 UTC — session `session-10e556c5` claimed tasks 1–8 on the pinned
  branch. No other claims existed in the repository at claim time.
- To be completed at task close: sources used, verification performed, irregularities,
  PR link, merge result, and Pages deployment status.

## Rules for other sessions

1. Do not edit files inside an `in progress` scope above without logging a request here.
2. Shared outputs (`index.html`, site navigation, combined data) are integrated only by
   the final integration session (task 8) after all other tasks finish.
3. `git pull --rebase` before every push. On conflict, stop, preserve the other session's
   work, resolve, and log the conflict here.
4. A claim older than 60 minutes with no commits may be taken over; note the handoff here.
5. Mark a row `done` only after recording its sources, verification, and irregularities.
