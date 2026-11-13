"""Unit tests for models, scoring and strict walk-forward evaluation."""
from __future__ import annotations

import math
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import models
import scoring
import walkforward

M = models.MODULUS


def point_mass(index: int) -> np.ndarray:
    dist = np.zeros(M, dtype=np.float64)
    dist[index] = 1.0
    return dist


def numbers_for(round_index: int, count: int) -> list[int]:
    """Deterministic synthetic submission list, count in [16, 60]."""
    return [
        (round_index * 7919 + sequence * 104729 + 12345) % M
        for sequence in range(count)
    ]


def create_db(path: Path, n_rounds: int = 40) -> list[dict]:
    """Create a minimal Phase-D-shaped database with synthetic completed rounds."""
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE rounds (
            trading_day TEXT NOT NULL,
            round_number INTEGER NOT NULL,
            result_status TEXT NOT NULL DEFAULT 'PENDING',
            PRIMARY KEY (trading_day, round_number)
        );
        CREATE TABLE submission_events (
            trading_day TEXT NOT NULL,
            round_number INTEGER NOT NULL,
            display_sequence INTEGER NOT NULL,
            five_digit_number TEXT NOT NULL,
            PRIMARY KEY (trading_day, round_number, display_sequence)
        );
        """
    )
    appended: list[dict] = []
    for index in range(n_rounds):
        trading_day = f"2026-01-{index // 10 + 1:02d}"
        round_number = index % 10 + 1
        count = 16 + (index * 7) % 45
        numbers = numbers_for(index, count)
        connection.execute(
            "INSERT INTO rounds VALUES (?, ?, 'COMPLETE')",
            (trading_day, round_number),
        )
        connection.executemany(
            "INSERT INTO submission_events VALUES (?, ?, ?, ?)",
            [
                (trading_day, round_number, position + 1, f"{number:05d}")
                for position, number in enumerate(numbers)
            ],
        )
        appended.append(
            {
                "trading_day": trading_day,
                "round_number": round_number,
                "numbers": numbers,
                "count": count,
                "residue": (sum(numbers) - numbers[15]) % M,
            }
        )
    connection.commit()
    connection.close()
    return appended


def append_round(path: Path, trading_day: str, round_number: int, numbers: list[int]) -> None:
    connection = sqlite3.connect(path)
    connection.execute(
        "INSERT INTO rounds VALUES (?, ?, 'COMPLETE')",
        (trading_day, round_number),
    )
    connection.executemany(
        "INSERT INTO submission_events VALUES (?, ?, ?, ?)",
        [
            (trading_day, round_number, position + 1, f"{number:05d}")
            for position, number in enumerate(numbers)
        ],
    )
    connection.commit()
    connection.close()


class ScoringTests(unittest.TestCase):
    def test_uniform_log_loss_brier_and_topk(self):
        p = models.uniform()
        self.assertEqual(p.shape, (M,))
        self.assertEqual(p.dtype, np.float64)
        self.assertAlmostEqual(float(p.sum()), 1.0, places=12)
        self.assertAlmostEqual(scoring.log_loss(p, 12345), math.log(M), places=9)
        self.assertAlmostEqual(scoring.brier(p, 12345), 1.0 - 1.0 / M, places=9)
        self.assertTrue(scoring.topk_hit(p, 0, 5))
        self.assertIsInstance(scoring.topk_hit(p, 0, 5), bool)
        self.assertFalse(scoring.topk_hit(p, 0, 0))
        # Uniform ties at the cutoff are resolved by ascending index.
        self.assertTrue(scoring.topk_hit(p, 4, 5))
        self.assertFalse(scoring.topk_hit(p, 5, 5))
        self.assertTrue(scoring.topk_hit(p, M - 1, M))

        peaked = np.zeros(M, dtype=np.float64)
        peaked[[9, 7, 123]] = [0.3, 0.5, 0.2]
        self.assertTrue(scoring.topk_hit(peaked, 7, 1))
        self.assertTrue(scoring.topk_hit(peaked, 9, 2))
        self.assertFalse(scoring.topk_hit(peaked, 123, 1))
        self.assertFalse(scoring.topk_hit(peaked, 123, 2))
        self.assertTrue(scoring.topk_hit(peaked, 123, 3))

        tied = np.zeros(M, dtype=np.float64)
        tied[[8, 5]] = [0.5, 0.5]
        self.assertTrue(scoring.topk_hit(tied, 5, 1))
        self.assertFalse(scoring.topk_hit(tied, 8, 1))
        self.assertTrue(scoring.topk_hit(tied, 8, 2))

    def test_probability_validation(self):
        with self.assertRaises(ValueError):
            scoring.log_loss(np.ones(10), 0)
        with self.assertRaises(ValueError):
            scoring.brier(np.full(M, 0.5), 0)
        with self.assertRaises(ValueError):
            scoring.topk_hit(np.full(M, 0.5), 0, 5)
        with self.assertRaises(ValueError):
            scoring.marginals(np.ones(10))

    def test_shift_moves_delta_mass_to_result(self):
        delta = point_mass(7)
        shifted = models.shift(delta, 99995)
        self.assertEqual(np.flatnonzero(shifted).tolist(), [2])
        self.assertAlmostEqual(float(shifted[2]), 1.0, places=12)
        self.assertAlmostEqual(float(shifted.sum()), 1.0, places=12)
        self.assertAlmostEqual(float((99995 + 7) % M), 2.0)

    def test_marginals_of_single_residue(self):
        bottom2, top3 = scoring.marginals(point_mass(12345))
        self.assertEqual(bottom2.shape, (100,))
        self.assertEqual(top3.shape, (1000,))
        self.assertEqual(bottom2[12], 1.0)
        self.assertEqual(top3[345], 1.0)
        self.assertAlmostEqual(float(bottom2.sum()), 1.0, places=12)
        self.assertAlmostEqual(float(top3.sum()), 1.0, places=12)
        self.assertEqual(int(np.count_nonzero(bottom2)), 1)
        self.assertEqual(int(np.count_nonzero(top3)), 1)

    def test_point_mass_losses(self):
        right = point_mass(777)
        self.assertAlmostEqual(scoring.log_loss(right, 777), 0.0, places=12)
        self.assertAlmostEqual(scoring.brier(right, 777), 0.0, places=12)
        wrong = point_mass(778)
        self.assertGreater(scoring.log_loss(wrong, 777), 20.0)
        self.assertAlmostEqual(scoring.brier(wrong, 777), 2.0, places=12)

    def test_calibration_table(self):
        table = scoring.calibration([0.05, 0.15, 0.95, 1.0], n_bins=10)
        self.assertEqual(len(table), 10)
        self.assertEqual(sum(entry["n"] for entry in table), 4)
        self.assertAlmostEqual(sum(entry["observed_rate"] for entry in table), 1.0, places=12)
        self.assertTrue(all({"lo", "hi", "n", "mean_predicted", "observed_rate"} <= set(entry) for entry in table))
        top_bin = table[-1]
        self.assertEqual(top_bin["n"], 2)
        self.assertAlmostEqual(top_bin["mean_predicted"], 0.975, places=12)


class ModelTests(unittest.TestCase):
    def test_historical_smoothing(self):
        counts = np.zeros(M, dtype=np.float64)
        counts[5] = 10.0
        counts[9] = 3.0
        prior = 100.0
        dist = models.historical(counts, prior_strength=prior)
        self.assertAlmostEqual(float(dist.sum()), 1.0, places=12)
        self.assertTrue(bool(np.all(dist > 0.0)))
        expected_zero = (prior / M) / (13.0 + prior)
        self.assertAlmostEqual(float(dist[0]), expected_zero, places=15)
        self.assertAlmostEqual(float(dist[5]), (10.0 + prior / M) / (13.0 + prior), places=15)

    def test_delta_distribution_counts_modulus(self):
        dist = models.delta_distribution([7, 7, 100007], prior_strength=20.0)
        self.assertAlmostEqual(float(dist.sum()), 1.0, places=12)
        self.assertAlmostEqual(float(dist[7]), (3.0 + 20.0 / M) / (3.0 + 20.0), places=15)
        self.assertEqual(int(np.argmax(dist)), 7)
        self.assertAlmostEqual(float(dist[0]), (20.0 / M) / (3.0 + 20.0), places=15)

    def test_conditional_delta_fallback_and_full_use(self):
        fallback = np.full(M, 1.0 / M, dtype=np.float64)
        same = models.conditional_delta({16: []}, 16, fallback, prior_strength=20.0)
        np.testing.assert_allclose(same, fallback)
        np.testing.assert_allclose(
            models.conditional_delta({}, 16, fallback, prior_strength=20.0), fallback
        )

        deltas = [7] * 29
        mixed = models.conditional_delta({16: deltas}, 16, fallback, prior_strength=20.0)
        specific = models.delta_distribution(deltas, prior_strength=20.0)
        expected = (29.0 / 59.0) * specific + (30.0 / 59.0) * fallback
        np.testing.assert_allclose(mixed, expected)
        self.assertAlmostEqual(float(mixed.sum()), 1.0, places=12)

        full = models.conditional_delta({16: [7] * 30}, 16, fallback, prior_strength=20.0)
        np.testing.assert_allclose(full, models.delta_distribution([7] * 30, prior_strength=20.0))
        self.assertEqual(int(np.argmax(full)), 7)
        self.assertGreater(float(full[7]), 0.5)


class WalkForwardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "phase_d.sqlite3"
        self.rows = create_db(self.db_path, 40)

    def tearDown(self):
        self.temp.cleanup()

    def test_load_rounds_uses_display_order_and_formula(self):
        loaded = walkforward.load_rounds(self.db_path)
        self.assertEqual(len(loaded), 40)
        self.assertEqual(
            [(r["trading_day"], r["round_number"]) for r in loaded],
            sorted((r["trading_day"], r["round_number"]) for r in loaded),
        )
        for record, expected in zip(loaded, self.rows):
            self.assertEqual(record["numbers"], expected["numbers"])
            self.assertEqual(record["count"], expected["count"])
            self.assertEqual(record["count"], len(record["numbers"]))
            self.assertEqual(
                record["residue"],
                (sum(record["numbers"]) - record["numbers"][15]) % M,
            )

    def test_future_rows_cannot_change_past_metrics(self):
        truncated = walkforward.run(self.db_path, k_values=(16, 50), min_train=30)
        self.assertEqual(truncated["data"]["rounds"], 40)
        self.assertEqual(truncated["data"]["days"], 4)
        self.assertEqual(sorted(truncated["models"]), ["A", "B", "C_k16", "C_k50"])
        for stats in truncated["models"].values():
            self.assertEqual(stats["rounds"], 10)
            self.assertEqual(stats["skipped"], 30)
            self.assertEqual(len(stats["calibration"]), 10)
        self.assertEqual(sum(day["rounds"] for day in truncated["per_day"]), 10)
        for day in truncated["per_day"]:
            self.assertEqual(set(day["models"]), set(truncated["models"]))
            for stats in day["models"].values():
                self.assertEqual(set(stats), {"mean_log_loss", "exact_residue",
                                              "bottom2_exact", "top3_exact"})
        for stats in truncated["paired_vs_A"].values():
            self.assertEqual(set(stats), {"rounds", "log_loss_improvement_mean",
                                          "rounds_better", "rounds_worse"})

        append_round(self.db_path, "2026-01-05", 1, [99999] + [0] * 59)
        full = walkforward.run(self.db_path, k_values=(16, 50), min_train=30)
        prefix = walkforward.run(self.db_path, k_values=(16, 50), min_train=30, stop_index=40)

        self.assertEqual(full["data"]["rounds"], 41)
        self.assertEqual(full["models"]["A"]["rounds"], 11)
        # The truncated prefix must be identical; no future row leaks backwards.
        self.assertEqual(prefix, truncated)

        loaded = walkforward.load_rounds(self.db_path)
        self.assertEqual(loaded[-1]["residue"], 99999)
        self.assertEqual(full["data"]["days"], 5)

    def test_invalid_short_round_raises(self):
        append_round(self.db_path, "2026-01-06", 1, [1, 2, 3])
        with self.assertRaises(ValueError):
            walkforward.load_rounds(self.db_path)


if __name__ == "__main__":
    unittest.main()
