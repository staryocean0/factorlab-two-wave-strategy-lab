import numpy as np
import pandas as pd

from factor_lab.visual_structure import EndpointChannelConfig, compute_endpoint_channel
from factor_lab.visual_structure.endpoint_channel import (
    component_turn_candidates,
    select_turn_candidates,
)


def test_per_kind_gap_keeps_nearby_opposite_kind_turns() -> None:
    candidates = [(10, "peak"), (12, "trough"), (13, "peak"), (28, "trough")]

    global_selected, global_skipped = select_turn_candidates(
        candidates,
        min_turn_gap_bars=5,
        mode="global_gap",
    )
    per_kind_selected, per_kind_skipped = select_turn_candidates(
        candidates,
        min_turn_gap_bars=5,
        mode="per_kind_gap",
    )

    assert global_selected == [(10, "peak"), (28, "trough")]
    assert [item[:2] for item in global_skipped] == [(12, "trough"), (13, "peak")]
    assert per_kind_selected == [(10, "peak"), (12, "trough"), (28, "trough")]
    assert [item[:2] for item in per_kind_skipped] == [(13, "peak")]


def test_endpoint_channel_adds_latest_visual_guard_for_current_bar() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=9, freq="h"),
            "high": [10.0, 12.0, 14.0, 13.0, 11.0, 12.0, 13.0, 12.0, 16.0],
            "low": [9.0, 10.0, 11.0, 10.0, 8.0, 9.0, 10.0, 9.0, 15.0],
            "close": [9.5, 11.0, 13.0, 12.0, 9.0, 10.0, 12.0, 10.5, 15.5],
        }
    )
    component = np.asarray([0.0, 1.0, 2.0, 1.0, 0.0, -1.0, 0.0, 0.5, 0.75])

    result = compute_endpoint_channel(
        frame,
        component,
        config=EndpointChannelConfig(
            map_window_bars=1,
            min_turn_gap_bars=2,
            max_extrapolate_bars=3,
            append_terminal_observed_anchor=False,
            append_latest_visual_guard=True,
        ),
    )

    assert component_turn_candidates(component) == [(3, "peak"), (6, "trough")]
    assert result.stats["latest_visual_guard_peak"] is True
    assert result.stats["latest_visual_guard_trough"] is True
    assert result.upper[-1] >= frame["close"].iloc[-1]
    assert result.lower[-1] <= frame["close"].iloc[-1]
