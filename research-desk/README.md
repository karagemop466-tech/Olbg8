# OLBG Research Desk

Evidence-first static dashboard for the requested 15 sports. **Partial research delivery, not a completed betting service:** 74 observed event rows, 20 pages, zero publishable selections and zero operational sport-specific pricing engines. Unknown values remain null/blank. No claims of comprehensive, real-time or daily verified coverage.

## Site

https://karagemop466-tech.github.io/Olbg8/research-desk/

- Executive summary and per-sport desks
- Our picks: explicit empty state rather than invented recommendations
- Searchable event inventory with OLBG links and checked official fixture references
- Pricing lab: all 15 sport specifications and tested arithmetic (not fitted prediction systems)
- Flagged for Review: global and row-level blockers

## Build and validate

Python 3.12, no dependencies:

```sh
cd research-desk
python scripts/build.py --publish
python scripts/test_site.py
python -m http.server 8000 --bind 0.0.0.0 --directory _site
```

`data/research.json` is the curated snapshot. `data/SOURCES.md` records exactly what was inspected and its limitations. `scripts/seed.py` reproduces the initial transcription only; it does **not** refresh sources. Build validates internal links; external source availability is not exhaustively checked. All confidence/price/prediction fields are blank pending evidence, calibration and eligibility.

## Automation

The supplementary workflow builds and tests on the session branch, PRs and main. Existing legacy Pages deploys main/root, including the committed research-desk pages. Changing Pages configuration was denied (403), so no permission change is required. The daily discovery workflow runs at 06:17 UTC on the default branch and retains an unverified JSON artifact for 14 days. It reads public event links without bypassing access controls; fetch failures are recorded, and empty extraction is not treated as no fixtures. It does not update the curated site, produce verified predictions or fit pricing systems. No user credentials or manual data entry are required for those automated jobs.

## Outstanding work

Exhaust public pagination with permission and robust dynamic-page retrieval; establish absolute times/settlement rules and current offered prices; acquire official historical and current statistics/availability sources for each competition; fit and calibrate the 15 sport distributions out of sample; evaluate every observed market and publish original 30+ word sourced analysis only when eligible. The quota of five per sport is not met. Never substitute OLBG tipster support percentages for independent probabilities.
