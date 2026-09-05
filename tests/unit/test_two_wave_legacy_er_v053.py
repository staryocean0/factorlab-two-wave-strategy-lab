"""Hard isolation tests for the v0.5.3 legacy raw-ER qualification overlay."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from factor_lab.visual_structure.two_wave.legacy_er_v053 import (
    REMOVED_REASON,
    adjust_v052_record_for_v053,
    build_legacy_er_run_v053,
)


def _record(
    record_id: str,
    reasons: list[str],
    *,
    start: int = 0,
    end: int = 10,
    confirmation: int = 12,
    classification: str = "not_same_scale",
    diagnostic: str = "uptrend",
) -> dict:
    return {
        "record_id": record_id,
        "ridge_tuple_id": f"tuple_{record_id}",
        "ridge_ids": [f"ridge_{record_id}_{i}" for i in range(5)],
        "five_occurrence_bars": [start, start + 2, start + 4, start + 7, end],
        "birth_scale_level": 5,
        "birth_scale_id": "tcss_sigma_2.82842712475",
        "birth_sigma_bars": 2.82842712475,
        "characteristic_scale_level": 5,
        "characteristic_scale_id": "tcss_sigma_2.82842712475",
        "characteristic_sigma_bars": 2.82842712475,
        "confirmation_bar": confirmation,
        "confirmation_time": f"2019-01-02T0{confirmation % 10}:00:00+00:00",
        "known_at": f"2019-01-02T0{confirmation % 10}:00:00+00:00",
        "start_bar": start,
        "end_bar": end,
        "scale_rejection_reasons": list(reasons),
        "scale_qualified": not reasons,
        "classification": classification,
        "geometric_direction_diagnostic": diagnostic,
        "leg_paths": [
            {"efficiency": 0.31},
            {"efficiency": 0.72},
            {"efficiency": 0.48},
            {"efficiency": 0.83},
        ],
        "selected": False,
        "overlap_suppressed_by": None,
        "future_outcome_used": False,
        "trade_authority": False,
    }


def _bars(n: int = 120) -> list[dict]:
    start = datetime(2019, 1, 2, 1, 30, tzinfo=UTC)
    rows = []
    for i in range(n):
        stamp = start + timedelta(minutes=5 * i)
        price = 100.0 + i * 0.01
        rows.append(
            {
                "timestamp": stamp.isoformat(),
                "available_at": stamp.isoformat(),
                "trading_day": stamp.date().isoformat(),
                "open": price,
                "high": price,
                "low": price,
                "close": price,
            }
        )
    return rows


def test_only_inefficient_leg_becomes_qualified_without_recomputing_raw_er():
    source = _record("only_er", [REMOVED_REASON])
    before_values = [row["efficiency"] for row in source["leg_paths"]]
    out = adjust_v052_record_for_v053(source)

    assert source["scale_rejection_reasons"] == [REMOVED_REASON]
    assert out["scale_rejection_reasons"] == []
    assert out["scale_qualified"] is True
    assert out["classification"] == source["geometric_direction_diagnostic"]
    assert out["legacy_raw_er_parent_gate_active"] is False
    assert out["legacy_raw_er_original_reasons"] == [REMOVED_REASON]
    assert out["legacy_raw_er_audit_values"] == before_values
    assert [row["efficiency"] for row in out["leg_paths"]] == before_values


def test_inefficient_leg_plus_other_failure_removes_only_er_and_stays_rejected():
    source = _record("er_plus_jump", ["corresponding_leg_duration_mismatch", REMOVED_REASON, "jump_dominated_leg"])
    out = adjust_v052_record_for_v053(source)

    assert out["scale_rejection_reasons"] == [
        "corresponding_leg_duration_mismatch",
        "jump_dominated_leg",
    ]
    assert out["scale_qualified"] is False
    assert out["classification"] == "not_same_scale"


def test_originally_qualified_record_and_identity_fields_are_preserved():
    source = _record("already_good", [], classification="downtrend", diagnostic="downtrend")
    out = adjust_v052_record_for_v053(source)

    for field in (
        "record_id",
        "ridge_tuple_id",
        "ridge_ids",
        "five_occurrence_bars",
        "birth_scale_level",
        "birth_scale_id",
        "birth_sigma_bars",
        "confirmation_bar",
        "known_at",
        "start_bar",
        "end_bar",
    ):
        assert out[field] == source[field]
    assert out["scale_qualified"] is True
    assert out["classification"] == "downtrend"
    assert out["scale_rejection_reasons"] == []


def test_v053_replays_same_deterministic_exclusive_ledger_policy():
    from factor_lab.visual_structure.two_wave.characteristic_scale_v051 import CharacteristicExclusiveLedger

    records = [
        adjust_v052_record_for_v053(_record("first", [REMOVED_REASON], start=0, end=10, confirmation=12)),
        adjust_v052_record_for_v053(_record("overlap", [REMOVED_REASON], start=5, end=15, confirmation=13)),
        adjust_v052_record_for_v053(_record("later", [REMOVED_REASON], start=10, end=20, confirmation=14)),
    ]
    ledger = CharacteristicExclusiveLedger()
    ledger.add_records(records)

    assert [row["record_id"] for row in ledger.selected] == ["first", "later"]
    overlap = next(row for row in ledger.records if row["record_id"] == "overlap")
    assert overlap["selected"] is False
    assert overlap["overlap_suppressed_by"] == "first"
    assert all(a["end_bar"] <= b["start_bar"] for a, b in zip(ledger.selected, ledger.selected[1:]))


def test_monotonic_input_changes_no_parent_identity_and_publishes_nothing():
    run = build_legacy_er_run_v053(_bars())
    assert run.base_run.tuple_births == []
    assert run.base_run.evaluated_records == []
    assert run.evaluated_records == []
    assert run.ledger.selected == []
