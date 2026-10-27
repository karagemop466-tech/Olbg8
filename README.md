# OLBG multi-sport line desk

An independent, source-linked research desk for the fifteen OLBG sports in scope:

Golf · Volleyball · Rugby Union · Cricket · Snooker · Darts · Baseball · Gaelic Sports ·
Greyhounds · Tennis · Motor Racing · Handball · Ice Hockey · Basketball · Rugby League

The site lives at <https://karagemop466-tech.github.io/Olbg8/>.

## What it does

1. **Captures the live OLBG board.** Fifteen sport feeds, every competition page linked from them, and the full market board of each event are read from OLBG's server-rendered HTML: event name, ISO start time, selection, market, price in decimal/fractional/American, tip record and consensus.
2. **Prices every market itself.** The bookmaker margin is removed with the power method to give a fair probability and a fair price for each selection, then nudged by official form where an official competition feed exists.
3. **Publishes picks.** Between five and seven picks per sport, restricted to fair prices between -250 and +10,000, each with a confidence band, an original write-up of at least thirty words, and links to the OLBG market and the official source.
4. **Flags what it cannot support.** Missing listings, missing crosswalks, blocked official sources and thin coverage are listed on **Flagged for Review** rather than smoothed away.

## Pages

| Page | Contents |
|---|---|
| `index.html` | Executive summary, highest-confidence picks, top write-ups, sport coverage grid |
| `picks.html` | Every pick: summary table plus the full write-up cards, grouped by sport |
| `matches.html` | Every captured event with market counts and source links (searchable) |
| `sports/<sport>.html` | Per-sport picks and the full event table |
| `sources.html` | Official source register per sport with capture status |
| `methodology.html` | De-vigging maths, confidence bands, price window, editorial rules |
| `flagged.html` | Everything unconfirmed, unavailable or below target |

## Repository layout

```
pipeline/
  collect.py          fetch OLBG + official sources (runs on a GitHub Actions runner)
  parse_olbg.py       sport, competition and feed rows -> out/olbg_feed.json
  parse_events.py     event pages -> full market boards -> out/olbg_events.json
  extract_official.py official payloads -> out/official_facts.json
  pricing.py          margin removal, fair prices, confidence bands, cover maths
  write.py            prediction prose assembled only from captured fields
  build.py            crosswalk, line origination, pick selection -> data/desk.json
  site.py             static HTML generation
  check.py            fail-closed audit of every published row and local link
  tests/              unit tests for the maths and the prose guard rails
data/desk.json        the payload the site is generated from
pipeline/out/         parsed captures and the capture manifest (URLs + SHA-256)
pipeline/raw/         raw captures, git-ignored, uploaded as a workflow artifact
```

## Running it

```bash
cd pipeline
python3 collect.py --mode harvest      # needs outbound internet
python3 parse_olbg.py
python3 parse_events.py
python3 extract_official.py
python3 build.py
cd .. && python3 pipeline/site.py && python3 pipeline/check.py
python3 -m unittest discover -s pipeline/tests -v
```

`.github/workflows/refresh.yml` runs that chain daily on `main` and commits the refreshed payload and site.
`.github/workflows/quality.yml` re-verifies every push and pull request.

## Editorial rules

- A price is only published if it was read from the captured OLBG board; `check.py` compares each pick against the capture and fails the build on a mismatch.
- A sentence about form, a record or a stat is only generated when the field exists in an official payload. Missing fields produce silence, not guesses.
- Market-anchored lines are labelled as such. They are de-margined prices, not independent ratings.
- The words *model* and *verified* never appear in published prose; both are internal concepts.
- No tipster's reasoning is reused. Write-ups are assembled from captured numbers.

## Honest limitations

- OLBG lists events that carry tipster activity, not every fixture in world sport. Sports with no listing at capture time produce no picks and are flagged.
- Official machine-readable feeds were reachable for MLB, NHL and Formula 1. Other sports are priced from the de-margined board and flagged accordingly.
- Prices move constantly. The linked OLBG market is the authority, not this page.

This is research, not betting advice. No outcome is guaranteed. Bet only where lawful and only what you can afford to lose.
