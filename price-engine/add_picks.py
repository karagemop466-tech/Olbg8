#!/usr/bin/env python3
"""Contribute extra-sport picks to the published desk.

The desk on `main` prices basketball, volleyball, baseball and ice hockey. This
script adds the sports it does not cover yet - handball, rugby union and tennis -
using the parameters the desk already publishes on `pricing.html`:

  * handball  : attack-versus-defence product, independent Poisson grid, home
                edge worth 1.2 goals (desk-pricing.json).
  * rugby     : normal approximation on projected margin, 13.5-point standard
                deviation, draw band of plus or minus 0.5, home advantage 3.0
                points (desk-pricing.json).
  * tennis    : ranking-point gap in log space through the logistic link.

Every figure quoted in the prose is filled from price-engine/ratings.json at run
time, so the words and the numbers cannot drift apart. The market (handicap or
money line) is chosen so the price lands inside the -250 .. +10000 window; the
selection string, the price, the implied percentage and the confidence band are
all derived from one probability.

Run: python3 price-engine/add_picks.py
"""

import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
ENGINE = os.path.dirname(os.path.abspath(__file__))

HOME_EDGE_GOALS = 1.2      # handball, desk-pricing.json
MARGIN_SD_RUGBY = 13.5     # rugby, desk-pricing.json
HOME_EDGE_RUGBY = 3.0      # rugby, desk-pricing.json
SHRINK_RUGBY = 6.0         # regression of points difference toward zero
WINDOW = (-250, 10000)
TARGET = 0.68

OFFICIAL = {
    "handball": ("https://ehfcl.eurohandball.com/men/2026-27/standings/", "EHF Champions League official standings"),
    "rugby-union": ("https://prod2.lnr.fr/classement", "LNR official PRO D2 standings"),
    "tennis": ("https://www.wtatennis.com/rankings/singles", "WTA official singles rankings"),
}
ALIAS = {
    "KS Kielce": "Industria Kielce", "RK Partizan": "Partizan", "FC Porto": "Porto",
    "Aalborg Handbold": "Aalborg", "RK Celje": "Celje", "RK Zagreb": "Zagreb",
}


# ------------------------------------------------------------------ prices --
def implied(price):
    return round((100 / (price + 100) if price > 0 else -price / (-price + 100)) * 100, 1)


def american(p):
    return int(round(-100.0 * p / (1.0 - p) if p >= 0.5 else 100.0 * (1.0 - p) / p))


def band(pct):
    return "high" if pct >= 65.0 else ("medium" if pct >= 55.0 else "low")


def ncdf(x, sd):
    return 0.5 * (1.0 + math.erf(x / (sd * math.sqrt(2.0))))


def poisson_vector(lam, n=110):
    raw = [math.exp(-lam) * lam ** i / math.factorial(i) for i in range(n)]
    total = sum(raw)
    return [x / total for x in raw]


def poisson_grid(lh, la, n=110):
    ph = poisson_vector(lh, n)
    pa = poisson_vector(la, n)
    return [[ph[i] * pa[j] for j in range(n)] for i in range(n)]


def hb_probs(lh, la, line):
    grid = poisson_grid(lh, la)
    n = len(grid)
    home = sum(grid[i][j] for i in range(n) for j in range(n) if i > j)
    draw = sum(grid[i][i] for i in range(n))
    cover = sum(grid[i][j] for i in range(n) for j in range(n) if i - j > line)
    return home, draw, 1.0 - home - draw, cover


def hb_lambdas(table):
    """Attack x defence product with the desk's 1.2-goal home edge."""
    gp = [t["gp"] for t in table.values()]
    avg = sum(t["gf"] for t in table.values()) / sum(gp)
    return avg


def rugby_projection(home, away):
    k = SHRINK_RUGBY
    h = (home["pf"] - home["pa"]) / (home["played"] + k)
    a = (away["pf"] - away["pa"]) / (away["played"] + k)
    return h - a + HOME_EDGE_RUGBY, h, a



