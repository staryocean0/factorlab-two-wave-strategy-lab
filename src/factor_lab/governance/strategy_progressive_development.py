# pyright: reportArgumentType=false

"""Hard-validity, progression-retention, and post-training audit governance."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Literal, cast

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest

PROGRESSION_SCHEMA_ID: Final = "factorlab.strategy_progressive_development@1.0"
POST_TRAINING_SCHEMA_ID: Final = "factorlab.post_training_account_audit@1.0"
PROGRESSION_CONTRACT_DIGEST: Final = (
    "sha256:af41d0f66c9ef3a12f61e01afa19dc021b249877a18b6b52244d7c958040141b"
)
POST_TRAINING_CONTRACT_DIGEST: Final = (
    "sha256:b7ac658bc4989cdb8367522458cd20f7f2e952d6926e09867dcd3acf31638413"
)
PROGRESSION_CONTRACT_RELATIVE: Final = Path("docs/ops/strategy_progressive_development@1.0.json")
POST_TRAINING_CONTRACT_RELATIVE: Final = Path("docs/ops/post_training_account_audit@1.0.json")
SOURCE_REFS: Final[tuple[str, ...]] = (
    ".codex/skills/strategy-slice-rebuild/SKILL.md",
    ".codex/skills/strategy-slice-rebuild/references/project-contract.md",
    ".codex/skills/strategy-slice-rebuild/references/post-training-account-audit.md",
    "docs/user/strategy_slice_rebuild_workflow.md",
    "docs/ops/strategy_slice_rebuild_whitepaper.md",
    "docs/ops/strategy_progressive_development@1.0.json",
    "docs/ops/post_training_account_audit@1.0.json",
    "docs/ops/strategy_progressive_development_whitepaper.md",
    "docs/user/strategy_progressive_development_workflow.md",
    "src/factor_lab/governance/strategy_progressive_development.py",
    "src/factor_lab/portfolio/post_training_account_audit.py",
    "src/factor_lab/factor_rotation/reaka_post_training_account_adapter.py",
    "src/factor_lab/factor_rotation/reaka_intraday_portfolio_mapping_v1.py",
    "docs/ops/reaka_intraday_portfolio_mapping@1.2.json",
    "docs/ops/reaka_intraday_portfolio_mapping_whitepaper.md",
    "docs/user/reaka_intraday_portfolio_mapping_workflow.md",
    "tests/unit/test_reaka_intraday_portfolio_mapping_v1.py",
    "scripts/build_strategy_progressive_development_workflow.py",
    "scripts/validate_strategy_progressive_development_workflow.py",
    "scripts/freeze_post_training_account_audit_plan.py",
    "scripts/validate_post_training_account_audit.py",
    "tests/unit/test_strategy_progressive_development.py",
    "scripts/factor_rotation/validate_reaka_intraday_portfolio_mapping_account_chain_v1.py",
    "tests/unit/test_reaka_intraday_portfolio_mapping_account_chain_v1.py",
    "docs/ops/reaka_intraday_portfolio_mapping_final_result.md",
    "docs/user/reaka_intraday_portfolio_mapping_final_handoff.md",
    "docs/ops/evidence/reaka_intraday_portfolio_mapping_account_final_v1_20260902/validation_report.json",
    "docs/ops/evidence/reaka_intraday_portfolio_mapping_account_final_v1_20260902/controller_acceptance.json",
    "docs/ops/evidence/strategy_progressive_development_infrastructure_v1_20260902/historical_v4_source_closure_incident.json",
)

HardDomain = Literal[
    "financial_semantics",
    "mathematical_identity",
    "temporal_causality",
    "execution_accounting",
    "reproducibility_and_source_closure",
    "evidence_scope_and_multiplicity",
    "authority_boundary",
]
ProgressionStatus = Literal[
    "invalid_rejected",
    "evidence_inconclusive",
    "no_measured_progress",
    "progress_material_retained",
    "progress_tradeoff_waiting_financial_owner",
    "progressive_research_snapshot",
    "retrospective_candidate_promoted",
]
PromotionStatus = Literal["not_evaluated", "blocked", "promoted"]
RobustnessLabel = Literal[
    "not_applicable",
    "weak_or_concentrated",
    "tradeoff_unresolved",
    "promotion_grade",
]
FinalScientificStatus = Literal[
    "retrospective_candidate_selected",
    "retain_common_root_no_increment",
    "progress_retained_no_policy_replacement",
    "candidate_family_insufficient",
    "opportunity_absent_inconclusive",
    "infrastructure_gap",
]

HARD_DOMAINS: Final[tuple[HardDomain, ...]] = (
    "financial_semantics",
    "mathematical_identity",
    "temporal_causality",
    "execution_accounting",
    "reproducibility_and_source_closure",
    "evidence_scope_and_multiplicity",
    "authority_boundary",
)


def _require_text(value: str, label: str) -> None:
    if not value.strip():
        raise ValidationError(f"{label} cannot be empty")


def _canonical_valid(payload: dict[str, object]) -> bool:
    body = dict(payload)
    stored = body.pop("canonical_digest", None)
    return stored == canonical_digest(body)


def _read_json(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


@dataclass(frozen=True, slots=True)
class HardValidityCheck:
    """One non-compensable financial, mathematical, temporal, or audit check."""

    check_id: str
    domain: HardDomain
    passed: bool
    evidence_refs: tuple[str, ...]
    failure_code: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.check_id, "check_id")
        if self.domain not in HARD_DOMAINS:
            raise ValidationError("unsupported hard-validity domain")
        if not self.evidence_refs or any(not value.strip() for value in self.evidence_refs):
            raise ValidationError("hard-validity checks require evidence references")
        if self.passed and self.failure_code is not None:
            raise ValidationError("a passed hard check cannot carry a failure code")
        if not self.passed and (self.failure_code is None or not self.failure_code.strip()):
            raise ValidationError("a failed hard check requires a failure code")


@dataclass(frozen=True, slots=True)
class ProgressMeasurement:
    """Comparable full-account evidence used for retention before promotion."""

    candidate_id: str
    comparator_id: str
    primary_metric_id: str
    candidate_value: float
    comparator_value: float
    higher_is_better: bool
    numerical_tolerance: float
    attempt_id: str
    attempt_count: int
    hard_checks: tuple[HardValidityCheck, ...]
    same_account_and_cost_basis: bool = True
    preregistered_primary_objective: bool = True
    full_account_repriced: bool = True
    financial_tradeoff_unresolved: bool = False
    research_snapshot_selected: bool = False
    promotion_gate_passed: bool = False
    affected_period_count: int = 0
    positive_affected_period_count: int = 0
    contribution_concentration: float = 0.0

    def __post_init__(self) -> None:
        for label, value in (
            ("candidate_id", self.candidate_id),
            ("comparator_id", self.comparator_id),
            ("primary_metric_id", self.primary_metric_id),
            ("attempt_id", self.attempt_id),
        ):
            _require_text(value, label)
        if self.candidate_id == self.comparator_id:
            raise ValidationError("a progression candidate must differ from its comparator")
        if not math.isfinite(self.candidate_value) or not math.isfinite(self.comparator_value):
            raise ValidationError("progression metric values must be finite")
        if not math.isfinite(self.numerical_tolerance) or self.numerical_tolerance < 0.0:
            raise ValidationError("numerical tolerance must be finite and nonnegative")
        if self.attempt_count < 1 or not self.hard_checks:
            raise ValidationError("progression evidence needs attempts and hard checks")
        if not 0 <= self.positive_affected_period_count <= self.affected_period_count:
            raise ValidationError("affected-period counts are invalid")
        if not 0.0 <= self.contribution_concentration <= 1.0:
            raise ValidationError("contribution concentration must be within [0, 1]")
        if self.promotion_gate_passed and self.financial_tradeoff_unresolved:
            raise ValidationError("an unresolved financial tradeoff cannot be promoted")

    def signed_improvement(self) -> float:
        raw = self.candidate_value - self.comparator_value
        return raw if self.higher_is_better else -raw


@dataclass(frozen=True, slots=True)
class StrategyProgressionDecision:
    """A retention decision whose promotion and production authorities stay separate."""

    status: ProgressionStatus
    candidate_id: str
    comparator_id: str
    signed_improvement: float
    retained_for_future_research: bool
    research_snapshot_selected: bool
    promotion_status: PromotionStatus
    robustness_label: RobustnessLabel
    failed_hard_check_ids: tuple[str, ...]
    fresh_oos: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if self.fresh_oos or self.production_authority:
            raise ValidationError("retrospective progression cannot grant fresh or production authority")
        if self.status == "invalid_rejected" and self.retained_for_future_research:
            raise ValidationError("hard-invalid economics cannot be retained as progression")
        if self.status in {
            "progress_material_retained",
            "progress_tradeoff_waiting_financial_owner",
            "progressive_research_snapshot",
            "retrospective_candidate_promoted",
        } and not self.retained_for_future_research:
            raise ValidationError("a positive progression status must retain the material")
        if self.promotion_status == "promoted" and self.status != "retrospective_candidate_promoted":
            raise ValidationError("promotion status and progression status disagree")

    def semantic_digest(self) -> str:
        return canonical_digest(asdict(self))


def assess_progression(measurement: ProgressMeasurement) -> StrategyProgressionDecision:
    """Retain any hard-valid improvement above replay noise without weakening promotion."""

    failed = tuple(check.check_id for check in measurement.hard_checks if not check.passed)
    framework_failures: list[str] = []
    if not measurement.same_account_and_cost_basis:
        framework_failures.append("same_account_and_cost_basis")
    if not measurement.preregistered_primary_objective:
        framework_failures.append("preregistered_primary_objective")
    if not measurement.full_account_repriced:
        framework_failures.append("full_account_repriced")
    failed_all = (*failed, *framework_failures)
    improvement = measurement.signed_improvement()
    effective_tolerance = measurement.numerical_tolerance + max(
        math.ulp(measurement.candidate_value),
        math.ulp(measurement.comparator_value),
    )
    if failed_all:
        return StrategyProgressionDecision(
            status="invalid_rejected",
            candidate_id=measurement.candidate_id,
            comparator_id=measurement.comparator_id,
            signed_improvement=improvement,
            retained_for_future_research=False,
            research_snapshot_selected=False,
            promotion_status="not_evaluated",
            robustness_label="not_applicable",
            failed_hard_check_ids=failed_all,
        )
    if abs(improvement) <= effective_tolerance:
        return StrategyProgressionDecision(
            status="evidence_inconclusive",
            candidate_id=measurement.candidate_id,
            comparator_id=measurement.comparator_id,
            signed_improvement=improvement,
            retained_for_future_research=False,
            research_snapshot_selected=False,
            promotion_status="not_evaluated",
            robustness_label="not_applicable",
            failed_hard_check_ids=(),
        )
    if improvement < -effective_tolerance:
        return StrategyProgressionDecision(
            status="no_measured_progress",
            candidate_id=measurement.candidate_id,
            comparator_id=measurement.comparator_id,
            signed_improvement=improvement,
            retained_for_future_research=False,
            research_snapshot_selected=False,
            promotion_status="blocked",
            robustness_label="not_applicable",
            failed_hard_check_ids=(),
        )
    if measurement.financial_tradeoff_unresolved:
        return StrategyProgressionDecision(
            status="progress_tradeoff_waiting_financial_owner",
            candidate_id=measurement.candidate_id,
            comparator_id=measurement.comparator_id,
            signed_improvement=improvement,
            retained_for_future_research=True,
            research_snapshot_selected=False,
            promotion_status="blocked",
            robustness_label="tradeoff_unresolved",
            failed_hard_check_ids=(),
        )
    if measurement.promotion_gate_passed:
        return StrategyProgressionDecision(
            status="retrospective_candidate_promoted",
            candidate_id=measurement.candidate_id,
            comparator_id=measurement.comparator_id,
            signed_improvement=improvement,
            retained_for_future_research=True,
            research_snapshot_selected=True,
            promotion_status="promoted",
            robustness_label="promotion_grade",
            failed_hard_check_ids=(),
        )
    if measurement.research_snapshot_selected:
        return StrategyProgressionDecision(
            status="progressive_research_snapshot",
            candidate_id=measurement.candidate_id,
            comparator_id=measurement.comparator_id,
            signed_improvement=improvement,
            retained_for_future_research=True,
            research_snapshot_selected=True,
            promotion_status="blocked",
            robustness_label="weak_or_concentrated",
            failed_hard_check_ids=(),
        )
    return StrategyProgressionDecision(
        status="progress_material_retained",
        candidate_id=measurement.candidate_id,
        comparator_id=measurement.comparator_id,
        signed_improvement=improvement,
        retained_for_future_research=True,
        research_snapshot_selected=False,
        promotion_status="blocked",
        robustness_label="weak_or_concentrated",
        failed_hard_check_ids=(),
    )


@dataclass(frozen=True, slots=True)
class PostTrainingAuditPlan:
    """Result-free account-policy family bound to one frozen score identity."""

    audit_id: str
    strategy_id: str
    model_artifact_digest: str
    checkpoint_digests: tuple[str, ...]
    score_definition_digest: str
    score_panel_digest: str
    primary_objective_id: str
    common_root_policy_id: str
    policy_ids: tuple[str, ...]
    variant_ids: tuple[str, ...]
    cost_scenario_ids: tuple[str, ...]
    concentration_dimension_ids: tuple[str, ...]
    execution_rule: str
    intraday: bool
    model_mutation_allowed: bool = False
    formal_isolated_required: bool = True
    production_authority: bool = False

    def __post_init__(self) -> None:
        for label, value in (
            ("audit_id", self.audit_id),
            ("strategy_id", self.strategy_id),
            ("model_artifact_digest", self.model_artifact_digest),
            ("score_definition_digest", self.score_definition_digest),
            ("score_panel_digest", self.score_panel_digest),
            ("primary_objective_id", self.primary_objective_id),
            ("common_root_policy_id", self.common_root_policy_id),
            ("execution_rule", self.execution_rule),
        ):
            _require_text(value, label)
        for label, values in (
            ("checkpoint_digests", self.checkpoint_digests),
            ("policy_ids", self.policy_ids),
            ("variant_ids", self.variant_ids),
            ("cost_scenario_ids", self.cost_scenario_ids),
        ):
            if not values or len(set(values)) != len(values):
                raise ValidationError(f"{label} must be nonempty and unique")
        if self.common_root_policy_id not in self.policy_ids:
            raise ValidationError("common root is missing from the policy family")
        if self.intraday and self.execution_rule != "next_tradable_after_bar_close":
            raise ValidationError("intraday audits require next_tradable_after_bar_close")
        if self.model_mutation_allowed or not self.formal_isolated_required or self.production_authority:
            raise ValidationError("post-training audit authority failed open")

    @property
    def expected_attempt_count(self) -> int:
        return len(self.policy_ids) * len(self.variant_ids) * len(self.cost_scenario_ids)

    def semantic_digest(self) -> str:
        return canonical_digest(asdict(self))


@dataclass(frozen=True, slots=True)
class PostTrainingAuditReceipt:
    """Outcome-neutral completion proof for one post-training account audit."""

    audit_id: str
    plan_digest: str
    model_digest_before: str
    model_digest_after: str
    score_digest_before: str
    score_digest_after: str
    prior_policy_id: str
    blind_output_policy_ids: tuple[str, ...]
    blind_and_family_commands_separate: bool
    manual_blind_review_completed: bool
    family_attempt_count: int
    formal_tree_digest: str
    isolated_tree_digest: str
    scientific_bytes_identical: bool
    hard_checks: tuple[HardValidityCheck, ...]
    retained_progression_ids: tuple[str, ...]
    promoted_candidate_id: str | None
    final_scientific_status: FinalScientificStatus
    model_retrained_or_finetuned: bool = False
    future_rows_read: int = 0
    fresh_oos: bool = False
    production_authority: bool = False

    def validate_against(self, plan: PostTrainingAuditPlan) -> None:
        if self.audit_id != plan.audit_id or self.plan_digest != plan.semantic_digest():
            raise ValidationError("post-training receipt is bound to the wrong plan")
        if self.model_digest_before != plan.model_artifact_digest:
            raise ValidationError("post-training receipt started from the wrong model")
        if self.model_digest_after != self.model_digest_before:
            raise ValidationError("post-training audit mutated the frozen model")
        if self.score_digest_before != plan.score_panel_digest or self.score_digest_after != self.score_digest_before:
            raise ValidationError("post-training audit mutated the frozen score panel")
        if (
            self.blind_output_policy_ids != (self.prior_policy_id,)
            or not self.blind_and_family_commands_separate
            or not self.manual_blind_review_completed
        ):
            raise ValidationError("blind and family account phases were not separated")
        if self.family_attempt_count != plan.expected_attempt_count:
            raise ValidationError("post-training family attempt denominator drifted")
        if (
            not self.scientific_bytes_identical
            or self.formal_tree_digest != self.isolated_tree_digest
            or any(not check.passed for check in self.hard_checks)
        ):
            raise ValidationError("post-training scientific validation failed")
        if self.promoted_candidate_id is not None and self.promoted_candidate_id not in plan.policy_ids:
            raise ValidationError("post-training receipt promoted an unknown policy")
        if self.final_scientific_status == "retrospective_candidate_selected":
            if self.promoted_candidate_id is None:
                raise ValidationError("selected status requires a promoted candidate")
        elif self.promoted_candidate_id is not None:
            raise ValidationError("non-selected status cannot carry a promoted candidate")
        if (
            self.model_retrained_or_finetuned
            or self.future_rows_read != 0
            or self.fresh_oos
            or self.production_authority
        ):
            raise ValidationError("post-training receipt exceeded retrospective authority")


def validate_progression_contract(payload: dict[str, object]) -> None:
    if not _canonical_valid(payload) or payload.get("canonical_digest") != PROGRESSION_CONTRACT_DIGEST:
        raise ValidationError("progression contract digest mismatch")
    if payload.get("schema_id") != PROGRESSION_SCHEMA_ID:
        raise ValidationError("progression contract schema mismatch")
    retention = cast(dict[str, object], payload.get("progression_retention"))
    if (
        retention.get("minimum_effect_size_gate_allowed") is not False
        or retention.get("positive_improvement_above_numerical_tolerance_is_retained") is not True
        or retention.get("failed_promotion_gate_may_delete_valid_progress") is not False
    ):
        raise ValidationError("progression retention semantics drifted")
    hard = cast(dict[str, object], payload.get("hard_validity_gate"))
    if hard.get("compensable_by_performance") is not False or tuple(
        cast(list[object], hard.get("domains", []))
    ) != HARD_DOMAINS:
        raise ValidationError("hard-validity governance drifted")
    migration = cast(dict[str, object], payload.get("historical_migration"))
    if migration.get("old_contracts_and_receipts_are_immutable") is not True:
        raise ValidationError("historical progression evidence became mutable")
    if payload.get("production_authority") is not False:
        raise ValidationError("progression contract granted production authority")


def validate_post_training_contract(payload: dict[str, object]) -> None:
    if not _canonical_valid(payload) or payload.get("canonical_digest") != POST_TRAINING_CONTRACT_DIGEST:
        raise ValidationError("post-training contract digest mismatch")
    if payload.get("schema_id") != POST_TRAINING_SCHEMA_ID:
        raise ValidationError("post-training contract schema mismatch")
    stages = cast(list[str], payload.get("stages", []))
    if stages != [
        "A0_freeze_model_score_identity",
        "A1_freeze_result_free_account_family",
        "A2_materialize_causal_formal_isolated_inputs",
        "A3_validate_and_benchmark_exact_workload",
        "A4_blind_test_prior_account_policy_only",
        "A5_manual_review_then_reprice_complete_family",
        "A6_seal_year_receipt_and_prior_policy_chain",
        "A7_outcome_neutral_final_audit_and_handoff",
    ]:
        raise ValidationError("post-training stage atlas drifted")
    blind = cast(dict[str, object], payload.get("blind_family_separation"))
    if (
        blind.get("blind_and_family_execution_may_share_one_command") is not False
        or blind.get("blind_output_may_contain_non_prior_policy") is not False
        or blind.get("family_execution_requires_completed_manual_blind_review") is not True
    ):
        raise ValidationError("post-training blind-family separation drifted")
    invariants = cast(dict[str, object], payload.get("hard_invariants"))
    if invariants.get("account_result_may_retrain_model") is not False:
        raise ValidationError("post-training account results may retrain the model")
    if invariants.get("formal_isolated_scientific_bytes_required") is not True:
        raise ValidationError("post-training determinism gate failed open")
    if payload.get("final_validator_outcome_neutral") is not True:
        raise ValidationError("post-training validator is outcome-specific")
    if payload.get("production_authority") is not False:
        raise ValidationError("post-training contract granted production authority")


def load_frozen_contracts(repo_root: Path) -> tuple[dict[str, object], dict[str, object]]:
    progression = _read_json(repo_root / PROGRESSION_CONTRACT_RELATIVE)
    post_training = _read_json(repo_root / POST_TRAINING_CONTRACT_RELATIVE)
    validate_progression_contract(progression)
    validate_post_training_contract(post_training)
    return progression, post_training


def post_training_plan_from_payload(payload: dict[str, object]) -> PostTrainingAuditPlan:
    """Parse and validate a canonical or pre-freeze plan payload."""

    body = dict(payload)
    stored = body.pop("canonical_digest", None)
    for key in (
        "checkpoint_digests",
        "policy_ids",
        "variant_ids",
        "cost_scenario_ids",
        "concentration_dimension_ids",
    ):
        body[key] = tuple(cast(list[object], body.get(key, [])))
    plan = PostTrainingAuditPlan(**body)  # type: ignore[arg-type]
    if stored is not None and stored != plan.semantic_digest():
        raise ValidationError("post-training plan canonical digest mismatch")
    return plan


def post_training_receipt_from_payload(payload: dict[str, object]) -> PostTrainingAuditReceipt:
    """Parse a receipt while preserving outcome-neutral scientific statuses."""

    body = dict(payload)
    stored = body.pop("canonical_digest", None)
    checks = tuple(
        HardValidityCheck(**cast(dict[str, object], row))  # type: ignore[arg-type]
        for row in cast(list[object], body.get("hard_checks", []))
    )
    body["hard_checks"] = checks
    body["blind_output_policy_ids"] = tuple(
        cast(list[object], body.get("blind_output_policy_ids", []))
    )
    body["retained_progression_ids"] = tuple(
        cast(list[object], body.get("retained_progression_ids", []))
    )
    receipt = PostTrainingAuditReceipt(**body)  # type: ignore[arg-type]
    if stored is not None and stored != canonical_digest(asdict(receipt)):
        raise ValidationError("post-training receipt canonical digest mismatch")
    return receipt


__all__ = [
    "HARD_DOMAINS",
    "POST_TRAINING_CONTRACT_DIGEST",
    "POST_TRAINING_SCHEMA_ID",
    "PROGRESSION_CONTRACT_DIGEST",
    "PROGRESSION_SCHEMA_ID",
    "SOURCE_REFS",
    "HardValidityCheck",
    "PostTrainingAuditPlan",
    "PostTrainingAuditReceipt",
    "ProgressMeasurement",
    "StrategyProgressionDecision",
    "assess_progression",
    "load_frozen_contracts",
    "post_training_plan_from_payload",
    "post_training_receipt_from_payload",
    "validate_post_training_contract",
    "validate_progression_contract",
]
