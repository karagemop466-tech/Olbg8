#!/usr/bin/env python3
"""Build the 2026-10-27 OLBG desk dataset from committed source snapshots.

This script performs three jobs, in order:

1. Reverse-engineer the captured OLBG SvelteKit event payloads into a complete
   inventory of events, markets, selections, displayed prices and tip counts.
2. Originate an independent fair price for every priced selection in every
   captured market, using a documented de-vig + tip-consensus + official-strength
   blend (see methodology.html).  No price is copied from another bookmaker.
3. Pick the strongest in-range selections per sport, attach official-source
   evidence and write a unique human-facing prediction for each.

Facts are only taken from the committed official snapshots or the OLBG event
payload. Where an official input is missing, the field stays blank/None and the
gap is published on the Flagged for Review page.
"""
from __future__ import annotations

import importlib.util
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAP = ROOT / "data" / "capture-20261027"
OFF = CAP / "official"
OUT = ROOT / "data" / "desk-20261027.json"

_spec = importlib.util.spec_from_file_location("collector", ROOT / "scripts" / "collect_20261027.py")
collector = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(collector)

MANIFEST = json.loads((CAP / "manifest.json").read_text())
CAPTURE_UTC = MANIFEST["capture_utc"]
CAPTURE_DT = datetime.strptime(CAPTURE_UTC, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
# Deterministic: the build is a pure function of the committed snapshot, so
# GitHub Actions can rebuild it and require a clean git diff.
BUILD_UTC = CAPTURE_UTC

# ---------------------------------------------------------------------------
# Scope. Each requested sport maps to its OLBG taxonomy and an official source.
# ---------------------------------------------------------------------------
SPORTS = [
    dict(key="golf", label="Golf", olbg=["golf"], hub="https://www.olbg.com/betting-tips/Golf/5",
         official_name="LPGA official tournaments", official_key="lpga_tournaments",
         secondary_name="PGA TOUR official schedule", secondary_key="pgatour_schedule",
         note="OLBG lists tournament-winner markets, not round-by-round matchups; event identity is checked against the official tour calendars."),
    dict(key="volleyball", label="Volleyball", olbg=["volleyball"], hub="https://www.olbg.com/betting-tips/Volleyball/21",
         official_name="CEV official match centres", official_key="cev_match_centres",
         secondary_name="CEV match centres (competition directory)", secondary_key="cev_match_centres",
         note="Most captured OLBG clubs play in domestic leagues outside the CEV competition directory."),
    dict(key="rugby-union", label="Rugby Union", olbg=["rugby_union"], hub="https://www.olbg.com/betting-tips/Rugby_Union/9",
         official_name="EPCR Champions Cup official matches", official_key="epcr_matches",
         secondary_name="LNR Pro D2 official calendar", secondary_key="lnr_prod2",
         note="United Rugby Championship rows are checked against the EPCR directory only; Pro D2 rows use the LNR calendar."),
    dict(key="cricket", label="Cricket", olbg=["cricket"], hub="https://www.olbg.com/betting-tips/Cricket/7",
         official_name="ICC official fixtures and results", official_key="icc_fixtures",
         secondary_name="Cricket Australia official fixtures", secondary_key="cricket_australia_fixtures",
         note="ICC/CA pages establish series identity; detailed XI and injury sheets were not published in these captures."),
    dict(key="snooker", label="Snooker", olbg=["snooker"], hub="https://www.olbg.com/betting-tips/Snooker/8",
         official_name="World Snooker Tour official matches", official_key="wst_matches",
         secondary_name="WST official rankings", secondary_key="wst_rankings",
         note="OLBG's Snooker hub and All Events feed returned zero tips at capture; no OLBG market row exists to price."),
    dict(key="darts", label="Darts", olbg=["darts"], hub="https://www.olbg.com/betting-tips/Darts/15",
         official_name="PDC official tournaments", official_key="pdc_tournaments",
         secondary_name="PDC official Order of Merit", secondary_key="pdc_order_of_merit",
         note="Captured Darts rows are outright tournament markets, not individual match fixtures."),
    dict(key="baseball", label="Baseball", olbg=["baseball"], hub="https://www.olbg.com/betting-tips/Baseball/12",
         official_name="MLB official schedule (StatsAPI)", official_key="mlb_schedule",
         secondary_name="MLB official standings (StatsAPI)", secondary_key="mlb_standings",
         note="The single remaining upcoming MLB listing is identity-matched to an official MLB game page."),
    dict(key="gaelic-sports", label="Gaelic Sports", olbg=["gaelic_football", "hurling"], hub="https://www.olbg.com/betting-tips/Gaelic_Football/25",
         official_name="GAA official fixtures and results", official_key="gaa_fixtures",
         secondary_name="GAA fixtures (secondary link)", secondary_key="gaa_fixtures",
         note="OLBG has no combined Gaelic Sports category; Gaelic Football and Hurling are captured separately."),
    dict(key="greyhounds", label="Greyhounds", olbg=["greyhounds"], hub="https://www.olbg.com/betting-tips/Greyhounds/28",
         official_name="GBGB official racing", official_key="gbgb_racing",
         secondary_name="GBGB official results", secondary_key="gbgb_results",
         note="OLBG's Greyhounds hub and All Events feed returned zero tips at capture; no race market row exists to price."),
    dict(key="tennis", label="Tennis", olbg=["tennis"], hub="https://www.olbg.com/betting-tips/Tennis/3",
         official_name="WTA official singles rankings", official_key="wta_rankings",
         secondary_name="WTA official tournaments", secondary_key="wta_tournaments",
         note="Official WTA ranking data is available; ATP's official pages returned HTTP 403 at capture and are flagged."),
    dict(key="motor-racing", label="Motor Racing", olbg=["motor_racing"], hub="https://www.olbg.com/betting-tips/Motor_Racing/14",
         official_name="Formula 1 official 2026 driver standings", official_key="f1_driver_standings",
         secondary_name="Formula 1 official 2026 calendar", secondary_key="formula1_calendar",
         note="OLBG lists qualifying and championship outright markets; official standings and calendar supply driver/race context."),
    dict(key="handball", label="Handball", olbg=["handball"], hub="https://www.olbg.com/betting-tips/Handball/20",
         official_name="EHF Champions League official standings", official_key="ehfcl_standings",
         secondary_name="EHF Champions League official matches", secondary_key="ehfcl_matches",
         note=" Champions League group tables give current form and goal data; domestic Swedish rows have no official capture."),
    dict(key="ice-hockey", label="Ice Hockey", olbg=["ice_hockey"], hub="https://www.olbg.com/betting-tips/Ice_Hockey/13",
         official_name="NHL official standings API", official_key="nhl_standings",
         secondary_name="NHL official schedule API", secondary_key="nhl_schedule_20261027",
         note="NHL rows are identity-matched to official game centres; European league rows are not covered by the NHL feed."),
    dict(key="basketball", label="Basketball", olbg=["basketball"], hub="https://www.olbg.com/betting-tips/Basketball/4",
         official_name="NBA official games page", official_key="nba_games",
         secondary_name="EuroLeague official games (capture blocked)", secondary_key="euroleague_games_page",
         note="NBA rows are checked against the official games page; EuroLeague endpoints returned HTTP 429/403 and are flagged."),
    dict(key="rugby-league", label="Rugby League", olbg=["rugby_league"], hub="https://www.olbg.com/betting-tips/Rugby_League/10",
         official_name="NRL official draw", official_key="nrl_draw",
         secondary_name="Super League official site", secondary_key="superleague_home",
         note="All captured Rugby League rows are long-dated outright markets for 2027, not near-term matches."),
]
SPORT_BY_OLBG = {k: s for s in SPORTS for k in s["olbg"]}
SCOPE = [s["label"] for s in SPORTS]


def official_url(key: str) -> str:
    rec = MANIFEST["official"].get(key) or {}
    return rec.get("url", "")


def official_ok(key: str) -> bool:
    rec = MANIFEST["official"].get(key) or {}
    return rec.get("status") == 200 and rec.get("bytes", 0) > 0


# ---------------------------------------------------------------------------
# Official snapshot parsers (all data comes from committed files).
# ---------------------------------------------------------------------------
def norm(value) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u00a0", " ").replace("\u202f", " "))


def read_text(key: str) -> str:
    path = OFF / f"{key}.txt"
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def read_json(key: str):
    path = OFF / f"{key}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


class Official:
    def __init__(self):
        self.wta = self._wta()
        self.f1 = self._f1()
        self.ehf = self._ehf()
        self.nhl_standings = self._nhl_standings()
        self.nhl_games = self._nhl_games()
        self.nhl_results = self._nhl_results()
        self.mlb_games = self._mlb_games()
        self.mlb_standings = self._mlb_standings()
        self.texts = {k: squash(read_text(k)) for k in [
            "nba_games", "icc_fixtures", "cricket_australia_fixtures", "epcr_matches",
            "lnr_prod2", "cev_match_centres", "gaa_fixtures", "pdc_tournaments",
            "lpga_tournaments", "pgatour_schedule", "wst_matches", "wst_calendar",
            "wst_rankings", "gbgb_racing", "gbgb_results", "nrl_draw", "superleague_home",
            "formula1_calendar", "f1_races_mirror", "wta_tournaments", "wta_scores",
            "wta_guangzhou_draws", "wta_tokyo_draws", "wta_courmayeur_draws",
            "wta_queretaro_draws", "wta_curitiba_draws", "wta_guangzhou_overview",
            "wta_tokyo_overview", "atp_vienna_draws", "atp_basel_draws",
            "atp_vienna_results", "atp_basel_results",
        ]}

    @staticmethod
    def _wta():
        out = {}
        text = squash(read_text("wta_rankings"))
        pat = re.compile(r"View Profile\s+(\d+)\s+(-?\d+|-)\s+([A-Za-z\u00c0-\u024f\-\'\.\s]+?)\s+([A-Z]{3})\s+(\d+)\s+(\d+)\s+([\d,]+)")
        for m in pat.finditer(text):
            out[norm(m.group(3))] = dict(rank=int(m.group(1)), move=m.group(2),
                                         country=m.group(4), points=m.group(7))
        return out

    @staticmethod
    def _f1():
        out = {}
        text = squash(read_text("f1_driver_standings"))
        start = text.find("2026 Drivers' Standings")
        segment = text[start:start + 1400] if start >= 0 else ""
        chunks = re.split(r"(?=\b\d{1,2}\s+[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z]{3}\s+[A-Z]{3})", segment)
        for chunk in chunks:
            m = re.match(r"(\d+)\s+([A-Za-z]+)\s+([A-Za-z]+)\s+([A-Z]{3})\s+([A-Z]{3})\s+(.+?)\s+(\d+)\s*$", chunk.strip())
            if m:
                name = f"{m.group(2)} {m.group(3)}"
                out[norm(name)] = dict(pos=int(m.group(1)), name=name, code=m.group(4),
                                       team=m.group(6).strip(), points=int(m.group(7)))
        return out

    @staticmethod
    def _ehf():
        out = {}
        text = squash(read_text("ehfcl_standings"))
        pat = re.compile(r"(\d+)\.\s+([A-Za-z\u00c0-\u024f\.\-\' ]+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*:\s*(\d+)\s+(-?\d+)\s+(\d+)")
        for m in pat.finditer(text):
            name = m.group(2).strip()
            if len(name) < 3 or len(name) > 45:
                continue
            out[norm(name)] = dict(pos=int(m.group(1)), name=name, gp=int(m.group(3)),
                                   w=int(m.group(4)), d=int(m.group(5)), l=int(m.group(6)),
                                   gf=int(m.group(7)), ga=int(m.group(8)), diff=int(m.group(9)),
                                   pts=int(m.group(10)))
        return out

    @staticmethod
    def _nhl_standings():
        out = {}
        data = read_json("nhl_standings") or {}
        for row in data.get("standings", []):
            abbr = row.get("teamAbbrev")
            if isinstance(abbr, dict):
                abbr = abbr.get("default")
            full = row.get("teamName", {}).get("default") if isinstance(row.get("teamName"), dict) else None
            rec = {k: row.get(k) for k in ("wins", "losses", "otLosses", "gamesPlayed", "goalFor",
                                           "goalAgainst", "points", "goalDifferential", "l10Wins",
                                           "l10Losses", "l10OtLosses", "l10GoalDifferential")}
            rec["full"] = full or ""
            if abbr:
                out[abbr.upper()] = rec
        return out

    @staticmethod
    def _nhl_games():
        games = []
        for key in ("nhl_schedule_20261027", "nhl_schedule_20261028", "nhl_schedule_20261029"):
            data = read_json(key) or {}
            for week in data.get("gameWeek", []):
                for g in week.get("games", []):
                    games.append(dict(
                        id=g.get("id"), start=g.get("startTimeUTC"), state=g.get("gameState"),
                        away=g.get("awayTeam", {}).get("abbrev"), home=g.get("homeTeam", {}).get("abbrev"),
                        away_name=g.get("awayTeam", {}).get("commonName", {}).get("default", ""),
                        home_name=g.get("homeTeam", {}).get("commonName", {}).get("default", ""),
                        link=g.get("gameCenterLink") or "",
                    ))
        return games

    @staticmethod
    def _nhl_results():
        results = []
        data = read_json("nhl_scores_now") or {}
        for g in data.get("games", []):
            if g.get("gameState") not in ("OFF", "FINAL"):
                continue
            results.append(dict(
                date=g.get("gameDate"), away=g.get("awayTeam", {}).get("abbrev"),
                home=g.get("homeTeam", {}).get("abbrev"),
                away_name=g.get("awayTeam", {}).get("name", {}).get("default", ""),
                home_name=g.get("homeTeam", {}).get("name", {}).get("default", ""),
                away_score=g.get("awayTeam", {}).get("score"),
                home_score=g.get("homeTeam", {}).get("score"),
            ))
        return results

    @staticmethod
    def _mlb_games():
        games = []
        data = read_json("mlb_schedule") or {}
        for d in data.get("dates", []):
            for g in d.get("games", []):
                t = g.get("teams", {})
                away, home = t.get("away", {}), t.get("home", {})
                games.append(dict(
                    pk=g.get("gamePk"), date=g.get("gameDate"), official_date=g.get("officialDate"),
                    state=g.get("status", {}).get("abstractGameState"),
                    away=away.get("team", {}).get("name"), home=home.get("team", {}).get("name"),
                    away_abbr=away.get("team", {}).get("abbreviation"), home_abbr=home.get("team", {}).get("abbreviation"),
                    away_score=away.get("score"), home_score=home.get("score"),
                    away_pitcher=(away.get("probablePitcher") or {}).get("fullName"),
                    home_pitcher=(home.get("probablePitcher") or {}).get("fullName"),
                ))
        return games

    @staticmethod
    def _mlb_standings():
        out = {}
        data = read_json("mlb_standings") or {}
        for group in data.get("records", []):
            for tr in group.get("teamRecords", []):
                name = tr.get("team", {}).get("name")
                if not name:
                    continue
                out[norm(name)] = {k: tr.get(k) for k in ("wins", "losses", "gamesPlayed",
                                                           "runsScored", "runsAllowed",
                                                           "runDifferential", "winningPercentage")}
                out[norm(name)]["abbr"] = tr.get("team", {}).get("abbreviation")
        return out

    def text_has(self, key: str, needle: str) -> bool:
        n = norm(needle)
        return bool(n and n in norm(self.texts.get(key, "")))


OFFICIAL = Official()

NBA_ALIAS = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets", "CHA": "Charlotte Hornets",
    "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers", "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets",
    "DET": "Detroit Pistons", "GS": "Golden State Warriors", "GSW": "Golden State Warriors", "HOU": "Houston Rockets",
    "IND": "Indiana Pacers", "LAC": "LA Clippers", "LAL": "Los Angeles Lakers", "LA": "Los Angeles Lakers",
    "MEM": "Memphis Grizzlies", "MIA": "Miami Heat", "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves",
    "NO": "New Orleans Pelicans", "NY": "New York Knicks", "NYK": "New York Knicks", "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns", "POR": "Portland Trail Blazers",
    "SAC": "Sacramento Kings", "SA": "San Antonio Spurs", "SAS": "San Antonio Spurs", "TOR": "Toronto Raptors",
    "UTA": "Utah Jazz", "WSH": "Washington Wizards",
}


