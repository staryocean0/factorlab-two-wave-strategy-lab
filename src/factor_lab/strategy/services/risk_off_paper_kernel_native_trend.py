# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportCallInDefaultInitializer=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Paper-native multiscale trend state machine for Risk-Off research.

The strategy consumes the twelve strictly lagged EWMA trend signals directly.
It does not consume W72, V56, V60, a channel, or any of the thirteen timing
tools.  W72 may only appear outside this module as an evaluation benchmark.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

import pandas as pd

PAPER_SIGNAL_SPANS: Final[tuple[int, ...]] = (
    5,
    10,
    15,
    20,
    30,
    60,
    100,
    150,
    200,
    300,
    400,
    500,
)
SCALE_GROUPS: Final[Mapping[str, tuple[int, ...]]] = {
    "fast": (5, 10, 15, 20),
    "middle": (30, 60, 100, 150),
    "slow": (200, 300, 400, 500),
}


def signal_column(span: int) -> str:
    """Return the authoritative lagged paper-signal column."""

    if span not in PAPER_SIGNAL_SPANS:
        raise ValueError(f"span must be one of {PAPER_SIGNAL_SPANS}")
    return f"paper_signal_s{span}_t_minus_1"


@dataclass(frozen=True, slots=True)
class PaperKernelNativeTrendSpec:
    """Low-degree native strategy parameters in standardized signal units."""

    risk_entry_score: float = -2.5
    fast_recovery_score: float = 0.0

    def __post_init__(self) -> None:
        if not self.risk_entry_score < self.fast_recovery_score:
            raise ValueError("risk entry must be below the recovery score")
        if self.risk_entry_score >= 0.0:
            raise ValueError("risk entry score must be negative")


def build_paper_native_scale_state(
    paper_panel: pd.DataFrame,
) -> pd.DataFrame:
    """Build same-date cross-scale scores without another time average."""

    required = {"timestamp"} | {
        signal_column(span) for span in PAPER_SIGNAL_SPANS
    }
    missing = sorted(required.difference(paper_panel.columns))
    if missing:
        raise KeyError(f"paper panel missing columns: {missing}")
    timestamp = pd.DatetimeIndex(
        pd.to_datetime(paper_panel["timestamp"], errors="raise"),
    )
    if timestamp.has_duplicates or not timestamp.is_monotonic_increasing:
        raise ValueError("paper timestamps must be ordered and unique")
    signals = pd.DataFrame(
        {
            signal_column(span): pd.to_numeric(
                paper_panel[signal_column(span)],
                errors="coerce",
            ).to_numpy(float)
            for span in PAPER_SIGNAL_SPANS
        },
        index=timestamp,
    )
    state = signals.copy()
    for group, spans in SCALE_GROUPS.items():
        state[f"paper_{group}_score"] = signals[
            [signal_column(span) for span in spans]
        ].mean(axis=1)
    score_columns = [f"paper_{group}_score" for group in SCALE_GROUPS]
    state["paper_scale_state_valid"] = state[score_columns].notna().all(axis=1)
    state["paper_weakest_scale_group"] = (
        state[score_columns]
        .idxmin(axis=1)
        .str.removeprefix("paper_")
        .str.removesuffix("_score")
    ).where(state["paper_scale_state_valid"], "unavailable")
    state["paper_weakest_scale_score"] = state[score_columns].min(axis=1).where(
        state["paper_scale_state_valid"],
    )
    state["second_temporal_average_applied"] = False
    state["runtime_uses_future"] = False
    return state


