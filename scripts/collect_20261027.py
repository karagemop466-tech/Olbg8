#!/usr/bin/env python3
"""Collect the 2026-10-27 OLBG SvelteKit data payloads and official sources.

Runs inside GitHub Actions (unrestricted egress). The sandbox itself only allows
a small set of outbound hosts, so the authoritative snapshot is committed back
to the session branch by `.github/workflows/collect-20261027.yml`.

Outputs under data/capture-20261027/:
  olbg-hubs/<key>.json       raw SvelteKit `__data.json` for each OLBG sport hub
  olbg-events/<id>.json      raw SvelteKit `__data.json` for each discovered event
  official/<key>.json|.txt   official feed snapshot or text extraction
  manifest.json              fetch status, URLs, counts, capture time

No odds, fixture, statistic or injury is invented here; this is a byte-faithful
capture of public endpoints plus a lossless decode of their flattened payloads.
"""
from __future__ import annotations

import concurrent.futures as cf
import html as html_lib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "capture-20261027"
HUB_DIR = OUT / "olbg-hubs"
ALL_DIR = OUT / "olbg-all-events"
EVT_DIR = OUT / "olbg-events"
OFF_DIR = OUT / "official"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# OLBG sport taxonomy established by the repository's earlier ID probe.
HUBS = {
    "tennis": ("Tennis", 3),
    "basketball": ("Basketball", 4),
    "golf": ("Golf", 5),
    "cricket": ("Cricket", 7),
    "snooker": ("Snooker", 8),
    "rugby_union": ("Rugby_Union", 9),
    "rugby_league": ("Rugby_League", 10),
    "baseball": ("Baseball", 12),
    "ice_hockey": ("Ice_Hockey", 13),
    "motor_racing": ("Motor_Racing", 14),
    "darts": ("Darts", 15),
    "handball": ("Handball", 20),
    "volleyball": ("Volleyball", 21),
    "gaelic_football": ("Gaelic_Football", 25),
    "hurling": ("Hurling", 26),
    "greyhounds": ("Greyhounds", 28),
}

# Official governing-body / league endpoints. JSON feeds are stored verbatim;
# HTML pages are stored as plain-text extracts with the exact source URL.
OFFICIAL_JSON = {
    "nhl_team_stats": "https://api-web.nhle.com/v1/standings/now",
    "nhl_schedule_20261027": "https://api-web.nhle.com/v1/schedule/2026-10-27",
    "nhl_schedule_20261028": "https://api-web.nhle.com/v1/schedule/2026-10-28",
    "nhl_schedule_20261029": "https://api-web.nhle.com/v1/schedule/2026-10-29",
    "nhl_standings": "https://api-web.nhle.com/v1/standings/now",
    "nhl_scores_now": "https://api-web.nhle.com/v1/score/now",
    "mlb_schedule": ("https://statsapi.mlb.com/api/v1/schedule?sportId=1"
                     "&startDate=2026-10-24&endDate=2026-11-05"
                     "&hydrate=team,linescore,probablePitcher,decisions"),
    "mlb_standings": ("https://statsapi.mlb.com/api/v1/standings?leagueId=103,104"
                      "&season=2026&standingsTypes=regularSeason&hydrate=team"),
    "nba_scoreboard": "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
    "nba_schedule": "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json",
    "nba_standings": "https://cdn.nba.com/static/json/staticData/standingsLeagueV2.json",
    "nba_data_scoreboard": "https://data.nba.net/prod/v1/20261027/scoreboard.json",
    "mlb_team_hitting": "https://statsapi.mlb.com/api/v1/teams/stats?stats=season&group=hitting&season=2026&sportIds=1",
    "mlb_team_pitching": "https://statsapi.mlb.com/api/v1/teams/stats?stats=season&group=pitching&season=2026&sportIds=1",
    "f1_races_mirror": "https://api.jolpi.ca/ergast/f1/2026/races/",
}

