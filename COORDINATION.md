# COORDINATION.md — shared task board

Repo: `karagemop466-tech/Olbg8` · Site: https://karagemop466-tech.github.io/Olbg8/ · Pages source: `main` / root (legacy build)

Last updated: 2026-10-26 (UTC)

## Rules in force

1. Read this file before starting any task. Claim a task by adding your session ID + file scope, then commit and push the claim immediately.
2. Never start a task another session has claimed and not released. Scopes must not overlap.
3. Each session works on its own branch (`session-<id>/<task>`) and edits only files in its claimed scope, except the integration session (final merge/verify/publish).
4. If you need a change in a file owned by another session, log a REQUEST here instead of editing it.
5. Small, frequent commits. `git pull --rebase` before every push. Do not discard another session's work to resolve a conflict — stop, resolve, and log it.
6. When a task finishes: record sources, verification performed, and irregularities here, then mark it `done`.
7. `needs review` = published on the site's **Flagged for Review** page; it does not block anything.
8. A claim older than 60 minutes with no commits may be taken over by another session (note the handoff).
9. Shared outputs (`data/*.json`, `index.html`, navigation) are changed only by the integration session after other tasks are done.
10. Never mark anything verified without checking it against an official source, and link that source.

## Sessions

| Session | Branch | Role | Notes |
|---|---|---|---|
| `arena-dd075b6d` | `arena/dd075b6d-olbg8` | Collection + pricing + writing + integration (this session) | Started 2026-10-26T20:31Z from `797e50d` |
| `scraper-bot` | n/a (GitHub Actions) | Automated OLBG collection runner | `.github/workflows/scrape.yml` — fetches OLBG, commits `data/olbg/*.json` |

## Task board

| # | Task | Status | Owner | File scope |
|---|---|---|---|---|
| T1 | Reverse-engineer OLBG event taxonomy (sport → competition → event URLs) | in progress | `arena-dd075b6d` | `scripts/olbg_collect.py`, `.github/workflows/scrape.yml`, `data/olbg/**` |
| T2 | Collect upcoming matches for the 15 covered sports | in progress | `arena-dd075b6d` | `data/olbg/**` |
| T3 | Pricing methodology for all 15 sports (originate lines, all market types) | unclaimed | — | `docs/methodology/*`, `scripts/price.py` |
| T4 | Pick selection + confidence grading (low/med/high) + odds band check | unclaimed | — | `data/picks.json` |
| T5 | Written predictions (≥30 words, unique, verified facts, sourced) | unclaimed | — | `data/picks.json` |
| T6 | Static site: landing dashboard, 15 sport pages, exec summary, methodology, flagged page | unclaimed | — | `site/**`, `index.html`, `assets/**` |
| T7 | Link + data verification pass (every row sourced or explicitly flagged) | unclaimed | — | `scripts/verify.py`, `data/flagged.json` |
| T8 | Integration: merge, re-verify, build check, PR to `main`, merge, confirm Pages deploy | unclaimed | — | repo-wide |

## Log

- **2026-10-26T20:31Z** `arena-dd075b6d` — Repo cloned/expanded from empty initial commit (`797e50d`, only `README.md`). No prior data, no prior site, no prior coordination board: created this board. Sandbox egress is allowlisted to GitHub/PyPI only, and `www.olbg.com` is unreachable from the agent sandbox, so live OLBG collection is delegated to a GitHub Actions job (runners have open egress; verified with a probe run, `40396544414`, success). Scraper commits raw collection output to the branch; the agent then parses, prices, writes, and builds the site locally.
- **2026-10-26T20:35Z** `arena-dd075b6d` — OLBG sport IDs confirmed from `https://www.olbg.com/sitemap-betting-tips.xml`: Tennis 3, Basketball 4, Golf 5, Cricket 7, Snooker 8, Rugby Union 9, Rugby League 10, Baseball 12, Ice Hockey 13, Motor Racing 14, Darts 15, Handball 20, Volleyball 21, Gaelic Football 25, Greyhounds 28. Note: OLBG's taxonomy has no "Gaelic Sports" node; the Gaelic node is `Gaelic_Football/25` — mapping logged for review on the flagged page.
