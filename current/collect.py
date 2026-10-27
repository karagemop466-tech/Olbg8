#!/usr/bin/env python3
"""Capture bounded, public OLBG listings and cross-reference official feeds.

No browser emulation, logins, private endpoints, circumvention, or fabricated
prices are used. The payload is deliberately a partial point-in-time snapshot.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from pricing import nhl_reference

HERE = Path(__file__).resolve().parent
AGENT = "Olbg8Bot/1.0"
CHECKED_AT = "2026-10-27T05:38:00Z"  # time of manual source audit; not updated by automation
MAX_BYTES = 6_000_000


def timestamp(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (ValueError, TypeError):
        return None


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def valid_olbg_url(url: str) -> bool:
    p = urlparse(url)
    return (p.scheme == "https" and p.netloc == "www.olbg.com" and
            p.path.startswith("/betting-tips/") and
            bool(re.fullmatch(r"\d+", parse_qs(p.query).get("event_id", [""])[0])))


def odds_from(attrs: dict) -> dict | None:
    try:
        decimal = float(attrs.get("data-decimal", ""))
        american = int(attrs.get("data-american", ""))
        if decimal <= 1 or abs(american) < 100 or abs(american) > 1_000_000:
            return None
        implied_decimal = 1 + (american / 100 if american > 0 else 100 / -american)
        if abs(decimal - implied_decimal) > max(.04, decimal * .02):
            return None  # inconsistent display attributes, don't guess which one is right
        return {"american": american, "decimal": decimal}
    except (ValueError, TypeError):
        return None


class CategoryParser(HTMLParser):
    """Extract OLBG's rendered event cards, not script state or off-site links."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.row = None
        self.depth = 0
        self.zone = None
        self.zone_depth = None
        self.capture = None
        self.text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set((attrs.get("class") or "").split())
        if tag == "div":
            if self.row is None and {"grd", "tip"} <= classes:
                self.row = {"event": None, "url": None, "start": None, "competition": None,
                            "selection": None, "market": None, "odds": None}
                self.depth = 1
                return
            if self.row is not None:
                self.depth += 1
                if "rw" in classes:
                    for zone in ("ev", "sel", "odds"):
                        if zone in classes:
                            self.zone, self.zone_depth = zone, self.depth
                            break
        if self.row is None:
            return
        if tag == "a" and attrs.get("itemprop") == "url":
            url = urljoin("https://www.olbg.com/", attrs.get("href", ""))
            if valid_olbg_url(url):
                self.row["url"] = url
        elif tag == "time" and attrs.get("itemprop") == "startDate":
            value = attrs.get("datetime")
            self.row["start"] = timestamp(parse_time(value)) if parse_time(value) else None
        elif tag == "span" and "ui-odds" in classes and self.zone == "odds":
            self.row["odds"] = odds_from(attrs)
        if tag == "h5" and attrs.get("itemprop") == "name":
            self.capture, self.text = (tag, "event"), []
        elif tag == "h4" and self.zone == "sel":
            self.capture, self.text = (tag, "selection"), []
        elif tag == "p" and self.zone in ("ev", "sel"):
            self.capture, self.text = (tag, "competition" if self.zone == "ev" else "market"), []

    def handle_data(self, data):
        if self.capture:
            self.text.append(data)

    def handle_endtag(self, tag):
        if self.row is None:
            return
        if self.capture and tag == self.capture[0]:
            self.row[self.capture[1]] = clean("".join(self.text)) or None
            self.capture, self.text = None, []
        if tag == "div":
            if self.zone_depth == self.depth:
                self.zone, self.zone_depth = None, None
            self.depth -= 1
            if self.depth == 0:
                if self.row["url"]:
                    self.row["id"] = parse_qs(urlparse(self.row["url"]).query)["event_id"][0]
                    self.rows.append(self.row)
                self.row = None
                self.capture = None


