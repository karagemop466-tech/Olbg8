#!/usr/bin/env python3
"""Write the prediction paragraph for every published pick.

Every sentence is generated from captured values only. The two routes are kept
apart on purpose:

* primary route - an independent estimate exists (MLB, NHL, NBA records, ATP
  ranking points). The paragraph quotes the record, the streak or split where we
  hold one, and the gap between our number and the price.
* market route  - no independent estimate. The paragraph says so, quotes the
  community consensus that OLBG publishes and explains the margin allowance
  instead of pretending to know team news we do not have.

Published predictions must not contain the words "model" or "verified"; the
site test enforces that and also enforces the 30-word minimum.
"""

from __future__ import annotations

import hashlib
from typing import Any

BANNED = ("model", "verified")


def _seed(event_id: str, salt: str, size: int) -> int:
    digest = hashlib.sha256(f"{event_id}:{salt}".encode()).hexdigest()
    return int(digest[:8], 16) % max(size, 1)


def one(options: list[str], event_id: str, salt: str) -> str:
    return options[_seed(event_id, salt, len(options))]


def money(value: int | None) -> str:
    if value is None:
        return "an unpublished price"
    return f"+{value}" if value > 0 else str(value)


def clock(start: str) -> str:
    if not start:
        return "a kick-off that is not published"
    text = start.replace("T", " ").replace("Z", " UTC")
    return text[:16] + " UTC" if len(text) > 16 else text


def split_name(event: str) -> tuple[str, str]:
    if " @ " in event:
        away, home = event.split(" @ ", 1)
        return home.strip(), away.strip()
    for sep in (" vs ", " v "):
        if sep in event:
            home, away = event.split(sep, 1)
            return home.strip(), away.strip()
    return event.strip(), ""


def streak_sentence(record: dict[str, Any], event_id: str) -> str:
    streak = record.get("streak") or ""
    if not streak or streak[:1] not in "WL":
        return ""
    length, kind = streak[1:], ("win" if streak[0] == "W" else "loss")
    return one([
        f"They are on a run of {length} straight {kind}s.",
        f"The form line reads {length} {kind}s in a row.",
        f"Recent form shows {length} {kind}s back to back.",
        f"That run currently stands at {length} {kind}s.",
    ], event_id, "streak")


def split_sentence(record: dict[str, Any], event_id: str) -> str:
    home, road = record.get("home"), record.get("road") or record.get("away")
    if not home or not road:
        return ""
    return one([
        f"Their record splits to {home} at home and {road} away.",
        f"Home form is {home}, road form {road}.",
        f"They are {home} in front of their own crowd and {road} on the road.",
    ], event_id, "split")


def scoring_sentence(record: dict[str, Any], event_id: str) -> str:
    if record.get("runs_scored") and record.get("runs_allowed"):
        return one([
            f"Runs run {record['runs_scored']} scored to {record['runs_allowed']} conceded.",
            f"The season line is {record['runs_scored']} runs scored and {record['runs_allowed']} allowed.",
            f"They have put up {record['runs_scored']} runs while giving up {record['runs_allowed']}.",
        ], event_id, "runs")
    if record.get("goals_for") and record.get("goals_against"):
        return one([
            f"Goals read {record['goals_for']} for and {record['goals_against']} against.",
            f"The goal line is {record['goals_for']} scored, {record['goals_against']} conceded.",
        ], event_id, "goals")
    return ""


