#!/usr/bin/env python3
"""OLBG collector - decodes the SvelteKit `__data.json` hydration feed.

The rendered OLBG sport pages are JavaScript shells. The actual fixture, market
and price data is served as a flattened `devalue` payload from
`<page path>/__data.json`. This module flattens that payload back into plain
Python objects and normalises the market rows so the rest of the pipeline can
work from real captured prices instead of scraped prose.

Run modes
---------
    python3 scripts/collect_olbg.py            # live fetch (used by CI runner)
    python3 scripts/collect_olbg.py --raw DIR  # parse already-saved raw bodies

Nothing here invents data. If a page cannot be fetched the sport is recorded
with an explicit error entry and zero rows.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "olbg"

# (display label, OLBG path segment, OLBG sport id)
SPORTS: list[tuple[str, str, int]] = [
    ("Golf", "Golf", 5),
    ("Volleyball", "Volleyball", 21),
    ("Rugby Union", "Rugby_Union", 9),
    ("Cricket", "Cricket", 7),
    ("Snooker", "Snooker", 8),
    ("Darts", "Darts", 15),
    ("Baseball", "Baseball", 12),
    ("Gaelic Football", "Gaelic_Football", 25),
    ("Hurling", "Hurling", 26),
    ("Greyhounds", "Greyhounds", 28),
    ("Tennis", "Tennis", 3),
    ("Motor Racing", "Motor_Racing", 14),
    ("Handball", "Handball", 20),
    ("Ice Hockey", "Ice_Hockey", 13),
    ("Basketball", "Basketball", 4),
    ("Rugby League", "Rugby_League", 10),
]

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
BASE = "https://www.olbg.com"


# ---------------------------------------------------------------- devalue ---
def unflatten(data: list[Any]) -> Any:
    """Rebuild a flattened devalue array.

    SvelteKit stores every distinct value once. An integer in the array is an
    index into the same array; resolving it yields the stored value, and that
    value is never re-resolved (so a stored literal `0` stays `0`).
    """
    if not isinstance(data, list) or not data:
        return None

    cache: dict[int, Any] = {}
    size = len(data)

    def resolve(index: Any) -> Any:
        if isinstance(index, bool) or not isinstance(index, int):
            return index
        if index < 0 or index >= size:
            return None
        if index in cache:
            return cache[index]
        value = data[index]
        if isinstance(value, dict):
            out: dict[str, Any] = {}
            cache[index] = out
            for key, ref in value.items():
                out[key] = resolve(ref)
            return out
        if isinstance(value, list):
            out_list: list[Any] = []
            cache[index] = out_list
            for ref in value:
                out_list.append(resolve(ref))
            return out_list
        cache[index] = value
        return value

    return resolve(0)


def decode_payload(body: bytes) -> Any:
    raw = json.loads(body.decode("utf-8", "replace"))
    nodes = raw.get("nodes") or []
    if not nodes:
        return None
    # Later nodes are the most specific; the last one is the page data.
    node = nodes[-1]
    if node.get("type") == "error":
        raise ValueError(f"OLBG data error node: {node.get('error')}")
    if node.get("type") != "data" or not isinstance(node.get("data"), list):
        return None
    return unflatten(node["data"])


def walk(node: Any):
    """Yield every dict/list reachable from node."""
    stack = [node]
    seen = 0
    while stack and seen < 400000:
        seen += 1
        current = stack.pop()
        if isinstance(current, dict):
            yield current
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)


# ---------------------------------------------------------------- fetching --
def fetch(url: str, tries: int = 3) -> tuple[int, bytes, str]:
    last_error = ""
    for attempt in range(tries):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": UA,
                "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
                "Accept-Language": "en-GB,en;q=0.9",
                "Referer": BASE + "/betting-tips",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.status, response.read(), ""
        except urllib.error.HTTPError as exc:  # pragma: no cover - network
            last_error = f"HTTP {exc.code}"
            if exc.code in (403, 404, 429):
                time.sleep(2 + attempt * 3)
            else:
                break
        except Exception as exc:  # pragma: no cover - network
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(2 + attempt * 2)
    return 0, b"", last_error


def data_url(page_path: str) -> str:
    path, _, query = page_path.partition("?")
    url = BASE + path.rstrip("/") + "/__data.json"
    return f"{url}?{query}" if query else url


# ------------------------------------------------------------- extraction ---
def collect_tips(tree: Any) -> list[dict[str, Any]]:
    """Pull market rows out of a decoded sport feed."""
    rows: list[dict[str, Any]] = []
    seen: set[tuple] = set()
    for node in walk(tree):
        if "eventUrl" not in node or "selection" not in node:
            continue
        selection = node.get("selection")
        market = node.get("market_alias") or node.get("market_name") or node.get("market")
        if not isinstance(selection, str) or not isinstance(market, str):
            continue
        key = (node.get("eventUrl"), market, selection, node.get("odds"))
        if key in seen:
            continue
        seen.add(key)
        rows.append(node)
    return rows


def american_from_decimal(price: float | None) -> int | None:
    if not price or price <= 1.0:
        return None
    if price >= 2.0:
        return int(round((price - 1.0) * 100))
    return int(round(-100.0 / (price - 1.0)))


def to_decimal(value: Any) -> float | None:
    try:
        price = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return round(price, 4) if price > 1.0 else None


def iso_from_unix(value: Any) -> str:
    try:
        stamp = int(value)
    except (TypeError, ValueError):
        return ""
    if stamp < 1_000_000_000 or stamp > 4_000_000_000:
        return ""
    return datetime.fromtimestamp(stamp, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalise(row: dict[str, Any], sport: dict[str, Any]) -> dict[str, Any]:
    decimal = to_decimal(row.get("odds"))
    american = row.get("american_odds")
    try:
        american_int = int(str(american).replace("+", "")) if american not in (None, "") else None
    except ValueError:
        american_int = None
    if american_int is None:
        american_int = american_from_decimal(decimal)
    event_url = str(row.get("eventUrl") or "")
    event_id = ""
    match = re.search(r"event_id=(\d+)", event_url)
    if match:
        event_id = match.group(1)
    return {
        "sport": sport["label"],
        "sport_key": sport["key"],
        "sport_id": sport["sport_id"],
        "event_id": event_id,
        "event_name": str(row.get("event_name_alias") or "").strip(),
        "competition": str(row.get("menu_league") or "").strip(),
        "market": str(row.get("market_alias") or row.get("market_name") or row.get("market") or "").strip(),
        "selection": str(row.get("selection") or "").strip(),
        "decimal_odds": decimal,
        "american_odds": american_int,
        "fractional_odds": str(row.get("fractional_odds") or ""),
        "start_utc": iso_from_unix(row.get("event_start_unix_timestamp")),
        "olbg_url": event_url if event_url.startswith("http") else BASE + event_url,
        "experts_count": row.get("experts_count"),
        "win_tips": row.get("win_tips"),
        "win_tips_count": row.get("win_tips_count"),
        "confidence": row.get("confidence"),
        "comments_count": row.get("comments_count"),
        "expired": bool(row.get("expired")) if row.get("expired") is not None else None,
        "venue": row.get("venue") or "",
        "address": row.get("address") or "",
    }


def api_urls(tree: Any) -> list[str]:
    found: list[str] = []
    for node in walk(tree):
        for key, value in node.items():
            if isinstance(key, str) and key.lower().endswith("apiurl") and isinstance(value, str):
                if value not in found:
                    found.append(value)
    return found


def market_shapes(tree: Any) -> dict[str, Any]:
    """Probe summary of the market objects on an event page."""
    keysets: dict[str, int] = {}
    samples: list[dict[str, Any]] = []
    markets: dict[str, int] = {}
    for node in walk(tree):
        if "selection" in node and "odds" in node and len(node) < 40:
            signature = ",".join(sorted(str(k) for k in node))
            keysets[signature] = keysets.get(signature, 0) + 1
            name = node.get("market_name") or node.get("market") or node.get("market_alias") or node.get("marketName")
            if isinstance(name, str):
                markets[name] = markets.get(name, 0) + 1
            if len(samples) < 4:
                samples.append({k: node.get(k) for k in list(node)[:24]})
    return {"keysets": keysets, "markets": markets, "samples": samples}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", help="directory of previously saved raw bodies")
    parser.add_argument("--event-pages", type=int, default=4, help="event detail pages per sport")
    args = parser.parse_args()

    captured = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_dir = Path(args.raw) if args.raw else None
    if raw_dir:
        OUT_DIR = raw_dir / "out"
        OUT_DIR.mkdir(parents=True, exist_ok=True)

    probe: dict[str, Any] = {"captured_utc": captured, "sports": {}, "events": {}}
    all_rows: list[dict[str, Any]] = []

    for label, segment, sport_id in SPORTS:
        key = re.sub(r"[^a-z0-9]+", "-", label.lower())
        sport = {"label": label, "key": key, "sport_id": sport_id, "segment": segment}
        pages = {
            "hub": f"/betting-tips/{segment}/{sport_id}",
            "all_events": f"/betting-tips/{segment}/All_{segment}/All_Events/{sport_id}",
        }
        sport_probe: dict[str, Any] = {"sport_id": sport_id, "pages": {}, "api_urls": []}
        rows: list[dict[str, Any]] = []
        for name, page_path in pages.items():
            if raw_dir:
                candidate = raw_dir / f"{key}__{name}.json"
                if not candidate.exists():
                    sport_probe["pages"][name] = {"status": "missing-local"}
                    continue
                body = candidate.read_bytes()
                status, error = 200, ""
            else:
                status, body, error = fetch(data_url(page_path))
                time.sleep(0.7)
                (raw_dir / f"{key}__{name}.json").write_bytes(body) if raw_dir else None
            entry = {"status": status, "bytes": len(body), "error": error}
            if status == 200 and body:
                try:
                    tree = decode_payload(body)
                    found = collect_tips(tree)
                    entry["tips"] = len(found)
                    for api in api_urls(tree):
                        if api not in sport_probe["api_urls"]:
                            sport_probe["api_urls"].append(api)
                    rows.extend(normalise(row, sport) for row in found)
                except Exception as exc:  # noqa: BLE001
                    entry["decode_error"] = f"{type(exc).__name__}: {exc}"
            sport_probe["pages"][name] = entry

        # de-duplicate identical (event, market, selection, price) observations
        deduped: list[dict[str, Any]] = []
        seen: set[tuple] = set()
        for row in rows:
            key2 = (row["event_id"], row["market"], row["selection"], row["decimal_odds"])
            if key2 in seen:
                continue
            seen.add(key2)
            deduped.append(row)
        deduped.sort(key=lambda r: (r["start_utc"], r["event_name"], r["market"], r["selection"]))
        all_rows.extend(deduped)
        sport_probe["rows"] = len(deduped)
        sport_probe["events"] = len({r["event_id"] for r in deduped})
        probe["sports"][key] = sport_probe

        if deduped:
            (OUT_DIR / f"{key}.json").write_text(
                json.dumps({"sport": label, "sport_id": sport_id, "captured_utc": captured, "rows": deduped}, indent=1)
            )

        # Event detail: full market list for a few events per sport.
        if not raw_dir:
            event_ids: list[str] = []
            for row in deduped:
                if row["event_id"] and row["event_id"] not in event_ids:
                    event_ids.append(row["event_id"])
            for event_id in event_ids[: args.event_pages]:
                row = next(r for r in deduped if r["event_id"] == event_id)
                status, body, error = fetch(data_url(row["olbg_url"]))
                time.sleep(0.7)
                detail = {"status": status, "bytes": len(body), "error": error, "url": row["olbg_url"]}
                if status == 200 and body:
                    try:
                        tree = decode_payload(body)
                        detail["shapes"] = market_shapes(tree)
                        detail["api_urls"] = api_urls(tree)
                    except Exception as exc:  # noqa: BLE001
                        detail["decode_error"] = f"{type(exc).__name__}: {exc}"
                probe["events"][f"{key}:{event_id}"] = detail

    payload = {
        "captured_utc": captured,
        "source": "OLBG.com SvelteKit __data.json hydration feeds",
        "sports": {label: sid for label, _, sid in SPORTS},
        "rows": all_rows,
    }
    (OUT_DIR / "latest.json").write_text(json.dumps(payload, indent=1))
    (OUT_DIR / "_probe.json").write_text(json.dumps(probe, indent=1))
    print(f"captured {len(all_rows)} market rows across {len(SPORTS)} categories")


if __name__ == "__main__":
    main()