class MarketParser(HTMLParser):
    """Extract market heading and visible outcomes from rendered event sections."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.markets = []
        self.market = None
        self.in_button = False
        self.row = None
        self.depth = 0
        self.capture = None
        self.text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set((attrs.get("class") or "").split())
        if tag == "button" and re.fullmatch(r"market_id_\d+", attrs.get("id", "")):
            self.market = {"id": attrs["id"][10:], "name": None, "selections": []}
            self.in_button = True
        elif tag == "div" and self.market:
            if self.row is None and "grd" in classes and re.fullmatch(r"\d+", attrs.get("id", "")):
                self.row = {"id": attrs["id"], "selection": None, "odds": None}
                self.depth = 1
            elif self.row is not None:
                self.depth += 1
        if tag == "h4" and (self.in_button or self.row is not None):
            self.capture, self.text = ("h4", "market" if self.in_button else "selection"), []
        elif tag == "span" and self.row is not None and "ui-odds" in classes:
            self.row["odds"] = odds_from(attrs)

    def handle_data(self, data):
        if self.capture:
            self.text.append(data)

    def handle_endtag(self, tag):
        if self.capture and tag == self.capture[0]:
            value = clean("".join(self.text)) or None
            if self.capture[1] == "market" and self.market:
                self.market["name"] = value
            elif self.row:
                self.row["selection"] = value
            self.capture, self.text = None, []
        if tag == "button" and self.in_button:
            self.in_button = False
            if self.market and self.market["name"]:
                self.markets.append(self.market)
            else:
                self.market = None
        elif tag == "div" and self.row is not None:
            self.depth -= 1
            if self.depth == 0:
                if self.row["selection"] and self.market:
                    self.market["selections"].append(self.row)
                self.row = None


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old, new = urlparse(req.full_url), urlparse(newurl)
        if new.scheme != "https" or new.hostname != old.hostname:
            raise ValueError("cross-host or non-HTTPS redirect refused")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class PublicClient:
    def __init__(self, delay=1.25):
        self.opener = build_opener(SafeRedirect())
        self.last = {}
        self.delay = delay

    def get(self, url):
        parsed = urlparse(url)
        allowed = {"www.olbg.com", "api-web.nhle.com", "statsapi.mlb.com"}
        if parsed.scheme != "https" or parsed.hostname not in allowed:
            raise ValueError("host not on the fixed public source allowlist")
        wait = self.delay - (time.monotonic() - self.last.get(parsed.hostname, 0))
        if wait > 0:
            time.sleep(wait)
        req = Request(url, headers={"User-Agent": AGENT, "Accept": "text/html,application/json;q=0.9,*/*;q=0.5"})
        try:
            with self.opener.open(req, timeout=25) as response:
                body = response.read(MAX_BYTES + 1)
                self.last[parsed.hostname] = time.monotonic()
                if len(body) > MAX_BYTES:
                    raise ValueError("response exceeded size limit")
                return body.decode("utf-8", errors="replace")
        finally:
            self.last[parsed.hostname] = time.monotonic()


def is_challenge(body):
    m = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
    title = clean(m.group(1)).lower() if m else ""
    return ("just a moment" in title or "access denied" in title or
            "cf-chl-" in body.lower() or "challenge-platform" in body.lower())


def read_robots(client):
    body = client.get("https://www.olbg.com/robots.txt")
    robots = RobotFileParser()
    robots.set_url("https://www.olbg.com/robots.txt")
    robots.parse(body.splitlines())
    return robots


def describe_error(exc):
    if isinstance(exc, HTTPError):
        return f"HTTP {exc.code}"
    if isinstance(exc, URLError):
        return "network or TLS error"
    return type(exc).__name__ + ": " + str(exc)[:140]


def manual_crosswalk(row, curated):
    for entry in curated:
        if (entry["sport"] != row["sport"] or entry["id"] != row["id"] or
                entry["name"] != row.get("event")):
            continue
        date = (row.get("start") or "")[:10]
        if not date or not entry["date"] <= date <= entry.get("lastDate", entry["date"]):
            continue
        return {
            "kind": "manual", "url": entry["officialUrl"], "date": entry["date"],
            "lastDate": entry.get("lastDate"), "start": entry.get("officialStart"),
            "checkedAt": CHECKED_AT, "note": entry["note"]
        }
    return None


def norm(value):
    return clean(re.sub(r"[^a-z0-9]+", " ", (value or "").lower()))


def name_matches(olbg_side, official_name):
    a, b = norm(olbg_side), norm(official_name)
    # Official nickname must match whole words at the end. Never fuzzy-match.
    return bool(b and (a == b or a.endswith(" " + b)))


def dynamic_crosswalk(row, fixtures, checked_at):
    if (row.get("competition") or "").lower() not in ("nhl", "mlb") or not row.get("start"):
        return None
    sides = (row.get("event") or "").split(" @ ")
    olbg_time = parse_time(row["start"])
    if len(sides) != 2 or not olbg_time:
        return None
    candidates = []
    for f in fixtures:
        official_time = parse_time(f.get("start"))
        if (f["league"].lower() != row["competition"].lower() or not official_time or
                abs((official_time - olbg_time).total_seconds()) > 7200):
            continue
        if name_matches(sides[0], f["away"]) and name_matches(sides[1], f["home"]):
            candidates.append(f)
    if len(candidates) != 1:
        return None
    f = candidates[0]
    delta = int((parse_time(row["start"]) - parse_time(f["start"])).total_seconds() / 60)
    return {"kind": "schedule-api", "url": f["url"], "start": f["start"],
            "checkedAt": checked_at, "note": "Matched both official team names, league and a unique start within two hours.",
            "timeDifferenceMinutes": delta, "awayAbbrev": f.get("awayAbbrev"), "homeAbbrev": f.get("homeAbbrev"),
            "season": f.get("season"), "gameType": f.get("gameType")}


def nhl_fixtures(payload):
    result = []
    for day in payload.get("gameWeek", []):
        for game in day.get("games", []):
            if game.get("gameState") not in ("FUT", "PRE"):
                continue
            away, home = game.get("awayTeam", {}), game.get("homeTeam", {})
            def nickname(team):
                v = team.get("commonName", {})
                return v.get("default", "") if isinstance(v, dict) else str(v)
            if game.get("id") and game.get("startTimeUTC") and nickname(away) and nickname(home):
                result.append({"league":"NHL", "away":nickname(away), "home":nickname(home),
                               "start":game["startTimeUTC"], "awayAbbrev":away.get("abbrev"), "homeAbbrev":home.get("abbrev"),
                               "season":game.get("season"), "gameType":game.get("gameType"),
                               "url":f"https://api-web.nhle.com/v1/gamecenter/{game['id']}/landing"})
    return result


def mlb_fixtures(payload):
    result = []
    for day in payload.get("dates", []):
        for game in day.get("games", []):
            state = game.get("status", {}).get("abstractGameState")
            if state != "Preview":
                continue
            def nickname(side):
                t = game.get("teams", {}).get(side, {}).get("team", {})
                return t.get("teamName") or ""
            if game.get("gamePk") and game.get("gameDate") and nickname("away") and nickname("home"):
                result.append({"league":"MLB", "away":nickname("away"), "home":nickname("home"),
                               "start":game["gameDate"],
                               "url":f"https://www.mlb.com/gameday/{game['gamePk']}"})
    return result


def get_official_fixtures(client, now):
    begin = now.date()
    end = begin + timedelta(days=7)
    urls = {
        "NHL": f"https://api-web.nhle.com/v1/schedule/{begin.isoformat()}",
        "MLB": "https://statsapi.mlb.com/api/v1/schedule?" + urlencode({"sportId":1,"startDate":begin.isoformat(),"endDate":end.isoformat(),"hydrate":"team,probablePitcher"}),
    }
    fixtures, statuses = [], []
    for league, url in urls.items():
        try:
            payload = json.loads(client.get(url))
            found = nhl_fixtures(payload) if league == "NHL" else mlb_fixtures(payload)
            fixtures.extend(found)
            statuses.append({"name":league, "status":"ok", "count":len(found), "url":url})
        except (HTTPError, URLError, OSError, ValueError, TypeError, KeyError) as exc:
            statuses.append({"name":league, "status":"error", "detail":describe_error(exc), "url":url})
    standings = {}
    standings_url = "https://api-web.nhle.com/v1/standings/now"
    try:
        payload = json.loads(client.get(standings_url))
        for team in payload.get("standings", []):
            abbr = team.get("teamAbbrev", {}).get("default")
            if abbr:
                standings[abbr] = team
        if not standings:
            raise ValueError("no NHL standings records")
        statuses.append({"name":"NHL standings", "status":"ok", "count":len(standings), "url":standings_url})
    except (HTTPError, URLError, OSError, ValueError, TypeError, KeyError) as exc:
        statuses.append({"name":"NHL standings", "status":"error", "detail":describe_error(exc), "url":standings_url})
    return fixtures, statuses, standings


def nhl_line(official, standings):
    if not official or official.get("kind") != "schedule-api" or official.get("gameType") != 2:
        return None
    home, away = standings.get(official.get("homeAbbrev")), standings.get(official.get("awayAbbrev"))
    if not home or not away or home.get("seasonId") != official.get("season") or away.get("seasonId") != official.get("season"):
        return None
    try:
        values = nhl_reference(home, away)
    except (ValueError, TypeError, KeyError):
        return None
    return {**values, "home":official["homeAbbrev"], "away":official["awayAbbrev"],
            "inputs": {official["homeAbbrev"]:{k:home[k] for k in ("gamesPlayed","goalFor","goalAgainst")},
                       official["awayAbbrev"]:{k:away[k] for k in ("gamesPlayed","goalFor","goalAgainst")}},
            "source":"https://api-web.nhle.com/v1/standings/now",
            "label":"Uncalibrated winner reference; equal split of tied scores; not a settled-market quote."}


def build_snapshot(client, now, market_budget=2):
    catalog = json.loads((HERE / "catalog.json").read_text())
    curated = json.loads((HERE / "curated.json").read_text())
    captured = timestamp(now)
    snapshot = {"schema":"olbg-current/v1", "capturedAt":captured, "sports":catalog,
                "hubs":[], "officialFeeds":[], "events":[], "publishedPicks":[],
                "limits": {"pagesPerHub":1, "eventDetailsPerSport":market_budget,
                           "description":"First public hub response only; deeper listings and unsampled event markets are not covered."}}
    try:
        robots = read_robots(client)
    except (HTTPError, URLError, OSError, ValueError) as exc:
        robots = None
        robots_error = describe_error(exc)
    fixtures, snapshot["officialFeeds"], standings = get_official_fixtures(client, now)
    seen = set()
    for sport in catalog:
        for label, number in sport["hubs"]:
            url = f"https://www.olbg.com/betting-tips/{label}/{number}"
            status = {"sport":sport["key"], "label":label.replace("_", " "), "url":url,
                      "status":"error", "count":0, "detail":None}
            snapshot["hubs"].append(status)
            if robots is None:
                status["detail"] = "robots.txt unavailable: " + robots_error
                continue
            if not robots.can_fetch(AGENT, url):
                status["detail"] = "robots.txt disallows this hub"
                continue
            try:
                body = client.get(url)
                if is_challenge(body):
                    status["detail"] = "access challenge; not bypassed"
                    continue
                parser = CategoryParser()
                parser.feed(body)
                if not parser.rows:
                    if "no tips found" in body.lower():
                        status["status"] = "no-tips"
                        status["detail"] = "OLBG displayed no tips on this page; this is not a fixture census."
                    else:
                        status["detail"] = "No event cards parsed; page may have changed."
                    continue
                for row in parser.rows:
                    # The event id is scoped by the OLBG hub, not globally across sports.
                    identity = (number, row["id"])
                    if identity in seen:
                        continue
                    seen.add(identity)
                    row.update({"sport":sport["key"], "hub":label, "capturedAt":captured})
                    row["official"] = dynamic_crosswalk(row, fixtures, captured) or manual_crosswalk(row, curated)
                    row["researchLine"] = nhl_line(row["official"], standings) if row["sport"] == "ice-hockey" else None
                    row["details"] = None
                    snapshot["events"].append(row)
                    status["count"] += 1
                status["status"] = "ok"
                status["detail"] = "First rendered page; may omit load-more results or untipped events."
            except (HTTPError, URLError, OSError, ValueError) as exc:
                status["detail"] = describe_error(exc)
    # A small fixed number of public event pages are examined per sport. Prioritize
    # event-specific official corroboration, then time. Avoid extra disallowed URLs.
    if robots:
        for sport in catalog:
            rows = [r for r in snapshot["events"] if r["sport"] == sport["key"] and
                    (not parse_time(r.get("start")) or parse_time(r["start"]) > now)]
            rows.sort(key=lambda r: (not bool(r.get("official")), r.get("start") or "9999", r["id"]))
            for row in rows[:market_budget]:
                if not robots.can_fetch(AGENT, row["url"]):
                    row["details"] = {"status":"error", "detail":"robots.txt disallows event URL", "markets":[]}
                    continue
                try:
                    body = client.get(row["url"])
                    if is_challenge(body):
                        row["details"] = {"status":"error", "detail":"access challenge; not bypassed", "markets":[]}
                        continue
                    parser = MarketParser()
                    parser.feed(body)
                    row["details"] = {"status":"ok" if parser.markets else "parse-error",
                                      "markets":parser.markets}
                except (HTTPError, URLError, OSError, ValueError) as exc:
                    row["details"] = {"status":"error", "detail":describe_error(exc), "markets":[]}
    return snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(HERE / "live.json"))
    parser.add_argument("--market-budget", type=int, default=2, choices=range(0, 4))
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    result = build_snapshot(PublicClient(), now, args.market_budget)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    ok = sum(h["status"] == "ok" for h in result["hubs"])
    exact = sum(bool(e["official"]) for e in result["events"])
    details = sum(bool(e.get("details") and e["details"]["status"] == "ok") for e in result["events"])
    print(f"Captured {len(result['events'])} event cards from {ok}/{len(result['hubs'])} hubs; {exact} official matches, {details} sampled detail pages; {result['capturedAt']}.")
    for hub in result["hubs"]:
        print(f"{hub['label']}: {hub['status']} ({hub['count']}) {hub.get('detail') or ''}")


if __name__ == "__main__":
    main()
