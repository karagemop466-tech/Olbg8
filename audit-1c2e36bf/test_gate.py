#!/usr/bin/env python3
"""Offline tests for the review gate. All candidate records here are synthetic."""
import copy
from datetime import datetime, timedelta, timezone
import unittest

from gate import (american_to_decimal, assess, assess_all, decimal_to_american,
                  expected_net, fair_decimal, parse_utc, valid_american, valid_url)

NOW = datetime(2026, 10, 27, 6, 0, tzinfo=timezone.utc)


def candidate():
    # Example data are deliberately fictitious and are never published as picks.
    sources = []
    for role in ("event", "form", "match_history", "statistic", "availability"):
        sources.append({"id": role, "scope": role, "event_id": "example-1", "reviewed": True,
                        "url": "https://www.cricket.com.au/matches/example",
                        "observed_utc": "2026-10-27T05:45:00Z", "excerpt": "Synthetic test assertion."})
    market = {"name": "Win Match", "selection": "Team A", "status": "offered",
              "offered_american": -150, "observed_utc": "2026-10-27T05:45:00Z",
              "source_id": "market", "settlement": "win_loss", "period": "full_event",
              "rules_note": "Synthetic example, match result only."}
    sources.append({"id": "market", "scope": "market", "event_id": "example-1", "reviewed": True,
                    "url": "https://www.olbg.com/betting-tips/Cricket/7?event_id=example-1",
                    "excerpt": "Synthetic test quote.",
                    **{k: market[k] for k in ("name", "selection", "status", "offered_american", "observed_utc")}})
    return {"id": "example-1", "sport": "cricket",
            "event": {"id": "example-1", "name": "Team A vs Team B", "start_utc": "2026-10-27T10:00:00Z"},
            "market": market, "sources": sources,
            "claim_sources": {role: role for role in ("event", "form", "match_history", "statistic", "availability")},
            "material_availability_reviewed": True,
            "analysis": ("Team A to win is the synthetic example selection for this test. These sample words describe "
                         "recent performances, a previous meeting, a relevant statistic and assessed availability, while "
                         "making clear that this text is not a real sporting prediction."),
            "pricing": {"win_probability": 0.6, "push_probability": 0.0, "fair_american": -150,
                        "method": "Synthetic formula for testing only", "independent_from_tip_shares": True,
                        "input_source_ids": ["form", "statistic"], "confidence": "medium",
                        "confidence_basis": "Synthetic evidence-quality example",
                        "calibration": {"reviewed": True, "artifact_url": "https://example.org/evaluation",
                                        "sample_size": 10, "brier_score": 0.2,
                                        "train_end_utc": "2026-01-01T00:00:00Z",
                                        "holdout_start_utc": "2026-01-02T00:00:00Z",
                                        "holdout_end_utc": "2026-10-26T00:00:00Z"}}}


class ArithmeticTests(unittest.TestCase):
    def test_american_boundaries(self):
        for n in (-250, -100, 100, 10000):
            self.assertTrue(valid_american(n))
        for n in (-99, 0, 99, True, -150.0, float("nan")):
            self.assertFalse(valid_american(n))
        self.assertAlmostEqual(american_to_decimal(-250), 1.4)
        self.assertAlmostEqual(american_to_decimal(10000), 101.0)
        self.assertEqual(decimal_to_american(2.0), 100)
        with self.assertRaises(ValueError):
            american_to_decimal(-99)

    def test_push_refunds_and_expected_return(self):
        self.assertAlmostEqual(fair_decimal(0.5, 0.1), 1.8)
        self.assertEqual(decimal_to_american(fair_decimal(0.5, 0.1)), -125)
        self.assertAlmostEqual(expected_net(0.5, 0.1, 2.0), 0.1)
        with self.assertRaises(ValueError):
            fair_decimal(0.7, 0.3)
        with self.assertRaises(ValueError):
            fair_decimal(float("nan"), 0)

    def test_time_and_urls(self):
        self.assertIsNone(parse_utc("2026-10-27T06:00:00"))
        self.assertEqual(parse_utc("2026-10-27T02:00:00-04:00"), NOW)
        self.assertTrue(valid_url("https://api-web.nhle.com/v1/score", ("nhle.com",)))
        self.assertFalse(valid_url("https://nhle.com.attacker.invalid/", ("nhle.com",)))
        self.assertFalse(valid_url("https://nhle.com@attacker.invalid/", ("nhle.com",)))
        self.assertFalse(valid_url("http://www.olbg.com/", ("olbg.com",)))


