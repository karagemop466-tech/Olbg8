"""OLBG parsers: fixtures from sport pages, markets/odds/tip-consensus from event pages.

Validated against saved markup in data/olbg/html/. No guessing: every field is
read from an explicit attribute or JSON-LD block on the page.
"""
import json
import re

from bs4 import BeautifulSoup

BASE = "https://www.olbg.com"
ODDS_RE = re.compile(r"^\d+(\.\d+)?$")


def _txt(node):
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)) if node else ""


def parse_event_links(html, sport_slug, sport_id):
    """Return upcoming event stubs from a sport listing page."""
    soup = BeautifulSoup(html, "html.parser")
    events = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "event_id=" not in href or f"/{sport_slug}/" not in href:
            continue
        eid = re.search(r"event_id=(\d+)", href).group(1)
        url = href if href.startswith("http") else BASE + href
        name = _txt(a)
        if not name or len(name) < 3:
            continue
        # context: nearest ancestor that also contains a date/time string
        ctx = ""
        node = a
        for _ in range(5):
            node = node.parent
            if node is None:
                break
            ctx = _txt(node)
            if re.search(r"(Today|Tomorrow|\d{1,2} \w{3})", ctx):
                break
        when = ""
        m = re.search(r"(Today|Tomorrow|\d{1,2} \w{3})\s+(\d{1,2}:\d{2})", ctx)
        if m:
            when = f"{m.group(1)} {m.group(2)}"
        tips = ""
        mt = re.search(r"(\d+)\s*/\s*(\d+)\s*Win Tips", ctx)
        if mt:
            tips = f"{mt.group(1)}/{mt.group(2)}"
        pct = re.search(r"(\d+)%", ctx)
        rec = {
            "event_id": eid,
            "name": name,
            "url": url,
            "sport_slug": sport_slug,
            "sport_id": sport_id,
            "listing_when": when,
            "listing_tips": tips,
            "listing_pct": pct.group(1) if pct else "",
        }
        prev = events.get(eid)
        if prev is None or (len(rec["listing_tips"]) > len(prev["listing_tips"])):
            events[eid] = rec
    # competition path + fixture name from the canonical URL
    # /betting-tips/<Sport>/<Group>/<Comp>/<EventSlug>/<sport_id>
    for rec in events.values():
        parts = [p for p in rec["url"].split("?")[0].split("/") if p]
        if len(parts) >= 6:
            rec["competition_group"] = parts[2].replace("_", " ")
            rec["competition"] = parts[3].replace("_", " ")
            rec["fixture_slug"] = parts[4]
            rec["fixture_name"] = (parts[4].replace("_vs_", " vs ")
                                   .replace("_@_", " @ ").replace("_", " "))
        else:
            rec["competition_group"] = rec["competition"] = ""
    return list(events.values())


def parse_event_page(html):
    """Parse an OLBG event page into fixture metadata, markets and selections."""
    soup = BeautifulSoup(html, "html.parser")
    out = {"markets": [], "competitors": [], "start_utc": "", "name": "",
           "sport": "", "competition": "", "canonical": ""}
    # --- JSON-LD SportsEvent (authoritative for name/start/competitors)
    for sc in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(sc.string or "{}")
        except Exception:  # noqa: BLE001
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if item.get("@type") == "SportsEvent":
                out["name"] = item.get("name", "")
                out["start_utc"] = item.get("startDate", "")
                out["sport"] = item.get("sport", "")
                comps = item.get("competitor", [])
                out["competitors"] = [c.get("name", "") for c in comps if isinstance(c, dict)]
    link = soup.find("link", rel="canonical")
    if link:
        out["canonical"] = link.get("href", "")
    # breadcrumb competition (text of the event header block)
    h1 = soup.find("h1")
    if h1:
        parent = h1.find_parent()
        bread = _txt(parent)[:300] if parent else ""
        out["header_text"] = bread

    # --- markets and selections, built from odds spans (each selection row has one)
    rows = []
    for row in soup.select("div.grd"):
        if row.find_parent("div", class_="cmt"):
            continue                      # tipster comment card, not a selection row
        slct = row.select_one("div.rw.slct")
        odds = row.select_one("div.rw.odds span.ui-odds")
        if slct is None or odds is None:
            continue
        h4 = slct.find("h4")
        if h4 is None:
            continue
        dec = odds.get("data-decimal", "")
        if not dec or not ODDS_RE.match(dec):
            continue
        win = row.select_one("div.rw.win")
        wintxt = _txt(win) if win else ""
        mt = re.search(r"(\d+)\s*/\s*(\d+)\s*Win Tips", wintxt)
        mp = re.search(r"\b(\d{1,3})%", wintxt)
        # market name = nearest preceding market heading button
        market = ""
        prev = row.find_previous("button", id=re.compile(r"^market_id_"))
        if prev is not None:
            hh = prev.find("h4")
            market = _txt(hh) if hh else ""
        rows.append({
            "selection": _txt(h4),
            "market": market,
            "decimal": float(dec),
            "american": odds.get("data-american", ""),
            "fractional": odds.get("data-fractional", ""),
            "tips": f"{mt.group(1)}/{mt.group(2)}" if mt else "",
            "pct": mp.group(1) if mp else "",
        })

    # --- market headings (so markets with no priced selection are still recorded)
    headings = []
    for btn in soup.select('button[id^="market_id_"]'):
        h = btn.find("h4")
        if h:
            headings.append({"market_id": btn.get("id", ""), "market": _txt(h)})

    markets = {}
    for r in rows:
        key = r["market"] or "(unlabelled)"
        markets.setdefault(key, {"market": key, "selections": []})
        if all(s["selection"] != r["selection"] for s in markets[key]["selections"]):
            markets[key]["selections"].append({k: r[k] for k in
                                               ("selection", "decimal", "american",
                                                "fractional", "tips", "pct")})
    out["markets"] = list(markets.values())
    out["market_headings"] = headings
    # total tip count and consensus leader for the primary market
    out["tip_total"] = max([int(r["tips"].split("/")[1]) for r in rows if "/" in r["tips"]],
                           default=0)
    return out


def parse_sport_id(url):
    m = re.search(r"/(\d+)(?:\?|$)", url)
    return m.group(1) if m else ""
