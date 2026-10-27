#!/usr/bin/env python3
"""Originate our own prices for every captured OLBG listing.

Design rules
------------
1. A price is only produced when both competitors have a rating input copied
   from an official source (see data/ratings.json). If either side is missing,
   the price stays blank and the row is flagged, never guessed.
2. Published prices are fair (zero-margin) prices converted from our own
   probability. Every match also carries a handicap line and a total line.
3. Small samples are shrunk toward the league average before they are used:
   weight = games_played / (games_played + K), with K recorded below.
4. Confidence bands: High >= 70%, Medium 62-69.9%, Low < 62%.
5. Publication window: only selections priced between -250 and +10000 are
   headline picks. Stronger favourites are still priced and still labelled, but
   they are marked as outside the window instead of being hidden.

Run: python3 scripts/originate.py
"""

import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

HOME_EDGE = {
    "Basketball": 3.0,
    "Handball": 2.0,
    "Ice Hockey": 0.25,
    "Baseball": 0.12,
    "Rugby Union": 3.5,
    "Tennis": 0.0,
}

MARGIN_SD = {
    "Basketball": 11.0,
    "Handball": 7.6,
    "Ice Hockey": 2.1,
    "Baseball": 3.6,
    "Rugby Union": 12.5,
    "Tennis": 0.0,
}

SHRINK_K = {
    "Basketball": 12.0,
    "Handball": 8.0,
    "Ice Hockey": 10.0,
    "Baseball": 60.0,
    "Rugby Union": 6.0,
}

SCORING_STEP = {
    "Basketball": 0.5,
    "Handball": 1.0,
    "Ice Hockey": 0.5,
    "Baseball": 0.5,
    "Rugby Union": 0.5,
}

HIGH = 0.700
MEDIUM = 0.620
PRICE_FLOOR = -250.0
PRICE_CEILING = 10000.0

DRAW_SPORTS = {"Handball", "Rugby Union"}


def ncdf(x, mu=0.0, sd=1.0):
    return 0.5 * (1.0 + math.erf((x - mu) / (sd * math.sqrt(2.0))))


def american(p):
    if p is None or p <= 0.0 or p >= 1.0:
        return None
    if p >= 0.5:
        return -100.0 * p / (1.0 - p)
    return 100.0 * (1.0 - p) / p


def implied(price):
    if price is None:
        return None
    if price < 0:
        return (-price) / ((-price) + 100.0)
    return 100.0 / (price + 100.0)


def band(p):
    if p is None:
        return None
    if p >= HIGH:
        return "High"
    if p >= MEDIUM:
        return "Medium"
    return "Low"


def round_to_step(value, step):
    return round(value / step) * step


def two_way(p_home):
    return {
        "home": {"probability": round(p_home, 4), "american": round(american(p_home), 1)},
        "away": {"probability": round(1.0 - p_home, 4), "american": round(american(1.0 - p_home), 1)},
    }


def three_way(mu, sd):
    p_home = 1.0 - ncdf(0.5, mu, sd)
    p_away = ncdf(-0.5, mu, sd)
    p_draw = max(0.0, 1.0 - p_home - p_away)
    return {
        "home": {"probability": round(p_home, 4), "american": round(american(p_home), 1)},
        "draw": {"probability": round(p_draw, 4), "american": round(american(p_draw), 1)},
        "away": {"probability": round(p_away, 4), "american": round(american(p_away), 1)},
    }


def _diff_per_game(team, for_key, against_key, games_key):
    games = team.get(games_key) or (team.get("w", 0) + team.get("l", 0)) or 1
    return (team[for_key] - team[against_key]) / games, (team[for_key] + team[against_key]) / games, games


def basketball_margin(t):
    return _diff_per_game(t, "pf", "pa", "gp")


def handball_margin(t):
    return _diff_per_game(t, "gf", "ga", "gp")


def hockey_margin(t):
    games = t["gp"]
    return (t["gf"] - t["ga"]) / games, (t["gf"] + t["ga"]) / games, games


