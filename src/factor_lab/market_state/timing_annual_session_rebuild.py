"""Isolated annual-session whole-policy rebuild governance.

Each annual session first challenges the policy frozen by the preceding
session, then turns the newly opened year into research material and rebuilds a
complete policy from the common root plus this experiment branch's cumulative
materials.  Parallel experiments are evidence-isolated: they may share the
common root and raw carrier data, but never policies, ledgers, candidate
families, parameters, conclusions, or lockbox results.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Final, Literal, cast

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest

SCHEMA_ID: Final[str] = "strategy_annual_session_rebuild@4.0"
CODE_VERSION: Final[str] = "strategy-annual-session-rebuild-20260812-r2"

SOURCE_REFS: Final[tuple[str, ...]] = (
    ".codex/skills/strategy-slice-rebuild/SKILL.md",
    ".codex/skills/strategy-slice-rebuild/references/project-contract.md",
    "AGENTS.md",
    "ai-readme.md",
    "docs/user/strategy_slice_rebuild_workflow.md",
    "docs/ops/strategy_slice_rebuild_whitepaper.md",
    "src/factor_lab/market_state/timing_annual_session_rebuild.py",
    "scripts/build_strategy_slice_rebuild_workflow.py",
    "scripts/validate_strategy_slice_rebuild_workflow.py",
    "tests/unit/test_strategy_annual_session_rebuild.py",
)

SessionConclusion = Literal[
    "no_new_root",
    "root_hypothesis",
    "resolved_root",
    "infrastructure_gap",
]
RootStatus = Literal["unresolved", "resolved"]
SuccessorStatus = Literal[
    "frozen_nontrivial_research_candidate",
    "no_incremental_successor",
    "candidate_family_insufficient",
]


def _require_text(value: str, label: str) -> None:
    if not value.strip():
        raise ValidationError(f"{label} cannot be empty")


@dataclass(frozen=True, slots=True)
class BranchIsolationDeclaration:
    """Clean-room boundary for one experiment parallel to other rebuilds."""

    experiment_id: str
    common_root_policy_id: str
    common_root_policy_digest: str
    allowed_source_roots: tuple[str, ...]
    forbidden_parallel_experiment_ids: tuple[str, ...]
    forbidden_source_roots: tuple[str, ...]
    inherited_parent_experiment_id: str | None = None
    parallel_results_used_for_design: bool = False
    parallel_results_used_for_selection: bool = False
    clean_room_required: bool = True

    def __post_init__(self) -> None:
        for label, value in (
            ("experiment_id", self.experiment_id),
            ("common_root_policy_id", self.common_root_policy_id),
            ("common_root_policy_digest", self.common_root_policy_digest),
        ):
            _require_text(value, label)
        if self.inherited_parent_experiment_id is not None:
            raise ValidationError("an isolated parallel experiment cannot inherit a sibling experiment")
        if not self.allowed_source_roots or not self.forbidden_parallel_experiment_ids:
            raise ValidationError("branch isolation needs explicit allow and deny inventories")
        if set(self.allowed_source_roots) & set(self.forbidden_source_roots):
            raise ValidationError("allowed and forbidden source roots overlap")
        if self.experiment_id in self.forbidden_parallel_experiment_ids:
            raise ValidationError("the current experiment cannot forbid itself")
        if (
            self.parallel_results_used_for_design
            or self.parallel_results_used_for_selection
            or not self.clean_room_required
        ):
            raise ValidationError("parallel experiment evidence contaminated the clean room")


@dataclass(frozen=True, slots=True)
class AnnualSliceSpec:
    """One independent material-discovery year, never a runtime feature."""

    slice_id: str
    start: str
    end_exclusive: str
    session_order: int
    duration_months: int = 12
    calendar_identity_used_as_feature: bool = False
    runtime_rule_authority: bool = False

    def __post_init__(self) -> None:
        _require_text(self.slice_id, "slice_id")
        start = date.fromisoformat(self.start)
        end = date.fromisoformat(self.end_exclusive)
        if start.month != 1 or start.day != 1 or end != date(start.year + 1, 1, 1):
            raise ValidationError("annual research slices must be natural years")
        if self.duration_months != 12 or self.session_order < 1:
            raise ValidationError("annual research slice metadata is invalid")
        if self.calendar_identity_used_as_feature or self.runtime_rule_authority:
            raise ValidationError("annual slice identity cannot enter a runtime policy")


def canonical_pre2021_annual_sessions() -> tuple[AnnualSliceSpec, ...]:
    """Return twelve disjoint natural-year research sessions for 2009--2020."""

    return tuple(
        AnnualSliceSpec(
            slice_id=f"annual_{year}",
            start=f"{year}-01-01",
            end_exclusive=f"{year + 1}-01-01",
            session_order=order,
        )
        for order, year in enumerate(range(2009, 2021), start=1)
    )


def validate_annual_slice_atlas(slices: tuple[AnnualSliceSpec, ...]) -> None:
    expected = canonical_pre2021_annual_sessions()
    if slices != expected:
        raise ValidationError("annual session atlas must be the twelve canonical disjoint years")


@dataclass(frozen=True, slots=True)
class AnnualResearchSessionReceipt:
    """Completion proof for one deliberately reviewed annual research session."""

    session_id: str
    session_order: int
    slice_id: str
    prior_policy_id: str
    prior_policy_digest: str
    evidence_pack_path: str
    blind_backtest_path: str
    graph_event_ledger_path: str
    analysis_ledger_path: str
    rebuild_preregistration_path: str
    rebuild_receipt_path: str
    rebuilt_policy_id: str
    rebuilt_policy_digest: str
    observed_material_ids: tuple[str, ...]
    cumulative_material_ids: tuple[str, ...]
    root_hypothesis_ids: tuple[str, ...]
    promoted_obligation_ids: tuple[str, ...]
    conclusion: SessionConclusion
    prior_session_receipt_digest: str | None
    evidence_review_completed: bool = True
    prior_policy_blind_backtest_completed: bool = True
    graph_event_attribution_completed: bool = True
    problem_attribution_completed: bool = True
    constraint_review_completed: bool = True
    whole_policy_rebuilt: bool = True
    rebuilt_from_common_root_and_branch_materials: bool = True
    incremental_patch_from_prior_policy: bool = False
    parallel_branch_material_used: bool = False
    blind_backtest_candidate_ranking_performed: bool = False
    interpretation_or_promotion_automated: bool = False
    batch_generated: bool = False
    next_session_started_before_completion: bool = False
    calendar_identity_used_as_feature: bool = False
    runtime_rule_authority: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        for label, value in (
            ("session_id", self.session_id),
            ("slice_id", self.slice_id),
            ("prior_policy_id", self.prior_policy_id),
            ("prior_policy_digest", self.prior_policy_digest),
            ("evidence_pack_path", self.evidence_pack_path),
            ("blind_backtest_path", self.blind_backtest_path),
            ("graph_event_ledger_path", self.graph_event_ledger_path),
            ("analysis_ledger_path", self.analysis_ledger_path),
            ("rebuild_preregistration_path", self.rebuild_preregistration_path),
            ("rebuild_receipt_path", self.rebuild_receipt_path),
            ("rebuilt_policy_id", self.rebuilt_policy_id),
            ("rebuilt_policy_digest", self.rebuilt_policy_digest),
        ):
            _require_text(value, label)
        if self.session_order < 1 or not self.observed_material_ids:
            raise ValidationError("annual session must record at least one reviewed observation")
        if len(set(self.observed_material_ids)) != len(self.observed_material_ids):
            raise ValidationError("annual session observations must be unique")
        if not self.cumulative_material_ids or not set(self.observed_material_ids).issubset(
            self.cumulative_material_ids
        ):
            raise ValidationError("annual rebuild must retain every current observation")
        if len(set(self.cumulative_material_ids)) != len(self.cumulative_material_ids):
            raise ValidationError("cumulative material ids must be unique")
        if self.conclusion not in {
            "no_new_root",
            "root_hypothesis",
            "resolved_root",
            "infrastructure_gap",
        }:
            raise ValidationError("unsupported annual session conclusion")
        if self.promoted_obligation_ids and self.conclusion != "resolved_root":
            raise ValidationError("only a resolved root may propose a hard obligation")
        if not (
            self.evidence_review_completed
            and self.prior_policy_blind_backtest_completed
            and self.graph_event_attribution_completed
            and self.problem_attribution_completed
            and self.constraint_review_completed
            and self.whole_policy_rebuilt
            and self.rebuilt_from_common_root_and_branch_materials
        ):
            raise ValidationError("annual research session review is incomplete")
        if (
            self.incremental_patch_from_prior_policy
            or self.parallel_branch_material_used
            or self.blind_backtest_candidate_ranking_performed
            or self.interpretation_or_promotion_automated
            or self.batch_generated
            or self.next_session_started_before_completion
        ):
            raise ValidationError("annual sessions violated blind-test, clean-room, or whole-rebuild governance")
        if self.calendar_identity_used_as_feature or self.runtime_rule_authority:
            raise ValidationError("annual research output cannot directly become a runtime rule")
        if self.production_authority:
            raise ValidationError("retrospective annual sessions cannot grant production authority")

    def payload(self) -> dict[str, object]:
        return asdict(self)

    def semantic_digest(self) -> str:
        return canonical_digest(self.payload())


def validate_annual_research_sessions(
    receipts: tuple[AnnualResearchSessionReceipt, ...],
    *,
    slices: tuple[AnnualSliceSpec, ...] | None = None,
    isolation: BranchIsolationDeclaration | None = None,
) -> None:
    """Require twelve completed, sequential, separately persisted reviews."""

    if slices is None:
        slices = canonical_pre2021_annual_sessions()
    validate_annual_slice_atlas(slices)
    if len(receipts) != len(slices):
        raise ValidationError("all twelve annual research sessions must be completed")
    if isolation is None:
        raise ValidationError("annual session validation requires a branch isolation declaration")
    evidence_paths: set[str] = set()
    analysis_paths: set[str] = set()
    auxiliary_paths: set[str] = set()
    for index, (receipt, slice_spec) in enumerate(zip(receipts, slices, strict=True)):
        if (
            receipt.session_order != slice_spec.session_order
            or receipt.slice_id != slice_spec.slice_id
            or receipt.session_id != f"session_{slice_spec.session_order:02d}_{slice_spec.slice_id}"
        ):
            raise ValidationError("annual session sequence drifted from the frozen atlas")
        expected_prior = None if index == 0 else receipts[index - 1].semantic_digest()
        if receipt.prior_session_receipt_digest != expected_prior:
            raise ValidationError("annual session receipt chain is incomplete or out of order")
        expected_prior_policy_id = (
            isolation.common_root_policy_id if index == 0 else receipts[index - 1].rebuilt_policy_id
        )
        expected_prior_policy_digest = (
            isolation.common_root_policy_digest if index == 0 else receipts[index - 1].rebuilt_policy_digest
        )
        if (
            receipt.prior_policy_id != expected_prior_policy_id
            or receipt.prior_policy_digest != expected_prior_policy_digest
        ):
            raise ValidationError("annual policy snapshot chain is incomplete or skipped")
        if index:
            prior_materials = set(receipts[index - 1].cumulative_material_ids)
            if not prior_materials.issubset(receipt.cumulative_material_ids):
                raise ValidationError("annual rebuild discarded prior branch materials")
            if not set(receipt.observed_material_ids) - prior_materials:
                raise ValidationError("annual session added no year-specific material")
        if receipt.evidence_pack_path in evidence_paths or receipt.analysis_ledger_path in analysis_paths:
            raise ValidationError("each annual session needs separate evidence and analysis files")
        evidence_paths.add(receipt.evidence_pack_path)
        analysis_paths.add(receipt.analysis_ledger_path)
        for path in (
            receipt.blind_backtest_path,
            receipt.graph_event_ledger_path,
            receipt.rebuild_preregistration_path,
            receipt.rebuild_receipt_path,
        ):
            if path in auxiliary_paths:
                raise ValidationError("each annual session needs separate blind-test and rebuild files")
            auxiliary_paths.add(path)


@dataclass(frozen=True, slots=True)
class RootCauseHypothesis:
    """A cross-session mechanism hypothesis distilled from raw observations."""

    root_cause_id: str
    source_session_ids: tuple[str, ...]
    source_material_ids: tuple[str, ...]
    mechanism_statement_zh: str
    falsifiable_contrast_zh: str
    status: RootStatus
    economically_material: bool
    frozen_causal_challenge_support: bool = False
    calendar_identity_used_as_feature: bool = False

    def __post_init__(self) -> None:
        for label, value in (
            ("root_cause_id", self.root_cause_id),
            ("mechanism_statement_zh", self.mechanism_statement_zh),
            ("falsifiable_contrast_zh", self.falsifiable_contrast_zh),
        ):
            _require_text(value, label)
        if not self.source_session_ids or not self.source_material_ids:
            raise ValidationError("root hypothesis needs source sessions and observations")
        if self.status not in {"unresolved", "resolved"}:
            raise ValidationError("unsupported root status")
        if self.status == "resolved" and not self.economically_material:
            raise ValidationError("an immaterial root cannot become resolved policy authority")
        if self.status == "resolved" and len(set(self.source_session_ids)) < 2 and not self.frozen_causal_challenge_support:
            raise ValidationError("resolved roots need replication or a frozen causal challenge")
        if self.calendar_identity_used_as_feature:
            raise ValidationError("a root cause cannot be a calendar label")


@dataclass(frozen=True, slots=True)
class HardObligation:
    """One policy obligation promoted from one resolved mechanism root."""

    obligation_id: str
    root_cause_id: str
    required_behavior_zh: str
    forbidden_behavior_zh: str
    promotion_basis: Literal[
        "replicated_independent_sessions",
        "frozen_causal_challenge",
        "structural_invariant",
    ]
    forbidden_revised_owner_ids: tuple[str, ...] = ()
    runtime_rule_authority: bool = False
    calendar_identity_used_as_feature: bool = False

    def __post_init__(self) -> None:
        for label, value in (
            ("obligation_id", self.obligation_id),
            ("root_cause_id", self.root_cause_id),
            ("required_behavior_zh", self.required_behavior_zh),
            ("forbidden_behavior_zh", self.forbidden_behavior_zh),
        ):
            _require_text(value, label)
        if self.runtime_rule_authority or self.calendar_identity_used_as_feature:
            raise ValidationError("research obligations cannot directly encode runtime/calendar rules")
        if len(set(self.forbidden_revised_owner_ids)) != len(self.forbidden_revised_owner_ids):
            raise ValidationError("forbidden revised-owner ids must be unique")


def validate_hard_obligation_promotions(
    roots: tuple[RootCauseHypothesis, ...],
    obligations: tuple[HardObligation, ...],
    *,
    candidate_family_effective_dof: int,
) -> None:
    """Prevent raw-case volume from becoming an unbounded veto surface."""

    if candidate_family_effective_dof < 1:
        raise ValidationError("candidate-family effective degrees of freedom must be positive")
    by_id = {root.root_cause_id: root for root in roots}
    if len(by_id) != len(roots):
        raise ValidationError("root-cause ids must be unique")
    if len(obligations) > candidate_family_effective_dof:
        raise ValidationError("hard-obligation count exceeds candidate-family expressive capacity")
    root_ids = [item.root_cause_id for item in obligations]
    if len(root_ids) != len(set(root_ids)):
        raise ValidationError("one root cause may promote at most one hard obligation")
    for obligation in obligations:
        root = by_id.get(obligation.root_cause_id)
        if root is None or root.status != "resolved":
            raise ValidationError("unresolved or unknown roots cannot become hard obligations")
        if obligation.promotion_basis == "frozen_causal_challenge" and not root.frozen_causal_challenge_support:
            raise ValidationError("frozen-challenge promotion lacks causal support")


@dataclass(frozen=True, slots=True)
class SuccessorDecision:
    """Scientific status of a rebuilt family; a baseline fallback is never a new version."""

    status: SuccessorStatus
    baseline_candidate_id: str
    selected_candidate_id: str | None
    selected_changed_claim_count: int
    selected_account_path_equals_baseline: bool
    all_hard_obligations_passed: bool
    candidate_family_gap_detected: bool
    production_authority: bool = False

    def __post_init__(self) -> None:
        _require_text(self.baseline_candidate_id, "baseline_candidate_id")
        if self.status not in {
            "frozen_nontrivial_research_candidate",
            "no_incremental_successor",
            "candidate_family_insufficient",
        }:
            raise ValidationError("unsupported successor status")
        if self.production_authority:
            raise ValidationError("retrospective successor decisions cannot grant production authority")
        if self.status == "frozen_nontrivial_research_candidate":
            if (
                self.selected_candidate_id is None
                or self.selected_candidate_id == self.baseline_candidate_id
                or self.selected_changed_claim_count < 1
                or self.selected_account_path_equals_baseline
                or not self.all_hard_obligations_passed
                or self.candidate_family_gap_detected
            ):
                raise ValidationError("a frozen successor must be nontrivial and fully admissible")
        elif self.selected_candidate_id not in {None, self.baseline_candidate_id}:
            raise ValidationError("failed successor states cannot publish a challenger")


def build_strategy_slice_rebuild_contract() -> dict[str, object]:
    """Build the project-level annual-session strategy-development contract."""

    slices = canonical_pre2021_annual_sessions()
    stages = (
        ("s1_declare_data_roles", "封印开发、复审、新鲜挑战与聚合黑箱边界。"),
        ("s2_seal_parallel_branch", "冻结共同起点、允许源和并行实验禁读清单。"),
        ("s3_freeze_execution", "冻结执行、T+1、成本、指标与本轮搜索预算。"),
        ("s4_build_annual_atlas", "只建立十二个互不重叠自然年研究会话。"),
        ("s5_blind_challenge_prior", "每年先只盲测上一会话冻结的完整策略。"),
        ("s6_attribute_open_ended", "逐图逐事件寻找问题，不把旧候选空间当答案边界。"),
        ("s7_distill_branch_roots", "只用共同起点与本支线累计材料归并机制根因。"),
        ("s8_preregister_round_family", "观察后先预登记本轮有界整案族和搜索次数。"),
        ("s9_rebuild_whole_policy", "每个年度会话都从共同起点整案重建而非补丁继承。"),
        ("s10_seal_snapshot", "每年封存新策略、台账与链式回执后才能打开下一年。"),
        ("s11_require_nontrivial_successor", "基准或账户等价回退必须报告无增量。"),
        ("s12_wait_fresh_challenge", "2020重建后只标研究候选，等待真正未见时段。"),
    )
    payload: dict[str, object] = {
        "schema_id": SCHEMA_ID,
        "code_version": CODE_VERSION,
        "purpose_zh": "让并行实验从共同起点隔离出发，每年盲测、归因、整案重建并封存新快照。",
        "stage_count": len(stages),
        "stages": [{"stage_id": stage_id, "requirement_zh": requirement} for stage_id, requirement in stages],
        "canonical_slices": [asdict(item) for item in slices],
        "session_protocol": {
            "session_count": 12,
            "rolling_or_offset_windows_allowed": False,
            "one_year_per_session": True,
            "single_year_evidence_invocation_only": True,
            "shell_loop_or_batch_driver_allowed": False,
            "evidence_preparation_may_be_automated": True,
            "interpretation_or_promotion_may_be_automated": False,
            "batch_session_completion_allowed": False,
            "manual_analysis_ledger_required": True,
            "manual_constraint_review_required": True,
            "main_researcher_signoff_required": True,
            "next_session_requires_prior_receipt_digest": True,
            "next_session_requires_prior_policy_digest": True,
            "blind_backtest_candidate_ranking_allowed": False,
            "post_attribution_bounded_rebuild_allowed": True,
            "whole_policy_rebuild_every_session_required": True,
            "incremental_patch_from_prior_winner_allowed": False,
            "common_root_plus_branch_materials_only": True,
            "parallel_experiment_reference_allowed": False,
            "graph_event_attribution_required": True,
        },
        "constraint_governance": {
            "raw_observation_is_hard_obligation": False,
            "unresolved_root_is_hard_obligation": False,
            "one_root_one_hard_obligation": True,
            "hard_obligation_budget_lte_candidate_family_effective_dof": True,
            "baseline_is_comparator_not_successor": True,
            "account_equivalent_candidate_is_successor": False,
            "no_admissible_nontrivial_candidate_status": "candidate_family_insufficient",
        },
        "invariants": {
            "calendar_identity_is_runtime_feature": False,
            "rolling_or_offset_material_windows_allowed": False,
            "batch_scientific_judgment_allowed": False,
            "unresolved_root_hard_promotion_allowed": False,
            "baseline_fallback_can_be_new_version": False,
            "whole_policy_rebuild_required": True,
            "complete_candidate_family_repriced": True,
            "no_opportunity_counts_as_pass": False,
            "consumed_lockbox_reuse_allowed": False,
            "parallel_experiment_evidence_reuse_allowed": False,
            "common_root_shared_across_parallel_experiments": True,
            "annual_prior_snapshot_blind_challenge_required": True,
            "annual_whole_policy_rebuild_required": True,
            "final_snapshot_has_fresh_challenge": False,
        },
        "failure_routing": (
            {
                "failure": "session_analysis_incomplete",
                "action": "finish_current_session_ledger_before_opening_next_year",
            },
            {
                "failure": "parallel_branch_contamination",
                "action": "invalidate_branch_and_restart_from_common_root",
            },
            {
                "failure": "unresolved_root_cause",
                "action": "return_to_attribution_change_measurement_or_factor_family",
            },
            {
                "failure": "hard_obligations_exceed_family_capacity",
                "action": "declare_candidate_family_insufficient_and_redesign_bounded_family",
            },
            {
                "failure": "only_baseline_or_account_equivalent_candidate_survives",
                "action": "report_no_incremental_successor_not_a_new_version",
            },
            {
                "failure": "prior_snapshot_fails_next_annual_challenge",
                "action": "convert_year_to_materials_and_rebuild_whole_policy_from_common_root",
            },
        ),
        "current_lockbox_boundary": {
            "start": "2021-01-01",
            "end_exclusive": "2027-01-01",
            "aggregate_lockbox_already_consumed": True,
            "detailed_reuse_for_v7_allowed": False,
            "aggregate_reuse_for_v7_selection_allowed": False,
        },
        "parallel_experiment_contract": {
            "common_root_formula_and_raw_carriers_may_be_shared": True,
            "sibling_policy_or_material_may_be_shared": False,
            "sibling_candidate_or_parameter_may_be_shared": False,
            "sibling_result_or_conclusion_may_be_shared": False,
            "source_allowlist_and_denylist_required": True,
            "contaminated_branch_must_restart": True,
        },
        "source_refs": list(SOURCE_REFS),
        "research_authority": True,
        "parameter_authority": False,
        "routing_authority": False,
        "architecture_lock_authority": False,
        "production_authority": False,
    }
    payload["semantic_digest"] = canonical_digest(payload)
    return payload


def validate_strategy_slice_rebuild_contract(payload: dict[str, object]) -> None:
    """Fail closed when annual-session or constraint-governance semantics drift."""

    if payload.get("schema_id") != SCHEMA_ID or payload.get("code_version") != CODE_VERSION:
        raise ValidationError("annual-session strategy workflow identity drifted")
    if payload.get("canonical_slices") != [asdict(item) for item in canonical_pre2021_annual_sessions()]:
        raise ValidationError("canonical annual-session atlas drifted")
    protocol = cast(dict[str, object], payload.get("session_protocol"))
    if not isinstance(protocol, dict) or protocol != {
        "session_count": 12,
        "rolling_or_offset_windows_allowed": False,
        "one_year_per_session": True,
        "single_year_evidence_invocation_only": True,
        "shell_loop_or_batch_driver_allowed": False,
        "evidence_preparation_may_be_automated": True,
        "interpretation_or_promotion_may_be_automated": False,
        "batch_session_completion_allowed": False,
        "manual_analysis_ledger_required": True,
        "manual_constraint_review_required": True,
        "main_researcher_signoff_required": True,
        "next_session_requires_prior_receipt_digest": True,
        "next_session_requires_prior_policy_digest": True,
        "blind_backtest_candidate_ranking_allowed": False,
        "post_attribution_bounded_rebuild_allowed": True,
        "whole_policy_rebuild_every_session_required": True,
        "incremental_patch_from_prior_winner_allowed": False,
        "common_root_plus_branch_materials_only": True,
        "parallel_experiment_reference_allowed": False,
        "graph_event_attribution_required": True,
    }:
        raise ValidationError("annual research session protocol drifted")
    constraints = cast(dict[str, object], payload.get("constraint_governance"))
    if not isinstance(constraints, dict) or any(
        constraints.get(key) is not expected
        for key, expected in {
            "raw_observation_is_hard_obligation": False,
            "unresolved_root_is_hard_obligation": False,
            "one_root_one_hard_obligation": True,
            "hard_obligation_budget_lte_candidate_family_effective_dof": True,
            "baseline_is_comparator_not_successor": True,
            "account_equivalent_candidate_is_successor": False,
        }.items()
    ):
        raise ValidationError("constraint-promotion governance drifted")
    invariants = cast(dict[str, object], payload.get("invariants"))
    if not isinstance(invariants, dict):
        raise ValidationError("annual-session invariants are missing")
    required_false = {
        "calendar_identity_is_runtime_feature",
        "rolling_or_offset_material_windows_allowed",
        "batch_scientific_judgment_allowed",
        "unresolved_root_hard_promotion_allowed",
        "baseline_fallback_can_be_new_version",
        "no_opportunity_counts_as_pass",
        "consumed_lockbox_reuse_allowed",
        "parallel_experiment_evidence_reuse_allowed",
    }
    required_true = {
        "whole_policy_rebuild_required",
        "complete_candidate_family_repriced",
        "common_root_shared_across_parallel_experiments",
        "annual_prior_snapshot_blind_challenge_required",
        "annual_whole_policy_rebuild_required",
    }
    if any(invariants.get(key) is not False for key in required_false):
        raise ValidationError("a forbidden annual-session behavior was enabled")
    if any(invariants.get(key) is not True for key in required_true):
        raise ValidationError("a required whole-policy behavior was disabled")
    if invariants.get("final_snapshot_has_fresh_challenge") is not False:
        raise ValidationError("the final retrospective snapshot cannot claim a fresh challenge")
    parallel = cast(dict[str, object], payload.get("parallel_experiment_contract"))
    if not isinstance(parallel, dict) or parallel != {
        "common_root_formula_and_raw_carriers_may_be_shared": True,
        "sibling_policy_or_material_may_be_shared": False,
        "sibling_candidate_or_parameter_may_be_shared": False,
        "sibling_result_or_conclusion_may_be_shared": False,
        "source_allowlist_and_denylist_required": True,
        "contaminated_branch_must_restart": True,
    }:
        raise ValidationError("parallel experiment isolation contract drifted")
    lockbox = cast(dict[str, object], payload.get("current_lockbox_boundary"))
    if not isinstance(lockbox, dict) or (
        lockbox.get("aggregate_lockbox_already_consumed") is not True
        or lockbox.get("detailed_reuse_for_v7_allowed") is not False
        or lockbox.get("aggregate_reuse_for_v7_selection_allowed") is not False
    ):
        raise ValidationError("the consumed post-2020 lockbox was reopened for the isolated branch")
    if payload.get("source_refs") != list(SOURCE_REFS):
        raise ValidationError("annual-session source inventory drifted")
    if any(
        payload.get(key) is not False
        for key in (
            "parameter_authority",
            "routing_authority",
            "architecture_lock_authority",
            "production_authority",
        )
    ):
        raise ValidationError("retrospective infrastructure granted excessive authority")


__all__ = [
    "AnnualResearchSessionReceipt",
    "AnnualSliceSpec",
    "BranchIsolationDeclaration",
    "CODE_VERSION",
    "HardObligation",
    "RootCauseHypothesis",
    "SCHEMA_ID",
    "SOURCE_REFS",
    "SuccessorDecision",
    "build_strategy_slice_rebuild_contract",
    "canonical_pre2021_annual_sessions",
    "validate_annual_research_sessions",
    "validate_annual_slice_atlas",
    "validate_hard_obligation_promotions",
    "validate_strategy_slice_rebuild_contract",
]
