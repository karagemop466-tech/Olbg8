# OLBG Research Desk

An independent, evidence-led GitHub Pages research dashboard for **15 requested sports**, including both Gaelic Football and Hurling under Gaelic Sports.

**Website:** https://karagemop466-tech.github.io/Olbg8/

## Current status — 2026-10-26 inspection

- 116 **observed OLBG event entries**, transcribed from inspected public-page extracts, with source links and raw display times. This is **not an exhaustive list**.
- 15 category pages, executive summary, searchable event inventory, Flagged for Review, pricing methodology and collection monitor.
- Limited official corroboration from NHL, MLB, ICC, EHF, F1 and LPGA. Evidence scope is recorded per entry; official-directory links are explicitly not fixture confirmation.
- **Zero published picks / zero originated production lines.** Official historical ingestion, fitted parameters, backtests, complete event/market joining and unique prediction production remain unfinished. The daily five-per-sport target has not been met. Mathematical prototypes must not be represented as calibrated forecasts.
- Unknown values stay `null` in JSON / blank in tables. Tipster support is not win probability. Market benchmarks are clearly separated from independent fair lines.

## Run locally

Requires Python 3.11+. No dependencies, credentials, paid feed, or manual entry needed to view/build the snapshot.

```sh
python -m unittest discover -s tests -v
python -m scripts.build
python -m scripts.check
python -m http.server 8080 --bind 0.0.0.0 --directory _site
```

The static app uses relative paths and supports the `/Olbg8/` project path. Every requested sport has a dedicated HTML page. JavaScript only enhances filtering; the data and navigation render without it.

## Collection and deployment

`.github/workflows/pages.yml` tests pushes and PRs. Main and daily scheduled runs attempt public category discovery, build, and deploy via GitHub Pages Actions. Schedule: **05:17 UTC**, subject to GitHub scheduling delays. The production Pages source must be set to **GitHub Actions**.

`python -m scripts.collect` respects robots.txt and stops at failed permissions or access challenges. It stores category results in `data/collection-status.json`, and successful HTML snapshots (hashed) in ignored `data/collection/`. CI retains the audit artifacts for seven days. New labels appear in the collection log only; they cannot silently become confirmed fixtures or picks. No undocumented endpoint, anti-bot bypass, login or betting action is used.

The repository sandbox cannot connect directly to OLBG, so its initial collector attempt is marked blocked. Page-retrieval tools could inspect the sources; those observations are stored separately from automated collection attempts. A scheduled run **does not refresh historical official facts**, nor does it complete the autonomous prediction pipeline.

## Files

- `data/sports.json`: source registry, checked-content scope, proposed pricing and input requirements.
- `data/observations.json`: dated event observations, scoped official corroboration, blanks and flags.
- `data/audit.json`: audit boundary, source URLs and unresolved delivery requirements.
- `data/picks.json`: empty; release gate fails closed until production adapters exist.
- `scripts/seed.py`: reproducible transcription of observations from the 2026-10-26 inspection, **not a current data fetcher**. Do not run it as a refresh job.
- `scripts/pricing.py`: tested odds/settlement math, IID first-to, regulation Poisson and full-field ranking research kernels; **not fitted sport adapters**.
- `scripts/policy.py`: editorial/data checks plus unconditional production-adapter blocker.
- `scripts/build.py`: dependency-free static generator; output `_site/` is ignored.
- `scripts/check.py`, `tests/`: local links, Pages path, source-link presence, withholding and mathematical tests.
- `COORDINATION.md`: ownership, verification, publication log and follow-up gaps.

## Safety and interpretation

No guarantee of outcomes or returns. Use the official sources for current information, and observe applicable local laws and legal age requirements. This project is not affiliated with OLBG and does not place bets. Linking a source is not the same as proving a claim; read the row-level evidence notes.
