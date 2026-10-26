# Source inspection and delivery audit

Inspection date: **2026-10-26 UTC**. Original repository: a seven-character README only, no pre-existing scraper, data, site, tests or prediction engine.

## What was actually inspected

The page-retrieval tool retrieved the first text chunk of each of 16 OLBG sport pages. Gaelic Football and Hurling together form the requested Gaelic Sports category. All three chunks of the cross-sport landing page were also inspected, and the first chunk of the MIL Brewers @ TB Rays event page was inspected for market labels. Long category pages have additional chunks and dynamic Load More controls: the 116 transcribed observations are a subset, not a complete event universe. The numeric ID and event-name path came from visible source links. Original tipster commentary was not republished as our own writing.

The source registry in `data/sports.json` records official sources actually retrieved and the limited content they expose. Some are competition directories, not matching evidence. Every event with corroboration has a separate `official_fact` and a source; this never makes its selection, price, form or availability confirmed. Inspection dates have day precision; no precise historical retrieval times were invented.

## Important contrasts

| Observation | Sources checked | Consequence |
|---|---|---|
| OLBG cricket/hockey/basketball clocks differ by four hours between category and landing extracts. | https://www.olbg.com/betting-tips ; https://www.olbg.com/betting-tips/Cricket/7 ; https://www.olbg.com/betting-tips/Ice_Hockey/13 | Preserve raw clocks. Do not assume locale/timezone or assign a UTC event time from them. |
| OLBG Kings/Rangers, Leafs/Flames and Wings/Oilers clocks are seven minutes later than NHL scheduled times. | https://www.olbg.com/betting-tips/Ice_Hockey/13 ; https://www.nhl.com/schedule/2026-10-26 | Preserve official starts separately. These are not proof of the OLBG prediction cutoff. |
| MLB schedule lists MIL at TB October 27, 8 PM ET; OLBG lists Tomorrow 00:00. | https://www.mlb.com/schedule/2026-10-27 ; https://www.olbg.com/betting-tips/Baseball/12 | Official UTC conversion October 28 00:00Z is stored separately. No safe date join to OLBG yet. |
| LPGA Maybank starts October 29, ends November 1; OLBG lists November 1. | https://www.lpga.com/tournaments ; https://www.olbg.com/betting-tips/Golf/5 | Tournament closing date is not the opening date. Entry field and selection evidence are missing. |
| OLBG has no snooker tips in inspected extract. WST says no tournament today. | https://www.olbg.com/betting-tips/Snooker/8 ; https://www.wst.tv/matches/ | Not evidence of no future matches. No fabricated daily five. |
| OLBG greyhound page contains an Expired row. | https://www.olbg.com/betting-tips/Greyhounds/28 ; official research destination https://www.gbgb.org.uk/racing/ | Row retained as flagged observation, not an upcoming actionable race. |
| NHL schedule includes DraftKings moneyline quotes. OLBG event extract shows no numeric betting odds. | https://www.nhl.com/schedule/2026-10-26 ; https://www.olbg.com/betting-tips/Baseball/MLB/MLB/MIL_Brewers_@_TB_Rays/12?event_id=160795 | Published only as market context; neither copied prices nor no-vig conversions are called independently originated lines. |
| NRL draw contains upcoming World Cup internationals; OLBG extract contains only 2027 outrights. | https://www.nrl.com/draw/ ; https://www.olbg.com/betting-tips/Rugby_League/10 | Full-list and off-season claims would be unsupported. |

## Failed paths, corrected destinations

- `https://en.volleyballworld.com/volleyball/competitions` returned Page Not Found. The official homepage at https://en.volleyballworld.com/ was retrieved instead and links a global schedule. No club fixture confirmation claimed.
- `https://www.gbgb.org.uk/racing/race-results/` returned a 404 page. https://www.gbgb.org.uk/racing/ was retrieved instead and links its results/search interface. No runner-level evidence was present in the inspected text.
- `https://www.pdc.tv/tournaments/calendar` redirected to https://www.pdc.tv/calendar/ and exposed substantial consent text; no draw substantiated.
- https://www.nba.com/games?date=2026-10-26 returned calendar counts and an error for the individual fixture list.
- https://www.mlb.com/gameday/849803/preview redirected to the full event path but provided no pitcher/lineup data in the retrieved text.
- Direct sandbox HTTPS to OLBG failed TLS connection setup. The autonomous collector records the permission-access failure rather than bypassing it.

## Requirement matrix

| Requirement | Delivery state |
|---|---|
| Clean dashboard and category pages | Implemented; static build and relative-link tests |
| Executive summary makes picks obvious | Implemented; explicitly zero qualifying picks |
| Source link every data row | Checked by tests; directory-only links distinguished from corroboration |
| Unknown values blank, flags visible | Implemented; all selection/price/confidence fields blank |
| 5–10 original, ≥30-word picks per sport | **Not delivered**; no substantiated qualified predictions |
| Originate lines for every covered event | **Not delivered**; sport research specifications and math kernels only |
| Complete updated OLBG fixture/market list | **Not delivered**; partial observed subset, best-effort link discovery |
| Official form, match statistics, availability | **Incomplete**; no full evidence packet for a pick |
| Autonomous daily prediction service | **Not delivered**; scheduled discovery/build only |
| Tests, PR merge and Pages publishing | Record actual outcome in COORDINATION.md |

Flagged research items are non-blocking for publishing the dashboard; they must not be represented as a completed prediction service. No `verified=true` flags or invented confidence levels are used to fill gaps.
