# OLBG desk — 27 October 2026

A clean, source-first static GitHub Pages dashboard that reverse-engineers OLBG's event feeds, originates an independent line for every priced market, and publishes fully written picks for exactly these 15 sports:

Golf · Volleyball · Rugby Union · Cricket · Snooker · Darts · Baseball · Gaelic Sports · Greyhounds · Tennis · Motor Racing · Handball · Ice Hockey · Basketball · Rugby League

Live site: <https://karagemop466-tech.github.io/Olbg8/> (Pages builds from `main` at the repository root).

## What is on the site

| Page | Contents |
| --- | --- |
| [Overview](index.html) | Executive summary, the highest-confidence selections, a coverage ledger for all 15 sports, and the next upcoming OLBG events. An obvious link leads to the picks. |
| [Today's picks](picks.html) | The recommendation page. Every pick names its selection and market, shows the OLBG price next to our fair line, carries a low / medium / high confidence badge, and has a unique 100+ word prediction with official facts and links. |
| [Our lines](lines.html) | Every priced selection in every captured OLBG market — 2,393 originated lines in this snapshot — plus blank rows for markets OLBG published without prices. |
| [Matches](matches.html) | The full OLBG event inventory with start times, market counts, official crosswalk level, independent totals where official scoring feeds allowed them, and source links. |
| [One page per sport](sports/tennis.html) | 15 category pages that repeat the picks, lines, matches, official sources and flags for that sport. |
| [Sources](sources.html) | The official / discovery / supplemental source register, each with its capture status, byte count, and link. |
| [Methodology](methodology.html) | The OLBG `__data.json` reverse-engineering, the de-vig + consensus + official-strength pricing formula, confidence rules, market coverage and verification steps. |
| [Flagged for review](flagged.html) | Every irregularity, missing official value, blocked endpoint, time discrepancy, short-priced exclusion and coverage gap, each with source links. |

## Snapshot at a glance

- Captured **2026-10-27 06:17:39 UTC** by [the hosted collector](.github/workflows/collect-20261027.yml): 16 OLBG sport hubs, 16 “All Events” pages, **201** individual event payloads and **65** official source endpoints (47 returned HTTP 200; the rest are published with their failure status).
- **596** event markets decoded; **592** had displayed prices, producing **2,393** originated lines. Four Greyhounds race rows had no displayed prices at all — they are published as blank, flagged rows rather than guessed.
- **180** upcoming events; **92** start on the capture date (UTC).
- **63** unique written picks across **13** sports: 11 high confidence, 49 medium, 3 low. All sit inside the requested **−250 to +10000** band. Twelve sports reached the five-pick target; Baseball has three (only one upcoming MLB game with three markets), Motor Racing has five across two outright/qualifying events, and Snooker and Greyhounds have none because OLBG published no tipped Snooker event and no priced Greyhounds selection.
- **652** flagged items are published on the review page. Nothing unverified was silently filled in.

## How OLBG was reverse-engineered

OLBG sport hubs and event pages are SvelteKit routes. Appending `/__data.json` to a hub URL (e.g. `https://www.olbg.com/betting-tips/Tennis/3/__data.json`) returns the flattened server payload; the same endpoint on an event URL returns the full `event` object, `eventSchema` JSON-LD, every market, every selection, decimal/American/fractional prices, tip counts, confidence values and start time. The collector decodes those flattened arrays and writes the exact bytes to `data/capture-20261027/`, so the derived dataset is reproducible from committed raw files.

## Where the facts come from

- **Market facts** (event names, start times, market names, selections, displayed prices, tip counts) — the captured OLBG `__data.json` payloads. Every row links to its OLBG event page.
- **Official facts** (fixture identity, standings, rankings, results, calendars, tournament details) — official governing-body / league endpoints captured at the same time: NHL, MLB StatsAPI, WTA (rankings, tournaments and 2026 draw pages), ATP (link only; HTTP 403 at capture), ICC, Cricket Australia, CEV, EHF Champions League, EPCR, LNR Pro D2, GAA, GBGB, PDC, WST, PGA TOUR, LPGA, Formula 1, NBA, EuroLeague (HTTP 429/403 link only), NRL, Super League. Event-specific NHL game centres and MLB gameday pages are linked directly.
- **Our calculations** (fair prices, edges, confidence, independent totals) — transparent formulas in [methodology.html](methodology.html), computed from the two source groups above. They are research lines, not bookmaker offers.

OLBG is discovery / market context only. An official calendar or standings page is **not** treated as proof of an exact match, lineup, injury status or price. Where an official event-level crosswalk, an injury sheet or a displayed price is missing, the field is blank and the gap appears on [Flagged for review](flagged.html).

## Verification standard

`scripts/verify_desk.py` fails the build unless:

1. Every event, market, selection, pick and flag has an official-source link and an OLBG link; **every generated table row** carries an official link.
2. Every priced market's fair probabilities sum to 100% and every selection has an originated American price.
3. Every prediction is unique, at least 30 words, names its selection, states its confidence, avoids the words “model” and “verified”, and sits inside −250..+10000.
4. Every pick's prose appears on both the picks page and its sport page; every shortfall and empty sport is flagged.
5. Every internal link resolves, the executive summary and flagged page exist, unpriced markets are published as blank rows, and the dataset is a deterministic function of the committed snapshot.

Additional legacy checks (`scripts/test_site.py`) still validate the older source-first audit payload retained under `data/dashboard.json`.

## Run locally

```bash
python3 scripts/desk_data.py      # rebuild data/desk-20261027.json from the committed capture
python3 scripts/render_desk.py    # rebuild all root pages, sport pages, CSS and JS
python3 scripts/verify_desk.py    # fail-closed verification
python3 -m http.server 8000 --bind 0.0.0.0
```

The site is plain HTML; JavaScript only adds table filtering. No runtime data fetch is required. Opening `index.html` directly also works.

## Repository layout

- `data/capture-20261027/` — committed raw OLBG hub / all-events / event `__data.json` payloads, official JSON and text snapshots, and `manifest.json` with capture times and HTTP statuses.
- `data/desk-20261027.json` — the derived dataset (events, lines, picks, flags, sources, methodology).
- `scripts/collect_20261027.py`, `.github/workflows/collect-20261027.yml` — hosted bulk collector.
- `scripts/desk_data.py`, `scripts/render_desk.py`, `scripts/verify_desk.py` — deterministic build and verification.
- `data/dashboard.json`, `data/olbg-capture.json`, `data/line-research.json`, `data/official-evidence.json`, `data/publication-gate.json`, `data/sources.json` — legacy 2026-10-26 audit artifacts, retained unchanged.
- `previous-desk/` — static archive of the 05:26 UTC dashboard that concurrent sessions had merged to `main` before this integration; its data files and build scripts remain committed under `data/`, `scripts/` and `pipeline/`.
- `research-desk/`, `evidence-lab/`, `board/`, `current/` — supplementary audit artifacts from earlier sessions, linked from the footer or archived desk but not part of primary navigation. Their CI gates (`scripts/test_line_desk.py`) are retained in the quality workflow; root-page generators from those pipelines no longer overwrite the integrated primary site (see `refresh.yml`).
- `pricing.html` — retained legacy pricing explainer with a banner pointing at the current [methodology](methodology.html) and [lines](lines.html).
- `COORDINATION.md` — shared task claims, source checks, irregularities, and PR / merge / deployment record.

This is independent research, not OLBG advice and not a guarantee. Check the linked official source and the live market before relying on any information. Only bet where lawful and only what you can afford to lose.
