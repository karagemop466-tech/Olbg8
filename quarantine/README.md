# Quarantined content

## `FABRICATED-data-darts.json` (was `data/darts.json`)

Removed from the published site on 2026-10-27 by session `0d9bd3c1`. Retained here, unedited, as evidence of what was wrong.

Why it was pulled, point by point:

1. **It claimed `"verified": "True"` on every row while citing no match-level source.** All five rows pointed at `https://www.pdc.tv/tournaments/european-championship` (or the same URL without the slug) - a tournament directory page, not a fixture, result, lineup or injury source. A directory URL cannot substantiate "averaging a massive 105 in his previous match".
2. **The event does not line up with the PDC calendar.** The file is headed "European Championship 2026". The European Championship is an October event, but on the capture date OLBG listed **no** live darts match market at all: the Darts category page contained only the `PDC World Championship 2027` outright and `Players Championship 31`. The fixtures in this file - Humphries v van Gerwen, Littler v Price, Smith v Cross, Aspinall v Wright, Anderson v Clayton - were not present on OLBG, and no source for them appears anywhere in the repository's own capture files (`data/olbg-capture.json` contains no darts events with those pairings).
3. **The statistics are uncheckable and read as invented.** "Checkout percentage on the outer ring is flawless", "inconsistency on his double 16s", "has been easily distracted in recent long-format matches", "averaging under 95 in his last two outings" - none of these is a metric published by the PDC, and none is supported by any link in the repository.
4. **It contradicted the repository's own publication gate.** The same commit that merged this file left `data/dashboard.json` recording `"publishedPicks": 0` on the grounds that no row cleared the gate. An orphan file with five "High confidence" picks and no connection to the site was therefore both unverifiable and inconsistent with the published state.

Nothing in this file has been carried into `data/picks.json` or the site. Real darts coverage is in the Darts sport page, priced from the two markets OLBG actually published.