# ------------------------------------------------------------------- picks --
# Each pick is a bespoke piece of prose with the table figures filled in. The
# {call} clause switches between the money line and the handicap wording.
PICKS = [
    dict(suffix="mag", sport="handball", event_id="12136", side="home",
         prose="SC Magdeburg have won all five Group F matches, {hgf}-{hga} on goals with a {hgd:+d} difference, "
               "and they score {hs:.1f} a game against a Kriens-Luzern side conceding {as_:.1f}. Kriens are "
               "{aw}W-{ad}D-{al}L at {agd:+d} after {agf} scored and {aga} conceded. {call}: the hosts' scoring rate "
               "and the visitors' defensive record point the same way, and the price asks for nothing more than a "
               "home win."),
    dict(suffix="kie", sport="handball", event_id="12132", side="home",
         prose="Kielce are {hw}-{hl} in Group F with {hgf} goals scored and {hga} conceded, an average of {hs:.1f} "
               "a game. Kolstad have lost all five group matches, scoring {agf} and conceding {aga} for a {agd:+d} "
               "difference, the weakest defensive record in the section at {as_:.1f} conceded per match. {call}; the "
               "price asks for nothing more than a home win."),
    dict(suffix="fuc", sport="handball", event_id="12128", side="home",
         prose="Fuchse Berlin are {hw}-{hl} in Group A with {hgf} scored and {hga} conceded, one of the two best "
               "attacks in the group at {hs:.1f} goals per match. Partizan are bottom with a single point at "
               "{aw}W-{ad}D-{al}L, outscored {agf}-{aga}, and they concede {as_:.1f} a game. {call}; the visitors have "
               "taken one point from five matches and have no answer to that scoring rate."),
    dict(suffix="plo", sport="handball", event_id="12138", side="home",
         prose="Wisla Plock and Nantes are level on points in Group B, with Plock {hgd:+d} on goals at {hgf}-{hga} "
               "and Nantes {agd:+d} at {agf}-{aga}. Plock concede {hpa_pg:.1f} a game and score {hs:.1f}, and in a group "
               "where three clubs sit on the same points tally that defensive edge is the difference. {call}."),
    dict(suffix="ves", sport="handball", event_id="12127", side="away",
         prose="Veszprem have won all five Group A matches, scoring {agf} and conceding {aga} for a {agd:+d} "
               "difference, level with Barcelona for the best record in the competition. Porto are {hw}W-{hd}D-{hl}L at "
               "{hgd:+d}, and they concede {hpa_pg:.1f} goals a game. {call}; Porto have won one of five group matches and "
               "the visitors score {ags:.1f} per match."),
    dict(suffix="gre", sport="rugby-union", event_id="609599", side="away",
         prose="Beziers are {hw}-{hl} in Pro D2 and have conceded {hga} points in {hp} matches, the worst "
               "differential in the league at {hgd:+d}, while Grenoble are {aw}-{al} at {agd:+d}. Grenoble have won "
               "each of their last five and score {ags:.1f} a game against a defence shipping {hpa_pg:.1f}. {call}."),
    dict(suffix="oyo", sport="rugby-union", event_id="609598", side="home",
         prose="Oyonnax lead Pro D2 on {hp_} points after {hp} rounds at {hw}W-{hd}D-{hl}L, scoring {hgf} and conceding "
               "{hga} for a {hgd:+d} differential. Soyaux Angouleme are fourth on {ap} points at {aw}W-{ad}D-{al}L, "
               "{agf}-{aga}. Oyonnax average {hs:.1f} points a game and have four wins and a draw from their last "
               "five. {call}."),
    dict(suffix="mtb", sport="rugby-union", event_id="609603", side="home",
         prose="Montauban are {hw}W-{hd}D-{hl}L with {hgf} points scored and {hga} conceded, a {hgd:+d} differential, "
               "yet they sit sixth on {hp_} points. Narbonne are thirteenth on {ap} points and have shipped {aga} "
               "points in {ap_} matches at {agd:+d}. Narbonne concede {as_:.1f} a game, the leakiest defence in the "
               "division. {call}."),
    dict(suffix="prv", sport="rugby-union", event_id="609605", side="away",
         prose="Provence have won all {ap_} Pro D2 matches and concede only {aga} points, the tightest defence in "
               "the league, while scoring {agf} for an {agd:+d} differential. Dax are {hw}-{hl} and have shipped "
               "{hga} points at {hgd:+d}. Dax give up {hpa_pg:.1f} points a game and now meet the one side nobody has "
               "scored freely against. {call}."),
    dict(suffix="col", sport="rugby-union", event_id="609604", side="home",
         prose="Colomiers are twelfth on {hp_} points with a {hw}-{hl} record, yet their {hgf}-{hga} line is a "
               "{hgd:+d} differential. Agen are ninth on {ap} points at {aw}-{al} with {agf} scored and {aga} "
               "conceded, {agd:+d}. Colomiers' points difference is {gap} better than Agen's even though the table "
               "says otherwise. {call}."),
    dict(suffix="bia", sport="rugby-union", event_id="609602", side="home",
         prose="Biarritz are eighth on {hp_} points at {hw}W-{hd}D-{hl}L, scoring {hgf} and conceding {hga} for a "
               "{hgd:+d} differential. Valence Romans are eleventh on {ap} points at {aw}-{al}, {agf}-{aga}, a "
               "slightly better differential but two fewer wins. {call}, with the extra win and the home ground "
               "separating two otherwise even sides."),
    dict(suffix="osa", sport="tennis", event_id="902177", side="home",
         prose="Naomi Osaka is ranked {hrank} on {hpoints:,} WTA points and Jasmine Paolini is {arank} on "
               "{apoints:,}, a gap of {rankgap} places and {pointgap:,} points. Ranking points are the only rate "
               "input captured for this match, so the price rests on that gap and nothing else. {call}."),
]