OFFICIAL_HTML = {
    "atp_scores": "https://www.atptour.com/en/scores/current",
    "atp_rankings": "https://www.atptour.com/en/rankings/singles",
    "wta_tournaments": "https://www.wtatennis.com/tournaments",
    "wta_rankings": "https://www.wtatennis.com/rankings/singles",
    "icc_fixtures": "https://www.icc-cricket.com/fixtures-results",
    "cricket_australia_fixtures": "https://www.cricket.com.au/fixtures",
    "pdc_tournaments": "https://www.pdc.tv/tournaments",
    "wst_matches": "https://www.wst.tv/matches",
    "wst_calendar": "https://www.wst.tv/calendar",
    "pgatour_schedule": "https://www.pgatour.com/schedule",
    "lpga_tournaments": "https://www.lpga.com/tournaments",
    "dpworld_schedule": "https://www.europeantour.com/dpworld-tour/schedule/",
    "formula1_calendar": "https://www.formula1.com/en/racing/2026",
    "nrl_draw": "https://www.nrl.com/draw/",
    "superleague_fixtures": "https://www.superleague.co.uk/fixtures",
    "epcr_matches": "https://www.epcrugby.com/champions-cup/matches",
    "lnr_prod2": "https://prod2.lnr.fr/calendrier-et-resultats",
    "cev_match_centres": "https://www.cev.eu/match-centres/",
    "ehfcl_matches": "https://ehfcl.eurohandball.com/men/2026-27/matches/",
    "ehfcl_standings": "https://ehfcl.eurohandball.com/men/2026-27/standings/",
    "gaa_fixtures": "https://www.gaa.ie/fixtures-results",
    "gbgb_racing": "https://www.gbgb.org.uk/racing/",
    "gbgb_results": "https://www.gbgb.org.uk/results/",
    "euroleague_home": "https://www.euroleaguebasketball.net/en/euroleague/",
    "euroleague_standings_page": "https://www.euroleaguebasketball.net/en/euroleague/standings/",
    "euroleague_games_page": "https://www.euroleaguebasketball.net/en/euroleague/games/",
    "nba_games": "https://www.nba.com/games?date=2026-10-27",
    "nhl_schedule_page": "https://www.nhl.com/schedule/2026-10-27",
    "mlb_schedule_page": "https://www.mlb.com/schedule",
    "f1_driver_standings": "https://www.formula1.com/en/results/2026/drivers",
    "f1_team_standings": "https://www.formula1.com/en/results/2026/team",
    "pdc_order_of_merit": "https://www.pdc.tv/order-of-merit",
    "wst_rankings": "https://www.wst.tv/rankings",
    "icc_team_rankings": "https://www.icc-cricket.com/rankings/team-rankings",
    "gbgb_racecards": "https://www.gbgb.org.uk/racing/race-cards/",
    "atp_scores_alt": "https://www.atptour.com/en/scores/results-archive",
    "wta_scores": "https://www.wtatennis.com/scores",
    "superleague_home": "https://www.superleague.co.uk/",
    "nrl_ladder": "https://www.nrl.com/ladder/",
    # Event-level official draw pages discovered on the governing-body sites.
    # These are the 2026 tournaments present in the OLBG Tennis feed.
    "wta_guangzhou_draws": "https://www.wtatennis.com/tournaments/1023/guangzhou/2026/draws",
    "wta_tokyo_draws": "https://www.wtatennis.com/tournaments/1056/tokyo/2026/draws",
    "wta_courmayeur_draws": "https://www.wtatennis.com/tournaments/1174/courmayeur-125/2026/draws",
    "wta_queretaro_draws": "https://www.wtatennis.com/tournaments/1145/queretaro-125/2026/draws",
    "wta_curitiba_draws": "https://www.wtatennis.com/tournaments/1180/curitiba-125/2026/draws",
    "wta_guangzhou_overview": "https://www.wtatennis.com/tournaments/1023/guangzhou/2026",
    "wta_tokyo_overview": "https://www.wtatennis.com/tournaments/1056/tokyo/2026",
    "atp_vienna_draws": "https://www.atptour.com/en/scores/archive/vienna/337/2026/draws",
    "atp_basel_draws": "https://www.atptour.com/en/scores/archive/basel/328/2026/draws",
    "atp_vienna_results": "https://www.atptour.com/en/scores/current/vienna/337/results",
    "atp_basel_results": "https://www.atptour.com/en/scores/current/basel/328/results",
}


