# OLBG multi-sport line desk

An independent price desk for the fifteen OLBG sports requested for this project.
It reverse-engineers how OLBG publishes its fixture and market data, originates
its own line for every captured market, grades each selection, and writes a
prediction for every published pick.

**Live site:** <https://karagemop466-tech.github.io/Olbg8/>

## What is on the site

| Page | What it answers |
|---|---|
| **Overview** (`index.html`) | Executive summary: the highest-graded picks right now, headline counts, and coverage by sport. |
| **Picks** (`picks.html`) | Every published pick as a card: selection, OLBG price, our line, confidence, the written prediction and its sources. Filter by sport, confidence or free text. |
| **All matches** (`matches.html`) | Every captured event and market, with the market price, the de-vigged probability, our line and the edge. |
| **Sports** (`sports/*.html`) | One page per requested sport: its picks, then every captured event with its full market table. |
| **Flagged for review** (`flagged.html`) | Everything that could not be confirmed: sports with no market, sports priced from market data only, and row-level gaps. |
| **Sources** (`sources.html`) | The source register — every primary feed and OLBG category used, with links. |
| **Method** (`methodology.html`) | How a price is produced, what the confidence grades mean, and what the site deliberately does not do. |

## How the data is produced

OLBG's category pages are JavaScript shells; the fixture, market and price data
is delivered from the page's own SvelteKit hydration payload
(`/betting-tips/<Sport>/<id>/__data.json`) in a flattened `devalue` array. The
collector decodes that array, then walks category → competition → event pages.

```
scripts/collect_olbg.py       OLBG hydration decoder + inventory walk
scripts/collect_official.py   probe and capture of primary league/tour feeds
scripts/pricing_core.py       implied probability, Shin de-vig, log5, grading
scripts/build_dashboard.py    events -> markets -> lines -> picks -> dashboard.json
scripts/predictions.py        written prediction for every published pick
scripts/test_site.py          fail-closed validation of the published payload
```

Rebuild locally (no third-party dependencies):

```bash
python3 scripts/build_dashboard.py
python3 scripts/test_site.py
python3 -m http.server 8000 --bind 0.0.0.0   # then open http://localhost:8000/
```

The browser loads `data/dashboard.json` over HTTP, so serve the folder rather
than opening the HTML files directly.

### Where the network work happens

The agent sandbox can only reach GitHub, npm and PyPI, so OLBG and the league
feeds are captured by GitHub Actions runners and committed as JSON:

* `.github/workflows/olbg-collect.yml` — OLBG inventory capture (`data/olbg/`)
* `.github/workflows/official-collect.yml` — primary-source probe (`data/official/`)

## Pricing method in one paragraph

A captured decimal price is converted to an implied probability. OLBG's public
payload exposes a single price per market, so the second side of the book cannot
be measured; the margin is instead removed with a published allowance by market
type (4% win markets, 4.5% handicaps and totals, 12% outrights). Where a primary
feed gives an independent measurement — log5 on MLB winning percentage with a
home-field term, on NHL points percentage with home ice, on NBA win percentage
with home court, or a logistic on ATP/WTA ranking points — that estimate is
blended 60/40 with the market figure and the disagreement is reported as the
edge. The published line is the fair decimal odds of the blended probability, with
no margin added.

**Confidence** is about how likely the selection is to win, not how large the
edge is: `high` means our own probability is at least 70% inside the requested
−250 to +10000 band with primary data or a community majority behind it,
`medium` 55–70%, `low` everything else (published only where a sport would
otherwise be blank).

## Verification standard

* Every published pick carries the OLBG market link it was priced from.
* Every pick written on the primary route carries the primary source link.
* `scripts/test_site.py` fails the build if a pick is missing a price, a
  confidence grade, a ≥30-word prediction, an OLBG link, or if any prediction
  contains a blank value or the internal wording the brief prohibits.
* Missing data stays missing. A sport with no OLBG market is published as a gap
  on **Flagged for review**, not filled with an invented fixture.

## Current snapshot

* 190 OLBG events, 223 markets, 257 priced selections across 13 of the 15
  requested sports.
* 63 published picks: 3 high, 25 medium, 35 low.
* Snooker and Greyhounds exposed no market row in the public payload at capture
  time; both are listed as gaps with the category URL that was checked.
* Primary data covered 28 tennis matches, 8 basketball games, 7 ice-hockey games
  and 2 baseball games. Every other competition is market-anchored and says so.

## Repository layout

```
data/olbg/        captured OLBG markets (per sport + markets.json + probe log)
data/official/    captured primary feeds and the endpoint probe record
data/dashboard.json  derived payload the site renders
assets/           styles.css, app.js, favicon
sports/           fifteen sport pages
evidence-lab/     earlier session's audit artifact (not part of this desk)
research-desk/    earlier session's audit artifact (not part of this desk)
```

Independent research, not betting advice. 18+. Bet only what you can afford to
lose. OLBG is the market source; it is not a governing body and is not
responsible for any claim made here.
