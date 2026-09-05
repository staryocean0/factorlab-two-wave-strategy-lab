from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest
from jsonschema import Draft202012Validator

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.tool_registry import DISCOVERED_TOOL_IDS
from factor_lab.market_state.tool_registry_v1_4 import (
    CURRENT_TOOL_IDS as V1_4_TOOL_IDS,
)
from factor_lab.market_state.tool_registry_v1_4 import (
    PAPER_KERNEL_TOOL_ID,
    build_tool_registry_v1_4_payload,
)
from factor_lab.market_state.tool_registry_v1_5 import (
    CURRENT_TOOL_IDS,
    LAT_TOOL_ID,
    build_tool_registry_v1_5_payload,
    run_lowpass_bandpass_lat_channel_benchmark,
    validate_tool_registry_v1_5_payload,
)

ROOT = Path(__file__).resolve().parents[2]


def _bars(size: int = 1200) -> pd.DataFrame:
    timestamp = pd.date_range("2020-01-01", periods=size, freq="15min")
    returns = 0.0001 + 0.001 * np.sin(np.arange(size) / 31.0)
    close = 100.0 * np.exp(np.cumsum(returns))
    return pd.DataFrame({"timestamp": timestamp, "close": close})


def test_v1_5_has_current_fifteen_with_lat_channel_appended() -> None:
    old = build_tool_registry_v1_4_payload()
    new = build_tool_registry_v1_5_payload()

    assert tuple(item["tool_id"] for item in old["tools"]) == V1_4_TOOL_IDS
    assert tuple(item["tool_id"] for item in new["tools"]) == CURRENT_TOOL_IDS
    assert new["tools"][:14] == old["tools"]
    assert new["benchmarks"][:14] == old["benchmarks"]
    assert new["tool_count"] == 15
    assert new["tools"][-1]["tool_id"] == LAT_TOOL_ID
    assert new["tools"][-1]["tool_category_id"] == "channel"
    assert new["tools"][-1]["method_family_id"] == "volatility_channel"
    assert "causal_jump_gap_shock" not in CURRENT_TOOL_IDS
    assert new["historical_registry_not_inherited"] == "tool_registry_v1_3"
    assert new["base_registry_version"] == "tool_registry_v1_4"
    assert DISCOVERED_TOOL_IDS + (PAPER_KERNEL_TOOL_ID, LAT_TOOL_ID) == CURRENT_TOOL_IDS


def test_v1_5_benchmark_is_causal_runnable_and_prefix_invariant() -> None:
    bars = _bars()
    full = run_lowpass_bandpass_lat_channel_benchmark(bars)
    prefix = run_lowpass_bandpass_lat_channel_benchmark(bars.iloc[:900])

    assert full["tool_id"].eq(LAT_TOOL_ID).all()
    assert full["causal"].all()
    assert full["execution_lag_bars"].eq(1).all()
    assert full["target_position"].isin([0.0, 1.0]).all()
    pdt.assert_frame_equal(full.iloc[: len(prefix)].reset_index(drop=True), prefix.reset_index(drop=True))


def test_v1_5_fails_closed_on_accidental_sixteenth_tool() -> None:
    payload = copy.deepcopy(build_tool_registry_v1_5_payload())
    payload["tools"].append(payload["tools"][-1])

    with pytest.raises(ValidationError, match="append only"):
        validate_tool_registry_v1_5_payload(payload)


def test_v1_5_fails_closed_on_routing_authority() -> None:
    payload = copy.deepcopy(build_tool_registry_v1_5_payload())
    payload["tool_routing_authority"] = True

    with pytest.raises(ValidationError, match="tool_routing_authority"):
        validate_tool_registry_v1_5_payload(payload)


def test_v1_5_payload_matches_public_schema() -> None:
    schema = json.loads(
        (ROOT / "docs/schemas/json/market_state_tool_registry@1.5.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(build_tool_registry_v1_5_payload())