# ---------------------------------------------------------------------------
# Event parsing.
# ---------------------------------------------------------------------------
def parse_schema(root: dict) -> dict:
    raw = root.get("eventSchema")
    if not raw or not isinstance(raw, str):
        return {}
    m = re.search(r"<script[^>]*>(.*?)</script>", raw, re.S)
    try:
        return json.loads(m.group(1)) if m else {}
    except Exception:
        return {}


def split_competitors(schema: dict, name: str) -> list[str]:
    comps = [c.get("name", "") for c in (schema.get("competitor") or []) if isinstance(c, dict)]
    if len(comps) == 2:
        # OLBG sometimes appends the match label to the second competitor.
        for label in (" One Day Match", " T20 Match", " T20 Big Bash", " 1st T20 Match",
                      " 3rd T20 Match", " 3rd ODI", " T20", " 1st Test", " 3rd Test"):
            comps[1] = comps[1].replace(label, "")
        return [c.strip() for c in comps]
    m = re.split(r"\s+(?:vs|v|@)\s+", name)
    return [x.strip() for x in m] if len(m) == 2 else []


def first_abbrev(name: str) -> str:
    m = re.match(r"^([A-Z]{2,3})\b", name.strip())
    return m.group(1) if m else ""


def load_events() -> list[dict]:
    events = []
    for eid, rec in MANIFEST["events"].items():
        path = CAP / "olbg-events" / f"{eid}.json"
        if not path.exists() or rec.get("status") != 200:
            continue
        roots = collector.decoded_roots(path.read_bytes())
        root = next((r for r in roots if isinstance(r, dict) and isinstance(r.get("event"), dict)), None)
        if not root:
            continue
        ev = root["event"]
        schema = parse_schema(root)
        name = schema.get("name") or re.sub(r"\s+Tips\s*$", "", str(root.get("pageTitle") or "")).strip()
        start = schema.get("startDate") or (datetime.fromtimestamp(ev["unixTimestamp"], timezone.utc).isoformat().replace("+00:00", "Z") if ev.get("unixTimestamp") else "")
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        except Exception:
            start_dt = None
        markets = []
        for mk in ev.get("markets") or []:
            tips = []
            for t in mk.get("tips") or []:
                tips.append(dict(
                    selection=t.get("selection") or "",
                    decimal=str(t.get("odds") or ""),
                    american=str(t.get("american_odds") or ""),
                    fractional=str(t.get("fractional_odds") or ""),
                    win_tips=int(t.get("win_tips") or 0),
                    total_tips=int(t.get("win_tips_count") or 0),
                    confidence=t.get("confidence"),
                    expired=bool(t.get("expired")),
                ))
            markets.append(dict(id=mk.get("id"), name=mk.get("name") or "Unnamed market", tips=tips))
        sport = SPORT_BY_OLBG.get(rec["sport_key"])
        if not sport:
            continue
        page_url = rec["page_url"] or ""
        if page_url.startswith("/"):
            page_url = "https://www.olbg.com" + page_url
        events.append(dict(
            id=eid, sport_key=rec["sport_key"], sport=sport["label"], sport_slug=sport["key"],
            name=name, competitors=split_competitors(schema, name),
            competition=(ev.get("leagueName") or ev.get("tournament") or "").strip(),
            start_utc=start, start_dt=start_dt.isoformat() if start_dt else "",
            horizon=horizon(start_dt),
            olbg_url=page_url, olbg_data_url=rec["url"],
            markets=markets, market_names=[m["name"] for m in markets],
            upcoming=bool(start_dt and start_dt > CAPTURE_DT),
            expired=bool(markets) and all(t["expired"] for m in markets for t in m["tips"]),
        ))
    events.sort(key=lambda e: (e["start_utc"] or "9999", e["id"]))
    return events


