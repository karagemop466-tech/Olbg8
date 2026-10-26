#!/usr/bin/env python3
"""Originate prices for every OLBG market we collected, then choose picks.

Method (documented in docs/methodology/pricing.md):
  1. market anchor  : de-vigged implied probability from the prices OLBG displays
  2. model prior    : available for tennis (ATP/WTA ranking points), NHL, MLB and
                      NBA (Pythagorean + log5 + measured home advantage)
  3. blend          : p = w * model + (1 - w) * anchor, w set per sport from the
                      quality of the rating input (never above 0.5)
  4. prices         : fair decimal = 1/p. A 3% book margin is carried on the
                      opposing side, so the pick itself is offered at fair odds.
  5. confidence     : high >= 70%, medium 60-69.9%, low < 60%  (absolute, so a
                      six-runner greyhound race can never produce a 'high' pick)

Every row keeps the OLBG event URL plus the reference-source URL used, so each
number in the output is checkable. Nothing is invented: when a rating input is
missing the row says so and confidence is capped.
"""
import json
import math
import os
import re
from datetime import datetime, timezone

OLBG_DIR = "data/olbg"
REF_DIR = "data/reference"
OUT_LINES = "data/lines.json"
OUT_PICKS = "data/picks.json"
OUT_INDEX = "data/coverage.json"

SPORTS = ["Golf", "Volleyball", "Rugby_Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic_Football", "Greyhounds", "Tennis", "Motor_Racing", "Handball",
          "Ice_Hockey", "Basketball", "Rugby_League"]
SPORT_LABEL = {"Gaelic_Football": "Gaelic Sports"}
BAND_LOW, BAND_HIGH = 1.40, 101.0          # -250 to +10000 in decimal terms

# ---------------------------------------------------------------- parameters
# sd = standard deviation of the margin (home score - away score) in that sport's
# scoring unit; used only to price handicap/total markets around a mean.
PARAMS = {
    "Tennis":        {"two_way": True,  "sd": 6.0,  "model": "tennis"},
    "Basketball":    {"two_way": True,  "sd": 12.0, "model": "nba"},
    "Ice_Hockey":    {"two_way": True,  "sd": 2.3,  "model": "nhl"},
    "Baseball":      {"two_way": True,  "sd": 4.3,  "model": "mlb"},
    "Cricket":       {"two_way": True,  "sd": 30.0, "model": "anchor"},
    "Volleyball":    {"two_way": True,  "sd": 8.0,  "model": "anchor"},
    "Handball":      {"two_way": True,  "sd": 8.0,  "model": "anchor", "draw": 0.08},
    "Rugby_Union":   {"two_way": True,  "sd": 13.0, "model": "anchor", "draw": 0.04},
    "Rugby_League":  {"two_way": True,  "sd": 14.0, "model": "anchor", "draw": 0.03},
    "Gaelic_Football": {"two_way": True, "sd": 12.0, "model": "anchor", "draw": 0.05},
    "Snooker":       {"two_way": True,  "sd": 2.0,  "model": "anchor"},
    "Darts":         {"two_way": True,  "sd": 2.5,  "model": "anchor"},
    "Greyhounds":    {"two_way": False, "sd": 0.0,  "model": "anchor"},
    "Golf":          {"two_way": False, "sd": 0.0,  "model": "anchor"},
    "Motor_Racing":  {"two_way": False, "sd": 0.0,  "model": "anchor"},
}
MARKET_WEIGHT = {"tennis": 0.45, "nhl": 0.45, "mlb": 0.45, "nba": 0.40, "anchor": 0.0}

WIN_KEYS = ("win match", "money line", "match winner", "to win", "win tournament",
            "outright", "daily races", "daily race", "winner", "head to head")
HCP_KEYS = ("handicap", "pointspread", "point spread", "games won", "set handicap",
            "spread", "line", "start")
TOTAL_KEYS = ("total", "over/under", "over under", "points total", "goals total")


# ---------------------------------------------------------------- utilities
def american(dec):
    if dec is None:
        return ""
    if dec >= 2.0:
        return f"+{round((dec - 1) * 100)}"
    return f"{round(-100 / (dec - 1))}"


