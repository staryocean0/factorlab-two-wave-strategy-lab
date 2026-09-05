# pyright: reportAny=false, reportArgumentType=false
# pyright: reportImplicitStringConcatenation=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnusedCallResult=false
"""Tool-factor coupling contracts (14 tools, append-only extension).

This module bridges the unified factor catalog to the 14 current tools.  It
reuses -- never copies -- the frozen 13-tool R2F formula-mechanism-factor
mapping from :mod:`tool_formula_mechanisms` and adds an **append-only**
extension for the 14th tool ``paper_kernel_multiscale_trend_router`` derived
from its strategy prototype contract.

Boundaries enforced here:

* the 13-tool prefix (tool ids, formula ids, mechanism edges, factor mappings)
  is byte-identical to the frozen R2F bundle;
* the 14th tool is a clearly-marked extension; it does **not** mutate the
  frozen prefix and does **not** fabricate historical R2 validation evidence;
* every signal-relevant parameter is labelled ``direct`` /
  ``validity_only`` / ``geometry_only`` / ``cost_only``; only ``direct``
  parameters may enter the current signal's tuning degrees of freedom;
* every authority flag is False.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.tool_formula_mechanisms import (
    SIGNAL_RELEVANCE,
    factor_formula_mappings,
    mechanism_specs,
    tool_formula_specs,
)
from factor_lab.market_state.tool_registry import DISCOVERED_TOOL_IDS
from factor_lab.market_state.tool_registry_v1_4 import (
    CURRENT_TOOL_IDS,
    PAPER_KERNEL_TOOL_ID,
)

COUPLING_SCHEMA_ID = "market_state_tool_factor_coupling@1.0"
COUPLING_VERSION = "tool_factor_coupling_v1"

# Extended signal-relevance vocabulary: the frozen 13-tool bundle uses
# direct/validity_only/geometry_only.  We add cost_only for completeness in the
# unified view (a cost parameter changes turnover but not the bare signal).
SIGNAL_RELEVANCE_EXTENDED = SIGNAL_RELEVANCE + ("cost_only",)


@dataclass(frozen=True, slots=True)
class ToolParameterEffect:
    """One parameter's effect on a tool's current benchmark signal."""

    parameter_id: str
    formula_term: str
    physical_meaning: str
    benchmark_signal_relevance: str
    expected_tradeoff: str

    def __post_init__(self) -> None:
        if self.benchmark_signal_relevance not in SIGNAL_RELEVANCE_EXTENDED:
            raise ValidationError(
                f"benchmark signal relevance is invalid: "
                f"{self.benchmark_signal_relevance}"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "parameter_id": self.parameter_id,
            "formula_term": self.formula_term,
            "physical_meaning": self.physical_meaning,
            "benchmark_signal_relevance": self.benchmark_signal_relevance,
            "expected_tradeoff": self.expected_tradeoff,
        }


@dataclass(frozen=True, slots=True)
class ToolFormulaExtension:
    """Append-only formula contract for a tool not in the frozen 13-tool prefix."""

    tool_id: str
    formula_id: str
    transform_formula: str
    signal_formula: str
    execution_formula: str
    implementation_ref: str
    native_source_refs: tuple[str, ...]
    parameter_effects: tuple[ToolParameterEffect, ...]
    mechanism_ids: tuple[str, ...]
    extension_status: str = "append_only_no_frozen_prefix_mutation"

    def __post_init__(self) -> None:
        if self.tool_id == PAPER_KERNEL_TOOL_ID:
            if self.extension_status != "append_only_no_frozen_prefix_mutation":
                raise ValidationError(
                    "paper-kernel extension must be append-only"
                )
        if self.tool_id in DISCOVERED_TOOL_IDS:
            raise ValidationError(
                "extension must not redefine a frozen 13-tool prefix member"
            )
        if self.tool_id not in CURRENT_TOOL_IDS:
            raise ValidationError(
                f"extension tool {self.tool_id} is not a current 14-tool member"
            )
        parameter_ids = [item.parameter_id for item in self.parameter_effects]
        if len(parameter_ids) != len(set(parameter_ids)):
            raise ValidationError(
                f"duplicate parameter effect for {self.tool_id}"
            )
        if not self.mechanism_ids:
            raise ValidationError(
                f"extension tool {self.tool_id} needs at least one mechanism"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "tool_id": self.tool_id,
            "formula_id": self.formula_id,
            "transform_formula": self.transform_formula,
            "signal_formula": self.signal_formula,
            "execution_formula": self.execution_formula,
            "implementation_ref": self.implementation_ref,
            "native_source_refs": list(self.native_source_refs),
            "parameter_effects": [item.to_dict() for item in self.parameter_effects],
            "mechanism_ids": list(self.mechanism_ids),
            "extension_status": self.extension_status,
        }


def paper_kernel_formula_extension() -> ToolFormulaExtension:
    """Derive the append-only formula contract for the 14th tool.

    The paper-kernel tool is a causal normalized-return EWMA bank with a
    slow/middle/fast hierarchical router.  We trace its real decision path
    (plan step 5): parameters that change the macro boundary / hysteresis /
    rebound thresholds directly change the long-vs-cash signal; ``cost_bps``
    is a cost-only term; ``bars_per_day`` is a geometry/validity term that
    sets the sampling grid without changing the buy/sell sequence semantics.
    """

    return ToolFormulaExtension(
        tool_id=PAPER_KERNEL_TOOL_ID,
        formula_id="paper_kernel_multiscale_trend_router_formula_v1_extension",
        transform_formula=(
            "causal normalized-return EWMA at twelve spans "
            "(paper_span_s in {5,10,15,20,30,60,100,150,200,300,400,500} days); "
            "spans grouped into slow/middle/fast scale banks"
        ),
        signal_formula=(
            "macro router: down=slow<=-macro_boundary and middle<0; "
            "up=slow>=macro_boundary and middle>0; otherwise flat; "
            "macro_up/flat apply fast_direction_hysteresis (|fast|>=fast_hysteresis); "
            "macro_down permits only a separately armed fast rebound "
            "(rebound_oversold_strength / rebound_entry_score / rebound_failure_score)"
        ),
        execution_formula=(
            "decide at the closed bar; execute next bar (single_execution_shift=True)"
        ),
        implementation_ref=(
            "src/factor_lab/strategy/services/"
            "risk_off_paper_kernel_hierarchical_trend_v1.py:"
            "route_paper_kernel_hierarchical_trend_v1"
        ),
        native_source_refs=(
            "src/factor_lab/strategy/services/risk_off_paper_kernel_hierarchical_trend_v1.py",
            "src/factor_lab/strategy/services/risk_off_paper_kernel_native_trend.py",
            "src/factor_lab/cloudridge/paper_kernel.py",
        ),
        parameter_effects=(
            ToolParameterEffect(
                parameter_id="macro_boundary",
                formula_term="slow <= -macro_boundary / slow >= +macro_boundary",
                physical_meaning="macro regime switch threshold on the slow EWMA bank",
                benchmark_signal_relevance="direct",
                expected_tradeoff=(
                    "larger boundary delays regime calls (fewer false switches, "
                    "more lag); smaller boundary is more reactive but noisier"
                ),
            ),
            ToolParameterEffect(
                parameter_id="fast_hysteresis",
                formula_term="|fast_score| >= fast_hysteresis",
                physical_meaning="hysteresis band for the fast-direction router",
                benchmark_signal_relevance="direct",
                expected_tradeoff=(
                    "wider hysteresis suppresses flip noise at the cost of "
                    "entry/exit latency"
                ),
            ),
            ToolParameterEffect(
                parameter_id="rebound_oversold_strength",
                formula_term="fast_score <= -rebound_oversold_strength",
                physical_meaning="oversold strength gating the armed rebound branch",
                benchmark_signal_relevance="direct",
                expected_tradeoff=(
                    "gates whether a macro-down rebound may arm; changes the "
                    "long/cash sequence in macro-down"
                ),
            ),
            ToolParameterEffect(
                parameter_id="rebound_entry_score",
                formula_term="fast_score >= rebound_entry_score",
                physical_meaning="entry score threshold for the armed rebound",
                benchmark_signal_relevance="direct",
                expected_tradeoff=(
                    "raises/lowers the bar for rebound long entry; changes the "
                    "long/cash sequence"
                ),
            ),
            ToolParameterEffect(
                parameter_id="rebound_failure_score",
                formula_term="fast_score <= rebound_failure_score",
                physical_meaning="failure/exit score for the armed rebound",
                benchmark_signal_relevance="direct",
                expected_tradeoff=(
                    "tightens/loosens rebound exit; changes the long/cash sequence"
                ),
            ),
            ToolParameterEffect(
                parameter_id="cost_bps",
                formula_term="turnover * cost_bps / 10000",
                physical_meaning="per-turnover transaction cost in basis points",
                benchmark_signal_relevance="cost_only",
                expected_tradeoff=(
                    "changes net value via turnover cost; does not change the "
                    "bare long/cash decision sequence"
                ),
            ),
            ToolParameterEffect(
                parameter_id="bars_per_day",
                formula_term="span_bars = span_days * bars_per_day; nu = 1-2/(span_bars+1)",
                physical_meaning=(
                    "sampling grid multiplier that scales every EWMA span and "
                    "the volatility span; changes the actual span_bars feeding "
                    "each signal line"
                ),
                benchmark_signal_relevance="direct",
                expected_tradeoff=(
                    "different values change the EWMA decay nu for every signal "
                    "line and the volatility normalization, which changes the "
                    "long/cash decision sequence (verified empirically: bars_per_day "
                    "8 vs 16 diverges on thousands of bars)"
                ),
            ),
        ),
        # Reuse existing mechanisms; do not fabricate symmetry-only mechanisms
        # (plan step 5.3).  The paper-kernel router's primitives are: scale
        # matching (multi-scale EWMA bank), delay vs run-age tradeoff, path
        # noise false-switch (hysteresis), and switch-cost burden.
        mechanism_ids=(
            "spectral_scale_match",
            "delay_duration_tradeoff",
            "path_noise_false_switch",
            "switch_cost_burden",
        ),
    )


def build_tool_factor_coupling() -> dict[str, object]:
    """Assemble the 14-tool -> formula -> parameter -> mechanism -> factor view.

    The 13-tool prefix rows are projections of the frozen R2F bundle (reused,
    not copied).  The 14th tool is the append-only extension.  The result is a
    canonical-digest-signed payload with an explicit extension marker.
    """

    # Frozen 13-tool prefix (reused verbatim).
    frozen_formulas = [spec.to_dict() for spec in tool_formula_specs()]
    extension = paper_kernel_formula_extension()
    extension_dict = extension.to_dict()

    # Build mechanism -> applicable tools index from frozen mechanisms.
    mechanisms = {m.mechanism_id: m for m in mechanism_specs()}
    mechanism_tools = {
        mechanism_id: list(mechanism.applicable_tool_ids)
        for mechanism_id, mechanism in mechanisms.items()
    }
    # The 14th tool reuses existing mechanisms; record its membership without
    # mutating the frozen mechanism->tool applicability sets.
    extension_mechanism_membership = {
        mechanism_id: (mechanism_id in extension.mechanism_ids)
        for mechanism_id in mechanisms
    }

    # Frozen 13-tool factor mappings (reused verbatim).
    mappings = [m.to_dict() for m in factor_formula_mappings()]

    # Per-tool parameter signal-relevance audit (frozen 13 + extension 14).
    parameter_audit: list[dict[str, object]] = []
    for formula in frozen_formulas:
        tool_id = str(formula["tool_id"])
        for effect in cast(list[dict[str, object]], formula["parameter_effects"]):
            parameter_audit.append(
                {
                    "tool_id": tool_id,
                    "parameter_id": str(effect["parameter_id"]),
                    "benchmark_signal_relevance": str(
                        effect["benchmark_signal_relevance"]
                    ),
                    "source": "frozen_r2f_prefix",
                }
            )
    for effect in extension.parameter_effects:
        parameter_audit.append(
            {
                "tool_id": extension.tool_id,
                "parameter_id": effect.parameter_id,
                "benchmark_signal_relevance": effect.benchmark_signal_relevance,
                "source": "append_only_extension",
            }
        )

    direct_parameters = [
        item
        for item in parameter_audit
        if item["benchmark_signal_relevance"] == "direct"
    ]
    inactive_parameters = [
        item
        for item in parameter_audit
        if item["benchmark_signal_relevance"] != "direct"
    ]

    payload: dict[str, object] = {
        "schema_id": COUPLING_SCHEMA_ID,
        "registry_version": COUPLING_VERSION,
        "method": "reuse_frozen_r2f_append_paper_kernel_extension",
        "current_tool_ids": list(CURRENT_TOOL_IDS),
        "discovered_tool_ids_prefix": list(DISCOVERED_TOOL_IDS),
        "paper_kernel_tool_id": PAPER_KERNEL_TOOL_ID,
        "extension_policy": "branch_from_v1_2_append_paper_kernel_only",
        "frozen_prefix_tool_count": len(DISCOVERED_TOOL_IDS),
        "extension_tool_count": 1,
        "total_tool_count": len(CURRENT_TOOL_IDS),
        "frozen_prefix_formula_specs": frozen_formulas,
        "extension_formula_specs": [extension_dict],
        "frozen_prefix_factor_mappings": mappings,
        "frozen_prefix_factor_mapping_count": len(mappings),
        "mechanism_applicable_tools_frozen": mechanism_tools,
        "extension_mechanism_membership": extension_mechanism_membership,
        "parameter_signal_relevance_audit": parameter_audit,
        "direct_parameter_count": len(direct_parameters),
        "inactive_parameter_count": len(inactive_parameters),
        "signal_tuning_candidate_policy": (
            "only benchmark_signal_relevance == 'direct' parameters may enter "
            "the current signal's tuning degrees of freedom"
        ),
        "market_data_rows_read": 0,
        "research_executed": False,
        "blackbox_exclusion": ["2021-01-01", "2026-12-31"],
        "field_labels_zh": {
            "current_tool_ids": "当前十四个工具身份",
            "discovered_tool_ids_prefix": "冻结十三工具前缀",
            "paper_kernel_tool_id": "论文核多尺度趋势路由工具身份",
            "extension_policy": "扩展策略",
            "frozen_prefix_formula_specs": "冻结前缀工具公式",
            "extension_formula_specs": "追加扩展工具公式",
            "frozen_prefix_factor_mappings": "冻结前缀因子映射",
            "mechanism_applicable_tools_frozen": "冻结机制适用工具",
            "extension_mechanism_membership": "扩展工具机制归属",
            "parameter_signal_relevance_audit": "参数信号相关性审计",
            "direct_parameter_count": "直接调参候选数",
            "inactive_parameter_count": "不进入调参数",
            "signal_tuning_candidate_policy": "调参候选策略",
        },
        "signal_authority": False,
        "routing_authority": False,
        "dynamic_parameter_authority": False,
        "production_authority": False,
    }
    payload["semantic_digest"] = canonical_digest(payload)
    validate_tool_factor_coupling(payload)
    return payload


def validate_tool_factor_coupling(payload: dict[str, object]) -> None:
    """Fail closed on prefix mutation, accidental 15th tool, or authority grant."""

    if payload.get("schema_id") != COUPLING_SCHEMA_ID:
        raise ValidationError("tool factor coupling schema id changed")
    if payload.get("registry_version") != COUPLING_VERSION:
        raise ValidationError("tool factor coupling version changed")
    for flag in (
        "signal_authority",
        "routing_authority",
        "dynamic_parameter_authority",
        "production_authority",
    ):
        if payload.get(flag) is not False:
            raise ValidationError(f"coupling cannot grant {flag}")
    frozen_formulas = cast(list[dict[str, object]], payload["frozen_prefix_formula_specs"])
    frozen_tool_ids = tuple(str(item["tool_id"]) for item in frozen_formulas)
    if frozen_tool_ids != DISCOVERED_TOOL_IDS:
        raise ValidationError(
            "frozen 13-tool prefix must be byte-identical to the R2F bundle"
        )
    extensions = cast(list[dict[str, object]], payload["extension_formula_specs"])
    extension_tool_ids = {str(item["tool_id"]) for item in extensions}
    if extension_tool_ids != {PAPER_KERNEL_TOOL_ID}:
        raise ValidationError(
            "extension must contain exactly the paper-kernel tool"
        )
    if "causal_jump_gap_shock" in {*frozen_tool_ids, *extension_tool_ids}:
        raise ValidationError(
            "revoked jump/gap owner cannot enter the current 14-tool view"
        )
    # Frozen prefix must equal the live R2F bundle (guard against silent drift).
    expected_frozen = [spec.to_dict() for spec in tool_formula_specs()]
    if frozen_formulas != expected_frozen:
        raise ValidationError(
            "frozen prefix formula specs drifted from the R2F authority"
        )
    expected_mappings = [m.to_dict() for m in factor_formula_mappings()]
    if cast(list[dict[str, object]], payload["frozen_prefix_factor_mappings"]) != expected_mappings:
        raise ValidationError(
            "frozen prefix factor mappings drifted from the R2F authority"
        )
    audit = cast(list[dict[str, object]], payload["parameter_signal_relevance_audit"])
    for item in audit:
        if item["benchmark_signal_relevance"] not in SIGNAL_RELEVANCE_EXTENDED:
            raise ValidationError(
                f"invalid signal relevance: {item['benchmark_signal_relevance']}"
            )
    stored_digest = payload.get("semantic_digest")
    unsigned = dict(payload)
    _ = unsigned.pop("semantic_digest", None)
    if stored_digest != canonical_digest(unsigned):
        raise ValidationError("tool factor coupling semantic digest mismatch")


__all__ = [
    "COUPLING_SCHEMA_ID",
    "COUPLING_VERSION",
    "SIGNAL_RELEVANCE_EXTENDED",
    "ToolFormulaExtension",
    "ToolParameterEffect",
    "build_tool_factor_coupling",
    "paper_kernel_formula_extension",
    "validate_tool_factor_coupling",
]
