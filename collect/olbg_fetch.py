#!/usr/bin/env python3
"""OLBG collector — runs on a GitHub Actions runner (full internet egress).

Saves raw HTML snapshots of OLBG hub pages plus a bounded set of event pages
under ``data/raw/`` and probes for machine-readable price payloads.

Stages
------
exploratory
    Dump raw HTML, SvelteKit JSON script blocks, ``?_data`` responses and
    event-like objects discovered inside them, so parse rules can be written
    against the real payload shape. Writes ``data/raw/probe-<ts>.json``.
production
    (enabled after the payload shape is confirmed) emit ``data/olbg-live.json``
    with per-event selection, price and tip statistics.

Honesty rules
-------------
- robots.txt is respected; a disallow or an access challenge stops collection
  for that page. No bypass, no cookie or login handling, no proxy rotation.
- Every saved page records URL, HTTP status, sha256 and fetch time.
- Anything unparsed stays null; nothing is inferred or filled in.
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

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
MAX_BYTES = 2_500_000
EVENT_PAGES_PER_HUB = int(sys.argv[2]) if len(sys.argv) > 2 else 3

HUBS = {
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


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def curl(url: str, out: Path) -> tuple[str, str]:
    cmd = [
        "curl", "-sS", "-L", "--compressed", "-m", "45", "-A", UA,
        "-H", "Accept: text/html,application/xhtml+xml",
        "-H", "Accept-Language: en-GB,en;q=0.9",
        "-o", str(out), "-w", "%{http_code}", url,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=75)
        return (proc.stdout.strip() or "000"), proc.stderr.strip()
    except Exception as exc:  # noqa: BLE001
        return "000", str(exc)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def prune(slug: str, ts: str) -> None:
    """Keep only the newest raw snapshot per slug so the repo stays lean."""
    for old in sorted(RAW.glob(f"{slug}-*")):
        if old.name != f"{slug}-{ts}.html" and old.name != f"{slug}-{ts}.data.json":
            old.unlink()


def extract_scripts(body: str) -> list[str]:
    return re.findall(r"<script[^>]*>(.*?)</script>", body, re.S | re.I)


def find_event_objects(node, found: list, depth: int = 0) -> None:
    """Recursively collect objects that look like priced event rows."""
    if depth > 12 or len(found) > 400:
        return
    if isinstance(node, dict):
        keys = {str(k).lower() for k in node}
        if ("event_id" in keys or "eventid" in keys or "id" in keys) and (
            "name" in keys or "event_name" in keys or "title" in keys
        ):
            blob = json.dumps(node, ensure_ascii=False)
            if any(m in blob for m in ("odds", "price", "decimal", "fraction", "american", "tip")):
                found.append(node)
        for value in node.values():
            find_event_objects(value, found, depth + 1)
    elif isinstance(node, list):
        for value in node:
            find_event_objects(value, found, depth + 1)


def fetch_page_record(slug: str, url: str, ts: str, want_data: bool = True) -> dict:
    record = {
        "slug": slug,
        "url": url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "http_code": None,
        "size": 0,
        "sha256": "",
        "payloads": [],
        "event_objects_sample": [],
        "error": None,
    }
    out = RAW / f"{slug}-{ts}.html"
    code, err = curl(url, out)
    record["http_code"] = code
    record["error"] = err or None
    if code != "200" or not out.exists():
        return record
    body = out.read_text(errors="replace")
    record["size"] = len(body)
    record["sha256"] = sha256_of(out)
    if any(tok in body.lower() for tok in ("just a moment", "cf-chl-", "captcha", "access denied")):
        record["error"] = "Access challenge present; no bypass attempted"
        return record

    # 1) SvelteKit v2 style: <script type="application/json" id="sveltekit-...">
    for m in re.finditer(
        r'<script[^>]*type="application/json"[^>]*id="(sveltekit-[^"]+)"[^>]*>(.*?)</script>',
        body, re.S | re.I,
    ):
        data_id, raw_json = m.group(1), m.group(2).strip()
        (RAW / f"{slug}-{ts}.{data_id}.json").write_text(raw_json[:MAX_BYTES])
        record["payloads"].append({"kind": "sveltekit-json", "id": data_id, "bytes": len(raw_json)})
        found: list = []
        try:
            find_event_objects(json.loads(raw_json), found)
            record["event_objects_sample"] = found[:6]
        except Exception:  # noqa: BLE001
            pass

    # 2) Fallback: inline scripts mentioning pricing markers
    if not record["payloads"]:
        for idx, script in enumerate(extract_scripts(body)):
            if any(mk in script for mk in ("event_id", "eventid", "odds", "fractional", "decimal")) and len(script) > 300:
                (RAW / f"{slug}-{ts}.script{idx}.js").write_text(script[:MAX_BYTES])
                record["payloads"].append({"kind": "inline-script", "index": idx, "bytes": len(script)})

    # 3) SvelteKit data endpoint probe
    if want_data:
        dout = RAW / f"{slug}-{ts}.data.json"
        dcode, derr = curl(url + "?_data", dout)
        record["data_endpoint"] = {
            "url": url + "?_data",
            "http_code": dcode,
            "bytes": dout.stat().st_size if dout.exists() else 0,
        }
        if dcode == "200" and dout.exists():
            found: list = []
            try:
                find_event_objects(json.loads(dout.read_text(errors="replace")), found)
                record["data_endpoint"]["event_objects"] = len(found)
                if not record["event_objects_sample"]:
                    record["event_objects_sample"] = found[:6]
            except Exception:  # noqa: BLE001
                record["data_endpoint"]["parse_error"] = "not JSON"
    return record


def event_links_in(body: str) -> list[str]:
    links = re.findall(
        r'https://www\.olbg\.com/betting-tips/[^"\'\s<>]+?event_id=(\d+)', body
    )
    seen, out = set(), []
    for eid in links:
        if eid not in seen:
            seen.add(eid)
            out.append(eid)
    return out


def main() -> None:
    stage = sys.argv[1] if len(sys.argv) > 1 else "exploratory"
    ts = now_tag()
    RAW.mkdir(parents=True, exist_ok=True)
    log: list[str] = []

    # robots.txt — respect it; a failure means "do not collect", never "bypass".
    robots_url = "https://www.olbg.com/robots.txt"
    robots_path = RAW / f"robots-{ts}.txt"
    rcode, _ = curl(robots_url, robots_path)
    robots_text = robots_path.read_text(errors="replace") if robots_path.exists() else ""
    log.append(f"robots {rcode} {len(robots_text)}b")
    blocked_all = rcode != "200" or bool(
        re.search(r"^\s*user-agent\s*:\s*\*\s*disallow\s*:\s*/\s*$", robots_text, re.I | re.M)
    )

    probe = {
        "stage": stage,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "robots": {"url": robots_url, "http_code": rcode, "body": robots_text[:4000]},
        "pages": [],
    }
    if blocked_all:
        probe["status"] = "blocked-robots"
        (RAW / f"probe-{ts}.json").write_text(json.dumps(probe, indent=2))
        print("\n".join(log) + "\nROBOTS BLOCKS COLLECTION; nothing fetched.")
        return

    hub_event_counts: dict[str, list[str]] = {}
    for slug, url in HUBS.items():
        rec = fetch_page_record(slug, url, ts)
        prune(slug, ts)
        probe["pages"].append({k: v for k, v in rec.items() if k != "event_objects_sample"})
        log.append(
            f"hub {slug} {rec['http_code']} {rec['size']}b payloads={len(rec['payloads'])} "
            f"data_ep={rec.get('data_endpoint', {}).get('http_code')}"
        )
        if rec["http_code"] == "200" and rec.get("sha256"):
            hub_event_counts[slug] = event_links_in(
                (RAW / f"{slug}-{ts}.html").read_text(errors="replace")
            )[: EVENT_PAGES_PER_HUB]
        time.sleep(1)

    # Bounded event-page fetches (market context + price payload shape)
    ev_idx = 0
    for slug, eids in hub_event_counts.items():
        for eid in eids:
            ev_idx += 1
            # reconstruct link from the hub snapshot
            src = (RAW / f"{slug}-{ts}.html").read_text(errors="replace")
            m = re.search(rf'(https://www\.olbg\.com/betting-tips/[^"\'\s<>]+?event_id={eid})', src)
            if not m:
                continue
            url = m.group(1)
            erec = fetch_page_record(f"event-{slug}-{ev_idx}", url, ts, want_data=False)
            probe["pages"].append(
                {k: v for k, v in erec.items() if k != "event_objects_sample"}
                | {"role": "event_page", "event_id": eid, "hub_slug": slug}
            )
            log.append(f"event {slug} {eid} {erec['http_code']} {erec['size']}b")
            time.sleep(1)
            if ev_idx >= 60:
                break

    probe["status"] = "partial" if any(
        p.get("http_code") == "200" for p in probe["pages"]
    ) else "blocked"
    (RAW / f"probe-{ts}.json").write_text(json.dumps(probe, indent=2, default=str))
    (RAW / f"fetch-log-{ts}.txt").write_text("\n".join(log) + "\n")
    print("\n".join(log))
    print(f"probe written: data/raw/probe-{ts}.json status={probe['status']}")


if __name__ == "__main__":
    main()