def horizon(start_dt) -> str:
    if not start_dt:
        return "unknown"
    if start_dt.date() == CAPTURE_DT.date():
        return "today"
    if start_dt <= CAPTURE_DT + timedelta(days=7):
        return "this-week"
    return "later"


# ---------------------------------------------------------------------------
# Official evidence crosswalk.
# ---------------------------------------------------------------------------
def base_official(sport: dict, ev: dict) -> dict:
    key = sport["official_key"]
    return dict(
        url=official_url(key) or "", name=sport["official_name"], level="directory",
        urls=[dict(name=sport["official_name"], url=official_url(key) or "")],
        facts=[], form=[], stats=[], availability="", flags=[],
        secondary=dict(name=sport["secondary_name"], url=official_url(sport["secondary_key"]) or ""),
    )


def official_for_event(sport: dict, ev: dict) -> dict:
    key = sport["key"]
    out = base_official(sport, ev)
    comps = ev["competitors"]
    name = ev["name"]
    try:
        if key == "ice-hockey":
            official_nhl(out, ev, comps)
        elif key == "baseball":
            official_mlb(out, ev, comps)
        elif key == "tennis":
            official_tennis(out, ev, comps)
        elif key == "basketball":
            official_basketball(out, ev, comps)
        elif key == "handball":
            official_handball(out, ev, comps)
        elif key == "motor-racing":
            official_motorsport(out, ev)
        elif key == "golf":
            official_golf(out, ev)
        elif key == "cricket":
            official_cricket(out, ev, comps)
        elif key == "rugby-union":
            official_rugby_union(out, ev, comps)
        elif key == "volleyball":
            official_volleyball(out, ev, comps)
        elif key == "gaelic-sports":
            official_gaelic(out, ev, comps)
        elif key == "darts":
            official_darts(out, ev)
        elif key == "rugby-league":
            official_rugby_league(out, ev)
        else:
            out["flags"].append("No event-specific official crosswalk is available for this sport.")
    except Exception as exc:  # never fail the build; publish the gap instead
        out["flags"].append(f"Official crosswalk could not be completed: {type(exc).__name__}.")
    if not out["facts"]:
        out["flags"].append("No official event-level fact matched this OLBG row; official link is a sport directory.")
    if not out["availability"]:
        out["flags"].append("No official injury/availability report was captured for this fixture.")
    return out


def official_nhl(out, ev, comps):
    if "nhl" not in norm(ev["competition"]):
        out["flags"].append("This is a European league fixture; the captured NHL feed does not cover it.")
        return
    aa, ha = (first_abbrev(x) for x in comps) if len(comps) == 2 else ("", "")
    game = next((g for g in OFFICIAL.nhl_games if g["away"] == aa and g["home"] == ha), None)
    if game:
        link = "https://www.nhl.com" + game["link"] if game["link"].startswith("/") else game["link"]
        out["url"] = link or out["url"]
        out["level"] = "event"
        out["urls"].append(dict(name="NHL official game centre", url=out["url"]))
        out["facts"].append(f"NHL's official schedule lists {aa} at {ha} at {game['start'][:16].replace('T', ' ')} UTC under game ID {game['id']}.")
        if ev["start_utc"][:16] and game["start"][:16] != ev["start_utc"][:16]:
            out["flags"].append("OLBG start time differs from the NHL official start time; check the game centre before staking.")
    for abbr in (aa, ha):
        row = OFFICIAL.nhl_standings.get(abbr)
        if not row:
            continue
        gp = row.get("gamesPlayed") or 0
        gf, ga = row.get("goalFor") or 0, row.get("goalAgainst") or 0
        out["stats"].append(f"{abbr} have {row.get('wins')}-{row.get('losses')}-{row.get('otLosses')} from {gp} games with {gf} goals for and {ga} against in the NHL standings feed.")
        if gp:
            out.setdefault("_rates", {})[abbr] = dict(gf=gf / gp, ga=ga / gp,
                                                     pts=(row.get("points") or 0) / max(gp, 1))
        l10 = f"{row.get('l10Wins')}-{row.get('l10Losses')}-{row.get('l10OtLosses')}" if row.get("l10Wins") is not None else ""
        if l10:
            out["form"].append(f"{abbr}'s last ten NHL games are {l10} with a {row.get('l10GoalDifferential')} goal differential.")
    for abbr in (aa, ha):
        results = [r for r in OFFICIAL.nhl_results if abbr in (r["away"], r["home"])][:2]
        for r in results:
            if r["away_score"] is not None and r["home_score"] is not None:
                out["form"].append(f"NHL's official score feed records {r['away']} {r['away_score']}-{r['home_score']} {r['home']} on {r['date']}.")
    out["_strength"] = out.get("_rates", {})


