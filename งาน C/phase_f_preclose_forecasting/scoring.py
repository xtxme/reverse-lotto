"""Proper scoring rules and diagnostics for residue distributions."""
from __future__ import annotations

import math

import numpy as np

from models import MODULUS

_SUM_TOL = 1e-6


def _validate_probability_vector(p: np.ndarray, name: str = "p") -> np.ndarray:
    """Validate a one-dimensional probability vector and return it as float64."""
    arr = np.asarray(p, dtype=np.float64)
    if arr.ndim != 1 or arr.size == 0:
        raise ValueError(f"{name} must be a non-empty 1-D vector")
    if not np.all(np.isfinite(arr)) or np.any(arr < 0.0):
        raise ValueError(f"{name} must be finite and non-negative")
    if not np.isclose(float(arr.sum()), 1.0, rtol=0.0, atol=_SUM_TOL):
        raise ValueError(f"{name} must sum to 1")
    return arr


def _target(y: int, size: int) -> int:
    index = int(y)
    if index < 0 or index >= size:
        raise ValueError(f"target {index} is outside [0, {size})")
    return index


def log_loss(p: np.ndarray, y: int, floor: float = 1e-9) -> float:
    """Negative log probability assigned to the realized class."""
    if floor <= 0.0:
        raise ValueError("floor must be strictly positive")
    dist = _validate_probability_vector(p)
    return float(-math.log(max(float(dist[_target(y, dist.size)]), floor)))


def brier(p: np.ndarray, y: int) -> float:
    """Brier score ``sum(p*p) - 2*p[y] + 1`` for a single realized class."""
    dist = _validate_probability_vector(p)
    index = _target(y, dist.size)
    return float(np.sum(dist * dist) - 2.0 * dist[index] + 1.0)


def topk_hit(p: np.ndarray, y: int, k: int) -> bool:
    """Whether ``y`` is in the top ``k`` entries of ``p``.

    Uses ``np.argpartition``.  Ties at the cutoff are resolved by ascending
    index: entries strictly above the cutoff first, then equal values in index
    order.  ``k <= 0`` returns ``False``; ``k >= len(p)`` returns ``True``.
    """
    dist = _validate_probability_vector(p)
    index = _target(y, dist.size)
    k = int(k)
    if k <= 0:
        return False
    if k >= dist.size:
        return True
    threshold = float(dist[np.argpartition(-dist, k - 1)[k - 1]])
    above = int(np.count_nonzero(dist > threshold))
    value = float(dist[index])
    if value > threshold:
        return True
    if value < threshold:
        return False
    return int(np.count_nonzero(dist[:index] == threshold)) < k - above


def marginals(p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(bottom2, top3)`` sums of a 100000-class distribution."""
    dist = _validate_probability_vector(p)
    if dist.size != MODULUS:
        raise ValueError(f"p must have length {MODULUS}")
    grid = dist.reshape(MODULUS // 1000, 1000)
    return grid.sum(axis=1), grid.sum(axis=0)


def confidence_calibration(confidences: list[float], hits: list[bool], n_bins: int = 10) -> list[dict]:
    """Reliability of the top-1 prediction: confidence vs observed hit rate.

    This is the meaningful multiclass reliability table: bin by the model's own
    maximum probability, then compare mean confidence with the observed top-1
    accuracy inside the bin.
    """
    n_bins = int(n_bins)
    if n_bins <= 0:
        raise ValueError("n_bins must be positive")
    conf = np.asarray(confidences, dtype=np.float64)
    outcome = np.asarray([1.0 if h else 0.0 for h in hits], dtype=np.float64)
    if conf.ndim != 1 or outcome.ndim != 1 or conf.size != outcome.size:
        raise ValueError("confidences and hits must be equal-length vectors")
    if conf.size and (not np.all(np.isfinite(conf)) or np.any(conf < 0.0) or np.any(conf > 1.0)):
        raise ValueError("confidences must be in [0, 1]")
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins = (np.clip(np.searchsorted(edges, conf, side="right") - 1, 0, n_bins - 1)
            if conf.size else np.empty(0, dtype=np.int64))
    table: list[dict] = []
    for b in range(n_bins):
        mask = bins == b
        n = int(np.count_nonzero(mask))
        table.append({
            "lo": float(edges[b]), "hi": float(edges[b + 1]), "n": n,
            "mean_predicted": float(conf[mask].mean()) if n else 0.0,
            "observed_rate": float(outcome[mask].mean()) if n else 0.0,
        })
    return table


def calibration(p_y_values: list[float], n_bins: int = 10) -> list[dict]:
    """Reliability table binned by the probability assigned to realized classes.

    Each value falls in ``[lo, hi)`` (last bin closed).  With one probability per
    realized outcome and no separate binary outcomes, ``observed_rate`` is the
    observed share of samples in the bin (``n / total``); ``mean_predicted`` is
    the mean supplied probability in that bin.  Empty bins report zero means.
    """
    n_bins = int(n_bins)
    if n_bins <= 0:
        raise ValueError("n_bins must be positive")
    values = np.asarray(p_y_values, dtype=np.float64)
    if values.ndim != 1:
        raise ValueError("p_y_values must be one-dimensional")
    if not np.all(np.isfinite(values)) or np.any(values < 0.0) or np.any(values > 1.0):
        raise ValueError("p_y_values must be probabilities in [0, 1]")
    total = int(values.size)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins = (np.clip(np.searchsorted(edges, values, side="right") - 1, 0, n_bins - 1)
            if total else np.empty(0, dtype=np.int64))
    table: list[dict] = []
    for b in range(n_bins):
        mask = bins == b
        n = int(np.count_nonzero(mask))
        table.append({
            "lo": float(edges[b]), "hi": float(edges[b + 1]), "n": n,
            "mean_predicted": float(values[mask].mean()) if n else 0.0,
            "observed_rate": float(n / total) if total else 0.0,
        })
    return table
