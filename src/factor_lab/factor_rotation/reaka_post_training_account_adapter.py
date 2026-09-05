"""Compatibility map from sealed REAKA P7 evidence into generic progression semantics."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, cast

from factor_lab.factor_rotation.reaka_intraday_portfolio_mapping_v1 import (
    CLOCKS,
    COMMON_ROOT_POLICY_ID,
    SLIPPAGE_MULTIPLIERS,
    build_policy_grid,
)
from factor_lab.governance.canonicalization import canonical_digest

SCHEMA_ID: Final = "factorlab.reaka_post_training_account_adapter@1.0"


def build_reaka_p7_compatibility_map() -> dict[str, object]:
    policies = build_policy_grid()
    payload: dict[str, object] = {
        "schema_id": SCHEMA_ID,
        "strategy_id": "REAKA_d8_h8_K1_r0",
        "historical_contract_digest": (
            "sha256:36f630c37ac8bfe9fee4d98b6a341562fb96549fff6d423fa7f0a62dbacafd0b"
        ),
        "historical_final_validation_digest": (
            "sha256:fe915f6f9714f72f0fe5786bf75e1e6ed50e621cddc7135d9677bae26015cb67"
        ),
        "historical_final_acceptance_digest": (
            "sha256:4b548d51f29894b5d5d2e42aff4d1ac4abbe4ca3d7b0abc9e56dc7132d300b84"
        ),
        "common_root_policy_id": COMMON_ROOT_POLICY_ID,
        "policy_ids": [policy.policy_id for policy in policies],
        "policy_count": len(policies),
        "variant_ids": list(CLOCKS),
        "cost_scenario_ids": [f"slippage_{value:.1f}x" for value in SLIPPAGE_MULTIPLIERS],
        "attempt_count": len(policies) * len(CLOCKS) * len(SLIPPAGE_MULTIPLIERS),
        "historical_final_selected_policy_id": COMMON_ROOT_POLICY_ID,
        "historical_final_selected_policy_is_winner": False,
        "historical_final_clock_nomination": None,
        "historical_result_mutated": False,
        "production_authority": False,
    }
    payload["canonical_digest"] = canonical_digest(payload)
    return payload


def build_reaka_p7_progression_migration_ledger() -> dict[str, object]:
    materials = [
        {
            "material_id": "reaka_p7_2014_top50_two_clock_progress",
            "evidence_ref": (
                "docs/ops/evidence/reaka_intraday_portfolio_mapping_account_v1_20260901/"
                "annual_sessions/2014/analysis_ledger.json"
            ),
            "status": "retrospective_candidate_then_later_not_retained",
            "next_round_role": "progression_material_only",
        },
        {
            "material_id": "reaka_p7_2015_top50_return_drawdown_tradeoff",
            "evidence_ref": (
                "docs/ops/evidence/reaka_intraday_portfolio_mapping_account_v1_20260901/"
                "annual_sessions/2015/analysis_ledger.json"
            ),
            "status": "progress_tradeoff_waiting_financial_owner",
            "next_round_role": "progression_material_only",
        },
        {
            "material_id": "reaka_p7_2016_2019_top50_1430_only_progress",
            "evidence_refs": [
                (
                    "docs/ops/evidence/reaka_intraday_portfolio_mapping_account_v1_20260901/"
                    f"annual_sessions/{year}/analysis_ledger.json"
                )
                for year in range(2016, 2020)
            ],
            "status": "valid_single_variant_progress_not_promoted",
            "next_round_role": "progression_material_only",
        },
        {
            "material_id": "reaka_p7_2020_cross_clock_conflict",
            "evidence_ref": (
                "docs/ops/evidence/reaka_intraday_portfolio_mapping_account_v1_20260901/"
                "annual_sessions/2020/analysis_ledger.json"
            ),
            "status": "positive_1430_negative_1445_tradeoff",
            "next_round_role": "progression_material_only",
        },
        {
            "material_id": "reaka_p7_2020_1445_clock_7_of_10_quarterly_weak",
            "evidence_ref": (
                "output/factor-rotation/reaka_intraday_portfolio_mapping_account_v2_2009_2020/"
                "annual_sessions/2020/formal/session_receipt.json"
            ),
            "status": "clock_progress_not_nominated",
            "next_round_role": "progression_material_only",
        },
    ]
    payload: dict[str, object] = {
        "schema_id": "factorlab.reaka_p7_progression_migration@1.0",
        "historical_verdict_unchanged": True,
        "historical_verdict": "competition_completed_no_challenger_policy_and_no_clock_nominated",
        "retained_progression_materials": materials,
        "material_count": len(materials),
        "old_receipts_rewritten": False,
        "historical_strategy_reselected": False,
        "consumed_history_rerun": False,
        "fresh_oos": False,
        "production_authority": False,
    }
    payload["canonical_digest"] = canonical_digest(payload)
    return payload


def validate_reaka_p7_adapter(
    compatibility: Mapping[str, object],
    migration: Mapping[str, object],
) -> list[str]:
    blockers: list[str] = []
    compatibility_body = dict(compatibility)
    compatibility_digest = compatibility_body.pop("canonical_digest", None)
    if compatibility_digest != canonical_digest(compatibility_body):
        blockers.append("reaka_adapter_compatibility_digest_mismatch")
    expected_policy_ids = [policy.policy_id for policy in build_policy_grid()]
    if cast(list[object], compatibility.get("policy_ids", [])) != expected_policy_ids:
        blockers.append("reaka_adapter_policy_ids_drifted")
    if compatibility.get("attempt_count") != 144:
        blockers.append("reaka_adapter_attempt_count_drifted")
    if compatibility.get("historical_final_selected_policy_is_winner") is not False:
        blockers.append("reaka_adapter_rewrote_administrative_root_as_winner")
    migration_body = dict(migration)
    migration_digest = migration_body.pop("canonical_digest", None)
    if migration_digest != canonical_digest(migration_body):
        blockers.append("reaka_progression_migration_digest_mismatch")
    if migration.get("historical_verdict_unchanged") is not True:
        blockers.append("reaka_progression_migration_rejudged_history")
    if migration.get("consumed_history_rerun") is not False:
        blockers.append("reaka_progression_migration_reran_consumed_history")
    if any(
        migration.get(key) is not False
        for key in ("old_receipts_rewritten", "historical_strategy_reselected", "production_authority")
    ):
        blockers.append("reaka_progression_migration_authority_fail_open")
    return blockers


__all__ = [
    "SCHEMA_ID",
    "build_reaka_p7_compatibility_map",
    "build_reaka_p7_progression_migration_ledger",
    "validate_reaka_p7_adapter",
]