def official_mlb(out, ev, comps):
    aa, ha = (first_abbrev(x) for x in comps) if len(comps) == 2 else ("", "")
    day = ev["start_utc"][:10]
    games = [g for g in OFFICIAL.mlb_games if {g["away_abbr"], g["home_abbr"]} == {aa, ha}]
    # Match on the UTC gameDate (OLBG timestamps are UTC); officialDate is the
    # local US calendar date and is one day earlier for night games.
    upcoming = next((g for g in games if (g["date"] or "")[:10] == day and g["state"] != "Final"), None)
    if upcoming:
        out["url"] = f"https://www.mlb.com/gameday/{upcoming['pk']}"
        out["level"] = "event"
        out["urls"].append(dict(name="MLB official gameday", url=out["url"]))
        out["facts"].append(f"MLB's official schedule lists game {upcoming['pk']} at {upcoming['date'][:16].replace('T', ' ')} UTC (official date {upcoming['official_date']}) with {upcoming['away']} at {upcoming['home']}.")
        if upcoming["away_pitcher"] or upcoming["home_pitcher"]:
            out["facts"].append(f"MLB lists {upcoming['away_pitcher'] or 'an unconfirmed starter'} and {upcoming['home_pitcher'] or 'an unconfirmed starter'} as probable pitchers.")
        if (upcoming["date"] or "")[:16] != ev["start_utc"][:16]:
            out["flags"].append("OLBG start time differs from MLB's official start time; confirm on the linked game page.")
    finals = [g for g in games if g["state"] == "Final" and g["away_score"] is not None][:3]
    for g in finals:
        out["form"].append(f"MLB's official feed records {g['away']} {g['away_score']}-{g['home_score']} {g['home']} on {g['official_date']}.")
    for g in games:
        for side, abbr in (("away", g["away_abbr"]), ("home", g["home_abbr"])):
            row = next((v for k, v in OFFICIAL.mlb_standings.items() if v.get("abbr") == abbr), None)
            if row and abbr not in [x[:3] for x in out["stats"]]:
                out["stats"].append(f"{abbr} finished the MLB regular season {row.get('wins')}-{row.get('losses')} with {row.get('runsScored')} runs scored and {row.get('runsAllowed')} allowed in the official standings feed.")
    if finals:
        total = [g["away_score"] + g["home_score"] for g in finals]
        out["_total_estimate"] = round(sum(total) / len(total), 2)


TENNIS_DRAWS = {
    "WTA Guangzhou": ("wta_guangzhou_draws", "WTA official Guangzhou Open 2026 draw"),
    "WTA Tokyo": ("wta_tokyo_draws", "WTA official Toray Pan Pacific Open 2026 draw"),
    "WTA Courmayeur": ("wta_courmayeur_draws", "WTA official Courmayeur 125 2026 draw"),
    "WTA Queretaro": ("wta_queretaro_draws", "WTA official Queretaro 125 2026 draw"),
    "WTA Curitiba": ("wta_curitiba_draws", "WTA official Curitiba 125 2026 draw"),
    "ATP Vienna": ("atp_vienna_draws", "ATP official Vienna 2026 draw"),
    "ATP Basel": ("atp_basel_draws", "ATP official Basel 2026 draw"),
}


def official_tennis(out, ev, comps):
    competition = ev["competition"] or ""
    draw = TENNIS_DRAWS.get(competition)
    if draw:
        key, label = draw
        url = official_url(key)
        if url:
            out["url"] = url
            out["name"] = label
            out["urls"][0] = dict(name=label, url=url)
        ok = official_ok(key)
        if not ok:
            out["flags"].append(f"{label} returned HTTP {MANIFEST['official'].get(key, {}).get('status')} at capture; the link is supplied for manual review.")
        found = [p for p in comps if OFFICIAL.text_has(key, p)]
        if len(found) >= 2:
            out["level"] = "event"
            out["facts"].append(f"The {label} page lists both {' and '.join(found)} in its singles draw.")
        elif found:
            out["level"] = "competition"
            out["facts"].append(f"The {label} page was captured; {', '.join(found)} appears in the draw data.")
            out["flags"].append("Only one player from this OLBG match was found in the official draw text.")
        else:
            out["level"] = "competition" if ok else "directory"
            out["facts"].append(f"The {label} page is the official tournament-level source for this event.")
            out["flags"].append("Neither player name was matched inside the captured official draw text, so the official link is tournament-level rather than match-level.")
    # WTA official rankings are the captured official source for ranked players.
    ranks = []
    for player in comps:
        rec = OFFICIAL.wta.get(norm(player))
        if rec:
            ranks.append((player, rec))
            out["stats"].append(f"The WTA official singles ranking lists {player} at No. {rec['rank']} with {rec['points']} points ({rec['country']}).")
    if ranks:
        out["level"] = "event" if out["level"] == "event" else "competition"
        out["_ranks"] = {norm(p): r["rank"] for p, r in ranks}
    elif not draw:
        out["flags"].append("No official WTA/ATP ranking or draw page matched this event; ATP's official pages were blocked with HTTP 403 at capture.")
        out["urls"].append(dict(name="ATP Tour official scores (HTTP 403 at capture)",
                                url="https://www.atptour.com/en/scores/current"))
    out["urls"].append(dict(name="WTA official tournaments", url=official_url("wta_tournaments")))


def official_basketball(out, ev, comps):
    if "NBA" in (ev["competition"] or ""):
        full = [NBA_ALIAS.get(first_abbrev(c), "") for c in comps]
        if all(full) and all(OFFICIAL.text_has("nba_games", f) for f in full):
            out["level"] = "competition"
            out["facts"].append(f"NBA's official games page lists {full[0]} and {full[1]} among the day's matchups.")
        else:
            out["flags"].append("The captured NBA games page did not expose an event-specific box score or team record.")
        out["url"] = official_url("nba_games")
    else:
        out["flags"].append("EuroLeague and other European official endpoints returned HTTP 429/403 at capture; the official league link is provided for review.")
        out["url"] = official_url("euroleague_games_page") or "https://www.euroleaguebasketball.net/en/euroleague/games/"
        out["urls"].append(dict(name="EuroLeague official games (capture blocked)", url=out["url"]))
    out["urls"][0]["url"] = out["url"]


def official_handball(out, ev, comps):
    aliases = {
        "Veszprem": "Veszprem HC", "FC Porto": "FC Porto", "Fuchse Berlin": "Fuchse Berlin",
        "RK Partizan": "RK Partizan AdmiralBet", "GOG": "GOG", "Sporting CP": "Sporting Clube de Portugal",
        "Pick Szeged": "OTP Bank - PICK Szeged", "IFK Kristianstad": "IFK Kristianstad",
        "PSG Handball": "Paris Saint-Germain Handball", "Aalborg Handbold": "Aalborg Handbold",
        "SC Magdeburg": "SC Magdeburg", "HC Kriens Luzern": "HC Kriens-Luzern",
        "KS Kielce": "Industria Kielce", "Kolstad": "Kolstad Handball", "Wisla Plock": "Orlen Wisla Plock",
        "Nantes": "HBC Nantes", "HC Vardar": "HC Vardar 1961", "MT Melsungen": "MT Melsungen",
        "RK Celje": "RK Celje Pivovarna Lasko", "RK Zagreb": "RK Zagreb",
        "Montpellier": "Montpellier Handball", "Dinamo Bucuresti": "Dinamo Bucuresti",
    }
    matched = 0
    for c in comps:
        key = norm(aliases.get(c, c))
        row = OFFICIAL.ehf.get(key)
        if not row:
            row = next((v for k, v in OFFICIAL.ehf.items() if key and (key in k or k in key)), None)
        if row:
            matched += 1
            out["stats"].append(f"EHF Champions League official standings list {row['name']} at {row['w']}-{row['d']}-{row['l']} from {row['gp']} games with {row['gf']}:{row['ga']} goals and {row['pts']} points.")
            out.setdefault("_rates", {})[norm(c)] = dict(gf=row["gf"] / max(row["gp"], 1),
                                                          ga=row["ga"] / max(row["gp"], 1),
                                                          pts=row["pts"] / max(row["gp"], 1))
    if matched:
        out["level"] = "competition"
        out["facts"].append("The official EHF Champions League group table was captured for this round.")
    if OFFICIAL.text_has("ehfcl_matches", comps[0] if comps else ev["name"]):
        out["facts"].append("The official EHF Champions League matches page lists this fixture's round.")
    out["_strength"] = out.get("_rates", {})


