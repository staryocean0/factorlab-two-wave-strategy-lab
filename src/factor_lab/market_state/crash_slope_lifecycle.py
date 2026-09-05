"""Causal intraday slope diagnostics around ex-post decline episodes.

The episode peak and trough are research labels.  They must never be consumed
by a live rule.  Candidate slope activations use only the current and trailing
bars; the labels are joined afterwards to measure recall and false hits.
"""

# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportOperatorIssue=false

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
import pandas as pd

from factor_lab.market_state.downside_bucket_morphology import describe_decline_path
from factor_lab.strategy.services.risk_off_state_bucket_evaluation import (
    zigzag_decline_segments,
)

FIELD_LABELS_ZH: Final[dict[str, str]] = {
    "event_id": "暴跌事件编号",
    "event_level": "事件层级",
    "threshold": "峰谷下跌确认阈值",
    "daily_anchor_peak": "日线完整回撤背景高点",
    "daily_trough": "日线最低点",
    "rebound_confirmation": "反弹确认点",
    "intraday_anchor_peak": "日内精确背景高点",
    "intraday_trough": "日内精确最低点",
    "impulse_reference_peak": "冲击腿参考高点",
    "impulse_slope_run_start": "本轮OLS下行状态起点",
    "impulse_slope_onset": "持续下行斜率启动点",
    "frequency": "K线级别",
    "downside_slope_bps_per_day": "下行OLS斜率（基点/交易日）",
    "slope_r_squared": "OLS拟合优度",
    "duration_minutes": "持续交易分钟数",
    "remaining_decline_share": "首次命中后剩余跌幅占比",
    "precision": "命中精确率",
    "event_recall": "暴跌事件召回率",
    "false_activations_per_year": "每年假命中次数",
}


@dataclass(frozen=True)
class IntradaySlopeSpec:
    """Physical-time specification shared by 5m and 15m carriers."""

    slope_window_minutes: int = 120
    onset_fraction_of_event_maximum: float = 0.20
    onset_minimum_bps_per_day: float = 50.0
    onset_sustain_minutes: int = 60
    onset_sustain_share: float = 0.75
    minimum_stage_minutes: int = 30

    def __post_init__(self) -> None:
        if self.slope_window_minutes <= 0 or self.onset_sustain_minutes <= 0:
            raise ValueError("physical windows must be positive")
        if not 0.0 < self.onset_fraction_of_event_maximum < 1.0:
            raise ValueError("onset_fraction_of_event_maximum must lie in (0, 1)")
        if self.onset_minimum_bps_per_day < 0.0:
            raise ValueError("onset_minimum_bps_per_day must be non-negative")
        if not 0.0 < self.onset_sustain_share <= 1.0:
            raise ValueError("onset_sustain_share must lie in (0, 1]")


def bars_per_day(frequency: str) -> int:
    """Return the A-share trading-bar count for a supported carrier."""

    mapping = {"5m": 48, "15m": 16}
    if frequency not in mapping:
        raise ValueError(f"unsupported frequency: {frequency}")
    return mapping[frequency]


def minutes_per_bar(frequency: str) -> int:
    """Return physical minutes per supported bar."""

    mapping = {"5m": 5, "15m": 15}
    if frequency not in mapping:
        raise ValueError(f"unsupported frequency: {frequency}")
    return mapping[frequency]


