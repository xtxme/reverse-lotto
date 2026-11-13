"""Strict walk-forward evaluation of residue, bottom-2 and top-3 forecasts.

The run is retrospective: completed-round rows are truncated synthetically to
simulate what was visible before the close.  It is NOT pre-close evidence.
"""
from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import quote

import numpy as np

import models
import scoring

MODULUS = models.MODULUS
LABELS = {
    "information_set": "RETROSPECTIVE_POST_CLOSE_SIMULATION",
    "note": "Uses final completed-round data with synthetic truncation; not pre-close evidence.",
}
METRIC_KEYS = ("exact_residue", "top5_residue", "top10_residue", "bottom2_exact",
               "bottom2_top5", "top3_exact", "top3_top5")


def _connect_read_only(db_path: str | Path) -> sqlite3.Connection:
    """Open an existing SQLite database without permitting any write."""
    path = Path(db_path).expanduser().resolve()
    connection = sqlite3.connect("file:" + quote(str(path), safe="/") + "?mode=ro", uri=True)
    connection.execute("PRAGMA query_only=ON")
    return connection


def load_rounds(db_path: str | Path) -> list[dict]:
    """Load completed rounds in ``(trading_day, round_number)`` order.

    Numbers follow ``display_sequence``.  Empty or malformed rounds are skipped;
    1..15 valid numbers raise ``ValueError`` because row 16 is required.
    """
    query = """
        SELECT r.trading_day, r.round_number, e.five_digit_number
        FROM rounds AS r
        JOIN submission_events AS e
          ON e.trading_day = r.trading_day AND e.round_number = r.round_number
        WHERE r.result_status = 'COMPLETE'
        ORDER BY r.trading_day, r.round_number, e.display_sequence
    """
    connection = _connect_read_only(db_path)
    try:
        rows = connection.execute(query).fetchall()
    finally:
        connection.close()

    grouped: dict[tuple[str, int], list[Any]] = {}
    for trading_day, round_number, raw_number in rows:
        try:
            key = (str(trading_day), int(round_number))
        except (TypeError, ValueError):
            continue
        grouped.setdefault(key, []).append(raw_number)

    rounds: list[dict] = []
    for trading_day, round_number in sorted(grouped):
        numbers: list[int] = []
        malformed = False
        for raw in grouped[(trading_day, round_number)]:
            text = raw if isinstance(raw, str) else ""
            if len(text) != 5 or not text.isascii() or not text.isdigit():
                malformed = True
                break
            numbers.append(int(text))
        if malformed or not numbers:
            continue
        count = len(numbers)
        if count < 16:
            raise ValueError(f"round {trading_day}/{round_number} has only {count} numbers; at least 16 required")
        residue = (sum(numbers) - numbers[15]) % MODULUS
        assert count == len(numbers)
        rounds.append({
            "trading_day": trading_day, "round_number": round_number,
            "numbers": numbers, "count": count, "residue": residue,
        })
    return rounds


def _mean(total: float, rounds: int) -> float | None:
    return float(total / rounds) if rounds else None


def _rate(hits: int, rounds: int) -> float:
    return float(hits / rounds) if rounds else 0.0


