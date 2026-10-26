# COORDINATION.md — shared task board

Session ID: `arena-33ef165e`
Branch: `arena/33ef165e-olbg8` (platform-fixed branch; this session cannot create or push other branches)
Last updated: 2026-10-26

## Rules of engagement (this repo)

- This board is the shared task board. Claim a task by adding your session ID + file scope below, then commit & push immediately.
- Never edit files claimed by another session; log a request here instead.
- Shared outputs (`data/*.json`, `site/index.html`, navigation) are owned by the final integration session.
- `needs review` = item published on the site's **Flagged for Review** page; it does not block other work.
- Stale claims (>60 min with no commits) may be taken over, with a handoff note in the log.
- Platform constraint: the Arena session is pinned to `arena/33ef165e-olbg8`; PRs are opened **from** that branch into `main` and merged with `gh pr merge <n> --merge`.

## Task board

| # | Task | Status | Owner | File scope | Notes |
|---|------|--------|-------|------------|-------|
| 1 | Repo audit + board creation | done | arena-33ef165e | `COORDINATION.md`, `README.md` | Initial commit contained only `# Olbg8` |
| 2 | OLBG reverse engineering: discover per-sport upcoming-match endpoints and market structure | in progress | arena-33ef165e | `research/olbg-endpoints.md`, `scripts/fetch_olbg.py`, `data/raw/olbg/*` | Must record exact URLs + fetch date for every row |
| 3 | Official-source verification: fixtures, form, recent results, stats, injuries | unclaimed | arena-33ef165e | `research/official-sources.md`, `data/raw/official/*` | One official link per verified field, else blank + flag |
| 4 | Pricing engine: originate in-house lines for every covered event (win / handicap / total where supportable) | unclaimed | arena-33ef165e | `scripts/price.py`, `research/pricing-method.md`, `data/prices.json` | Document math; never present derived lines as market odds |
| 5 | Written predictions: 5 highest-confidence picks per sport, >=30 words, low/medium/high confidence | unclaimed | arena-33ef165e | `data/predictions.json`, `research/prediction-notes.md` | Only use verified facts; no invented injuries |
| 6 | Static dashboard site: landing executive summary + per-sport subpages + tables + Flagged for Review | unclaimed | arena-33ef165e | `site/**`, `scripts/build_site.py` | Clean simple dashboard; every row has source link |
| 7 | Integration verification: line-by-line re-verify, internal link check, build check | unclaimed | arena-33ef165e | `research/verification.md`, `scripts/check_site.py` | Any unresolved value => blank + flagged |
| 8 | PR from `arena/33ef165e-olbg8` -> `main`, merge, enable + confirm GitHub Pages, record links | unclaimed | arena-33ef165e | `COORDINATION.md` (log section) | Retry build/deploy until live |

## Session log

- 2026-10-26 — `arena-33ef165e`: repo audit complete; only `README.md` existed (7 bytes). Board created and tasks 1–2 claimed. Pushing claim immediately.
- 2026-10-26 — `arena-33ef165e`: no other sessions had claimed any scope at claim time (no `COORDINATION.md` existed, single initial commit, no remote branches other than `main`).
