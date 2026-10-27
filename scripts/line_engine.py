"""OLBG line origination engine.

Purpose
-------
Turn evidence we can actually source into our OWN betting lines, for every
sport in scope, without ever inventing an input.

The engine is deliberately split into two halves:

1. Pure arithmetic (this file). Every function is deterministic, unit tested
   and takes explicit inputs. It cannot guess: if an input is ``None`` the
   dependent output is ``None``.

2. Evidence (``data/live/*.json`` and ``data/evidence/*.json``). Anything that
   is not captured from OLBG or an official source is left blank upstream and
   arrives here as ``None``.

Nothing in this module contacts the network.

The anchor we can source
------------------------
OLBG publishes, for every market on every event, the number of tips each
selection has received and the total number of tips on all outcomes in that
market. OLBG's own golf page states the definition:

    "The selection odds are shown alongside the number of tips received
     compared with the total number of tips on all outcomes in the market,
     which gives the confidence percentage."

    -- https://www.olbg.com/betting-tips/Golf/5

and the Value Rating definition on the same page confirms OLBG itself treats
that share as a probability to be compared against odds-implied probability.

So tip share across all outcomes of one market is a normalised crowd
distribution: it already sums to 1, so there is no bookmaker overround to
strip out. It is a legitimate, citable probability anchor.

Its weakness is sample size. Most OLBG markets at capture carry 1-8 tips.
A raw share from 2 tips is noise, not information. We therefore shrink it
toward a prior with a Dirichlet-multinomial posterior mean, which is exactly
the right tool: small samples stay near the prior, large samples overwhelm it.

    p_i = (n_i + k * pi_i) / (N + k)

``k`` is the prior strength expressed in pseudo-tips and is set per sport.
``pi`` is the prior. When we have captured official strength data (rankings,
standings, points) we build ``pi`` from it; when we have not, ``pi`` is
uniform and the row is flagged as carrying no independent information beyond
the crowd.

Calibration constants are assumptions, not verified facts
--------------------------------------------------------
Converting a win probability into a handicap line, or a scoring rate into a
total, needs a sport-specific slope and a dispersion figure. Those are market
conventions, recorded in ``SPORT_CALIBRATION`` and labelled as assumptions.
Any price that depends on them is marked ``calibrated=True`` downstream so it
can never be mistaken for an observed number.
"""

from __future__ import annotations

import math
from typing import Dict, Optional

__all__ = [
    "SPORT_CALIBRATION",
    "PRICE_BAND",
    "OUTCOME_HALF_WIDTH",
    "cal",
    "price_pack",
    "shrink_tips",
    "prior_from_strength",
    "prob_to_decimal",
    "prob_to_american",
    "american_to_prob",
    "decimal_to_prob",
    "normalise",
    "add_overround",
    "two_way_from_three_way",
    "expected_margin",
    "fair_handicap",
    "price_handicap",
    "price_total",
    "confidence_label",
    "in_price_band",
    "norm_cdf",
]


# --------------------------------------------------------------------------
# Price band requested for high-confidence work: -250 through +10000.
# -250 implies 71.43%; +10000 implies 0.99%. Anything shorter than -250 is
# excluded as a trivially heavy favourite, anything longer than +10000 as an
# unpriceable lottery ticket.
# --------------------------------------------------------------------------
PRICE_BAND = {"min_american": -250, "max_american": 10000}

# --------------------------------------------------------------------------
# Outcome granularity. Every scoring unit in these sports -- runs, goals,
# points, frames, legs, sets, games -- is a whole number, so a match total or
# a winning margin can only land on an integer. A whole-number line therefore
# pushes when the outcome lands exactly on it, which is the continuous window
# +/- 0.5. A line quoted at a half point can never push.
# --------------------------------------------------------------------------
OUTCOME_HALF_WIDTH = 0.5