class GateTests(unittest.TestCase):
    def test_complete_test_schema(self):
        self.assertEqual(assess(candidate(), NOW), [])
        self.assertEqual(assess_all([candidate()], NOW)[0]["status"], "reviewed_schema_only")

    def test_incomplete_real_world_like_row_is_withheld(self):
        result = assess({"id": "legacy", "sport": "cricket", "analysis": "India"}, NOW)
        for code in ("missing_event_evidence", "missing_availability_evidence", "missing_or_unzoned_start",
                     "offer_not_confirmed", "missing_or_invalid_offered_odds", "missing_out_of_sample_calibration"):
            self.assertIn(code, result)

    def test_offer_boundaries_and_source_must_agree(self):
        for odds in (-250, 100, 10000):
            c = candidate(); c["market"]["offered_american"] = odds; c["sources"][-1]["offered_american"] = odds
            self.assertNotIn("offered_odds_outside_window", assess(c, NOW))
        for odds in (-251, 10001):
            c = candidate(); c["market"]["offered_american"] = odds; c["sources"][-1]["offered_american"] = odds
            self.assertIn("offered_odds_outside_window", assess(c, NOW))
        c = candidate(); c["market"]["offered_american"] = -120
        self.assertIn("market_capture_mismatch", assess(c, NOW))
        c["market"]["source_id"] = []
        self.assertIn("missing_olbg_market_evidence", assess(c, NOW))

    def test_stale_future_and_started(self):
        c = candidate(); c["market"]["observed_utc"] = "2026-10-27T01:59:59Z"; c["sources"][-1]["observed_utc"] = c["market"]["observed_utc"]
        self.assertIn("stale_quote", assess(c, NOW))
        c["market"]["observed_utc"] = "2026-10-27T02:00:00Z"; c["sources"][-1]["observed_utc"] = c["market"]["observed_utc"]
        self.assertNotIn("stale_quote", assess(c, NOW))
        c["market"]["observed_utc"] = "2026-10-27T06:00:01Z"
        self.assertIn("invalid_quote_time", assess(c, NOW))
        c = candidate(); c["event"]["start_utc"] = "2026-10-27T06:00:00Z"
        self.assertIn("event_started_or_expired", assess(c, NOW))

    def test_source_scope_and_official_boundary(self):
        c = candidate(); c["sources"][0]["url"] = "https://www.cricket.com.au.evil.invalid/matches/1"
        self.assertIn("missing_event_evidence", assess(c, NOW))
        c = candidate(); c["sources"][1]["event_id"] = "different-match"
        self.assertIn("missing_form_evidence", assess(c, NOW))
        c = candidate(); c["claim_sources"]["event"] = []
        self.assertIn("missing_event_evidence", assess(c, NOW))
        c = candidate(); c["sources"][0]["excerpt"] = ""
        self.assertIn("missing_event_evidence", assess(c, NOW))
        c = candidate(); c["material_availability_reviewed"] = False
        self.assertIn("availability_not_assessed", assess(c, NOW))

    def test_no_evaluation_leakage(self):
        c = candidate(); c["pricing"]["calibration"]["holdout_start_utc"] = "2026-01-01T00:00:00Z"
        self.assertIn("missing_out_of_sample_calibration", assess(c, NOW))
        c = candidate(); c["pricing"]["calibration"]["holdout_end_utc"] = "2026-10-28T00:00:00Z"
        self.assertIn("missing_out_of_sample_calibration", assess(c, NOW))
        c = candidate(); c["pricing"]["independent_from_tip_shares"] = False
        self.assertIn("independent_pricing_not_recorded", assess(c, NOW))
        c = candidate(); c["pricing"]["input_source_ids"] = [{}]
        self.assertIn("unreviewed_pricing_input", assess(c, NOW))

    def test_settlement_and_probability(self):
        c = candidate(); c["market"]["settlement"] = "win_push_loss"
        c["pricing"].update(win_probability=0.5, push_probability=0.1, fair_american=-125)
        self.assertEqual(assess(c, NOW), [])
        c["pricing"]["fair_american"] = 100
        self.assertIn("fair_price_mismatch", assess(c, NOW))
        c["market"]["settlement"] = "win_loss"
        self.assertIn("push_in_win_loss_market", assess(c, NOW))
        c = candidate(); c["pricing"]["win_probability"] = float("inf")
        self.assertIn("invalid_probability_or_push", assess(c, NOW))

    def test_analysis_uniqueness_and_word_ban(self):
        a = candidate(); b = copy.deepcopy(a); b["id"] = "example-2"
        both = assess_all([a, b], NOW)
        self.assertTrue(all("duplicate_analysis" in row["reasons"] for row in both))
        a["analysis"] += " Verified."
        self.assertIn("banned_word_in_analysis", assess(a, NOW))
        a["analysis"] = "Team A wins."
        self.assertIn("short_analysis", assess(a, NOW))

    def test_defensive_arguments(self):
        with self.assertRaises(ValueError):
            assess(candidate(), datetime(2026, 10, 27, 6, 0))
        with self.assertRaises(ValueError):
            assess(candidate(), NOW, timedelta(0))
        self.assertEqual(assess(None, NOW), ["candidate_not_object"])


if __name__ == "__main__":
    unittest.main()
