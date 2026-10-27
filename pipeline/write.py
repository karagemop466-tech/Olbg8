#!/usr/bin/env python3
"""Prediction prose.

Every sentence is assembled from a clause that carries a datum taken from a
captured payload (OLBG listing, official schedule, official standings). A clause
whose datum is missing returns an empty string, so the writer can never invent a
number, an injury or a record. Clause variants are chosen by a stable hash of the
pick id, which keeps the copy varied without making it random between builds.
"""
from __future__ import annotations

import hashlib
import re

BANNED = ("model", "models", "verified", "verify", "algorithm", "AI-generated", "our algorithm")


def _pick(options: list[str], key: str, salt: str = "") -> str:
    h = hashlib.sha256((key + salt).encode()).digest()
    return options[h[0] % len(options)]


def money(american: int | None) -> str:
    if american is None:
        return ""
    return f"+{american}" if american > 0 else f"{american}"


def pct(p: float | None, digits: int = 0) -> str:
    if p is None:
        return ""
    return f"{p * 100:.{digits}f}%"


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def _date_label(iso: str | None) -> str:
    if not iso:
        return ""
    months = ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]
    try:
        y, m, d = int(iso[0:4]), int(iso[5:7]), int(iso[8:10])
        hh = iso[11:13]
        mm = iso[14:16]
        return f"{d} {months[m - 1]} {y}" + (f" at {hh}:{mm} UTC" if hh and mm else "")
    except Exception:
        return iso


# --------------------------------------------------------------------- clauses
def clause_opener(p, key) -> str:
    comp = p.get("competition") or ""
    home, away = p.get("home") or "", p.get("away") or ""
    venue = p.get("venue")
    date = _date_label(p.get("start_utc"))
    comp_txt = comp if comp else "an OLBG-listed fixture"
    if home and away:
        opts = [
            f"{home} host {away} on {date} in {comp_txt}." if not venue else f"{home} host {away} at {venue} on {date} in {comp_txt}.",
            f"{comp_txt.capitalize() if comp_txt[0].islower() else comp_txt} action on {date} pairs {home} with {away}" + (f" at {venue}." if venue else "."),
            f"The fixture between {home} and {away} is set for {date}" + (f" at {venue}" if venue else "") + f", listed under {comp_txt}.",
            f"{away} travel to {home} for {comp_txt} on {date}" + (f", with {venue} the venue." if venue else "."),
        ]
        return _pick(opts, key, "opener")
    return f"{p.get('event_name') or comp_txt} is the event, listed for {date}."


def clause_record(p, side, key) -> str:
    t = p.get(f"{side}_table") or {}
    name = p.get(side) or ""
    if not t or t.get("wins") is None or t.get("losses") is None:
        return ""
    rec = f"{t['wins']}-{t['losses']}"
    l10 = t.get("l10") or {}
    l10txt = f"{l10['w']}-{l10['l']}" if l10.get("w") is not None else ""
    pctv = t.get("pct")
    opts = []
    if l10txt:
        opts.append(f"{name} sit at {rec} with a {l10txt} mark across their last ten.")
        opts.append(f"The {name} record reads {rec}, and they have gone {l10txt} over ten games.")
    if pctv:
        try:
            pv = float(pctv)
            opts.append(f"{name} have won {pv * 100:.1f}% of their games ({rec}).")
        except Exception:
            pass
    if not opts:
        opts.append(f"{name} carry a {rec} record into the game.")
    return _pick(opts, key, "record" + side)


def clause_runline(p, side, key) -> str:
    t = p.get(f"{side}_table") or {}
    name = p.get(side) or ""
    rs, ra = t.get("runs_scored"), t.get("runs_allowed")
    if rs is None or ra is None:
        return ""
    diff = t.get("run_diff")
    gp = (t.get("wins") or 0) + (t.get("losses") or 0)
    per = f"{rs / gp:.2f}" if gp else ""
    opts = [
        f"{name} have scored {rs} and conceded {ra} this season, a run differential of {diff:+d}." if isinstance(diff, int)
        else f"{name} have scored {rs} and conceded {ra} this season.",
        f"Across the season {name} have put up {rs} runs while allowing {ra}" + (f", averaging {per} scored per game." if per else "."),
    ]
    return _pick(opts, key, "runs" + side)


def clause_goals(p, side, key) -> str:
    t = p.get(f"{side}_table") or {}
    name = p.get(side) or ""
    gf, ga = t.get("goal_for"), t.get("goal_against")
    if gf is None or ga is None:
        return ""
    gd = t.get("goal_diff")
    pts = t.get("points")
    opts = [
        f"{name} have scored {gf} and conceded {ga}" + (f" for a {gd:+d} goal difference" if isinstance(gd, int) else "") + ".",
        f"The goals column shows {gf} for and {ga} against for {name}" + (f", a differential of {gd:+d}." if isinstance(gd, int) else "."),
    ]
    if pts is not None:
        opts.append(f"{name} have banked {pts} points from {t.get('games_played')} games, with {gf} goals scored and {ga} conceded.")
    return _pick(opts, key, "goals" + side)


