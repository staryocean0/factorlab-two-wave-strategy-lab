# pyright: reportAny=false

"""Distribution-free tests for downside bucket morphology.

These helpers judge whether two already-frozen market-state buckets describe
different decline paths.  They do not select the bucket formula or tune a
trading parameter.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np


def _maximum_positive_run(values: np.ndarray) -> float:
    maximum = 0.0
    current = 0.0
    for value in values:
        if value > 0.0:
            current += float(value)
            maximum = max(maximum, current)
        else:
            current = 0.0
    return maximum


def _run_lengths(mask: np.ndarray) -> list[int]:
    lengths: list[int] = []
    current = 0
    for active in mask:
        if active:
            current += 1
        elif current:
            lengths.append(current)
            current = 0
    if current:
        lengths.append(current)
    return lengths


def describe_decline_path(
    log_close: Iterable[float],
    log_open: Iterable[float] | None = None,
) -> dict[str, float]:
    """Describe one completed peak-to-trough path using only its own bars."""

    close = np.asarray(tuple(log_close), dtype=float)
    if len(close) < 2 or not np.isfinite(close).all():
        raise ValueError("log_close must contain at least two finite values")
    decline = float(close[0] - close[-1])
    if decline <= 0.0:
        raise ValueError("path must finish below its starting close")
    returns = np.diff(close)
    down_moves = np.clip(-returns, 0.0, None)
    positive_moves = np.clip(returns, 0.0, None)
    active_down = down_moves[down_moves > 1e-12]
    gross_down = float(active_down.sum())
    absolute_path = float(np.abs(returns).sum())
    down_count = len(active_down)
    uniformity = float(active_down.mean() / np.sqrt(np.square(active_down).mean())) if down_count else 0.0
    shares = active_down / max(gross_down, 1e-12)
    ordered_shares = np.sort(shares)[::-1]
    signs = np.sign(returns[np.abs(returns) > 1e-12])
    flips = int(np.sum(signs[1:] != signs[:-1])) if len(signs) > 1 else 0
    down_runs = _run_lengths(returns < -1e-12)
    midpoint = max(1, len(returns) // 2)
    first_speed = float(down_moves[:midpoint].mean())
    second_speed = float(down_moves[midpoint:].mean()) if midpoint < len(returns) else 0.0
    overall_speed = float(down_moves.mean())
    quarter_start = max(1, int(np.floor(len(returns) * 0.75)))
    result = {
        "bar_count": float(len(returns)),
        "decline_log_size": decline,
        "net_decline_speed_per_bar": decline / len(returns),
        "down_bar_fraction": float(np.mean(returns < -1e-12)),
        "down_move_uniformity": uniformity,
        "largest_down_move_share": float(ordered_shares[0]) if down_count else 0.0,
        "top_three_down_move_share": float(ordered_shares[:3].sum()),
        "late_to_early_down_speed_ratio": second_speed / max(first_speed, 1e-12),
        "downside_acceleration_score": (second_speed - first_speed) / max(overall_speed, 1e-12),
        "final_quarter_gross_down_share": float(down_moves[quarter_start:].sum()) / max(gross_down, 1e-12),
        "decline_path_efficiency": decline / max(absolute_path, 1e-12),
        "internal_rebound_to_decline": float(positive_moves.sum()) / max(decline, 1e-12),
        "maximum_rebound_leg_to_decline": _maximum_positive_run(returns) / max(decline, 1e-12),
        "direction_flip_rate": flips / max(len(signs) - 1, 1),
        "mean_down_run_bars": float(np.mean(down_runs)) if down_runs else 0.0,
        "maximum_down_run_share": max(down_runs, default=0) / len(returns),
    }
    if log_open is not None:
        open_values = np.asarray(tuple(log_open), dtype=float)
        if len(open_values) != len(close) or not np.isfinite(open_values).all():
            raise ValueError("log_open must be finite and align with log_close")
        result["bearish_candle_fraction"] = float(np.mean(close < open_values))
    return result


def cliffs_delta(left: Iterable[float], right: Iterable[float]) -> float:
    """Return Cliff's delta after dropping non-finite observations."""

    left_values = np.asarray(tuple(left), dtype=float)
    right_values = np.asarray(tuple(right), dtype=float)
    left_values = left_values[np.isfinite(left_values)]
    right_values = right_values[np.isfinite(right_values)]
    if not len(left_values) or not len(right_values):
        return float("nan")
    comparisons = np.sign(left_values[:, None] - right_values[None, :])
    return float(comparisons.mean())


def classify_morphology_stability(
    effects: Iterable[float],
    *,
    expected_direction: int,
    actionable_effect_floor: float = 0.147,
) -> dict[str, object]:
    """Classify a frozen cross-period effect without averaging away reversals.

    ``expected_direction`` is ``1`` when the first bucket should be larger and
    ``-1`` when it should be smaller.  Every period, including the frozen audit,
    must independently pass for an effect to be actionable.
    """

    if expected_direction not in (-1, 1):
        raise ValueError("expected_direction must be -1 or 1")
    if not np.isfinite(actionable_effect_floor) or actionable_effect_floor <= 0.0:
        raise ValueError("actionable_effect_floor must be finite and positive")
    raw = np.asarray(tuple(effects), dtype=float)
    aligned = raw * expected_direction
    complete = bool(len(aligned) and np.isfinite(aligned).all())
    direction_consistent = bool(complete and np.all(aligned > 0.0))
    actionable = bool(direction_consistent and np.all(aligned >= actionable_effect_floor))
    if actionable:
        classification = "actionable_stable"
    elif direction_consistent:
        classification = "weak_direction_only"
    else:
        classification = "unstable_or_reversed"
    return {
        "classification": classification,
        "complete": complete,
        "direction_consistent": direction_consistent,
        "actionable": actionable,
        "minimum_aligned_effect": (float(np.min(aligned)) if complete else float("nan")),
    }


__all__ = [
    "classify_morphology_stability",
    "cliffs_delta",
    "describe_decline_path",
]
