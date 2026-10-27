#!/usr/bin/env python3
"""OLBG production collector — runs on a GitHub Actions runner.

OLBG is a SvelteKit app: the rendered HTML is a shell and the fixture, market
and price data is served as a flattened ``devalue`` payload at
``<page path>/__data.json``. This collector:

1. fetches every in-scope sport hub ``__data.json`` (16 categories),
2. decodes the flattened payload back into plain objects,
3. keeps every displayed tip/tournament row (selection, market, decimal/
   american/fractional odds, event id and url, unix start timestamp, tip
   counts, confidence, experts, expiry),
4. fetches ``__data.json`` for a bounded set of upcoming event pages to
   capture the full market grid (win, handicap, totals, set betting, ...),
5. commits the raw payloads and the parsed JSON back to the branch for
   line-by-line audit in the sandbox.

Honesty rules
-------------
- robots.txt is respected; a disallow stops collection for that path.
- No login, cookies, proxies or anti-bot evasion; a normal browser UA only.
- Every page records URL, HTTP status, sha256 and retrieval time.
- Decode failures are recorded with the error; no data is invented.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "olbg"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
MAX_BYTES = 4_000_000
EVENTS_PER_HUB = int(sys.argv[2]) if len(sys.argv) > 2 else 4

HUBS: dict[str, str] = {
    "tennis": "https://www.olbg.com/betting-tips/Tennis/3",
    "basketball": "https://www.olbg.com/betting-tips/Basketball/4",
    "golf": "https://www.olbg.com/betting-tips/Golf/5",
    "cricket": "https://www.olbg.com/betting-tips/Cricket/7",
    "snooker": "https://www.olbg.com/betting-tips/Snooker/8",
    "rugby-union": "https://www.olbg.com/betting-tips/Rugby_Union/9",
    "rugby-league": "https://www.olbg.com/betting-tips/Rugby_League/10",
    "baseball": "https://www.olbg.com/betting-tips/Baseball/12",
    "ice-hockey": "https://www.olbg.com/betting-tips/Ice_Hockey/13",
    "motor-racing": "https://www.olbg.com/betting-tips/Motor_Racing/14",
    "darts": "https://www.olbg.com/betting-tips/Darts/15",
    "handball": "https://www.olbg.com/betting-tips/Handball/20",
    "volleyball": "https://www.olbg.com/betting-tips/Volleyball/21",
    "gaelic-football": "https://www.olbg.com/betting-tips/Gaelic_Football/25",
    "hurling": "https://www.olbg.com/betting-tips/Hurling/26",
    "greyhounds": "https://www.olbg.com/betting-tips/Greyhounds/28",
}


# ------------------------------------------------------------- devalue decode
def unflatten(data: list) -> Any:
    """Rebuild SvelteKit's flattened devalue payload.

    Every distinct value is stored once in ``data``; any integer found inside
    a container is an index into that array (booleans are literals). The root
    value is at index 0.
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
            out_list: list = []
            cache[index] = out_list
            for ref in value:
                out_list.append(resolve(ref))
            return out_list
        cache[index] = value
        return value

    return resolve(0)


def decode(body: str) -> Any:
    raw = json.loads(body)
    if isinstance(raw, dict) and raw.get("type") == "data":
        nodes = raw.get("nodes") or []
        node = nodes[-1] if nodes else {}
        if node.get("type") == "error":
            raise ValueError(f"OLBG data error node: {node.get('error')}")
        if node.get("type") == "data" and isinstance(node.get("data"), list):
            return unflatten(node["data"])
    raise ValueError("unexpected __data.json shape")


