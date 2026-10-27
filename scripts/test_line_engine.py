"""Tests for the line origination engine.

Run: python3 scripts/test_line_engine.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from line_engine import (  # noqa: E402
    OUTCOME_HALF_WIDTH, PRICE_BAND, SPORT_CALIBRATION, add_overround, american_to_prob,
    confidence_label, decimal_to_prob, expected_margin, fair_handicap,
    in_price_band, norm_cdf, normalise, price_handicap, price_total,
    prior_from_strength, prob_to_american, prob_to_decimal, shrink_tips,
    two_way_from_three_way,
)

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name} {detail}")
        FAILS.append(name)


def approx(a, b, tol=1e-6):
    return a is not None and b is not None and abs(a - b) <= tol


print("odds conversion")
check("evens -> +100/-100 boundary", prob_to_american(0.5) == 100)
check("p=0.75 -> -300", prob_to_american(0.75) == -300)
check("p=0.25 -> +300", prob_to_american(0.25) == 300)
check("p=1/3 -> +200", prob_to_american(1.0 / 3.0) == 200)
check("p=0.01 -> +9900", prob_to_american(0.01) == 9900)
check("p=0 -> None (unpriceable)", prob_to_american(0.0) is None)
check("p=1 -> None (unpriceable)", prob_to_american(1.0) is None)
check("p=None -> None", prob_to_american(None) is None)
check("decimal p=0.5 -> 2.0", approx(prob_to_decimal(0.5), 2.0))
check("round trip -250", approx(american_to_prob(-250), 250 / 350.0, 1e-9))
check("round trip +10000", approx(american_to_prob(10000), 100 / 10100.0, 1e-9))
check("decimal round trip", approx(decimal_to_prob(prob_to_decimal(0.62)), 0.62, 1e-3))
check("american_to_prob(0) is None", american_to_prob(0) is None)

print("price band")
check("-250 in band", in_price_band(-250))
check("+10000 in band", in_price_band(10000))
check("-300 out of band (too short)", not in_price_band(-300))
check("-1000 out of band", not in_price_band(-1000))
check("+20000 out of band", not in_price_band(20000))
check("None out of band", not in_price_band(None))
check("band constants", PRICE_BAND == {"min_american": -250, "max_american": 10000})
# -250 implies 71.43%; the brief's concern is that anything shorter is a
# trivial favourite. Confirm the boundary arithmetic.
check("-250 implies 71.4%", approx(american_to_prob(-250), 0.7142857, 1e-6))

print("normalise / overround")
n = normalise({"a": 2, "b": 2})
check("normalise sums to 1", approx(sum(n.values()), 1.0))
check("normalise empty on all-zero", normalise({"a": 0, "b": 0}) == {})
b = add_overround({"a": 0.5, "b": 0.5}, 0.045)
check("overround sums to 1+overround", approx(sum(b.values()), 1.045))
check("overround shortens price", b["a"] > 0.5)
check("overround caps at 0.999", add_overround({"a": 0.99, "b": 0.01}, 0.5)["a"] <= 0.999)

print("shrinkage estimator")
# With no tips at all, output must equal the prior exactly.
p = shrink_tips({"a": 0, "b": 0}, prior={"a": 0.7, "b": 0.3}, k=5.0)
check("zero tips -> prior", approx(p["a"], 0.7, 1e-9) and approx(p["b"], 0.3, 1e-9))
# With huge tips, output must approach the raw crowd share.
p = shrink_tips({"a": 100000, "b": 0}, prior={"a": 0.1, "b": 0.9}, k=5.0)
check("huge sample -> crowd share", p["a"] > 0.999)
# A single tip out of one must NOT produce 100%.
p = shrink_tips({"a": 1, "b": 0}, k=8.0)
check("1/1 tip is not a certainty", p["a"] < 0.6, f"got {p['a']}")
check("shrunk distribution sums to 1", approx(sum(p.values()), 1.0))
# Exact arithmetic: (1 + 8*0.5)/(1+8) = 5/9
p = shrink_tips({"a": 1, "b": 0}, k=8.0)
check("exact posterior mean 5/9", approx(p["a"], 5.0 / 9.0, 1e-9), f"got {p['a']}")
# Prior completes uniformly over outcomes with no stated prior.
p = shrink_tips({"a": 2, "b": 1, "c": 0}, prior={"a": 0.5}, k=3.0)
check("partial prior completes + sums to 1", approx(sum(p.values()), 1.0))
check("empty market -> empty", shrink_tips({}) == {})
# More tips must move the estimate toward the crowd.
low = shrink_tips({"a": 1, "b": 1}, prior={"a": 0.9, "b": 0.1}, k=8.0)["a"]
high = shrink_tips({"a": 10, "b": 10}, prior={"a": 0.9, "b": 0.1}, k=8.0)["a"]
check("bigger sample reduces prior pull", high < low, f"{low} vs {high}")

print("strength prior")
check("missing strength -> None (never invent)",
      prior_from_strength(None, 1500.0) is None)
check("both present -> dict", prior_from_strength(1600.0, 1500.0) is not None)
pr = prior_from_strength(1600.0, 1500.0, home_advantage=0.0, slope=0.01)
check("stronger side favoured", pr["home"] > 0.5)
check("prior sums to 1", approx(pr["home"] + pr["away"], 1.0))
pr2 = prior_from_strength(1500.0, 1500.0, home_advantage=3.0, slope=0.1)
check("home advantage lifts even sides", pr2["home"] > 0.5)

print("three-way collapse")
t = two_way_from_three_way(0.4, 0.3, 0.3)
check("draw split evenly by default", approx(t["home"], 0.55) and approx(t["away"], 0.45))
check("mass conserved", approx(t["home"] + t["away"], 1.0))
t2 = two_way_from_three_way(0.4, 0.3, 0.3, overtime_win_share=0.75)
check("custom OT share honoured", approx(t2["home"], 0.625))

print("normal cdf")
check("cdf(0)=0.5", approx(norm_cdf(0.0), 0.5, 1e-12))
check("cdf monotonic", norm_cdf(1.0) > norm_cdf(0.0) > norm_cdf(-1.0))
check("cdf(1.96)~0.975", approx(norm_cdf(1.96), 0.975, 1e-3))

print("margin, handicap, totals")
check("even game -> zero expected margin",
      approx(expected_margin(0.5, "basketball"), 0.0))
check("field sport -> None margin", expected_margin(0.6, "golf") is None)
check("None prob -> None margin", expected_margin(None, "basketball") is None)
fh = fair_handicap(0.5 + 6.5 / 33.0, "basketball")
check("fair handicap round trip", approx(fh, -6.5, 0.51), f"got {fh}")
check("fair handicap None for field sport", fair_handicap(0.7, "golf") is None)
ph = price_handicap(0.65, -3.5, "basketball")
check("handicap priced", ph is not None and ph["p_cover"] > 0.5)
check("handicap components sum to 1",
      approx(ph["p_cover"] + ph["p_push"] + ph["p_lose"], 1.0, 2e-4))
check("handicap marked calibrated", ph["calibrated"] is True)
check("bigger line -> harder to cover",
      price_handicap(0.65, -12.5, "basketball")["p_cover"] < ph["p_cover"])
check("handicap None without prob", price_handicap(None, -3.5, "basketball") is None)
check("handicap None for field sport", price_handicap(0.7, 1.5, "golf") is None)
# A side given points should cover more often than the same side laying them.
check("receiving points covers more",
      price_handicap(0.5, +6.5, "rugby_union")["p_cover"]
      > price_handicap(0.5, -6.5, "rugby_union")["p_cover"])

tt = price_total(215.0, None, 20.0, increment=0.5)
check("total originates a line when none given", tt is not None and tt["line"] is not None)
check("total over+under+push = 1 (4dp rounding tolerance)",
      approx(tt["p_over"] + tt["p_under"] + tt["p_push"], 1.0, 2e-4))
check("originated total sits near expectation", abs(tt["line"] - 215.0) <= 0.75)
check("total None without expectation", price_total(None, 215.0, 20.0) is None)
check("total None without dispersion", price_total(215.0, 215.0, None) is None)
check("over easier on a low line",
      price_total(220.0, 200.0, 20.0)["p_over"] > 0.8)
check("under easier on a high line",
      price_total(200.0, 220.0, 20.0)["p_under"] > 0.8)
# A half-point line cannot push; a whole-number line can.
half_line = price_total(215.0, 215.5, 20.0)
whole_line = price_total(215.0, 215.0, 20.0)
check("half-point total has zero push", approx(half_line["p_push"], 0.0, 1e-12))
check("half-point total still sums to 1",
      approx(half_line["p_over"] + half_line["p_under"] + half_line["p_push"], 1.0, 2e-4))
check("whole-number total carries real push", whole_line["p_push"] > 0.01)
check("whole-number total sums to 1",
      approx(whole_line["p_over"] + whole_line["p_under"] + whole_line["p_push"], 1.0, 2e-4))
# Carving a push window out of the middle must take mass from BOTH sides,
# measured against the half-point quotes on either side of the same centre.
# A whole-number 215 line needs T>215.5 to go over and T<214.5 to go under,
# whereas 214.5 needs only T>214.5 over and 215.5 only T<215.5 under.
low_half = price_total(215.0, 214.5, 20.0)
check("push window takes mass from the over side",
      whole_line["p_over"] < low_half["p_over"],
      f'{whole_line["p_over"]} vs {low_half["p_over"]}')
check("push window takes mass from the under side",
      whole_line["p_under"] < half_line["p_under"],
      f'{whole_line["p_under"]} vs {half_line["p_under"]}')
# Boundaries must coincide exactly where they are the same point.
check("whole 215 over boundary equals half 215.5 over boundary",
      approx(whole_line["p_over"], half_line["p_over"], 1e-9))
check("whole 215 under boundary equals half 214.5 under boundary",
      approx(whole_line["p_under"], low_half["p_under"], 1e-9))
# Handicap partition must also be exact on both line types.
for ln in (-3.5, -4.0, 6.5, 7.0):
    hp = price_handicap(0.6, ln, "basketball")
    check(f"handicap {ln} partition sums to 1",
          approx(hp["p_cover"] + hp["p_push"] + hp["p_lose"], 1.0, 2e-4))
check("half-point handicap has zero push",
      approx(price_handicap(0.6, -3.5, "basketball")["p_push"], 0.0, 1e-12))
check("whole-number handicap carries push",
      price_handicap(0.6, -4.0, "basketball")["p_push"] > 0.01)
# Two sides of the same line are complementary once push is shared.
a = price_handicap(0.6, -4.0, "basketball")
b = price_handicap(0.4, +4.0, "basketball")
check("opposite sides of one line mirror",
      approx(a["p_cover"], b["p_lose"], 2e-4) and approx(a["p_push"], b["p_push"], 2e-4))

check("outcome granularity constant", OUTCOME_HALF_WIDTH == 0.5)
check("whole-number push window is outcome granularity not quoting step",
      price_total(215.0, 215.0, 20.0)["p_push"]
      > price_total(215.0, 215.0, 20.0, increment=0.5)["p_push"] - 1e-9)

print("confidence labels")
check("None -> low", confidence_label(None) == "low")
check("official + big edge -> high",
      confidence_label(0.78, "official") == "high")
check("crowd_only can never be high",
      confidence_label(0.99, "crowd_only") != "high")
check("crowd_only big edge -> medium",
      confidence_label(0.90, "crowd_only") == "medium")
check("coin flip -> low", confidence_label(0.5, "official") == "low")
check("partial mid edge -> medium", confidence_label(0.68, "partial") == "medium")
check("monotone in edge (official)",
      confidence_label(0.9, "official") == "high"
      and confidence_label(0.55, "official") == "low")

print("calibration table integrity")
for s, c in SPORT_CALIBRATION.items():
    keys = {"margin_per_prob_point", "margin_sd", "handicap_increment",
            "supports_handicap", "supports_total", "draw_possible",
            "prior_strength_k", "unit"}
    ok = keys.issubset(c.keys()) and c["prior_strength_k"] > 0
    if c["supports_handicap"]:
        ok = ok and c["margin_per_prob_point"] and c["margin_sd"] and c["handicap_increment"]
    check(f"calibration {s}", ok, str(c))
expected_sports = {"basketball", "ice_hockey", "baseball", "rugby_union",
                   "rugby_league", "cricket_t20", "cricket_odi", "volleyball",
                   "handball", "tennis", "golf", "motor_racing", "snooker",
                   "darts", "greyhounds", "gaelic"}
check("all 15 requested sports have a pricing profile",
      expected_sports.issubset(set(SPORT_CALIBRATION)),
      str(expected_sports - set(SPORT_CALIBRATION)))

print()
if FAILS:
    print(f"{len(FAILS)} FAILURES: {FAILS}")
    sys.exit(1)
print("all line engine tests passed")