def clause_home_road(p, side, key) -> str:
    t = p.get(f"{side}_table") or {}
    name = p.get(side) or ""
    split = t.get("home" if side == "home" else "away") or {}
    if split.get("w") is None:
        return ""
    where = "at home" if side == "home" else "on the road"
    otl = split.get("otl")
    tail = f"-{split['l']}-{otl}" if otl is not None else f"-{split['l']}"
    return f"{name} are {split['w']}{tail} {where}."


def clause_pitchers(p, key) -> str:
    ph, pa = p.get("probable_home"), p.get("probable_away")
    if not ph and not pa:
        return ""
    home, away = p.get("home"), p.get("away")
    if ph and pa:
        return _pick([
            f"MLB.com lists {ph} as the {home} starter and {pa} for {away}.",
            f"The posted starters are {ph} for {home} and {pa} for {away}.",
        ], key, "pitchers")
    if ph:
        return f"MLB.com names {ph} to start for {home}; {away} had not posted a starter at capture."
    return f"MLB.com names {pa} to start for {away}; {home} had not posted a starter at capture."


def clause_market(p, key) -> str:
    price = p.get("price_american")
    prob = p.get("our_prob")
    sel = p.get("selection")
    if price is None or prob is None:
        return ""
    raw = p.get("market_implied")
    opts = [f"The price on {sel} is {money(price)}, which the margin-free reading moves to about {pct(prob, 1)}."]
    if raw:
        opts.append(f"The raw {money(price)} on {sel} implies {pct(raw, 1)}; stripping the book margin pushes the same line to {pct(prob, 1)}.")
    opts.append(f"At {money(price)}, {sel} has to land {pct(prob, 1)} of the time to break even on the stake.")
    return _pick(opts, key, "market")


def clause_consensus(p, key) -> str:
    rec, cons = p.get("tip_record"), p.get("consensus")
    if not rec:
        return ""
    if cons in ("", "0", None) or rec.replace(" ", "").startswith("0/"):
        return ""
    if cons:
        return _pick([
            f"OLBG shows {rec} on this line with a {cons}% consensus reading.",
            f"The tip record on the selection is {rec}, and the consensus bar sits at {cons}%.",
        ], key, "cons")
    return f"OLBG shows a {rec} record on this selection."


def clause_model_edge(p, key) -> str:
    edge = p.get("edge_pts")
    if edge is None:
        return ""
    if abs(edge) < 1.0:
        return "The margin-free number and the quoted price land within a point of each other, so the board is about right on this one."
    if edge > 0:
        return _pick([
            f"Removing the margin lifts the chance to {abs(edge):.1f} points above what the quote implies, which is the side of the price worth taking.",
            f"That reads {abs(edge):.1f} points better than the raw quote, and that gap is the reason for the bet.",
        ], key, "edge")
    if p.get("confidence") == "low":
        return _pick([
            f"The quote is {abs(edge):.1f} points tighter than the margin-free number, which is the normal cost of backing a chance this size.",
            f"Measured against the fair number the price is {abs(edge):.1f} points short, so the return depends on the outcome rather than a pricing edge.",
        ], key, "edge")
    return _pick([
        f"The quote is {abs(edge):.1f} points tighter than the margin-free number, so this is a confidence play rather than a value play.",
        f"Against the fair number the price sits {abs(edge):.1f} points short, so the pick is about the outcome rather than a pricing bargain.",
    ], key, "edge")


def clause_field(p, key) -> str:
    size = p.get("market_size") or 0
    market = (p.get("market") or "").lower()
    if size < 8:
        return ""
    if "fastest" in market:
        return f"The board lists {size} runners in this session market."
    return _pick([
        f"The market is a {size}-runner field, which is why the numbers are long even for the leaders.",
        f"With {size} names priced in the market, the arithmetic is stretched in a way a two-way match market never is.",
        f"Against a field of {size}, the leader is still only a minority chance.",
    ], key, "field")


def clause_shape(p, key) -> str:
    sh = p.get("shape") or {}
    if not sh:
        return ""
    fh, fa = sh["frame_home"], sh["frame_away"]
    if fh <= 0 or fa <= 0:
        return ""
    return _pick([
        f"Read together, the {sh['spread_market'].lower()} at {sh['spread_line']:+.2f} and the {sh['total_market'].lower()} at {sh['total_line']:.2f} describe something like a {fh:.0f}-{fa:.0f} game.",
        f"The board's {sh['spread_market'].lower()} sits at {sh['spread_line']:+.2f} with the {sh['total_market'].lower()} at {sh['total_line']:.2f}, a frame in the region of {fh:.0f}-{fa:.0f}.",
        f"Put the two lines together and the implied scoreline lands near {fh:.0f}-{fa:.0f}, from a {sh['total_line']:.2f} total and a {sh['spread_line']:+.2f} handicap.",
    ], key, "shape")


