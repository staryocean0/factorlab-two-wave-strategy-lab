# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportCallIssue=false, reportGeneralTypeIssues=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Research-only scale-constrained return ceilings for timing strategies.

The oracle sees future returns, but it must obey the same position alphabet,
minimum holding duration and one-way transaction cost as the evaluated fixed
parameter paths.  It is an evaluation denominator, never a trading signal.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError

SCHEMA_ID: Final[str] = "market_state_timing_scale_oracle@1.0"


@dataclass(frozen=True, slots=True)
class ScaleOracleSpec:
    """The tradability constraints that define one timing scale."""

    scale_id: str
    minimum_holding_bars: int
    allowed_positions: tuple[int, ...]
    one_way_cost_bps: float
    periods_per_year: float
    force_flat_at_end: bool = True
    buy_cost_bps: float | None = None
    sell_cost_bps: float | None = None

    def __post_init__(self) -> None:
        if not self.scale_id.strip():
            raise ValueError("scale_id must not be empty")
        if self.minimum_holding_bars < 1:
            raise ValueError("minimum_holding_bars must be positive")
        if tuple(sorted(set(self.allowed_positions))) != self.allowed_positions:
            raise ValueError("allowed_positions must be unique and sorted")
        if 0 not in self.allowed_positions or not set(self.allowed_positions).issubset({-1, 0, 1}):
            raise ValueError("allowed_positions must contain zero and use only -1/0/1")
        if self.one_way_cost_bps < 0.0:
            raise ValueError("one_way_cost_bps must be non-negative")
        if (self.buy_cost_bps is None) != (self.sell_cost_bps is None):
            raise ValueError("buy_cost_bps and sell_cost_bps must be supplied together")
        if (
            self.buy_cost_bps is not None
            and self.sell_cost_bps is not None
            and min(self.buy_cost_bps, self.sell_cost_bps) < 0.0
        ):
            raise ValueError("directional transaction costs must be non-negative")
        if self.periods_per_year <= 0.0:
            raise ValueError("periods_per_year must be positive")


def timing_scale_oracle_contract() -> dict[str, object]:
    """Return the non-tradable scale-ceiling contract."""

    return {
        "schema_id": SCHEMA_ID,
        "scientific_role": "scale_specific_hindsight_return_ceiling",
        "scale_definition": (
            "position_alphabet_plus_minimum_holding_bars_plus_execution_grid_plus_one_way_cost"
        ),
        "same_exam_requirements": [
            "same_log_return_path",
            "same_allowed_positions",
            "same_minimum_holding_bars",
            "same_signed_transaction_cost_model",
            "same_forced_terminal_flattening",
        ],
        "supported_cost_models": [
            "symmetric_one_way_cost",
            "asymmetric_buy_sell_cost",
        ],
        "nested_ceiling_order": [
            "market_scale_oracle",
            "tool_family_oracle",
            "candidate_realized_path",
        ],
        "lookahead_only": True,
        "signal_authority": False,
        "routing_authority": False,
        "parameter_authority": False,
        "production_authority": False,
    }


def evaluate_executed_position_path(
    log_returns: pd.Series,
    executed_positions: pd.Series,
    *,
    spec: ScaleOracleSpec,
) -> tuple[pd.DataFrame, dict[str, float | int | str | bool]]:
    """Evaluate one already-executed path under the registered scale contract."""

    returns = _validated_returns(log_returns)
    positions = _validated_positions(executed_positions, returns.index, spec=spec)
    _validate_minimum_holding(positions, spec=spec)
    previous = positions.shift(1, fill_value=0).astype(int)
    change = (positions - previous).astype(float)
    turnover = change.abs()
    gross = positions.astype(float) * returns
    cost = _transaction_cost_for_change(change, spec=spec)
    if spec.force_flat_at_end and len(cost):
        terminal_change = pd.Series(
            [-float(positions.iloc[-1])],
            index=pd.Index([cost.index[-1]]),
            dtype=float,
        )
        cost.iloc[-1] += float(_transaction_cost_for_change(terminal_change, spec=spec).iloc[0])
    net = gross - cost
    ledger = pd.DataFrame(
        {
            "log_return": returns,
            "executed_position": positions,
            "gross_log_value": gross,
            "transaction_cost_log": cost,
            "net_log_value": net,
        }
    )
    years = len(returns) / spec.periods_per_year
    return ledger, {
        "scale_id": spec.scale_id,
        "bar_count": len(returns),
        "elapsed_years": years,
        "gross_log_value": float(gross.sum()),
        "transaction_cost_log": float(cost.sum()),
        "net_log_value": float(net.sum()),
        "net_log_value_per_year": float(net.sum()) / years,
        "position_change_count": int(turnover.gt(0.0).sum()),
        "active_bar_count": int(positions.ne(0).sum()),
        "lookahead_only": False,
    }


