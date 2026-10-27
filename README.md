# OLBG multi-sport desk

A static GitHub Pages site that answers three questions for fifteen OLBG sports:
**what is on, what price do we make it, and what is the written prediction.**

Live site: <https://karagemop466-tech.github.io/Olbg8/>

## The pages

| Page | What it is for |
|---|---|
| `index.html` | Executive summary: headline numbers, the highest-confidence picks, the picks inside the -250 to +10000 window, and coverage by sport. |
| `picks.html` | The written predictions. One card per pick: competition, selection, our price, our chance, confidence band and the official source. |
| `matches.html` | The full price board: all 111 OLBG listings with our money line, handicap, total and the exact reason for any blank. Filterable by sport and searchable. |
| `pricing.html` | How the number is made: the formula, the parameters per sport, and a worked example. |
| `methodology.html` | Capture rules, pricing gate, publication gate, confidence bands and the price-window rule. |
| `sources.html` | Every official page used, its URL, its capture time and how many rows depend on it. |
| `flagged.html` | Everything blank, uncertain or contradictory, including rows we refused to fill. |
| `sports/<sport>.html` | One page for each of the fifteen requested sports. |

## Capture

OLBG's fifteen requested category pages were read on **2026-10-27 05:30 UTC** at
`olbg.com/betting-tips/<Sport>/<id>`, with sport ids Tennis 3, Basketball 4, Golf 5,
Cricket 7, Snooker 8, Rugby Union 9, Rugby League 10, Baseball 12, Ice Hockey 13,
Motor Racing 14, Darts 15, Handball 20, Volleyball 21, Gaelic Football 25, Greyhounds 28.

Result: **111 listings** across 13 sports with a market. Snooker and Greyhounds displayed
*No tips found* and are reported as empty rather than padded. Gaelic Football (and Hurling,
had it been listed) is published under the single **Gaelic Sports** page the brief asked for.

## Pricing

`scripts/originate.py` turns an official season record into a price:

1. **Rating** — points/goals/runs for and against per game, straight from the official table.
2. **Shrink** — `games / (games + K)` pulls a short sample back toward the league average.
3. **Project a margin** — home rating minus away rating plus a sport-specific home edge.
4. **Probability** — normal distribution around that margin, with a sport-specific SD, and a
   draw band for handball and rugby union.
5. **Price** — fair American odds, `-100p/(1-p)` or `100(1-p)/p`.

Every match also gets a handicap line (the projected margin, rounded) and a total
(the combined scoring rate the two records imply). Tennis uses a Bradley–Terry comparison
of ranking points instead.

A match is priced **only** when both competitors appear in an official table that was
actually read. Otherwise the price stays blank and the row is flagged. That is why
10 of the 15 sports have no written prediction in this edition.

## Publication rules

- A pick is published only when our chance of the selection winning is at least 55%.
- Confidence: **High** ≥ 70%, **Medium** 62–69.9%, **Low** < 62%.
- The brief's -250 to +10000 window is enforced as a label, not a filter: picks shorter
  than -250 are shown and tagged *Outside window*, because on fair prices a 70% chance is
  -233 and the two rules otherwise overlap in a very narrow band.
- Written predictions are at least 30 words, name the selection, quote only figures from the
  official source on the card, and never mention injuries, because no team-news source was read.

## Rebuild

```bash
python3 scripts/originate.py     # ratings -> prices -> data/matches.json
python3 scripts/build_site.py    # data -> static HTML
python3 scripts/test_site.py     # pages, links, prices, predictions
python3 -m http.server 8000 --bind 0.0.0.0
```

No build dependencies. `data/ratings.json` holds every rating input together with the
official URL and capture time it came from; edit that file, not the HTML.

## Files from earlier sessions

`research-desk/` and `evidence-lab/` are retained as historical audit artifacts from
earlier sessions and are not part of the primary navigation. `data/dashboard.json`,
`data/olbg-capture.json`, `data/line-research.json`, `data/official-evidence.json` and
`data/publication-gate.json` are the older capture set; `data/official-evidence.json` is
still the record for the MLB, NHL, EHF and WTA snapshot times quoted in the sources page.
