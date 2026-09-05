"""Causal consumption primitives for timing-tool parameter routing.

The market-field tables are measurements, not trading signals.  This module
provides the missing bridge needed by a tool-specific research sample:

* expose a completed daily observation only on its decision-eligible day;
* choose a parameter only at a fresh lifecycle entry and freeze that choice;
* gate a complete lifecycle with an entry-time threshold; and
* recompose ordered specialist claims over one residual target before the
  account-level signed T+1 state machine is applied.

It deliberately contains no market thresholds or strategy-specific formula.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from factor_lab.market_state.timing_three_bucket_iir_reference_v1 import (
    enforce_signed_true_t_plus_one_with_owner,
)


def expand_decision_eligible_daily_state(
    daily_state: pd.DataFrame,
    execution_index: pd.DatetimeIndex,
    *,
    value_columns: Sequence[str],
) -> pd.DataFrame:
    """Expand causal daily values to intraday bars by eligible trading date."""

    required = {"trading_day", "decision_eligible_date", *value_columns}
    missing = sorted(required.difference(daily_state.columns))
    if missing:
        raise KeyError(f"daily market state is missing columns: {missing}")
    if execution_index.empty or execution_index.has_duplicates or not execution_index.is_monotonic_increasing:
        raise ValueError("execution index must be non-empty, unique, and ordered")
    frame = daily_state.loc[:, ["trading_day", "decision_eligible_date", *value_columns]].copy()
    frame["trading_day"] = pd.to_datetime(frame["trading_day"], errors="raise")
    frame["decision_eligible_date"] = pd.to_datetime(frame["decision_eligible_date"], errors="raise")
    frame = frame.sort_values("decision_eligible_date").reset_index(drop=True)
    if frame["decision_eligible_date"].duplicated().any():
        raise ValueError("decision-eligible dates must be unique")
    if bool(frame["decision_eligible_date"].le(frame["trading_day"]).any()):
        raise ValueError("daily state must become eligible after its trading day")
    keyed = frame.set_index(frame["decision_eligible_date"].dt.normalize())
    expanded = keyed.loc[:, value_columns].reindex(execution_index.normalize())
    expanded.index = execution_index
    expanded.attrs["alignment"] = "decision_eligible_date_to_same_day_intraday"
    expanded.attrs["runtime_uses_future"] = False
    return expanded


def gate_complete_lifecycle_by_entry_threshold(
    active: pd.Series,
    entry_measurement: pd.Series,
    entry_threshold: float | pd.Series,
) -> pd.DataFrame:
    """Accept or reject a complete lifecycle using only its entry observation."""

    if not isinstance(active.index, pd.DatetimeIndex):
        raise TypeError("lifecycle gate requires a DatetimeIndex")
    if not active.index.equals(entry_measurement.index):
        raise ValueError("lifecycle and entry measurement indexes must match")
    if isinstance(entry_threshold, pd.Series):
        if not active.index.equals(entry_threshold.index):
            raise ValueError("lifecycle and entry threshold indexes must match")
        threshold = pd.to_numeric(entry_threshold, errors="raise")
    else:
        threshold = pd.Series(float(entry_threshold), index=active.index)
    lifecycle = active.astype(bool)
    measurement = pd.to_numeric(entry_measurement, errors="coerce")
    starts = lifecycle & ~lifecycle.shift(1, fill_value=False)
    accepted_starts = starts & measurement.ge(threshold)
    group = starts.cumsum()
    accepted = (
        pd.Series(
            np.where(starts.to_numpy(bool), accepted_starts.to_numpy(bool), False),
            index=active.index,
            dtype=bool,
        )
        .groupby(group)
        .transform("max")
    )
    gated = lifecycle & accepted.astype(bool)
    return pd.DataFrame(
        {
            "lifecycle_active": lifecycle,
            "entry_trigger": starts,
            "entry_measurement": measurement,
            "entry_threshold": threshold,
            "entry_accepted": accepted_starts,
            "gated_lifecycle": gated,
        },
        index=active.index,
    )


def route_complete_lifecycle_by_entry(
    candidate_decisions: Mapping[str, pd.Series],
    owner_at_entry: pd.Series,
) -> pd.DataFrame:
    """Choose only on a fresh entry and freeze the chosen lifecycle to exit."""

    if not candidate_decisions:
        raise ValueError("candidate decisions cannot be empty")
    if not isinstance(owner_at_entry.index, pd.DatetimeIndex):
        raise TypeError("lifecycle owner requires a DatetimeIndex")
    index = owner_at_entry.index
    candidates: dict[str, pd.Series] = {}
    starts: dict[str, pd.Series] = {}
    for candidate_id, decision in candidate_decisions.items():
        if not candidate_id:
            raise ValueError("candidate identifiers cannot be empty")
        if not decision.index.equals(index):
            raise ValueError(f"candidate index mismatch: {candidate_id}")
        active = decision.astype(bool)
        candidates[candidate_id] = active
        starts[candidate_id] = active & ~active.shift(1, fill_value=False)

    active_owner: str | None = None
    routed = np.zeros(len(index), dtype=bool)
    entry = np.zeros(len(index), dtype=bool)
    exit_trigger = np.zeros(len(index), dtype=bool)
    owner_values = np.full(len(index), "none", dtype=object)
    for location in range(len(index)):
        if active_owner is not None and not bool(candidates[active_owner].iloc[location]):
            active_owner = None
            exit_trigger[location] = True
        if active_owner is None:
            requested_value = owner_at_entry.iloc[location]
            requested = "" if pd.isna(requested_value) else str(requested_value)
            if requested and requested not in candidates:
                raise ValueError(f"unknown lifecycle owner requested: {requested}")
            if requested and bool(starts[requested].iloc[location]):
                active_owner = requested
                entry[location] = True
        if active_owner is not None:
            routed[location] = True
            owner_values[location] = active_owner
    return pd.DataFrame(
        {
            "routed_decision_active": routed,
            "routed_candidate_id": owner_values,
            "routed_entry_trigger": entry,
            "routed_exit_trigger": exit_trigger,
            "requested_candidate_id": owner_at_entry.astype("string"),
            "runtime_uses_future": False,
        },
        index=index,
    )


def compose_ordered_specialist_claims(
    residual_desired_position: pd.Series,
    ordered_specialist_positions: Mapping[str, pd.Series],
) -> pd.DataFrame:
    """Compose disjoint specialist ownership over one residual target path."""

    if not ordered_specialist_positions:
        raise ValueError("at least one specialist position is required")
    if not isinstance(residual_desired_position.index, pd.DatetimeIndex):
        raise TypeError("claim composition requires a DatetimeIndex")
    index = residual_desired_position.index
    residual = pd.to_numeric(residual_desired_position, errors="raise").fillna(0.0).clip(-1.0, 1.0)
    desired = residual.copy()
    desired_owner = pd.Series("residual", index=index, dtype="string")
    unclaimed = pd.Series(True, index=index, dtype=bool)
    output: dict[str, pd.Series] = {}
    for specialist_id, specialist_position in ordered_specialist_positions.items():
        if not specialist_position.index.equals(index):
            raise ValueError(f"specialist index mismatch: {specialist_id}")
        position = pd.to_numeric(specialist_position, errors="raise").fillna(0.0)
        if bool(~position.isin([-1.0, 0.0, 1.0]).any()):
            raise ValueError(f"specialist positions must be signed unit values: {specialist_id}")
        claim = position.ne(0.0) & unclaimed
        desired.loc[claim] = position.loc[claim]
        desired_owner.loc[claim] = specialist_id
        unclaimed &= ~claim
        output[f"{specialist_id}_claim"] = claim
    output["residual_claim"] = unclaimed
    output["combo_desired_position"] = desired
    output["combo_desired_owner"] = desired_owner
    executed = enforce_signed_true_t_plus_one_with_owner(desired, desired_owner)
    output["combo_t1_position"] = executed["t1_position"]
    output["combo_t1_owner"] = executed["t1_owner"]
    frame = pd.DataFrame(output, index=index)
    claim_columns = [column for column in frame if column.endswith("_claim")]
    if not frame[claim_columns].astype(int).sum(axis=1).eq(1).all():
        raise RuntimeError("ordered claim composition is not exhaustive and exclusive")
    frame.attrs["specialist_priority"] = list(ordered_specialist_positions)
    frame.attrs["single_final_t1_state_machine"] = True
    return frame


__all__ = [
    "compose_ordered_specialist_claims",
    "expand_decision_eligible_daily_state",
    "gate_complete_lifecycle_by_entry_threshold",
    "route_complete_lifecycle_by_entry",
]
