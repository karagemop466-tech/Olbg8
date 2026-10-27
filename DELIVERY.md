# OLBG desk — delivery summary (2026-10-27)

**Live site:** <https://karagemop466-tech.github.io/Olbg8/>

## Where the picks are

Open **Picks** in the top navigation, or <https://karagemop466-tech.github.io/Olbg8/picks.html>.
Each block states the bet and our price in a shaded strip, then the written prediction, then the evidence with a
link per fact. The landing page also shows the three strongest picks as cards and a ranked table of all twelve.

## The twelve picks (all inside −250 to +10000 American)

| # | Sport | Match (UTC) | Bet | Our line | Win chance | Confidence |
|---|---|---|---|---|---|---|
| 1 | Basketball | Panathinaikos vs Milano — 27 Oct 19:15 | Handicap: Panathinaikos −19.5 | −246 | 71.1% | high |
| 2 | Basketball | Besiktas vs Olympiacos — 28 Oct 17:30 | Money line: Olympiacos | −211 | 67.8% | high |
| 3 | Basketball | BC Dubai vs Paris — 27 Oct 16:00 | Handicap: BC Dubai −7.5 | −198 | 66.4% | high |
| 4 | Basketball | Bayern Munich vs Barcelona — 27 Oct 19:00 | Handicap: Barcelona −3.5 | −182 | 64.5% | medium |
| 5 | Basketball | Crvena Zvezda vs Maccabi — 27 Oct 19:00 | Handicap: Crvena Zvezda −9.5 | −173 | 63.4% | medium |
| 6 | Basketball | Baskonia vs Real Madrid — 27 Oct 20:00 | Handicap: Real Madrid −9.5 | −170 | 63.0% | medium |
| 7 | Basketball | Asvel vs Partizan — 28 Oct 19:00 | Handicap: Partizan −3.5 | −168 | 62.7% | medium |
| 8 | Basketball | Valencia vs Fenerbahce — 27 Oct 19:30 | Money line: Valencia | −149 | 59.8% | medium |
| 9 | Basketball | Virtus Bologna vs Zalgiris — 28 Oct 19:30 | Money line: Virtus Bologna | −135 | 57.4% | medium |
| 10 | Baseball | MIL Brewers @ TB Rays — 28 Oct 00:00 | Money line: Milwaukee Brewers | −131 | 56.7% | medium |
| 11 | Ice Hockey | BOS Bruins @ CAR Hurricanes — 28 Oct 00:00 | Money line: Boston Bruins | −118 | 54.1% | low |
| 12 | Volleyball | Conegliano vs Vallefoglia — 28 Oct 19:00 | Set score: Conegliano to win 3-1 | +198 | 33.6% | low |

## What is in each tab

| Tab | Contents |
|---|---|
| Overview | Executive summary, three hero picks, ranked table, coverage table for all 15 sports |
| Picks | All twelve predictions in full, grouped by sport |
| Matches | 115 captured OLBG listings, one table per sport, every row linked to its OLBG event page |
| Pricing | How each of the 15 sports is priced, market by market, with margins and a worked example |
| Sources | Source register plus the result of every official page opened, including the four that returned 404 |
| Flagged | 16 items that could not be closed against an official source, with links |
| Method | Reverse-engineering notes, the publication gate, the window and the known limits |

## Coverage by sport

- **With picks (4):** Basketball 9, Volleyball 1, Baseball 1, Ice Hockey 1.
- **Listings captured, no pick yet (11):** Golf 3, Rugby Union 13, Cricket 13, Snooker 0, Darts 2, Gaelic Sports 4,
  Greyhounds 1, Tennis 14, Motor Racing 1, Handball 15, Rugby League 3.

Why no pick: each sport needs an official page to confirm the fixture and the form. Four of those pages failed this
session (URC 404, EHF 404, ICC 404, GAA listed no upcoming club fixture); the rest are outright-only markets
(snooker had no tips at all) or rows not re-captured in this snapshot. Every gap is on **Flagged** with the URL that
unblocks it — nothing was filled in by inference.

## Verification

`python3 scripts/build_site.py && python3 scripts/check_site.py` → 22 pages, 447 assertions, 0 broken links.
The gate enforces: 30-word minimum predictions, no banned reader-facing words, price window, implied-percentage
arithmetic, confidence banding, an OLBG link plus an independent official link on every pick, event ids present in
the capture, ISO timestamps, source links on every flag, and internal link/anchor integrity.
