# OLBG Research Desk

A clean, source-first static GitHub Pages dashboard for the requested OLBG sports:

- Golf
- Volleyball
- Rugby Union
- Cricket
- Snooker
- Darts
- Baseball
- Gaelic Sports
- Greyhounds
- Tennis
- Motor Racing
- Handball
- Ice Hockey
- Basketball
- Rugby League

## What is in the primary site

- **Overview** — executive summary, publication status, sport coverage ledger, and the next captured listings.
- **Matches** — searchable table of every in-scope OLBG listing in the capture, with the OLBG selection, displayed price, our research line where one was supportable, confidence, and both source paths.
- **Picks** — the only recommendation page. It currently publishes zero actionable picks. Four full prose research briefs are retained as explicitly withheld notes because the capture did not clear every publication gate.
- **One page per sport** — a clean category view for all 15 requested sports, including categories with no OLBG listing in this capture.
- **Flagged for Review** — source gaps, missing event crosswalks, incomplete injury/availability checks, scope interpretation, and every flagged row.
- **Sources** — official-source register and OLBG hub links.
- **Methodology & markets** — OLBG reverse-engineering notes, market definitions, line calculation, confidence bands, and publication gates.

## Snapshot

The included capture was taken **2026-10-26 05:18:26 UTC**. It contains **116 in-scope OLBG listings** after excluding one Hurling listing because Hurling was not requested. Four rows were identity-matched to an official event source and 17 rows have a research line from captured official inputs. No actionable pick is published.

Those zeroes are deliberate. OLBG's sport pages expose events with tipster activity, not a complete fixture database. An official calendar or standings page is not treated as proof of an exact match, lineup, injury status, or available market. Blank values remain blank and are flagged instead of being inferred.

## Run locally

The primary site is static and has no build dependency:

```bash
python3 scripts/build_dashboard.py
python3 scripts/test_site.py
python3 -m http.server 8000 --bind 0.0.0.0
```

Open `http://localhost:8000/` locally. The browser must load the JSON over HTTP; opening the HTML directly as a `file://` URL will block the data fetch in most browsers.

The data transform is deterministic and uses these committed capture files:

- `data/olbg-capture.json` — OLBG event feed and displayed selection/price snapshot.
- `data/line-research.json` — research lines and official-source checks.
- `data/official-evidence.json` — captured official evidence payload.
- `data/publication-gate.json` — publication decision record.
- `data/dashboard.json` — derived payload consumed by the site.
- `data/sources.json` — official-source register.

## Verification standard

A row must have an OLBG event link and an official source reference. An exact event crosswalk, current relevant statistics, a material availability/injury check, a defensible in-range line, and unique written reasoning are all required before a recommendation can appear on **Picks**. High-confidence prose must be unique, natural, at least 30 words, and must not claim facts that lack an official source. The repository's `COORDINATION.md` records source checks, irregularities, integration, and release status.

This is independent research, not OLBG advice and not a guarantee. Check the linked source and current market before relying on any information. Only bet where lawful and only what you can afford to lose.

## GitHub Pages

The repository is configured for Pages from `main` at <https://karagemop466-tech.github.io/Olbg8/>. The workflow validates the committed primary site and deploys the repository root after changes reach `main`.

The older `research-desk/` directory is retained as a supplementary audit artifact from earlier repository work. It is not the primary navigation or publication payload.
