from __future__ import annotations

import copy
import json
from pathlib import Path

import pandas as pd
import pytest
from jsonschema import Draft202012Validator

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.timing_priority_composition import (
    TimingPriorityClaim,
    apply_timing_priority_waterfall,
    build_timing_priority_composition_payload,
    validate_timing_priority_composition_payload,
)
from factor_lab.market_state.tool_registry_v1_5 import CURRENT_TOOL_IDS

ROOT = Path(__file__).resolve().parents[2]


def test_framework_has_two_empty_sides_and_no_authority() -> None:
    payload = build_timing_priority_composition_payload()

    assert payload["tool_count"] == 15
    assert tuple(payload["eligible_tool_ids"]) == CURRENT_TOOL_IDS
    assert payload["side_contracts"]["upside_capture"]["priority_ladder"] == []
    assert payload["side_contracts"]["downside_protection"]["priority_ladder"] == []
    assert payload["selection_data_rows_read"] == 0
    assert payload["return_rows_read"] == 0
    assert payload["tool_routing_authority"] is False


def test_waterfall_claims_overlap_once_and_passes_remainder_down() -> None:
    index = pd.RangeIndex(6)
    first = TimingPriorityClaim(
        tool_id=CURRENT_TOOL_IDS[0],
        side_id="upside_capture",
        priority_rank=1,
        state_id="first_state",
        eligible=pd.Series([True, True, False, False, False, False], index=index),
    )
    second = TimingPriorityClaim(
        tool_id=CURRENT_TOOL_IDS[1],
        side_id="upside_capture",
        priority_rank=2,
        state_id="second_state",
        eligible=pd.Series([True, False, True, False, True, False], index=index),
    )

    result = apply_timing_priority_waterfall(index, side_id="upside_capture", claims=(second, first))

    assert result["responsible_tool_id"].tolist() == [
        CURRENT_TOOL_IDS[0],
        CURRENT_TOOL_IDS[0],
        CURRENT_TOOL_IDS[1],
        "unassigned",
        CURRENT_TOOL_IDS[1],
        "unassigned",
    ]
    assert result["claimed"].sum() == 4
    assert result["remaining_unassigned"].tolist() == [False, False, False, True, False, True]


def test_waterfall_rejects_unknown_tool_duplicate_rank_and_cross_side_claim() -> None:
    index = pd.RangeIndex(2)
    mask = pd.Series([True, False], index=index)
    with pytest.raises(ValidationError, match="current 15"):
        TimingPriorityClaim("unknown", "upside_capture", 1, "state", mask)

    first = TimingPriorityClaim(CURRENT_TOOL_IDS[0], "upside_capture", 1, "a", mask)
    duplicate = TimingPriorityClaim(CURRENT_TOOL_IDS[1], "upside_capture", 1, "b", mask)
    with pytest.raises(ValidationError, match="unique"):
        apply_timing_priority_waterfall(index, side_id="upside_capture", claims=(first, duplicate))

    downside = TimingPriorityClaim(CURRENT_TOOL_IDS[1], "downside_protection", 2, "b", mask)
    with pytest.raises(ValidationError, match="Cross-side|cross-side"):
        apply_timing_priority_waterfall(index, side_id="upside_capture", claims=(first, downside))


def test_framework_fails_closed_if_a_priority_is_preselected() -> None:
    payload = copy.deepcopy(build_timing_priority_composition_payload())
    payload["side_contracts"]["upside_capture"]["priority_ladder"] = [CURRENT_TOOL_IDS[0]]

    with pytest.raises(ValidationError, match="preselect"):
        validate_timing_priority_composition_payload(payload)


def test_framework_payload_matches_public_schema() -> None:
    schema = json.loads(
        (
            ROOT
            / "docs/schemas/json/market_state_timing_priority_composition@1.1.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(build_timing_priority_composition_payload())
