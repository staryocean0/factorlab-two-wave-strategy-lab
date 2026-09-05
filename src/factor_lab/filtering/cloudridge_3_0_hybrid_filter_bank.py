# pyright: reportAny=false, reportExplicitAny=false, reportMissingTypeStubs=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportArgumentType=false
# pyright: reportAttributeAccessIssue=false, reportIndexIssue=false
# pyright: reportCallIssue=false, reportGeneralTypeIssues=false
# pyright: reportOperatorIssue=false, reportAssignmentType=false
# pyright: reportPrivateUsage=false, reportUnnecessaryCast=false
# pyright: reportCallInDefaultInitializer=false, reportUnreachable=false
"""Causal hybrid filter-bank and event-clock buckets for CloudRidge 3.0.

The current carrier remains a Laplace biquad band-pass.  Faster and slower
context components can instead use Butterworth filters with explicit period
bounds.  A parent observation is locked at the start of one current-band
event and expires at the next current-band direction switch; no fixed-bar
forecast horizon is part of this contract.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final, Literal, cast

import numpy as np
import pandas as pd
from scipy import signal

from factor_lab.filtering.timing_validation import (
    FilterSpec,
    _biquad_coefficients,
    apply_filter_spec,
)

FilterBankFamily = Literal["all_iir", "hybrid", "all_butter"]
EventPolicy = Literal[
    "naked_current",
    "parent_agreement",
    "child_confirmation",
    "parent_child_confirmation",
    "train_selected_buckets",
]

CURRENT_Q_GRID: Final[tuple[float, ...]] = (0.5, 1.0, 2.0)
DEFAULT_BUTTER_ORDER: Final[int] = 4
EVENT_POLICIES: Final[tuple[EventPolicy, ...]] = (
    "naked_current",
    "parent_agreement",
    "child_confirmation",
    "parent_child_confirmation",
    "train_selected_buckets",
)


@dataclass(frozen=True, slots=True)
class HybridFilterBankSpec:
    """One scale-derived causal fast/current/slow filter bank."""

    current_period_bars: int = 160
    current_q: float = 1.0
    butter_order: int = DEFAULT_BUTTER_ORDER
    family: FilterBankFamily = "hybrid"

    def __post_init__(self) -> None:
        if self.current_period_bars < 16 or self.current_period_bars % 8:
            raise ValueError("current_period_bars must be divisible by 8 and >= 16")
        if not any(math.isclose(self.current_q, q) for q in CURRENT_Q_GRID):
            raise ValueError("current_q must come from the frozen 0.5/1/2 grid")
        if self.butter_order < 1:
            raise ValueError("butter_order must be positive")
        if self.family not in {"all_iir", "hybrid", "all_butter"}:
            raise ValueError(f"unsupported filter-bank family: {self.family}")

    @property
    def fast_center_bars(self) -> int:
        return self.current_period_bars // 4

    @property
    def slow_center_bars(self) -> int:
        return self.current_period_bars * 4

    @property
    def explicit_period_bands(self) -> dict[str, tuple[int, int]]:
        current = self.current_period_bars
        return {
            "fast": (current // 8, current // 2),
            "current": (current // 2, current * 2),
            "slow": (current * 2, current * 8),
        }

    @property
    def spec_id(self) -> str:
        q_id = f"{self.current_q:g}".replace(".", "p")
        return (
            f"{self.family}_p{self.current_period_bars}_q{q_id}_"
            f"butter{self.butter_order}"
        )


def _validate_log_close(log_close: pd.Series) -> pd.Series:
    numeric = cast(pd.Series, pd.to_numeric(log_close, errors="coerce")).astype(float)
    if not isinstance(numeric.index, pd.DatetimeIndex):
        raise TypeError("log_close index must be a DatetimeIndex")
    if not numeric.index.is_monotonic_increasing or numeric.index.has_duplicates:
        raise ValueError("log_close index must be sorted and unique")
    if len(numeric) < 8 or numeric.isna().any():
        raise ValueError("log_close requires at least eight finite observations")
    if not np.isfinite(numeric.to_numpy(float)).all():
        raise ValueError("log_close must be finite")
    return numeric


def butterworth_bandpass_component(
    log_close: pd.Series,
    *,
    short_period_bars: int,
    long_period_bars: int,
    order: int = DEFAULT_BUTTER_ORDER,
) -> pd.Series:
    """Return a causal Butterworth component for one explicit period band."""

    clean = _validate_log_close(log_close)
    if short_period_bars < 3 or long_period_bars <= short_period_bars:
        raise ValueError("explicit period bounds must satisfy 3 <= short < long")
    if order < 1:
        raise ValueError("Butterworth order must be positive")
    high_frequency = 1.0 / float(short_period_bars)
    low_frequency = 1.0 / float(long_period_bars)
    if high_frequency >= 0.5:
        raise ValueError("short period must remain below the Nyquist frequency")
    sos = signal.butter(
        order,
        [low_frequency, high_frequency],
        btype="bandpass",
        fs=1.0,
        output="sos",
    )
    source = clean.to_numpy(float)
    # Band-pass filters reject levels.  Anchoring to the first observed level
    # avoids a large recursive start-up transient without using future data.
    filtered = signal.sosfilt(sos, source - source[0])
    result = pd.Series(filtered, index=clean.index, dtype=float)
    result.iloc[: min(len(result), long_period_bars)] = np.nan
    return result


def _iir_component(log_close: pd.Series, period_bars: int, q: float) -> pd.Series:
    spec = FilterSpec(
        name=f"laplace_iir_bp_p{period_bars}_q{q:g}",
        family="laplace_iir",
        mode="bandpass",
        params={"period": period_bars, "q": q},
        output_kind="component",
    )
    return apply_filter_spec(log_close, spec)


def component_delta_direction(component: pd.Series) -> pd.Series:
    """Return the carried sign of ``delta(component)`` after causal warm-up."""

    numeric = cast(pd.Series, pd.to_numeric(component, errors="coerce")).astype(float)
    delta = numeric.diff()
    raw = pd.Series(np.sign(delta.to_numpy(float)), index=numeric.index, dtype=float)
    raw.loc[delta.isna()] = np.nan
    carried = cast(pd.Series, raw.replace(0.0, np.nan).ffill())
    carried.loc[numeric.isna()] = np.nan
    return carried.rename("component_delta_direction")


def frequency_state_key(
    fast_direction: pd.Series,
    current_direction: pd.Series,
    slow_direction: pd.Series,
) -> pd.Series:
    """Encode the eight states, leaving warm-up rows explicitly missing."""

    aligned = pd.concat(
        [
            fast_direction.rename("fast"),
            current_direction.rename("current"),
            slow_direction.rename("slow"),
        ],
        axis=1,
    )
    valid = aligned.notna().all(axis=1)
    out = pd.Series(pd.NA, index=aligned.index, dtype="string")
    if bool(valid.any()):
        selected = aligned.loc[valid]
        fast = np.where(selected["fast"].gt(0.0), "fast_up", "fast_down")
        current = np.where(
            selected["current"].gt(0.0), "current_up", "current_down"
        )
        slow = np.where(selected["slow"].gt(0.0), "slow_up", "slow_down")
        out.loc[valid] = [
            f"{left}|{middle}|{right}"
            for left, middle, right in zip(fast, current, slow, strict=True)
        ]
    return out.rename("frequency_state")


def build_filter_bank_panel(
    log_close: pd.Series,
    spec: HybridFilterBankSpec | None = None,
) -> pd.DataFrame:
    """Build one causal component/direction panel for the frozen bank."""

    clean = _validate_log_close(log_close)
    selected = spec or HybridFilterBankSpec()
    bands = selected.explicit_period_bands
    if selected.family == "all_iir":
        fast = _iir_component(clean, selected.fast_center_bars, 1.0)
        current = _iir_component(
            clean, selected.current_period_bars, selected.current_q
        )
        slow = _iir_component(clean, selected.slow_center_bars, 1.0)
    else:
        fast = butterworth_bandpass_component(
            clean,
            short_period_bars=bands["fast"][0],
            long_period_bars=bands["fast"][1],
            order=selected.butter_order,
        )
        slow = butterworth_bandpass_component(
            clean,
            short_period_bars=bands["slow"][0],
            long_period_bars=bands["slow"][1],
            order=selected.butter_order,
        )
        if selected.family == "all_butter":
            current = butterworth_bandpass_component(
                clean,
                short_period_bars=bands["current"][0],
                long_period_bars=bands["current"][1],
                order=selected.butter_order,
            )
        else:
            current = _iir_component(
                clean, selected.current_period_bars, selected.current_q
            )
    fast_direction = component_delta_direction(fast)
    current_direction = component_delta_direction(current)
    slow_direction = component_delta_direction(slow)
    panel = pd.DataFrame(index=clean.index)
    panel.index.name = "timestamp"
    panel["log_close"] = clean
    panel["log_return"] = clean.diff().fillna(0.0)
    panel["component_fast"] = fast
    panel["component_current"] = current
    panel["component_slow"] = slow
    panel["direction_fast"] = fast_direction
    panel["direction_current"] = current_direction
    panel["direction_slow"] = slow_direction
    panel["frequency_state"] = frequency_state_key(
        fast_direction, current_direction, slow_direction
    )
    panel["bank_spec_id"] = selected.spec_id
    return panel


def _direction_segments(panel: pd.DataFrame) -> list[tuple[int, int]]:
    required = {
        "direction_fast",
        "direction_current",
        "direction_slow",
        "frequency_state",
    }
    missing = sorted(required.difference(panel.columns))
    if missing:
        raise KeyError(f"filter-bank panel missing columns: {missing}")
    valid = panel[list(required - {"frequency_state"})].notna().all(axis=1)
    positions = np.flatnonzero(valid.to_numpy())
    if not len(positions):
        return []
    current = panel["direction_current"].to_numpy(float)
    starts = [int(positions[0])]
    previous = int(positions[0])
    for raw_position in positions[1:]:
        position = int(raw_position)
        if position != previous + 1 or current[position] != current[previous]:
            starts.append(position)
        previous = position
    return [
        (start, starts[index + 1] if index + 1 < len(starts) else len(panel))
        for index, start in enumerate(starts)
    ]


def extract_current_band_events(
    panel: pd.DataFrame,
    *,
    carrier_id: str = "cloudridge",
) -> pd.DataFrame:
    """Create variable-duration current-band events ending at the next switch."""

    segments = _direction_segments(panel)
    rows: list[dict[str, object]] = []
    for event_number, (start, stop) in enumerate(segments):
        complete = stop < len(panel)
        if not complete:
            continue
        start_time = pd.Timestamp(panel.index[start])
        next_time = pd.Timestamp(panel.index[stop])
        event_return = float(
            panel["log_close"].iloc[stop] - panel["log_close"].iloc[start]
        )
        current_direction = int(np.sign(float(panel["direction_current"].iloc[start])))
        rows.append(
            {
                "carrier_id": carrier_id,
                "event_id": f"{carrier_id}:{event_number:06d}",
                "event_start_timestamp": start_time,
                "next_current_event_timestamp": next_time,
                "onset_position": start,
                "next_event_position": stop,
                "event_duration_bars": stop - start,
                "fast_direction": int(
                    np.sign(float(panel["direction_fast"].iloc[start]))
                ),
                "current_direction": current_direction,
                "slow_direction": int(
                    np.sign(float(panel["direction_slow"].iloc[start]))
                ),
                "frequency_state": str(panel["frequency_state"].iloc[start]),
                "event_log_return": event_return,
                "current_aligned_event_log_return": current_direction * event_return,
                "complete_before_next_event": True,
                "fixed_horizon_bars": None,
            }
        )
    return pd.DataFrame(rows)


def build_event_locked_signal(
    panel: pd.DataFrame,
    policy: EventPolicy,
    *,
    approved_buckets: frozenset[str] | None = None,
) -> pd.Series:
    """Build a veto/delay-only signal inside each current-band event."""

    if policy not in EVENT_POLICIES:
        raise ValueError(f"unsupported event policy: {policy}")
    approved = approved_buckets or frozenset()
    signal_values = np.zeros(len(panel), dtype=float)
    fast = panel["direction_fast"].to_numpy(float)
    current = panel["direction_current"].to_numpy(float)
    slow = panel["direction_slow"].to_numpy(float)
    states = panel["frequency_state"].astype("string")
    for start, stop in _direction_segments(panel):
        if current[start] <= 0.0:
            continue
        if policy == "naked_current":
            signal_values[start:stop] = 1.0
            continue
        if policy == "parent_agreement":
            if slow[start] > 0.0:
                signal_values[start:stop] = 1.0
            continue
        if policy == "train_selected_buckets":
            if str(states.iloc[start]) in approved:
                signal_values[start:stop] = 1.0
            continue
        if policy == "parent_child_confirmation" and slow[start] <= 0.0:
            continue
        fast_up = np.flatnonzero(fast[start:stop] > 0.0)
        if len(fast_up):
            confirmation = start + int(fast_up[0])
            signal_values[confirmation:stop] = 1.0
    return pd.Series(signal_values, index=panel.index, name=policy)


def fit_positive_mid_up_buckets(
    events: pd.DataFrame,
    *,
    train_end: pd.Timestamp,
    min_events: int = 12,
    minimum_event_log_return: float = 0.0007,
    minimum_positive_windows: int = 2,
    minimum_carriers: int = 1,
) -> tuple[frozenset[str], pd.DataFrame]:
    """Approve only completed train-era up-event buckets with stable value."""

    if min_events < 1 or not 1 <= minimum_positive_windows <= 3:
        raise ValueError("bucket stability thresholds are invalid")
    required = {
        "carrier_id",
        "event_start_timestamp",
        "next_current_event_timestamp",
        "current_direction",
        "frequency_state",
        "event_log_return",
    }
    missing = sorted(required.difference(events.columns))
    if missing:
        raise KeyError(f"event frame missing columns: {missing}")
    eligible = events.loc[
        events["next_current_event_timestamp"].le(train_end)
        & events["current_direction"].eq(1)
    ].copy()
    columns = [
        "frequency_state",
        "event_count",
        "carrier_count",
        "mean_event_log_return",
        "positive_window_count",
        "approved",
    ]
    if eligible.empty:
        return frozenset(), pd.DataFrame(columns=columns)
    times = pd.to_datetime(eligible["event_start_timestamp"])
    low = int(times.min().value)
    high = int(times.max().value)
    width = max(high - low, 1)
    window = np.floor(3.0 * (times.astype("int64") - low) / (width + 1)).astype(int)
    eligible["training_window"] = np.clip(window, 0, 2)
    rows: list[dict[str, object]] = []
    approved: set[str] = set()
    for state, group in eligible.groupby("frequency_state", sort=True):
        positive_windows = 0
        for _window, window_group in group.groupby("training_window"):
            window_mean = float(window_group["event_log_return"].mean())
            if window_mean > minimum_event_log_return:
                positive_windows += 1
        row = {
            "frequency_state": str(state),
            "event_count": int(len(group)),
            "carrier_count": int(group["carrier_id"].nunique()),
            "mean_event_log_return": float(group["event_log_return"].mean()),
            "positive_window_count": positive_windows,
        }
        is_approved = bool(
            row["event_count"] >= min_events
            and row["carrier_count"] >= minimum_carriers
            and row["mean_event_log_return"] > minimum_event_log_return
            and positive_windows >= minimum_positive_windows
        )
        row["approved"] = is_approved
        rows.append(row)
        if is_approved:
            approved.add(str(state))
    return frozenset(approved), pd.DataFrame(rows, columns=columns)


def summarize_event_buckets(events: pd.DataFrame) -> pd.DataFrame:
    """Summarize each exact onset bucket on its next current-band event."""

    if events.empty:
        return pd.DataFrame()
    grouped = events.groupby("frequency_state", sort=True)
    rows: list[dict[str, object]] = []
    for state, group in grouped:
        aligned = group["current_aligned_event_log_return"].astype(float)
        rows.append(
            {
                "frequency_state": str(state),
                "event_count": int(len(group)),
                "carrier_count": int(group["carrier_id"].nunique()),
                "median_event_duration_bars": float(
                    group["event_duration_bars"].median()
                ),
                "mean_event_log_return": float(group["event_log_return"].mean()),
                "mean_current_aligned_event_log_return": float(aligned.mean()),
                "aligned_positive_share": float(aligned.gt(0.0).mean()),
            }
        )
    return pd.DataFrame(rows)


def _iir_response(period_bars: int, q: float, frequencies: np.ndarray) -> np.ndarray:
    b0, b1, b2, a1, a2 = _biquad_coefficients("bandpass", period_bars, q)
    _freq, response = signal.freqz(
        [b0, b1, b2], [1.0, a1, a2], worN=frequencies, fs=1.0
    )
    return cast(np.ndarray, response)


def _butter_response(
    short_period_bars: int,
    long_period_bars: int,
    order: int,
    frequencies: np.ndarray,
) -> np.ndarray:
    sos = signal.butter(
        order,
        [1.0 / long_period_bars, 1.0 / short_period_bars],
        btype="bandpass",
        fs=1.0,
        output="sos",
    )
    _freq, response = signal.sosfreqz(sos, worN=frequencies, fs=1.0)
    return cast(np.ndarray, response)


def frequency_response_audit(
    spec: HybridFilterBankSpec,
    *,
    points: int = 32768,
) -> pd.DataFrame:
    """Quantify response overlap and nominal-band energy for one bank."""

    if points < 1024:
        raise ValueError("frequency response audit requires at least 1024 points")
    frequencies = np.linspace(1e-7, 0.5 - 1e-7, points)
    bands = spec.explicit_period_bands
    if spec.family == "all_iir":
        responses = {
            "fast": _iir_response(spec.fast_center_bars, 1.0, frequencies),
            "current": _iir_response(
                spec.current_period_bars, spec.current_q, frequencies
            ),
            "slow": _iir_response(spec.slow_center_bars, 1.0, frequencies),
        }
    else:
        responses = {
            "fast": _butter_response(*bands["fast"], spec.butter_order, frequencies),
            "slow": _butter_response(*bands["slow"], spec.butter_order, frequencies),
        }
        responses["current"] = (
            _butter_response(
                *bands["current"], spec.butter_order, frequencies
            )
            if spec.family == "all_butter"
            else _iir_response(spec.current_period_bars, spec.current_q, frequencies)
        )
    rows: list[dict[str, object]] = []
    for name, response in responses.items():
        magnitude_squared = np.abs(response) ** 2
        short_period, long_period = bands[name]
        inside = (frequencies >= 1.0 / long_period) & (
            frequencies <= 1.0 / short_period
        )
        rows.append(
            {
                "bank_spec_id": spec.spec_id,
                "bank_family": spec.family,
                "audit_type": "nominal_band_energy_share",
                "left_component": name,
                "right_component": "nominal_band",
                "value": float(
                    magnitude_squared[inside].sum() / magnitude_squared.sum()
                ),
                "short_period_bars": short_period,
                "long_period_bars": long_period,
            }
        )
    names = ("fast", "current", "slow")
    for left_index, left_name in enumerate(names):
        for right_name in names[left_index + 1 :]:
            left = np.abs(responses[left_name])
            right = np.abs(responses[right_name])
            rows.append(
                {
                    "bank_spec_id": spec.spec_id,
                    "bank_family": spec.family,
                    "audit_type": "magnitude_overlap_cosine",
                    "left_component": left_name,
                    "right_component": right_name,
                    "value": float(
                        np.dot(left, right)
                        / (np.linalg.norm(left) * np.linalg.norm(right))
                    ),
                    "short_period_bars": None,
                    "long_period_bars": None,
                }
            )
    return pd.DataFrame(rows)