def compute_market_scale_oracle(
    log_returns: pd.Series,
    *,
    spec: ScaleOracleSpec,
) -> tuple[pd.DataFrame, dict[str, float | int | str | bool]]:
    """Maximize hindsight net value over every scale-compliant position path."""

    returns = _validated_returns(log_returns)
    available = [spec.allowed_positions for _ in range(len(returns))]
    positions = _optimize_position_path(returns.to_numpy(float), available, spec=spec)
    ledger, summary = evaluate_executed_position_path(
        returns,
        pd.Series(positions, index=returns.index),
        spec=spec,
    )
    summary = {**summary, "lookahead_only": True, "oracle_kind": "market_scale_oracle"}
    ledger["lookahead_only"] = True
    ledger["oracle_kind"] = "market_scale_oracle"
    return ledger, summary


def compute_tool_family_oracle(
    log_returns: pd.Series,
    fixed_candidate_positions: pd.DataFrame,
    *,
    spec: ScaleOracleSpec,
) -> tuple[pd.DataFrame, dict[str, float | int | str | bool]]:
    """Choose hindsight actions only from registered fixed-parameter paths."""

    returns = _validated_returns(log_returns)
    if fixed_candidate_positions.empty or not len(fixed_candidate_positions.columns):
        raise ValidationError("tool family oracle requires fixed candidate paths")
    if not fixed_candidate_positions.index.equals(returns.index):
        raise ValidationError("tool family candidate paths must align with log returns")
    candidate_values: list[np.ndarray] = []
    for column in fixed_candidate_positions.columns:
        path = _validated_positions(fixed_candidate_positions[column], returns.index, spec=spec)
        _validate_minimum_holding(path, spec=spec)
        candidate_values.append(path.to_numpy(int))
    matrix = np.column_stack(candidate_values)
    available = [tuple(sorted({0, *matrix[row].tolist()})) for row in range(len(matrix))]
    positions = _optimize_position_path(returns.to_numpy(float), available, spec=spec)
    ledger, summary = evaluate_executed_position_path(
        returns,
        pd.Series(positions, index=returns.index),
        spec=spec,
    )
    summary = {
        **summary,
        "lookahead_only": True,
        "oracle_kind": "tool_family_oracle",
        "fixed_candidate_count": len(fixed_candidate_positions.columns),
    }
    ledger["lookahead_only"] = True
    ledger["oracle_kind"] = "tool_family_oracle"
    return ledger, summary