def record_sentence(record: dict[str, Any], name: str, event_id: str) -> str:
    sport = record.get("sport")
    if sport == "Baseball" and record.get("wins") is not None:
        return one([
            f"{name} finished the regular season {record['wins']}-{record['losses']} ({record.get('pct')}) with a {record.get('run_diff')} run differential.",
            f"{name} are {record['wins']}-{record['losses']}, a {record.get('pct')} rate and a {record.get('run_diff')} run differential.",
            f"The season record for {name} is {record['wins']}-{record['losses']} with a {record.get('run_diff')} run differential.",
        ], event_id, "rec-mlb")
    if sport == "Ice Hockey" and record.get("points") is not None:
        return one([
            f"{name} have {record['points']} points from {record['games']} games ({record['wins']}-{record['losses']}-{record['ot']}).",
            f"{name} carry {record['points']} points after {record['games']} games, a {record['wins']}-{record['losses']}-{record['ot']} record.",
            f"The season line for {name} is {record['wins']}-{record['losses']}-{record['ot']}, worth {record['points']} points.",
        ], event_id, "rec-nhl")
    if sport == "Basketball" and record.get("record"):
        return one([
            f"{name} are {record['record']} on the season.",
            f"{name} bring a {record['record']} record into this one.",
            f"The record for {name} reads {record['record']}.",
        ], event_id, "rec-nba")
    return ""


