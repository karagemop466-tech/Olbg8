#!/usr/bin/env python3
"""OLBG collector.

Reverse-engineered sources
--------------------------
1. Sport hubs `/betting-tips/<Sport>/<id>` are JavaScript shells. Their
   SvelteKit hydration payload lives at `<path>/__data.json` in a flattened
   `devalue` array. That payload names OLBG's own JSON endpoints under keys such
   as `tipsApiUrl`.
2. Those endpoints (`/sports/<Sport>/top_tips?...&paginate=1-100`) return the
   tip rows: event, market, selection, decimal/American/fractional price,
   kick-off, expert and confidence counts. `paginate` is a plain range, so the
   whole board can be walked in pages of 100.
3. Each event page has its own hydration payload which carries the full market
   board for that event (all markets, all selections, all prices).

Only captured values are written. Missing values stay missing.

Modes
-----
--mode tips     walk the paginated tips API for every category
--mode detail   walk the event pages for the captured events (market depth)
--mode raw      dump one decoded event tree per category for parser work
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "olbg"

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
TIPS_HOST = "https://tipsb.olbg.info"
API_KEY = "S6H8MM3KN52Q8KN8"   # shipped in OLBG's own public page payload
PAGE = 100


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- devalue ---
def unflatten(data: list[Any]) -> Any:
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
            bucket: list[Any] = []
            cache[index] = bucket
            for ref in value:
                bucket.append(resolve(ref))
            return bucket
        cache[index] = value
        return value

    return resolve(0)


def decode_payload(body: bytes) -> Any:
    raw = json.loads(body.decode("utf-8", "replace"))
    nodes = raw.get("nodes") or []
    if not nodes:
        return raw
    node = nodes[-1]
    if node.get("type") == "error":
        raise ValueError(f"data node error: {node.get('error')}")
    if node.get("type") != "data" or not isinstance(node.get("data"), list):
        return None
    return unflatten(node["data"])


def walk(node: Any, limit: int = 600000):
    stack = [node]
    seen = 0
    while stack and seen < limit:
        seen += 1
        current = stack.pop()
        if isinstance(current, dict):
            yield current
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)


# ---------------------------------------------------------------- fetching --
def fetch(url: str, tries: int = 3, referer: str = f"{BASE}/betting-tips") -> tuple[int, bytes, str]:
    last = ""
    for attempt in range(tries):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": UA,
                    "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
                    "Accept-Language": "en-GB,en;q=0.9",
                    "Accept-Encoding": "gzip",
                    "Referer": referer,
                },
            )
            with urllib.request.urlopen(request, timeout=40) as response:
                body = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return response.status, body, ""
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}"
            if exc.code in (403, 429, 500, 502, 503):
                time.sleep(3 + attempt * 4)
            else:
                break
        except Exception as exc:  # pragma: no cover - network
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(2 + attempt * 2)
    return 0, b"", last


def absolute(url: str) -> str:
    """Resolve an OLBG data path to the host that actually serves it."""
    if url.startswith("http"):
        target = url
    elif url.startswith("/sports/"):
        target = TIPS_HOST + url
    else:
        target = BASE + url
    if "/sports/" in target and "api_key=" not in target:
        target += ("&" if "?" in target else "?") + f"api_key={API_KEY}"
    return target


def data_url(url: str) -> str:
    absolute = url if url.startswith("http") else BASE + url
    path, _, query = absolute.partition("?")
    target = path.rstrip("/") + "/__data.json"
    return f"{target}?{query}" if query else target


def api_templates(tree: Any) -> list[str]:
    found: list[str] = []
    for node in walk(tree):
        for key, value in node.items():
            if isinstance(key, str) and key.lower().endswith("apiurl") and isinstance(value, str):
                if "top_tips" in value and value not in found:
                    found.append(value)
    return found


# ------------------------------------------------------------- extraction ---
def market_rows(tree: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node in walk(tree):
        if "selection" in node and "market_alias" in node and "eventUrl" in node:
            rows.append(node)
    return rows


def to_decimal(value: Any) -> float | None:
    try:
        price = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return round(price, 4) if price > 1.0 else None


def american(decimal: float | None, given: Any = None) -> int | None:
    if given not in (None, "", "-"):
        try:
            return int(str(given).replace("+", ""))
        except ValueError:
            pass
    if not decimal:
        return None
    if decimal >= 2.0:
        return int(round((decimal - 1.0) * 100))
    return int(round(-100.0 / (decimal - 1.0)))


def iso_from_unix(value: Any) -> str:
    try:
        stamp = int(value)
    except (TypeError, ValueError):
        return ""
    if not 1_000_000_000 < stamp < 4_000_000_000:
        return ""
    return datetime.fromtimestamp(stamp, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def event_id_from(url: str) -> str:
    match = re.search(r"event_id=(\d+)", url or "")
    return match.group(1) if match else ""


def normalise(row: dict[str, Any], sport: dict[str, Any]) -> dict[str, Any]:
    decimal = to_decimal(row.get("odds"))
    url = str(row.get("eventUrl") or "")
    return {
        "sport": sport["label"],
        "sport_key": sport["key"],
        "sport_id": sport["sport_id"],
        "event_id": event_id_from(url),
        "event_name": str(row.get("event_name_alias") or "").strip(),
        "competition": str(row.get("menu_league") or "").strip(),
        "market": str(row.get("market_alias") or "").strip(),
        "selection": str(row.get("selection") or "").strip(),
        "decimal_odds": decimal,
        "american_odds": american(decimal, row.get("american_odds")),
        "fractional_odds": str(row.get("fractional_odds") or ""),
        "start_utc": iso_from_unix(row.get("event_start_unix_timestamp")),
        "olbg_url": url if url.startswith("http") else BASE + url,
        "experts_count": row.get("experts_count"),
        "win_tips": row.get("win_tips"),
        "win_tips_count": row.get("win_tips_count"),
        "confidence": row.get("confidence"),
        "comments_count": row.get("comments_count"),
        "expired": row.get("expired"),
        "venue": row.get("venue") or "",
        "address": row.get("address") or "",
    }


# ------------------------------------------------------------------ modes ---
def collect_tips(state: dict[str, Any], max_pages: int) -> None:
    probe = state["probe"]
    all_rows: list[dict[str, Any]] = []
    for label, segment, sport_id in SPORTS:
        key = re.sub(r"[^a-z0-9]+", "-", label.lower())
        sport = {"label": label, "key": key, "sport_id": sport_id, "segment": segment}
        hub = f"/betting-tips/{segment}/{sport_id}"
        status, body, error = fetch(data_url(hub))
        entry: dict[str, Any] = {"hub": {"status": status, "bytes": len(body), "error": error}, "pages": []}
        templates: list[str] = []
        if status == 200 and body:
            try:
                templates = api_templates(decode_payload(body))
            except Exception as exc:  # noqa: BLE001
                entry["hub"]["decode_error"] = f"{type(exc).__name__}: {exc}"
        if not templates:
            templates = [
                f"/sports/{segment}/top_tips?source=&paginate=1-100&include_recommendations=1"
                "&include_expired=0&bookie_name=_best_&client_type=desktop_website"
            ]
        entry["templates"] = templates[:2]
        extra_pages = [f"/betting-tips/{segment}/All_{segment}/All_Events/{sport_id}"]

        rows: list[dict[str, Any]] = []
        working: str | None = None
        for index in range(max_pages):
            start = index * PAGE + 1
            end = start + PAGE - 1
            candidates = [working] if working else list(templates) + [
                f"/sports/{segment}/top_tips?source=&paginate=1-100&include_recommendations=1"
                "&include_expired=0&bookie_name=_best_&client_type=desktop_website"
            ]
            status, body, error, url = 0, b"", "no candidate", ""
            for candidate in candidates:
                if not candidate:
                    continue
                url = re.sub(r"paginate=[\d\-]+", f"paginate={start}-{end}", candidate)
                url = url.replace("include_expired=1", "include_expired=0")
                url = absolute(url)
                status, body, error = fetch(url, tries=2)
                print(f"{key} {start}-{end} status={status} bytes={len(body)} host={url.split('/')[2]} err={error}", flush=True)
                if status == 200 and body:
                    working = candidate
                    break
            page_info = {"range": f"{start}-{end}", "status": status, "bytes": len(body), "error": error}
            if status != 200 or not body:
                entry["pages"].append(page_info)
                break
            try:
                tree = decode_payload(body)
                found = market_rows(tree)
            except Exception as exc:  # noqa: BLE001
                page_info["decode_error"] = f"{type(exc).__name__}: {exc}"
                entry["pages"].append(page_info)
                break
            page_info["rows"] = len(found)
            entry["pages"].append(page_info)
            print(f"{key} {start}-{end} rows={len(found)}", flush=True)
            rows.extend(normalise(row, sport) for row in found)
            if len(found) < PAGE:
                break
            time.sleep(0.4)

        deduped: list[dict[str, Any]] = []
        seen: set[tuple] = set()
        for row in rows:
            sig = (row["event_id"], row["market"], row["selection"], row["decimal_odds"])
            if sig in seen:
                continue
            seen.add(sig)
            deduped.append(row)
        for page_path in extra_pages:
            status2, body2, error2 = fetch(data_url(page_path))
            extra = {"status": status2, "bytes": len(body2), "error": error2}
            if status2 == 200 and body2:
                try:
                    found2 = market_rows(decode_payload(body2))
                    extra["tips"] = len(found2)
                    rows.extend(normalise(row, sport) for row in found2)
                except Exception as exc:  # noqa: BLE001
                    extra["decode_error"] = f"{type(exc).__name__}: {exc}"
            entry.setdefault("extra_pages", []).append(extra)

        deduped: list[dict[str, Any]] = []
        seen2: set[tuple] = set()
        for row in rows:
            sig = (row["event_id"], row["market"], row["selection"], row["decimal_odds"])
            if sig in seen2:
                continue
            seen2.add(sig)
            deduped.append(row)
        deduped.sort(key=lambda r: (r["start_utc"], r["event_name"], r["market"], r["selection"]))
        all_rows.extend(deduped)
        entry["rows"] = len(deduped)
        entry["events"] = len({r["event_id"] for r in deduped})
        probe["sports"][key] = entry
        if deduped:
            (OUT_DIR / f"{key}.json").write_text(
                json.dumps({"sport": label, "sport_id": sport_id, "captured_utc": state["captured"], "rows": deduped}, indent=1)
            )

    state["rows"] = all_rows
    (OUT_DIR / "latest.json").write_text(
        json.dumps(
            {"captured_utc": state["captured"], "source": "OLBG.com top_tips JSON endpoint", "rows": all_rows},
            indent=1,
        )
    )


def collect_detail(state: dict[str, Any], per_sport: int) -> None:
    """Fetch event pages and keep every market row plus a structural probe."""
    latest = json.loads((OUT_DIR / "latest.json").read_text())
    rows = latest["rows"]
    detail: dict[str, Any] = {}
    by_sport: dict[str, list[str]] = {}
    for row in rows:
        if not row["event_id"] or not row["olbg_url"]:
            continue
        bucket = by_sport.setdefault(row["sport_key"], [])
        if row["event_id"] not in bucket:
            bucket.append(row["event_id"])
    for sport_key, event_ids in by_sport.items():
        kept: list[dict[str, Any]] = []
        for event_id in event_ids[:per_sport]:
            row = next(r for r in rows if r["event_id"] == event_id)
            status, body, error = fetch(data_url(row["olbg_url"]), tries=2, referer=row["olbg_url"])
            record: dict[str, Any] = {"event_id": event_id, "event_name": row["event_name"], "status": status, "bytes": len(body), "error": error}
            if status == 200 and body:
                try:
                    tree = decode_payload(body)
                    shapes = market_board(tree)
                    record["markets"] = shapes["markets"]
                    record["rows"] = shapes["rows"]
                    record["api_urls"] = shapes["api_urls"][:4]
                    record["keysets"] = shapes["keysets"]
                    kept.append(record)
                except Exception as exc:  # noqa: BLE001
                    record["decode_error"] = f"{type(exc).__name__}: {exc}"
            detail[f"{sport_key}:{event_id}"] = record
            time.sleep(0.35)
        (OUT_DIR / f"{sport_key}-markets.json").write_text(json.dumps(kept, indent=1))
    (OUT_DIR / "_detail.json").write_text(json.dumps(detail, indent=1))


def market_board(tree: Any) -> dict[str, Any]:
    """Collect every selection-level odds object on an event page."""
    rows: list[dict[str, Any]] = []
    keysets: dict[str, int] = {}
    apis: list[str] = []
    for node in walk(tree):
        for key, value in node.items():
            if isinstance(key, str) and key.lower().endswith("apiurl") and isinstance(value, str):
                if value not in apis:
                    apis.append(value)
        if "odds" not in node:
            continue
        if not ({"selection", "name", "outcome", "outcome_name"} & set(node)):
            continue
        signature = ",".join(sorted(str(k) for k in node))[:400]
        keysets[signature] = keysets.get(signature, 0) + 1
        slim = {k: node[k] for k in node if not isinstance(node[k], (dict, list))}
        if len(json.dumps(slim)) < 900:
            rows.append(slim)
    markets: dict[str, int] = {}
    for row in rows:
        name = row.get("market_alias") or row.get("market_name") or row.get("market")
        if isinstance(name, str):
            markets[name] = markets.get(name, 0) + 1
    return {"rows": rows[:400], "keysets": dict(sorted(keysets.items(), key=lambda kv: -kv[1])[:12]), "markets": markets, "api_urls": apis}


def dump_raw(state: dict[str, Any]) -> None:
    """Save one full decoded event payload per category for parser development."""
    latest = json.loads((OUT_DIR / "latest.json").read_text())
    raw_dir = OUT_DIR / "raw"
    raw_dir.mkdir(exist_ok=True)
    seen: set[str] = set()
    for row in latest["rows"]:
        if row["sport_key"] in seen or not row["olbg_url"]:
            continue
        seen.add(row["sport_key"])
        status, body, error = fetch(data_url(row["olbg_url"]), tries=2, referer=row["olbg_url"])
        if status != 200 or not body:
            continue
        try:
            tree = decode_payload(body)
        except Exception:  # noqa: BLE001
            continue
        text = json.dumps(tree)
        if len(text) > 3_000_000:
            continue
        (raw_dir / f"{row['sport_key']}.json").write_text(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="tips", choices=["tips", "detail", "raw", "all"])
    parser.add_argument("--max-pages", type=int, default=12)
    parser.add_argument("--detail-events", type=int, default=30)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    state: dict[str, Any] = {"captured": now_iso(), "probe": {"captured_utc": now_iso(), "sports": {}}}

    if args.mode in ("tips", "all"):
        collect_tips(state, args.max_pages)
        (OUT_DIR / "_probe.json").write_text(json.dumps(state["probe"], indent=1))
        print(f"tips: {len(state['rows'])} rows")
    if args.mode in ("detail", "all"):
        collect_detail(state, args.detail_events)
        print("detail captured")
    if args.mode == "raw":
        dump_raw(state)
        print("raw dumps captured")


if __name__ == "__main__":
    main()