def baseball_margin(t):
    games = t["w"] + t["l"]
    return t["run_diff"] / games, (t["runs_scored"] + t["runs_allowed"]) / games, games


def rugby_margin(t):
    return _diff_per_game(t, "pf", "pa", "played")


TEAM_METRICS = {
    "Basketball": basketball_margin,
    "Handball": handball_margin,
    "Ice Hockey": hockey_margin,
    "Baseball": baseball_margin,
    "Rugby Union": rugby_margin,
}


def price_team_match(sport, home, away):
    fn = TEAM_METRICS[sport]
    h_diff, h_total, h_gp = fn(home["rating"])
    a_diff, a_total, a_gp = fn(away["rating"])
    k = SHRINK_K[sport]
    h_diff *= h_gp / (h_gp + k)
    a_diff *= a_gp / (a_gp + k)
    mu = (h_diff - a_diff) + HOME_EDGE[sport]
    sd = MARGIN_SD[sport]
    total = round_to_step((h_total + a_total) / 2.0, SCORING_STEP[sport])

    ml = three_way(mu, sd) if sport in DRAW_SPORTS else two_way(1.0 - ncdf(0.0, mu, sd))

    line = round_to_step(abs(mu), SCORING_STEP[sport])
    if line < SCORING_STEP[sport]:
        line = SCORING_STEP[sport]
    if mu >= 0:
        fav, dog = home["name"], away["name"]
        p_fav = 1.0 - ncdf(line, mu, sd)
    else:
        fav, dog = away["name"], home["name"]
        p_fav = ncdf(-line, mu, sd)
    handicap = {
        "line": line,
        "favourite": fav,
        "underdog": dog,
        "favourite_probability": round(p_fav, 4),
        "favourite_price": round(american(p_fav), 1),
        "underdog_probability": round(1.0 - p_fav, 4),
        "underdog_price": round(american(1.0 - p_fav), 1),
        "display": f"{fav} -{line} / {dog} +{line}",
    }

    total_market = {
        "line": total,
        "over_probability": 0.5,
        "over_price": -100.0,
        "under_price": -100.0,
        "note": f"Originated total: {total} points",
    }

    return {
        "expected_margin": round(mu, 2),
        "expected_total": total,
        "margin_sd": sd,
        "moneyline": ml,
        "handicap": handicap,
        "total": total_market,
    }


def price_tennis(home, away):
    ph, pa = home["rating"]["points"], away["rating"]["points"]
    diff = math.log(ph) - math.log(pa)
    p_home = 1.0 / (1.0 + math.exp(-diff / 1.5))
    return {
        "expected_margin": None,
        "expected_total": None,
        "margin_sd": None,
        "moneyline": two_way(p_home),
        "handicap": None,
        "total": None,
    }


def price_match(sport, home, away):
    if sport == "Tennis":
        return price_tennis(home, away)
    return price_team_match(sport, home, away)


def split_event(event):
    if "@" in event:
        away, home = [p.strip() for p in event.split("@", 1)]
        return home, away
    if " vs " in event:
        a, b = [p.strip() for p in event.split(" vs ", 1)]
        return a, b
    if " v " in event:
        a, b = [p.strip() for p in event.split(" v ", 1)]
        return a, b
    return None, None