def get(url: str, timeout: int = 30, tries: int = 3) -> tuple[int, bytes, str]:
    last = "unknown error"
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
            "Cache-Control": "no-cache",
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read(), resp.headers.get("content-type", "")
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}"
            if exc.code in (403, 404, 410, 429):
                time.sleep(1.2 * (attempt + 1))
        except Exception as exc:  # network/DNS/timeouts
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(1.0 * (attempt + 1))
    return 0, b"", last


SPECIAL = {-1: None, -2: None, -3: None, -4: None, -5: None, -6: 0}


def unflatten_node(node: dict):
    """Decode a SvelteKit devalue `data` array into ordinary Python values.

    Integers appearing as members of an object/array are references into the
    flat array. Primitives stored directly in the array are literal values.
    """
    data = node.get("data")
    if not isinstance(data, list) or not data:
        return None
    memo: dict[int, object] = {}

    def resolve(idx: int):
        if idx in SPECIAL:
            return SPECIAL[idx]
        if idx in memo:
            return memo[idx]
        if idx < 0 or idx >= len(data):
            return None
        value = data[idx]
        if isinstance(value, dict):
            out = {}
            memo[idx] = out
            for key, child in value.items():
                out[key] = resolve(child) if isinstance(child, int) and not isinstance(child, bool) else child
            return out
        if isinstance(value, list):
            out = []
            memo[idx] = out
            for child in value:
                out.append(resolve(child) if isinstance(child, int) and not isinstance(child, bool) else child)
            return out
        memo[idx] = value
        return value

    return resolve(0)


def decoded_roots(payload: bytes) -> list:
    try:
        doc = json.loads(payload)
    except Exception:
        return []
    roots = []
    for node in doc.get("nodes", []) or []:
        if isinstance(node, dict) and node.get("type") == "data":
            try:
                roots.append(unflatten_node(node))
            except Exception:
                roots.append(None)
    return roots


def find_key(roots: list, key: str):
    for root in roots:
        if isinstance(root, dict) and key in root:
            return root[key]
    return None


def strip_html(raw: bytes) -> str:
    text = raw.decode("utf-8", "replace")
    text = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()[:300000]


def hub_url(slug: str, sport_id: int) -> str:
    return f"https://www.olbg.com/betting-tips/{slug}/{sport_id}/__data.json"


def event_data_url(event_url: str) -> tuple[str, str] | None:
    if not event_url:
        return None
    parts = urllib.parse.urlsplit(event_url)
    if not parts.path.startswith("/betting-tips/"):
        return None
    query = parts.query
    path = parts.path.rstrip("/") + "/__data.json"
    if query:
        path += "?" + query
    return "https://www.olbg.com" + path, event_url


