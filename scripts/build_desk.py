#!/usr/bin/env python3
"""Session 51373243 — deterministic v2 dashboard builder.

Reads scripts/desk_data_rows.py + scripts/desk_data_picks.py and writes:
  data/dashboard.json        (app.js v2 contract)
  data/olbg-capture.json     (raw capture record)
  data/official-evidence.json
  data/line-research.json
  data/sources.json          (registry consumed by app.js sources page)

Rules baked in:
  * every event row carries an OLBG link + an official reference link
  * rows without an event-level official crosswalk get status
    "reference-only" and a visible flag (never silently passed)
  * draft prose >= 30 words, no forbidden internal terms (audited here)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import desk_data_rows as dr
import desk_data_picks as dp

FORBIDDEN = ("model", "verified")

# ---- official reference map: (sport, league) -> (url, name) -----------------
LEAGUE_OFFICIAL = {
    ("baseball", "MLB"): ("https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-27", "MLB StatsAPI schedule"),
    ("basketball", "NBA"): ("https://www.nba.com/games?date=2026-10-27", "NBA.com games (27 Oct)"),
    ("basketball", "EuroLeague"): ("https://www.euroleaguebasketball.net", "EuroLeague official site"),
    ("basketball", "EuroCup"): ("https://www.euroleaguebasketball.net/eurocup/", "EuroCup official site"),
    ("basketball", "BCL"): ("https://www.euroleaguebasketball.net/basketball-champions-league/", "Basketball Champions League site"),
    ("basketball", "Korea KBL"): ("https://www.kbl.or.kr", "KBL official site (Korean)"),
    ("basketball", "Brazil NBB"): ("https://www.cbfl.com.br", "CBF Liga (NBB) official site"),
    ("cricket", "International T20"): ("https://www.icc-cricket.com/fixtures-results", "ICC fixtures & results"),
    ("cricket", "International ODI"): ("https://www.icc-cricket.com/fixtures-results", "ICC fixtures & results"),
    ("cricket", "International Test"): ("https://www.icc-cricket.com/fixtures-results", "ICC fixtures & results"),
    ("cricket", "Franchise T20"): ("https://www.icc-cricket.com/fixtures-results", "ICC fixtures (franchise)"),
    ("cricket", "BBL Women"): ("https://www.cricket.com.au", "Cricket Australia (BBL Women)"),
    ("cricket", "NZ domestic"): ("https://www.nzcricket.co.nz", "New Zealand Cricket"),
    ("cricket", "Cricket World Cup 2027"): ("https://www.icc-cricket.com/fixtures-results", "ICC (CWC 2027 ante-post)"),
    ("darts", "PDC PC"): ("https://www.pdc.tv", "PDC official site"),
    ("darts", "PDC Worlds"): ("https://www.pdc.tv", "PDC official site"),
    ("gaelic_sports", "Cork club football"): ("https://www.gaa.ie", "GAA official site"),
    ("gaelic_sports", "GAA"): ("https://www.gaa.ie", "GAA official site"),
    ("golf", "LPGA — Kuala Lumpur"): ("https://www.lpga.com/tournaments", "LPGA official schedule"),
    ("golf", "PGA Tour"): ("https://www.pgatour.com", "PGA Tour official site"),
    ("golf", "Korn Ferry Tour"): ("https://www.kornferrytour.com", "Korn Ferry Tour official site"),
    ("handball", "EHF CL (men)"): ("https://ehfcl.eurohandball.com/men/2026-27/matches/", "EHF Champions League schedule"),
    ("handball", "Germany Bundesliga"): ("https://www.handball-bundesliga.de", "Handball-Bundesliga official site"),
    ("handball", "Sweden Women"): ("https://svenskhandboll.se", "Svensk Handboll official site"),
    ("ice_hockey", "NHL"): ("https://www.nhl.com/standings", "NHL.com standings"),
    ("ice_hockey", "Finland SM Liiga"): ("https://www.liiga.fi", "Liiga official site"),
    ("ice_hockey", "Swedish Hockey League"): ("https://www.shl.se", "SHL official site"),
    ("ice_hockey", "Germany Eishockey Liga"): ("https://www.deutsche-eishockey-liga.de", "DEL official site"),
    ("ice_hockey", "Switzerland NLA"): ("https://www.nla.ch", "NLA official site"),
    ("ice_hockey", "Austria EHL"): ("https://www.eishockeyliga.at", "Austrian Eishockey Liga"),
    ("ice_hockey", "Danish Metal Ligaen"): ("https://www.hockeyligaen.dk", "Danish Metal Ligaen official site"),
    ("motor_racing", "F1"): ("https://www.formula1.com/en/racing/2026", "Formula 1 2026 calendar"),
    ("rugby_league", "NRL (Australia)"): ("https://www.nrl.com", "NRL official site"),
    ("rugby_league", "Super League"): ("https://www.superleague.com", "Super League official site"),
    ("rugby_union", "Pro D2 J9"): ("https://prod2.lnr.fr/calendrier-et-resultats", "LNR Pro D2 calendar (J9)"),
    ("rugby_union", "Top 14 / Pro D2"): ("https://top14.lnr.fr", "LNR Top 14 / Pro D2"),
    ("rugby_union", "Six Nations 2027"): ("https://www.sixnationsrugby.com", "Six Nations official site"),
    ("rugby_union", "United Rugby Championship"): ("https://www.urc-rugby.com", "URC official site"),
    ("tennis", "ATP (Basel/Vienna swing)"): ("https://www.atptour.com/en/scores/current", "ATP Tour current scores"),
    ("tennis", "ATP Basel"): ("https://www.atptour.com/en/scores/current", "ATP Tour current scores"),
    ("tennis", "ATP Basel R2"): ("https://www.atptour.com/en/scores/current", "ATP Tour current scores"),
    ("tennis", "WTA (Bangkok week)"): ("https://www.wtatennis.com", "WTA official site"),
    ("volleyball", "Turkey"): ("https://tvf.org.tr", "Turkish Volleyball Federation"),
    ("volleyball", "Turkey Men"): ("https://tvf.org.tr", "Turkish Volleyball Federation"),
    ("volleyball", "Italy Serie A1 Women"): ("https://www.pallavolo-seriesa.it", "Italian Serie A1 (Lega) site"),
    ("volleyball", "Poland Women"): ("https://www.1liga.pl", "Polish 1 Liga women's site"),
    ("volleyball", "Brazil"): ("https://www.cbv.com.br", "Brazilian Volleyball Confederation"),
    ("volleyball", "Brazil Women"): ("https://www.cbv.com.br", "Brazilian Volleyball Confederation"),
    ("volleyball", "Germany Women"): ("https://www.dvb.de", "Deutscher Volleyball Bund"),
}

SPORT_OFFICIAL = {
    "golf": ("https://www.lpga.com/tournaments", "LPGA official schedule", None, None),
    "volleyball": ("https://www.fivb.com", "FIVB (club rows use national league sites per row)", None, None),
    "rugby_union": ("https://prod2.lnr.fr/calendrier-et-resultats", "LNR Pro D2 calendar (J9)",
                    "https://top14.lnr.fr", "LNR Top 14 (J7 results)"),
    "cricket": ("https://www.icc-cricket.com/fixtures-results", "ICC fixtures & results", None, None),
    "snooker": ("https://wst.tv", "World Snooker Tour (hub empty today)", None, None),
    "darts": ("https://www.pdc.tv", "PDC official site (cookie-walled at capture)", None, None),
    "baseball": ("https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-27", "MLB StatsAPI schedule", None, None),
    "gaelic_sports": ("https://www.gaa.ie", "GAA official site", None, None),
    "greyhounds": (None, None, None, None),
    "tennis": ("https://www.atptour.com/en/scores/current", "ATP Tour current scores",
               "https://www.wtatennis.com", "WTA official site"),
    "motor_racing": ("https://www.formula1.com/en/racing/2026", "Formula 1 2026 calendar", None, None),
    "handball": ("https://ehfcl.eurohandball.com/men/2026-27/matches/", "EHF Champions League schedule",
                 "https://www.handball-bundesliga.de", "Handball-Bundesliga site"),
    "ice_hockey": ("https://www.nhl.com/standings", "NHL.com standings",
                   "https://www.liiga.fi", "Liiga official site"),
    "basketball": ("https://www.nba.com/games?date=2026-10-27", "NBA.com games (27 Oct)",
                   "https://www.euroleaguebasketball.net", "EuroLeague official site"),
    "rugby_league": ("https://www.nrl.com", "NRL official site",
                     "https://www.superleague.com", "Super League official site"),
}

GENERIC_FLAG = ("No event-level official crosswalk in this capture; official reference is "
                "sport/league-level only, so event identity is unconfirmed.")
TIME_FLAG_CRICKET = ("OLBG display time is UK-relative and payload timestamps diverge from "
                     "official viewer-zone times; treat the ICC page as the time authority (F-1027-02).")
TIME_FLAG_RUGBYU = ("OLBG payload timestamps diverge from LNR official kickoffs; use the LNR "
                    "calendar time (F-1027-02).")


def to_iso(ts):
    if ts in (None, ""):
        return None
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def amer_num(value):
    if value in (None, ""):
        return None
    try:
        n = float(value)
        return int(n) if n == int(n) else n
    except (TypeError, ValueError):
        return value


def main() -> None:
    errors: list[str] = []
    picks_by_event: dict[str, list] = {}
    for p in dp.PICKS:
        picks_by_event.setdefault(p[1], []).append(p)
        if len(p[8].split()) < 30:
            errors.append(f"pick {p[1]} prose under 30 words")
        for b in FORBIDDEN:
            if b in p[8].lower():
                errors.append(f"pick {p[1]} contains banned word {b!r}")
    events = []
    for r in dr.ROWS:
        official_key = r.get("official")
        official_ref = dr.OFFICIAL.get(official_key) if official_key else None
        league_ref = LEAGUE_OFFICIAL.get((r["sport"], r["league"]))
        if official_ref:
            off_url, off_name, status = official_ref["url"], official_ref["name"], "event-confirmed"
        else:
            off_url, off_name = (league_ref or (None, None))
            status = "reference-only"
        if off_url is None:
            errors.append(f"row {r['event_id']}: no official reference available")
            off_url, off_name, status = "", "no reference captured", "reference-only"

        flags = list(r.get("flags") or [])
        if status == "reference-only" and not flags:
            flags.append(GENERIC_FLAG)
        if status == "event-confirmed" and r["sport"] == "cricket" and not any("time" in f for f in flags):
            flags.append(TIME_FLAG_CRICKET)
        if status == "event-confirmed" and r["sport"] == "rugby_union" and not any("LNR" in f for f in flags):
            flags.append(TIME_FLAG_RUGBYU)

        desk = r.get("desk")
        picks = picks_by_event.get(r["event_id"], [])
        primary = picks[0] if picks else None

        event = {
            "id": r["event_id"],
            "sportKey": r["sport"],
            "sport": dr.SPORT_LABELS[r["sport"]],
            "eventType": r["etype"],
            "competition": r["league"],
            "event": r["event"],
            "startUtc": to_iso(r.get("ts")),
            "olbgTime": r.get("olbg_time"),
            "official": {"url": off_url, "name": off_name, "status": status},
            "olbg": {
                "event": r["url"],
                "selection": r.get("sel"),
                "market": r.get("market"),
                "decimal": r.get("dec"),
                "american": amer_num(r.get("amer")),
                "fractional": r.get("frac"),
                "tipPct": r.get("conf"),
                "tips": (f"{r['tips']}/{r['tips_n']}" if r.get("tips") is not None else None),
            },
            "research": None,
            "flags": flags,
            "draftPrediction": None,
        }
        if desk:
            event["research"] = {
                "american": amer_num(desk["amer"]),
                "decimal": desk.get("dec"),
                "selection": desk.get("inputs", "").split(" — ")[0] or None,
                "market": r.get("market"),
                "confidence": "high" if desk["p"] > 0.70 else "medium" if desk["p"] >= 0.55 else "low",
                "probability": round(desk["p"] * 100),
                "inputs": desk.get("inputs"),
            }
        if primary:
            event["draftPrediction"] = {
                "confidence": primary[6],
                "selection": primary[3],
                "market": primary[4],
                "line": primary[5],
                "researchP": primary[7],
                "text": primary[8],
                "source_ids": primary[9],
            }
        events.append(event)

    # per-sport aggregation
    sports = []
    for key, label in dr.SPORT_LABELS.items():
        rows = [e for e in events if e["sportKey"] == key]
        sp_official = SPORT_OFFICIAL[key]
        sp_picks = [p for p in dp.PICKS if p[0] == key]
        note = (dr.EMPTY_SPORTS[key] if key in dr.EMPTY_SPORTS else
                f"{len(rows)} OLBG listings captured; {len(sp_picks)} written picks published "
                f"(target {len(sp_picks)}+ of 5 — shortfall flagged where the hub carries fewer priced rows).")
        if key in dr.EMPTY_SPORTS:
            note = dr.EMPTY_SPORTS[key]
        elif len(sp_picks) < 5:
            note = (f"{len(rows)} OLBG listings captured; only {len(sp_picks)} written picks publishable "
                    f"because the hub carried that many priced/official-input rows. The shortfall is reported, "
                    f"not filled (target 5+).")
        sports.append({
            "key": key, "label": label,
            "olbg_hub": dr.HUBS[key],
            "official_url": sp_official[0], "official_name": sp_official[1],
            "official_alt": sp_official[2], "official_alt_name": sp_official[3],
            "note": note,
            "events": len(rows),
            "matchEvents": sum(1 for e in rows if e["eventType"] in ("fixture", "race")),
            "researchLines": sum(1 for e in rows if e["research"]),
            "draftPredictions": 0,
            "publishedPicks": len(sp_picks),
        })

    # executive summary: highest research probability first
    ranked = sorted(dp.PICKS, key=lambda p: p[7], reverse=True)
    published_summary = []
    for p in ranked[:12]:
        published_summary.append(
            f"[{p[6].upper()}] {dr.SPORT_LABELS[p[0]]} — {p[3]} · {p[5]} "
            f"(research probability {p[7]}%)"
        )

    n_confirmed = sum(1 for e in events if e["official"]["status"] == "event-confirmed")
    n_lines = sum(1 for e in events if e["research"])
    dashboard = {
        "asOfLabel": dr.AS_OF_LABEL,
        "captureUtc": dr.CAPTURE_UTC,
        "timezoneNote": ("Start times are OLBG payload timestamps stored in UTC where present; several "
                         "sports show OLBG-vs-official time divergence — official sources are the time "
                         "authority and affected rows are flagged (see Flagged, F-1027-02)."),
        "summary": {
            "olbgEvents": len(events),
            "matchEvents": sum(1 for e in events if e["eventType"] in ("fixture", "race")),
            "researchLines": n_lines,
            "eventConfirmed": n_confirmed,
            "draftPredictions": 0,
            "publishedPicks": len(dp.PICKS),
            "sportsWithListings": sum(1 for s in sports if s["events"] > 0),
            "sportsInScope": len(sports),
        },
        "publication": {
            "message": (
                f"{len(dp.PICKS)} written picks are published across "
                f"{sum(1 for s in sports if s['publishedPicks'])} sports, each labeled low/medium/high by "
                f"research probability and each row linked to OLBG plus an official reference. Blank prices "
                f"are deliberate — unverified values stay blank and flagged. The executive list below ranks "
                f"by research probability, not by payout."
            ),
            "publishedPicks": published_summary,
        },
        "dailyTargetPerSport": 5,
        "scope": [dr.SPORT_LABELS[k] for k in dr.SPORT_LABELS],
        "sports": sports,
        "flags": dp.FLAGS,
        "events": events,
        "picks": [
            {
                "sportKey": p[0], "sport": dr.SPORT_LABELS[p[0]],
                "eventId": p[1], "label": p[2], "selection": p[3], "market": p[4],
                "line": p[5], "confidence": p[6], "researchP": p[7],
                "text": p[8], "source_ids": p[9],
            }
            for p in dp.PICKS
        ],
    }

    (ROOT / "data" / "dashboard.json").write_text(json.dumps(dashboard, indent=2, ensure_ascii=False))
    (ROOT / "data" / "olbg-capture.json").write_text(json.dumps({
        "captureUtc": dr.CAPTURE_UTC,
        "asOfLabel": dr.AS_OF_LABEL,
        "method": ("OLBG sport hub pages and event pages fetched via their SvelteKit hydration payload "
                   "({page}/__data.json); prices are displayed best-odds at capture time, not a book offer."),
        "hubs": dr.HUBS,
        "sportIds": dr.SPORT_IDS,
        "rows": dr.ROWS,
    }, indent=2, ensure_ascii=False))
    (ROOT / "data" / "official-evidence.json").write_text(json.dumps(
        {"captureUtc": dr.CAPTURE_UTC, "evidence": dr.OFFICIAL}, indent=2, ensure_ascii=False))
    (ROOT / "data" / "line-research.json").write_text(json.dumps({
        "captureUtc": dr.CAPTURE_UTC,
        "method": {
            "probabilityScale": {"high": "> 70%", "medium": "55-70%", "low": "< 55%"},
            "priceWindow": {"low": -250, "high": 10000},
            "fairPrice": ("From research probability p: decimal = 1/p; American = -100/(d-1) for d<2, "
                          "+100*(d-1) for d>=2. Lines are reference prices from captured official inputs, "
                          "never a bookmaker offer."),
        },
        "deskLines": [
            {"event_id": r["event_id"], "sport": r["sport"], "event": r["event"],
             "line": r["desk"], "official": r.get("official")}
            for r in dr.ROWS if r.get("desk")
        ],
        "researchLineCount": n_lines,
    }, indent=2, ensure_ascii=False))
    (ROOT / "data" / "sources.json").write_text(json.dumps(
        {"captureUtc": dr.CAPTURE_UTC, "registry": dp.SOURCES}, indent=2, ensure_ascii=False))

    if errors:
        print("BUILD ERRORS:")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    print(f"build ok: {len(events)} events, {len(dp.PICKS)} picks, "
          f"{n_confirmed} confirmed, {n_lines} research lines, "
          f"{sum(1 for s in sports if s['events'])} sports with listings")


if __name__ == "__main__":
    main()
