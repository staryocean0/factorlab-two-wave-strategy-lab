"""Causal orthogonal veto for the frozen four-hour downside entry."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from factor_lab.market_state.crash_slope_lifecycle import validate_ohlc


@dataclass(frozen=True, slots=True)
class DownsideEntryOrthogonalVetoSpec:
    lookback_bars: int = 12
    minimum_jump_concentration: float = 0.16553209471304586
    feature_name: str = "jump_concentration_h12"

    def __post_init__(self) -> None:
        if self.lookback_bars < 3:
            raise ValueError("lookback_bars must be at least three")
        if not 0.0 < self.minimum_jump_concentration < 1.0:
            raise ValueError("minimum jump concentration must lie in (0, 1)")


def downside_entry_jump_concentration(
    causal_ohlc: pd.DataFrame,
    *,
    lookback_bars: int = 12,
) -> pd.Series:
    """Return max absolute close return divided by total absolute movement."""

    market = validate_ohlc(causal_ohlc, expected_frequency="15m")
    index = pd.DatetimeIndex(market["timestamp"])
    close_return = pd.Series(np.log(market["close"].to_numpy(float)), index=index).diff()
    absolute = close_return.abs()
    denominator = absolute.rolling(lookback_bars, min_periods=lookback_bars).sum()
    result = absolute.rolling(lookback_bars, min_periods=lookback_bars).max() / denominator.replace(0.0, np.nan)
    result.name = f"jump_concentration_h{lookback_bars}"
    return result


def evaluate_downside_entry_orthogonal_veto(
    causal_ohlc: pd.DataFrame,
    signal_timestamps: pd.Series | pd.DatetimeIndex,
    spec: DownsideEntryOrthogonalVetoSpec = DownsideEntryOrthogonalVetoSpec(),
) -> pd.DataFrame:
    """Evaluate a close-time veto for execution on the next carrier bar."""

    signals = pd.DatetimeIndex(pd.to_datetime(signal_timestamps, errors="raise"))
    if signals.has_duplicates:
        raise ValueError("signal timestamps must be unique")
    concentration = downside_entry_jump_concentration(causal_ohlc, lookback_bars=spec.lookback_bars).reindex(signals)
    available = concentration.notna()
    kept = ~available | concentration.ge(spec.minimum_jump_concentration)
    result = pd.DataFrame(
        {
            "signal_timestamp": signals,
            spec.feature_name: concentration.to_numpy(float),
            "orthogonal_veto_feature_available": available.to_numpy(bool),
            "orthogonal_veto_kept": kept.to_numpy(bool),
            "orthogonal_veto_rejected": (~kept).to_numpy(bool),
            "runtime_uses_future": False,
            "production_authority": False,
        }
    )
    result.attrs["formula_contract"] = downside_entry_orthogonal_veto_contract(spec)
    return result


def downside_entry_orthogonal_veto_contract(
    spec: DownsideEntryOrthogonalVetoSpec = DownsideEntryOrthogonalVetoSpec(),
) -> dict[str, object]:
    return {
        "schema_id": "market_state_downside_entry_orthogonal_veto@0.1",
        "candidate_spec": asdict(spec),
        "formula": ("max(abs(delta_log_close), lookback) / sum(abs(delta_log_close), lookback) >= minimum_jump_concentration"),
        "decision_time": "frozen_entry_signal_bar_close",
        "execution_time": "next_15m_bar_open",
        "missing_feature_policy": "fail_open_keep_frozen_entry",
        "entry_formula_modified": False,
        "exit_formula_modified": False,
        "runtime_uses_future": False,
        "research_authority": True,
        "production_authority": False,
    }


__all__ = [
    "DownsideEntryOrthogonalVetoSpec",
    "downside_entry_jump_concentration",
    "downside_entry_orthogonal_veto_contract",
    "evaluate_downside_entry_orthogonal_veto",
]
