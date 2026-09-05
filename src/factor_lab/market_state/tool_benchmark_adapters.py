# pyright: reportAny=false, reportArgumentType=false, reportAssignmentType=false
# pyright: reportAttributeAccessIssue=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportOperatorIssue=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Causal benchmark adapters for concrete timing tools."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import cast

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.filtering.cloudridge_3_0_hybrid_filter_bank import (
    butterworth_bandpass_component,
)
from factor_lab.filtering.timing_validation import (
    FilterSpec,
    apply_filter_spec,
    signal_from_filtered,
)
from factor_lab.market_state.tool_registry import ToolBenchmarkSpec
from factor_lab.strategy.services.risk_off_v57_asymmetric_arc_envelope import (
    AsymmetricArcEnvelopeSpec,
    build_causal_asymmetric_arc_envelope,
)
from factor_lab.strategy.services.risk_off_v57_lowpass_battle import (
    direction_decision,
)
from factor_lab.strategy.services.risk_off_v58_frequency_bollinger import (
    FrequencyBollingerSpec,
    build_frequency_bollinger,
    channel_decision,
)
from factor_lab.strategy.services.risk_off_v58_lowpass_residual_envelope import (
    LowpassResidualEnvelopeSpec,
    build_causal_lowpass_residual_envelope,
)

TOOL_BENCHMARK_PANEL_SCHEMA_ID = "market_state_tool_benchmark_panel@1.2"

BenchmarkParameters = Mapping[str, float | int | str]
_OPTIONAL_PROFILE_PARAMETER_KEYS: Mapping[str, frozenset[str]] = {
    "frequency_selective_bollinger_channel": frozenset(
        {"band_upper_frequency_ratio"}
    ),
}


def run_tool_benchmark(
    bars: pd.DataFrame,
    spec: ToolBenchmarkSpec,
    *,
    frequency: str,
) -> pd.DataFrame:
    """Run one next-bar long/cash probe and expose role-specific outcomes."""

    return run_tool_benchmark_profile(
        bars,
        spec,
        frequency=frequency,
        parameters=spec.parameters_by_frequency[frequency],
        benchmark_id=spec.benchmark_id,
    )


def run_tool_benchmark_profile(
    bars: pd.DataFrame,
    spec: ToolBenchmarkSpec,
    *,
    frequency: str,
    parameters: BenchmarkParameters,
    benchmark_id: str,
) -> pd.DataFrame:
    """Replay one immutable formula profile without mutating a benchmark spec.

    This is a deterministic research adapter only.  It does not select a
    profile, register an experiment, or grant dynamic-parameter authority.
    New V2 research must still register its candidate vectors before calling
    this function; this surface exists so historical Task4 replays no longer
    rewrite ``parameters_by_frequency`` inside scripts.
    """

    frame = _validated_bars(bars, frequency=frequency)
    if not benchmark_id.strip():
        raise ValidationError("benchmark profile id is required")
    baseline_keys = set(spec.parameters_by_frequency[frequency])
    allowed_keys = baseline_keys | set(
        _OPTIONAL_PROFILE_PARAMETER_KEYS.get(spec.tool_id, frozenset())
    )
    if not baseline_keys.issubset(parameters) or not set(parameters).issubset(allowed_keys):
        raise ValidationError("benchmark profile must preserve the declared parameter keys")
    params = dict(parameters)
    builders: dict[
        str, Callable[[pd.DataFrame, BenchmarkParameters], pd.Series]
    ] = {
        "laplace_iir_mixed_bandpass": _iir_bandpass_target,
        "laplace_iir_lowpass": _iir_lowpass_target,
        "butterworth_clean_bandpass": _butterworth_target,
        "rolling_fourier_bandpass": _fourier_bandpass_target,
        "causal_haar_wavelet_bandpass": _haar_wavelet_bandpass_target,
        "r3_nested_moving_average_component": _r3_component_target,
        "bollinger_volatility_channel": _volatility_channel_target,
        "frequency_selective_bollinger_channel": _frequency_bollinger_target,
        "butterworth_lowpass_residual_envelope": _lowpass_residual_target,
        "causal_asymmetric_arc_state_space_envelope": _asymmetric_arc_target,
        "donchian_price_channel": _price_channel_target,
        "causal_trendline_channel": _trendline_channel_target,
        "simple_moving_average_trend": _moving_average_target,
    }
    try:
        raw_target = builders[spec.tool_id](frame, params)
    except KeyError as exc:
        raise ValidationError(f"unsupported concrete tool: {spec.tool_id}") from exc
    target = raw_target.astype(float).clip(0.0, 1.0).fillna(0.0)
    forward_market_return = np.log(frame["close"].shift(-1) / frame["close"])
    turnover = target.diff().abs().fillna(target.abs())
    cost = turnover * (float(params["cost_bps"]) / 10_000.0)
    long_value = target * forward_market_return - cost
    cash_value = -(1.0 - target) * forward_market_return - cost
    panel = pd.DataFrame(
        {
            "benchmark_panel_schema_id": TOOL_BENCHMARK_PANEL_SCHEMA_ID,
            "benchmark_id": benchmark_id,
            "tool_id": spec.tool_id,
            "method_family_id": spec.method_family_id,
            "bar_frequency": frequency,
            "decision_time": frame["timestamp"],
            "target_position": target,
            "forward_market_log_return": forward_market_return,
            "turnover": turnover,
            "transaction_cost_log_return": cost,
            "long_capture_value": long_value,
            "cash_avoidance_value": cash_value,
            "causal": True,
            "execution_lag_bars": 1,
        }
    ).dropna(subset=["forward_market_log_return"])
    long_trades = _completed_episode_outcomes(
        panel,
        active=panel["target_position"].gt(0.5),
        value_column="long_capture_value",
    )
    cash_episodes = _completed_episode_outcomes(
        panel,
        active=panel["target_position"].le(0.5),
        value_column="cash_avoidance_value",
    )
    panel["long_trade_outcome"] = long_trades
    panel["cash_episode_outcome"] = cash_episodes
    return panel


