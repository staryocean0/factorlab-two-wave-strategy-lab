"""Scale-aware endpoint channel extraction.

The endpoint channel is a posterior visual skeleton:

1. A scale component, such as a 40D bandpass component, supplies candidate
   peak/trough turns.
2. Each turn maps back to the raw price high/low in a bounded neighborhood.
3. Same-kind endpoints are connected into upper/lower polylines.
4. The midline is the geometric center between upper and lower lines.

This is deliberately separated from trading logic.  The default configuration
uses per-kind turn spacing so peak candidates do not suppress nearby trough
candidates, which was the source of visible missing endpoints in the first
prototype.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd
from numpy.typing import NDArray

TurnGapMode = Literal["global_gap", "per_kind_gap"]


@dataclass(frozen=True, slots=True)
class EndpointChannelConfig:
    """Configuration for posterior endpoint-channel extraction."""

    map_window_bars: int = 30
    min_turn_gap_bars: int = 15
    max_extrapolate_bars: int = 120
    turn_gap_mode: TurnGapMode = "per_kind_gap"
    append_terminal_observed_anchor: bool = True
    append_latest_visual_guard: bool = True

    def __post_init__(self) -> None:
        if self.map_window_bars < 0:
            raise ValueError("map_window_bars must be >= 0")
        if self.min_turn_gap_bars < 1:
            raise ValueError("min_turn_gap_bars must be >= 1")
        if self.max_extrapolate_bars < 0:
            raise ValueError("max_extrapolate_bars must be >= 0")
        if self.turn_gap_mode not in ("global_gap", "per_kind_gap"):
            raise ValueError(f"unsupported turn_gap_mode: {self.turn_gap_mode}")


@dataclass(frozen=True, slots=True)
class EndpointAnchor:
    """One mapped raw-price endpoint."""

    idx: int
    turn_idx: int
    confirm_idx: int
    kind: Literal["peak", "trough"]
    log_price: float
    price: float
    timestamp: Any = None
    endpoint_timestamp: Any = None
    terminal_observed: bool = False
    latest_visual_guard: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "idx": self.idx,
            "turn_idx": self.turn_idx,
            "confirm_idx": self.confirm_idx,
            "kind": self.kind,
            "log_price": self.log_price,
            "price": self.price,
            "timestamp": self.timestamp,
            "endpoint_timestamp": self.endpoint_timestamp,
            "terminal_observed": self.terminal_observed,
            "latest_visual_guard": self.latest_visual_guard,
        }


@dataclass(frozen=True, slots=True)
class EndpointChannelResult:
    """Endpoint channel arrays and diagnostics."""

    upper: NDArray[np.float64]
    mid: NDArray[np.float64]
    lower: NDArray[np.float64]
    mid_slope: NDArray[np.float64]
    peak_anchors: list[EndpointAnchor]
    trough_anchors: list[EndpointAnchor]
    selected_turns: list[tuple[int, str]]
    skipped_turns: list[tuple[int, str, int]]
    turn_candidates: list[tuple[int, str]]
    stats: dict[str, Any]


def component_turn_candidates(component: pd.Series | NDArray[np.float64]) -> list[tuple[int, str]]:
    values = np.asarray(component, dtype=float)
    if len(values) < 2:
        return []
    delta = np.diff(values, prepend=values[0])
    sign = np.sign(delta)
    for idx in range(1, len(sign)):
        if sign[idx] == 0.0:
            sign[idx] = sign[idx - 1]

    candidates: list[tuple[int, str]] = []
    for idx in range(1, len(sign)):
        if sign[idx - 1] > 0 and sign[idx] < 0:
            candidates.append((idx, "peak"))
        elif sign[idx - 1] < 0 and sign[idx] > 0:
            candidates.append((idx, "trough"))
    return candidates


def select_turn_candidates(
    candidates: list[tuple[int, str]],
    *,
    min_turn_gap_bars: int,
    mode: TurnGapMode = "per_kind_gap",
) -> tuple[list[tuple[int, str]], list[tuple[int, str, int]]]:
    selected: list[tuple[int, str]] = []
    skipped: list[tuple[int, str, int]] = []
    if mode == "global_gap":
        last = -(10**9)
        for idx, kind in candidates:
            gap = idx - last
            if gap < min_turn_gap_bars:
                skipped.append((idx, kind, gap))
                continue
            selected.append((idx, kind))
            last = idx
        return selected, skipped

    last_by_kind = {"peak": -(10**9), "trough": -(10**9)}
    for idx, kind in candidates:
        gap = idx - last_by_kind[kind]
        if gap < min_turn_gap_bars:
            skipped.append((idx, kind, gap))
            continue
        selected.append((idx, kind))
        last_by_kind[kind] = idx
    return selected, skipped


def _timestamp_at(frame: pd.DataFrame, column: str | None, idx: int) -> Any:
    if not column or column not in frame.columns:
        return None
    return frame[column].iloc[idx]


def _raw_endpoint_index(
    frame: pd.DataFrame,
    *,
    turn_idx: int,
    kind: str,
    window: int,
    high_column: str,
    low_column: str,
) -> int:
    lo = max(0, int(turn_idx) - window)
    hi = min(len(frame) - 1, int(turn_idx) + window)
    field = high_column if kind == "peak" else low_column
    values = pd.to_numeric(frame[field].iloc[lo : hi + 1], errors="coerce").to_numpy(float)
    if not len(values) or not np.isfinite(values).any():
        return int(turn_idx)
    offset = int(np.nanargmax(values) if kind == "peak" else np.nanargmin(values))
    return int(lo + offset)


def _dedupe_anchors(anchors: list[EndpointAnchor], kind: str) -> list[EndpointAnchor]:
    by_idx: dict[int, EndpointAnchor] = {}
    for anchor in anchors:
        if anchor.kind != kind:
            continue
        current = by_idx.get(anchor.idx)
        if current is None:
            by_idx[anchor.idx] = anchor
            continue
        if kind == "peak" and anchor.log_price > current.log_price:
            by_idx[anchor.idx] = anchor
        elif kind == "trough" and anchor.log_price < current.log_price:
            by_idx[anchor.idx] = anchor
    return sorted(by_idx.values(), key=lambda item: item.idx)


def _append_terminal_observed_anchor(
    anchors: list[EndpointAnchor],
    *,
    kind: Literal["peak", "trough"],
    log_values: NDArray[np.float64],
) -> list[EndpointAnchor]:
    if not anchors:
        return anchors
    start_idx = anchors[-1].idx + 1
    if start_idx >= len(log_values):
        return anchors
    window = log_values[start_idx:]
    if not len(window) or not np.isfinite(window).any():
        return anchors
    offset = int(np.nanargmax(window) if kind == "peak" else np.nanargmin(window))
    idx = int(start_idx + offset)
    if idx <= anchors[-1].idx:
        return anchors
    log_price = float(log_values[idx])
    return [
        *anchors,
        EndpointAnchor(
            idx=idx,
            turn_idx=idx,
            confirm_idx=idx,
            kind=kind,
            log_price=log_price,
            price=float(math.exp(log_price)),
            terminal_observed=True,
        ),
    ]


def _append_latest_visual_guard_anchor(
    anchors: list[EndpointAnchor],
    *,
    kind: Literal["peak", "trough"],
    log_values: NDArray[np.float64],
) -> list[EndpointAnchor]:
    if not anchors or not len(log_values):
        return anchors
    idx = len(log_values) - 1
    if anchors[-1].idx >= idx:
        return anchors
    log_price = float(log_values[idx])
    return [
        *anchors,
        EndpointAnchor(
            idx=idx,
            turn_idx=idx,
            confirm_idx=idx,
            kind=kind,
            log_price=log_price,
            price=float(math.exp(log_price)),
            latest_visual_guard=True,
        ),
    ]


def _fill_anchor_polyline(
    anchors: list[EndpointAnchor],
    values: NDArray[np.float64],
    slopes: NDArray[np.float64],
    *,
    max_extrapolate_bars: int,
) -> int:
    if len(anchors) < 2:
        return 0

    segment_count = 0
    n = len(values)
    pairs = list(zip(anchors[:-1], anchors[1:], strict=True))
    fill_ranges: list[tuple[int, int, EndpointAnchor, EndpointAnchor]] = []
    for left, right in pairs:
        fill_ranges.append((left.idx, right.idx, left, right))
        segment_count += 1

    last_left, last_right = pairs[-1]
    if last_right.idx < n - 1 and max_extrapolate_bars > 0:
        end_idx = min(n - 1, last_right.idx + max_extrapolate_bars)
        fill_ranges.append((last_right.idx + 1, end_idx, last_left, last_right))

    for start_idx, end_idx, left, right in fill_ranges:
        if end_idx < start_idx or right.idx == left.idx:
            continue
        slope = (right.log_price - left.log_price) / (right.idx - left.idx)
        for idx in range(max(0, start_idx), min(n - 1, end_idx) + 1):
            values[idx] = left.log_price + slope * (idx - left.idx)
            slopes[idx] = slope
    return segment_count


def compute_endpoint_channel(
    frame: pd.DataFrame,
    component: pd.Series | NDArray[np.float64],
    *,
    config: EndpointChannelConfig | None = None,
    timestamp_column: str | None = "timestamp",
    high_column: str = "high",
    low_column: str = "low",
    close_column: str = "close",
) -> EndpointChannelResult:
    """Compute a posterior endpoint channel from raw OHLC and a scale component."""

    cfg = config or EndpointChannelConfig()
    if len(frame) != len(component):
        raise ValueError("frame and component must have the same length")
    if frame.empty:
        empty = np.asarray([], dtype=float)
        return EndpointChannelResult(
            upper=empty,
            mid=empty,
            lower=empty,
            mid_slope=empty,
            peak_anchors=[],
            trough_anchors=[],
            selected_turns=[],
            skipped_turns=[],
            turn_candidates=[],
            stats={"point_count": 0},
        )

    high = pd.to_numeric(frame[high_column], errors="coerce").to_numpy(float)
    low = pd.to_numeric(frame[low_column], errors="coerce").to_numpy(float)
    close = pd.to_numeric(frame[close_column], errors="coerce").to_numpy(float)
    log_high = np.log(np.clip(high, 1e-12, None))
    log_low = np.log(np.clip(low, 1e-12, None))

    candidates = component_turn_candidates(component)
    selected_turns, skipped_turns = select_turn_candidates(
        candidates,
        min_turn_gap_bars=cfg.min_turn_gap_bars,
        mode=cfg.turn_gap_mode,
    )

    anchors: list[EndpointAnchor] = []
    for turn_idx, kind_value in selected_turns:
        kind = "peak" if kind_value == "peak" else "trough"
        endpoint_idx = _raw_endpoint_index(
            frame,
            turn_idx=turn_idx,
            kind=kind,
            window=cfg.map_window_bars,
            high_column=high_column,
            low_column=low_column,
        )
        endpoint_log = float(log_high[endpoint_idx] if kind == "peak" else log_low[endpoint_idx])
        anchors.append(
            EndpointAnchor(
                idx=endpoint_idx,
                turn_idx=int(turn_idx),
                confirm_idx=int(max(turn_idx, endpoint_idx)),
                kind=kind,
                log_price=endpoint_log,
                price=float(math.exp(endpoint_log)),
                timestamp=_timestamp_at(frame, timestamp_column, int(turn_idx)),
                endpoint_timestamp=_timestamp_at(frame, timestamp_column, int(endpoint_idx)),
            )
        )

    peak_anchors = _dedupe_anchors(anchors, "peak")
    trough_anchors = _dedupe_anchors(anchors, "trough")
    if cfg.append_terminal_observed_anchor:
        peak_anchors = _append_terminal_observed_anchor(peak_anchors, kind="peak", log_values=log_high)
        trough_anchors = _append_terminal_observed_anchor(trough_anchors, kind="trough", log_values=log_low)
    if cfg.append_latest_visual_guard:
        peak_anchors = _append_latest_visual_guard_anchor(peak_anchors, kind="peak", log_values=log_high)
        trough_anchors = _append_latest_visual_guard_anchor(trough_anchors, kind="trough", log_values=log_low)

    upper_log = np.full(len(frame), np.nan)
    lower_log = np.full(len(frame), np.nan)
    upper_slope = np.full(len(frame), np.nan)
    lower_slope = np.full(len(frame), np.nan)
    upper_segment_count = _fill_anchor_polyline(
        peak_anchors,
        upper_log,
        upper_slope,
        max_extrapolate_bars=cfg.max_extrapolate_bars,
    )
    lower_segment_count = _fill_anchor_polyline(
        trough_anchors,
        lower_log,
        lower_slope,
        max_extrapolate_bars=cfg.max_extrapolate_bars,
    )

    finite_channel = np.isfinite(upper_log) & np.isfinite(lower_log)
    crossed = finite_channel & (upper_log <= lower_log)
    if crossed.any():
        upper_fixed = np.maximum(upper_log[crossed], lower_log[crossed])
        lower_fixed = np.minimum(upper_log[crossed], lower_log[crossed])
        upper_log[crossed] = upper_fixed
        lower_log[crossed] = lower_fixed

    upper = np.full(len(frame), np.nan)
    mid = np.full(len(frame), np.nan)
    lower = np.full(len(frame), np.nan)
    mid_slope = np.full(len(frame), np.nan)
    finite_channel = np.isfinite(upper_log) & np.isfinite(lower_log)
    upper[finite_channel] = np.exp(upper_log[finite_channel])
    lower[finite_channel] = np.exp(lower_log[finite_channel])
    mid[finite_channel] = np.exp(0.5 * (upper_log[finite_channel] + lower_log[finite_channel]))
    finite_slope = finite_channel & np.isfinite(upper_slope) & np.isfinite(lower_slope)
    mid_slope[finite_slope] = 0.5 * (upper_slope[finite_slope] + lower_slope[finite_slope])

    finite_full = finite_channel & np.isfinite(close)
    close_outside = finite_full & ((close > upper) | (close < lower))
    finite_upper = np.isfinite(upper) & np.isfinite(close) & (close > 0)
    stats = {
        "point_count": int(len(frame)),
        "turn_gap_mode": cfg.turn_gap_mode,
        "map_window_bars": int(cfg.map_window_bars),
        "min_turn_gap_bars": int(cfg.min_turn_gap_bars),
        "max_extrapolate_bars": int(cfg.max_extrapolate_bars),
        "turn_candidate_count": int(len(candidates)),
        "selected_turn_count": int(len(selected_turns)),
        "skipped_turn_count": int(len(skipped_turns)),
        "peak_anchor_count": int(len(peak_anchors)),
        "trough_anchor_count": int(len(trough_anchors)),
        "upper_segment_count": int(upper_segment_count),
        "lower_segment_count": int(lower_segment_count),
        "non_null_mid_count": int(np.isfinite(mid).sum()),
        "close_outside_channel_count": int(close_outside.sum()),
        "close_outside_channel_ratio": float(close_outside.sum() / max(int(finite_full.sum()), 1)),
        "max_upper_close_ratio": float(np.nanmax(upper[finite_upper] / close[finite_upper]))
        if finite_upper.any()
        else None,
        "posterior_visual_channel": True,
        "causal_for_trading": False,
        "latest_visual_guard_peak": bool(peak_anchors[-1].latest_visual_guard) if peak_anchors else False,
        "latest_visual_guard_trough": bool(trough_anchors[-1].latest_visual_guard) if trough_anchors else False,
    }
    return EndpointChannelResult(
        upper=upper,
        mid=mid,
        lower=lower,
        mid_slope=mid_slope,
        peak_anchors=peak_anchors,
        trough_anchors=trough_anchors,
        selected_turns=selected_turns,
        skipped_turns=skipped_turns,
        turn_candidates=candidates,
        stats=stats,
    )
