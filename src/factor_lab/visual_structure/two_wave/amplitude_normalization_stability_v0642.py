"""Read-only v0.6.42 amplitude-normalization stability helpers."""
from __future__ import annotations

import math
from typing import Sequence

SCHEMA = "two_wave_amplitude_normalization_stability@0.6.42"
NUMERIC_EPS = 1e-12


def _finite_nonnegative(value: float, name: str) -> float:
    x = float(value)
    if not math.isfinite(x) or x < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return x


def symmetric_relative_difference(a: float, b: float) -> float:
    """Threshold-free 2|a-b|/(a+b), with the all-zero case mapped to zero."""
    x = _finite_nonnegative(a, "a")
    y = _finite_nonnegative(b, "b")
    denom = x + y
    if denom <= NUMERIC_EPS:
        return 0.0
    return float(2.0 * abs(x - y) / denom)


def signed_symmetric_relative_difference(rescue: float, nonrescue: float) -> float:
    """Signed 2(r-n)/(|r|+|n|), used only for one-sided attribution."""
    r = float(rescue)
    n = float(nonrescue)
    if not math.isfinite(r) or not math.isfinite(n):
        raise ValueError("finite values required")
    denom = abs(r) + abs(n)
    if denom <= NUMERIC_EPS:
        return 0.0
    return float(2.0 * (r - n) / denom)


def amplitude_metrics(
    detrended_amplitudes_price: Sequence[float], amplitude_unit_price: float
) -> dict:
    amps = tuple(float(x) for x in detrended_amplitudes_price)
    if len(amps) != 2 or not all(math.isfinite(x) and x > 0 for x in amps):
        raise ValueError("two positive finite detrended amplitudes required")
    unit = float(amplitude_unit_price)
    if not math.isfinite(unit) or unit <= 0:
        raise ValueError("positive finite amplitude unit required")
    expected = (amps[0] + amps[1]) / 2.0
    if abs(unit - expected) > 1e-9 * max(1.0, abs(unit), abs(expected)):
        raise ValueError("amplitude unit does not match frozen mean-amplitude formula")
    imbalance = float(2.0 * abs(amps[0] - amps[1]) / (amps[0] + amps[1]))
    return {
        "schema": SCHEMA,
        "amp1_price": amps[0],
        "amp2_price": amps[1],
        "amplitude_unit_price": unit,
        "cycle_amplitude_imbalance": imbalance,
    }


def counterfactual_crossing_attribution(
    *,
    rescue_max_raw_w1: float,
    rescue_amplitude_unit: float,
    nonrescue_max_raw_w1: float,
    nonrescue_amplitude_unit: float,
    inherited_w1_ceiling: float,
) -> dict:
    rr = _finite_nonnegative(rescue_max_raw_w1, "rescue_max_raw_w1")
    nr = _finite_nonnegative(nonrescue_max_raw_w1, "nonrescue_max_raw_w1")
    ra = float(rescue_amplitude_unit)
    na = float(nonrescue_amplitude_unit)
    ceiling = float(inherited_w1_ceiling)
    if not math.isfinite(ra) or ra <= 0 or not math.isfinite(na) or na <= 0:
        raise ValueError("positive finite amplitude units required")
    if not math.isfinite(ceiling) or ceiling <= 0:
        raise ValueError("positive finite inherited ceiling required")

    rescue_norm = rr / ra
    nonrescue_norm = nr / na
    if rescue_norm > ceiling + NUMERIC_EPS:
        raise ValueError("actual rescue side must pass the inherited W1 ceiling")
    if nonrescue_norm <= ceiling + NUMERIC_EPS:
        raise ValueError("actual non-rescue side must fail the inherited W1 ceiling")

    raw_only = rr / na
    denominator_only = nr / ra
    raw_only_pass = raw_only <= ceiling + NUMERIC_EPS
    denominator_only_pass = denominator_only <= ceiling + NUMERIC_EPS

    if raw_only_pass and denominator_only_pass:
        category = "either_component_alone_sufficient"
    elif raw_only_pass:
        category = "raw_numerator_change_sufficient"
    elif denominator_only_pass:
        category = "amplitude_denominator_change_sufficient"
    else:
        category = "both_changes_required"

    return {
        "schema": SCHEMA,
        "actual_rescue_normalized": float(rescue_norm),
        "actual_nonrescue_normalized": float(nonrescue_norm),
        "raw_only_normalized": float(raw_only),
        "denominator_only_normalized": float(denominator_only),
        "raw_only_pass": bool(raw_only_pass),
        "denominator_only_pass": bool(denominator_only_pass),
        "attribution_category": category,
        "inherited_w1_ceiling": ceiling,
    }


def sign_bucket(value: float) -> str:
    x = float(value)
    if not math.isfinite(x):
        raise ValueError("finite value required")
    if x > NUMERIC_EPS:
        return "positive"
    if x < -NUMERIC_EPS:
        return "negative"
    return "zero"
