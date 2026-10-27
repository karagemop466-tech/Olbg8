#!/usr/bin/env python3
"""Line origination and probability maths for the OLBG research desk.

The engine works in three steps.

1. Margin removal. Every OLBG market is quoted with a bookmaker margin. We strip
   it with the power method (also called the log-odds or Shin-style adjustment),
   which keeps the relative ordering of prices but shrinks longshots harder than
   proportional de-vigging. The result is a fair probability for each selection
   in that market, and the fair probabilities sum to exactly 1.
2. Independent adjustment. Where an official competition feed exists we compare
   the two teams on that feed (record, last-ten form, scoring differential) and
   tilt the fair price by a capped, documented amount. Where no official feed
   exists we publish the de-margined price unchanged and label the row as
   market-anchored so nothing is presented as an independent rating.
3. Board construction. For sports with a scoring model we also originate a
   handicap line and a match-total line, with cover probabilities from a normal
   approximation whose spread is set per sport from observed scoring variation.

All functions are deterministic and unit-tested in tests/.
"""
from __future__ import annotations

import math
from typing import Iterable

# Observed scoring variation used for handicap/total cover maths.
SPORT_SD = {
    "baseball": {"margin": 4.2, "total": 3.4},
    "ice-hockey": {"margin": 2.35, "total": 1.85},
    "basketball": {"margin": 11.5, "total": 15.5},
    "rugby-league": {"margin": 14.0, "total": 11.5},
    "rugby-union": {"margin": 12.5, "total": 9.5},
    "handball": {"margin": 7.5, "total": 6.5},
    "volleyball": {"margin": 0.0, "total": 0.0},
    "tennis": {"margin": 0.0, "total": 0.0},
    "cricket": {"margin": 0.0, "total": 0.0},
    "darts": {"margin": 0.0, "total": 0.0},
    "snooker": {"margin": 0.0, "total": 0.0},
    "golf": {"margin": 0.0, "total": 0.0},
    "motor-racing": {"margin": 0.0, "total": 0.0},
    "greyhounds": {"margin": 0.0, "total": 0.0},
    "gaelic-sports": {"margin": 9.5, "total": 8.5},
}

# Home-field/court advantage expressed as a probability nudge before renormalising.
HOME_EDGE = {
    "baseball": 0.018, "ice-hockey": 0.022, "basketball": 0.030,
    "rugby-league": 0.035, "rugby-union": 0.035, "handball": 0.040,
    "volleyball": 0.030, "cricket": 0.015, "gaelic-sports": 0.030,
}


def american_to_decimal(american: float) -> float:
    a = float(american)
    if a >= 100 or a > 0:
        return 1.0 + a / 100.0
    return 1.0 + 100.0 / abs(a)


def decimal_to_american(dec: float) -> int:
    dec = float(dec)
    if dec <= 1.0000001:
        raise ValueError("decimal odds must exceed 1.0")
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100))
    return int(round(-100.0 / (dec - 1.0)))


def implied(decimal: float) -> float:
    return 1.0 / float(decimal)


def devig_power(decimals: Iterable[float], tol: float = 1e-12, max_iter: int = 200) -> list[float]:
    """Fair probabilities from decimal prices using the power method.

    Solves sum(p_i ** k) = 1 for k >= 1 where p_i = 1 / decimal_i, so the
    overround is absorbed by shrinking longshots proportionally more.
    """
    probs = [implied(d) for d in decimals]
    if not probs:
        return []
    if len(probs) == 1:
        return [1.0]
    if abs(sum(probs) - 1.0) < tol:
        return probs
    lo, hi = 1.0, 40.0
    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        total = sum(p ** mid for p in probs)
        if total > 1.0:
            lo = mid
        else:
            hi = mid
        if abs(total - 1.0) < 1e-13:
            break
    k = (lo + hi) / 2.0
    fair = [p ** k for p in probs]
    s = sum(fair)
    return [f / s for f in fair]


def devig_proportional(decimals: Iterable[float]) -> list[float]:
    probs = [implied(d) for d in decimals]
    s = sum(probs)
    return [p / s for p in probs] if s else []


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def cover_probability(margin: float, line: float, sd: float) -> float:
    """Probability a team covers, given its expected margin and the handicap it takes.

    `margin` is the team's expected winning margin (negative if it loses on
    average) and `line` is the handicap it takes, so -1.5 means giving 1.5.
    Covering needs margin + line > 0.
    """
    if sd <= 0:
        raise ValueError("sd must be positive")
    return normal_cdf((margin + line) / sd)


def expected_value(prob: float, decimal: float) -> float:
    """Expected profit per unit staked."""
    return prob * (decimal - 1.0) - (1.0 - prob)


def confidence_band(prob: float) -> str:
    if prob >= 0.70:
        return "high"
    if prob >= 0.60:
        return "medium"
    return "low"


def in_price_window(american: float, low: int = -250, high: int = 10000) -> bool:
    a = float(american)
    return low <= a <= high


def fair_board(selections: list[dict], sport: str, home_first: bool = True) -> list[dict]:
    """Attach fair probability and fair price to each selection of one market.

    `selections` are dicts with at least `selection` and `decimal`.
    """
    decimals = [float(s["decimal"]) for s in selections]
    fair = devig_power(decimals)
    out = []
    for sel, p in zip(selections, fair):
        dec = 1.0 / p if p > 0 else None
        out.append({**sel, "fair_prob": p, "fair_decimal": dec,
                    "fair_american": decimal_to_american(dec) if dec else None,
                    "market_implied": implied(sel["decimal"])})
    return out


# --------------------------------------------------------------- ratings tilt
def form_tilt(home_form: dict, away_form: dict, sport: str) -> float:
    """Capped probability tilt for the home side from official results data.

    Each qualifying comparison contributes a small, bounded amount; the total is
    clipped to +/-0.035 so a short-sample run can never dominate the price.
    """
    tilt = 0.0
    checks = 0

    def add(diff, scale, weight):
        nonlocal tilt, checks
        if diff is None:
            return
        tilt += max(-1.0, min(1.0, diff / scale)) * weight
        checks += 1

    # last-ten win differential
    h10, a10 = home_form.get("l10_pct"), away_form.get("l10_pct")
    if h10 is not None and a10 is not None:
        add(h10 - a10, 0.40, 0.012)
    # points percentage (hockey/basketball style)
    hp, ap = home_form.get("point_pct"), away_form.get("point_pct")
    if hp is not None and ap is not None:
        add(hp - ap, 0.35, 0.012)
    # scoring differential per game
    hd, ad = home_form.get("diff_per_game"), away_form.get("diff_per_game")
    if hd is not None and ad is not None:
        add(hd - ad, 2.5 if sport == "ice-hockey" else 1.6, 0.010)
    # win percentage
    hw, aw = home_form.get("pct"), away_form.get("pct")
    if hw is not None and aw is not None:
        add(hw - aw, 0.30, 0.008)
    if checks == 0:
        return 0.0
    return max(-0.035, min(0.035, tilt))


def apply_tilt(probs: list[float], tilt: float, home_index: int = 0,
               draw_index: int | None = None) -> list[float]:
    """Shift probability mass between the home and away selection."""
    if not probs or abs(tilt) < 1e-9:
        return list(probs)
    out = list(probs)
    away_index = 1 if home_index == 0 else 0
    move = min(abs(tilt), out[home_index] * 0.5, out[away_index] * 0.5)
    if tilt > 0:
        out[home_index] += move
        out[away_index] -= move
    else:
        out[home_index] -= move
        out[away_index] += move
    s = sum(out)
    return [p / s for p in out]