ALIASES = {
    "Basketball": {
        "Panathinaikos": "Panathinaikos",
        "Milano": "Milano",
        "BC Dubai": "BC Dubai",
        "Paris": "Paris",
        "Valencia": "Valencia",
        "Fenerbahce": "Fenerbahce",
        "Bayern Munich": "Bayern Munich",
        "Barcelona": "Barcelona",
        "Baskonia": "Baskonia",
        "Real Madrid": "Real Madrid",
        "Crvena Zvezda": "Crvena Zvezda",
        "Maccabi Tel Aviv": "Maccabi Tel Aviv",
        "Besiktas": "Besiktas",
        "Olympiacos": "Olympiacos",
        "Asvel Lyon Villeurbanne": "Asvel Lyon Villeurbanne",
        "Partizan": "Partizan",
        "Virtus Bologna": "Virtus Bologna",
        "Zalgiris": "Zalgiris",
    },
    "Handball": {
        "SC Magdeburg": "SC Magdeburg",
        "HC Kriens Luzern": "HC Kriens Luzern",
        "HC Vardar": "HC Vardar",
        "MT Melsungen": "MT Melsungen",
        "Wisla Plock": "Wisla Plock",
        "Nantes": "Nantes",
        "KS Kielce": "Industria Kielce",
        "Kolstad": "Kolstad",
        "PSG Handball": "PSG Handball",
        "Aalborg Handbold": "Aalborg",
        "RK Celje": "Celje",
        "RK Zagreb": "Zagreb",
        "Fuchse Berlin": "Fuchse Berlin",
        "RK Partizan": "Partizan",
        "FC Porto": "Porto",
        "Veszprem": "Veszprem",
        "GOG": "GOG",
        "Sporting CP": "Sporting CP",
        "Montpellier": "Montpellier",
        "Dinamo Bucuresti": "Dinamo Bucuresti",
        "IFK Kristianstad": "IFK Kristianstad",
        "Pick Szeged": "Pick Szeged",
        "FC Barcelona": "FC Barcelona",
    },
    "Ice Hockey": {
        "BOS Bruins": "BOS",
        "CAR Hurricanes": "CAR",
        "CLB Blue Jackets": "CBJ",
        "PHI Flyers": "PHI",
    },
    "Baseball": {"MIL Brewers": "MIL", "TB Rays": "TB"},
    "Rugby Union": {
        "Dax": "Dax",
        "Provence": "Provence",
        "Colomiers": "Colomiers",
        "Agen": "Agen",
        "Montauban": "Montauban",
        "Narbonne": "Narbonne",
        "Oyonnax": "Oyonnax",
        "Soyaux Angouleme": "Soyaux Angouleme",
        "Beziers": "Beziers",
        "Grenoble": "Grenoble",
        "Nissa": "Nissa",
        "Aurillac": "Aurillac",
        "Biarritz": "Biarritz",
        "Valence Romans": "Valence Romans",
    },
}

SOURCE_KEY = {
    "Basketball": "euroleague",
    "Handball": "ehfcl",
    "Ice Hockey": "nhl",
    "Baseball": "mlb",
    "Rugby Union": "prod2",
    "Tennis": "wta",
}

RATINGS_KEY = {
    "Basketball": "basketball",
    "Handball": "handball",
    "Ice Hockey": "ice_hockey",
    "Baseball": "baseball",
    "Rugby Union": "rugby_union",
    "Tennis": "tennis",
}


def lookup(sport, name, ratings):
    block = ratings[RATINGS_KEY[sport]]
    table = block.get("teams") or block.get("players") or {}
    canonical = ALIASES.get(sport, {}).get(name, name)
    return table.get(canonical), canonical


