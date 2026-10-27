"""Unit tests for the line-origination maths and the prose guard rails."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pricing as P  # noqa: E402
import write as W  # noqa: E402


class OddsConversion(unittest.TestCase):
    def test_american_decimal_round_trip(self):
        for am in (-250, -130, -105, 100, 125, 450, 10000):
            dec = P.american_to_decimal(am)
            self.assertAlmostEqual(P.decimal_to_american(dec), am, delta=1)

    def test_decimal_edge_cases(self):
        self.assertAlmostEqual(P.american_to_decimal(100), 2.0)
        self.assertAlmostEqual(P.american_to_decimal(-100), 2.0)
        with self.assertRaises(ValueError):
            P.decimal_to_american(1.0)


class Devig(unittest.TestCase):
    def test_two_way_sums_to_one(self):
        fair = P.devig_power([1.77, 2.25])
        self.assertAlmostEqual(sum(fair), 1.0, places=12)
        self.assertGreater(fair[0], fair[1])

    def test_favourite_shrinks_less_than_longshot(self):
        decs = [1.10, 8.00]
        fair = P.devig_power(decs)
        raw = [1 / d for d in decs]
        fav_drop = raw[0] - fair[0]
        dog_drop = raw[1] - fair[1]
        self.assertLess(fav_drop, dog_drop)

    def test_single_selection_market(self):
        self.assertEqual(P.devig_power([1.5]), [1.0])

    def test_multi_runner_sums_to_one(self):
        decs = [4.5, 5.5, 7.5, 10.0, 12.0, 16.0, 21.0, 26.0]
        fair = P.devig_power(decs)
        self.assertAlmostEqual(sum(fair), 1.0, places=10)
        self.assertTrue(all(p < 1 for p in fair))

    def test_fair_board_prices(self):
        board = P.fair_board([{"selection": "A", "decimal": 1.77}, {"selection": "B", "decimal": 2.25}], "tennis")
        self.assertEqual(len(board), 2)
        self.assertTrue(all(b["fair_prob"] > 0 for b in board))
        self.assertLess(abs(board[0]["fair_american"] - P.decimal_to_american(board[0]["fair_decimal"])), 1)


class Windows(unittest.TestCase):
    def test_price_window_bounds(self):
        self.assertTrue(P.in_price_window(-250))
        self.assertFalse(P.in_price_window(-251))
        self.assertTrue(P.in_price_window(10000))
        self.assertFalse(P.in_price_window(10001))

    def test_confidence_bands(self):
        self.assertEqual(P.confidence_band(0.70), "high")
        self.assertEqual(P.confidence_band(0.699), "medium")
        self.assertEqual(P.confidence_band(0.60), "medium")
        self.assertEqual(P.confidence_band(0.599), "low")


class Tilts(unittest.TestCase):
    def test_tilt_is_capped(self):
        strong = {"l10_pct": 1.0, "point_pct": 1.0, "diff_per_game": 9.0, "pct": 1.0}
        weak = {"l10_pct": 0.0, "point_pct": 0.0, "diff_per_game": -9.0, "pct": 0.0}
        self.assertLessEqual(P.form_tilt(strong, weak, "ice-hockey"), 0.035)
        self.assertGreaterEqual(P.form_tilt(weak, strong, "ice-hockey"), -0.035)

    def test_missing_data_gives_no_tilt(self):
        self.assertEqual(P.form_tilt({}, {}, "baseball"), 0.0)

    def test_apply_tilt_keeps_probabilities_valid(self):
        out = P.apply_tilt([0.55, 0.45], 0.03)
        self.assertAlmostEqual(sum(out), 1.0, places=12)
        self.assertGreater(out[0], 0.55)


class CoverMaths(unittest.TestCase):
    def test_cover_probability_symmetry(self):
        self.assertAlmostEqual(P.cover_probability(0.0, 0.0, 2.35), 0.5, places=9)

    def test_cover_probability_favourite_line(self):
        # a team expected to win by 1.5 laying -1.5 should cover about half the time
        self.assertAlmostEqual(P.cover_probability(1.5, -1.5, 2.35), 0.5, places=9)
        self.assertGreater(P.cover_probability(2.5, -1.5, 2.35), 0.5)


class Prose(unittest.TestCase):
    def test_never_emits_banned_words(self):
        p = {
            "id": "x-1", "sport": "ice-hockey", "event_name": "A vs B", "competition": "NHL",
            "start_utc": "2026-10-27T23:00:00Z", "home": "A", "away": "B", "selection": "A",
            "market": "Money Line", "price_american": -180, "our_prob": 0.65, "market_implied": 0.643,
            "edge_pts": 0.7, "confidence": "medium", "official_confirmed": False,
            "home_table": {"wins": 5, "losses": 3, "points": 10, "goal_for": 20, "goal_against": 15,
                           "goal_diff": 5, "games_played": 8, "l10": {"w": 6, "l": 2}},
            "away_table": {"wins": 4, "losses": 4, "points": 8, "goal_for": 18, "goal_against": 18,
                           "goal_diff": 0, "games_played": 8, "l10": {"w": 4, "l": 4}},
        }
        text = W.build_prediction(p, facts_available=True)
        self.assertGreaterEqual(W.word_count(text), 30)
        for bad in ("model", "verified"):
            self.assertNotIn(bad, text.lower())
        self.assertTrue(text[0].isupper())

    def test_missing_data_produces_no_claims(self):
        p = {"id": "y-1", "sport": "tennis", "event_name": "A vs B", "competition": "",
             "start_utc": "2026-10-27T10:00:00Z", "home": "A", "away": "B", "selection": "A",
             "market": "Win Match", "price_american": -150, "our_prob": 0.60,
             "market_implied": 0.59, "edge_pts": 1.0, "confidence": "medium",
             "official_confirmed": False}
        text = W.build_prediction(p, facts_available=False)
        self.assertNotIn("98-64", text)
        self.assertGreaterEqual(W.word_count(text), 30)


if __name__ == "__main__":
    unittest.main()