def official_motorsport(out, ev):
    out["url"] = official_url("f1_driver_standings")
    drivers = [norm(x) for x in OFFICIAL.f1]
    out["level"] = "competition"
    out["facts"].append("Formula 1's official 2026 driver standings and race calendar were captured.")
    out["stats"].append("Official F1 standings: " + "; ".join(
        f"{r['pos']}. {r['name']} ({r['team']}) {r['points']} pts" for r in
        sorted(OFFICIAL.f1.values(), key=lambda x: x["pos"])[:5]) + ".")
    out["urls"].append(dict(name="Formula 1 official 2026 calendar", url=official_url("formula1_calendar")))
    if OFFICIAL.text_has("formula1_calendar", "Mexico"):
        out["facts"].append("The official F1 calendar includes the Mexico City Grand Prix round.")
    out["_f1"] = OFFICIAL.f1


def official_golf(out, ev):
    out["url"] = official_url("lpga_tournaments")
    out["level"] = "competition" if OFFICIAL.text_has("lpga_tournaments", ev["name"]) else "directory"
    if OFFICIAL.text_has("lpga_tournaments", "Maybank Championship") and "Maybank" in ev["name"]:
        out["facts"].append("LPGA's official tournaments page lists the Maybank Championship for October 29 - November 1, 2026 at Kuala Lumpur Golf & Country Club with a $3.00M purse.")
        out["stats"].append("LPGA lists Miyu Yamashita as the 2025 Maybank champion at 18 under par.")
    elif "Mexico" in ev["name"] or "Simmons" in ev["name"]:
        out["url"] = official_url("pgatour_schedule")
        out["facts"].append("The PGA TOUR official schedule was captured; this event was not identity-matched within the captured schedule text.")
        out["flags"].append("Golf event identity could not be matched to a captured official tournament page.")
    else:
        out["flags"].append("Golf event identity could not be matched to a captured official tournament page.")
    out["urls"][0]["url"] = out["url"]


def official_cricket(out, ev, comps):
    out["url"] = official_url("icc_fixtures")
    found = sum(1 for c in comps if OFFICIAL.text_has("icc_fixtures", c))
    if found >= 2:
        out["level"] = "competition"
        out["facts"].append(f"ICC's official fixtures and results page lists the {' vs '.join(comps)} series.")
        out["flags"].append("The ICC fixtures page is JavaScript-rendered; this identity match comes from embedded official page text rather than a structured fixture API.")
    elif OFFICIAL.text_has("cricket_australia_fixtures", comps[0] if comps else ev["name"]):
        out["url"] = official_url("cricket_australia_fixtures")
        out["level"] = "competition"
        out["facts"].append("Cricket Australia's official fixtures page was captured with this competition's schedule.")
    else:
        out["flags"].append("No official event-level fixture match for this cricket row.")
    out["urls"][0]["url"] = out["url"]


def official_rugby_union(out, ev, comps):
    out["url"] = official_url("lnr_prod2") if "Division 2" in (ev["competition"] or "") else official_url("epcr_matches")
    key = "lnr_prod2" if "Division 2" in (ev["competition"] or "") else "epcr_matches"
    found = sum(1 for c in comps if OFFICIAL.text_has(key, c))
    if found >= 2:
        out["level"] = "competition"
        out["facts"].append(f"The official {'LNR Pro D2' if key == 'lnr_prod2' else 'EPCR'} fixtures page lists {' and '.join(comps)}.")
    else:
        out["flags"].append("No official event-level fixture match for this rugby union row.")
    out["urls"][0]["url"] = out["url"]


def official_volleyball(out, ev, comps):
    found = [c for c in comps if OFFICIAL.text_has("cev_match_centres", c)]
    if found:
        out["level"] = "competition"
        out["facts"].append(f"CEV's official match-centre directory was captured; {', '.join(found)} appear in the competition listings.")
    else:
        out["flags"].append("Domestic volleyball clubs in this row are not covered by the CEV match-centre capture.")
    out["urls"][0]["url"] = official_url("cev_match_centres")


def official_gaelic(out, ev, comps):
    found = [c for c in comps if OFFICIAL.text_has("gaa_fixtures", c)]
    if found:
        out["level"] = "competition"
        out["facts"].append(f"The GAA official fixtures page was captured; {', '.join(found)} appear in the fixtures/results listings.")
    else:
        out["flags"].append("No official event-level fixture match for this Gaelic Football row.")
    out["urls"][0]["url"] = official_url("gaa_fixtures")


def official_darts(out, ev):
    out["level"] = "competition" if OFFICIAL.text_has("pdc_tournaments", ev["name"]) else "directory"
    if out["level"] == "competition":
        out["facts"].append("The PDC official tournaments page lists this event.")
    else:
        out["flags"].append("PDC's captured tournament page did not expose an event-specific card for this Players Championship / outright row.")
    out["urls"][0]["url"] = official_url("pdc_tournaments")


def official_rugby_league(out, ev):
    out["level"] = "directory"
    out["facts"].append("NRL and Super League official pages were captured, but all OLBG rows are long-dated 2027 outright markets.")
    out["flags"].append("Long-dated outright market: no official 2027 fixture, lineup or injury sheet is available in this snapshot.")
    out["url"] = official_url("nrl_draw")
    out["urls"][0]["url"] = out["url"]
    out["urls"].append(dict(name="Super League official site", url=official_url("superleague_home")))


# ---------------------------------------------------------------------------
# Line origination.
# ---------------------------------------------------------------------------
def prob_to_american(p: float) -> int:
    if p <= 0 or p >= 1:
        return 0
    return int(round(-100 * p / (1 - p))) if p >= 0.5 else int(round(100 * (1 - p) / p))


def fmt_us(value) -> str:
    if value in (None, "", 0):
        return "—"
    n = int(value)
    return f"+{n}" if n > 0 else str(n)


def valid_decimal(value: str):
    try:
        d = float(value)
        return d if d > 1.0 else None
    except Exception:
        return None


def market_family(name: str) -> str:
    n = norm(name)
    if any(x in n for x in ("total", "games won", "points total", "game totals")):
        return "total"
    if any(x in n for x in ("handicap", "pointspread", "puck line", "run line", "games won")):
        return "handicap"
    if any(x in n for x in ("tournament", "championship", "outright", "grand final", "win football", "win race")):
        return "outright"
    if any(x in n for x in ("batsman", "man of the match", "fastest qualifier", "set score", "set betting", "top team")):
        return "player"
    return "win"


def strength_tilt(ev: dict, official: dict, selections: list[dict]) -> dict:
    """Return a per-selection probability nudge from official strength data."""
    rates = official.get("_strength") or {}
    comps = ev["competitors"]
    if len(comps) != 2 or len(rates) < 2:
        return {}
    a, b = (rates.get(norm(c)) for c in comps)
    if not a or not b:
        return {}
    diff = (a.get("pts", 0) + a.get("gf", 0) - a.get("ga", 0)) - (b.get("pts", 0) + b.get("gf", 0) - b.get("ga", 0))
    scale = 0.12 if abs(diff) < 6 else 0.18
    logistic = 1 / (1 + math.exp(-diff / 3.0))
    tilt = {norm(comps[0]): logistic, norm(comps[1]): 1 - logistic}
    out = {}
    for s in selections:
        key = norm(s["selection"])
        for team, val in tilt.items():
            if team and team in key:
                out[key] = (val - 0.5) * scale
    return out