def run(db_path: str | Path, k_values: tuple[int, ...] = (16, 50), min_train: int = 30,
        prior_strength: float = 100.0, delta_prior: float = 20.0, stop_index: int | None = None) -> dict:
    """Run models A (uniform), B (historical) and C_k (conditional delta).

    Target ``i`` trains only on rounds ``[:i]``.  ``stop_index`` evaluates the
    first ``stop_index`` sorted rounds, proving future rows cannot leak backwards.
    """
    if int(min_train) < 0:
        raise ValueError("min_train must be non-negative")
    if float(prior_strength) <= 0.0 or float(delta_prior) <= 0.0:
        raise ValueError("prior strengths must be strictly positive")
    ks: list[int] = []
    for value in k_values:
        k = int(value)
        if k <= 0:
            raise ValueError("k_values must contain positive integers")
        if k not in ks:
            ks.append(k)

    all_rounds = load_rounds(db_path)
    cutoff = len(all_rounds) if stop_index is None else max(0, min(int(stop_index), len(all_rounds)))
    rounds = all_rounds[:cutoff]
    min_train = int(min_train)
    skipped = min(min_train, len(rounds))
    model_names = ["A", "B"] + [f"C_k{k}" for k in ks]
    evaluations: list[dict] = []

    # prefix[j] = numbers[0] + ... + numbers[j]
    prefix_sums = [np.cumsum(np.asarray(r["numbers"], dtype=np.int64)) for r in rounds]
    for i, target in enumerate(rounds):
        if i < min_train:
            continue
        train = rounds[:i]
        target_residue = target["residue"]
        target_bottom2, target_top3 = target_residue // 1000, target_residue % 1000
        distributions = {"A": models.uniform()}

        training_residues = np.fromiter(
            (item["residue"] for item in train), dtype=np.int64, count=len(train))
        counts = np.bincount(training_residues, minlength=MODULUS).astype(np.float64)
        distributions["B"] = models.historical(counts, prior_strength)

        for k in ks:
            name = f"C_k{k}"
            k_effective = min(k, target["count"])
            deltas_by_k: dict[int, list[int]] = {}
            all_deltas: list[int] = []
            for j, training_round in enumerate(train):
                training_k = min(k, training_round["count"])
                delta = (training_round["residue"] - int(prefix_sums[j][training_k - 1])) % MODULUS
                deltas_by_k.setdefault(training_k, []).append(delta)
                all_deltas.append(delta)
            fallback = models.delta_distribution(all_deltas, delta_prior)
            p_delta = models.conditional_delta(deltas_by_k, k_effective, fallback, delta_prior)
            distributions[name] = models.shift(p_delta, int(prefix_sums[i][k_effective - 1]))

        for name, p in distributions.items():
            bottom2, top3 = scoring.marginals(p)
            hits = {
                "exact_residue": scoring.topk_hit(p, target_residue, 1),
                "top5_residue": scoring.topk_hit(p, target_residue, 5),
                "top10_residue": scoring.topk_hit(p, target_residue, 10),
                "bottom2_exact": scoring.topk_hit(bottom2, target_bottom2, 1),
                "bottom2_top5": scoring.topk_hit(bottom2, target_bottom2, 5),
                "top3_exact": scoring.topk_hit(top3, target_top3, 1),
                "top3_top5": scoring.topk_hit(top3, target_top3, 5),
            }
            evaluations.append({
                "index": i, "day": target["trading_day"], "model": name,
                "loss": scoring.log_loss(p, target_residue),
                "brier": scoring.brier(p, target_residue),
                "p_y": float(p[target_residue]), "hits": hits,
                "confidence": float(p.max()), "top1_hit": bool(int(np.argmax(p)) == target_residue),
                "k_effective": min(k, target["count"]) if name.startswith("C_k") else None,
            })

    def stats_for(events: list[dict]) -> dict:
        n = len(events)
        return {
            "rounds": n,
            "mean_log_loss": _mean(sum(e["loss"] for e in events), n),
            "mean_brier": _mean(sum(e["brier"] for e in events), n),
            **{metric: _rate(sum(int(e["hits"][metric]) for e in events), n) for metric in METRIC_KEYS},
            "calibration": scoring.confidence_calibration([e["confidence"] for e in events],
                                                          [e["top1_hit"] for e in events], 10),
            "mean_confidence": _mean(sum(e["confidence"] for e in events), n),
            "top1_hit_rate": _rate(sum(1 for e in events if e["top1_hit"]), n),
            "skipped": skipped,
        }

    report_models: dict[str, dict] = {}
    for name in model_names:
        events = [e for e in evaluations if e["model"] == name]
        report_models[name] = stats_for(events)
        if name.startswith("C_k"):
            report_models[name]["k_effective"] = dict(sorted(Counter(
                e["k_effective"] for e in events if e["k_effective"] is not None).items()))

    per_day: list[dict] = []
    for day in sorted({e["day"] for e in evaluations}):
        day_events = [e for e in evaluations if e["day"] == day]
        models_for_day = {}
        for name in model_names:
            events = [e for e in day_events if e["model"] == name]
            n = len(events)
            models_for_day[name] = {
                "mean_log_loss": _mean(sum(e["loss"] for e in events), n),
                "exact_residue": _rate(sum(int(e["hits"]["exact_residue"]) for e in events), n),
                "bottom2_exact": _rate(sum(int(e["hits"]["bottom2_exact"]) for e in events), n),
                "top3_exact": _rate(sum(int(e["hits"]["top3_exact"]) for e in events), n),
            }
        per_day.append({"trading_day": day, "rounds": len({e["index"] for e in day_events}),
                        "models": models_for_day})

    losses = {name: [e["loss"] for e in evaluations if e["model"] == name] for name in model_names}
    baseline = losses["A"]
    paired_vs_A: dict[str, dict] = {}
    for name in model_names:
        differences = [base - other for base, other in zip(baseline, losses[name])]
        paired_vs_A[name] = {
            "rounds": len(differences),
            "log_loss_improvement_mean": float(np.mean(differences)) if differences else None,
            "rounds_better": int(sum(1 for value in differences if value > 0.0)),
            "rounds_worse": int(sum(1 for value in differences if value < 0.0)),
        }

    days = sorted({r["trading_day"] for r in rounds})
    return {
        "labels": dict(LABELS),
        "data": {"rounds": len(rounds), "days": len(days),
                 "first_day": days[0] if days else None,
                 "last_day": days[-1] if days else None},
        "models": report_models,
        "per_day": per_day,
        "paired_vs_A": paired_vs_A,
    }