def build_nested_scale_potential_table(
    log_returns: pd.Series,
    fixed_candidate_positions: pd.DataFrame,
    *,
    spec: ScaleOracleSpec,
    candidate_kinds: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Build exact market/family/candidate nested ceilings for one period."""

    _, market = compute_market_scale_oracle(log_returns, spec=spec)
    _, family = compute_tool_family_oracle(log_returns, fixed_candidate_positions, spec=spec)
    market_value = float(market["net_log_value_per_year"])
    family_value = float(family["net_log_value_per_year"])
    tolerance = 1e-10
    if family_value > market_value + tolerance:
        raise RuntimeError("tool family oracle exceeded the market scale oracle")
    kinds = dict(candidate_kinds or {})
    rows: list[dict[str, object]] = []
    for column in fixed_candidate_positions.columns:
        _, candidate = evaluate_executed_position_path(
            log_returns,
            fixed_candidate_positions[column],
            spec=spec,
        )
        realized = float(candidate["net_log_value_per_year"])
        if realized > family_value + tolerance:
            raise RuntimeError(f"candidate exceeded its tool family oracle: {column}")
        architecture_gap = market_value - family_value
        parameter_gap = family_value - realized
        closure_error = realized - (market_value - architecture_gap - parameter_gap)
        rows.append(
            {
                "scale_id": spec.scale_id,
                "candidate_id": str(column),
                "candidate_kind": kinds.get(str(column), "static"),
                "bar_count": int(candidate["bar_count"]),
                "elapsed_years": float(candidate["elapsed_years"]),
                "market_scale_oracle_net_value_per_year": market_value,
                "tool_family_oracle_net_value_per_year": family_value,
                "candidate_realized_net_value_per_year": realized,
                "tool_architecture_gap_per_year": architecture_gap,
                "parameter_matching_gap_per_year": parameter_gap,
                "value_conservation_error": closure_error,
                "candidate_position_change_count": int(candidate["position_change_count"]),
                "market_oracle_position_change_count": int(market["position_change_count"]),
                "tool_family_oracle_position_change_count": int(family["position_change_count"]),
                "lookahead_only": True,
                "production_authority": False,
            }
        )
    return pd.DataFrame(rows)


def _validated_returns(log_returns: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(log_returns, errors="coerce")
    values = pd.Series(numeric.to_numpy(float), index=log_returns.index, dtype=float)
    if values.empty or values.isna().any() or not np.isfinite(values.to_numpy(float)).all():
        raise ValidationError("log returns must be non-empty, aligned and finite")
    return values


def _validated_positions(
    positions: pd.Series,
    index: pd.Index,
    *,
    spec: ScaleOracleSpec,
) -> pd.Series:
    if not positions.index.equals(index):
        raise ValidationError("executed positions must align with log returns")
    numeric = pd.to_numeric(positions, errors="coerce")
    if numeric.isna().any() or not np.isfinite(numeric.to_numpy(float)).all():
        raise ValidationError("executed positions must be finite")
    integer = pd.Series(numeric.to_numpy(int), index=index, dtype=int)
    if not np.array_equal(integer.to_numpy(int), numeric.to_numpy(float)):
        raise ValidationError("executed positions must be integer -1/0/1 values")
    if not set(integer.unique()).issubset(set(spec.allowed_positions)):
        raise ValidationError("executed positions violate the scale position alphabet")
    return integer


def _validate_minimum_holding(positions: pd.Series, *, spec: ScaleOracleSpec) -> None:
    previous = 0
    dwell = spec.minimum_holding_bars
    for value in positions.to_numpy(int):
        current = int(value)
        if current != previous:
            if dwell < spec.minimum_holding_bars:
                raise ValidationError("candidate path changes before the scale minimum holding duration")
            previous = current
            dwell = 1
        else:
            dwell = min(spec.minimum_holding_bars, dwell + 1)


def _optimize_position_path(
    returns: np.ndarray,
    available_actions: Sequence[tuple[int, ...]],
    *,
    spec: ScaleOracleSpec,
) -> np.ndarray:
    if len(returns) != len(available_actions):
        raise ValueError("available action rows must align with returns")
    hold = spec.minimum_holding_bars
    states: dict[tuple[int, int], float] = {(0, hold): 0.0}
    parents: list[dict[tuple[int, int], tuple[int, int]]] = []
    for bar, value in enumerate(returns):
        actions = tuple(sorted(set(int(item) for item in available_actions[bar])))
        if not actions or not set(actions).issubset(set(spec.allowed_positions)):
            raise ValidationError("oracle action set violates the scale position alphabet")
        next_states: dict[tuple[int, int], float] = {}
        next_parent: dict[tuple[int, int], tuple[int, int]] = {}
        for (previous, dwell), objective in states.items():
            state_actions = actions if dwell >= hold else tuple(sorted({*actions, previous}))
            for current in state_actions:
                if current != previous and dwell < hold:
                    continue
                next_dwell = min(hold, dwell + 1) if current == previous else 1
                state = (current, next_dwell)
                candidate = (
                    objective
                    + current * float(value)
                    - _transaction_cost_for_scalar_change(current - previous, spec=spec)
                )
                if candidate > next_states.get(state, -np.inf):
                    next_states[state] = candidate
                    next_parent[state] = (previous, dwell)
        if not next_states:
            raise ValidationError("no scale-compliant oracle path remains")
        states = next_states
        parents.append(next_parent)
    terminal = max(
        states,
        key=lambda state: states[state]
        - (
            _transaction_cost_for_scalar_change(-state[0], spec=spec)
            if spec.force_flat_at_end
            else 0.0
        ),
    )
    path = np.zeros(len(returns), dtype=int)
    state = terminal
    for bar in range(len(returns) - 1, -1, -1):
        path[bar] = state[0]
        state = parents[bar][state]
    return path


def _transaction_cost_rates(spec: ScaleOracleSpec) -> tuple[float, float]:
    """Return buy/sell rates while preserving the legacy symmetric contract."""

    if spec.buy_cost_bps is None and spec.sell_cost_bps is None:
        rate = spec.one_way_cost_bps / 10_000.0
        return rate, rate
    if spec.buy_cost_bps is None or spec.sell_cost_bps is None:
        raise ValueError("buy_cost_bps and sell_cost_bps must be supplied together")
    return spec.buy_cost_bps / 10_000.0, spec.sell_cost_bps / 10_000.0


def _transaction_cost_for_scalar_change(change: int | float, *, spec: ScaleOracleSpec) -> float:
    buy_rate, sell_rate = _transaction_cost_rates(spec)
    value = float(change)
    return max(value, 0.0) * buy_rate + max(-value, 0.0) * sell_rate


def _transaction_cost_for_change(
    change: pd.Series,
    *,
    spec: ScaleOracleSpec,
) -> pd.Series:
    buy_rate, sell_rate = _transaction_cost_rates(spec)
    return change.clip(lower=0.0) * buy_rate + (-change.clip(upper=0.0)) * sell_rate


__all__ = [
    "SCHEMA_ID",
    "ScaleOracleSpec",
    "build_nested_scale_potential_table",
    "compute_market_scale_oracle",
    "compute_tool_family_oracle",
    "evaluate_executed_position_path",
    "timing_scale_oracle_contract",
]