def price_market(ev: dict, official: dict, market: dict) -> dict:
    tips = [t for t in market["tips"] if valid_decimal(t["decimal"]) and t["selection"]]
    official_support = official["level"] in ("event", "competition") or bool(
        official.get("stats") or official.get("form"))
    result = dict(event_id=ev["id"], sport=ev["sport"], sport_slug=ev["sport_slug"],
                  event=ev["name"], competition=ev["competition"], start_utc=ev["start_utc"],
                  horizon=ev["horizon"], market=market["name"], family=market_family(market["name"]),
                  olbg_url=ev["olbg_url"], official_url=official["url"], official_name=official["name"],
                  official_level=official["level"], official_support=official_support,
                  selections=[], flags=[], priced=False)
    if not tips:
        result["flags"].append("No usable displayed prices in this market.")
        return result
    raw = [1 / valid_decimal(t["decimal"]) for t in tips]
    overround = sum(raw)
    market_prob = [r / overround for r in raw]
    total_tips = max((t["total_tips"] for t in tips), default=0)
    win_tips = [t["win_tips"] for t in tips]
    tip_sum = sum(win_tips)
    consensus = [w / tip_sum for w in win_tips] if tip_sum > 0 else [1 / len(tips)] * len(tips)
    w = 0.28 * (total_tips / (total_tips + 8)) if total_tips > 0 else 0.0
    fair = [(1 - w) * mp + w * cp for mp, cp in zip(market_prob, consensus)]
    tilt = strength_tilt(ev, official, tips) if result["family"] == "win" else {}
    if tilt:
        for i, t in enumerate(tips):
            fair[i] += tilt.get(norm(t["selection"]), 0.0)
    total_fair = sum(max(f, 0.00001) for f in fair)
    fair = [max(f, 0.00001) / total_fair for f in fair]
    for i, (t, mp, cp, fp) in enumerate(zip(tips, market_prob, consensus, fair)):
        displayed = re.sub(r"[^0-9+-]", "", t["american"])
        try:
            displayed_int = int(displayed)
        except Exception:
            displayed_int = prob_to_american(1 / valid_decimal(t["decimal"]))
        edge = (fp - mp) * 100
        result["selections"].append(dict(
            selection=t["selection"], decimal=t["decimal"], american=t["american"],
            fractional=t["fractional"], displayed_american=displayed_int,
            implied_pct=round(mp * 100, 2), consensus_pct=round(cp * 100, 2),
            fair_pct=round(fp * 100, 2), our_american=prob_to_american(fp),
            edge_pp=round(edge, 2), win_tips=t["win_tips"], total_tips=t["total_tips"],
        ))
    result["overround_pct"] = round((overround - 1) * 100, 2)
    result["tip_weight"] = round(w, 3)
    result["priced"] = True
    if overround > 1.35:
        result["flags"].append("High displayed overround in this market; fair prices are less certain.")
    if total_tips == 0:
        result["flags"].append("No tip-consensus count in this market; line is a de-vigged market price only.")
    if len(tips) == 1:
        result["flags"].append("Only one side of this market has a displayed price.")
    if tilt:
        result["flags"].append("Official strength feed contributes a small documented adjustment.")
    return result


# ---------------------------------------------------------------------------
# Picks and prose.
# ---------------------------------------------------------------------------
SPORT_ANGLE = {
    "golf": "Course fit and recent ball-striking form matter more here than name recognition, and an outright price has to survive a full field.",
    "volleyball": "Side-out efficiency and the first-set rotation usually decide this kind of fixture, so the quoted price deserves a second look.",
    "rugby-union": "Set-piece territory and discipline tend to swing matches in these competitions, especially when the handicap is short.",
    "cricket": "Conditions and the make-up of the XI shape this contest, and the toss can move a match price quickly.",
    "snooker": "Frame-by-frame scoring patterns matter in this market; OLBG published no tipped event in this capture.",
    "darts": "Averaging and doubling under pressure decide Players Championship events, where the draw changes quickly.",
    "baseball": "Bullpen usage and the probable starter shape the total as much as the moneyline in this series.",
    "gaelic-sports": "Club championship matches are often decided by turnover count and conversion rate inside the 45.",
    "greyhounds": "Trap draw, early pace and sectional times are the core inputs; OLBG published no tipped race in this capture.",
    "tennis": "Hold percentage and return pressure shape this matchup more than reputation, particularly in a short-format event.",
    "motor-racing": "Qualifying trim and tyre preparation drive this market, and official championship context frames the field.",
    "handball": "Six-on-six conversion and goalkeeper efficiency are the levers in these group matches.",
    "ice-hockey": "Shot quality, goaltending and special teams drive the puck line and total together.",
    "basketball": "Pace and shot profile decide whether a spread or total offers the cleaner position.",
    "rugby-league": "Long-range outright prices move on squad announcements, so it is important to separate price from certainty.",
}

MARKET_ANGLE = {
    "win": "This is a straight result selection, so the side has to finish the contest rather than merely compete.",
    "total": "This is an over/under position on the quoted number, so the fair price matters as much as the direction.",
    "handicap": "The handicap asks whether the margin clears a fixed number, which changes the risk profile of the result price.",
    "outright": "This is an ante-post or outright selection against a full field, so each-way terms and field size matter.",
    "player": "This is a player-performance market, where role and opportunity can be as important as the match result.",
}

OPENERS = [
    "The play for {event} is {selection} in the {market} market.",
    "For {event}, our selection is {selection} ({market}).",
    "Our strongest position on {event} is {selection} to land the {market} bet.",
    "{selection} is the selection we want on {event}, in the {market} market.",
    "Take {selection} in the {market} market for {event}.",
    "We are siding with {selection} on {event} ({market}).",
    "The {market} price on {selection} is the side we prefer in {event}.",
    "Our pick for {event}: {selection}, {market}.",
]

CLOSERS = [
    "Confidence is {conf} because {reason}. Recheck the linked official page and the live price before staking.",
    "We rate this {conf} confidence: {reason}. Prices move, so confirm the market on the linked OLBG event page.",
    "This is a {conf}-confidence selection — {reason}. Availability and the official schedule should be checked again before bet placement.",
    "Confidence: {conf}. {reason}. Use the source links to confirm the fixture and current odds first.",
]


def compose_prediction(pick: dict, ev: dict, official: dict, idx: int) -> str:
    sport = ev["sport_slug"]
    conf = pick["confidence"]
    selection = pick["selection"]
    market = pick["market"]
    opener = OPENERS[idx % len(OPENERS)].format(event=ev["name"], selection=selection, market=market.lower())
    bits = [opener,
            SPORT_ANGLE.get(sport, ""),
            MARKET_ANGLE.get(pick["family"], MARKET_ANGLE["win"])]
    if pick.get("selection_fact"):
        bits.append(pick["selection_fact"])
    if pick["edge_pp"] >= 0.05:
        edge_text = f"an edge of {pick['edge_pp']:.1f} percentage points over the de-vigged market line"
    elif pick["edge_pp"] > -0.05:
        edge_text = "no measurable edge over the de-vigged market line, so this is a price-confirmation position"
    else:
        edge_text = f"a {abs(pick['edge_pp']):.1f} percentage point shortfall to the de-vigged market line, so stake size should be minimal"
    bits.append(
        f"OLBG displays {fmt_us(pick['displayed_american'])} (decimal {pick['decimal']}) for this selection, while our originated fair price is {fmt_us(pick['our_american'])} — {edge_text}.")
    if pick["total_tips"]:
        bits.append(f"{pick['win_tips']} of {pick['total_tips']} OLBG tips on this market back this side, and the event page lists {len(ev['market_names'])} markets in total ({', '.join(ev['market_names'][:4])}).")
    else:
        bits.append(f"No tip-consensus count was published for this market, so the line rests on the displayed prices across {len(ev['market_names'])} captured markets.")
    facts = (official["facts"] + official["stats"] + official["form"])
    for fact in facts[:3]:
        bits.append(fact)
    if not facts:
        bits.append("The captured official pages did not expose an event-specific form or statistics line for this fixture; that gap is published on the Flagged for Review page rather than filled with an estimate.")
    if official["availability"]:
        bits.append(official["availability"])
    else:
        bits.append("No official injury or availability report was published in the captured sources, so that field is intentionally left blank and flagged.")
    reasons = {
        "high": "the price sits inside the -250 to +10000 band, tip support is clear and the official source adds usable context",
        "medium": "the price is in range but supporting evidence is thinner",
        "low": "the edge is narrow or the supporting official evidence is incomplete",
    }
    bits.append(CLOSERS[idx % len(CLOSERS)].format(conf=conf, reason=reasons[conf]))
    text = " ".join(b for b in bits if b)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def in_band(american: int) -> bool:
    return -250 <= american <= 10000