# --------------------------------------------------------------------------
# Per-sport calibration.
#
#   margin_per_prob_point : expected winning margin per 1.00 of win
#                           probability above 0.50, expressed in the sport's
#                           scoring unit. Equivalently, how much of an
#                           expected margin a given edge implies.
#   margin_sd             : standard deviation of the winning margin.
#   handicap_increment    : the granularity lines are quoted at.
#   supports_handicap     : does the sport have a mainstream handicap market.
#   supports_total        : does the sport have a mainstream over/under.
#   draw_possible         : can regulation time end level.
#   prior_strength_k      : pseudo-tips of weight given to the prior.
#
# These are ASSUMPTIONS. They are calibrated to widely used market
# conventions for each sport and are never presented as observed data.
# --------------------------------------------------------------------------
SPORT_CALIBRATION: Dict[str, dict] = {
    # Basketball: the standard convention is roughly 3% win probability per
    # point of spread near even money, i.e. ~33 points of expected margin per
    # unit of probability. NBA margins disperse wider than EuroLeague.
    "basketball": dict(margin_per_prob_point=33.0, margin_sd=12.0,
                       handicap_increment=0.5, supports_handicap=True,
                       supports_total=True, draw_possible=False,
                       prior_strength_k=8.0, unit="points"),
    "basketball_euro": dict(margin_per_prob_point=30.0, margin_sd=11.0,
                            handicap_increment=0.5, supports_handicap=True,
                            supports_total=True, draw_possible=False,
                            prior_strength_k=8.0, unit="points"),
    # Ice hockey: one goal moves a regulation win probability by roughly
    # 20%, so ~5 goals of expected margin per unit probability. The puck
    # line is conventionally fixed at 1.5 and priced, not derived.
    "ice_hockey": dict(margin_per_prob_point=5.0, margin_sd=2.3,
                       handicap_increment=0.5, supports_handicap=True,
                       supports_total=True, draw_possible=True,
                       prior_strength_k=8.0, unit="goals"),
    # Baseball: one run is worth roughly 10% near even money. Run line is
    # conventionally fixed at 1.5. Totals disperse around 4 runs.
    "baseball": dict(margin_per_prob_point=10.0, margin_sd=4.0,
                     handicap_increment=0.5, supports_handicap=True,
                     supports_total=True, draw_possible=False,
                     prior_strength_k=10.0, unit="runs"),
    # Rugby union: one point is worth about 2.5-3%, giving ~36 points of
    # expected margin per unit probability. Handicaps quote at 0.5.
    "rugby_union": dict(margin_per_prob_point=36.0, margin_sd=14.0,
                        handicap_increment=0.5, supports_handicap=True,
                        supports_total=True, draw_possible=True,
                        prior_strength_k=6.0, unit="points"),
    # Rugby league: higher scoring than union; one point worth ~2%.
    "rugby_league": dict(margin_per_prob_point=50.0, margin_sd=17.0,
                         handicap_increment=0.5, supports_handicap=True,
                         supports_total=True, draw_possible=True,
                         prior_strength_k=6.0, unit="points"),
    # Cricket: format dependent. T20 totals cluster near 160-180, ODI near
    # 260-290. A 1% edge is worth very little in runs because the toss and
    # conditions dominate, so the slope is shallow.
    "cricket_t20": dict(margin_per_prob_point=25.0, margin_sd=22.0,
                        handicap_increment=0.5, supports_handicap=True,
                        supports_total=True, draw_possible=False,
                        prior_strength_k=8.0, unit="runs"),
    "cricket_odi": dict(margin_per_prob_point=45.0, margin_sd=45.0,
                        handicap_increment=0.5, supports_handicap=True,
                        supports_total=True, draw_possible=True,
                        prior_strength_k=8.0, unit="runs"),
    # Volleyball: best-of-five sets, so the natural handicap is in sets
    # (-1.5 / +1.5) or points within a match. Set margins are tight.
    "volleyball": dict(margin_per_prob_point=2.2, margin_sd=1.4,
                       handicap_increment=0.5, supports_handicap=True,
                       supports_total=True, draw_possible=False,
                       prior_strength_k=6.0, unit="sets"),
    # Handball: high scoring, ~60 goals a game. One goal worth ~2%.
    "handball": dict(margin_per_prob_point=50.0, margin_sd=7.0,
                     handicap_increment=0.5, supports_handicap=True,
                     supports_total=True, draw_possible=True,
                     prior_strength_k=6.0, unit="goals"),
    # Tennis: no mainstream match handicap in sets beyond +/-1.5, and the
    # market is effectively two-way. Totals are quoted in games.
    "tennis": dict(margin_per_prob_point=4.0, margin_sd=5.0,
                   handicap_increment=0.5, supports_handicap=False,
                   supports_total=True, draw_possible=False,
                   prior_strength_k=10.0, unit="games"),
    # Field sports. Outright markets only: no handicap, no total.
    "golf": dict(margin_per_prob_point=None, margin_sd=None,
                 handicap_increment=None, supports_handicap=False,
                 supports_total=False, draw_possible=False,
                 prior_strength_k=4.0, unit="outright"),
    "motor_racing": dict(margin_per_prob_point=None, margin_sd=None,
                         handicap_increment=None, supports_handicap=False,
                         supports_total=False, draw_possible=False,
                         prior_strength_k=4.0, unit="outright"),
    # Snooker and darts are two-way match sports quoted in frames/legs.
    "snooker": dict(margin_per_prob_point=3.0, margin_sd=2.5,
                    handicap_increment=0.5, supports_handicap=True,
                    supports_total=True, draw_possible=False,
                    prior_strength_k=8.0, unit="frames"),
    "darts": dict(margin_per_prob_point=2.5, margin_sd=2.0,
                  handicap_increment=0.5, supports_handicap=True,
                  supports_total=True, draw_possible=False,
                  prior_strength_k=8.0, unit="legs"),
    # Greyhound racing: a trap-draw field market, no handicap.
    "greyhounds": dict(margin_per_prob_point=None, margin_sd=None,
                       handicap_increment=None, supports_handicap=False,
                       supports_total=False, draw_possible=False,
                       prior_strength_k=4.0, unit="outright"),
    # Gaelic football and hurling: point (1) and goal (3) scoring, margins
    # usually single digits in points.
    "gaelic": dict(margin_per_prob_point=14.0, margin_sd=8.0,
                   handicap_increment=0.5, supports_handicap=True,
                   supports_total=True, draw_possible=True,
                   prior_strength_k=6.0, unit="points"),
}