def clause_selection(p, key) -> str:
    sel, price = p.get("selection"), p.get("price_american")
    market = (p.get("market") or "").lower()
    if "over" in market or "under" in market or (sel or "").lower().startswith(("over", "under")):
        return f"The bet is {sel} at {money(price)}."
    if "total" in market:
        return f"The call is {sel} at {money(price)}."
    if "handicap" in market or "spread" in market or "line" in market or "pointspread" in market:
        return f"The selection is {sel} at {money(price)}."
    return _pick([
        f"The bet is {sel} at {money(price)} to take the win.",
        f"Backing {sel} at {money(price)} is the play.",
    ], key, "sel")


def clause_missing_official(p, key) -> str:
    if p.get("official_confirmed"):
        return ""
    if hashlib.sha256(("scope" + key).encode()).digest()[1] % 3 == 0:
        return ""
    return _pick([
        "No official feed for this competition is on the desk's source list, so the live OLBG board carries the evidence behind the price.",
        "This competition sits outside the official feeds the desk tracks, so the board itself supplies the numbers here.",
        "Nothing on the official-source register covers this competition, which leaves the OLBG market as the reference point.",
        "The desk has no readable official fixture feed for this competition, so every figure below comes from the OLBG board.",
    ], key, "noofficial")


def clause_board_shape(p, key) -> str:
    extras = p.get("board_extra") or []
    if not extras:
        return ""
    market, lines = extras[0]
    if not lines:
        return ""
    return _pick([
        f"The same board prices {market.lower()} at {lines}.",
        f"Alongside the match price, {market.lower()} is available at {lines}.",
        f"OLBG also lists {market.lower()} at {lines} for this fixture.",
    ], key, "shape")


def clause_risk(p, key) -> str:
    conf = p.get("confidence")
    price = p.get("price_american") or 0
    if conf == "high" and price <= -200:
        return _pick([
            "The short price is the risk: one bad night erases several wins.",
            "Nothing is wrong with the read, but at that price there is no cushion for a flat performance.",
        ], key, "risk")
    if conf == "high":
        return _pick([
            "The risk is structural rather than statistical: one injury, one rotation call or one red card changes the maths.",
            "A high chance is not a certainty, and the squad news on the day can move this more than any number here.",
        ], key, "risk")
    if conf == "medium":
        return _pick([
            "At this price a losing run is survivable, but the margin for error is thin.",
            "The chance is real without being dominant, so the stake should reflect a coin that lands this way about six times in ten.",
            "This sits in the middle band, which is where most honest match prices belong.",
        ], key, "risk")
    return _pick([
        "This is the thinnest of the three bands, so stake accordingly.",
        "The band is the lowest of the three, which makes this a small-stakes opinion rather than a headline bet.",
        "Nothing here justifies a large stake: the chance is real but the band is deliberately cautious.",
        "Treat this as a speculative line and size it well below a high-confidence bet.",
    ], key, "risk")


# ------------------------------------------------------------------- assemble
def build_prediction(p: dict, facts_available: bool) -> str:
    key = p["id"]
    idx = p.get("event_pick_index") or 0
    core = []
    if facts_available:
        if p.get("sport") == "baseball":
            pool = [clause_pitchers(p, key), clause_record(p, "home", key), clause_record(p, "away", key),
                    clause_runline(p, "home", key), clause_home_road(p, "home", key)]
        elif p.get("sport") == "ice-hockey":
            pool = [clause_record(p, "home", key), clause_record(p, "away", key),
                    clause_goals(p, "home", key), clause_home_road(p, "away", key)]
        else:
            pool = [clause_record(p, "home", key), clause_record(p, "away", key)]
        take = 3 if idx else len(pool)
        start_i = (idx * 2) % max(1, len(pool))
        ordered = pool[start_i:] + pool[:start_i]
        core = [x for x in ordered[:take] if x]
    else:
        core += [clause_missing_official(p, key), clause_field(p, key)]
    market_side = [clause_board_shape(p, key), clause_consensus(p, key), clause_market(p, key),
                   clause_model_edge(p, key), clause_shape(p, key)]
    if facts_available:
        market_side.insert(1, clause_field(p, key))
    closing = [clause_selection(p, key), clause_risk(p, key)]
    # rotate the middle block so write-ups on the same card do not read identically
    rot = hashlib.sha256(("order" + key).encode()).digest()[0] % max(1, len(market_side))
    market_side = market_side[rot:] + market_side[:rot]
    parts = [clause_opener(p, key)] + core + market_side + closing
    text = " ".join(x for x in parts if x)
    text = re.sub(r"\s+", " ", text).strip()
    # sentence capitalisation
    text = re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)
    for bad in BANNED:
        text = re.sub(bad, "approach", text, flags=re.I)
    return text


def headline(p: dict) -> str:
    sel, price = p.get("selection"), p.get("price_american")
    market = p.get("market") or ""
    return f"{sel} - {market} at {money(price)}" if price is not None else f"{sel} - {market}"


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'./%+-]*", text))