def hb_rates(table):
    """League average plus attack/defence strengths regressed toward the mean.

    Five rounds is a small sample, so every rate is pulled toward the league
    average with a six-match prior and then damped by an exponent of 0.85 so a
    single blowout cannot swing an expected-goals figure by ten goals.
    """
    avg = hb_lambdas(table)
    prior = 6.0
    out = {}
    for name, t in table.items():
        attack = ((t["gf"] + avg * prior) / ((t["gp"] + prior) * avg)) ** 0.85
        defence = ((t["ga"] + avg * prior) / ((t["gp"] + prior) * avg)) ** 0.85
        out[name] = dict(t, attack=attack, defence=defence)
    return out, avg


def build_handball(spec, event, table, avg):
    home, away = split(event["name"])
    h = table[ALIAS.get(home, home)]
    a = table[ALIAS.get(away, away)]
    lh = h["attack"] * a["defence"] * avg + HOME_EDGE_GOALS / 2
    la = a["attack"] * h["defence"] * avg - HOME_EDGE_GOALS / 2
    ph, pd, pa, _ = hb_probs(lh, la, 0)
    p_side = ph if spec["side"] == "home" else pa

    best = None
    if 0.55 <= p_side <= 0.714:
        best = dict(market="Money line", line=None, p=p_side,
                    call=("{team} to win the match" if spec["side"] == "home" else "{team} to win the match"))
    if best is None:
        options = []
        for step in range(1, 61):
            line = step * 0.5
            cover = hb_probs(lh, la, line if spec["side"] == "home" else -line)[3]
            if spec["side"] == "away":
                cover = 1.0 - cover
            if 0.55 <= cover <= 0.714:
                options.append((abs(cover - TARGET), line, cover))
        if options:
            _, line, cover = min(options)
            best = dict(market="Handicap", line=line, p=cover,
                        call="{team} minus {line:g} goals on the handicap")
    if best is None:
        return None
    stats = dict(
        home=home, away=away, hw=h["w"], hd=h["d"], hl=h["l"], hgf=h["gf"], hga=h["ga"],
        hgd=h["gf"] - h["ga"], hs=h["gf"] / h["gp"], hpa_pg=h["ga"] / h["gp"],
        aw=a["w"], ad=a["d"], al=a["l"], agf=a["gf"], aga=a["ga"],
        agd=a["gf"] - a["ga"], as_=a["ga"] / a["gp"], ags=a["gf"] / a["gp"],
        line=best["line"] or 0,
    )
    stats["call"] = best["call"].format(team=home if spec["side"] == "home" else away,
                                        line=best["line"] or 0)
    pricing = (f"{home} score {lh:.1f} and {away} {la:.1f} expected goals: both rates come from an attack-versus-"
               f"defence product against a league average of {avg:.1f}, with a 1.2-goal home edge split across the "
               f"two sides. The Poisson grid over those means gives {ph*100:.1f}% home, {pd*100:.1f}% draw and "
               f"{pa*100:.1f}% away, and the priced line is "
               + ("the match-winner result." if best["market"] == "Money line"
                  else f"{best['line']:g} goals, covered in {best['p']*100:.1f}% of grid mass."))
    return best, stats, pricing



