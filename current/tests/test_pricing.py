import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pricing import pythagorean, log5, american

class PricingTests(unittest.TestCase):
    def test_reproducible_reference(self):
        p = log5(pythagorean(832, 618), pythagorean(736, 650))
        self.assertAlmostEqual(p, .585689102550563)
        self.assertEqual(american(p), -141)
        self.assertEqual(american(1-p), 141)
        self.assertAlmostEqual(log5(.6, .6), .5)
    def test_reject_invalid_inputs(self):
        with self.assertRaises(ValueError): pythagorean(0, 100)
        with self.assertRaises(ValueError): log5(1, .5)
        with self.assertRaises(ValueError): american(0)