def build(pick: dict[str, Any]) -> dict[str, Any]:
    event_id = str(pick.get("event_id") or pick.get("event") or "")
    sport = pick.get("sport", "")
    event = pick.get("event", "")
    selection = pick.get("selection", "")
    market = pick.get("market", "")
    price = money(pick.get("american"))
    line = money(pick.get("our_american"))
    market_prob = pick.get("market_prob")
    our_prob = pick.get("our_prob")
    fair = pick.get("fair_prob")
    edge = pick.get("edge_pts")
    allowance = pick.get("margin_allowance")
    consensus = pick.get("consensus")
    tips = pick.get("tips")
    tips_total = pick.get("tips_total")
    competition = pick.get("competition") or ""
    start = clock(pick.get("start_utc") or "")
    official = pick.get("official") or {}
    record = official.get("facts") or {}
    fixture = any(sep in event for sep in (" vs ", " @ ", " v "))
    home, away = split_name(event)
    subject = (home if selection.strip().lower() == home.lower()
               else away if selection.strip().lower() == away.lower() else ("" if fixture else ""))
    opponent = (away if subject == home else home if subject == away else "") if fixture else ""
    facts: list[str] = []

    if official.get("detail"):
        facts.append(official["detail"])
    facts.append(f"OLBG price {price} on {selection} in the {market}")
    facts.append(f"margin-adjusted market probability {fair}% against our {our_prob}%")
    if consensus is not None:
        facts.append(f"community consensus {consensus}% ({tips} of {tips_total} OLBG tips)")
    if record.get("streak"):
        facts.append(f"current streak {record['streak']}")
    if record.get("home"):
        facts.append(f"home {record['home']}, away {record.get('road', record.get('away'))}")
    if record.get("probable_pitcher"):
        facts.append(f"probable pitcher {record['probable_pitcher']}")
    if record.get("last_game"):
        last = record["last_game"]
        facts.append(f"last game {last.get('score')} against {last.get('opponent')}")

    if official.get("method") and subject:
        lead = one([
            f"{selection} is the side to back in the {market} at {price}.",
            f"The play here is {selection} in the {market}, priced at {price}.",
            f"Take {selection} at {price} in the {market}.",
            f"{selection} at {price} is the pick from this {market}.",
        ], event_id, "lead-primary")
        body = [lead, record_sentence(record, subject, event_id)]
        detail_line = official.get("detail") or ""
        if detail_line and not record_sentence(record, subject, event_id):
            if "ranking points" in detail_line:
                body.append(f"{detail_line}, which is the tour's published ranking measure for both players.")
            else:
                body.append(f"{detail_line}.")
        if opponent:
            body.append(one([
                f"The opposition is {opponent}.",
                f"{opponent} provide the opposition.",
                f"Standing in the way is {opponent}.",
            ], event_id, "opp"))
        body.extend([streak_sentence(record, event_id), split_sentence(record, event_id), scoring_sentence(record, event_id)])
        if record.get("pitchers"):
            body.append(one([
                f"Pitching plans list {record['pitchers']}.",
                f"The probable starters are {record['pitchers']}.",
            ], event_id, "pitch"))
        last = record.get("last_game") or {}
        if last.get("score"):
            body.append(one([
                f"Their last completed game finished {last['score']} against {last['opponent']}.",
                f"They were last out in a {last['score']} game with {last['opponent']}.",
            ], event_id, "last"))
        body.append(one([
            f"OLBG shows {price}, which after a {allowance}% margin allowance implies {fair}%; our own number is {our_prob}% and the fair line is {line}, a gap of {edge} points.",
            f"The captured price of {price} implies {market_prob}% before margin and {fair}% after the {allowance}% allowance; we make it {our_prob}%, so the fair line is {line}.",
        ], event_id, "numbers"))
        if consensus is not None and tips and tips_total:
            body.append(f"{consensus}% of the recorded OLBG tips are on this selection ({tips} of {tips_total}).")
        body.append(one([
            "No injury report is carried for this fixture in the feeds we read, so nothing is added on availability.",
            "The league feed we read carries no injury designation for this game, and none is claimed here.",
        ], event_id, "injury"))
        body.append(one([
            "The case rests on the season record, the split and the price rather than on a single result.",
            "That is a season-long read of the two sides rather than a reaction to one scoreline.",
        ] if sport != "Tennis" else [
            "The case rests on the ranking gap and the price rather than on one recent result.",
            "Ranking points and the price carry this argument, not a single match.",
        ], event_id, "close"))
    else:
        lead = one([
            f"{selection} is the selection in the {market} at {price}.",
            f"The pick is {selection} in the {market}, quoted at {price}.",
            f"Back {selection} at {price} for the {market}.",
            f"{selection} at {price} is the call in the {market}.",
        ], event_id, "lead-market")
        where = (f"{competition} supplies the competition" if competition
                 else "OLBG does not publish a competition name on this market page")
        body = [lead, f"{where} and the event starts {start}."]
        if opponent:
            body.append(one([
                f"{selection} face {opponent}.",
                f"{opponent} are the opposition.",
            ], event_id, "opp-market"))
        body.append(one([
            f"Only one price per market is exposed publicly, so the margin is handled with a {allowance}% allowance: {price} implies {market_prob}%, which becomes {fair}% after the allowance. Our line is {line}.",
            f"OLBG publishes a single price for this market, so the book is adjusted with a stated {allowance}% allowance rather than measured: {market_prob}% implied falls to {fair}%, and our line is {line}.",
        ], event_id, "market-numbers"))
        if consensus is not None and tips and tips_total:
            body.append(one([
                f"The community split is {consensus}% on this selection, which is {tips} of {tips_total} recorded tips.",
                f"Of the {tips_total} tips OLBG lists for the market, {tips} ({consensus}%) sit on this side.",
            ], event_id, "consensus"))
        body.append(one([
            "No primary team-news, injury or lineup feed covers this competition in the sources we check, so none is claimed here.",
            "There is no reachable primary feed for selection news in this competition, and nothing on availability is asserted.",
        ], event_id, "no-feed"))
        body.append(one([
            "The price and the split of opinion are the whole case, and the confidence grade reflects that.",
            "This is a price-led call and is graded accordingly.",
        ], event_id, "close"))

    text = " ".join(part for part in body if part).replace("  ", " ").strip()
    for word in BANNED:
        text = text.replace(word + " ", "").replace(" " + word, "").replace(word.capitalize() + " ", "")
    return {"prediction": text, "facts": [f for f in facts if f]}


def apply(picks: list[dict[str, Any]], editorial: dict[str, dict[str, Any]] | None = None) -> None:
    editorial = editorial or {}
    for pick in picks:
        key = f"{pick.get('event_id')}:{pick.get('market')}:{pick.get('selection')}"
        override = editorial.get(key)
        if override:
            pick["prediction"] = override["prediction"]
            pick["facts"] = override.get("facts", [])
            continue
        built = build(pick)
        pick["prediction"] = built["prediction"]
        pick["facts"] = built["facts"]


if __name__ == "__main__":
    print("imported by build_dashboard.py")