def main():
    listings = json.load(open(os.path.join(DATA, "olbg-listings.json")))
    ratings = json.load(open(os.path.join(DATA, "ratings.json")))
    try:
        predictions = json.load(open(os.path.join(DATA, "predictions.json")))["entries"]
    except FileNotFoundError:
        predictions = {}

    # OLBG splits "Gaelic Sports" into Gaelic Football and Hurling. The brief asks
    # for one Gaelic Sports page, so both collapse into that single bucket.
    SPORT_BUCKET = {"Gaelic Football": "Gaelic Sports", "Hurling": "Gaelic Sports"}
    fields = listings["fields"]
    base = listings["base_url"]

    rows = []
    for raw in listings["rows"]:
        item = dict(zip(fields, raw))
        sport = SPORT_BUCKET.get(item["sport"], item["sport"])
        row = {
            "id": f"{sport.lower().replace(' ', '-')}-{item['event_id']}",
            "sport": sport,
            "event": item["event"],
            "event_id": item["event_id"],
            "competition": item["competition"],
            "start_label": item["start_label"],
            "olbg_market": item["market"],
            "olbg_selection": item["selection"],
            "olbg_tips": item["tips"],
            "olbg_pct": item["pct"],
            "olbg_url": base + item["path"],
            "basis": "unrated",
            "markets": None,
            "pick": None,
            "flags": [],
        }

        home_name, away_name = split_event(item["event"])
        if sport not in RATINGS_KEY:
            row["flags"].append("No official rating input for this competition in this session")
        elif home_name is None:
            row["flags"].append("Outright market: needs a field-strength list, none captured this session")
        else:
            row["home"] = home_name
            row["away"] = away_name
            home_rating, home_canon = lookup(sport, home_name, ratings)
            away_rating, away_canon = lookup(sport, away_name, ratings)
            if home_rating is None or away_rating is None:
                missing = [n for n, r in ((home_name, home_rating), (away_name, away_rating)) if r is None]
                row["flags"].append("No rating input for: " + ", ".join(missing))
            else:
                row[home_name] = home_canon
                result = price_match(
                    sport,
                    {"name": home_name, "rating": home_rating},
                    {"name": away_name, "rating": away_rating},
                )
                row["basis"] = "ratings"
                row["markets"] = result
                row["projection"] = {"margin": result["expected_margin"], "total": result["expected_total"]}
                row["rating_inputs"] = {
                    "home": dict(home_rating, name=home_name),
                    "away": dict(away_rating, name=away_name),
                }
                ml = result["moneyline"]
                side, prob = max((("home", ml["home"]["probability"]), ("away", ml["away"]["probability"])),
                                 key=lambda x: x[1])
                selection = home_name if side == "home" else away_name
                price = ml[side]["american"]
                in_window = price is not None and PRICE_FLOOR <= price <= PRICE_CEILING
                row["pick"] = {
                    "market": "Match winner (money line)",
                    "selection": selection,
                    "side": side,
                    "probability": prob,
                    "american": price,
                    "decimal": round(1.0 + (price / 100.0 if price > 0 else 100.0 / -price), 3),
                    "confidence": band(prob),
                    "in_price_window": in_window,
                    "published": False,
                }
                if not in_window:
                    row["flags"].append(
                        "Priced shorter than -250, outside the stated publication window"
                    )
                if result["handicap"] and result["handicap"]["favourite_probability"] >= 0.5:
                    row["pick"]["handicap_view"] = result["handicap"]["display"]

        src_key = SOURCE_KEY.get(row["sport"])
        if src_key and row.get("pick"):
            src = ratings["sources"][src_key]
            row["source_urls"] = {src_key: src["url"]}
            row["source_labels"] = {src_key: src["label"].split(" (")[0]}
        else:
            row["source_urls"] = {}
            row["source_labels"] = {}

        entry = predictions.get(row["id"])
        if entry and row.get("pick"):
            row["pick"]["published"] = True
            row["pick"]["confidence"] = entry["confidence"]
            row["prediction"] = entry

        rows.append(row)

    payload = {
        "schema": "matches-v1",
        "built_utc": "2026-10-27T06:00:00Z",
        "listing_capture_utc": listings["captured_utc"],
        "price_window": {"floor": PRICE_FLOOR, "ceiling": PRICE_CEILING},
        "bands": {"high": HIGH, "medium": MEDIUM},
        "sport_parameters": {
            "home_edge": HOME_EDGE,
            "margin_sd": MARGIN_SD,
            "shrink_k": SHRINK_K,
            "scoring_step": SCORING_STEP,
            "draw_sports": sorted(DRAW_SPORTS),
        },
        "rows": rows,
    }
    json.dump(payload, open(os.path.join(DATA, "matches.json"), "w"), indent=1)

    rated = [r for r in rows if r["basis"] == "ratings"]
    picked = [r for r in rated if r["pick"]]
    print(f"rows={len(rows)} rated={len(rated)} picks={len(picked)}")
    for r in sorted(picked, key=lambda r: -r["pick"]["probability"]):
        p = r["pick"]
        tag = "in " if p["in_price_window"] else "OUT"
        print(f"{r['sport']:12s} {tag} {r['event'][:44]:44s} {p['selection'][:20]:20s} "
              f"{p['probability']:.3f} {p['american']:8.0f} {p['confidence']}")


if __name__ == "__main__":
    main()
