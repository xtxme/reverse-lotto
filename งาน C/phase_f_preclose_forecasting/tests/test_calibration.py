import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import scoring


class CalibrationTests(unittest.TestCase):
    def test_confidence_bins_match_observed_hit_rate(self):
        confidences = [0.05, 0.15, 0.15, 0.95]
        hits = [False, False, True, True]
        table = scoring.confidence_calibration(confidences, hits, n_bins=10)
        self.assertEqual(len(table), 10)
        first = table[0]
        second = table[1]
        last = table[9]
        self.assertEqual(first['n'], 1)
        self.assertAlmostEqual(first['mean_predicted'], 0.05)
        self.assertAlmostEqual(first['observed_rate'], 0.0)
        self.assertEqual(second['n'], 2)
        self.assertAlmostEqual(second['mean_predicted'], 0.15)
        self.assertAlmostEqual(second['observed_rate'], 0.5)
        self.assertEqual(last['n'], 1)
        self.assertAlmostEqual(last['observed_rate'], 1.0)
        self.assertEqual(sum(b['n'] for b in table), 4)

    def test_confidence_calibration_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            scoring.confidence_calibration([1.2], [True])
        with self.assertRaises(ValueError):
            scoring.confidence_calibration([0.5], [True, False])

    def test_marginals_of_point_mass(self):
        p = np.zeros(100000)
        p[12345] = 1.0
        bottom2, top3 = scoring.marginals(p)
        self.assertAlmostEqual(bottom2[12], 1.0)
        self.assertAlmostEqual(top3[345], 1.0)
        self.assertAlmostEqual(float(bottom2.sum()), 1.0)
        self.assertAlmostEqual(float(top3.sum()), 1.0)


if __name__ == '__main__':
    unittest.main()