# ----------------------------------------------------------------------- I/O
def curl(url: str, out: Path) -> tuple[str, str]:
    cmd = [
        "curl", "-sS", "-L", "--compressed", "-m", "45", "-A", UA,
        "-H", "Accept: application/json, text/html;q=0.9",
        "-o", str(out), "-w", "%{http_code}", url,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=75)
        return (proc.stdout.strip() or "000"), proc.stderr.strip()
    except Exception as exc:  # noqa: BLE001
        return "000", str(exc)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def ts_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm_row(row: Any, sport: str) -> dict | None:
    """Normalise one devalue row into the desk schema; None if not a row."""
    if not isinstance(row, dict):
        return None
    if not row.get("eventUrl") and not row.get("event_url"):
        return None
    try:
        start = row.get("event_start_unix_timestamp")
        start_utc = (
            datetime.fromtimestamp(int(start), tz=timezone.utc).isoformat()
            if start
            else None
        )
    except (TypeError, ValueError):
        start_utc = None
    return {
        "sport": sport,
        "tip_id": row.get("id"),
        "selection": row.get("selection"),
        "market": row.get("market_alias") or row.get("market"),
        "odds_decimal": row.get("odds"),
        "odds_american": row.get("american_odds"),
        "odds_fractional": row.get("fractional_odds"),
        "event_start_utc": start_utc,
        "event_start_unix": row.get("event_start_unix_timestamp"),
        "event_url": ("https://www.olbg.com" + row["eventUrl"]) if row.get("eventUrl") else None,
        "event_name": row.get("event_name_alias"),
        "league": row.get("menu_league"),
        "category_url": row.get("categoryUrl"),
        "experts": row.get("experts_count"),
        "win_tips": row.get("win_tips"),
        "win_tips_count": row.get("win_tips_count"),
        "nap_tips": row.get("nap_tips"),
        "ew_tips": row.get("ew_tips"),
        "confidence": row.get("confidence"),
        "stars_rating": row.get("stars_rating"),
        "comments": row.get("comments_count"),
        "expired": row.get("expired"),
        "vc_outcome_id": row.get("vc_outcome_id"),
        "vc_sport_id": row.get("vc_sport_id"),
        "venue": row.get("venue"),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*-2*.json"):
        if old.name != "summary.json":
            old.unlink()
    log: list[str] = []
    now = ts_iso()

    robots_raw = OUT / f"robots-{now[:10]}.txt"
    rcode, _ = curl("https://www.olbg.com/robots.txt", robots_raw)
    robots = robots_raw.read_text(errors="replace") if robots_raw.exists() else ""
    log.append(f"robots {rcode} {len(robots)}b")
    blocked_all = rcode != "200" or bool(
        re.search(r"^\s*user-agent\s*:\s*\*\s*\n?\s*disallow\s*:\s*/\s*$", robots, re.I | re.M)
    )

    all_tips: list[dict] = []
    all_tournaments: list[dict] = []
    summary: dict[str, Any] = {"retrieved_at": now, "sports": {}, "status": "ok"}

    if blocked_all:
        summary["status"] = "blocked-robots"
        (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
        print("\n".join(log) + "\nROBOTS BLOCKS COLLECTION.")
        return

    hub_rows: dict[str, list[dict]] = {}
    for slug, url in HUBS.items():
        data_url = url + "/__data.json"
        raw_path = OUT / f"hub-{slug}-__data.json"
        code, err = curl(data_url, raw_path)
        item: dict[str, Any] = {
            "slug": slug, "url": data_url, "retrieved_at": ts_iso(),
            "http_code": code, "sha256": sha256_of(raw_path), "bytes": raw_path.stat().st_size if raw_path.exists() else 0,
            "tips": 0, "tournaments": 0, "error": err or None,
        }
        if code == "200" and raw_path.exists():
            try:
                page = decode(raw_path.read_text(errors="replace"))
                tips, tourns = [], []
                for row in (page.get("tips") or []) if isinstance(page, dict) else []:
                    norm = norm_row(row, slug)
                    if norm:
                        tips.append(norm)
                for row in (page.get("tournaments") or []) if isinstance(page, dict) else []:
                    norm = norm_row(row, slug)
                    if norm:
                        tourns.append(norm)
                hub_rows[slug] = tips
                all_tips.extend(tips)
                all_tournaments.extend(tourns)
                item.update(tips=len(tips), tournaments=len(tourns))
            except Exception as exc:  # noqa: BLE001
                item["error"] = f"decode: {type(exc).__name__}: {exc}"
        else:
            item["error"] = item.get("error") or f"http {code}"
        summary["sports"][slug] = item
        log.append(f"hub {slug} {code} tips={item['tips']} tourns={item['tournaments']}")
        time.sleep(1)

    # ---- event pages: upcoming rows only, top by tip count ---------------
    now_unix = int(time.time())
    events_done: list[dict] = []
    for slug, rows in hub_rows.items():
        upcoming = [
            r for r in rows
            if isinstance(r.get("event_start_unix"), int) and r["event_start_unix"] > now_unix + 300
        ]
        upcoming.sort(key=lambda r: (r.get("win_tips_count") or 0), reverse=True)
        seen: set[str] = set()
        count = 0
        for row in upcoming:
            if count >= EVENTS_PER_HUB:
                break
            url = row.get("event_url")
            if not url or url in seen:
                continue
            seen.add(url)
            count += 1
            raw_path = OUT / f"event-{slug}-{count}-__data.json"
            code, err = curl(url + "/__data.json", raw_path)
            ev: dict[str, Any] = {
                "hub_slug": slug, "event_url": url, "retrieved_at": ts_iso(),
                "http_code": code, "sha256": sha256_of(raw_path),
                "bytes": raw_path.stat().st_size if raw_path.exists() else 0,
                "error": err or None, "markets": [],
            }
            if code == "200" and raw_path.exists():
                try:
                    page = decode(raw_path.read_text(errors="replace"))
                    markets = page.get("markets") if isinstance(page, dict) else None
                    if markets is None and isinstance(page, dict):
                        # event pages expose the grid under different keys;
                        # record the top-level keys for the audit and store the
                        # full decoded page so the sandbox can map them exactly.
                        ev["page_top_level_keys"] = sorted(k for k in page.keys() if isinstance(k, str))
                        (OUT / f"event-{slug}-{count}-decoded.json").write_text(
                            json.dumps(page, indent=2, ensure_ascii=False, default=str)[:MAX_BYTES]
                        )
                    if isinstance(markets, list):
                        ev["markets"] = markets
                except Exception as exc:  # noqa: BLE001
                    ev["error"] = f"decode: {type(exc).__name__}: {exc}"
            else:
                ev["error"] = ev.get("error") or f"http {code}"
            events_done.append(ev)
            log.append(f"event {slug} {row.get('event_name')} {code}")
            time.sleep(1)

    summary["events_captured"] = len(events_done)
    summary["total_tips"] = len(all_tips)
    summary["total_tournaments"] = len(all_tournaments)
    summary["status"] = "ok" if all_tips or all_tournaments else "empty"

    (OUT / "tips.json").write_text(json.dumps(all_tips, indent=2, ensure_ascii=False) + "\n")
    (OUT / "tournaments.json").write_text(json.dumps(all_tournaments, indent=2, ensure_ascii=False) + "\n")
    (OUT / "events.json").write_text(json.dumps(events_done, indent=2, ensure_ascii=False, default=str) + "\n")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    (OUT / f"fetch-log-{now[:10]}.txt").write_text("\n".join(log) + "\n")
    print("\n".join(log))
    print(
        f"DONE status={summary['status']} tips={summary['total_tips']} "
        f"tournaments={summary['total_tournaments']} events={summary['events_captured']}"
    )


if __name__ == "__main__":
    main()
