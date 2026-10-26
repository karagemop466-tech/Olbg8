# OLBG Research Desk

A static, audit-first dashboard for monitoring the 15 requested OLBG sports. It deliberately separates **OLBG community listings** from **independently originated picks**.

## Current status

The 26 October 2026 snapshot contains source-linked OLBG observations. No prediction is published because the official event, roster/injury inputs, current odds, and independent fair line were not all confirmed. Missing facts remain blank and appear on **Flagged for Review**.

## Local use

```bash
python scripts/build.py
python scripts/check.py
python -m http.server 8000
```

Open `http://localhost:8000/`. The site uses plain HTML, CSS, JavaScript, and JSON with no build dependency.

## Data contract

- `data/sports.json` — coverage, OLBG category links, markets, and sport-specific pricing approach.
- `data/events.json` — timestamped discovery ledger. A row is not a recommendation.
- `scripts/build.py` — generates the landing page, methodology, review page, and 15 sport pages.
- `scripts/check.py` — validates required fields, source domains, sport coverage, generated pages, and local links.

## Publication controls

A written pick may be added only when:

1. The event and start time are confirmed by the organizer, league, or governing body.
2. Referenced form, statistics, lineups, and injuries each have an official source.
3. A reproducible fair probability and fair American price are recorded.
4. The probability is at least 70%, market odds are between −250 and +10000, and uncertainty testing does not erase the edge.
5. The prediction is at least 30 words and clearly names the selection and market.

Community support percentages are retained only as OLBG observations; they are not treated as probabilities or as this project's picks.

## GitHub Pages

The repository is configured for Pages from `main` at <https://karagemop466-tech.github.io/Olbg8/>. GitHub's Pages deployment runs after changes reach `main`.