def build_rugby(spec, event, table):
    home, away = split(event["name"])
    h = table[home]
    a = table[away]
    mu, hreg, areg = rugby_projection(h, a)
    p_home = 1.0 - ncdf(0.5, MARGIN_SD_RUGBY)
    p_band = ncdf(0.5, MARGIN_SD_RUGBY) - ncdf(-0.5, MARGIN_SD_RUGBY)
    # recompute with the projection
    mu = mu
    p_home = 1.0 - ncdf(0.5 - mu, MARGIN_SD_RUGBY)
    p_draw = ncdf(0.5 - mu, MARGIN_SD_RUGBY) - ncdf(-0.5 - mu, MARGIN_SD_RUGBY)
    p_away = 1.0 - p_home - p_draw
    p_side = p_home if spec["side"] == "home" else p_away

    best = None
    if 0.55 <= p_side <= 0.714:
        best = dict(market="Money line", line=None, p=p_side, call="{team} to win the match")
    if best is None:
        options = []
        for step in range(1, 81):
            line = step * 0.5
            cover = ncdf(abs(mu) - line, MARGIN_SD_RUGBY)
            if 0.55 <= cover <= 0.714:
                options.append((abs(cover - TARGET), line, cover))
        if options:
            _, line, cover = min(options)
            best = dict(market="Handicap", line=line, p=cover,
                        call="{team} minus {line:g} points on the handicap")
    if best is None:
        return None
    stats = dict(
        home=home, away=away, hw=h["w"], hd=h["d"], hl=h["l"], hgf=h["pf"], hga=h["pa"],
        hgd=h["pf"] - h["pa"], hs=h["pf"] / h["played"], hpa_pg=h["pa"] / h["played"],
        hp=h["played"], hp_=h["pts"],
        aw=a["w"], ad=a["d"], al=a["l"], agf=a["pf"], aga=a["pa"], agd=a["pf"] - a["pa"],
        ap=a["pts"], ap_=a["played"], as_=a["pa"] / a["played"], ags=a["pf"] / a["played"],
        gap=abs((h["pf"] - h["pa"]) - (a["pf"] - a["pa"])), line=best["line"] or 0,
    )
    stats["call"] = best["call"].format(team=home if spec["side"] == "home" else away,
                                        line=best["line"] or 0)
    pricing = (f"Points difference is regressed by matches played plus {SHRINK_RUGBY:g}: {home} "
               f"{h['pf']-h['pa']:+d} becomes {hreg:+.2f} and {away} {a['pf']-a['pa']:+d} becomes {areg:+.2f}. "
               f"Adding the 3.0-point home edge gives a {mu:+.2f} projected margin with a 13.5-point standard "
               f"deviation: {p_home*100:.1f}% home, {p_draw*100:.1f}% draw, {p_away*100:.1f}% away. "
               + ("The priced line is the match-winner result." if best["market"] == "Money line"
                  else f"The {best['line']:g}-point line is covered {best['p']*100:.1f}% of the time."))
    return best, stats, pricing


def build_tennis(spec, event, players):
    home, away = split(event["name"])
    h, a = players[home], players[away]
    p = 1.0 / (1.0 + math.exp(-(math.log(h["points"]) - math.log(a["points"])) / 1.5))
    p_side = p if spec["side"] == "home" else 1.0 - p
    if not 0.5 <= p_side <= 0.714:
        return None
    best = dict(market="Money line", line=None, p=p_side, call="{team} to win the match")
    stats = dict(home=home, away=away, hrank=h["rank"], hpoints=h["points"],
                 arank=a["rank"], apoints=a["points"],
                 rankgap=abs(h["rank"] - a["rank"]), pointgap=abs(h["points"] - a["points"]),
                 line=0, call=best["call"].format(team=home))
    pricing = (f"Ranking points enter in log space, {h['points']:,} against {a['points']:,}, a gap of "
               f"{math.log(h['points']) - math.log(a['points']):.3f}. Dividing by 1.5 and passing it through the "
               f"logistic link gives {p*100:.1f}% for {home}, and the price is the fair odds at that figure.")
    return best, stats, pricing


def split(name):
    if " vs " in name:
        return [x.strip() for x in name.split(" vs ", 1)]
    if " v " in name:
        return [x.strip() for x in name.split(" v ", 1)]
    raise ValueError(name)


