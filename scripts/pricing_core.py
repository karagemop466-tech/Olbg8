#!/usr/bin/env python3
"""Line origination, confidence grading and pick selection.

Method
------
1. Every OLBG market row carries a decimal price. Prices are converted to
   implied probabilities.
2. The overround is removed per market. We use Shin's method (which corrects
   the favourite-longshot bias fixed-odds books exhibit) and fall back to
   proportional normalisation when Shin has no solution.
3. Where a primary source gives us an independent measurement - club records
   and home advantage for MLB/NBA/NHL, ranking points for tennis - we blend it
   with the market estimate. The blend weight depends on how much official
   evidence exists for that event and is recorded on every row.
4. Our own price is the decimal odds implied by that blended probability.
   Confidence is graded from market completeness, official evidence and the
   size of the disagreement, never from the price alone.

No number here is typed in by hand: every input is read from a captured file.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

MIN_AMERICAN = -250
MAX_AMERICAN = 10000


# ------------------------------------------------------------------ market ---
def implied(decimal: float | None) -> float | None:
    if not decimal or decimal <= 1.0:
        return None
    return 1.0 / decimal


def shin_probabilities(decimals: list[float]) -> list[float] | None:
    """Shin (1993) de-vigging.

    Solves for the insider-trading proportion z so that the recovered
    probabilities sum to one.
    """
    inverses = [1.0 / d for d in decimals]
    booksum = sum(inverses)
    if booksum <= 0:
        return None
    if booksum <= 1.0 + 1e-9:
        return [p / booksum for p in inverses]

    def total(z: float) -> float:
        acc = 0.0
        for pi in inverses:
            disc = z * z + 4.0 * (1.0 - z) * pi * pi / booksum
            if disc < 0:
                return float("nan")
            acc += (math.sqrt(disc) - z) / (2.0 * (1.0 - z))
        return acc

    low, high = 0.0, 0.45
    for _ in range(80):
        mid = (low + high) / 2.0
        value = total(mid)
        if math.isnan(value):
            high = mid
            continue
        if abs(value - 1.0) < 1e-12:
            break
        if value > 1.0:
            low = mid
        else:
            high = mid
    z = (low + high) / 2.0
    probs = []
    for pi in inverses:
        disc = z * z + 4.0 * (1.0 - z) * pi * pi / booksum
        if disc < 0:
            return None
        probs.append((math.sqrt(disc) - z) / (2.0 * (1.0 - z)))
    total_p = sum(probs)
    if total_p <= 0 or not all(0 < p < 1 for p in probs):
        return None
    return [p / total_p for p in probs]


def proportional(decimals: list[float]) -> list[float]:
    inverses = [1.0 / d for d in decimals]
    total = sum(inverses)
    return [p / total for p in inverses]


def american(decimal: float | None) -> int | None:
    if not decimal or decimal <= 1.0:
        return None
    if decimal >= 2.0:
        return int(round((decimal - 1.0) * 100))
    return int(round(-100.0 / (decimal - 1.0)))


def decimal_from_prob(prob: float | None) -> float | None:
    if not prob or prob <= 0 or prob >= 1:
        return None
    return round(1.0 / prob, 2)


def in_range(price: int | None) -> bool:
    return price is not None and MIN_AMERICAN <= price <= MAX_AMERICAN


# --------------------------------------------------------- official models ---
def log5(win_a: float, win_b: float, home_edge: float) -> float:
    """Bill James' log5 with a home-field multiplier on A's side."""
    a = min(max(win_a, 0.01), 0.99)
    b = min(max(win_b, 0.01), 0.99)
    base = (a * (1 - b)) / (a * (1 - b) + (1 - a) * b)
    shifted = base + home_edge
    return min(max(shifted, 0.02), 0.98)


def ranking_prob(points_a: float, points_b: float, scale: float) -> float:
    if points_a <= 0 or points_b <= 0:
        return 0.5
    diff = math.log(points_a / points_b) * scale
    return 1.0 / (1.0 + math.exp(-diff))


# ------------------------------------------------------------- confidence ---
def grade(market_complete: bool, official: bool, edge_pts: float, price: int | None) -> str:
    if not market_complete:
        return "low"
    if not in_range(price):
        return "low"
    if official and edge_pts >= 2.5:
        return "high"
    if official and edge_pts >= 1.0:
        return "medium"
    if not official and edge_pts >= 1.0:
        return "medium"
    return "low"


def grade_probability(our_prob: float, in_band: bool, supported: bool) -> str:
    """User-facing confidence: how likely is the selection to win, and is it backed?

    high   - our own probability is at least 70% (a -250 favourite or shorter
             in American terms), the line sits inside the published band and
             either primary data or a majority of the community backs it.
    medium - 55% to 70%, similarly supported.
    low    - everything else, published only when a sport would otherwise be
             blank.
    """
    if not in_band:
        return "low"
    if our_prob >= 70.0 and supported:
        return "high"
    if our_prob >= 55.0 and supported:
        return "medium"
    return "low"


def confidence_score(level: str, edge_pts: float, coverage: float) -> float:
    base = {"high": 60.0, "medium": 38.0, "low": 18.0}[level]
    return round(base + min(edge_pts, 8.0) * 3.0 + coverage * 12.0, 2)


# ------------------------------------------------------------------ build ---
def load_rows(olbg_dir: Path) -> list[dict[str, Any]]:
    latest = olbg_dir / "latest.json"
    if latest.exists():
        payload = json.loads(latest.read_text())
        rows = payload.get("rows") or []
        if rows:
            return rows
    rows: list[dict[str, Any]] = []
    for path in sorted(olbg_dir.glob("*.json")):
        if path.name.startswith("_") or path.name == "latest.json":
            continue
        payload = json.loads(path.read_text())
        rows.extend(payload.get("rows") or [])
    return rows


def load_team_index() -> dict[str, dict[str, Any]]:
    """Canonical team names with records, from primary league feeds."""
    index: dict[str, dict[str, Any]] = {}
    standings = DATA / "official" / "nhl-standings.json"
    if standings.exists():
        payload = json.loads(standings.read_text())
        for row in payload.get("standings", []):
            names = {
                f"{row.get('placeName', {}).get('default', '')} {row.get('teamName', {}).get('default', '')}".strip(),
                row.get("teamCommonName", {}).get("default", ""),
                row.get("teamAbbrev", {}).get("default", ""),
            }
            entry = {
                "sport": "Ice Hockey",
                "wins": row.get("wins"),
                "losses": row.get("losses"),
                "ot": row.get("otLosses"),
                "points": row.get("points"),
                "point_pct": row.get("pointPctg"),
                "goals_for": row.get("goalFor"),
                "goals_against": row.get("goalAgainst"),
                "streak": row.get("streakCode") or "",
                "home": f"{row.get('homeWins')}-{row.get('homeLosses')}-{row.get('homeOtLosses')}",
                "road": f"{row.get('roadWins')}-{row.get('roadLosses')}-{row.get('roadOtLosses')}",
                "source": "https://api-web.nhle.com/v1/standings/now",
            }
            for name in names:
                if name:
                    index.setdefault(name.lower(), entry)
    mlb = DATA / "official" / "mlb-standings.json"
    if mlb.exists():
        payload = json.loads(mlb.read_text())
        for group in payload.get("records", []):
            for team in group.get("teamRecords", []):
                name = team.get("team", {}).get("name", "")
                splits = {s.get("type"): s for s in team.get("records", {}).get("splitRecords", [])}
                entry = {
                    "sport": "Baseball",
                    "wins": team.get("wins"),
                    "losses": team.get("losses"),
                    "pct": team.get("winningPercentage"),
                    "games_back": team.get("gamesBack"),
                    "runs_scored": team.get("runsScored"),
                    "runs_allowed": team.get("runsAllowed"),
                    "run_diff": team.get("runDifferential"),
                    "streak": team.get("streak", {}).get("streakCode", ""),
                    "home": f"{splits.get('home', {}).get('wins', '?')}-{splits.get('home', {}).get('losses', '?')}",
                    "away": f"{splits.get('away', {}).get('wins', '?')}-{splits.get('away', {}).get('losses', '?')}",
                    "source": f"https://www.mlb.com/standings",
                }
                for alias in {name, name.split()[-1]}:
                    if alias:
                        index.setdefault(alias.lower(), entry)
    return index


def load_nba_records() -> dict[str, dict[str, Any]]:
    path = DATA / "official" / "espn-nba-teams.json"
    out: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return out
    payload = json.loads(path.read_text())
    for sport in payload.get("sports", []):
        for league in sport.get("leagues", []):
            for team in league.get("teams", []):
                item = team.get("team", {})
                record = next(iter(item.get("record", {}).get("items", [])), {}).get("summary", "")
                entry = {
                    "sport": "Basketball",
                    "record": record,
                    "name": item.get("displayName"),
                    "abbrev": item.get("abbreviation"),
                    "source": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams",
                }
                for alias in {item.get("displayName", ""), item.get("name", ""), item.get("abbreviation", "")}:
                    if alias:
                        out.setdefault(alias.lower(), entry)
    return out


def parse_record(record: str) -> tuple[int, int]:
    try:
        wins, losses = record.split("-")[:2]
        return int(wins), int(losses)
    except (ValueError, AttributeError):
        return 0, 0


def team_aliases() -> dict[str, str]:
    """OLBG abbreviates US clubs ("BKN Nets"); map them to full names."""
    mapping: dict[str, str] = {}
    teams = DATA / "official" / "mlb-teams.json"
    if teams.exists():
        payload = json.loads(teams.read_text())
        for team in payload.get("teams", []):
            name = team.get("name", "")
            mapping[name.lower()] = name
            mapping[(team.get("teamName") or "").lower()] = name
            if team.get("abbreviation"):
                mapping[team["abbreviation"].lower()] = name
    return mapping
