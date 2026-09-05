# pyright: reportAny=false, reportArgumentType=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.timing_layer3_orchestration import (
    OwnerProfile,
    StateAdapterContract,
    apply_layer3_owner_waterfall,
)

ROOT = Path(__file__).resolve().parents[2]


def _profile(
    profile_id: str,
    tool_id: str,
    rank: int,
    *,
    installed: bool = True,
) -> OwnerProfile:
    return OwnerProfile(
        profile_id=profile_id,
        strategy_plugin_id=f"plugin_{profile_id}",
        claim_tool_id=tool_id,
        side_id="upside_capture",
        priority_rank=rank,
        state_adapter_id=f"state_{profile_id}",
        formula_contract_ref=f"docs/ops/{profile_id}.json",
        formula_digest="sha256:" + "a" * 64,
        installed=installed,
    )


def test_generic_waterfall_routes_profiles_without_position_output() -> None:
    index = pd.RangeIndex(5)
    first = _profile("first", "laplace_iir_mixed_bandpass", 1)
    second = _profile("second", "laplace_iir_lowpass", 2)
    candidate = _profile("candidate", "butterworth_clean_bandpass", 3, installed=False)
    result = apply_layer3_owner_waterfall(
        index,
        side_id="upside_capture",
        profiles=(first, second, candidate),
        eligibility_by_profile={
            "first": pd.Series([True, False, False, True, False], index=index),
            "second": pd.Series([True, True, False, False, False], index=index),
        },
    )
    assert result["responsible_profile_id"].tolist() == [
        "first",
        "second",
        "unassigned",
        "first",
        "unassigned",
    ]
    assert not any("position" in str(column).lower() for column in result.columns)
    contract = result.attrs["timing_layer_contract"]
    assert contract["imports_concrete_strategy_implementations"] is False
    assert contract["production_authority"] is False


def test_state_adapter_and_owner_profile_fail_closed() -> None:
    adapter = StateAdapterContract(
        "volatility_state_v2",
        ("layer2.volatility",),
        ("low", "normal", "high"),
        "docs/ops/volatility.json",
    )
    assert adapter.replaceable_by_layer2_measurement
    with pytest.raises(ValidationError, match="position"):
        StateAdapterContract(
            "bad",
            ("x",),
            ("on", "off"),
            "x",
            position_output=True,
        )


def test_generic_kernel_source_does_not_import_concrete_plugins() -> None:
    text = (ROOT / "src/factor_lab/market_state/timing_layer3_orchestration.py").read_text(encoding="utf-8")
    assert "timing_explosive_layer_v3 import" not in text
    assert "timing_crash_rebound_current_best_r1 import" not in text
