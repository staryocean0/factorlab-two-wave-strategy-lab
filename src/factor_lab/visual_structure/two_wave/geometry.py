"""Five confirmed extrema define drift; every intervening close defines coverage."""

from __future__ import annotations

import math

import numpy as np

from .models import Config


def fit_geometry(pivots: list[dict], bars: list[dict], config: Config) -> dict:
    """Fit x=a+bt+w*high using the two completed cycles, never the confirmation leg.

    The regression width is used in D/E.  The operative frozen envelope uses
    min/max(x-bt) over *all* closes through the fifth extremum.  These different
    widths and their coverage are both reported rather than silently conflated.
    """
    if len(pivots) != 5:
        raise ValueError("exactly five confirmed alternating pivots are required")
    start, end = pivots[0]["occurrence_bar"], pivots[-1]["occurrence_bar"]
    if not all(pivots[i]["occurrence_bar"] < pivots[i + 1]["occurrence_bar"] for i in range(4)):
        raise ValueError("pivot occurrence bars must increase strictly")
    if not all(pivots[i]["kind"] != pivots[i + 1]["kind"] for i in range(4)):
        raise ValueError("pivots must alternate")
    t = np.array([p["occurrence_bar"] - start for p in pivots], dtype=float)
    x = np.array([p["log_price"] for p in pivots], dtype=float)
    high = np.array([p["kind"] == "high" for p in pivots], dtype=float)
    design = np.column_stack((np.ones(5), t, high))
    coef, _, rank, _ = np.linalg.lstsq(design, x, rcond=None)
    a, b, width = (float(v) for v in coef)
    result = {
        "valid": False,
        "origin_bar": start,
        "fit_end_bar": end,
        "a": a,
        "b": b,
        "width": width,
        "D": None,
        "E": None,
        "lower_offset": None,
        "upper_offset": None,
        "envelope_width": None,
        "nominal_coverage": None,
        "envelope_coverage": None,
        "fit_bar_count": end - start + 1,
        "classification": "uncertain",
        "attributes": [],
        "regression_rank": int(rank),
    }
    if rank != 3 or not all(math.isfinite(v) for v in (a, b, width)):
        result["attributes"] = ["invalid_regression"]
        return result
    if width <= config.min_width:
        # In particular, a negative fitted w is not fixed with abs(w).
        result["attributes"] = ["nonpositive_or_tiny_width"]
        return result
    interval = bars[start : end + 1]
    if len(interval) != end - start + 1:
        raise ValueError("all bar closes in the completed two-cycle interval are required")
    full_t = np.arange(end - start + 1, dtype=float)

    def row_log_close(row: dict) -> float:
        # Legacy geometry tests and Engine-normalized bars already carry
        # log_close.  Raw manifest callers carry close instead.  Branching
        # explicitly avoids eager evaluation of a fallback expression and
        # therefore preserves the old path byte-for-value.
        if "log_close" in row:
            return float(row["log_close"])
        return math.log(float(row["close"]))

    full_x = np.array([row_log_close(row) for row in interval], dtype=float)
    residuals = x - design @ coef
    detrended = full_x - b * full_t
    lower, upper = float(detrended.min()), float(detrended.max())
    envelope_width = upper - lower
    eps = 1e-12
    nominal_coverage = float(np.mean((detrended >= a - eps) & (detrended <= a + width + eps)))
    envelope_coverage = float(np.mean((detrended >= lower - eps) & (detrended <= upper + eps)))
    drift = b * float(t[-1]) / width
    error = float(np.sqrt(np.mean(residuals**2)) / width)
    phase_lines = {}
    for kind, mask in (("high", high == 1), ("low", high == 0)):
        phase_design = np.column_stack((np.ones(int(mask.sum())), t[mask]))
        line, _, _, _ = np.linalg.lstsq(phase_design, x[mask], rcond=None)
        phase_lines[kind] = {
            "offset": float(line[0]),
            "slope": float(line[1]),
            "normalized_drift": float(line[1] * t[-1] / width),
        }
    majority_steps = np.diff(x[::2]) / width
    majority_slopes = np.diff(x[::2]) / np.diff(t[::2]) * t[-1] / width
    high_drift = phase_lines["high"]["normalized_drift"]
    low_drift = phase_lines["low"]["normalized_drift"]
    phase_width_start = phase_lines["high"]["offset"] - phase_lines["low"]["offset"]
    phase_width_end = phase_width_start + (phase_lines["high"]["slope"] - phase_lines["low"]["slope"]) * t[-1]
    cycle_amplitudes = [float(np.ptp(x[:3])), float(np.ptp(x[2:]))]
    amplitude_ratio = max(cycle_amplitudes) / min(cycle_amplitudes) if min(cycle_amplitudes) > 0 else None
    attributes = []
    if error > config.max_fit_error:
        attributes.append("poor_pivot_fit")
    if min(phase_width_start, phase_width_end) <= config.min_width:
        width_ratio = None
        attributes.append("phase_lines_cross_or_collapse")
    else:
        width_ratio = float(max(phase_width_start, phase_width_end) / min(phase_width_start, phase_width_end))
        if width_ratio > config.max_width_ratio:
            attributes.append("expanding" if phase_width_end > phase_width_start else "converging")
    tol = config.direction_tolerance
    if (high_drift > tol and low_drift < -tol) or (high_drift < -tol and low_drift > tol):
        attributes.append("high_low_direction_conflict")
    if (majority_steps[0] > tol and majority_steps[1] < -tol) or (majority_steps[0] < -tol and majority_steps[1] > tol):
        attributes.append("within_phase_direction_conflict")
    if abs(high_drift - low_drift) > config.max_slope_disagreement:
        attributes.append("phase_slope_disagreement")
    if abs(float(majority_slopes[0] - majority_slopes[1])) > config.max_slope_disagreement:
        attributes.append("uneven_phase_drift")
    if amplitude_ratio is None or amplitude_ratio > config.max_width_ratio:
        attributes.append("cycle_amplitude_change")
    if envelope_width / width > config.max_width_ratio:
        attributes.append("large_envelope_expansion")
    classification = "uncertain"
    if not attributes:
        classification = "range" if abs(drift) <= config.drift_threshold else ("uptrend" if drift > 0 else "downtrend")
    result.update(
        {
            "valid": True,
            "D": float(drift),
            "E": error,
            "lower_offset": lower,
            "upper_offset": upper,
            "envelope_width": envelope_width,
            "nominal_coverage": nominal_coverage,
            "envelope_coverage": envelope_coverage,
            "envelope_to_model_width_ratio": envelope_width / width,
            "phase_lines": phase_lines,
            "phase_width_start": float(phase_width_start),
            "phase_width_end": float(phase_width_end),
            "phase_width_ratio": width_ratio,
            "majority_phase_step_displacements": [float(v) for v in majority_steps],
            "majority_phase_step_slopes": [float(v) for v in majority_slopes],
            "cycle_amplitudes_log": cycle_amplitudes,
            "cycle_amplitude_ratio": amplitude_ratio,
            "classification": classification,
            "attributes": attributes,
            "price_basis": "log_close",
            "time_basis": "bar_ordinal",
            "boundary_basis": "frozen_all_completed_interval_closes",
        }
    )
    return result