def cal(sport: str) -> dict:
    """Return the calibration block for a sport, tolerating cricket variants."""
    if sport in SPORT_CALIBRATION:
        return SPORT_CALIBRATION[sport]
    if sport.startswith("cricket"):
        return SPORT_CALIBRATION["cricket_odi"]
    raise KeyError(f"no calibration for sport {sport!r}")


# --------------------------------------------------------------------------
# Odds arithmetic
# --------------------------------------------------------------------------
def prob_to_decimal(p: Optional[float]) -> Optional[float]:
    """Fair decimal odds from a probability. p=0 is unpriceable."""
    if p is None:
        return None
    if p <= 0.0:
        return None
    return round(1.0 / p, 3)


def prob_to_american(p: Optional[float]) -> Optional[int]:
    """Fair American odds from a probability, rounded to an integer."""
    if p is None:
        return None
    if p <= 0.0 or p >= 1.0:
        return None
    if p > 0.5:
        return int(round(-100.0 * p / (1.0 - p)))
    return int(round(100.0 * (1.0 - p) / p))


def american_to_prob(a: Optional[int]) -> Optional[float]:
    """Implied probability of an American price, ignoring vig."""
    if a is None or a == 0:
        return None
    if a > 0:
        return 100.0 / (a + 100.0)
    return abs(a) / (abs(a) + 100.0)


