# OLBG Match Research Dashboard

A static, source-first GitHub Pages dashboard for researching OLBG-listed events across 15 requested sports. It separates OLBG listing sightings from independently confirmed fixtures, sourced market prices, original lines and fully reasoned predictions.

## What is published now

- An executive summary and linked page for each requested sport.
- A dated, explicitly non-exhaustive snapshot of listing items visible on OLBG's betting-tips page on **2026-10-26 UTC**.
- OLBG source links and primary-organization schedule starting points on each sport page.
- Empty selection, line, confidence and analysis fields until event-specific supporting sources have been checked.
- A **Flagged for Review** page explaining coverage, source, pricing and verification gaps.

This is a research scaffold, not a complete or automatically refreshed feed. The OLBG page uses relative “Today/Tomorrow” labels, and the captured entries have not been independently confirmed against the event organizers. No match predictions, prices, injury claims or official statistics are asserted. In particular, OLBG tipster counts/percentages are community consensus and are not bookmaker odds or fair probabilities.

## Run locally

Serve this directory over HTTP (browser `fetch()` does not work reliably from `file://`):

```sh
python3 -m http.server 8000
```

Then open `http://localhost:8000`. The site has no build step or third-party JavaScript dependencies.

## Data and verification conventions

- `data/sports.json`: sport directory, OLBG category URLs, and primary-organization schedule starting points. A general organization page is not event-level confirmation.
- `data/events.json`: source sightings only. It intentionally does not store selections or prices.
- `sports/*.html`: category subpages rendered from the JSON files.
- Empty cells mean “not confirmed / not entered,” not zero, no market, or no fixture.
- Before publishing a pick, record an event-specific official fixture/draw source, time zone, primary match stats and current form, independently sourced market/price and capture timestamp, line method, confidence rationale, and a unique written prediction of at least 30 words. Record an official injury/availability source only when one exists; otherwise leave that field blank and flag it.

The static pages cannot refresh themselves or scrape OLBG. New data requires a review of the live listing and primary sources, with explicit source links and a new snapshot date.
