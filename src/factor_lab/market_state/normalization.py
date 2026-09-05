"""Causal normalization primitives for market-state online facts."""

from __future__ import annotations

import math

import numpy as np


def empirical_location(current: float, prior: np.ndarray) -> float:
    """Return the empirical percentile of ``current`` against strict prior data."""

    clean = np.asarray(prior, dtype=float)
    clean = clean[np.isfinite(clean)]
    if clean.size == 0 or not math.isfinite(float(current)):
        return math.nan
    return float(np.mean(clean <= float(current)))


def robust_scale(
    prior: np.ndarray,
    *,
    iqr_divisor: float = 1.349,
    mad_multiplier: float = 1.4826,
) -> tuple[float, str]:
    """Return IQR/1.349, then MAD*1.4826, then the explicit zero fallback."""

    clean = np.asarray(prior, dtype=float)
    clean = clean[np.isfinite(clean)]
    if clean.size == 0:
        return 0.0, "zero"
    q25, q75 = np.quantile(clean, [0.25, 0.75])
    scale = float((q75 - q25) / iqr_divisor)
    if math.isfinite(scale) and scale > 0.0:
        return scale, "iqr"
    median = float(np.median(clean))
    mad_scale = float(np.median(np.abs(clean - median)) * mad_multiplier)
    if math.isfinite(mad_scale) and mad_scale > 0.0:
        return mad_scale, "mad"
    return 0.0, "zero"


__all__ = ["empirical_location", "robust_scale"]