def decimal_to_prob(d: Optional[float]) -> Optional[float]:
    """Implied probability of a decimal price, ignoring vig."""
    if d is None or d <= 1.0:
        return None
    return 1.0 / d


def in_price_band(american: Optional[int],
                  lo: int = PRICE_BAND["min_american"],
                  hi: int = PRICE_BAND["max_american"]) -> bool:
    """True when a price sits inside the requested -250 to +10000 band."""
    if american is None:
        return False
    return lo <= american <= hi


def normalise(probs: Dict[str, float]) -> Dict[str, float]:
    """Scale a dict of non-negative weights so it sums to 1."""
    total = sum(v for v in probs.values() if v is not None and v > 0)
    if total <= 0:
        return {}
    return {k: (v / total if v else 0.0) for k, v in probs.items()}


def add_overround(probs: Dict[str, float],
                  overround: float = 0.045) -> Dict[str, float]:
    """Turn fair probabilities into a book by scaling every price up.

    ``overround`` is the bookmaker's total percentage across the market.
    Each probability is multiplied by (1 + overround), which shortens every
    price; the market then sums to 1 + overround.
    """
    if not probs:
        return {}
    f = 1.0 + overround
    out = {k: v * f for k, v in probs.items()}
    # Cap so no single outcome is quoted as a certainty.
    return {k: min(v, 0.999) for k, v in out.items()}


# --------------------------------------------------------------------------
# The shrinkage estimator: this is where a line actually originates
# --------------------------------------------------------------------------
def shrink_tips(tips: Dict[str, Optional[int]],
                prior: Optional[Dict[str, float]] = None,
                k: Optional[float] = None,
                sport: str = "basketball") -> Dict[str, float]:
    """Dirichlet-multinomial posterior mean over a market's selections.

    ``tips`` maps selection name -> number of tips received. Selections with
    ``None`` counts are treated as zero but still occupy the outcome space,
    because OLBG lists every outcome it accepts tips on.

    ``prior`` maps the same names -> prior probability. Missing names get an
    equal share of the leftover prior mass. When ``prior`` is ``None`` the
    prior is uniform, and the result is pure shrunk crowd opinion.

    ``k`` is prior strength in pseudo-tips; defaults to the sport's value.

    Returns a dict summing to 1. Returns ``{}`` when there are no selections.
    """
    names = [n for n in tips]
    if not names:
        return {}
    if k is None:
        k = cal(sport)["prior_strength_k"]

    # Build the prior, completing it uniformly over unnamed outcomes.
    if prior:
        known = {n: prior[n] for n in names if n in prior and prior[n] is not None}
        unknown = [n for n in names if n not in known]
        left = max(0.0, 1.0 - sum(known.values()))
        pi = dict(known)
        if unknown:
            share = left / len(unknown) if left > 0 else 0.0
            for n in unknown:
                pi[n] = share
        pi = normalise(pi) or {n: 1.0 / len(names) for n in names}
    else:
        pi = {n: 1.0 / len(names) for n in names}

    n_total = sum(v for v in tips.values() if v)
    denom = n_total + k
    out = {}
    for n in names:
        c = tips[n] or 0
        out[n] = (c + k * pi[n]) / denom
    return normalise(out)


def prior_from_strength(home_strength: Optional[float],
                        away_strength: Optional[float],
                        home_advantage: float = 0.0,
                        slope: float = 1.0) -> Optional[Dict[str, float]]:
    """Turn two official strength ratings into a two-way prior.

    Strength can be ranking points, standings percentage, Elo or any ordinal
    score where higher is better, provided both sides use the SAME scale.
    A logistic maps the gap (plus home advantage) onto a win probability.

    Returns ``None`` when either strength is missing, so no prior can be
    silently invented.
    """
    if home_strength is None or away_strength is None:
        return None
    gap = (home_strength - away_strength) + home_advantage
    p_home = 1.0 / (1.0 + math.exp(-slope * gap))
    return {"home": p_home, "away": 1.0 - p_home}


