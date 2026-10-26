# OLBG Multi-Sport Predictions Desk

Reverse-engineered, sourced coverage of upcoming OLBG markets across 15 sports:
Golf, Volleyball, Rugby Union, Cricket, Snooker, Darts, Baseball, Gaelic Sports,
Greyhounds, Tennis, Motor Racing, Handball, Ice Hockey, Basketball, Rugby League.

**Live site:** https://karagemop466-tech.github.io/Olbg8/

## What is in here

| Path | Purpose |
|---|---|
| `data/olbg/` | Raw OLBG collection output (committed by the Actions runner, not hand-written) |
| `data/*.json` | Normalised matches, originated lines, picks, flagged items |
| `scripts/` | Collector (runs on Actions), pricer, site builder, verifier |
| `site/` | Generated static site (published from `main` root by GitHub Pages) |
| `docs/methodology/` | How every sport is priced |
| `COORDINATION.md` | Shared task board for parallel sessions |

## Ground rules

- Every table row carries a source link to an official or primary source.
- If a value cannot be confirmed from a source it is left blank and flagged as unverified.
- Nothing is inferred or back-filled.