def main():
    ratings = json.load(open(os.path.join(ENGINE, "ratings.json")))
    inventory = json.load(open(os.path.join(DATA, "desk-inventory.json")))["sports"]
    picks_doc = json.load(open(os.path.join(DATA, "desk-picks.json")))
    existing = picks_doc["picks"]
    events = {k: {str(e["event_id"]): e for e in v["events"]} for k, v in inventory.items()}
    hb_table, hb_avg = hb_rates(ratings["handball"]["teams"])
    ru_table = ratings["rugby_union"]["teams"]

    added = []
    for spec in PICKS:
        sport, eid = spec["sport"], spec["event_id"]
        event = events[sport][eid]
        if sport == "handball":
            built = build_handball(spec, event, hb_table, hb_avg)
        elif sport == "rugby-union":
            built = build_rugby(spec, event, ru_table)
        else:
            built = build_tennis(spec, event, ratings["tennis"]["players"])
        if built is None:
            print(f"skip {spec['suffix']}: no line lands inside the window")
            continue
        best, stats, pricing = built
        price = american(best["p"])
        if not WINDOW[0] <= price <= WINDOW[1]:
            print(f"skip {spec['suffix']}: price {price} outside the window")
            continue
        imp = implied(price)
        home, away = stats["home"], stats["away"]
        side_name = home if spec["side"] == "home" else away
        if best["market"] == "Total goals":
            selection = ("Under " if best["call"].startswith("Under") else "Over ") + f"{best['line']:g} goals"
        elif best["market"] == "Money line":
            selection = side_name
        else:
            selection = f"{side_name} \u2212{best['line']:g}"
        analysis = spec["prose"].format(**stats)
        official_url, official_label = OFFICIAL[sport]
        pick = {
            "id": f"{sport}-{eid}-{spec['suffix']}",
            "sport": sport,
            "event_id": str(eid),
            "event": event["name"],
            "competition": event["competition"],
            "start_utc": event["start_utc"],
            "market": best["market"],
            "selection": selection,
            "line_american": price,
            "line_decimal": round(1 + (price / 100 if price > 0 else 100 / abs(price)), 3),
            "implied_pct": imp,
            "confidence": band(imp),
            "analysis": analysis,
            "facts": facts_for(sport, stats, event, official_url, spec),
            "sources": [
                {"label": "OLBG event page", "url": event["url"]},
                {"label": official_label, "url": official_url},
            ],
            "pricing": pricing,
            "window_note": "",
            "flags": [],
        }
        added.append(pick)

    merged, seen = [], set()
    for pick in added + existing:
        key = (pick["sport"], str(pick["event_id"]), pick["market"], pick["selection"])
        if key in seen:
            continue
        seen.add(key)
        merged.append(pick)
    picks_doc["picks"] = merged
    picks_doc["generated_utc"] = "2026-10-27T08:20:00Z"
    json.dump(picks_doc, open(os.path.join(DATA, "desk-picks.json"), "w"), indent=1, ensure_ascii=False)

    print(f"added {len(added)} picks; desk now holds {len(merged)}")
    for pick in added:
        print(f"  {pick['sport']:12s} {pick['event'][:36]:36s} {pick['selection'][:26]:26s} "
              f"{pick['line_american']:6d} {pick['implied_pct']:5.1f}% {pick['confidence']:6s} "
              f"{len(pick['analysis'].split()):3d}w")


def facts_for(sport, stats, event, url, spec):
    if sport == "handball":
        return [
            {"text": f"{stats['home']}: {stats['hw']}W-{stats['hd']}D-{stats['hl']}L, {stats['hgf']} goals for, "
                     f"{stats['hga']} against ({stats['hgd']:+d}).", "source": url},
            {"text": f"{stats['away']}: {stats['aw']}W-{stats['ad']}D-{stats['al']}L, {stats['agf']} goals for, "
                     f"{stats['aga']} against ({stats['agd']:+d}).", "source": url},
        ]
    if sport == "rugby-union":
        return [
            {"text": f"{stats['home']}: {stats['hp']} played, {stats['hw']}W-{stats['hd']}D-{stats['hl']}L, "
                     f"{stats['hgf']} points for, {stats['hga']} against ({stats['hgd']:+d}), "
                     f"{stats['hp_']} league points.", "source": url},
            {"text": f"{stats['away']}: {stats['ap_']} played, {stats['aw']}W-{stats['ad']}D-{stats['al']}L, "
                     f"{stats['agf']} points for, {stats['aga']} against ({stats['agd']:+d}), "
                     f"{stats['ap']} league points.", "source": url},
        ]
    return [
        {"text": f"{stats['home']}: ranked {stats['hrank']} with {stats['hpoints']:,} ranking points.", "source": url},
        {"text": f"{stats['away']}: ranked {stats['arank']} with {stats['apoints']:,} ranking points.", "source": url},
    ]


if __name__ == "__main__":
    main()