def align_paper_native_scale_state(
    state: pd.DataFrame,
    completed_close_index: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Expose one lagged-signal row at its close, never before its timestamp."""

    if (
        completed_close_index.empty
        or completed_close_index.has_duplicates
        or not completed_close_index.is_monotonic_increasing
    ):
        raise ValueError("completed_close_index must be non-empty and ordered")
    if (
        state.empty
        or not isinstance(state.index, pd.DatetimeIndex)
        or state.index.has_duplicates
        or not state.index.is_monotonic_increasing
    ):
        raise ValueError("state must be a non-empty ordered daily frame")
    required = {
        "paper_fast_score",
        "paper_middle_score",
        "paper_slow_score",
        "paper_weakest_scale_group",
        "paper_weakest_scale_score",
        "paper_scale_state_valid",
    }
    missing = sorted(required.difference(state.columns))
    if missing:
        raise KeyError(f"paper state missing columns: {missing}")
    daily = state.loc[:, sorted(required)].copy()
    daily["paper_state_timestamp"] = daily.index
    aligned = pd.merge_asof(
        pd.DataFrame({"decision_timestamp": completed_close_index}),
        daily.reset_index(drop=True).sort_values("paper_state_timestamp"),
        left_on="decision_timestamp",
        right_on="paper_state_timestamp",
        direction="backward",
        allow_exact_matches=True,
    ).set_index("decision_timestamp")
    if bool(
        aligned["paper_state_timestamp"]
        .gt(aligned.index)
        .fillna(False)
        .any(),
    ):
        raise AssertionError("future paper state reached a strategy decision")
    aligned["paper_scale_state_valid"] = aligned[
        "paper_scale_state_valid"
    ].fillna(False)
    aligned["paper_weakest_scale_group"] = aligned[
        "paper_weakest_scale_group"
    ].fillna("unavailable")
    aligned["runtime_uses_future"] = False
    return aligned


def route_paper_native_trend(
    aligned_state: pd.DataFrame,
    spec: PaperKernelNativeTrendSpec | None = None,
) -> pd.DataFrame:
    """Route the weakest entry scale and use the fast score for recovery."""

    spec = spec or PaperKernelNativeTrendSpec()
    required = {
        "paper_fast_score",
        "paper_weakest_scale_group",
        "paper_weakest_scale_score",
        "paper_scale_state_valid",
    }
    missing = sorted(required.difference(aligned_state.columns))
    if missing:
        raise KeyError(f"aligned state missing columns: {missing}")
    if (
        aligned_state.empty
        or not isinstance(aligned_state.index, pd.DatetimeIndex)
        or aligned_state.index.has_duplicates
        or not aligned_state.index.is_monotonic_increasing
    ):
        raise ValueError("aligned_state must be a non-empty ordered frame")
    risk_active = False
    owner = "none"
    long_decisions: list[float] = []
    risk_states: list[bool] = []
    owners: list[str] = []
    transitions: list[str] = []
    for row in aligned_state.itertuples():
        transition = "hold_state"
        valid = bool(row.paper_scale_state_valid)
        if not risk_active:
            if valid and float(row.paper_weakest_scale_score) <= spec.risk_entry_score:
                risk_active = True
                owner = str(row.paper_weakest_scale_group)
                transition = "enter_risk"
        elif valid and float(row.paper_fast_score) >= spec.fast_recovery_score:
            risk_active = False
            owner = "none"
            transition = "recover_long"
        long_decisions.append(0.0 if risk_active else 1.0)
        risk_states.append(risk_active)
        owners.append(owner)
        transitions.append(transition)
    decision = pd.Series(
        long_decisions,
        index=aligned_state.index,
        dtype=float,
    )
    return pd.DataFrame(
        {
            "paper_native_risk_decision": risk_states,
            "paper_native_route_owner": owners,
            "paper_native_transition": transitions,
            "decision_long_for_next_bar": decision,
            "executable_long_position": decision.shift(1, fill_value=0.0),
            "single_execution_shift": True,
            "runtime_uses_future": False,
        },
        index=aligned_state.index,
    )


def paper_native_trend_contract() -> Mapping[str, object]:
    """Return the frozen V0 research contract."""

    return {
        "schema_id": "risk_off_paper_kernel_native_trend@1.0",
        "strategy_identity": "paper_native_multiscale_trend_v0",
        "paper_signal_spans": list(PAPER_SIGNAL_SPANS),
        "scale_groups": {
            group: list(spans) for group, spans in SCALE_GROUPS.items()
        },
        "group_score_formula": "same_timestamp_equal_weight_mean",
        "second_temporal_average_applied": False,
        "entry_router": "weakest_group_score_le_risk_entry_score",
        "recovery_router": "fast_group_score_ge_fast_recovery_score",
        "frozen_spec": {
            "risk_entry_score": -2.5,
            "fast_recovery_score": 0.0,
        },
        "signal_clock": (
            "paper_signal_s*_t_minus_1 observed at row close; execute next bar"
        ),
        "benchmark_only": ["bare_w72_k1_c1_r1", "buy_and_hold"],
        "excluded_strategy_inputs": [
            "w72",
            "v56",
            "v60",
            "large_channel",
            "thirteen_timing_tools",
        ],
        "single_execution_shift": True,
        "runtime_uses_future": False,
        "production_authority": False,
    }


__all__ = [
    "PAPER_SIGNAL_SPANS",
    "SCALE_GROUPS",
    "PaperKernelNativeTrendSpec",
    "align_paper_native_scale_state",
    "build_paper_native_scale_state",
    "paper_native_trend_contract",
    "route_paper_native_trend",
    "signal_column",
]
