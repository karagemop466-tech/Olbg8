# Source audit — 2026-10-26 UTC

Retrieval method: Arena page retrieval tool, except the explicitly failed curl probe. Only extracted content was inspected. No full raw DOM/network trace, private API, authenticated feed or exhaustive pagination audit was available. Individual event URLs were observed as links on the sport pages, not all fetched individually. Thus link syntax is checked, not external HTTP availability for every event.

## OLBG first-party evidence

All 15 requested sport category pages in `research.json` (Gaelic Sports is represented by the captured Gaelic Football category) were retrieved and their first text chunk inspected. The main [tips page](https://www.olbg.com/betting-tips) was read across all three chunks to discover category IDs. Tennis and basketball incorrectly guessed IDs redirected to canonical IDs 3 and 4; stored URLs use those canonical paths.

The recorded event names, IDs, display strings and markets are selected transcriptions of those excerpts; this is **not a full event list**. No tipster comment is used as an official sports statistic or copied into an original prediction. Selections, confidence, prices and predictions are null in every row. Blank Gaelic Football market names reflect missing labels in the extract.

- [Golf](https://www.olbg.com/betting-tips/Golf/5)
- [Volleyball](https://www.olbg.com/betting-tips/Volleyball/21)
- [Rugby Union](https://www.olbg.com/betting-tips/Rugby_Union/9)
- [Cricket](https://www.olbg.com/betting-tips/Cricket/7)
- [Snooker](https://www.olbg.com/betting-tips/Snooker/8): “No tips found.” Not proof of no fixtures.
- [Darts](https://www.olbg.com/betting-tips/Darts/15)
- [Baseball](https://www.olbg.com/betting-tips/Baseball/12)
- [Gaelic Football](https://www.olbg.com/betting-tips/Gaelic_Football/25)
- [Greyhounds](https://www.olbg.com/betting-tips/Greyhounds/28): explicit Expired label on Towcester 8:24; times differ from race labels.
- [Tennis](https://www.olbg.com/betting-tips/Tennis/3)
- [Motor Racing](https://www.olbg.com/betting-tips/Motor_Racing/14)
- [Handball](https://www.olbg.com/betting-tips/Handball/20)
- [Ice Hockey](https://www.olbg.com/betting-tips/Ice_Hockey/13)
- [Basketball](https://www.olbg.com/betting-tips/Basketball/4)
- [Rugby League](https://www.olbg.com/betting-tips/Rugby_League/10)

[Brewers at Rays detail](https://www.olbg.com/betting-tips/Baseball/MLB/MLB/MIL_Brewers_@_TB_Rays/12?event_id=160795) fetched: Money Line, Run Line ±1.50 and Game Totals 7.50 observed. WIN @ had no numeric price. Tipster comments disagree on winners and totals; not adopted as facts. No documented public programmatic API was established. Public URL anatomy is sport/competition/event/category ID with `event_id` query parameter; use sport+event ID as key, not selection count. “Load More” means first-page completeness cannot be assumed.

## Official sport sources actually inspected

| Source | Observation supported | Does not establish |
|---|---|---|
| https://www.mlb.com/schedule/2026-10-26 | MIL at TB; World Series; Oct 26, 8:00 PM ET. UTC conversion uses America/New_York October DST: Oct 27 00:00 UTC. | Pitchers, form, injuries, prices |
| https://www.mlb.com/gameday/849804 | Redirected to Brewers/Rays Oct 26 game URL; extracted shell only | Pitchers or lineup |
| https://www.formula1.com/en/racing/2026 | Mexico weekend Oct 30–Nov 1 | Race outcome probabilities |
| https://www.formula1.com/en/racing/2026/mexico | Nov 1 race; 71 laps; 4.304 km circuit; 305.354 km distance | Independent race lines, final grid, timezone for displayed race time |
| https://www.icc-cricket.com/fixtures-results | Upcoming NZ/India T20, Namibia/Ireland ODI, Pakistan/Sri Lanka ODI, Afghanistan/Zimbabwe T20, South Africa/Australia Test | Absolute dates from the extracted local-time cards |
| https://www.icc-cricket.com/matches/271648/new-zealand-vs-india | Page title identifies IND in NZ 5 T20Is, 2026; main content loading placeholders | Current form or injury report |
| https://www.nba.com/schedule | Schedule filters and navigation only | Any particular future fixture |
| https://www.atptour.com/en/scores/current | Live/completed scores and player links | Future OLBG matchup eligibility |
| https://www.pdc.tv/tournaments/calendar | Redirect to https://www.pdc.tv/calendar/; first chunk dominated by consent text | PDC event dates |

## Network limitation

Direct curl to https://www.olbg.com/ failed SSL connection in this sandbox, whose outbound host access is restricted. Page retrieval above succeeded separately. Do not generalize the direct-request failure to an OLBG outage. GitHub Actions discovery is a distinct, unverified execution environment and may be blocked or served incomplete HTML. It saves audit artifacts only, never silently overwrites the curated snapshot.
