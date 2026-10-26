#!/usr/bin/env python3
"""Build the source-first, static dashboard data from the captured OLBG desk.

The capture is intentionally kept beside the derived dashboard so every displayed
number can be traced back to the page snapshot or to the official-source notes.
No fixture, line, injury, or prediction is invented in this transform.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

CAPTURE_UTC = "2026-10-26T05:18:26Z"
BUILD_UTC = "2026-10-26T00:00:00Z"

SPORTS = [
    {
        "key": "golf",
        "label": "Golf",
        "olbg_label": "Golf",
        "sport_id": 5,
        "olbg_hub": "https://www.olbg.com/betting-tips/Golf/5",
        "official_url": "https://www.pgatour.com/schedule",
        "official_name": "PGA TOUR official schedule",
        "official_alt": "https://www.lpga.com/tournaments",
        "official_alt_name": "LPGA official tournament schedule",
        "note": "No event appeared in the captured OLBG feed. That is not evidence that the tours have no events; OLBG only exposes events with tipster activity.",
    },
    {
        "key": "volleyball",
        "label": "Volleyball",
        "olbg_label": "Volleyball",
        "sport_id": 21,
        "olbg_hub": "https://www.olbg.com/betting-tips/Volleyball/21",
        "official_url": "https://www.cev.eu/match-centres/",
        "official_name": "European Volleyball Confederation match centres",
        "official_alt": "https://www.cbv.com.br/",
        "official_alt_name": "Brazilian Volleyball Confederation",
        "note": "Official event identity and current team data were not captured for these OLBG listings; lines remain blank unless a separate research row is present.",
    },
    {
        "key": "rugby-union",
        "label": "Rugby Union",
        "olbg_label": "Rugby Union",
        "sport_id": 9,
        "olbg_hub": "https://www.olbg.com/betting-tips/Rugby_Union/9",
        "official_url": "https://prod2.lnr.fr/calendrier-et-resultats",
        "official_name": "LNR Pro D2 official calendar and results",
        "official_alt": "https://www.epcrugby.com/champions-cup/matches",
        "official_alt_name": "EPCR Champions Cup fixtures and results",
        "note": "The captured OLBG row was not crosswalked to an event-specific governing-body fixture.",
    },
    {
        "key": "cricket",
        "label": "Cricket",
        "olbg_label": "Cricket",
        "sport_id": 7,
        "olbg_hub": "https://www.olbg.com/betting-tips/Cricket/7",
        "official_url": "https://www.icc-cricket.com/fixtures-results",
        "official_name": "International Cricket Council fixtures and results",
        "official_alt": "https://www.cricket.com.au/fixtures",
        "official_alt_name": "Cricket Australia fixtures",
        "note": "The ICC fixture page was read for the international calendar. No captured row cleared the identity and availability gate for a recommendation.",
    },
    {
        "key": "snooker",
        "label": "Snooker",
        "olbg_label": "Snooker",
        "sport_id": 8,
        "olbg_hub": "https://www.olbg.com/betting-tips/Snooker/8",
        "official_url": "https://www.wst.tv/matches",
        "official_name": "World Snooker Tour match list",
        "official_alt": "https://www.wst.tv/calendar",
        "official_alt_name": "World Snooker Tour calendar",
        "note": "The captured OLBG page said no tips found. No event is published here rather than filling the page from a different calendar.",
    },
    {
        "key": "darts",
        "label": "Darts",
        "olbg_label": "Darts",
        "sport_id": 15,
        "olbg_hub": "https://www.olbg.com/betting-tips/Darts/15",
        "official_url": "https://www.pdc.tv/tournaments",
        "official_name": "Professional Darts Corporation tournaments",
        "note": "The captured feed contains an outright tournament listing, not a match-level event. No match prediction is promoted.",
    },
    {
        "key": "baseball",
        "label": "Baseball",
        "olbg_label": "Baseball",
        "sport_id": 12,
        "olbg_hub": "https://www.olbg.com/betting-tips/Baseball/12",
        "official_url": "https://www.mlb.com/schedule",
        "official_name": "Major League Baseball official schedule",
        "official_alt": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-26&endDate=2026-11-05&hydrate=team,linescore,probablePitcher",
        "official_alt_name": "MLB StatsAPI schedule",
        "note": "One scheduled World Series game was identity-matched. The research line is shown separately from the OLBG displayed price and is withheld from the publishable picks page.",
    },
    {
        "key": "gaelic-sports",
        "label": "Gaelic Sports",
        "olbg_label": "Gaelic Football",
        "sport_id": 25,
        "olbg_hub": "https://www.olbg.com/betting-tips/Gaelic_Football/25",
        "official_url": "https://www.gaa.ie/fixtures-results",
        "official_name": "GAA fixtures and results",
        "official_alt": "https://ladiesgaelic.ie/fixtures/",
        "official_alt_name": "Ladies Gaelic Football fixtures",
        "note": "This dashboard treats OLBG's Gaelic Football taxonomy as the requested Gaelic Sports category. The interpretation remains flagged for review.",
    },
    {
        "key": "greyhounds",
        "label": "Greyhounds",
        "olbg_label": "Greyhounds",
        "sport_id": 28,
        "olbg_hub": "https://www.olbg.com/betting-tips/Greyhounds/28",
        "official_url": "https://www.gbgb.org.uk/racing/",
        "official_name": "Greyhound Board of Great Britain racing",
        "official_alt": "https://www.gbgb.org.uk/results/",
        "official_alt_name": "Greyhound Board of Great Britain results",
        "note": "The event is a race listing. Trap, runner, going, and injury data were not captured from the official race card, so no line is originated.",
    },
    {
        "key": "tennis",
        "label": "Tennis",
        "olbg_label": "Tennis",
        "sport_id": 3,
        "olbg_hub": "https://www.olbg.com/betting-tips/Tennis/3",
        "official_url": "https://www.atptour.com/en/scores/current",
        "official_name": "ATP Tour scores and schedules",
        "official_alt": "https://www.wtatennis.com/tournaments",
        "official_alt_name": "WTA official tournaments",
        "note": "The WTA rankings page provided identity context for two research rows, but the captured official material did not establish an event-specific draw, availability report, or full recent-form record.",
    },
    {
        "key": "motor-racing",
        "label": "Motor Racing",
        "olbg_label": "Motor Racing",
        "sport_id": 14,
        "olbg_hub": "https://www.olbg.com/betting-tips/Motor_Racing/14",
        "official_url": "https://www.formula1.com/en/racing/2026",
        "official_name": "Formula 1 official 2026 calendar",
        "note": "The captured OLBG listing is an outright/top-six market. Qualifying order, car setup, weather, and driver availability were not captured, so the line is blank.",
    },
    {
        "key": "handball",
        "label": "Handball",
        "olbg_label": "Handball",
        "sport_id": 20,
        "olbg_hub": "https://www.olbg.com/betting-tips/Handball/20",
        "official_url": "https://ehfcl.eurohandball.com/men/2026-27/matches/",
        "official_name": "EHF Champions League official matches",
        "official_alt": "https://ehfcl.eurohandball.com/men/2026-27/standings/",
        "official_alt_name": "EHF Champions League official standings",
        "note": "The official standings supplied team data for research lines, but most OLBG event names were not identity-matched to an official fixture page.",
    },
    {
        "key": "ice-hockey",
        "label": "Ice Hockey",
        "olbg_label": "Ice Hockey",
        "sport_id": 13,
        "olbg_hub": "https://www.olbg.com/betting-tips/Ice_Hockey/13",
        "official_url": "https://www.nhl.com/schedule",
        "official_name": "NHL official schedule and game centres",
        "official_alt": "https://api-web.nhle.com/v1/standings/now",
        "official_alt_name": "NHL official standings API",
        "note": "Three NHL fixtures were identity-matched to NHL game centres and one additional line was calculated from captured standings. Injury and confirmed-goaltender checks are still open.",
    },
    {
        "key": "basketball",
        "label": "Basketball",
        "olbg_label": "Basketball",
        "sport_id": 4,
        "olbg_hub": "https://www.olbg.com/betting-tips/Basketball/4",
        "official_url": "https://www.nba.com/games?date=2026-10-26",
        "official_name": "NBA official games and scores",
        "official_alt": "https://www.euroleaguebasketball.net/en/euroleague/",
        "official_alt_name": "EuroLeague official site",
        "note": "OLBG listed NBA and other leagues, but no captured official fixture crosswalk cleared the source-first gate. Lines and picks stay blank.",
    },
    {
        "key": "rugby-league",
        "label": "Rugby League",
        "olbg_label": "Rugby League",
        "sport_id": 10,
        "olbg_hub": "https://www.olbg.com/betting-tips/Rugby_League/10",
        "official_url": "https://www.nrl.com/draw/",
        "official_name": "NRL official draw",
        "official_alt": "https://www.superleague.co.uk/",
        "official_alt_name": "Super League official site",
        "note": "The captured feed contained future outright markets only; no upcoming match was published as a match pick.",
    },
]

SPORT_BY_OLBG = {s["olbg_label"]: s for s in SPORTS}
SPORT_BY_KEY = {s["key"]: s for s in SPORTS}

# These are full prose research briefs, deliberately withheld from the picks page.
# The official capture did not include all required availability and market checks.
DRAFT_NOTES = {
    "baseball-160795": {
        "selection": "Tampa Bay Rays moneyline",
        "confidence": "Low",
        "text": (
            "Tampa Bay Rays moneyline is the research selection at -104, not a bookmaker quote. MLB’s official schedule names Robert Gasser for Milwaukee and Freddy Peralta for Tampa Bay at Tropicana Field, with the game set for 8:00 p.m. ET. The captured official standings show Milwaukee 8–2 across its last ten and Tampa Bay 5–5; the run profiles are 5.14 scored and 3.81 allowed for Milwaukee against 4.54 and 4.01 for Tampa Bay. No official lineup or injury clearance was captured, so this remains low confidence and is withheld."
        ),
        "source_ids": ["baseball-fixture", "baseball-standings"],
    },
    "ice_hockey-200101": {
        "selection": "New York Rangers moneyline",
        "confidence": "Medium",
        "text": (
            "New York Rangers moneyline is the research selection at -227 for the NHL meeting with the Los Angeles Kings at Madison Square Garden. The captured NHL schedule identifies the 7:00 p.m. EDT game, while the official standings snapshot records New York 5–4–1 over its last ten and Los Angeles 2–5–2. The Rangers’ scoring profile is 3.15 goals for and 2.77 against per game, compared with 2.33 and 3.56 for the Kings. Confirmed goaltenders and availability were not captured, so this is withheld from publication."
        ),
        "source_ids": ["nhl-schedule", "nhl-standings"],
    },
    "ice_hockey-200103": {
        "selection": "Toronto Maple Leafs moneyline",
        "confidence": "Low",
        "text": (
            "Toronto Maple Leafs moneyline is the research selection at -123 against the Calgary Flames in Calgary. NHL’s official schedule places the game at Scotiabank Saddledome, and the captured standings show Toronto 6–2–2 across its last ten compared with Calgary 4–6–0. Toronto’s profile is 3.85 goals for and 3.15 against per game; Calgary’s is 2.30 for and 3.90 against. The official capture did not include a final lineup, starting goalie, or injury report, so this low-confidence brief is not an actionable pick."
        ),
        "source_ids": ["nhl-schedule", "nhl-standings"],
    },
    "ice_hockey-200102": {
        "selection": "Edmonton Oilers moneyline",
        "confidence": "High",
        "text": (
            "Edmonton Oilers moneyline is the research selection at -263 against the Detroit Red Wings at Rogers Place. NHL’s official game centre lists Edmonton 8–2–1 and Detroit 4–4–3 before the 9:30 p.m. EDT faceoff; the same official material gives Edmonton 4.36 goals per game against Detroit’s 2.55. The captured last-ten records are 8–2–0 for Edmonton and 4–3–3 for Detroit, with the Oilers also holding the stronger scoring profile. The price falls outside the requested -250 boundary and availability was not cleared, so publication is withheld."
        ),
        "source_ids": ["nhl-game-edm-det", "nhl-standings"],
    },
}

SOURCE_REGISTRY = [
    {
        "id": "olbg-feed",
        "name": "OLBG sport feeds",
        "kind": "discovery",
        "url": "https://www.olbg.com/betting-tips",
        "captured": CAPTURE_UTC,
        "supports": "Named listings, event links, displayed selection, market, OLBG tip share and displayed price.",
        "limitation": "OLBG exposes tipped events rather than a complete fixture database; the page also contains a load-more boundary.",
    },
    {
        "id": "baseball-fixture",
        "name": "MLB official schedule",
        "kind": "official",
        "url": "https://www.mlb.com/schedule",
        "captured": CAPTURE_UTC,
        "supports": "Milwaukee at Tampa Bay World Series listing, time, venue and probable pitchers.",
        "limitation": "A schedule does not establish a final lineup or injury clearance.",
    },
    {
        "id": "baseball-standings",
        "name": "MLB StatsAPI standings",
        "kind": "official",
        "url": "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026&standingsTypes=regularSeason&hydrate=team",
        "captured": CAPTURE_UTC,
        "supports": "Captured team records and scoring inputs used by the research line.",
        "limitation": "Standings are not a lineup, injury, or sportsbook market source.",
    },
    {
        "id": "nhl-schedule",
        "name": "NHL official schedule",
        "kind": "official",
        "url": "https://www.nhl.com/schedule/2026-10-26",
        "captured": CAPTURE_UTC,
        "supports": "NHL fixtures, game-centre links, times and the league schedule context.",
        "limitation": "Schedule data alone does not clear player availability or starting goaltender status.",
    },
    {
        "id": "nhl-game-edm-det",
        "name": "NHL Edmonton–Detroit game centre",
        "kind": "official",
        "url": "https://www.nhl.com/gamecenter/det-vs-edm/2026/10/26/2026020187",
        "captured": CAPTURE_UTC,
        "supports": "Fixture identity, team records, player-to-watch data, team rates and last-ten form.",
        "limitation": "The captured page did not supply a final injury/lineup clearance for publication.",
    },
    {
        "id": "nhl-standings",
        "name": "NHL official standings API",
        "kind": "official",
        "url": "https://api-web.nhle.com/v1/standings/now",
        "captured": CAPTURE_UTC,
        "supports": "NHL standing and scoring inputs used for the research lines.",
        "limitation": "A standings snapshot is not an offer or a guaranteed pre-game lineup.",
    },
    {
        "id": "icc-fixtures",
        "name": "ICC fixtures and results",
        "kind": "official",
        "url": "https://www.icc-cricket.com/fixtures-results",
        "captured": CAPTURE_UTC,
        "supports": "Official cricket fixture identity and scheduled start context.",
        "limitation": "The captured page did not expose a complete form, injury and likely XI record for every OLBG listing.",
    },
    {
        "id": "f1-calendar",
        "name": "Formula 1 official 2026 calendar",
        "kind": "official",
        "url": "https://www.formula1.com/en/racing/2026",
        "captured": CAPTURE_UTC,
        "supports": "Upcoming Grand Prix calendar and round dates.",
        "limitation": "Calendar pages do not establish qualifying order, weather, car setup or driver availability.",
    },
    {
        "id": "atp-scores",
        "name": "ATP Tour scores and schedules",
        "kind": "official",
        "url": "https://www.atptour.com/en/scores/current",
        "captured": CAPTURE_UTC,
        "supports": "ATP event and player score context.",
        "limitation": "The captured page may show live/current play rather than every future OLBG event.",
    },
    {
        "id": "wta-tournaments",
        "name": "WTA official tournaments",
        "kind": "official",
        "url": "https://www.wtatennis.com/tournaments",
        "captured": CAPTURE_UTC,
        "supports": "WTA tournament and draw-release context.",
        "limitation": "A tournament page is not a complete player availability or injury source.",
    },
]


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def json_dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def infer_event_type(row: dict) -> str:
    market = (row.get("market") or "").lower()
    name = (row.get("event_name") or "").lower()
    sport = row.get("sport")
    if not name:
        return "unknown"
    if sport == "Greyhounds":
        return "race"
    if any(word in market for word in ("tournament", "grand final winner", "outright", "top 6")):
        return "outright"
    if any(word in name for word in ("championship", "grand prix")) and "@" not in name and " vs " not in name and " v " not in name:
        return "outright"
    return "fixture"


def short_status(row: dict, desk: dict | None) -> str:
    if desk is None:
        return "listed-no-line"
    if desk.get("identity_confirmed") and desk.get("pick"):
        return "research-line"
    if desk.get("pick"):
        return "research-line-unmatched"
    return "listed-no-line"


def make_flag_list(row: dict, desk: dict | None, sport: dict) -> list[str]:
    flags: list[str] = []
    if desk:
        flags.extend(desk.get("flags") or [])
    if not row.get("event_name"):
        flags.append("The OLBG payload left the event name blank; it is displayed as blank and is not inferred from the URL slug.")
    if desk is None:
        flags.append("No official event-specific crosswalk was captured; no own line or selection is published.")
    elif not desk.get("identity_confirmed"): 
        flags.append("The official source supplied context or team data but did not identity-match this OLBG event.")
    if row.get("expired"):
        flags.append("OLBG marked the listing expired at capture time.")
    if infer_event_type(row) == "outright":
        flags.append("This is an outright/top-six market, not a match-level fixture; it is excluded from the daily match-pick quota.")
    if not (desk and desk.get("pick")):
        flags.append(sport["note"])
    return list(dict.fromkeys(flags))


def main() -> None:
    raw = load("olbg-capture.json")
    desk = load("line-research.json")
    desk_by_id = {r["id"]: r for r in desk.get("rows", [])}
    raw_rows = [r for r in raw.get("rows", []) if r.get("sport") != "Hurling"]
    excluded = [r for r in raw.get("rows", []) if r.get("sport") == "Hurling"]

    events: list[dict] = []
    for row in raw_rows:
        sport = SPORT_BY_OLBG.get(row.get("sport"))
        if sport is None:
            continue
        # The raw capture preserves OLBG's underscore sport key (for example
        # ``ice_hockey``), while the public dashboard uses readable slugs.
        desk_id = f"{row.get('sport_key')}-{row.get('event_id')}"
        event_id = f"{sport['key']}-{row.get('event_id')}"
        d = desk_by_id.get(desk_id)
        pick = (d or {}).get("pick") or {}
        fixture_url = (d or {}).get("fixture_url")
        official_url = fixture_url or (d or {}).get("official_url") or sport["official_url"]
        official_name = (f"{sport['official_name']} fixture" if fixture_url else ((d or {}).get("official_name") or sport["official_name"]))
        identity = bool((d or {}).get("identity_confirmed"))
        event_type = infer_event_type(row)
        notes = DRAFT_NOTES.get(desk_id)
        event = {
            "id": event_id,
            "sport": sport["label"],
            "sportKey": sport["key"],
            "sportId": sport["sport_id"],
            "eventType": event_type,
            "competition": row.get("competition") or None,
            "event": row.get("event_name"),
            "startUtc": row.get("start_utc"),
            "venue": (d or {}).get("venue") or row.get("venue") or None,
            "olbg": {
                "hub": sport["olbg_hub"],
                "event": row.get("olbg_url"),
                "selection": row.get("selection") or None,
                "market": row.get("market") or None,
                "american": row.get("olbg_american"),
                "decimal": row.get("olbg_decimal"),
                "tipPct": row.get("tip_pct"),
                "tips": row.get("tips_total"),
                "tipsters": row.get("tips_won"),
                "experts": row.get("experts", 0),
                "expired": bool(row.get("expired")),
            },
            "official": {
                "url": official_url,
                "name": official_name,
                "status": "event-confirmed" if identity else ("stats-only" if d else "reference-only"),
                "sourceNote": sport["note"] if not identity else "The official event/source crosswalk is present in the capture.",
            },
            "research": {
                "status": short_status(row, d),
                "selection": pick.get("selection") or None,
                "market": pick.get("market") or None,
                "american": pick.get("american"),
                "probability": pick.get("probability"),
                "confidence": pick.get("confidence"),
                "inPriceWindow": pick.get("in_price_window"),
                "markets": d.get("markets") if d else {},
                "form": d.get("form") if d else {},
                "scoring": d.get("scoring") if d else {},
                "expectedMargin": d.get("expected_margin") if d else None,
                "expectedTotal": d.get("expected_total") if d else None,
            },
            "flags": make_flag_list(row, d, sport),
            "draftPrediction": notes,
        }
        events.append(event)

    by_sport = Counter(e["sportKey"] for e in events)
    lines = [e for e in events if e["research"]["american"] is not None]
    confirmed = [e for e in events if e["official"]["status"] == "event-confirmed"]
    match_events = [e for e in events if e["eventType"] == "fixture"]

    dashboard = {
        "schema": "olbg-research-dashboard/v1",
        "captureUtc": CAPTURE_UTC,
        "builtUtc": BUILD_UTC,
        "asOfLabel": "26 October 2026 · UTC",
        "timezoneNote": "OLBG displays local-time labels. This capture stores normalized UTC timestamps where a timestamp was available; the source links remain the authority for rechecking time.",
        "scope": [s["label"] for s in SPORTS],
        "dailyTargetPerSport": 5,
        "publication": {
            "publishedPicks": [],
            "publishedCount": 0,
            "draftPredictionCount": sum(1 for e in events if e["draftPrediction"]),
            "message": "No recommendation cleared every publication gate. The full prose briefs are retained as withheld research notes, not presented as actionable picks.",
        },
        "summary": {
            "olbgEvents": len(events),
            "matchEvents": len(match_events),
            "researchLines": len(lines),
            "eventConfirmed": len(confirmed),
            "draftPredictions": sum(1 for e in events if e["draftPrediction"]),
            "publishedPicks": 0,
            "sportsWithListings": sum(1 for s in SPORTS if by_sport.get(s["key"], 0)),
            "sportsInScope": len(SPORTS),
        },
        "sports": [
            {
                **s,
                "events": by_sport.get(s["key"], 0),
                "matchEvents": sum(1 for e in events if e["sportKey"] == s["key"] and e["eventType"] == "fixture"),
                "researchLines": sum(1 for e in events if e["sportKey"] == s["key"] and e["research"]["american"] is not None),
                "eventConfirmed": sum(1 for e in events if e["sportKey"] == s["key"] and e["official"]["status"] == "event-confirmed"),
                "draftPredictions": sum(1 for e in events if e["sportKey"] == s["key"] and e["draftPrediction"]),
            }
            for s in SPORTS
        ],
        "excluded": [
            {
                "sport": "Hurling",
                "event": r.get("event_name"),
                "olbg": r.get("olbg_url"),
                "reason": "Not in the requested sport list; retained only as an audit note and excluded from all dashboard counts.",
            }
            for r in excluded
        ],
        "flags": [
            {
                "id": "PUB-001",
                "severity": "high",
                "title": "Daily written-pick target not met",
                "body": "The requested target is five written predictions per sport. Zero are published because the captured evidence did not establish every required identity, market, availability, and current-form field for a recommendation.",
                "links": [{"label": "Publication gate", "url": "publication-gate.json"}],
            },
            {
                "id": "SRC-001",
                "severity": "high",
                "title": "OLBG is a tipped-event feed, not a complete fixture database",
                "body": "A sport page can omit an upcoming event until a tipster posts a tip, and the feed has a load-more boundary. The inventory is therefore a reproducible OLBG listing snapshot, not a claim that no other fixtures exist.",
                "links": [{"label": "OLBG tips", "url": "https://www.olbg.com/betting-tips"}],
            },
            {
                "id": "SRC-002",
                "severity": "medium",
                "title": "Most listings lack an event-specific official crosswalk",
                "body": f"The capture contains {len(events)} in-scope OLBG listings, while only {len(confirmed)} are identity-matched to an official fixture source. Rows without a crosswalk remain visible for review but have no publishable selection.",
                "links": [{"label": "Official-source register", "url": "sources.html"}],
            },
            {
                "id": "PRICE-001",
                "severity": "medium",
                "title": "Research lines are not bookmaker offers",
                "body": f"There are {len(lines)} research-priced rows. They are fair-price calculations from captured official form/scoring inputs, shown alongside—not substituted for—OLBG displayed odds. A blank line means the inputs were insufficient.",
                "links": [{"label": "Methodology", "url": "methodology.html"}],
            },
            {
                "id": "AVAIL-001",
                "severity": "medium",
                "title": "Availability and injury clearance is incomplete",
                "body": "The captured official schedules and standings do not provide a complete injury, lineup, starting-goaltender, or driver-availability check for every row. Predictions are withheld when that information is material.",
                "links": [{"label": "Withheld prose notes", "url": "picks.html"}],
            },
            {
                "id": "SCOPE-001",
                "severity": "low",
                "title": "Gaelic Sports is represented by OLBG's Gaelic Football taxonomy",
                "body": "The requested label is broader than the OLBG taxonomy captured here. Gaelic Football is included; Hurling is excluded because it was not requested. This interpretation is left for review.",
                "links": [{"label": "GAA official fixtures", "url": "https://www.gaa.ie/fixtures-results"}],
            },
        ],
        "events": events,
    }

    json_dump(DATA / "dashboard.json", dashboard)
    json_dump(DATA / "sources.json", {"schema": "olbg-research-sources/v1", "captureUtc": CAPTURE_UTC, "sports": SPORTS, "registry": SOURCE_REGISTRY})

    print(f"Built {len(events)} in-scope events ({len(lines)} research lines, {len(confirmed)} event-confirmed, {len(match_events)} match events).")


if __name__ == "__main__":
    main()
