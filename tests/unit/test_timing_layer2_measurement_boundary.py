# pyright: reportAny=false, reportArgumentType=false, reportMissingTypeStubs=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.timing_layer2_3_contracts import (
    LAYER2_ASSET_IDS,
    build_layer2_paper_kernel_measurements,
    build_layer2_six_axis_measurements,
    build_layer2_volatility_measurements,
    layer2_measurement_contract,
    validate_layer2_measurement_frame,
    validate_timing_layer2_3_registry,
)

ROOT = Path(__file__).resolve().parents[2]


def _daily_bars(rows: int = 900) -> pd.DataFrame:
    index = np.arange(rows, dtype=float)
    returns = 0.0002 + 0.006 * np.sin(index / 17.0)
    return pd.DataFrame(
        {
            "timestamp": pd.bdate_range("2010-01-04", periods=rows),
            "close": 100.0 * np.exp(np.cumsum(returns)),
        }
    )


def _intraday_bars(rows: int = 1_200) -> pd.DataFrame:
    index = np.arange(rows, dtype=float)
    close = 100.0 * np.exp(np.cumsum(0.00002 + 0.001 * np.sin(index / 13.0)))
    timestamp = pd.date_range("2015-01-05 09:35", periods=rows, freq="5min")
    return pd.DataFrame(
        {
            "timestamp": timestamp,
            "trading_day": timestamp.strftime("%Y-%m-%d"),
            "segment_id": 0,
            "close": close,
        }
    )


def test_registry_covers_the_exact_frozen_lane2_denominator() -> None:
    registry = json.loads((ROOT / "docs/ops/timing_layer2_3_registry@1.0.json").read_text(encoding="utf-8"))
    inventory = json.loads((ROOT / "docs/ops/timing_infrastructure_four_layer_inventory@1.0.json").read_text(encoding="utf-8"))

    result = validate_timing_layer2_3_registry(
        registry,
        project_root=ROOT,
        frozen_inventory=inventory,
    )

    assert result["lane2_asset_count"] == 29
    assert result["measurement_asset_count"] == len(LAYER2_ASSET_IDS) == 17
    assert result["split_identity_count"] == 5
    assert result["formula_mutation"] is False
    assert result["production_authority"] is False


def test_layer2_contract_forbids_owner_action_position_and_selection() -> None:
    contract = layer2_measurement_contract()

    assert contract["measurement_authority"] is True
    assert contract["routing_authority"] is False
    assert contract["ownership_outputs_forbidden"] is True
    assert contract["position_outputs_forbidden"] is True
    assert contract["strategy_or_frequency_selection_forbidden"] is True
    assert contract["production_authority"] is False


def test_volatility_measurement_adapter_drops_target_and_three_state_surface() -> None:
    measurements = build_layer2_volatility_measurements(_intraday_bars())
    lowered = {str(column).lower() for column in measurements.columns}

    assert "future_rv_16" not in lowered
    assert not any(token in column for column in lowered for token in ("state", "position", "claim", "action", "responsible_tool"))
    assert measurements.attrs["timing_layer_contract"]["four_layer_role"] == ("layer2_kline_measurement")
    assert measurements.attrs["timing_layer_contract"]["position_output"] is False


def test_layer2_validator_fails_closed_on_state_or_position_columns() -> None:
    with pytest.raises(ValidationError, match="strategy/state outputs"):
        validate_layer2_measurement_frame(pd.DataFrame({"timestamp": [1], "volatility_state": [2]}))
    with pytest.raises(ValidationError, match="strategy/state outputs"):
        validate_layer2_measurement_frame(pd.DataFrame({"timestamp": [1], "target_position": [1]}))


def test_six_axis_and_paper_kernel_facades_are_measurement_only() -> None:
    bars = _daily_bars()
    six_axis = build_layer2_six_axis_measurements(bars)
    paper = build_layer2_paper_kernel_measurements(bars)

    assert six_axis.attrs["timing_layer_contract"]["adapter_id"] == ("six_axis_measurement@1.0")
    assert paper.attrs["timing_layer_contract"]["adapter_id"] == ("paper_kernel_timeseries@1.0")
    assert "axis_direction" in six_axis
    assert "paper_signal_s1_t_minus_1" in paper
    assert not any("position" in str(column).lower() for column in six_axis.columns)
    assert not any("position" in str(column).lower() for column in paper.columns)
