# OLBG multi-sport line desk

An independent price desk for the fifteen OLBG sports requested for this project.
It reverse-engineers how OLBG publishes fixtures and market data, originates its
own line for every captured market, grades each selection, and writes a
prediction for every published pick.

**Live site:** <https://karagemop466-tech.github.io/Olbg8/>

## Pages

| Page | What it answers |
|---|---|
| **Overview** (`index.html`) | Executive summary: the highest-graded picks, headline counts, coverage by sport. |
| **Picks** (`picks.html`) | Every published pick: selection, OLBG price, our line, confidence, written prediction, sources. Filterable. |
| **All matches** (`matches.html`) | Every captured event and market with market price, de-vigged probability, our line and the edge. |
| **Sports** (`sports/*.html`) | One page per requested sport: its picks, then its captured events and market tables. |
| **Flagged for review** (`flagged.html`) | Sports with no market, sports priced from market data only, row-level gaps. |
| **Sources** (`sources.html`) | The source register with every primary feed and OLBG category used. |
| **Method** (`methodology.html`) | How a price is produced, what the grades mean, what the site will not do. |

## Current snapshot

* **190 OLBG events · 223 markets · 257 priced selections** across **13 of the 15** requested sports.
* **63 published picks** — 3 high, 25 medium, 35 low — each with a prediction of at least 30 words.
* Snooker and Greyhounds exposed no market row at capture time and are published as gaps, not filled in.
* Primary data covered 28 tennis matches, 8 basketball games, 7 ice-hockey games and 2 baseball games.

## How the data is produced

OLBG category pages are JavaScript shells. The rows come from the route's SvelteKit
hydration payload (`/betting-tips/<Sport>/<id>/__data.json`), a flattened `devalue`
array that the collector decodes. It then walks category → competition → event pages.

```
scripts/collect_olbg.py       OLBG hydration decoder + inventory walk
scripts/collect_official.py   probe and capture of primary league/tour feeds
scripts/pricing_core.py       implied probability, Shin de-vig, log5, grading
scripts/build_dashboard.py    events -> markets -> lines -> picks -> dashboard.json
scripts/predictions.py        written prediction for every published pick
scripts/test_site.py          fail-closed validation of the published payload
```

```bash
python3 scripts/build_dashboard.py
python3 scripts/test_site.py
python3 -m http.server 8000 --bind 0.0.0.0   # then open http://localhost:8000/
```

The browser loads `data/dashboard.json` over HTTP, so serve the folder rather than
opening the HTML files directly.

Network work runs on GitHub Actions runners because the agent sandbox only reaches
GitHub, npm and PyPI: `.github/workflows/olbg-collect.yml` captures OLBG,
`.github/workflows/official-collect.yml` captures the primary feeds.

## Pricing method

A captured decimal price becomes an implied probability. OLBG's public payload
exposes **one price per market**, not both sides, so the margin is removed with a
published allowance by market type (4% win markets, 4.5% handicaps and totals, 12%
outrights) rather than measured. Where a primary feed gives an independent
measurement — log5 on MLB winning percentage with a home-field term, on NHL points
percentage with home ice, on NBA win percentage with home court, or a logistic on
ATP/WTA ranking points — that estimate is blended 60/40 with the market figure and
the disagreement is reported as the edge. The published line is the fair odds of
the blended probability, with no margin added.

**Confidence** is probability-based: `high` ≥70% inside the requested −250 to
+10000 band with primary data or a community majority behind it, `medium` 55–70%,
`low` everything else (published only where a sport would otherwise be blank).

## Verification

`scripts/test_site.py` fails the build if a pick lacks a price, a grade, a ≥30-word
prediction or an OLBG link, if any prediction contains a blank value or the internal
wording the brief prohibits, or if any local link breaks. The build is deterministic
and CI fails if the committed `data/dashboard.json` differs from a rebuild.

Missing data stays missing: a sport with no OLBG market is published on **Flagged
for review** rather than filled with an invented fixture.

## Repository layout

```
data/olbg/         captured OLBG markets, per sport, plus markets.json and the probe log
data/official/     captured primary feeds and the endpoint probe
data/dashboard.json  derived payload rendered by the site
assets/            styles.css, app.js, favicon
sports/            fifteen sport pages
desk-v1/           the previous root desk, archived byte-for-byte and still browsable
board/ current/ evidence-lab/ research-desk/   earlier sessions' desks, untouched
```

## Provenance and scope

Every pick carries the OLBG market URL it was priced from and, on the primary route,
the league or tour URL that supplied its facts. OLBG is a market source, not a
governing body, and is not responsible for any claim made here. Independent
research, not betting advice. 18+. Bet only what you can afford to lose.