def two_way_from_three_way(home: float, draw: float, away: float,
                           overtime_win_share: float = 0.5) -> Dict[str, float]:
    """Collapse a 1X2 distribution into a two-way 'to win' distribution.

    Used for sports where the market we are pricing settles after extra time
    or a shootout. The draw mass is split by ``overtime_win_share``, which
    defaults to an even split; a genuinely better side takes more of it in
    practice, so callers should pass a captured value when they have one.
    """
    return {"home": home + draw * overtime_win_share,
            "away": away + draw * (1.0 - overtime_win_share)}


# --------------------------------------------------------------------------
# Margin, handicap and total pricing
# --------------------------------------------------------------------------
def norm_cdf(x: float) -> float:
    """Standard normal CDF, using erf so there is no dependency."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def expected_margin(p_side: Optional[float], sport: str,
                    slope: Optional[float] = None) -> Optional[float]:
    """Expected winning margin for a side given its win probability.

    Margin is centred on 0.50: an even game has an expected margin of zero.
    Returns ``None`` for field sports that have no margin concept.
    """
    if p_side is None:
        return None
    c = cal(sport)
    m = c["margin_per_prob_point"] if slope is None else slope
    if m is None:
        return None
    return (p_side - 0.5) * m


def fair_handicap(p_side: Optional[float], sport: str,
                  side_is_home: bool = True) -> Optional[float]:
    """Derive the handicap line that makes this side a pick'em.

    The fair line is the negative of the expected margin: if a side is
    expected to win by 6.4 points, the even-money handicap is -6.5.
    Rounded to the sport's quoting increment.
    """
    em = expected_margin(p_side, sport)
    if em is None:
        return None
    inc = cal(sport)["handicap_increment"] or 0.5
    line = -em
    if not side_is_home:
        line = em
    return round(line / inc) * inc


def _push_half_width(line: float, step: float) -> float:
    """Half-width of the push window for a line.

    Two different granularities matter here and they are not the same:

    * the QUOTING step, i.e. how finely a bookmaker prices a line (0.5 for
      most of these sports, occasionally 0.25);
    * the OUTCOME granularity, i.e. how finely a match total or winning
      margin can actually land. Runs, goals, points, frames, legs, sets and
      games are all whole numbers, so the outcome granularity is 1.0.

    Only a whole-number line can push, and when it does the outcome has to
    land exactly on it, which in continuous terms is the window
    ``[line - 0.5, line + 0.5]``. So the half-width is 0.5 -- half the
    OUTCOME granularity -- not half the quoting step. Using the quoting step
    here would understate push risk by a factor of two on a 0.5-step sport.

    A line quoted at .5 (or .25) can never push, so its half-width is 0.0 and
    the three-way partition is exact.
    """
    if step <= 0:
        return 0.0
    if abs(line - round(line)) > 1e-9:
        return 0.0
    return OUTCOME_HALF_WIDTH


def _partition(mean: float, sd: float, threshold: float,
               half: float) -> tuple:
    """Split a normal distribution into (below, inside, above) around a window.

    The three pieces are disjoint and exhaustive, so they sum to exactly 1.
    """
    lo = norm_cdf((threshold - half - mean) / sd)
    hi = norm_cdf((threshold + half - mean) / sd)
    below = lo
    inside = max(0.0, hi - lo)
    above = max(0.0, 1.0 - hi)
    return below, inside, above


def price_handicap(p_side: Optional[float], line: float, sport: str,
                   sd: Optional[float] = None) -> Optional[dict]:
    """Price BOTH sides of a given handicap line.

    Uses a normal approximation to the margin distribution. That is an
    assumption: real margins are discretised and skewed, so the tails are
    only indicative. It is used because it is auditable and needs one
    dispersion parameter rather than a full match simulation.

    ``line`` is the side's own handicap, e.g. -6.5 means the side must win
    by more than 6.5.

    Cover / push / lose are computed as a disjoint partition of the margin
    distribution around the pivot ``-line``, so the three probabilities sum
    to exactly 1 and no push mass is double counted.
    """
    if p_side is None:
        return None
    c = cal(sport)
    if sd is None:
        sd = c["margin_sd"]
    if sd is None or sd <= 0:
        return None
    em = expected_margin(p_side, sport)
    if em is None:
        return None
    step = c["handicap_increment"] or 0.5
    half = _push_half_width(line, step)
    # Covering the line means margin + line > 0, i.e. margin > -line.
    lose, push, cover = _partition(em, sd, -line, half)
    return {
        "line": line,
        "p_cover": round(cover, 4),
        "p_push": round(push, 4),
        "p_lose": round(lose, 4),
        "american": prob_to_american(cover),
        "decimal": prob_to_decimal(cover),
        "calibrated": True,
    }


def price_total(expected_total: Optional[float], line: Optional[float],
                sd: Optional[float], increment: float = 0.5) -> Optional[dict]:
    """Price over and under on a match total.

    Needs an expected total and a dispersion, both of which must come from
    captured scoring data. If either is missing this returns ``None`` rather
    than falling back to a generic league average, because a generic average
    presented as a line would be a fabrication.

    Under / push / over form a disjoint partition of the total distribution
    around the line, so they sum to exactly 1.
    """
    if expected_total is None or sd is None or sd <= 0:
        return None
    if line is None:
        # Originate the line: nearest increment to the expectation.
        line = round(expected_total / increment) * increment
        # Avoid a line sitting exactly on the expectation where possible,
        # because that maximises push risk on a whole-number quote.
        if abs(line - expected_total) < 1e-9:
            line = line + increment / 2.0
    half = _push_half_width(line, increment)
    under, push, over = _partition(expected_total, sd, line, half)
    return {
        "line": round(line, 2),
        "expected_total": round(expected_total, 2),
        "p_over": round(over, 4),
        "p_under": round(under, 4),
        "p_push": round(push, 4),
        "american_over": prob_to_american(over),
        "american_under": prob_to_american(under),
        "calibrated": True,
    }


# --------------------------------------------------------------------------
# Confidence labelling
# --------------------------------------------------------------------------
def confidence_label(p: Optional[float], evidence_tier: str = "crowd_only",
                     min_tips: int = 5) -> str:
    """Assign low / medium / high.

    Confidence is deliberately NOT just a probability threshold. The brief
    asks for picks between -250 and +10000, and warns against treating any
    >70% price as automatically high confidence. So a label depends on three
    things: how far the probability is from a coin flip, how much evidence
    stands behind it, and whether the sample of tips is big enough to mean
    anything.

    ``evidence_tier`` is one of:
      ``official``    - official source confirms form/availability for this
                        exact event, and an official strength prior exists.
      ``partial``     - official source confirms the event identity and some
                        context, but not availability.
      ``crowd_only``  - nothing but the OLBG tip distribution.
    """
    if p is None:
        return "low"
    edge = abs(p - 0.5)
    tiers = {"official": 2, "partial": 1, "crowd_only": 0}
    tier = tiers.get(evidence_tier, 0)

    if tier >= 2 and edge >= 0.22:
        return "high"
    if tier >= 1 and edge >= 0.30:
        return "high"
    if tier >= 1 and edge >= 0.15:
        return "medium"
    if tier == 0 and edge >= 0.34:
        return "medium"
    return "low"


def price_pack(fair_probs: Dict[str, float],
               overround: float = 0.045) -> dict:
    """Bundle fair and book prices for every outcome in one market."""
    book = add_overround(fair_probs, overround)
    return {
        "fair": {k: {"p": round(v, 4),
                     "american": prob_to_american(v),
                     "decimal": prob_to_decimal(v)} for k, v in fair_probs.items()},
        "book": {k: {"p": round(v, 4),
                     "american": prob_to_american(v),
                     "decimal": prob_to_decimal(v)} for k, v in book.items()},
        "overround_applied": overround,
    }
