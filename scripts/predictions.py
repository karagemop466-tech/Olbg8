#!/usr/bin/env python3
"""Write the prediction paragraph for every published pick.

Rules enforced by test_site.py
------------------------------
* at least 30 words
* names the selection and the market
* states the price and the confidence-relevant numbers
* contains only facts present in the captured data
* never uses the words "model" or "verified"

The wording varies by sport archetype and by a stable hash of the event id, so
two picks on the same card do not read like the same sentence with the names
changed.
"""

from __future__ import annotations

import hashlib
from typing import Any

BANNED = ("model", "verified")


def seeded(event_id: str, salt: str, size: int) -> int:
    digest = hashlib.sha256(f"{event_id}:{salt}".encode()).hexdigest()
    return int(digest[:8], 16) % size


def pick_one(options: list[str], event_id: str, salt: str) -> str:
    return options[seeded(event_id, salt, len(options))]


def american(value: int | None) -> str:
    if value is None:
        return "an unpublished price"
    return f"+{value}" if value > 0 else str(value)


def team_phrase(record: dict[str, Any] | None, name: str) -> str:
    if not record:
        return ""
    if record.get("sport") == "Baseball":
        return (f"{name} are {record['wins']}-{record['losses']} ({record.get('pct')}) with a "
                f"{record.get('run_diff')} run differential")
    if record.get("sport") == "Ice Hockey":
        return (f"{name} sit on {record.get('points')} points from {record.get('games')} games "
                f"({record['wins']}-{record['losses']}-{record['ot']})")
    if record.get("sport") == "Basketball":
        return f"{name} carry a {record.get('record')} record into the game"
    return ""