def validate_ohlc(frame: pd.DataFrame, *, expected_frequency: str | None = None) -> pd.DataFrame:
    """Return sorted finite OHLC without silently repairing malformed rows."""

    required = {"timestamp", "open", "high", "low", "close"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"missing OHLC columns: {sorted(missing)}")
    result = frame.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], errors="raise")
    result = result.sort_values("timestamp", kind="stable").reset_index(drop=True)
    if result.empty or result["timestamp"].duplicated().any():
        raise ValueError("OHLC timestamps must be non-empty and unique")
    values = result[["open", "high", "low", "close"]].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(values.to_numpy(float)).all() or (values <= 0.0).any().any():
        raise ValueError("OHLC values must be finite and positive")
    if (values["high"] < values[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError("OHLC high is inconsistent")
    if (values["low"] > values[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("OHLC low is inconsistent")
    result[["open", "high", "low", "close"]] = values
    if expected_frequency is not None and "frequency" in result:
        observed = set(result["frequency"].dropna().astype(str).unique())
        if observed != {expected_frequency}:
            raise ValueError(f"expected frequency {expected_frequency}, observed {sorted(observed)}")
    return result


def rolling_downside_slope_panel(
    intraday_ohlc: pd.DataFrame,
    *,
    frequency: str,
    slope_window_minutes: int = 120,
) -> pd.DataFrame:
    """Build a prefix-invariant trailing OLS slope panel.

    Downside slope is positive when the fitted log-price line points down.  It
    is expressed in basis points per trading day so 5m and 15m carriers share
    one physical threshold grid.
    """

    frame = validate_ohlc(intraday_ohlc, expected_frequency=frequency)
    minute = minutes_per_bar(frequency)
    window = max(3, int(np.ceil(slope_window_minutes / minute)))
    log_close = np.log(frame["close"].to_numpy(float))
    x = np.arange(window, dtype=float)
    x_mean = float(x.mean())
    denominator = float(np.square(x - x_mean).sum())
    rolling = pd.Series(log_close).rolling(window, min_periods=window)
    sum_y = rolling.sum()
    sum_xy = rolling.apply(lambda values: float(np.dot(values, x)), raw=True)
    beta = (sum_xy - x_mean * sum_y) / denominator
    sum_y2 = pd.Series(np.square(log_close)).rolling(window, min_periods=window).sum()
    centered_y2 = sum_y2 - np.square(sum_y) / window
    covariance = sum_xy - x_mean * sum_y
    r_squared = (np.square(covariance) / (denominator * centered_y2.replace(0.0, np.nan))).clip(0.0, 1.0)
    scale = float(bars_per_day(frequency) * 10_000)
    result = frame.copy()
    result["slope_window_bars"] = window
    result["slope_log_per_bar"] = beta.to_numpy(float)
    result["downside_slope_bps_per_day"] = np.clip(-beta.to_numpy(float) * scale, 0.0, None)
    result["slope_r_squared"] = r_squared.to_numpy(float)
    result.attrs["field_labels_zh"] = dict(FIELD_LABELS_ZH)
    return result


def _period(timestamp: pd.Timestamp) -> str:
    if timestamp < pd.Timestamp("2018-01-01"):
        return "2009-2017_development"
    if timestamp < pd.Timestamp("2021-01-01"):
        return "2018-2020_audit"
    return "2021-2026_resealed_blackbox"


def build_decline_event_ledger(
    daily_ohlc: pd.DataFrame,
    five_minute_ohlc: pd.DataFrame,
    *,
    thresholds: tuple[float, ...] = (0.05, 0.10, 0.15),
    start: str = "2009-01-01",
) -> pd.DataFrame:
    """Build hierarchical ex-post decline labels with refined 5m extrema."""

    daily = validate_ohlc(daily_ohlc)
    five = validate_ohlc(five_minute_ohlc, expected_frequency="5m")
    if tuple(sorted(set(thresholds))) != thresholds:
        raise ValueError("thresholds must be unique and increasing")
    timestamp = pd.DatetimeIndex(daily["timestamp"])
    close = pd.Series(daily["close"].to_numpy(float), index=timestamp)
    log_close = np.log(close)
    log_open = pd.Series(np.log(daily["open"].to_numpy(float)), index=timestamp)
    rows: list[dict[str, object]] = []
    level = {thresholds[0]: "leg", thresholds[1]: "episode", thresholds[2]: "major"}
    for threshold in thresholds:
        sequence = 0
        for peak, trough, rebound in zigzag_decline_segments(close, threshold):
            peak_time = timestamp[peak]
            trough_time = timestamp[trough]
            if peak_time < pd.Timestamp(start):
                continue
            local = five.loc[
                five["timestamp"].between(peak_time.normalize(), trough_time.normalize() + pd.Timedelta(days=1), inclusive="left")
            ]
            if local.empty:
                continue
            peak_location = int(local["high"].to_numpy(float).argmax())
            refined = local.iloc[peak_location:].copy()
            trough_location = int(refined["low"].to_numpy(float).argmin())
            refined_peak = local.iloc[peak_location]
            refined_trough = refined.iloc[trough_location]
            if pd.Timestamp(refined_trough["timestamp"]) <= pd.Timestamp(refined_peak["timestamp"]):
                continue
            sequence += 1
            shape = describe_decline_path(
                log_close.iloc[peak : trough + 1],
                log_open.iloc[peak : trough + 1],
            )
            event_id = f"decline_{int(round(threshold * 100)):02d}pct:{sequence:04d}"
            rows.append(
                {
                    "event_id": event_id,
                    "event_level": level[threshold],
                    "threshold": threshold,
                    "period": _period(peak_time),
                    "daily_anchor_peak": peak_time,
                    "daily_trough": trough_time,
                    "rebound_confirmation": timestamp[rebound] if rebound is not None else pd.NaT,
                    "intraday_anchor_peak": pd.Timestamp(refined_peak["timestamp"]),
                    "intraday_anchor_high": float(refined_peak["high"]),
                    "intraday_trough": pd.Timestamp(refined_trough["timestamp"]),
                    "intraday_trough_low": float(refined_trough["low"]),
                    "intraday_log_decline": float(np.log(float(refined_peak["high"]) / float(refined_trough["low"]))),
                    "parent_episode_id": "",
                    **shape,
                }
            )
    ledger = pd.DataFrame(rows).sort_values(["threshold", "daily_anchor_peak"], kind="stable").reset_index(drop=True)
    episodes = ledger.loc[ledger["event_level"].eq("episode")]
    for location, row in ledger.loc[~ledger["event_level"].eq("episode")].iterrows():
        overlap = episodes.loc[
            (episodes["intraday_anchor_peak"] <= row["intraday_trough"]) & (episodes["intraday_trough"] >= row["intraday_anchor_peak"])
        ]
        if overlap.empty:
            continue
        overlap_size = np.minimum(
            overlap["intraday_trough"].astype("int64"),
            pd.Timestamp(row["intraday_trough"]).value,
        ) - np.maximum(
            overlap["intraday_anchor_peak"].astype("int64"),
            pd.Timestamp(row["intraday_anchor_peak"]).value,
        )
        ledger.loc[location, "parent_episode_id"] = str(overlap.iloc[int(np.argmax(overlap_size))]["event_id"])
    ledger.attrs["field_labels_zh"] = dict(FIELD_LABELS_ZH)
    return ledger


def _first_sustained_location(values: np.ndarray, threshold: float, bars: int, share: float) -> int:
    active = np.asarray(values >= threshold, dtype=float)
    if len(active) < bars:
        return 0
    count = np.convolve(active, np.ones(bars, dtype=float), mode="valid")
    eligible = np.flatnonzero(count >= np.ceil(bars * share))
    return int(eligible[0]) if len(eligible) else int(np.nanargmax(values))


def _compress_short_stages(labels: np.ndarray, minimum_bars: int) -> np.ndarray:
    result = labels.astype(object).copy()
    if minimum_bars <= 1 or len(result) == 0:
        return result
    for _ in range(12):
        starts = np.r_[0, np.flatnonzero(result[1:] != result[:-1]) + 1]
        ends = np.r_[starts[1:], len(result)]
        short = [(start, end) for start, end in zip(starts, ends, strict=True) if end - start < minimum_bars]
        if not short:
            break
        changed = False
        for start, end in short:
            if start > 0:
                replacement = result[start - 1]
            elif end < len(result):
                replacement = result[end]
            else:
                continue
            result[start:end] = replacement
            changed = True
        if not changed:
            break
    return result


def build_event_slope_stages(
    event_ledger: pd.DataFrame,
    slope_panel: pd.DataFrame,
    *,
    frequency: str,
    spec: IntradaySlopeSpec = IntradaySlopeSpec(),
    event_level: str = "episode",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Attach post-hoc impulse anchors and run-length slope stages to events."""

    panel = slope_panel.reset_index(drop=True)
    minute = minutes_per_bar(frequency)
    sustain = max(1, int(np.ceil(spec.onset_sustain_minutes / minute)))
    minimum_stage = max(1, int(np.ceil(spec.minimum_stage_minutes / minute)))
    events = event_ledger.loc[event_ledger["event_level"].eq(event_level)].copy()
    event_updates: list[dict[str, object]] = []
    stage_rows: list[dict[str, object]] = []
    trace_rows: list[pd.DataFrame] = []
    for event in events.itertuples(index=False):
        local = panel.loc[panel["timestamp"].between(event.intraday_anchor_peak, event.intraday_trough)].copy()
        local = local.loc[np.isfinite(local["downside_slope_bps_per_day"])].reset_index(drop=True)
        if local.empty:
            continue
        slope = local["downside_slope_bps_per_day"].to_numpy(float)
        maximum = float(np.max(slope))
        threshold = max(spec.onset_minimum_bps_per_day, maximum * spec.onset_fraction_of_event_maximum)
        onset = _first_sustained_location(slope, threshold, sustain, spec.onset_sustain_share)
        maximum_location = int(np.argmax(slope))
        signed_slope = local["slope_log_per_bar"].to_numpy(float)
        prior_non_down = np.flatnonzero(signed_slope[:onset] >= 0.0)
        slope_run_start = int(prior_non_down[-1] + 1) if len(prior_non_down) else 0
        prior_start = max(0, slope_run_start - 1)
        reference_slice = local.iloc[prior_start : onset + 1]
        reference_row = reference_slice.iloc[int(reference_slice["high"].to_numpy(float).argmax())]
        impulse = local.iloc[onset:].copy().reset_index(drop=True)
        impulse_slope = impulse["downside_slope_bps_per_day"].to_numpy(float)
        impulse_signed_slope = impulse["slope_log_per_bar"].to_numpy(float)
        ratio = impulse_slope / max(maximum, 1e-12)
        labels = np.select(
            [impulse_signed_slope >= 0.0, ratio >= 0.75, ratio >= 0.50, ratio >= 0.25],
            ["rebound_or_flat", "extreme", "strong", "moderate"],
            default="weak",
        ).astype(object)
        labels = _compress_short_stages(labels, minimum_stage)
        impulse["slope_intensity_band"] = labels
        trace = local.copy()
        trace["slope_intensity_band"] = "pre_onset"
        trace.loc[onset:, "slope_intensity_band"] = labels
        trace["event_id"] = event.event_id
        trace["frequency"] = frequency
        trace["event_relative_location"] = np.arange(len(trace), dtype=int)
        trace_rows.append(
            trace[
                [
                    "event_id",
                    "frequency",
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "downside_slope_bps_per_day",
                    "slope_r_squared",
                    "slope_intensity_band",
                    "event_relative_location",
                ]
            ]
        )
        groups = impulse["slope_intensity_band"].ne(impulse["slope_intensity_band"].shift()).cumsum()
        previous_median = np.nan
        for stage_number, (_, stage) in enumerate(impulse.groupby(groups, sort=False), start=1):
            first = stage.iloc[0]
            last = stage.iloc[-1]
            median_slope = float(stage["downside_slope_bps_per_day"].median())
            stage_rows.append(
                {
                    "event_id": event.event_id,
                    "frequency": frequency,
                    "stage_number": stage_number,
                    "slope_intensity_band": str(first["slope_intensity_band"]),
                    "stage_start": pd.Timestamp(first["timestamp"]),
                    "stage_end": pd.Timestamp(last["timestamp"]),
                    "bar_count": len(stage),
                    "duration_minutes": len(stage) * minute,
                    "median_downside_slope_bps_per_day": median_slope,
                    "maximum_downside_slope_bps_per_day": float(stage["downside_slope_bps_per_day"].max()),
                    "median_slope_r_squared": float(stage["slope_r_squared"].median()),
                    "stage_log_return": float(np.log(float(last["close"]) / float(first["close"]))),
                    "slope_acceleration_from_previous": median_slope - previous_median if np.isfinite(previous_median) else np.nan,
                    "lifecycle_phase": (
                        "accelerating"
                        if int(stage.index[-1]) + onset < maximum_location
                        else "decelerating"
                        if int(stage.index[0]) + onset > maximum_location
                        else "maximum_slope"
                    ),
                }
            )
            previous_median = median_slope
        trough_row = local.iloc[-1]
        event_updates.append(
            {
                "event_id": event.event_id,
                "frequency": frequency,
                "impulse_reference_peak": pd.Timestamp(reference_row["timestamp"]),
                "impulse_reference_high": float(reference_row["high"]),
                "impulse_slope_run_start": pd.Timestamp(local.iloc[slope_run_start]["timestamp"]),
                "impulse_slope_onset": pd.Timestamp(local.iloc[onset]["timestamp"]),
                "onset_downside_slope_bps_per_day": float(slope[onset]),
                "maximum_slope_timestamp": pd.Timestamp(local.iloc[maximum_location]["timestamp"]),
                "maximum_downside_slope_bps_per_day": maximum,
                "trough_downside_slope_bps_per_day": float(trough_row["downside_slope_bps_per_day"]),
                "onset_to_maximum_bars": max(0, maximum_location - onset),
                "onset_to_trough_bars": max(0, len(local) - 1 - onset),
                "onset_to_maximum_minutes": max(0, maximum_location - onset) * minute,
                "onset_to_trough_minutes": max(0, len(local) - 1 - onset) * minute,
            }
        )
    updates = pd.DataFrame(event_updates)
    stages = pd.DataFrame(stage_rows)
    traces = pd.concat(trace_rows, ignore_index=True) if trace_rows else pd.DataFrame()
    for frame in (updates, stages, traces):
        frame.attrs["field_labels_zh"] = dict(FIELD_LABELS_ZH)
    return updates, stages, traces


def consecutive_true_age(condition: pd.Series) -> np.ndarray:
    """Return causal run length of a Boolean condition."""

    values = condition.fillna(False).to_numpy(bool)
    result = np.zeros(len(values), dtype=np.int32)
    age = 0
    for location, active in enumerate(values):
        age = age + 1 if active else 0
        result[location] = age
    return result


def build_slope_duration_activations(
    slope_panel: pd.DataFrame,
    *,
    frequency: str,
    slope_threshold_bps_per_day: float,
    duration_minutes: int,
) -> pd.DataFrame:
    """Return only first causal activations of one slope-duration rule."""

    if slope_threshold_bps_per_day <= 0.0 or duration_minutes <= 0:
        raise ValueError("slope threshold and duration must be positive")
    bars = max(1, int(np.ceil(duration_minutes / minutes_per_bar(frequency))))
    condition = slope_panel["downside_slope_bps_per_day"].ge(slope_threshold_bps_per_day)
    age = consecutive_true_age(condition)
    activation = age == bars
    result = slope_panel.loc[activation, ["timestamp", "close", "downside_slope_bps_per_day", "slope_r_squared"]].copy()
    result["frequency"] = frequency
    result["slope_threshold_bps_per_day"] = slope_threshold_bps_per_day
    result["duration_minutes"] = duration_minutes
    result["duration_bars"] = bars
    result["signal_run_age_bars"] = age[activation]
    return result.reset_index(drop=True)


def match_activations_to_events(
    activations: pd.DataFrame,
    event_ledger: pd.DataFrame,
    *,
    target_threshold: float,
) -> pd.DataFrame:
    """Join causal activations to already-built ex-post event intervals."""

    events = event_ledger.loc[event_ledger["threshold"].eq(target_threshold)].sort_values("intraday_anchor_peak").copy()
    left = activations.sort_values("timestamp").copy()
    right = events[
        [
            "event_id",
            "period",
            "intraday_anchor_peak",
            "intraday_anchor_high",
            "intraday_trough",
            "intraday_trough_low",
            "intraday_log_decline",
        ]
    ].copy()
    matched = pd.merge_asof(
        left,
        right,
        left_on="timestamp",
        right_on="intraday_anchor_peak",
        direction="backward",
        allow_exact_matches=True,
    )
    inside = matched["intraday_trough"].notna() & matched["timestamp"].le(matched["intraday_trough"])
    matched.loc[~inside, "event_id"] = np.nan
    matched["is_true_activation"] = matched["event_id"].notna()
    numerator = np.log(matched["close"] / matched["intraday_trough_low"])
    matched["remaining_decline_share"] = (numerator / matched["intraday_log_decline"]).clip(0.0, 1.0)
    matched.loc[~matched["is_true_activation"], "remaining_decline_share"] = np.nan
    matched["target_threshold"] = target_threshold
    return matched


def summarize_activation_surface(
    matched: pd.DataFrame,
    event_ledger: pd.DataFrame,
    *,
    target_threshold: float,
    period: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> dict[str, object]:
    """Summarize precision, recall and remaining opportunity for one cell."""

    local = matched.loc[matched["timestamp"].between(start, end, inclusive="left")].copy()
    events = event_ledger.loc[
        event_ledger["threshold"].eq(target_threshold) & event_ledger["intraday_anchor_peak"].between(start, end, inclusive="left")
    ]
    true = local.loc[local["is_true_activation"]]
    subthreshold = local.get("is_subthreshold_activation", pd.Series(False, index=local.index)).fillna(False).astype(bool)
    noise = ~local["is_true_activation"] & ~subthreshold
    years = max((end - start).days / 365.2425, 1e-12)
    eligible_ids = set(events["event_id"].astype(str))
    event_hits = int(matched.loc[matched["event_id"].isin(eligible_ids), "event_id"].nunique())
    return {
        "period": period,
        "target_threshold": target_threshold,
        "activation_count": len(local),
        "true_activation_count": len(true),
        "false_activation_count": int((~local["is_true_activation"]).sum()),
        "subthreshold_activation_count": int(subthreshold.sum()),
        "noise_activation_count": int(noise.sum()),
        "precision": float(true.shape[0] / len(local)) if len(local) else np.nan,
        "eligible_event_count": len(events),
        "hit_event_count": event_hits,
        "event_recall": float(event_hits / len(events)) if len(events) else np.nan,
        "false_activations_per_year": float((~local["is_true_activation"]).sum() / years),
        "median_remaining_decline_share": float(true["remaining_decline_share"].median()) if len(true) else np.nan,
    }


def crash_slope_lifecycle_contract() -> dict[str, object]:
    """Return the authority boundary for generated ledgers and surfaces."""

    return {
        "schema_id": "market_state_crash_slope_lifecycle@1.1",
        "episode_labels_are_ex_post": True,
        "daily_anchor_and_trough_are_runtime_features": False,
        "impulse_reference_and_stage_boundaries_are_runtime_features": False,
        "candidate_slope_activations_are_prefix_invariant": True,
        "candidate_action_timing": "activation_bar_close_then_next_bar_execution_if_used_later",
        "selection_data_end_exclusive": "2021-01-01",
        "development_period": ["2009-01-01", "2018-01-01"],
        "dynamic_parameter_audit_period": ["2018-01-01", "2021-01-01"],
        "post_2020_selection_forbidden": True,
        "post_2020_detail_persistence_forbidden": True,
        "post_2020_aggregate_recheck_only": True,
        "production_authority": False,
        "strategy_route_authority": False,
        "field_labels_zh": dict(FIELD_LABELS_ZH),
    }