def main() -> int:
    for d in (HUB_DIR, ALL_DIR, EVT_DIR, OFF_DIR):
        d.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    manifest = {
        "capture_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "collector": "scripts/collect_20261027.py",
        "hubs": {},
        "all_events": {},
        "events": {},
        "official": {},
        "notes": [],
    }
    print(f"capture started {manifest['capture_utc']}", flush=True)

    # 1. OLBG sport hub data endpoints.
    def fetch_hub(item):
        key, (slug, sid) = item
        url = hub_url(slug, sid)
        status, body, err = get(url)
        if status == 200 and body:
            (HUB_DIR / f"{key}.json").write_bytes(body)
        return key, {"url": url, "page_url": f"https://www.olbg.com/betting-tips/{slug}/{sid}",
                     "status": status, "bytes": len(body), "error": err if status != 200 else ""}

    with cf.ThreadPoolExecutor(max_workers=6) as pool:
        for key, rec in pool.map(fetch_hub, HUBS.items()):
            manifest["hubs"][key] = rec
            print(f"hub {key:18s} {rec['status']} {rec['bytes']}", flush=True)

    # 2. Fetch the sport "All Events" pages. These expose outright/tournament
    #    markets (Golf, Darts, Motor Racing, Rugby League) that the sport hub's
    #    `tips` array omits.
    def fetch_all_events(item):
        key, (slug, sid) = item
        url = f"https://www.olbg.com/betting-tips/{slug}/All_{slug}/All_Events/{sid}/__data.json"
        status, body, err = get(url)
        if status == 200 and body:
            (ALL_DIR / f"{key}.json").write_bytes(body)
        return key, {"url": url, "status": status, "bytes": len(body),
                     "error": err if status != 200 else ""}

    with cf.ThreadPoolExecutor(max_workers=6) as pool:
        for key, rec in pool.map(fetch_all_events, HUBS.items()):
            manifest["all_events"][key] = rec
            print(f"all-events {key:18s} {rec['status']} {rec['bytes']}", flush=True)

    # 3. Discover event URLs from hub tips, hub tournaments, and all-events tips.
    events: dict[str, dict] = {}
    sources = [(key, HUB_DIR / f"{key}.json") for key in HUBS] + \
              [(key, ALL_DIR / f"{key}.json") for key in HUBS]
    for key, path in sources:
        if not path.exists():
            continue
        roots = decoded_roots(path.read_bytes())
        feed = find_key(roots, "tips")
        tournaments = find_key(roots, "tournaments")
        rows = []
        for label, group in (("tips", feed), ("tournaments", tournaments)):
            if isinstance(group, list):
                rows += [("hub" if path.parent == HUB_DIR else "all", label, t) for t in group]
        if path.parent == HUB_DIR:
            manifest["hubs"][key]["tip_rows"] = len(feed or []) if isinstance(feed, list) else 0
            manifest["hubs"][key]["tournament_rows"] = len(tournaments or []) if isinstance(tournaments, list) else 0
        for origin, label, tip in rows:
            if not isinstance(tip, dict):
                continue
            ev_url = tip.get("eventUrl") or ""
            parsed = event_data_url(ev_url)
            if not parsed:
                continue
            data_url, page_url = parsed
            m = re.search(r"event_id=(\d+)", page_url)
            ev_id = m.group(1) if m else re.sub(r"\W+", "_", ev_url)[-80:]
            entry = events.setdefault(ev_id, {
                "event_id": ev_id, "sport_key": key, "page_url": page_url,
                "data_url": data_url, "origin": set(),
            })
            entry["origin"].add(f"{origin}:{label}")
    for entry in events.values():
        entry["origin"] = sorted(entry["origin"])
    print(f"discovered {len(events)} event pages", flush=True)

    # 3. Fetch each event's full market payload. Bounded for runner politeness.
    max_events = int(sys.argv[1]) if len(sys.argv) > 1 else 420
    selected = list(events.values())[:max_events]

    def fetch_event(entry):
        status, body, err = get(entry["data_url"], timeout=25, tries=2)
        if status == 200 and body:
            (EVT_DIR / f"{entry['event_id']}.json").write_bytes(body)
        return entry, {"url": entry["data_url"], "page_url": entry["page_url"],
                       "sport_key": entry["sport_key"], "status": status,
                       "bytes": len(body), "error": err if status != 200 else ""}

    with cf.ThreadPoolExecutor(max_workers=8) as pool:
        for entry, rec in pool.map(fetch_event, selected):
            manifest["events"][entry["event_id"]] = rec
    ok = sum(1 for r in manifest["events"].values() if r["status"] == 200)
    print(f"event payloads {ok}/{len(selected)} ok", flush=True)
    manifest["events_discovered"] = len(events)
    manifest["events_requested"] = len(selected)

    # 4. Official sources.
    def fetch_official(item):
        kind, key, url = item
        status, body, err = get(url, timeout=30, tries=2)
        if status == 200 and body:
            if kind == "json":
                (OFF_DIR / f"{key}.json").write_bytes(body)
            else:
                (OFF_DIR / f"{key}.txt").write_text(
                    f"SOURCE: {url}\nFETCHED_UTC: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\n\n"
                    + strip_html(body), encoding="utf-8")
        return key, {"url": url, "kind": kind, "status": status, "bytes": len(body),
                     "error": err if status != 200 else ""}

    targets = [("json", k, u) for k, u in OFFICIAL_JSON.items()] + \
              [("html", k, u) for k, u in OFFICIAL_HTML.items()]
    with cf.ThreadPoolExecutor(max_workers=8) as pool:
        for key, rec in pool.map(fetch_official, targets):
            manifest["official"][key] = rec
            print(f"official {key:28s} {rec['status']} {rec['bytes']}", flush=True)

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(f"done: {ok} event payloads, {len(targets)} official targets", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