def selection_official_fact(sport_slug: str, selection: str, ev: dict) -> str:
    """A selection-specific official statistic, when the captured feed has one."""
    key = norm(selection)
    try:
        if sport_slug == "motor-racing":
            row = OFFICIAL.f1.get(key)
            if row:
                return (f"Formula 1's official 2026 standings place {row['name']} {row['pos']} "
                        f"with {row['points']} points for {row['team']}.")
        if sport_slug == "tennis":
            row = OFFICIAL.wta.get(key)
            if row:
                return f"The official WTA singles ranking lists {selection} at No. {row['rank']} with {row['points']} points."
        if sport_slug == "handball":
            row = next((v for k, v in OFFICIAL.ehf.items() if key and (key in k or k in key)), None)
            if row:
                return (f"EHF's official group table records {row['name']} at {row['w']}-{row['d']}-{row['l']} "
                        f"with {row['gf']}:{row['ga']} goals.")
        if sport_slug == "ice-hockey":
            abbr = first_abbrev(selection)
            row = OFFICIAL.nhl_standings.get(abbr)
            if row:
                return (f"NHL's official standings put {abbr} at {row['wins']}-{row['losses']}-{row['otLosses']} "
                        f"with {row['goalFor']} goals for and {row['goalAgainst']} against.")
        if sport_slug == "baseball":
            abbr = first_abbrev(selection)
            row = next((v for v in OFFICIAL.mlb_standings.values() if v.get("abbr") == abbr), None)
            if row:
                return (f"MLB's official standings list {abbr} at {row['wins']}-{row['losses']} "
                        f"with {row['runsScored']} runs scored and {row['runsAllowed']} allowed.")
        if sport_slug == "golf" and "Maybank" in (ev["competition"] or "") and norm("Miyu Yamashita") in key:
            return "LPGA's official tournament page lists Miyu Yamashita as the 2025 Maybank Championship winner at 18 under par."
    except Exception:
        return ""
    return ""


def choose_picks(events: list[dict], official_by_id: dict, lines: list[dict]) -> list[dict]:
    candidates = []
    by_event = {e["id"]: e for e in events}
    for line in lines:
        ev = by_event.get(line["event_id"])
        if not ev or not ev["upcoming"] or not line["priced"]:
            continue
        sels = line["selections"]
        # Two-sided markets: one side only (never back both outcomes).
        # Multi-runner outright/player markets: allow several independent sides.
        if len(sels) > 3 and line["family"] in ("outright", "player"):
            shortlist = sorted(sels, key=lambda s: s["edge_pp"], reverse=True)[:8]
            max_per_market = 5
        else:
            shortlist = [max(sels, key=lambda s: s["edge_pp"])]
            max_per_market = 1
        for best in shortlist:
            # A zero-edge, price-only row is still published as a low-confidence
            # pick where the sport has no other in-range market.
            if not in_band(best["displayed_american"]) or best["edge_pp"] < -0.01:
                continue
            pick = dict(best)
            pick.update(
                event_id=ev["id"], sport=ev["sport"], sport_slug=ev["sport_slug"],
                event=ev["name"], competition=ev["competition"], start_utc=ev["start_utc"],
                horizon=ev["horizon"], market=line["market"], family=line["family"],
                olbg_url=ev["olbg_url"], official_url=line["official_url"],
                official_name=line["official_name"], official_level=line["official_level"],
                official_support=line["official_support"],
                market_count=len(ev["market_names"]), market_names=ev["market_names"],
                flags=list(line["flags"]), max_per_market=max_per_market,
                selection_fact=selection_official_fact(ev["sport_slug"], best["selection"], ev),
            )
            score = pick["edge_pp"] + 2.0 * (pick["total_tips"] / (pick["total_tips"] + 8))
            # Prefer a clear match result over an exotic or long-dated market.
            score += {"win": 1.2, "handicap": 0.8, "total": 0.8,
                      "outright": 0.0, "player": -0.3}.get(pick["family"], 0.0)
            if pick["official_support"]:
                score += 0.6
            if pick["selection_fact"]:
                score += 0.5
            if pick["horizon"] == "today":
                score += 0.4
            elif pick["horizon"] == "this-week":
                score += 0.2
            pick["score"] = round(score, 3)
            consensus = pick["consensus_pct"] / 100
            if (pick["edge_pp"] >= 1.5 and pick["total_tips"] >= 3 and consensus >= 0.55
                    and (pick["official_support"] or pick["selection_fact"])):
                pick["confidence"] = "high"
            elif pick["edge_pp"] >= 0.8 and (pick["total_tips"] >= 2 or pick["official_support"]):
                pick["confidence"] = "medium"
            else:
                pick["confidence"] = "low"
            pick["confidence_reason"] = {
                "high": "tip agreement, a positive fair-price edge and official context all align",
                "medium": "the edge is positive but one of the supporting inputs is thin",
                "low": "the edge is narrow or official support is incomplete",
            }[pick["confidence"]]
            candidates.append(pick)

    picks, used_triples, per_event, per_market = [], set(), Counter(), Counter()
    for sport in SPORTS:
        pool = [c for c in candidates if c["sport_slug"] == sport["key"]]
        pool.sort(key=lambda c: ({"high": 3, "medium": 2, "low": 1}[c["confidence"]], c["score"],
                                 -c["displayed_american"]), reverse=True)
        distinct_events = len({c["event_id"] for c in pool})
        max_per_event = 2 if distinct_events >= 3 else 5
        chosen = 0
        for cand in pool:
            if chosen >= 5:
                break
            triple = (cand["event_id"], cand["market"], cand["selection"])
            mkey = (cand["event_id"], cand["market"])
            if (triple in used_triples or per_event[cand["event_id"]] >= max_per_event
                    or per_market[mkey] >= cand["max_per_market"]):
                continue
            used_triples.add(triple)
            per_event[cand["event_id"]] += 1
            per_market[mkey] += 1
            chosen += 1
            picks.append(cand)
    for i, p in enumerate(picks):
        p["pick_no"] = i + 1
        p["sport_pick_no"] = sum(1 for x in picks[:i + 1] if x["sport_slug"] == p["sport_slug"])
    return picks