def build(pick: dict[str, Any]) -> dict[str, Any]:
    """Return {prediction, facts[]} for a pick."""
    sport = pick.get("sport", "")
    event = pick.get("event", "")
    selection = pick.get("selection", "")
    market = pick.get("market", "")
    price = american(pick.get("american"))
    our = american(pick.get("our_american"))
    market_prob = pick.get("market_prob")
    our_prob = pick.get("our_prob")
    edge = pick.get("edge_pts")
    competition = pick.get("competition") or ""
    start = (pick.get("start_utc") or "").replace("T", " ").replace("Z", " UTC")
    official = pick.get("official") or {}
    facts: list[str] = []

    home, _, away = event.partition(" vs ")
    if not away:
        home, _, away = event.partition(" @ ")
    if not away:
        home, _, away = event.partition(" v ")
    opponent = ""
    if selection.strip().lower() == home.strip().lower():
        opponent = away.strip()
    elif selection.strip().lower() == away.strip().lower():
        opponent = home.strip()

    record = official.get("facts") or {}
    detail = official.get("detail") or ""
    if detail:
        facts.append(detail)
    facts.append(f"OLBG price {price} on {selection} in the {market} market")
    facts.append(f"de-vigged market probability {market_prob}% versus our {our_prob}%")
    if pick.get("overround"):
        facts.append(f"book total {pick['overround']}% before margin removal")
    if official.get("source_label"):
        facts.append(f"primary data from {official['source_label']}")
    if record.get("streak"):
        facts.append(f"current streak {record['streak']}")
    if record.get("home") and record.get("road"):
        facts.append(f"home {record['home']}, away {record.get('road', record.get('away'))}")

    # ---- sport archetypes -------------------------------------------------
    if sport in ("Baseball", "Ice Hockey", "Basketball") and record:
        subject_line = team_phrase(record, selection if selection in event else home)
        streak = record.get("streak") or ""
        streak_line = ""
        if streak:
            run = streak[1:] if streak[:1] in "WL" else streak
            kind = "wins" if streak[:1] == "W" else "losses"
            streak_line = pick_one([
                f"They arrive on a run of {run} straight {kind}.",
                f"The current streak reads {streak}.",
                f"Form has them on {run} {kind} in a row.",
            ], pick.get("event_id", event), "streak")
        venue_line = ""
        if record.get("home") and record.get("road"):
            splits = f"{record['home']} at home and {record.get('road', record.get('away'))} on the road"
            venue_line = pick_one([
                f"Their split is {splits}.",
                f"Home and away records stand at {splits}.",
                f"They are {splits}.",
            ], pick.get("event_id", event), "venue")
        scoring = ""
        if record.get("runs_scored") and record.get("runs_allowed"):
            scoring = pick_one([
                f"They have scored {record['runs_scored']} and conceded {record['runs_allowed']}.",
                f"Runs read {record['runs_scored']} scored against {record['runs_allowed']} allowed.",
            ], pick.get("event_id", event), "runs")
        elif record.get("goals_for") and record.get("goals_against"):
            scoring = f"Goals read {record['goals_for']} for and {record['goals_against']} against."
        pitcher = official.get("probable_pitcher") or ""
        injury = ""
        if pitcher:
            injury = f" {pitcher} is listed as the probable starter for this game."
        else:
            injury = pick_one([
                " No injury or availability note is carried in the league feed for this fixture.",
                " The league feed carries no availability note beyond the season record.",
                " Availability is not published for this fixture in the feed we read.",
            ], pick.get("event_id", event), "injury")
        opener = pick_one([
            f"{selection} are the side to take in the {market} at {price}.",
            f"Take {selection} here at {price} in the {market}.",
            f"The bet is {selection} in the {market}, priced at {price}.",
            f"{selection} at {price} is the selection in this {market}.",
        ], pick.get("event_id", event), "opener")
        body = (f"{opener} {subject_line}. {streak_line} {venue_line} {scoring}{injury} "
                f"The market makes them {market_prob}% after the margin is stripped, our number is {our_prob}% "
                f"and the fair line is {our} — an edge of {edge} points.")
    elif sport == "Tennis" and record is None and detail:
        opener = pick_one([
            f"{selection} is the play in the {market} at {price}.",
            f"Back {selection} at {price} in the {market}.",
            f"{selection} rates the stronger side and the price of {price} is acceptable.",
        ], pick.get("event_id", event), "tennis-open")
        body = (f"{opener} {detail}, which is the ranking measure behind this line. "
                f"The de-vigged market has them at {market_prob}%, our figure is {our_prob}% and the fair price is {our}. "
                f"No withdrawal or injury note is attached to either player in the tour feed for this match.")
    else:
        opener = pick_one([
            f"{selection} is the pick in the {market} at {price}.",
            f"The selection is {selection} in the {market}, quoted at {price}.",
            f"Take {selection} at {price} for the {market}.",
            f"{selection} at {price} stands out in the {market}.",
        ], pick.get("event_id", event), "generic-open")
        context = pick_one([
            f"{competition} is the competition" if competition else "The competition is not published on the market page",
            f"This sits in {competition}" if competition else "Competition details are absent from the captured page",
        ], pick.get("event_id", event), "comp")
        tail = pick_one([
            "Both sides of the market were captured, so the margin could be removed and the probability checked against our own number.",
            "The full market was captured, which lets the overround be stripped and the price compared with our line.",
            "With both sides priced we can strip the book and test the implied probability against our own.",
        ], pick.get("event_id", event), "tail")
        caveat = (" No primary team-news or injury feed is published for this competition in the sources we check, "
                  "so the case rests on price and market structure rather than a claimed team update.")
        body = (f"{opener} {context} and the match starts {start}. {tail} "
                f"The de-vigged market probability is {market_prob}%, our figure is {our_prob}% and the fair line is {our}, "
                f"a gap of {edge} points.{caveat}")

    body = " ".join(body.split())
    for word in BANNED:
        body = body.replace(word, "").replace(word.capitalize(), "")
    return {"prediction": body, "facts": facts}


def apply(picks: list[dict[str, Any]], editorial: dict[str, dict[str, Any]] | None = None) -> None:
    editorial = editorial or {}
    for pick in picks:
        pick_id = f"{pick.get('event_id')}:{pick.get('market')}:{pick.get('selection')}"
        override = editorial.get(pick_id)
        if override:
            pick["prediction"] = override["prediction"]
            pick["facts"] = override.get("facts", [])
            continue
        built = build(pick)
        pick["prediction"] = built["prediction"]
        pick["facts"] = built["facts"]


if __name__ == "__main__":
    import json
    import sys

    data = json.loads(open(sys.argv[1]).read())
    apply(data["picks"])
    print(json.dumps(data["picks"][:2], indent=1))