def _validated_bars(bars: pd.DataFrame, *, frequency: str) -> pd.DataFrame:
    required = {"timestamp", "open", "high", "low", "close"}
    missing = sorted(required - set(bars.columns))
    if missing:
        raise ValidationError(f"tool benchmark bars missing columns: {missing}")
    frame = bars.loc[:, sorted(required)].copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    for column in ("open", "high", "low", "close"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = (
        frame.dropna()
        .sort_values("timestamp")
        .drop_duplicates("timestamp")
        .reset_index(drop=True)
    )
    if frame.empty or not bool((frame["close"] > 0.0).all()):
        raise ValidationError("tool benchmark bars must contain positive closes")
    if frequency not in {"1d", "60m", "15m"}:
        raise ValidationError(f"unsupported tool benchmark frequency: {frequency}")
    return frame


def _log_close(frame: pd.DataFrame) -> pd.Series:
    return pd.Series(
        np.log(frame["close"].to_numpy(dtype=float)),
        index=pd.DatetimeIndex(frame["timestamp"]),
    )


def _iir_bandpass_target(
    frame: pd.DataFrame, params: BenchmarkParameters
) -> pd.Series:
    component = apply_filter_spec(
        _log_close(frame),
        FilterSpec(
            name="market_state_tool_iir_bandpass",
            family="laplace_iir",
            mode="bandpass",
            params={
                "period": float(params["period_bars"]),
                "q": float(params["q"]),
            },
            output_kind="component",
        ),
    )
    signal = signal_from_filtered(component, output_kind="component")
    return pd.Series(signal.to_numpy(dtype=float), index=frame.index)


def _iir_lowpass_target(
    frame: pd.DataFrame, params: BenchmarkParameters
) -> pd.Series:
    level = apply_filter_spec(
        _log_close(frame),
        FilterSpec(
            name="market_state_tool_iir_lowpass",
            family="laplace_iir",
            mode="lowpass",
            params={
                "period": float(params["period_bars"]),
                "q": float(params["q"]),
            },
            output_kind="level",
        ),
    )
    signal = signal_from_filtered(level, output_kind="level")
    return pd.Series(signal.to_numpy(dtype=float), index=frame.index)


def _butterworth_target(
    frame: pd.DataFrame, params: BenchmarkParameters
) -> pd.Series:
    component = butterworth_bandpass_component(
        _log_close(frame),
        short_period_bars=int(params["short_period_bars"]),
        long_period_bars=int(params["long_period_bars"]),
        order=int(params["order"]),
    )
    signal = signal_from_filtered(component, output_kind="component")
    return pd.Series(signal.to_numpy(dtype=float), index=frame.index)


def _fourier_bandpass_target(
    frame: pd.DataFrame, params: BenchmarkParameters
) -> pd.Series:
    component = apply_filter_spec(
        _log_close(frame),
        FilterSpec(
            name="market_state_tool_fourier_bandpass",
            family="fourier_rolling",
            mode="bandpass",
            params={
                "window": int(params["window_bars"]),
                "low_period": float(params["low_period_bars"]),
                "high_period": float(params["high_period_bars"]),
            },
            output_kind="component",
        ),
    )
    signal = signal_from_filtered(component, output_kind="component")
    return pd.Series(signal.to_numpy(dtype=float), index=frame.index)


def _haar_wavelet_bandpass_target(
    frame: pd.DataFrame, params: BenchmarkParameters
) -> pd.Series:
    component = apply_filter_spec(
        _log_close(frame),
        FilterSpec(
            name="market_state_tool_haar_wavelet_bandpass",
            family="wavelet_haar",
            mode="bandpass",
            params={
                "window": int(params["window_bars"]),
                "level": int(params["level"]),
                "slow_level": int(params["slow_level"]),
            },
            output_kind="component",
        ),
    )
    signal = signal_from_filtered(component, output_kind="component")
    return pd.Series(signal.to_numpy(dtype=float), index=frame.index)


def _r3_component_target(
    frame: pd.DataFrame, params: BenchmarkParameters
) -> pd.Series:
    fast = int(params["fast_window_bars"])
    slow = int(params["slow_window_bars"])
    log_close = pd.Series(_log_close(frame).to_numpy(dtype=float), index=frame.index)
    component = (
        log_close - log_close.rolling(fast, min_periods=fast).mean()
    ).rolling(slow, min_periods=slow).mean()
    signal = signal_from_filtered(component, output_kind="component")
    return pd.Series(signal.to_numpy(dtype=float), index=frame.index)


def _volatility_channel_target(
    frame: pd.DataFrame, params: BenchmarkParameters
) -> pd.Series:
    window = int(params["window_bars"])
    width = float(params["width_sigma"])
    close = frame["close"].astype(float)
    center = close.rolling(window, min_periods=window).mean().shift(1)
    sigma = close.rolling(window, min_periods=window).std(ddof=0).shift(1)
    enter = close > center + width * sigma
    exit_ = close < center
    return _stateful_long_cash(enter, exit_)


def _frequency_bollinger_target(
    frame: pd.DataFrame, params: BenchmarkParameters
) -> pd.Series:
    """Use the native V58 15m channel and its native close decision."""

    close = pd.Series(
        frame["close"].to_numpy(dtype=float),
        index=pd.DatetimeIndex(frame["timestamp"]),
        dtype=float,
    )
    spec = FrequencyBollingerSpec(
        period_bars=int(params["period_bars"]),
        thickness_source=str(params["thickness_source"]),
        window_multiplier=float(params["window_multiplier"]),
        width_multiplier=float(params["width_multiplier"]),
        action=str(params["action"]),
        filter_order=int(params["filter_order"]),
        band_upper_frequency_ratio=float(params.get("band_upper_frequency_ratio", 2.0)),
    )
    channel = build_frequency_bollinger(close, spec)
    decision = channel_decision(channel, spec.action)
    return pd.Series(decision.to_numpy(dtype=float), index=frame.index)


def _lowpass_residual_target(
    frame: pd.DataFrame, params: BenchmarkParameters
) -> pd.Series:
    """Probe the native V58 geometry through its declared low-pass direction."""

    spec = LowpassResidualEnvelopeSpec(
        cutoff_period_bars=int(params["cutoff_period_bars"]),
        lowpass_order=int(params["lowpass_order"]),
        thickness_window_bars=int(params["thickness_window_bars"]),
        thickness_lower_quantile=float(params["thickness_lower_quantile"]),
        thickness_upper_quantile=float(params["thickness_upper_quantile"]),
        thickness_smoothing_half_life_bars=float(
            params["thickness_smoothing_half_life_bars"]
        ),
        warmup_bars=int(params["warmup_bars"]),
    )
    geometry = build_causal_lowpass_residual_envelope(frame, spec)
    line = pd.Series(
        geometry["lowpass_mid"].to_numpy(dtype=float),
        index=frame.index,
    )
    valid = pd.Series(
        geometry["v58_geometry_valid"].to_numpy(dtype=bool),
        index=frame.index,
    )
    return direction_decision(line, valid=valid).astype(float)


def _asymmetric_arc_target(
    frame: pd.DataFrame, params: BenchmarkParameters
) -> pd.Series:
    """Probe the native V57 state-space geometry through its declared midline."""

    spec = AsymmetricArcEnvelopeSpec(
        candidate_periods_bars=tuple(
            int(params[f"candidate_period_{index}"]) for index in range(1, 5)
        ),
        round_top_sharp_bottom_ratio=float(
            params["round_top_sharp_bottom_ratio"]
        ),
        initial_amplitude_log=float(params["initial_amplitude_log"]),
        initial_observation_sigma_log=float(
            params["initial_observation_sigma_log"]
        ),
        score_half_life_bars=float(params["score_half_life_bars"]),
        model_weight_half_life_bars=float(
            params["model_weight_half_life_bars"]
        ),
        model_score_temperature=float(params["model_score_temperature"]),
        observation_variance_half_life_bars=float(
            params["observation_variance_half_life_bars"]
        ),
        thickness_window_bars=int(params["thickness_window_bars"]),
        thickness_lower_quantile=float(params["thickness_lower_quantile"]),
        thickness_upper_quantile=float(params["thickness_upper_quantile"]),
        thickness_smoothing_half_life_bars=float(
            params["thickness_smoothing_half_life_bars"]
        ),
        warmup_bars=int(params["warmup_bars"]),
    )
    geometry = build_causal_asymmetric_arc_envelope(frame, spec)
    line = pd.Series(geometry["arc_mid"].to_numpy(dtype=float), index=frame.index)
    valid = pd.Series(
        geometry["arc_geometry_valid"].to_numpy(dtype=bool), index=frame.index
    )
    return direction_decision(line, valid=valid).astype(float)


def _price_channel_target(
    frame: pd.DataFrame, params: BenchmarkParameters
) -> pd.Series:
    entry_window = int(params["entry_window_bars"])
    exit_window = int(params["exit_window_bars"])
    upper = (
        frame["high"].rolling(entry_window, min_periods=entry_window).max().shift(1)
    )
    lower = frame["low"].rolling(exit_window, min_periods=exit_window).min().shift(1)
    return _stateful_long_cash(frame["close"] > upper, frame["close"] < lower)


def _trendline_channel_target(
    frame: pd.DataFrame, params: BenchmarkParameters
) -> pd.Series:
    window = int(params["window_bars"])
    rail_sigma = float(params["rail_sigma"])
    values = np.log(frame["close"].to_numpy(dtype=float))
    slope = np.full(len(values), np.nan, dtype=float)
    lower_rail = np.full(len(values), np.nan, dtype=float)
    x = np.arange(window, dtype=float)
    x_centered = x - x.mean()
    denominator = float(np.dot(x_centered, x_centered))
    for position in range(window, len(values)):
        history = values[position - window : position]
        history_mean = float(history.mean())
        beta = float(np.dot(x_centered, history - history_mean) / denominator)
        intercept = history_mean - beta * float(x.mean())
        fitted = intercept + beta * x
        residual_sigma = float(np.std(history - fitted, ddof=0))
        prediction = intercept + beta * float(window)
        slope[position] = beta
        lower_rail[position] = prediction - rail_sigma * residual_sigma
    close_log = pd.Series(values, index=frame.index)
    slope_series = pd.Series(slope, index=frame.index)
    lower = pd.Series(lower_rail, index=frame.index)
    enter = slope_series.gt(0.0) & close_log.ge(lower)
    exit_ = slope_series.le(0.0) | close_log.lt(lower)
    return _stateful_long_cash(enter, exit_)


def _moving_average_target(
    frame: pd.DataFrame, params: BenchmarkParameters
) -> pd.Series:
    fast = int(params["fast_window_bars"])
    slow = int(params["slow_window_bars"])
    close = frame["close"].astype(float)
    fast_average = close.rolling(fast, min_periods=fast).mean()
    slow_average = close.rolling(slow, min_periods=slow).mean()
    return cast(pd.Series, (fast_average > slow_average).astype(float))


def _stateful_long_cash(enter: pd.Series, exit_: pd.Series) -> pd.Series:
    state = 0.0
    values: list[float] = []
    for should_enter, should_exit in zip(
        enter.fillna(False).to_numpy(dtype=bool),
        exit_.fillna(False).to_numpy(dtype=bool),
        strict=True,
    ):
        if should_exit:
            state = 0.0
        elif should_enter:
            state = 1.0
        values.append(state)
    return pd.Series(values, index=enter.index, dtype="float64")


def _completed_episode_outcomes(
    panel: pd.DataFrame,
    *,
    active: pd.Series,
    value_column: str,
) -> pd.Series:
    """Attach each completed episode outcome to its causal entry decision."""

    mask = active.fillna(False).to_numpy(dtype=bool)
    values = pd.to_numeric(panel[value_column], errors="coerce").to_numpy(dtype=float)
    outcomes = np.full(len(panel), np.nan, dtype=float)
    start: int | None = None
    total = 0.0
    for position, is_active in enumerate(mask):
        if is_active and start is None:
            start = position
            total = 0.0
        if start is not None:
            value = values[position]
            if np.isfinite(value):
                total += float(value)
        next_active = bool(mask[position + 1]) if position + 1 < len(mask) else is_active
        if start is not None and is_active and not next_active:
            # The transition cost lives on the first inactive row.  Include it
            # before closing the episode if that row exists.
            if position + 1 < len(mask):
                exit_value = values[position + 1]
                if np.isfinite(exit_value):
                    total += float(exit_value)
            outcomes[start] = total
            start = None
            total = 0.0
    # Open episodes at the research boundary are deliberately not labelled.
    return pd.Series(outcomes, index=panel.index, dtype="float64")


__all__ = [
    "TOOL_BENCHMARK_PANEL_SCHEMA_ID",
    "run_tool_benchmark",
    "run_tool_benchmark_profile",
]
