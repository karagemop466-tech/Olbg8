# OLBG Research Desk

A multi-sport betting-research desk reverse-engineered from OLBG's tips pages. Every page here is
generated from four data files, so the site cannot display a number the pipeline did not produce.

As at **27 October 2026, 05:26 UTC**: 112 OLBG listings across 15 sports, **140 priced
selections**, **53 written predictions** across 13 sports, and every row carrying a link to the
source that was actually opened for it.

## The 15 sports

Golf · Volleyball · Rugby Union · Cricket · Snooker · Darts · Baseball · Gaelic Sports ·
Greyhounds · Tennis · Motor Racing · Handball · Ice Hockey · Basketball · Rugby League

## Pages

| Page | What it answers |
|---|---|
| [Overview](index.html) | Executive summary: the strongest positions today, coverage ledger per sport, and the irregularities found in the repository. |
| [Picks](picks.html) | The predictions. 53 cards, grouped by sport, each with the explicit selection, market, our line, the confidence band, the reasoning and its sources. |
| [Line board](matches.html) | All 140 priced selections across every market OLBG exposed, with the tip volume behind each. Filterable. |
| [Pricing](pricing.html) | How a share of tips becomes a line: the Dirichlet estimate, outcome counts, the −250 to +10,000 band, and confidence bands as actually applied. |
| [Sources](sources.html) | Every event matched to an official source, tiered A or B, with what each source was used to confirm — and the list of what was not checked. |
| [Method](methodology.html) | How an OLBG listing is structured, what its percentages mean, the market inventory and the time-zone finding. |
| [Flagged for review](flagged.html) | The review queue: the fabricated file that was removed, empty categories, thin markets, unpriced markets, out-of-band favourites. |
| [Sport pages](sports/) | One page per sport: its picks above its full market table, or the reason there is nothing to price. |

## Pipeline

```bash
python3 scripts/build_capture.py   # capture/raw-*.json  -> data/live-capture.json
python3 scripts/originate.py       # + data/crosswalks.json -> data/lines.json
python3 scripts/build_picks.py     # -> data/picks.json (every pick must resolve to a priced row)
python3 scripts/build_site.py      # -> all HTML pages
python3 scripts/test_site.py       # publication checks; exits non-zero on any failure
```

Sources are never hand-written into the HTML: `capture/raw-2026-10-27.json` holds the verbatim OLBG
rows, and `data/crosswalks.json` holds the source register, tiers and `not_checked` list.

## Standing rules this repository enforces

1. **No invented data.** A value that no source states is left blank and flagged, not estimated.
   `scripts/test_site.py` fails the build if a page renders a placeholder or a pick stops resolving.
2. **Confidence is earned in four steps** — official source matched, priced chance ≥ 60%, at least
   four tips in the market, and a line inside −250 to +10,000. Missing one is Medium or Low; the
   label and the reason are printed on the row.
3. **A favourite is not a pick.** Anything shorter than −250 is excluded from the picks surface by
   instruction, and the excluded rows are listed on the flagged page instead of being dropped.
4. **Shortfalls are stated, not filled.** Snooker and Greyhounds had no OLBG listing at capture time
   and publish zero picks; Golf, Darts, Motor Racing, Rugby League, Baseball and Gaelic games are
   under five because the listings or the tip volume did not support more. Each reason is on the
   Overview ledger.
5. **`"model"` and `"verified"` never appear in published prose.** Those words describe internal
   machinery, and a claim of verification without a source is how fabricated content reached this
   repository before. See [quarantine/README.md](quarantine/README.md).

## Verification standard

A row must have an OLBG event link, and any fact stated about it must trace to a source that was
opened in this session. Tier A means the governing body, tour, league data feed or the club's own
page named the fixture; tier B means reliable independent reporting. High requires tier A. OLBG's
own tip counts, displayed percentages and tipster comments are quoted as what OLBG published, never
restated as scouting. Injury and availability lines were checked only for the events where they were
found; the rest say so.

## Legacy and supplementary

`evidence-lab/` and `research-desk/` are earlier sessions' audits, preserved byte-for-byte and not
part of the primary navigation. `data/dashboard.json`, `data/line-research.json`,
`data/publication-gate.json`, `data/official-evidence.json`, `data/olbg-capture.json` and
`scripts/build_dashboard.py` are the superseded 2026-10-26 payload from the previous release: kept
because other sessions own them, and listed on the flagged page rather than silently deleted.

A parallel desk (`data/desk-*.json`, `price-engine/`, `assets/desk.css`, `scripts/check_site.py`) was
merged to `main` from another session while this one was in flight. Its generator is archived at
`price-engine/build_desk_site.py` and its 24-row payload is still validated by `scripts/check_site.py`
in CI, but its rows are not published alongside ours: that engine prices the same events differently,
and one page cannot carry two lines for one selection. The integration is written up on
[flagged.html](flagged.html).

## GitHub Pages

Published from `main` at <https://karagemop466-tech.github.io/Olbg8/> as a static root deploy — the
generated HTML is committed, so the deploy needs no build step. `.github/workflows/` validates the
committed site.

## Disclaimer

Independent research, not OLBG advice and not a guarantee. OLBG publishes tipster opinion; this desk
prices that opinion and adds sourced context. Check the linked source and the current market before
relying on anything here. Only bet where lawful, and only what you can afford to lose.