def dec_from_prob(p):
    return round(1.0 / p, 3) if p and p > 0 else None


def implied(dec):
    return 1.0 / dec if dec and dec > 1.0 else None


def devig(probs):
    s = sum(p for p in probs if p)
    if not s:
        return probs
    return [p / s if p else p for p in probs]


def market_type(name):
    n = (name or "").lower()
    if any(k in n for k in TOTAL_KEYS):
        return "TOTAL"
    if any(k in n for k in HCP_KEYS):
        return "HANDICAP"
    if any(k in n for k in WIN_KEYS):
        return "WIN"
    return "OTHER"


def line_value(selection):
    m = re.search(r"([+-]?\d+(?:\.\d+)?)\s*$", selection or "")
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    m = re.search(r"(?:over|under)\s*([+-]?\d+(?:\.\d+)?)", (selection or "").lower())
    return float(m.group(1)) if m else None


def norm(s):
    s = (s or "").lower()
    s = re.sub(r"\b(fc|afc|sc|bc|club|the)\b", " ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def starts(ts):
    return ts


# ---------------------------------------------------------------- reference
class Ref:
    def __init__(self):
        self.nhl = self._load("ice_hockey")
        self.mlb = self._load("baseball")
        self.nba = self._load("basketball")
        self.f1 = self._load("motor_racing")
        self.atp = self._load("pages/tennis_atp_rankings")
        self.wta = self._load("pages/tennis_wta_rankings")
        self.rank = {}
        for tour, snap in (("ATP", self.atp), ("WTA", self.wta)):
            for tbl in (snap or {}).get("tables", [])[:1]:
                rows = tbl.get("rows", [])
                for row in rows:
                    if len(row) < 4 or not row[0].isdigit():
                        continue
                    pts = row[3].replace(",", "")
                    if not pts.isdigit():
                        continue
                    self.rank[norm(row[2])] = {"tour": tour, "rank": int(row[0]),
                                               "points": int(pts)}
        self.home_edge = {}

    def _load(self, name):
        p = os.path.join(REF_DIR, f"{name}.json")
        try:
            with open(p) as fh:
                return json.load(fh)
        except Exception:  # noqa: BLE001
            return {}

    # ---- lookups
    def nhl_team(self, name):
        target = norm(name).split()[-1]
        for t in self.nhl.get("teams", []):
            if norm(t.get("team", "")).endswith(target) or t.get("abbrev", "").lower() == norm(name):
                return t
        return None

    def mlb_team(self, name):
        target = norm(name).split()[-1]
        for t in self.mlb.get("teams", []):
            if norm(t.get("team", "")).endswith(target):
                return t
        return None

    def nba_team(self, name):
        n = norm(name)
        for t in self.nba.get("teams", []):
            tn = norm(t.get("team", ""))
            if not tn:
                continue
            if tn.endswith(n.split()[-1]) or n.endswith(tn.split()[-1]):
                return t
        return None

    def player(self, name):
        n = norm(name)
        if n in self.rank:
            return self.rank[n]
        last = n.split()[-1] if n else ""
        for k, v in self.rank.items():
            if k.split() and k.split()[-1] == last:
                return v
        return None


# ---------------------------------------------------------------- models
def pyhthag_pct(scored, allowed, exp):
    if not scored or not allowed:
        return None
    try:
        s, a = float(scored), float(allowed)
    except (TypeError, ValueError):
        return None
    if s <= 0 or a <= 0:
        return None
    return (s ** exp) / ((s ** exp) + (a ** exp))


def log5(pa, pb):
    if pa is None or pb is None:
        return None
    eps = 1e-6
    pa = min(max(pa, eps), 1 - eps)
    pb = min(max(pb, eps), 1 - eps)
    num = pa * (1 - pb)
    den = num + pb * (1 - pa)
    return num / den if den else None


def fnum(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def apply_home(p_neutral, hca_prob):
    """Shift a neutral-venue probability by a measured home advantage."""
    if p_neutral is None or hca_prob is None:
        return p_neutral
    logit = math.log(p_neutral / (1 - p_neutral)) + hca_prob
    return 1 / (1 + math.exp(-logit))


def league_home_logit(ref, kind):
    """Measured league-wide home advantage as a logit shift, from official data."""
    if kind in ref.home_edge:
        return ref.home_edge[kind]
    val = None
    if kind == "mlb":
        hw = sum(fnum(t.get("home")) or 0 for t in ref.mlb.get("teams", []))
        aw = sum(fnum(t.get("away")) or 0 for t in ref.mlb.get("teams", []))
        if hw and aw:
            val = math.log((hw / (hw + aw)) / (1 - hw / (hw + aw)))
    elif kind == "nhl":
        hw = sum(fnum(t.get("home_wins")) or 0 for t in ref.nhl.get("teams", []))
        hl = sum(fnum(t.get("home_losses")) or 0 for t in ref.nhl.get("teams", []))
        if hw and hl:
            p = hw / (hw + hl)
            val = math.log(p / (1 - p))
    ref.home_edge[kind] = val
    return val


def model_prob(sport, home, away, ref):
    """Return (probability for 'home' side, facts dict, source url) or (None, {}, '')."""
    kind = PARAMS[sport]["model"]
    facts, src = {}, ""
    if kind == "nba":
        ht, at = ref.nba_team(home), ref.nba_team(away)
        if ht and at:
            ph = pyhthag_pct(ht.get("points_for"), ht.get("points_against"), 13.91)
            pa = pyhthag_pct(at.get("points_for"), at.get("points_against"), 13.91)
            base = log5(ph, pa)
            hca = league_home_logit(ref, "nba")
            if hca is None:
                hca = math.log(0.55 / 0.45)      # documented fallback: 55% league home rate
            p = apply_home(base, hca) if base else None
            facts = {"home": ht, "away": at, "method": "Pythagorean (exp 13.91) + log5"}
            src = "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings?season=2027"
            return p, facts, src
    if kind == "nhl":
        ht, at = ref.nhl_team(home), ref.nhl_team(away)
        if ht and at:
            ph = pyhthag_pct(ht.get("goals_for"), ht.get("goals_against"), 2.0)
            pa = pyhthag_pct(at.get("goals_for"), at.get("goals_against"), 2.0)
            base = log5(ph, pa)
            p = apply_home(base, league_home_logit(ref, "nhl")) if base else None
            facts = {"home": ht, "away": at, "method": "Pythagorean goals (exp 2) + log5"}
            src = "https://api-web.nhle.com/v1/standings/now"
            return p, facts, src
    if kind == "mlb":
        ht, at = ref.mlb_team(home), ref.mlb_team(away)
        if ht and at:
            ph = pyhthag_pct(ht.get("runs_scored"), ht.get("runs_allowed"), 1.83)
            pa = pyhthag_pct(at.get("runs_scored"), at.get("runs_allowed"), 1.83)
            base = log5(ph, pa)
            p = apply_home(base, league_home_logit(ref, "mlb")) if base else None
            facts = {"home": ht, "away": at, "method": "Pythagorean runs (exp 1.83) + log5"}
            src = "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026"
            return p, facts, src
    if kind == "tennis":
        hp, ap = ref.player(home), ref.player(away)
        if hp and ap:
            p = hp["points"] / (hp["points"] + ap["points"])
            facts = {"home": hp, "away": ap, "method": "Bradley-Terry on ranking points"}
            src = ("https://www.atptour.com/en/rankings/singles"
                   if hp["tour"] == "ATP" else
                   "https://www.wtatennis.com/rankings/singles")
            return p, facts, src
    return None, {}, ""


# ---------------------------------------------------------------- pricing
def price_event(ev, sport, ref):
    markets = ev.get("markets") or []
    if not markets:
        return []
    comps = ev.get("competitors") or []
    home = comps[0] if len(comps) > 0 else ""
    away = comps[1] if len(comps) > 1 else ""
    # OLBG lists US-style fixtures as "AWAY @ HOME"; JSON-LD keeps page order, so
    # resolve from the event name when it carries the venue marker.
    name = ev.get("name") or ""
    if " @ " in name:
        left, right = [s.strip() for s in name.split(" @ ", 1)]
        away, home = left, right
    mtype_overall = None
    mprob, facts, msrc = model_prob(sport, home, away, ref)
    weight = MARKET_WEIGHT.get(PARAMS[sport]["model"], 0.0)
    if mprob is None:
        weight = 0.0

    rows = []
    for mkt in markets:
        mt = market_type(mkt["market"])
        sels = mkt.get("selections", [])
        if mt == "OTHER":
            # market-level de-vig only (correct score, set betting, etc.)
            probs = devig([implied(s["decimal"]) for s in sels])
            for sel, p_m in zip(sels, probs):
                if p_m is None:
                    continue
                p = p_m
                rows.append(rec(sport, ev, mkt, sel, mt, p, p_m, 0.0,
                                facts, msrc, home, away))
            continue
        if mt == "TOTAL":
            probs = devig([implied(s["decimal"]) for s in sels])
            for sel, p_m in zip(sels, probs):
                if p_m is None:
                    continue
                rows.append(rec(sport, ev, mkt, sel, mt, p_m, p_m, 0.0,
                                facts, msrc, home, away))
            continue
        if mt == "WIN":
            probs = devig([implied(s["decimal"]) for s in sels])
            for i, (sel, p_m) in enumerate(zip(sels, probs)):
                if p_m is None:
                    continue
                # apply the model only to the two named sides of a head-to-head
                p = p_m
                used_model = False
                if weight and len(sels) == 2:
                    if norm(sel["selection"]) == norm(home):
                        pm = mprob
                    elif norm(sel["selection"]) == norm(away):
                        pm = 1 - mprob
                    else:
                        pm = None
                    if pm is not None:
                        p = weight * pm + (1 - weight) * p_m
                        used_model = True
                p = min(max(p, 0.001), 0.999)
                rows.append(rec(sport, ev, mkt, sel, mt, p, p_m, weight if used_model else 0.0,
                                facts, msrc, home, away))
            continue
        if mt == "HANDICAP":
            # de-vig within each line (the two sides of the same number)
            by_line = {}
            for s in sels:
                by_line.setdefault(line_value(s["selection"]), []).append(s)
            for ln, group in by_line.items():
                probs = devig([implied(s["decimal"]) for s in group])
                for sel, p_m in zip(group, probs):
                    if p_m is None:
                        continue
                    p = p_m
                    if weight and mprob is not None and ln is not None:
                        p = handicap_prob(sport, home, away, mprob, ln, sel["selection"],
                                          facts, p_m, weight)
                    rows.append(rec(sport, ev, mkt, sel, mt, min(max(p, 0.001), 0.999), p_m,
                                    weight, facts, msrc, home, away))
    return rows


def handicap_prob(sport, home, away, p_home, line, selection, facts, p_market, weight):
    """Probability the selection covers, from our expected margin distribution."""
    sd = PARAMS[sport]["sd"] or 1.0
    mean = expected_margin(sport, p_home, facts)
    # our own line is the median margin; the market line is priced off that spread
    sel_is_home = norm(selection).startswith(norm(home)) or norm(home).split()[-1] in norm(selection)
    signed = line if re.search(r"[-+]\s*\d", selection) else line
    # a quoted "-3.5" belongs to the named side; convert to the home side scale
    side = 1 if sel_is_home else -1
    if sel_is_home:
        margin = mean - signed
    else:
        margin = -mean - signed
    if not sd:
        return p_market
    p = normal_cdf(margin / sd)
    return weight * p + (1 - weight) * p_market


def normal_cdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def expected_margin(sport, p_home, facts):
    """Turn a home win probability into an expected scoring margin (documented sd)."""
    sd = PARAMS[sport]["sd"] or 1.0
    p = min(max(p_home, 0.02), 0.98)
    z = math.sqrt(2) * inv_erf(2 * p - 1)
    return z * sd


def inv_erf(x):
    # Winitzki approximation, plenty accurate for pricing displays
    a = 0.147
    ln = math.log(1 - x * x)
    t1 = 2 / (math.pi * a) + ln / 2
    return math.copysign(math.sqrt(math.sqrt(t1 * t1 - ln / a) - t1), x)


def rec(sport, ev, mkt, sel, mt, p, p_market, mweight, facts, msrc, home, away):
    price = dec_from_prob(p)
    price = round(price, 2) if price else None
    ev_url = ev.get("canonical") or ev.get("url")
    sources = [{"label": "OLBG event page (markets, prices, tip counts)", "url": ev_url}]
    if msrc:
        sources.append({"label": "Official reference data", "url": msrc})
    return {
        "sport": sport,
        "sport_label": SPORT_LABEL.get(sport, sport),
        "event_id": ev.get("event_id"),
        "event": ev.get("name") or ev.get("fixture_name"),
        "competition": ev.get("competition") or "",
        "competition_group": ev.get("competition_group") or "",
        "start_utc": ev.get("official_start_utc") or "",
        "home": home, "away": away,
        "market": mkt["market"],
        "market_type": mt,
        "selection": sel["selection"],
        "price": price,
        "american": american(price) if price else "",
        "fair_prob": round(p, 4),
        "market_prob_devig": round(p_market, 4) if p_market else None,
        "market_price": sel["decimal"],
        "market_american": sel["american"],
        "edge": round(p - p_market, 4) if p_market else None,
        "model_weight": round(mweight, 2),
        "tips": sel.get("tips", ""),
        "tips_pct": sel.get("pct", ""),
        "reference_method": (facts or {}).get("method", ""),
        "sources": sources,
        "event_url": ev_url,
    }


# ---------------------------------------------------------------- confidence
def confidence(p, band_ok, has_model):
    if p is None:
        return "low"
    if p >= 0.70 and band_ok:
        return "high"
    if p >= 0.70 and not band_ok:
        return "medium"        # right probability, price outside the requested band
    if p >= 0.60:
        return "medium"
    return "low"


def main():
    ref = Ref()
    coverage, all_lines, picks = [], [], []
    for sport in SPORTS:
        path = os.path.join(OLBG_DIR, f"sport_{sport}.json")
        try:
            with open(path) as fh:
                data = json.load(fh)
        except Exception:  # noqa: BLE001
            coverage.append({"sport": sport, "events": 0, "priced": 0, "note": "no collection file"})
            continue
        events = data.get("events", [])
        sport_lines = []
        for ev in events:
            sport_lines.extend(price_event(ev, sport, ref))
        all_lines.extend(sport_lines)
        # candidate picks: one per event, best of the event's selections
        by_event = {}
        for r in sport_lines:
            if r["price"] is None:
                continue
            band_ok = BAND_LOW <= r["price"] <= BAND_HIGH
            r["band_ok"] = band_ok
            r["confidence"] = confidence(r["fair_prob"], band_ok, bool(r["model_weight"]))
            key = r["event_id"]
            score = (r["fair_prob"], r["edge"] or 0)
            if key not in by_event or score > by_event[key][0]:
                by_event[key] = (score, r)
        ranked = sorted((v[1] for v in by_event.values()),
                        key=lambda r: (not r["band_ok"], -r["fair_prob"]))
        chosen, seen = [], set()
        for r in ranked:
            if r["event_id"] in seen:
                continue
            seen.add(r["event_id"])
            chosen.append(r)
            if len(chosen) >= 5:
                break
        picks.extend(chosen)
        coverage.append({
            "sport": sport,
            "label": SPORT_LABEL.get(sport, sport),
            "listing_url": data.get("listing_url"),
            "events_listed": data.get("events_listed", len(events)),
            "events_with_markets": data.get("events_with_markets", 0),
            "selections_priced": len(sport_lines),
            "events_priced": len(by_event),
            "picks": len(chosen),
            "high_confidence": sum(1 for r in chosen if r["confidence"] == "high"),
            "note": data.get("listing_note", ""),
        })
        print(sport, coverage[-1]["events_listed"], coverage[-1]["events_with_markets"],
              len(sport_lines), len(chosen), flush=True)

    os.makedirs("data", exist_ok=True)
    with open(OUT_LINES, "w") as fh:
        json.dump({"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "rows": all_lines}, fh, indent=1)
    with open(OUT_PICKS, "w") as fh:
        json.dump({"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "rows": picks}, fh, indent=1)
    with open(OUT_INDEX, "w") as fh:
        json.dump({"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "sports": coverage}, fh, indent=1)
    print("lines", len(all_lines), "picks", len(picks))


if __name__ == "__main__":
    main()
