"""Causal asymmetric arc-and-thickness geometry for Risk-Off V57.

This module is deliberately not a trading strategy.  It describes the raw
15-minute CloudRidge price path with two separate causal objects:

* an online, non-linear state-space oscillator whose canonical wave has a
  rounded top and a sharper bottom; and
* an asymmetric envelope estimated from the observed high/low innovations
  around that oscillator.

Every row at timestamp ``t`` uses observations at or before ``t``.  No
posterior crash labels, registered events, two-sided filters, or future bars
are accepted as runtime inputs.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import exp, log, pi

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class AsymmetricArcEnvelopeSpec:
    """Low-freedom physical specification for the V57 geometry prototype."""

    candidate_periods_bars: tuple[int, ...] = (64, 128, 256, 512)
    round_top_sharp_bottom_ratio: float = 0.15
    initial_amplitude_log: float = 0.012
    initial_observation_sigma_log: float = 0.004
    score_half_life_bars: float = 96.0
    model_weight_half_life_bars: float = 12.0
    model_score_temperature: float = 0.20
    observation_variance_half_life_bars: float = 64.0
    thickness_window_bars: int = 64
    thickness_lower_quantile: float = 0.10
    thickness_upper_quantile: float = 0.90
    thickness_smoothing_half_life_bars: float = 6.0
    warmup_bars: int = 512

    def __post_init__(self) -> None:
        periods = self.candidate_periods_bars
        if not periods or len(periods) != len(set(periods)):
            raise ValueError("candidate_periods_bars must be non-empty and unique")
        if min(periods) < 32 or tuple(sorted(periods)) != periods:
            raise ValueError("candidate periods must be sorted and at least 32 bars")
        if not 0.0 < self.round_top_sharp_bottom_ratio < 0.25:
            raise ValueError(
                "round_top_sharp_bottom_ratio must be in (0, 0.25)"
            )
        if self.initial_amplitude_log <= 0.0:
            raise ValueError("initial_amplitude_log must be positive")
        if self.initial_observation_sigma_log <= 0.0:
            raise ValueError("initial_observation_sigma_log must be positive")
        if self.score_half_life_bars <= 1.0:
            raise ValueError("score_half_life_bars must exceed one bar")
        if self.model_weight_half_life_bars <= 1.0:
            raise ValueError("model_weight_half_life_bars must exceed one bar")
        if self.model_score_temperature <= 0.0:
            raise ValueError("model_score_temperature must be positive")
        if self.observation_variance_half_life_bars <= 1.0:
            raise ValueError(
                "observation_variance_half_life_bars must exceed one bar"
            )
        if self.thickness_window_bars < 16:
            raise ValueError("thickness_window_bars must be at least 16")
        if not (
            0.0
            < self.thickness_lower_quantile
            < 0.5
            < self.thickness_upper_quantile
            < 1.0
        ):
            raise ValueError("thickness quantiles must straddle the median")
        if self.warmup_bars < max(periods):
            raise ValueError("warmup_bars must cover the longest candidate period")


@dataclass(slots=True)
class _OscillatorState:
    period_bars: int
    state: np.ndarray
    covariance: np.ndarray
    observation_variance: float
    score: float = 0.0


def asymmetric_arc_wave(
    phase: np.ndarray | float,
    ratio: float = 0.15,
) -> np.ndarray | float:
    """Return a one-peak/one-trough wave with round top and sharp bottom.

    ``cos(phase) - ratio*cos(2*phase)`` has no additional stationary points
    for ``0 < ratio < 0.25``.  Its curvature magnitude is
    ``1 - 4*ratio`` at the top and ``1 + 4*ratio`` at the bottom.
    """

    return np.cos(phase) - ratio * np.cos(2.0 * phase)


def _half_life_decay(half_life: float) -> float:
    return exp(log(0.5) / half_life)


def _observation(state: np.ndarray, ratio: float) -> tuple[float, np.ndarray]:
    level, _slope, log_amplitude, phase = state
    amplitude = float(np.exp(np.clip(log_amplitude, log(1e-5), log(0.30))))
    wave = float(asymmetric_arc_wave(phase, ratio))
    value = float(level + amplitude * wave)
    derivative_phase = amplitude * (
        -np.sin(phase) + 2.0 * ratio * np.sin(2.0 * phase)
    )
    jacobian = np.array(
        [1.0, 0.0, amplitude * wave, derivative_phase],
        dtype=float,
    )
    return value, jacobian


def _predict(
    model: _OscillatorState,
) -> tuple[np.ndarray, np.ndarray]:
    transition = np.array(
        [
            [1.0, 1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    predicted = transition @ model.state
    predicted[3] = (
        predicted[3] + 2.0 * pi / float(model.period_bars)
    ) % (2.0 * pi)
    variance = model.observation_variance
    process = np.diag(
        [
            max(variance * 1e-4, 1e-12),
            max(variance * 2e-7, 1e-14),
            2.5e-4,
            4.0e-4,
        ]
    )
    covariance = transition @ model.covariance @ transition.T + process
    return predicted, covariance


def _update_model(
    model: _OscillatorState,
    observation: float,
    *,
    ratio: float,
    score_decay: float,
    variance_decay: float,
) -> tuple[float, float, float]:
    predicted, predicted_covariance = _predict(model)
    predicted_value, jacobian = _observation(predicted, ratio)
    innovation = float(observation - predicted_value)
    innovation_variance = float(
        jacobian @ predicted_covariance @ jacobian
        + model.observation_variance
    )
    innovation_variance = max(innovation_variance, 1e-12)
    gain = (predicted_covariance @ jacobian) / innovation_variance
    updated = predicted + gain * innovation
    updated[1] = float(np.clip(updated[1], -0.01, 0.01))
    updated[2] = float(np.clip(updated[2], log(1e-5), log(0.30)))
    updated[3] %= 2.0 * pi

    identity = np.eye(4)
    residual_projection = identity - np.outer(gain, jacobian)
    covariance = (
        residual_projection
        @ predicted_covariance
        @ residual_projection.T
        + np.outer(gain, gain) * model.observation_variance
    )
    covariance = 0.5 * (covariance + covariance.T)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    covariance = (
        eigenvectors
        @ np.diag(np.maximum(eigenvalues, 1e-14))
        @ eigenvectors.T
    )

    normalized_surprise = (
        np.log(innovation_variance)
        + innovation * innovation / innovation_variance
    )
    model.score = (
        score_decay * model.score
        + (1.0 - score_decay) * float(normalized_surprise)
    )
    innovation_square = float(
        np.clip(innovation * innovation, 1e-10, 0.05**2)
    )
    model.observation_variance = float(
        np.clip(
            variance_decay * model.observation_variance
            + (1.0 - variance_decay) * innovation_square,
            1e-10,
            0.05**2,
        )
    )
    model.state = updated
    model.covariance = covariance
    posterior_value, _ = _observation(updated, ratio)
    return posterior_value, innovation, innovation_variance


def _validate_ohlc(ohlc: pd.DataFrame) -> pd.DataFrame:
    required = {"timestamp", "open", "high", "low", "close"}
    missing = sorted(required.difference(ohlc.columns))
    if missing:
        raise KeyError(f"V57 OHLC carrier missing columns: {missing}")
    if "runtime_uses_future" in ohlc and ohlc["runtime_uses_future"].astype(
        bool
    ).any():
        raise ValueError("V57 OHLC carrier declares future-dependent rows")
    if (
        "runtime_uses_registered_events" in ohlc
        and ohlc["runtime_uses_registered_events"].astype(bool).any()
    ):
        raise ValueError(
            "V57 OHLC carrier declares registered-event dependencies"
        )
    output = ohlc.loc[
        :,
        ["timestamp", "open", "high", "low", "close"],
    ].copy()
    output["timestamp"] = pd.to_datetime(output["timestamp"], errors="raise")
    output = output.sort_values("timestamp", kind="stable").reset_index(
        drop=True
    )
    if output["timestamp"].duplicated().any():
        raise ValueError("V57 OHLC timestamps must be unique")
    values = output[["open", "high", "low", "close"]].apply(
        pd.to_numeric,
        errors="coerce",
    )
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError("V57 OHLC values must be finite")
    if (values <= 0.0).any().any():
        raise ValueError("V57 OHLC values must be positive")
    if (
        (values["high"] < values[["open", "close", "low"]].max(axis=1)).any()
        or (
            values["low"]
            > values[["open", "close", "high"]].min(axis=1)
        ).any()
    ):
        raise ValueError("V57 OHLC ordering is invalid")
    output[["open", "high", "low", "close"]] = values
    return output


def build_causal_asymmetric_arc_envelope(
    ohlc: pd.DataFrame,
    spec: AsymmetricArcEnvelopeSpec = AsymmetricArcEnvelopeSpec(),
) -> pd.DataFrame:
    """Build the causal V57 arc centre and asymmetric thickness envelope."""

    output = _validate_ohlc(ohlc)
    count = len(output)
    if not count:
        raise ValueError("V57 OHLC carrier cannot be empty")

    log_open = np.log(output["open"].to_numpy(dtype=float))
    log_high = np.log(output["high"].to_numpy(dtype=float))
    log_low = np.log(output["low"].to_numpy(dtype=float))
    log_close = np.log(output["close"].to_numpy(dtype=float))

    initial_variance = spec.initial_observation_sigma_log**2
    models = [
        _OscillatorState(
            period_bars=period,
            state=np.array(
                [
                    log_close[0],
                    0.0,
                    log(spec.initial_amplitude_log),
                    pi,
                ],
                dtype=float,
            ),
            covariance=np.diag(
                [
                    initial_variance * 16.0,
                    initial_variance * 0.02,
                    0.75,
                    pi**2,
                ]
            ),
            observation_variance=initial_variance,
        )
        for period in spec.candidate_periods_bars
    ]
    score_decay = _half_life_decay(spec.score_half_life_bars)
    weight_decay = _half_life_decay(spec.model_weight_half_life_bars)
    variance_decay = _half_life_decay(
        spec.observation_variance_half_life_bars
    )
    thickness_decay = _half_life_decay(
        spec.thickness_smoothing_half_life_bars
    )

    model_weights = np.full(len(models), 1.0 / len(models), dtype=float)
    upper_residuals: deque[float] = deque(
        maxlen=spec.thickness_window_bars
    )
    lower_residuals: deque[float] = deque(
        maxlen=spec.thickness_window_bars
    )
    ranges: deque[float] = deque(maxlen=spec.thickness_window_bars)
    smoothed_upper_offset = spec.initial_observation_sigma_log * 2.0
    smoothed_lower_offset = -spec.initial_observation_sigma_log * 2.0

    centre_log = np.full(count, np.nan)
    upper_log = np.full(count, np.nan)
    lower_log = np.full(count, np.nan)
    phase = np.full(count, np.nan)
    amplitude = np.full(count, np.nan)
    slope = np.full(count, np.nan)
    period = np.full(count, np.nan)
    confidence = np.zeros(count)
    innovation = np.full(count, np.nan)
    geometry_valid = np.zeros(count, dtype=bool)
    phase_label = np.full(count, "warmup", dtype=object)

    for index, observed in enumerate(log_close):
        posterior_values = np.empty(len(models), dtype=float)
        innovations = np.empty(len(models), dtype=float)
        for model_index, model in enumerate(models):
            (
                posterior_values[model_index],
                innovations[model_index],
                _innovation_variance,
            ) = _update_model(
                model,
                float(observed),
                ratio=spec.round_top_sharp_bottom_ratio,
                score_decay=score_decay,
                variance_decay=variance_decay,
            )

        scores = np.asarray([model.score for model in models], dtype=float)
        stabilized = (
            -(scores - float(scores.min())) / spec.model_score_temperature
        )
        target_weights = np.exp(np.clip(stabilized, -60.0, 0.0))
        target_weights /= target_weights.sum()
        model_weights = (
            weight_decay * model_weights
            + (1.0 - weight_decay) * target_weights
        )
        model_weights /= model_weights.sum()
        dominant_index = int(np.argmax(model_weights))
        selected_centre = float(model_weights @ posterior_values)
        centre_log[index] = selected_centre
        innovation[index] = float(observed - selected_centre)
        phases = np.asarray([model.state[3] for model in models])
        phase[index] = float(
            np.arctan2(
                model_weights @ np.sin(phases),
                model_weights @ np.cos(phases),
            )
            % (2.0 * pi)
        )
        amplitude[index] = float(
            model_weights
            @ np.asarray([np.exp(model.state[2]) for model in models])
        )
        slope[index] = float(
            model_weights
            @ np.asarray([model.state[1] for model in models])
        )
        period[index] = float(models[dominant_index].period_bars)

        upper_residuals.append(float(log_high[index] - selected_centre))
        lower_residuals.append(float(log_low[index] - selected_centre))
        ranges.append(float(log_high[index] - log_low[index]))
        raw_upper = float(
            np.quantile(
                np.asarray(upper_residuals),
                spec.thickness_upper_quantile,
            )
        )
        raw_lower = float(
            np.quantile(
                np.asarray(lower_residuals),
                spec.thickness_lower_quantile,
            )
        )
        minimum_half_width = 0.5 * float(np.median(np.asarray(ranges)))
        raw_upper = max(raw_upper, minimum_half_width, 1e-6)
        raw_lower = min(raw_lower, -minimum_half_width, -1e-6)
        smoothed_upper_offset = (
            thickness_decay * smoothed_upper_offset
            + (1.0 - thickness_decay) * raw_upper
        )
        smoothed_lower_offset = (
            thickness_decay * smoothed_lower_offset
            + (1.0 - thickness_decay) * raw_lower
        )
        upper_log[index] = selected_centre + smoothed_upper_offset
        lower_log[index] = selected_centre + smoothed_lower_offset

        half_width = max(
            0.5 * (smoothed_upper_offset - smoothed_lower_offset),
            1e-8,
        )
        signal_to_thickness = amplitude[index] / half_width
        shape_strength = 1.0 / (
            1.0 + np.exp(-2.0 * (signal_to_thickness - 1.0))
        )
        normalized_entropy = float(
            -np.sum(model_weights * np.log(np.maximum(model_weights, 1e-15)))
            / np.log(len(model_weights))
        )
        confidence[index] = float(
            np.clip(shape_strength * (1.0 - normalized_entropy), 0.0, 1.0)
        )
        geometry_valid[index] = index + 1 >= spec.warmup_bars

        phase_fraction = phase[index] / (2.0 * pi)
        if not geometry_valid[index]:
            phase_label[index] = "warmup"
        elif phase_fraction < 0.125 or phase_fraction >= 0.875:
            phase_label[index] = "round_top"
        elif phase_fraction < 0.50:
            phase_label[index] = "descending_arc"
        elif phase_fraction < 0.625:
            phase_label[index] = "sharp_bottom"
        else:
            phase_label[index] = "ascending_arc"

    output["arc_mid"] = np.exp(centre_log)
    output["arc_upper"] = np.exp(upper_log)
    output["arc_lower"] = np.exp(lower_log)
    output["arc_phase_radian"] = phase
    output["arc_phase_fraction"] = phase / (2.0 * pi)
    output["arc_phase_label"] = phase_label
    output["arc_amplitude_log"] = amplitude
    output["arc_background_slope_log_per_15m"] = slope
    output["arc_dominant_period_bars"] = period.astype(np.int64)
    output["arc_thickness_log"] = upper_log - lower_log
    output["arc_thickness_pct"] = np.expm1(upper_log - lower_log) * 100.0
    output["arc_confidence"] = confidence
    output["arc_geometry_valid"] = geometry_valid
    output["arc_innovation_log"] = innovation
    output["arc_top_to_bottom_curvature_ratio"] = (
        1.0 + 4.0 * spec.round_top_sharp_bottom_ratio
    ) / (1.0 - 4.0 * spec.round_top_sharp_bottom_ratio)
    output["runtime_uses_future"] = False
    output["runtime_uses_registered_events"] = False
    output["strategy_version"] = "V57"
    output["strategy_version_id"] = (
        "risk_off_v57_causal_asymmetric_arc_envelope"
    )
    output["strategy_method_id"] = (
        "risk_off_v57_online_asymmetric_oscillator_envelope_v1"
    )
    output["research_authority"] = True
    output["production_authority"] = False
    output["action_semantics"] = (
        "geometry_only;no_trade_action;bar_t_uses_observations_through_t;"
        "round_top_sharp_bottom_state_space_arc;"
        "causal_high_low_innovation_quantile_envelope"
    )
    return output
