# pyright: reportAny=false, reportArgumentType=false
# pyright: reportImplicitStringConcatenation=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnusedCallResult=false
"""Unified timing-factor catalog (three-layer ontology).

This module is a thin catalog/orchestration layer.  It does NOT recompute any
formula: the six-axis public state lives in :mod:`timing_six_axis`, the
13-tool formula-mechanism-factor mapping lives in
:mod:`tool_formula_mechanisms`, and the current 14-tool identity lives in
:mod:`tool_registry_v1_4`.  Here we only fold those authorities into a single
machine-readable catalog and give every factor an explicit *completeness
outcome* so downstream consumers never face a silent gap.

The catalog is organised in three layers (plan section 3.1):

* ``common_market_state`` -- the six headline axes and their multi-scale
  components/term-structure; headline is a monitoring projection, never a
  sufficient statistic for any tool's tuning.
* ``tool_relative_coupling`` -- dimensionless matching quantities that bridge
  public state to a specific tool's internal decision variable.  These reuse
  the existing 34 factors (21 mapped existing attributes + 13 proposed
  formula-native measurements) and the 11 mechanisms / 43 mapping edges.
* ``execution_constraint`` -- cost, execution lag, minimum holding and T+1 /
  next-bar execution constraints.

Frozen boundaries that this module must respect:

* the 13-tool R2F prefix and its frozen evidence are immutable; the 14th tool
  ``paper_kernel_multiscale_trend_router`` is an append-only extension;
* ``path_efficiency_wN == abs(direction_wbi_wN)`` is an exact alias and the
  same-root ACF/VR/Hurst/BDCI family must never be counted as independent
  votes;
* factor *materialization* and factor *effectiveness* are strictly separated:
  a materialized series grants neither routing nor production authority.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import cast

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.timing_six_axis import (
    AXIS_IDS,
    build_axis_catalog,
    build_information_topology,
)
from factor_lab.market_state.tool_formula_mechanisms import (
    factor_formula_mappings,
    mechanism_specs,
    proposed_factor_specs,
)
from factor_lab.market_state.tool_mechanism_features import PROPOSED_FACTOR_IDS
from factor_lab.market_state.tool_registry import DISCOVERED_TOOL_IDS
from factor_lab.market_state.tool_registry_v1_4 import CURRENT_TOOL_IDS

CATALOG_SCHEMA_ID = "market_state_timing_factor_catalog@1.0"
CATALOG_VERSION = "timing_factor_catalog_v1"
COUPLING_SCHEMA_ID = "market_state_tool_factor_coupling@1.0"
COUPLING_VERSION = "tool_factor_coupling_v1"

# Three information layers (plan section 3.1).  Order is stable for deterministic
# serialization.
FACTOR_LAYERS = ("common_market_state", "tool_relative_coupling", "execution_constraint")

# Completeness outcomes (plan section 3.3).  Every catalog entry must end with
# one of these machine-readable outcomes -- "complete" means "has an outcome",
# NOT "validated effective".
COMPLETENESS_OUTCOMES = (
    "defined",  # formula + semantics complete
    "materializable",  # inputs available, strictly-causal computable, not yet run
    "materialized",  # timeseries + quality receipt exist
    "blocked_missing_input",  # cannot compute: upstream input missing
    "research_supported",  # empirical evidence supports (still no authority)
    "research_rejected",  # empirical evidence rejects
    "research_unknown",  # no empirical verdict
)

# Evidence-status vocabulary (kept distinct from materialization outcome).
EVIDENCE_STATUSES = (
    "research_supported",
    "research_rejected",
    "research_unknown",
)

# Authority gradients.  All default to False this round (plan section 5).
AUTHORITY_FLAGS = (
    "signal_authority",
    "routing_authority",
    "dynamic_parameter_authority",
    "production_authority",
)

# Topology relation types.  These must be EXPLICIT: a low correlation may never
# be auto-promoted to "orthogonal" (plan section 3.3 / step 2.3).
TOPOLOGY_RELATIONS = (
    "exact_alias",  # algebraically identical information
    "same_root_projection",  # same statistical root, may corroborate but not double-vote
    "conditional_orthogonal",  # orthogonal only under stated conditioning
    "unknown_relation",  # relation not yet characterised
)

# Carrier frequencies recognised across the catalog.
CARRIER_FREQUENCIES = ("1d", "60m", "15m")

# The same black-box exclusion inherited from the frozen subsystems.
BLACKBOX_EXCLUSION = ("2021-01-01", "2026-12-31")


@dataclass(frozen=True, slots=True)
class FactorCatalogEntry:
    """One row of the unified factor catalog."""

    factor_id: str
    factor_layer: str
    name_zh: str
    name_en: str
    physical_question: str
    causal_formula: str
    unit: str
    factor_version: str
    carrier_frequency: tuple[str, ...]
    scale: tuple[str, ...]
    available_at: str
    strictly_causal: bool
    completeness_outcome: str
    materialization_status: str
    evidence_status: str
    proxy_family_id: str | None
    applicable_mechanism_ids: tuple[str, ...]
    applicable_tool_ids: tuple[str, ...]
    applicable_parameter_axes: tuple[str, ...]
    denominator_zero_strategy: str
    warmup: str
    missing_semantics: str
    topology_relation: str
    aliases: tuple[str, ...]
    source_module: str
    authority: MappingProxyType[str, bool]
    field_labels_zh: MappingProxyType[str, str]

    def __post_init__(self) -> None:
        if self.factor_layer not in FACTOR_LAYERS:
            raise ValidationError(
                f"factor_layer must be one of {FACTOR_LAYERS}"
            )
        if self.completeness_outcome not in COMPLETENESS_OUTCOMES:
            raise ValidationError(
                f"completeness_outcome must be one of {COMPLETENESS_OUTCOMES}"
            )
        if self.materialization_status not in {
            "defined",
            "materializable",
            "materialized",
            "blocked_missing_input",
        }:
            raise ValidationError(
                "materialization_status must be one of "
                "defined/materializable/materialized/blocked_missing_input"
            )
        if self.evidence_status not in EVIDENCE_STATUSES:
            raise ValidationError(
                f"evidence_status must be one of {EVIDENCE_STATUSES}"
            )
        if self.topology_relation not in TOPOLOGY_RELATIONS:
            raise ValidationError(
                f"topology_relation must be one of {TOPOLOGY_RELATIONS}"
            )
        for flag in AUTHORITY_FLAGS:
            if self.authority.get(flag, True) is not False:
                raise ValidationError(
                    f"authority flag {flag} must be False this round"
                )

    def to_dict(self) -> dict[str, object]:
        return {
            "factor_id": self.factor_id,
            "factor_layer": self.factor_layer,
            "name_zh": self.name_zh,
            "name_en": self.name_en,
            "physical_question": self.physical_question,
            "causal_formula": self.causal_formula,
            "unit": self.unit,
            "factor_version": self.factor_version,
            "carrier_frequency": list(self.carrier_frequency),
            "scale": list(self.scale),
            "available_at": self.available_at,
            "strictly_causal": self.strictly_causal,
            "completeness_outcome": self.completeness_outcome,
            "materialization_status": self.materialization_status,
            "evidence_status": self.evidence_status,
            "proxy_family_id": self.proxy_family_id,
            "applicable_mechanism_ids": list(self.applicable_mechanism_ids),
            "applicable_tool_ids": list(self.applicable_tool_ids),
            "applicable_parameter_axes": list(self.applicable_parameter_axes),
            "denominator_zero_strategy": self.denominator_zero_strategy,
            "warmup": self.warmup,
            "missing_semantics": self.missing_semantics,
            "topology_relation": self.topology_relation,
            "aliases": list(self.aliases),
            "source_module": self.source_module,
            "authority": dict(self.authority),
            "field_labels_zh": dict(self.field_labels_zh),
        }


def _false_authority() -> MappingProxyType[str, bool]:
    return MappingProxyType({flag: False for flag in AUTHORITY_FLAGS})


def _field_labels_zh(**extra: str) -> MappingProxyType[str, str]:
    base: dict[str, str] = {
        "factor_id": "因子身份",
        "factor_layer": "因子层级",
        "name_zh": "中文名",
        "name_en": "英文名",
        "physical_question": "物理问题",
        "causal_formula": "因果公式",
        "unit": "单位",
        "factor_version": "因子版本",
        "carrier_frequency": "载体频率",
        "scale": "尺度",
        "available_at": "可用时点",
        "strictly_causal": "严格因果",
        "completeness_outcome": "完整性结局",
        "materialization_status": "物化状态",
        "evidence_status": "证据状态",
        "proxy_family_id": "同根代理家族",
        "applicable_mechanism_ids": "适用机制",
        "applicable_tool_ids": "适用工具",
        "applicable_parameter_axes": "适用参数轴",
        "denominator_zero_strategy": "分母为零策略",
        "warmup": "预热期",
        "missing_semantics": "缺失语义",
        "topology_relation": "拓扑关系",
        "aliases": "别名",
        "source_module": "来源模块",
        "authority": "权限",
    }
    base.update(extra)
    return MappingProxyType(base)


def _six_axis_common_state_entries() -> list[FactorCatalogEntry]:
    """Fold the six-axis headline + multi-scale components into the common layer."""

    axis_catalog = build_axis_catalog()
    entries: list[FactorCatalogEntry] = []
    for axis in axis_catalog:
        axis_id = str(axis["axis_id"])
        components = cast(list[str], axis.get("components", []))
        entries.append(
            FactorCatalogEntry(
                factor_id=f"common_axis:{axis_id}:headline",
                factor_layer="common_market_state",
                name_zh=f"{axis['label_zh']}标题投影",
                name_en=f"{axis_id}_headline",
                physical_question=str(axis["question"]),
                causal_formula="trailing-only rolling projection; headline only",
                unit="dimensionless_or_signed",
                factor_version="six_axis_headline_v1",
                carrier_frequency=("1d",),
                scale=("headline",),
                available_at="same close not actionable; next trading day decision eligible",
                strictly_causal=True,
                completeness_outcome="materialized",
                materialization_status="materialized",
                evidence_status="research_unknown",
                proxy_family_id=None,
                applicable_mechanism_ids=(),
                applicable_tool_ids=tuple(CURRENT_TOOL_IDS),
                applicable_parameter_axes=(),
                denominator_zero_strategy="not_applicable",
                warmup="longest rolling window used by the axis",
                missing_semantics=(
                    "cross_sectional_coherence stays NaN when group input absent; "
                    "never imputed from the index itself"
                ),
                topology_relation="same_root_projection",
                aliases=tuple(components),
                source_module="factor_lab.market_state.timing_six_axis",
                authority=_false_authority(),
                field_labels_zh=_field_labels_zh(),
            )
        )
        # Register the multi-scale components as materializable monitoring
        # rows.  They are NOT sufficient statistics for any tool's tuning.
        if components:
            entries.append(
                FactorCatalogEntry(
                    factor_id=f"common_axis:{axis_id}:multiscale_components",
                    factor_layer="common_market_state",
                    name_zh=f"{axis['label_zh']}多尺度分量/期限结构",
                    name_en=f"{axis_id}_multiscale_components",
                    physical_question=(
                        "尺度期限结构，供下游读取；标题只是监控投影，"
                        "不是任意工具调参的充分统计量"
                    ),
                    causal_formula="trailing-only multi-scale rolling statistics",
                    unit="dimensionless_or_signed",
                    factor_version="six_axis_multiscale_v1",
                    carrier_frequency=("1d",),
                    scale=tuple(components),
                    available_at="same close not actionable; next trading day decision eligible",
                    strictly_causal=True,
                    completeness_outcome="materialized",
                    materialization_status="materialized",
                    evidence_status="research_unknown",
                    proxy_family_id=None,
                    applicable_mechanism_ids=(),
                    applicable_tool_ids=tuple(CURRENT_TOOL_IDS),
                    applicable_parameter_axes=(),
                    denominator_zero_strategy="not_applicable",
                    warmup="longest rolling window among the components",
                    missing_semantics=(
                        "multi-scale components are monitoring inputs, not "
                        "auto-tuning statistics"
                    ),
                    topology_relation="same_root_projection",
                    aliases=(),
                    source_module="factor_lab.market_state.timing_six_axis",
                    authority=_false_authority(),
                    field_labels_zh=_field_labels_zh(),
                )
            )
    return entries


def _existing_factor_entries(
    mappings: list[dict[str, object]],
    mechanism_index: dict[str, dict[str, object]],
) -> dict[str, FactorCatalogEntry]:
    """Register the 21 existing attributes referenced as mapping edges.

    These are the public-market-state / tool-coupling attributes already in the
    frozen attribute ledger.  We register them by ``factor_id`` (the existing
    attribute id) and attach the consuming mechanisms + tools.
    """

    by_factor: dict[str, FactorCatalogEntry] = {}
    for mapping in mappings:
        if mapping.get("factor_status") != "existing":
            continue
        factor_id = str(mapping["factor_id"])
        mechanism_id = str(mapping["mechanism_id"])
        mechanism = mechanism_index[mechanism_id]
        tools = tuple(cast(list[str], mechanism.get("applicable_tool_ids", [])))
        relation = str(mapping.get("relation_to_driver", "unknown_relation"))
        proxy_family = mapping.get("proxy_family_id")
        entry = by_factor.get(factor_id)
        if entry is None:
            by_factor[factor_id] = FactorCatalogEntry(
                factor_id=f"coupling_existing:{factor_id}",
                factor_layer="tool_relative_coupling",
                name_zh=factor_id,
                name_en=factor_id,
                physical_question=str(mapping.get("rationale", "")),
                causal_formula="frozen attribute ledger measurement",
                unit="dimensionless_or_signed",
                factor_version="existing_attribute_v1",
                carrier_frequency=("1d", "60m", "15m"),
                scale=("fast_20d", "medium_60d"),
                available_at="same close not actionable; next trading day decision eligible",
                strictly_causal=True,
                completeness_outcome="materialized",
                materialization_status="materialized",
                evidence_status="research_unknown",
                proxy_family_id=str(proxy_family) if proxy_family else None,
                applicable_mechanism_ids=(mechanism_id,),
                applicable_tool_ids=tools,
                applicable_parameter_axes=(),
                denominator_zero_strategy="not_applicable",
                warmup="attribute ledger warmup",
                missing_semantics="stays NaN when upstream bar/state input missing",
                topology_relation=relation if relation in TOPOLOGY_RELATIONS else "unknown_relation",
                aliases=(),
                source_module="factor_lab.market_state.attributes_v1",
                authority=_false_authority(),
                field_labels_zh=_field_labels_zh(),
            )
        else:
            # merge mechanism + tool coverage
            merged_mechs = tuple(
                sorted({*entry.applicable_mechanism_ids, mechanism_id})
            )
            merged_tools = tuple(
                sorted({*entry.applicable_tool_ids, *tools})
            )
            by_factor[factor_id] = replace(
                entry,
                applicable_mechanism_ids=merged_mechs,
                applicable_tool_ids=merged_tools,
            )
    return by_factor


def _proposed_factor_entries(
    proposed: list[dict[str, object]],
    mechanism_index: dict[str, dict[str, object]],
) -> list[FactorCatalogEntry]:
    """Register the 13 missing formula-native measurements with explicit outcomes.

    Materialization outcomes follow plan step 4.2: factors computable from
    existing OHLC / cross-section / tool-internal state with strict causality
    are ``materializable``; the rest are ``blocked_missing_input``.  All stay
    ``proposed`` (inclusion_authority False) and ``research_unknown``.
    """

    # The materialization module (tool_mechanism_features.build_proposed_factor_matrix)
    # computes these 13 from causal bar data pre-2021, so they are materializable
    # when bounded input is supplied.  None are blocked this round.
    entries: list[FactorCatalogEntry] = []
    for spec in proposed:
        factor_id = str(spec["factor_id"])
        mechanism_ids = tuple(cast(list[str], spec.get("source_mechanism_ids", [])))
        tools: tuple[str, ...] = ()
        for mechanism_id in mechanism_ids:
            mechanism = mechanism_index.get(mechanism_id)
            if mechanism is not None:
                tools = tuple(
                    sorted(
                        {
                            *tools,
                            *cast(list[str], mechanism.get("applicable_tool_ids", [])),
                        }
                    )
                )
        entries.append(
            FactorCatalogEntry(
                factor_id=f"coupling_proposed:{factor_id}",
                factor_layer="tool_relative_coupling",
                name_zh=str(spec["name_zh"]),
                name_en=factor_id,
                physical_question=(
                    "工具公式专属耦合量：将公共市场状态与工具内部决策量联系"
                ),
                causal_formula=str(spec["causal_formula"]),
                unit="dimensionless",
                factor_version="proposed_factor_v1",
                # The unified package currently materializes this proposed
                # contract on the daily carrier only.  Intraday variants must
                # be registered separately after they have their own receipts.
                carrier_frequency=("1d",),
                scale=("fast_20d", "medium_60d"),
                available_at=(
                    "same close not actionable; next trading day decision eligible"
                ),
                strictly_causal=True,
                # Plan step 4.2: all 13 are materializable from existing causal
                # bar data.  None are fabricated; none are forced to "validated".
                completeness_outcome="materializable",
                materialization_status="materializable",
                evidence_status="research_unknown",
                proxy_family_id=str(spec.get("proxy_family_id")) or None,
                applicable_mechanism_ids=mechanism_ids,
                applicable_tool_ids=tools,
                applicable_parameter_axes=(),
                denominator_zero_strategy=(
                    "return NaN; fail-closed, never zero-fill"
                ),
                warmup=str(spec.get("required_history", "tool-dependent warmup")),
                missing_semantics=(
                    "fail-closed NaN when causal bar history is shorter than warmup"
                ),
                topology_relation="unknown_relation",
                aliases=(),
                source_module=(
                    "factor_lab.market_state.tool_mechanism_features "
                    "(build_proposed_factor_matrix)"
                ),
                authority=_false_authority(),
                field_labels_zh=_field_labels_zh(),
            )
        )
    return entries


def _execution_constraint_entries() -> list[FactorCatalogEntry]:
    """Register the execution-constraint layer (cost / lag / min-hold / T+1)."""

    constraints = [
        (
            "execution:transaction_cost_bps",
            "交易成本（基点）",
            "per-turnover transaction cost in basis points used by benchmarks",
            "switch_cost_burden mechanism cost term",
            "bps",
            tuple(CURRENT_TOOL_IDS),
        ),
        (
            "execution:lag_bars",
            "执行延迟（棒数）",
            "decision-at-close, execute-next-bar lag in bars",
            "delay_duration_tradeoff execution term",
            "bars",
            tuple(CURRENT_TOOL_IDS),
        ),
        (
            "execution:minimum_holding",
            "最短持有约束",
            "minimum holding period before a reversal is allowed",
            "switch_cost_burden holding term",
            "bars",
            tuple(CURRENT_TOOL_IDS),
        ),
        (
            "execution:t1_next_bar_only",
            "T+1 下一棒执行约束",
            "positions only change on the bar after the decision bar",
            "execution lag constraint",
            "boolean",
            tuple(CURRENT_TOOL_IDS),
        ),
    ]
    entries: list[FactorCatalogEntry] = []
    for factor_id, name_zh, question, formula, unit, tools in constraints:
        entries.append(
            FactorCatalogEntry(
                factor_id=factor_id,
                factor_layer="execution_constraint",
                name_zh=name_zh,
                name_en=factor_id.split(":", 1)[1],
                physical_question=question,
                causal_formula=formula,
                unit=unit,
                factor_version="execution_constraint_v1",
                carrier_frequency=("1d", "60m", "15m"),
                scale=("execution",),
                available_at="decision-eligible only after the decision bar closes",
                strictly_causal=True,
                completeness_outcome="defined",
                materialization_status="defined",
                evidence_status="research_unknown",
                proxy_family_id=None,
                applicable_mechanism_ids=("switch_cost_burden",),
                applicable_tool_ids=tools,
                applicable_parameter_axes=(),
                denominator_zero_strategy="not_applicable",
                warmup="0 bars; constraint applies from first decision bar",
                missing_semantics="constraint is always defined; no missing state",
                topology_relation="unknown_relation",
                aliases=(),
                source_module="factor_lab.market_state.tool_registry",
                authority=_false_authority(),
                field_labels_zh=_field_labels_zh(),
            )
        )
    return entries


def build_timing_factor_catalog() -> dict[str, object]:
    """Assemble the unified three-layer factor catalog.

    Returns a deterministic, canonical-digest-signed payload.  The catalog
    reuses (does not copy) the frozen authorities; the digest makes any drift
    detectable.
    """

    six_axis_entries = _six_axis_common_state_entries()
    mechanisms = list(mechanism_specs())
    mechanism_index = {
        str(item["mechanism_id"]): item for item in (m.to_dict() for m in mechanisms)
    }
    mappings = [m.to_dict() for m in factor_formula_mappings()]
    proposed = [p.to_dict() for p in proposed_factor_specs()]
    existing = _existing_factor_entries(mappings, mechanism_index)
    proposed_entries = _proposed_factor_entries(proposed, mechanism_index)
    execution_entries = _execution_constraint_entries()

    all_entries: list[dict[str, object]] = []
    # Stable layer order: common -> coupling -> execution
    all_entries.extend(entry.to_dict() for entry in six_axis_entries)
    all_entries.extend(entry.to_dict() for entry in existing.values())
    all_entries.extend(entry.to_dict() for entry in proposed_entries)
    all_entries.extend(entry.to_dict() for entry in execution_entries)

    # Validate uniqueness + completeness invariants before signing.
    ids = [str(entry["factor_id"]) for entry in all_entries]
    duplicates = [factor_id for factor_id, count in Counter(ids).items() if count > 1]
    if duplicates:
        raise ValidationError(f"duplicate factor ids in catalog: {duplicates}")

    # Every proposed factor id must appear exactly once.
    proposed_in_catalog = {
        entry_id
        for entry_id in ids
        if entry_id.startswith("coupling_proposed:")
    }
    missing_proposed = {
        f"coupling_proposed:{factor_id}" for factor_id in PROPOSED_FACTOR_IDS
    } - proposed_in_catalog
    if missing_proposed:
        raise ValidationError(
            f"catalog is missing proposed factors: {sorted(missing_proposed)}"
        )

    layer_counts = {
        layer: sum(1 for entry in all_entries if entry["factor_layer"] == layer)
        for layer in FACTOR_LAYERS
    }

    payload: dict[str, object] = {
        "schema_id": CATALOG_SCHEMA_ID,
        "registry_version": CATALOG_VERSION,
        "method": "unified_catalog_reuse_not_copy",
        "factor_layers": list(FACTOR_LAYERS),
        "completeness_outcomes": list(COMPLETENESS_OUTCOMES),
        "evidence_statuses": list(EVIDENCE_STATUSES),
        "topology_relations": list(TOPOLOGY_RELATIONS),
        "authority_flags": list(AUTHORITY_FLAGS),
        "carrier_frequencies": list(CARRIER_FREQUENCIES),
        "blackbox_exclusion": list(BLACKBOX_EXCLUSION),
        "market_data_rows_read": 0,
        "research_executed": False,
        "current_tool_ids": list(CURRENT_TOOL_IDS),
        "discovered_tool_ids_prefix": list(DISCOVERED_TOOL_IDS),
        "paper_kernel_tool_id": "paper_kernel_multiscale_trend_router",
        "extension_policy": "branch_from_v1_2_append_paper_kernel_only",
        "factor_count": len(all_entries),
        "layer_counts": layer_counts,
        "proposed_factor_count": len(proposed_entries),
        "existing_mapped_factor_count": len(existing),
        "common_axis_headline_count": len(AXIS_IDS),
        "factors": all_entries,
        "field_labels_zh": dict(_field_labels_zh()),
        "signal_authority": False,
        "routing_authority": False,
        "dynamic_parameter_authority": False,
        "production_authority": False,
    }
    payload["semantic_digest"] = canonical_digest(payload)
    validate_timing_factor_catalog(payload)
    return payload


def validate_timing_factor_catalog(payload: dict[str, object]) -> None:
    """Fail closed on layer/authority/completeness drift."""

    if payload.get("schema_id") != CATALOG_SCHEMA_ID:
        raise ValidationError("timing factor catalog schema id changed")
    if payload.get("registry_version") != CATALOG_VERSION:
        raise ValidationError("timing factor catalog version changed")
    for flag in AUTHORITY_FLAGS:
        if payload.get(flag) is not False:
            raise ValidationError(f"catalog cannot grant {flag}")
    factors = payload.get("factors")
    if not isinstance(factors, list):
        raise ValidationError("catalog factors must be a list")
    rows = cast(list[dict[str, object]], factors)
    seen_ids: set[str] = set()
    for row in rows:
        factor_id = str(row["factor_id"])
        if factor_id in seen_ids:
            raise ValidationError(f"duplicate factor id: {factor_id}")
        seen_ids.add(factor_id)
        if row["factor_layer"] not in FACTOR_LAYERS:
            raise ValidationError(f"unknown factor layer: {row['factor_layer']}")
        if row["completeness_outcome"] not in COMPLETENESS_OUTCOMES:
            raise ValidationError(
                f"unknown completeness outcome: {row['completeness_outcome']}"
            )
        authority = cast(dict[str, object], row.get("authority", {}))
        for flag in AUTHORITY_FLAGS:
            if authority.get(flag) is not False:
                raise ValidationError(
                    f"factor {factor_id} claims {flag}"
                )
    stored_digest = payload.get("semantic_digest")
    unsigned = dict(payload)
    _ = unsigned.pop("semantic_digest", None)
    if stored_digest != canonical_digest(unsigned):
        raise ValidationError("timing factor catalog semantic digest mismatch")


def build_factor_topology() -> dict[str, object]:
    """Expose exact aliases, same-root families and non-double-vote rules.

    Reuses :func:`timing_six_axis.build_information_topology` and folds in the
    43-edge ``proxy_family_id`` families so the unified topology is the single
    place to check "are these two factors independent?".
    """

    six_axis_topology = build_information_topology()
    mappings = factor_formula_mappings()
    families: dict[str, list[str]] = {}
    for mapping in mappings:
        family = mapping.proxy_family_id
        if family:
            families.setdefault(family, []).append(mapping.factor_id)
    family_members = {
        family: sorted(set(members)) for family, members in families.items()
    }
    return {
        "schema_id": "market_state_unified_factor_topology@1.0",
        "exact_aliases": cast(list[object], six_axis_topology["exact_aliases"]),
        "same_root_projections": cast(
            list[object], six_axis_topology["same_root_projections"]
        ),
        "proxy_families": [
            {
                "family": family,
                "members": members,
                "rule": (
                    "同根代理可互证，禁止当成多个独立因子重复投票"
                ),
            }
            for family, members in sorted(family_members.items())
        ],
        "topology_relations": list(TOPOLOGY_RELATIONS),
        "orthogonality_rule": (
            "相关较低不得自动升格为正交；正交性必须显式登记 exact_alias/"
            "same_root_projection/conditional_orthogonal/unknown_relation"
        ),
        "forbidden_mapping": cast(
            dict[str, object], six_axis_topology["forbidden_mapping"]
        ),
    }


__all__ = [
    "AUTHORITY_FLAGS",
    "BLACKBOX_EXCLUSION",
    "CATALOG_SCHEMA_ID",
    "CATALOG_VERSION",
    "COUPLING_SCHEMA_ID",
    "COUPLING_VERSION",
    "CARRIER_FREQUENCIES",
    "COMPLETENESS_OUTCOMES",
    "EVIDENCE_STATUSES",
    "FACTOR_LAYERS",
    "FactorCatalogEntry",
    "TOPOLOGY_RELATIONS",
    "build_factor_topology",
    "build_timing_factor_catalog",
    "validate_timing_factor_catalog",
]
