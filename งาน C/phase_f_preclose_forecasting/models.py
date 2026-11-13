"""Purely functional residue-distribution models.

Distributions are one-dimensional ``float64`` arrays of length ``MODULUS``
indexed by a residue ``r`` in ``[0, MODULUS)``.
"""
from __future__ import annotations

import numpy as np

MODULUS = 100000


def _as_distribution(dist: np.ndarray, name: str = "dist") -> np.ndarray:
    """Validate a residue distribution and return it as float64."""
    arr = np.asarray(dist, dtype=np.float64)
    if arr.ndim != 1 or arr.size != MODULUS:
        raise ValueError(f"{name} must be a 1-D vector of length {MODULUS}")
    if not np.all(np.isfinite(arr)) or np.any(arr < 0.0):
        raise ValueError(f"{name} must be finite and non-negative")
    if not np.isclose(float(arr.sum()), 1.0, rtol=0.0, atol=1e-6):
        raise ValueError(f"{name} must sum to 1")
    return arr


def uniform() -> np.ndarray:
    """Return the uniform distribution over all residues."""
    dist = np.full(MODULUS, 1.0 / MODULUS, dtype=np.float64)
    return dist / dist.sum()


def _smoothed(counts: np.ndarray, prior_strength: float) -> np.ndarray:
    """Add ``prior_strength`` pseudo-observations spread evenly over residues."""
    if prior_strength <= 0.0:
        raise ValueError("prior_strength must be strictly positive")
    arr = np.asarray(counts, dtype=np.float64)
    if arr.ndim != 1 or arr.size != MODULUS:
        raise ValueError(f"counts must be a 1-D vector of length {MODULUS}")
    if not np.all(np.isfinite(arr)) or np.any(arr < 0.0):
        raise ValueError("counts must be finite and non-negative")
    dist = (arr + prior_strength / MODULUS) / (float(arr.sum()) + prior_strength)
    return dist / dist.sum()


def historical(residue_counts: np.ndarray, prior_strength: float = 100.0) -> np.ndarray:
    """Smoothed empirical distribution of training-round residues."""
    return _smoothed(residue_counts, prior_strength)


def delta_distribution(deltas: list[int], prior_strength: float = 20.0) -> np.ndarray:
    """Smoothed empirical distribution of ``delta % MODULUS`` values."""
    if prior_strength <= 0.0:
        raise ValueError("prior_strength must be strictly positive")
    if deltas:
        values = np.fromiter((int(d) % MODULUS for d in deltas), dtype=np.int64, count=len(deltas))
        counts = np.bincount(values, minlength=MODULUS).astype(np.float64)
    else:
        counts = np.zeros(MODULUS, dtype=np.float64)
    return _smoothed(counts, prior_strength)


def shift(dist: np.ndarray, by: int) -> np.ndarray:
    """Return ``out`` with ``out[r] = dist[(r - by) % MODULUS]`` (``np.roll``)."""
    return np.roll(_as_distribution(dist), int(by) % MODULUS)


def conditional_delta(deltas_by_k: dict[int, list[int]], k: int, fallback: np.ndarray,
                      prior_strength: float = 20.0) -> np.ndarray:
    """Delta distribution for effective prefix length ``k``.

    With fewer than 30 samples the k-specific estimate is mixed with ``fallback``
    using weight ``n / (n + 30)``; ``n == 0`` returns ``fallback`` unchanged.
    """
    base = _as_distribution(fallback, "fallback")
    samples = deltas_by_k.get(int(k), [])
    n = len(samples)
    if n == 0:
        return fallback
    specific = delta_distribution(samples, prior_strength)
    if n >= 30:
        return specific
    weight = n / (n + 30.0)
    mixed = weight * specific + (1.0 - weight) * base
    return mixed / mixed.sum()
