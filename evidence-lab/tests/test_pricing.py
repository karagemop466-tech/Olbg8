import math
import unittest
from scripts.pricing import *
class PricingTests(unittest.TestCase):
    def test_odds(self):
        self.assertAlmostEqual(american_to_decimal(-250),1.4)
        self.assertEqual(american_to_decimal(10000),101)
        self.assertEqual(fair_odds(.5)['decimal'],2)
        self.assertAlmostEqual(fair_odds(.75)['american'],-300)
    def test_invalid_odds(self):
        for x in [0,99,-99,float('nan'),True,'100']:
            with self.assertRaises(ValueError):american_to_decimal(x)
    def test_eligibility(self):
        for x in [-250,-100,100,10000]:self.assertTrue(eligible_odds(x))
        for x in [-251,10001]:self.assertFalse(eligible_odds(x))
    def test_market_benchmark(self):
        probs=no_vig([-110,-110]);self.assertEqual(probs,[.5,.5])
    def test_return(self):
        self.assertAlmostEqual(expected_return(.6,0,100),.2)
        self.assertAlmostEqual(expected_return(.4,.2,100),0)
    def test_refunded_push(self):
        self.assertAlmostEqual(fair_odds(.4,.2)['decimal'],2)
    def test_bad_probability(self):
        for x in [0,1,-.5,float('inf'),True]:
            with self.assertRaises(ValueError):fair_odds(x)
    def test_series_normalization(self):
        for p in [.1,.5,.9]:
            for target in [1,3,6,10,18]:self.assertAlmostEqual(sum(first_to(p,target).values()),1)
    def test_series_symmetry(self):
        s=first_to(.5,3);self.assertAlmostEqual(sum(v for (h,a),v in s.items() if h>a),.5)
    def test_series_target(self):
        for x in [0,101,True,2.5]:
            with self.assertRaises(ValueError):first_to(.5,x)
    def test_poisson(self):
        scores=poisson_scores(3,2);self.assertAlmostEqual(sum(scores.values()),1)
        self.assertAlmostEqual(sum(h*p for (h,a),p in scores.items()),3)
    def test_tail_rejected(self):
        with self.assertRaises(ValueError):poisson_scores(10,10,10)
    def test_market_settlement(self):
        s={(2,1):.4,(1,1):.2,(0,1):.4}
        self.assertEqual(settle_scores(s,'regulation_1x2'),{'home':.4,'draw':.2,'away':.4})
        self.assertEqual(settle_scores(s,'handicap',0),{'win':.4,'push':.2,'loss':.4})
        self.assertEqual(settle_scores(s,'total',2),{'win':.4,'push':.2,'loss':.4})
    def test_no_unknown_settlement(self):
        with self.assertRaises(ValueError):settle_scores({(1,0):1},'winner')
        with self.assertRaises(ValueError):settle_scores({(1,0):.9},'total',1.5)
    def test_field(self):
        r=race_order({'a':0,'b':0},{'a':1,'b':1},1000)
        self.assertEqual(r,race_order({'a':0,'b':0},{'a':1,'b':1},1000))
        for a in r.values():self.assertAlmostEqual(sum(a),1)
        self.assertAlmostEqual(sum(a[0] for a in r.values()),1)
    def test_incomplete_field(self):
        with self.assertRaises(ValueError):race_order({'a':0,'b':0},{'a':1})