# ---------------------------------------------------------------------------
# Flags, sources and assembly.
# ---------------------------------------------------------------------------
def build_flags(events, official_by_id, lines, picks, sport_stats) -> list[dict]:
    flags = []

    def add(level, sport, subject, detail, urls):
        flags.append(dict(level=level, sport=sport, subject=subject, detail=detail,
                          urls=[u for u in urls if u and u.get("url")]))

    for sport in SPORTS:
        st = sport_stats[sport["key"]]
        primary = dict(name=sport["official_name"], url=official_url(sport["official_key"]))
        hub = dict(name="OLBG sport hub", url=sport["hub"])
        if st["events"] == 0:
            add("high", sport["label"], "No OLBG market rows",
                "The OLBG hub and All Events payloads contained no tipped event or tournament row for this sport at capture. Fewer than five picks are available (zero), nothing was priced and no pick is published.",
                [hub, primary])
        elif st["picks"] < 5:
            add("high", sport["label"], f"Only {st['picks']} picks published",
                f"The target is five picks per sport. OLBG supplied {st['events']} upcoming event row(s) and {st['lines']} priced market(s); picks were not invented beyond those rows.",
                [hub, primary])
        if st["distinct_matches"] < 5:
            add("medium", sport["label"], "Fewer than five distinct matches",
                f"OLBG supplied {st['distinct_matches']} distinct upcoming event(s) for this sport; the picks include more than one market from the same event where necessary.",
                [hub, primary])
        if not official_ok(sport["official_key"]):
            add("high", sport["label"], "Official source capture failed",
                f"The primary official source returned HTTP {MANIFEST['official'].get(sport['official_key'], {}).get('status')} at capture. The link is supplied for manual review; no fact from it was used.",
                [primary])
    for key, rec in MANIFEST["official"].items():
        if rec.get("status") != 200:
            add("medium", "All sports", f"Official source unavailable: {key}",
                f"Fetch status {rec.get('status')} ({rec.get('error', 'unavailable')}). No value was filled from this source.",
                [dict(name=key, url=rec.get("url"))])
    for ev in events:
        off = official_by_id[ev["id"]]
        srcs = [dict(name="OLBG event", url=ev["olbg_url"])] + off["urls"]
        if off["level"] == "directory":
            add("medium", ev["sport"], f"No official event crosswalk: {ev['name']}",
                "The official link is a sport/competition directory, not an event-specific fixture page. Team form, lineups and availability are left blank.", srcs)
        if not off["availability"]:
            add("low", ev["sport"], f"Availability not published: {ev['name']}",
                "No official injury, suspension or lineup report was captured for this event. The injury field is blank, not inferred.", srcs)
        if ev["horizon"] == "later":
            add("low", ev["sport"], f"Long-dated market: {ev['name']}",
                "This OLBG row starts more than seven days after the snapshot. It is an outright or future market, not a match played today.", srcs)
        if not ev["upcoming"]:
            add("low", ev["sport"], f"Already started / expired: {ev['name']}",
                "The OLBG timestamp is at or before the capture time. It is retained in the inventory but is not eligible for a pick.", srcs)
    for line in lines:
        if line["flags"] and line["priced"]:
            add("low", line["sport"], f"Market caveat: {line['event']} — {line['market']}",
                "; ".join(line["flags"]),
                [dict(name="OLBG event", url=line["olbg_url"]),
                 dict(name=line["official_name"], url=line["official_url"])])
    return flags


def main() -> int:
    events = load_events()
    official_by_id = {}
    official_rates = {}
    lines = []
    for ev in events:
        full = official_for_event(next(s for s in SPORTS if s["key"] == ev["sport_slug"]), ev)
        official_rates[ev["id"]] = full.get("_strength") or {}
        for mk in ev["markets"]:
            lines.append(price_market(ev, full, mk))
        # Internal helper keys are not part of the published payload.
        off = {k: v for k, v in full.items() if not k.startswith("_")}
        official_by_id[ev["id"]] = off
        ev["official"] = dict(url=off["url"], name=off["name"], level=off["level"])
    picks = choose_picks(events, official_by_id, lines)
    for pick in picks:
        off = official_by_id[pick["event_id"]]
        ev = next(e for e in events if e["id"] == pick["event_id"])
        pick["prediction"] = compose_prediction(pick, ev, off, pick["pick_no"] - 1)
        pick["official_urls"] = off["urls"]
        pick["facts"] = dict(identity=off["facts"], form=off["form"], stats=off["stats"],
                             selection=pick.get("selection_fact") or "",
                             availability=off["availability"] or "")
        pick["official_flags"] = off["flags"]

    # Derived totals / spreads from official scoring rates, where available.
    for ev in events:
        off = official_by_id[ev["id"]]
        rates = official_rates.get(ev["id"]) or {}
        if len(rates) == 2 and all("gf" in r and "ga" in r for r in rates.values()):
            values = list(rates.values())
            ev["independent_total"] = round(sum((v["gf"] + v["ga"]) / 2 for v in values), 2)
            ev["independent_total_source"] = off["url"]
        else:
            ev["independent_total"] = None
            ev["independent_total_source"] = ""

    sport_stats = {}
    for sport in SPORTS:
        slug = sport["key"]
        evs = [e for e in events if e["sport_slug"] == slug]
        ls = [l for l in lines if l["sport_slug"] == slug and l["priced"]]
        ps = [p for p in picks if p["sport_slug"] == slug]
        sport_stats[slug] = dict(
            key=slug, label=sport["label"], events=len(evs),
            upcoming=sum(1 for e in evs if e["upcoming"]),
            distinct_matches=len({e["id"] for e in evs if e["upcoming"]}),
            markets=sum(len(e["markets"]) for e in evs),
            lines=len(ls), priced_selections=sum(len(l["selections"]) for l in ls),
            picks=len(ps), high=sum(1 for p in ps if p["confidence"] == "high"),
            official_url=official_url(sport["official_key"]), official_name=sport["official_name"],
            secondary_url=official_url(sport["secondary_key"]), secondary_name=sport["secondary_name"],
            official_status=MANIFEST["official"].get(sport["official_key"], {}).get("status"),
            hub=sport["hub"], note=sport["note"],
        )
    flags = build_flags(events, official_by_id, lines, picks, sport_stats)
    sources = []
    third_party = {"f1_races_mirror"}
    for key, rec in sorted(MANIFEST["official"].items()):
        role = "supplemental (not official)" if key in third_party else "official"
        sources.append(dict(key=key, name=key.replace("_", " ").title(), url=rec["url"],
                            kind=rec["kind"], role=role, status=rec["status"], bytes=rec["bytes"],
                            error=rec.get("error", "")))
    for sport in SPORTS:
        sources.append(dict(key="olbg-" + sport["key"], name=f"OLBG {sport['label']} hub",
                            url=sport["hub"], kind="discovery", role="discovery", status=200,
                            bytes=MANIFEST["hubs"].get(sport["olbg"][0], {}).get("bytes", 0), error=""))

    data = dict(
        schema="olbg8.desk/2026-10-27", capture_utc=CAPTURE_UTC, build_utc=BUILD_UTC,
        as_of=CAPTURE_DT.strftime("%-d %B %Y") + " · UTC",
        timezone_note="OLBG payload timestamps are ISO UTC; the site shows UTC throughout. Where an official start time differs, the row is flagged.",
        scope=SCOPE,
        summary=dict(
            events=len(events), upcoming=sum(1 for e in events if e["upcoming"]),
            sports=len(SPORTS), sports_with_events=sum(1 for s in sport_stats.values() if s["events"]),
            sports_with_picks=sum(1 for s in sport_stats.values() if s["picks"]),
            markets=sum(len(e["markets"]) for e in events),
            priced_markets=sum(1 for l in lines if l["priced"]),
            priced_selections=sum(len(l["selections"]) for l in lines),
            picks=len(picks), high=sum(1 for p in picks if p["confidence"] == "high"),
            medium=sum(1 for p in picks if p["confidence"] == "medium"),
            low=sum(1 for p in picks if p["confidence"] == "low"),
            flags=len(flags), official_sources=len([s for s in sources if s["role"] == "official" and s["status"] == 200]),
            event_official_links=sum(1 for e in events if e["official"]["level"] == "event"),
            today_events=sum(1 for e in events if e["upcoming"] and e["horizon"] == "today"),
        ),
        sports=[sport_stats[s["key"]] for s in SPORTS],
        events=events, lines=lines, picks=picks, flags=flags, sources=sources,
        methodology=dict(
            price_formula="For every market: p_i = 1/decimal_i; q_i = p_i / sum(p) removes the displayed overround; c_i = win_tips_i / sum(win_tips) is the OLBG consensus; w = 0.28 * total_tips/(total_tips+8); fair_i ∝ (1-w)q_i + w*c_i (+ a small official-strength tilt on two-sided result markets). fair_i converts to an American price.",
            confidence="High: edge >= 1.5 pp, >= 3 market tips, >= 55% consensus, and an official event/competition link, official form/statistic, or selection-specific official ranking. Medium: edge >= 0.8 pp with >= 2 tips or official support. Low: otherwise. All published picks must display between -250 and +10000.",
            limitations="OLBG publishes tipped events, not a complete fixture database. Displayed prices are OLBG quotes at snapshot time, not live bookmaker offers. Official injury sheets were not published in the captured sources; those fields stay blank and are flagged. Our fair price is a transparent research line, not a guarantee or a prediction of outcome certainty.",
        ),
    )
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"desk dataset: {len(events)} events, {len(lines)} markets, {len(picks)} picks, {len(flags)} flags")
    for s in data["sports"]:
        print(f"  {s['label']:16s} events={s['events']:3d} upcoming={s['upcoming']:3d} lines={s['lines']:3d} picks={s['picks']} high={s['high']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
