#!/usr/bin/env python3
"""Parse OLBG sport index snapshots (data/raw/*.html) into data/fixtures.json.

Source: OLBG sport listing pages captured verbatim by .github/workflows/fetch-raw.yml.
Each emitted record points at the exact OLBG event page it came from.
No values are inferred: a field is null when OLBG did not publish it.
"""
import json, re, html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

SPORTS = {
    "tennis": ("Tennis", "Tennis", 3),
    "basketball": ("Basketball", "Basketball", 4),
    "golf": ("Golf", "Golf", 5),
    "cricket": ("Cricket", "Cricket", 7),
    "snooker": ("Snooker", "Snooker", 8),
    "rugby-union": ("Rugby Union", "Rugby_Union", 9),
    "rugby-league": ("Rugby League", "Rugby_League", 10),
    "baseball": ("Baseball", "Baseball", 12),
    "ice-hockey": ("Ice Hockey", "Ice_Hockey", 13),
    "motor-racing": ("Motor Racing", "Motor_Racing", 14),
    "darts": ("Darts", "Darts", 15),
    "handball": ("Handball", "Handball", 20),
    "volleyball": ("Volleyball", "Volleyball", 21),
    "gaelic-football": ("Gaelic Sports — Football", "Gaelic_Football", 25),
    "hurling": ("Gaelic Sports — Hurling", "Hurling", 26),
    "greyhounds": ("Greyhounds", "Greyhounds", 28),
}

ROW_SPLIT = re.compile(r'<li class="min-h-\[')
EVENT_URL = re.compile(r'itemprop="url" href="(https://www\.olbg\.com/betting-tips/[^"]+event_id=(\d+))"')
EVENT_NAME = re.compile(r'<h5 class="truncate" itemprop="name">(.*?)</h5>', re.S)
START = re.compile(r'<time[^>]*itemprop="startDate" datetime="([^"]+)"[^>]*>(.*?)</time>', re.S)
SELECTION = re.compile(r'<h4[^>]*>(.*?)</h4>', re.S)
MARKET = re.compile(r'<p class="truncate text-sm">(.*?)</p>', re.S)
ODDS = re.compile(r'data-decimal="([^"]*)" data-american="([^"]*)" data-fractional="([^"]*)"')
TIPS = re.compile(r'<b class="text-xs truncate">(.*?)</b>', re.S)
PCT = re.compile(r'^\s*(\d+(?:\.\d+)?)%\s*$')
COMMENTS = re.compile(r'<i class="i-ui-comments[^"]*"></i>\s*([^<]+)<')


def clean(s):
    if s is None:
        return None
    t = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def parse_file(sport_dir, sport_name, sport_slug, sport_id):
    path = RAW / f"{sport_slug}.html"
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8", errors="replace")
    # keep only the tip list region to avoid nav/sidebar duplication
    start = raw.find('<ul class="l-list">')
    body = raw[start:] if start >= 0 else raw
    body = body.split('<div class="pagination')[0]
    out = []
    for chunk in ROW_SPLIT.split(body)[1:]:
        m_url = EVENT_URL.search(chunk)
        if not m_url:
            continue
        url, eid = m_url.group(1), m_url.group(2)
        m_name = EVENT_NAME.search(chunk)
        m_start = START.search(chunk)
        m_sel = SELECTION.search(chunk)
        m_mkt = MARKET.search(chunk)
        m_odds = ODDS.search(chunk)
        m_tips = TIPS.search(chunk)
        m_pct = PCT.search(clean(m_tips.group(1)) or "") if m_tips else None
        if not (m_sel and m_mkt):
            continue
        tips_txt = clean(m_tips.group(1)) if m_tips else None
        tips_n = total_n = None
        if tips_txt:
            mm = re.match(r"(\d+)\s*/\s*(\d+)", tips_txt)
            if mm:
                tips_n, total_n = int(mm.group(1)), int(mm.group(2))
        out.append({
            "sport": sport_dir,
            "sport_name": sport_name,
            "sport_id": sport_id,
            "event_id": int(eid),
            "event": clean(m_name.group(1)) if m_name else None,
            "start_utc": m_start.group(1) if m_start else None,
            "start_display": clean(m_start.group(2)) if m_start else None,
            "selection": clean(m_sel.group(1)),
            "market": clean(m_mkt.group(1)),
            "decimal": float(m_odds.group(1)) if m_odds and m_odds.group(1) else None,
            "american": m_odds.group(2) if m_odds and m_odds.group(2) else None,
            "fractional": m_odds.group(3) if m_odds else None,
            "tips": tips_n,
            "tips_total": total_n,
            "tip_share_pct": float(m_pct.group(1)) if m_pct else None,
            "comments": clean(COMMENTS.search(chunk).group(1)) if COMMENTS.search(chunk) else None,
            "olbg_url": url,
            "sport_page": f"https://www.olbg.com/betting-tips/{SPORTS[sport_slug][1]}/{sport_id}",
        })
    return out


def main():
    rows = []
    for slug, (name, dirname, sid) in SPORTS.items():
        got = parse_file(dirname, name, slug, sid)
        # de-duplicate identical (event_id, selection, market)
        seen, uniq = set(), []
        for r in got:
            k = (r["event_id"], r["selection"], r["market"])
            if k in seen:
                continue
            seen.add(k)
            uniq.append(r)
        rows.extend(uniq)
        print(f"{slug:16s} events={len({r['event_id'] for r in uniq}):3d} rows={len(uniq):3d}")
    (ROOT / "data" / "fixtures.json").write_text(json.dumps(rows, indent=1) + "\n")
    print("total rows", len(rows), "events", len({(r['sport'], r['event_id']) for r in rows}))


if __name__ == "__main__":
    main()
