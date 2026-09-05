# pyright: reportImportCycles=false
"""Typed Stage-1 contracts for formula graphs and bounded joint templates."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Literal, cast

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.formula_derivation.validation import (
    attach_semantic_digest,
    require_digest,
    require_exact_keys,
    require_mapping,
    require_sequence,
    require_text,
    validate_semantic_digest,
)


def _empty_object_mapping() -> dict[str, object]:
    return {}


FORMULA_COMPUTATION_GRAPH_SCHEMA_ID: Final[str] = "market_state_formula_computation_graph@1.0"
FORMULA_DERIVATION_PACKAGE_SCHEMA_ID: Final[str] = "market_state_formula_derivation_package@1.0"

EvidenceLevel = Literal[
    "structural_dependency",
    "empirical_association",
    "causal_economic_claim",
]
HeredityRequirement = Literal["none", "weak", "strong"]
FormulaOperator = Literal[
    "input",
    "constant",
    "source_attribute",
    "source_target_position",
    "execution_lag",
    "transaction_cost",
    "add",
    "subtract",
    "multiply",
    "safe_divide",
    "power",
    "feature_as_coefficient",
    "feature_as_exponent",
    "threshold_branch",
    "state_transition",
]

_OPERATORS: Final[frozenset[str]] = frozenset(
    {
        "input",
        "constant",
        "source_attribute",
        "source_target_position",
        "execution_lag",
        "transaction_cost",
        "add",
        "subtract",
        "multiply",
        "safe_divide",
        "power",
        "feature_as_coefficient",
        "feature_as_exponent",
        "threshold_branch",
        "state_transition",
    }
)
_TEMPLATE_OPERATORS: Final[frozenset[str]] = _OPERATORS.difference(
    {
        "input",
        "constant",
        "source_attribute",
        "source_target_position",
        "execution_lag",
        "transaction_cost",
    }
)
_BENCHMARK_PANEL_OPERATORS: Final[frozenset[str]] = frozenset(
    {
        "input",
        "constant",
        "source_attribute",
        "source_target_position",
        "execution_lag",
        "transaction_cost",
    }
)
_HEREDITY: Final[frozenset[str]] = frozenset({"none", "weak", "strong"})
_FORMULA_NODE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "node_id",
        "operator",
        "input_node_ids",
        "kline_field_refs",
        "parameter_refs",
        "unit",
        "availability",
        "warmup_bars",
        "missing_policy",
        "domain_guard",
        "source_witness",
        "evidence_level",
    }
)
_FORMULA_GRAPH_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_id",
        "graph_id",
        "tool_id",
        "tool_version",
        "nodes",
        "output_node_ids",
        "raw_kline_input_fields",
        "source_formula_contract",
        "source_materializer_ref",
        "decision_output_id",
        "execution_lag_bars",
        "cost_parameter_id",
        "market_data_rows_read",
        "return_rows_read",
        "empirical_validation_executed",
        "production_authority",
        "dynamic_parameter_authority",
        "tool_routing_authority",
        "field_labels_zh",
        "semantic_digest",
    }
)
_SOURCE_FORMULA_CONTRACT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "formula_id",
        "tool_id",
        "transform_formula",
        "signal_formula",
        "execution_formula",
        "implementation_ref",
        "native_source_refs",
        "parameter_effects",
        "mechanism_ids",
        "evidence_level",
    }
)
_PARAMETER_EFFECT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "parameter_id",
        "formula_term",
        "physical_meaning",
        "benchmark_signal_relevance",
        "expected_tradeoff",
        "evidence_level",
    }
)
_PARAMETER_CONTRAST_KEYS: Final[frozenset[str]] = frozenset(
    {
        "contrast_id",
        "baseline_profile_id",
        "candidate_profile_id",
        "delta_output_expression",
        "delta_parameter_expression",
        "action_disagreement_predicate",
        "boundary_margin_expression",
        "atomic_contributions",
        "exactness",
    }
)
_PARAMETER_CONTRAST_EXECUTION_KEYS: Final[frozenset[str]] = frozenset(
    {
        "baseline_parameters",
        "candidate_parameters",
        "synthetic_fixture_digest",
        "baseline_output_digest",
        "candidate_output_digest",
        "delta_output_digest",
        "action_disagreement_digest",
        "numeric_reconciliation_digest",
        "output_count",
        "maximum_delta_identity_error",
        "action_disagreement_count",
        "graph_execution_verified",
    }
)
_FORMULA_NATIVE_ATTRIBUTE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "attribute_id",
        "upstream_node_ids",
        "causal_formula",
        "unit",
        "availability",
        "factor_registration_status",
        "factor_spec_id",
        "registration_blocker",
        "evidence_level",
    }
)
_INTERACTION_TEMPLATE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "template_id",
        "atom_attribute_ids",
        "allowed_operators",
        "heredity_requirement",
        "marginal_admission_required",
        "complexity_budget",
        "state_topology",
        "execution_lag_bars",
    }
)
_FORMULA_DERIVATION_PACKAGE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_id",
        "package_id",
        "graph",
        "parameter_contrasts",
        "formula_native_attributes",
        "interaction_state_machine_templates",
        "source_artifact_digests",
        "sealed_interval",
        "readiness_status",
        "market_data_rows_read",
        "return_rows_read",
        "empirical_validation_executed",
        "production_authority",
        "dynamic_parameter_authority",
        "tool_routing_authority",
        "field_labels_zh",
        "semantic_digest",
    }
)

GRAPH_LABELS_ZH: Final[dict[str, str]] = {
    "schema_id": "Schema标识",
    "graph_id": "公式计算图标识",
    "tool_id": "择时工具标识",
    "tool_version": "择时工具版本",
    "nodes": "公式图节点",
    "output_node_ids": "输出节点标识",
    "raw_kline_input_fields": "原始K线输入字段",
    "source_formula_contract": "冻结工具公式合同",
    "source_materializer_ref": "原始K线物化器引用",
    "decision_output_id": "冻结目标仓位输出",
    "execution_lag_bars": "执行滞后K线数",
    "cost_parameter_id": "交易成本参数标识",
    "market_data_rows_read": "读取行情行数",
    "return_rows_read": "读取收益标签行数",
    "empirical_validation_executed": "是否执行实证验证",
    "production_authority": "生产权限",
    "dynamic_parameter_authority": "动态参数权限",
    "tool_routing_authority": "工具路由权限",
    "field_labels_zh": "中文字段标签",
    "semantic_digest": "语义摘要",
    "node_id": "节点标识",
    "operator": "运算符",
    "input_node_ids": "输入节点标识",
    "kline_field_refs": "K线字段引用",
    "parameter_refs": "参数引用",
    "unit": "单位",
    "availability": "可用时点",
    "warmup_bars": "预热K线数",
    "missing_policy": "缺失值政策",
    "domain_guard": "数值域防护",
    "source_witness": "源实现见证",
    "evidence_level": "证据等级",
    "formula_id": "冻结公式标识",
    "transform_formula": "变换公式",
    "signal_formula": "信号公式",
    "execution_formula": "执行公式",
    "implementation_ref": "冻结实现引用",
    "native_source_refs": "原生源引用",
    "parameter_effects": "参数公式效应",
    "mechanism_ids": "机制标识",
    "parameter_id": "参数标识",
    "formula_term": "参数所在公式项",
    "physical_meaning": "参数物理含义",
    "expected_tradeoff": "参数变化的预期权衡",
    "benchmark_signal_relevance": "对基准信号的相关作用",
    "lag_bars": "滞后K线数",
    "formula": "可执行公式",
    "baseline_parameters": "基准参数画像",
    "candidate_parameters": "候选参数画像",
    "synthetic_fixture_digest": "合成验证数据摘要",
    "baseline_output_digest": "基准图输出摘要",
    "candidate_output_digest": "候选图输出摘要",
    "delta_output_digest": "基准与候选数值差分摘要",
    "action_disagreement_digest": "动作分歧向量摘要",
    "numeric_reconciliation_digest": "数值恒等重算绑定摘要",
    "output_count": "参与差分重算的数值输出数",
    "maximum_delta_identity_error": "差分恒等式最大误差",
    "action_disagreement_count": "动作分歧数",
    "graph_execution_verified": "是否已通过计算图数值验证",
}

PACKAGE_LABELS_ZH: Final[dict[str, str]] = {
    "schema_id": "Schema标识",
    "package_id": "公式派生包标识",
    "graph": "公式计算图",
    "parameter_contrasts": "参数对照派生",
    "formula_native_attributes": "公式原生K线属性",
    "interaction_state_machine_templates": "交互与状态机模板",
    "sealed_interval": "封存数据区间",
    "readiness_status": "联合机制识别就绪状态",
    "market_data_rows_read": "读取行情行数",
    "return_rows_read": "读取收益标签行数",
    "empirical_validation_executed": "是否执行实证验证",
    "production_authority": "生产权限",
    "dynamic_parameter_authority": "动态参数权限",
    "tool_routing_authority": "工具路由权限",
    "source_artifact_digests": "上游制品摘要",
    "field_labels_zh": "中文字段标签",
    "semantic_digest": "语义摘要",
    "contrast_id": "参数对照标识",
    "baseline_profile_id": "基准参数画像标识",
    "candidate_profile_id": "候选参数画像标识",
    "delta_output_expression": "输出差分表达式",
    "delta_parameter_expression": "参数差分表达式",
    "action_disagreement_predicate": "动作分歧谓词",
    "boundary_margin_expression": "边界裕度表达式",
    "atomic_contributions": "原子参数贡献",
    "exactness": "推导精确性",
    "baseline_parameters": "基准参数画像",
    "candidate_parameters": "候选参数画像",
    "synthetic_fixture_digest": "合成验证数据摘要",
    "baseline_output_digest": "基准图输出摘要",
    "candidate_output_digest": "候选图输出摘要",
    "delta_output_digest": "基准与候选数值差分摘要",
    "action_disagreement_digest": "动作分歧向量摘要",
    "numeric_reconciliation_digest": "数值恒等重算绑定摘要",
    "output_count": "参与差分重算的数值输出数",
    "maximum_delta_identity_error": "差分恒等式最大误差",
    "action_disagreement_count": "动作分歧数",
    "graph_execution_verified": "是否已通过计算图数值验证",
    "attribute_id": "公式原生属性标识",
    "upstream_node_ids": "上游节点标识",
    "causal_formula": "因果可用公式",
    "unit": "单位",
    "availability": "可用时点",
    "factor_registration_status": "因子注册状态",
    "factor_spec_id": "FactorSpec标识",
    "registration_blocker": "注册阻断理由",
    "evidence_level": "证据等级",
    "template_id": "联合状态模板标识",
    "atom_attribute_ids": "原子属性标识",
    "allowed_operators": "允许运算符",
    "heredity_requirement": "遗传性要求",
    "marginal_admission_required": "是否要求边际先晋级",
    "complexity_budget": "复杂度预算",
    "state_topology": "状态拓扑",
    "execution_lag_bars": "执行滞后K线数",
    "base_factor_universe_query": "内部基础因子池查询",
    "tool_formula_spec": "冻结择时工具公式规格",
    "operator_count": "运算符取值数",
    "coefficient_count": "系数取值数",
    "exponent_count": "指数取值数",
    "branch_count": "分支取值数",
    "threshold_count": "阈值取值数",
    "scale_count": "尺度取值数",
    "state_memory_count": "状态记忆取值数",
    "minimum_abs_denominator": "最小绝对分母",
    "zero_denominator_policy": "零分母处理政策",
    "period_bars": "周期K线数",
    "memory_bars": "记忆K线数",
    "fast_window_bars": "快速窗口K线数",
    "slow_window_bars": "慢速窗口K线数",
    "window_bars": "窗口K线数",
    "windows": "多窗口集合",
    "width_sigma": "通道宽度标准差倍数",
    "rail_sigma": "轨道标准差倍数",
    "q": "滤波品质因子",
    "cost_bps": "交易成本基点",
    "state": "状态定义",
    "branches": "状态分支定义",
    "execution": "执行语义",
    "diagnostic_only": "是否仅作诊断",
}


def _frozen_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType(dict(value))


def _mapping_rows(payload: Mapping[str, object], key: str) -> tuple[Mapping[str, object], ...]:
    rows: list[Mapping[str, object]] = []
    for value in require_sequence(payload, key):
        if not isinstance(value, Mapping):
            raise ValidationError(f"{key} rows must be mappings")
        rows.append(cast(Mapping[str, object], value))
    return tuple(rows)


def _text_sequence(
    payload: Mapping[str, object],
    key: str,
    *,
    unique: bool = False,
) -> tuple[str, ...]:
    values = require_sequence(payload, key)
    if any(not isinstance(value, str) for value in values):
        raise ValidationError(f"{key} must contain strings")
    result = cast(tuple[str, ...], values)
    if unique and len(result) != len(set(result)):
        raise ValidationError(f"{key} must contain unique strings")
    return result


def _validate_string_mapping(payload: Mapping[str, object], *, label: str) -> None:
    if not payload or any(
        not key.strip()
        or not isinstance(value, str)
        or not value.strip()
        for key, value in payload.items()
    ):
        raise ValidationError(f"{label} must contain non-empty string labels")


def _validate_parameter_map(payload: Mapping[str, object], *, label: str) -> None:
    if not payload or any(
        not key.strip()
        or isinstance(value, (dict, list, tuple, set))
        or value is None
        for key, value in payload.items()
    ):
        raise ValidationError(f"{label} must contain scalar parameters")


def _validate_state_topology(payload: Mapping[str, object]) -> None:
    allowed_keys = {
        "state",
        "initial",
        "diagnostic_only",
        "execution",
        "memory_bars",
        "entry_window",
        "exit_window",
        "branches",
        "windows",
    }
    if not payload or not set(payload).issubset(allowed_keys):
        raise ValidationError("interaction state topology fields changed")
    for key in (
        "state",
        "initial",
        "diagnostic_only",
        "entry_window",
        "exit_window",
    ):
        if key in payload and (
            not isinstance(payload[key], str) or not cast(str, payload[key]).strip()
        ):
            raise ValidationError("interaction state topology text is invalid")
    if "execution" in payload and payload["execution"] != "next_bar":
        raise ValidationError("interaction state topology execution changed")
    for key in ("memory_bars", "windows"):
        if key not in payload:
            continue
        values = payload[key]
        if (
            not isinstance(values, list)
            or not values
            or any(
                isinstance(value, bool) or not isinstance(value, int) or value < 1
                for value in cast(list[object], values)
            )
            or len(cast(list[object], values)) != len(set(cast(list[int], values)))
        ):
            raise ValidationError("interaction state topology windows are invalid")
    if "branches" in payload:
        branches = payload["branches"]
        if (
            not isinstance(branches, list)
            or not branches
            or any(
                not isinstance(value, str) or not value.strip()
                for value in cast(list[object], branches)
            )
            or len(cast(list[object], branches))
            != len(set(cast(list[str], branches)))
        ):
            raise ValidationError("interaction state topology branches are invalid")


def _validate_source_witness(payload: Mapping[str, object]) -> None:
    key_sets = (
        frozenset({"formula_id", "implementation_ref"}),
        frozenset({"relative_path", "symbol"}),
    )
    if frozenset(payload) not in key_sets or any(
        not isinstance(value, str) or not value.strip() for value in payload.values()
    ):
        raise ValidationError("formula node source_witness does not match its closed schema")


def _validate_domain_guard(payload: Mapping[str, object]) -> None:
    keys = frozenset(payload)
    if not keys:
        return
    string_key_sets = (
        frozenset({"attribute_id", "causal_formula"}),
        frozenset({"signal_formula"}),
        frozenset({"formula"}),
    )
    if keys in string_key_sets and all(
        isinstance(value, str) and value.strip() for value in payload.values()
    ):
        return
    if keys == frozenset({"lag_bars"}) and payload.get("lag_bars") == 1:
        return
    raise ValidationError("formula node domain_guard does not match its closed schema")


def _validate_source_formula_contract(payload: Mapping[str, object]) -> None:
    if not payload:
        return
    require_exact_keys(
        payload,
        _SOURCE_FORMULA_CONTRACT_KEYS,
        label="source formula contract",
    )
    for contract_field in (
        "formula_id",
        "tool_id",
        "transform_formula",
        "signal_formula",
        "execution_formula",
        "implementation_ref",
    ):
        _ = require_text(payload, contract_field)
    if payload.get("evidence_level") != "implementation_identity":
        raise ValidationError("source formula contract evidence level changed")
    for reference_field in ("native_source_refs", "mechanism_ids"):
        values = _text_sequence(payload, reference_field, unique=True)
        if not values or any(not value.strip() for value in values):
            raise ValidationError(
                f"source formula contract requires {reference_field}"
            )
    effects = _mapping_rows(payload, "parameter_effects")
    if not effects:
        raise ValidationError("source formula contract requires parameter effects")
    for effect in effects:
        require_exact_keys(
            effect,
            _PARAMETER_EFFECT_KEYS,
            label="source formula parameter effect",
        )
        for effect_field in _PARAMETER_EFFECT_KEYS.difference({"evidence_level"}):
            _ = require_text(effect, effect_field)
        if effect.get("evidence_level") != "implementation_identity":
            raise ValidationError("source formula parameter effect evidence level changed")


@dataclass(frozen=True, slots=True)
class FormulaNode:
    """One deterministic formula node with explicit PIT and provenance semantics."""

    node_id: str
    operator: FormulaOperator
    input_node_ids: tuple[str, ...]
    kline_field_refs: tuple[str, ...]
    parameter_refs: tuple[str, ...]
    unit: str
    availability: Literal["after_close", "static"]
    warmup_bars: int
    missing_policy: str
    domain_guard: Mapping[str, object]
    source_witness: Mapping[str, object]
    evidence_level: EvidenceLevel = "structural_dependency"

    def __post_init__(self) -> None:
        if not self.node_id.strip() or self.operator not in _OPERATORS:
            raise ValidationError("formula node identity/operator is invalid")
        if self.evidence_level != "structural_dependency":
            raise ValidationError("Stage-1 formula nodes can claim structural_dependency only")
        if not self.unit.strip():
            raise ValidationError("formula node unit is required")
        if self.availability not in {"after_close", "static"} or self.warmup_bars < 0:
            raise ValidationError("formula node availability/warmup is invalid")
        if not self.missing_policy.strip() or not self.source_witness:
            raise ValidationError("formula node missing policy and source witness are required")
        if self.operator == "input" and not self.kline_field_refs:
            raise ValidationError("input formula node requires a K-line field reference")
        if self.operator == "source_attribute" and not isinstance(self.domain_guard.get("attribute_id"), str):
            raise ValidationError("source_attribute requires an attribute_id")
        if self.operator in {"safe_divide", "power", "feature_as_exponent"} and not self.domain_guard:
            raise ValidationError(f"{self.operator} requires an explicit domain guard")

    def to_dict(self) -> dict[str, object]:
        return {
            "node_id": self.node_id,
            "operator": self.operator,
            "input_node_ids": list(self.input_node_ids),
            "kline_field_refs": list(self.kline_field_refs),
            "parameter_refs": list(self.parameter_refs),
            "unit": self.unit,
            "availability": self.availability,
            "warmup_bars": self.warmup_bars,
            "missing_policy": self.missing_policy,
            "domain_guard": dict(self.domain_guard),
            "source_witness": dict(self.source_witness),
            "evidence_level": self.evidence_level,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> FormulaNode:
        require_exact_keys(payload, _FORMULA_NODE_KEYS, label="formula node")
        operator = require_text(payload, "operator")
        availability = require_text(payload, "availability")
        evidence_level = require_text(payload, "evidence_level")
        warmup = payload.get("warmup_bars")
        if isinstance(warmup, bool) or not isinstance(warmup, int) or warmup < 0:
            raise ValidationError("formula node warmup_bars must be a non-negative integer")
        domain_guard = require_mapping(payload, "domain_guard")
        source_witness = require_mapping(payload, "source_witness")
        _validate_domain_guard(domain_guard)
        _validate_source_witness(source_witness)
        return cls(
            node_id=require_text(payload, "node_id"),
            operator=cast(FormulaOperator, operator),
            input_node_ids=_text_sequence(payload, "input_node_ids"),
            kline_field_refs=_text_sequence(payload, "kline_field_refs"),
            parameter_refs=_text_sequence(payload, "parameter_refs"),
            unit=require_text(payload, "unit"),
            availability=cast(Literal["after_close", "static"], availability),
            warmup_bars=warmup,
            missing_policy=require_text(payload, "missing_policy"),
            domain_guard=_frozen_mapping(domain_guard),
            source_witness=_frozen_mapping(source_witness),
            evidence_level=cast(EvidenceLevel, evidence_level),
        )


@dataclass(frozen=True, slots=True)
class FormulaComputationGraph:
    """A traceable deterministic graph built without market or return rows."""

    graph_id: str
    tool_id: str
    tool_version: str
    nodes: tuple[FormulaNode, ...]
    output_node_ids: tuple[str, ...]
    raw_kline_input_fields: tuple[str, ...] = ()
    source_formula_contract: Mapping[str, object] | None = None
    source_materializer_ref: str = ""
    decision_output_id: str = ""
    execution_lag_bars: int = 1
    cost_parameter_id: str = "cost_bps"
    market_data_rows_read: int = 0
    return_rows_read: int = 0
    empirical_validation_executed: bool = False
    production_authority: bool = False
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False

    def __post_init__(self) -> None:
        if not all(value.strip() for value in (self.graph_id, self.tool_id, self.tool_version)):
            raise ValidationError("formula graph identity is required")
        if not self.nodes or not self.output_node_ids:
            raise ValidationError("formula graph needs nodes and outputs")
        node_ids = [node.node_id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValidationError("formula graph node identities must be unique")
        known: set[str] = set()
        for node in self.nodes:
            if any(parent not in known for parent in node.input_node_ids):
                raise ValidationError("formula graph nodes must be topologically ordered")
            known.add(node.node_id)
        if any(node_id not in known for node_id in self.output_node_ids):
            raise ValidationError("formula graph output is missing")
        if self.tool_version == "v1_benchmark":
            if any(node.operator not in _BENCHMARK_PANEL_OPERATORS for node in self.nodes):
                raise ValidationError(
                    "benchmark graph contains an operator unsupported by its panel executor"
                )
            if self.raw_kline_input_fields != (
                "timestamp",
                "open",
                "high",
                "low",
                "close",
            ):
                raise ValidationError("benchmark graph must bind the complete raw K-line input")
            if not self.source_formula_contract or not self.source_materializer_ref.strip():
                raise ValidationError("benchmark graph lacks its source formula materializer")
            source = self.source_formula_contract
            if source.get("tool_id") != self.tool_id or any(
                not isinstance(source.get(field), str) or not str(source[field]).strip()
                for field in (
                    "transform_formula",
                    "signal_formula",
                    "execution_formula",
                    "implementation_ref",
                )
            ):
                raise ValidationError("benchmark graph source formula contract is incomplete")
            if self.decision_output_id != "target_position":
                raise ValidationError("benchmark graph must expose its frozen target position")
            if self.execution_lag_bars != 1 or self.cost_parameter_id != "cost_bps":
                raise ValidationError("benchmark graph execution/cost contract changed")
            input_fields = {field for node in self.nodes if node.operator == "input" for field in node.kline_field_refs}
            if input_fields != set(self.raw_kline_input_fields) or any(
                field not in self.raw_kline_input_fields for node in self.nodes for field in node.kline_field_refs
            ):
                raise ValidationError("benchmark graph contains a non-raw K-line entry")
            required_path = {
                self.decision_output_id,
                "next_bar_position",
                "transaction_cost",
            }
            if not required_path.issubset(known) or not required_path.issubset(self.output_node_ids):
                raise ValidationError("benchmark graph execution path is not executable")
        if self.market_data_rows_read != 0 or self.return_rows_read != 0 or self.empirical_validation_executed:
            raise ValidationError("Stage-1 formula graph must be zero-data and non-empirical")
        if self.production_authority or self.dynamic_parameter_authority or self.tool_routing_authority:
            raise ValidationError("formula graph cannot grant authority")

    def to_dict(self) -> dict[str, object]:
        return attach_semantic_digest(
            {
                "schema_id": FORMULA_COMPUTATION_GRAPH_SCHEMA_ID,
                "graph_id": self.graph_id,
                "tool_id": self.tool_id,
                "tool_version": self.tool_version,
                "nodes": [node.to_dict() for node in self.nodes],
                "output_node_ids": list(self.output_node_ids),
                "raw_kline_input_fields": list(self.raw_kline_input_fields),
                "source_formula_contract": dict(self.source_formula_contract or {}),
                "source_materializer_ref": self.source_materializer_ref,
                "decision_output_id": self.decision_output_id,
                "execution_lag_bars": self.execution_lag_bars,
                "cost_parameter_id": self.cost_parameter_id,
                "market_data_rows_read": self.market_data_rows_read,
                "return_rows_read": self.return_rows_read,
                "empirical_validation_executed": self.empirical_validation_executed,
                "production_authority": self.production_authority,
                "dynamic_parameter_authority": self.dynamic_parameter_authority,
                "tool_routing_authority": self.tool_routing_authority,
                "field_labels_zh": dict(GRAPH_LABELS_ZH),
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> FormulaComputationGraph:
        require_exact_keys(payload, _FORMULA_GRAPH_KEYS, label="formula computation graph")
        if payload.get("schema_id") != FORMULA_COMPUTATION_GRAPH_SCHEMA_ID:
            raise ValidationError("formula computation graph schema changed")
        validate_semantic_digest(payload)
        labels = require_mapping(payload, "field_labels_zh")
        _validate_string_mapping(labels, label="formula computation graph labels")
        if dict(labels) != GRAPH_LABELS_ZH:
            raise ValidationError("formula computation graph labels changed")
        source_formula_contract = require_mapping(payload, "source_formula_contract")
        _validate_source_formula_contract(source_formula_contract)
        for graph_field in (
            "source_materializer_ref",
            "decision_output_id",
            "cost_parameter_id",
        ):
            if not isinstance(payload.get(graph_field), str):
                raise ValidationError(
                    f"formula computation graph requires string {graph_field}"
                )
        for authority_field in (
            "empirical_validation_executed",
            "production_authority",
            "dynamic_parameter_authority",
            "tool_routing_authority",
        ):
            if payload.get(authority_field) is not False:
                raise ValidationError(
                    f"formula computation graph requires {authority_field}=false"
                )
        execution_lag_bars = _integer(payload, "execution_lag_bars")
        if execution_lag_bars < 0:
            raise ValidationError("formula computation graph execution lag is invalid")
        return cls(
            graph_id=require_text(payload, "graph_id"),
            tool_id=require_text(payload, "tool_id"),
            tool_version=require_text(payload, "tool_version"),
            nodes=tuple(FormulaNode.from_dict(row) for row in _mapping_rows(payload, "nodes")),
            output_node_ids=_text_sequence(payload, "output_node_ids", unique=True),
            raw_kline_input_fields=_text_sequence(
                payload,
                "raw_kline_input_fields",
                unique=True,
            ),
            source_formula_contract=_frozen_mapping(source_formula_contract),
            source_materializer_ref=cast(str, payload["source_materializer_ref"]),
            decision_output_id=cast(str, payload["decision_output_id"]),
            execution_lag_bars=execution_lag_bars,
            cost_parameter_id=cast(str, payload["cost_parameter_id"]),
            market_data_rows_read=_integer(payload, "market_data_rows_read"),
            return_rows_read=_integer(payload, "return_rows_read"),
            empirical_validation_executed=False,
            production_authority=False,
            dynamic_parameter_authority=False,
            tool_routing_authority=False,
        )


@dataclass(frozen=True, slots=True)
class ParameterContrastDerivation:
    """A formula-level contrast between two frozen parameter profiles."""

    contrast_id: str
    baseline_profile_id: str
    candidate_profile_id: str
    delta_output_expression: str
    delta_parameter_expression: str
    action_disagreement_predicate: str
    boundary_margin_expression: str
    atomic_contributions: Mapping[str, str]
    exactness: Literal["symbolic_exact", "deterministic_numeric"]
    baseline_parameters: Mapping[str, object] = field(default_factory=_empty_object_mapping)
    candidate_parameters: Mapping[str, object] = field(default_factory=_empty_object_mapping)
    synthetic_fixture_digest: str = ""
    baseline_output_digest: str = ""
    candidate_output_digest: str = ""
    delta_output_digest: str = ""
    action_disagreement_digest: str = ""
    numeric_reconciliation_digest: str = ""
    output_count: int = 0
    maximum_delta_identity_error: float = 0.0
    action_disagreement_count: int = 0
    graph_execution_verified: bool = False

    def __post_init__(self) -> None:
        text = (
            self.contrast_id,
            self.baseline_profile_id,
            self.candidate_profile_id,
            self.delta_output_expression,
            self.delta_parameter_expression,
            self.action_disagreement_predicate,
            self.boundary_margin_expression,
        )
        if not all(value.strip() for value in text) or not self.atomic_contributions:
            raise ValidationError("parameter contrast is incomplete")
        if self.exactness not in {"symbolic_exact", "deterministic_numeric"}:
            raise ValidationError("parameter contrast exactness is invalid")
        if not self.graph_execution_verified:
            return
        if (
            not self.baseline_parameters
            or set(self.baseline_parameters) != set(self.candidate_parameters)
            or self.baseline_parameters == self.candidate_parameters
        ):
            raise ValidationError("parameter contrast profiles are not a real pair")
        for digest_field, digest in (
            ("synthetic_fixture_digest", self.synthetic_fixture_digest),
            ("baseline_output_digest", self.baseline_output_digest),
            ("candidate_output_digest", self.candidate_output_digest),
            ("delta_output_digest", self.delta_output_digest),
            ("action_disagreement_digest", self.action_disagreement_digest),
            ("numeric_reconciliation_digest", self.numeric_reconciliation_digest),
        ):
            _ = require_digest(digest, field=digest_field)
        expected_reconciliation = canonical_digest(
            {
                "baseline_output_digest": self.baseline_output_digest,
                "candidate_output_digest": self.candidate_output_digest,
                "delta_output_digest": self.delta_output_digest,
                "action_disagreement_digest": self.action_disagreement_digest,
                "output_count": self.output_count,
                "action_disagreement_count": self.action_disagreement_count,
                "maximum_delta_identity_error": self.maximum_delta_identity_error,
            }
        )
        if self.numeric_reconciliation_digest != expected_reconciliation:
            raise ValidationError("parameter contrast numeric reconciliation binding drifted")
        if (
            isinstance(self.output_count, bool)
            or self.output_count < 1
            or isinstance(self.action_disagreement_count, bool)
            or self.action_disagreement_count < 0
            or self.action_disagreement_count > self.output_count
            or self.maximum_delta_identity_error != 0.0
        ):
            raise ValidationError("parameter contrast lacks executable numeric verification")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "contrast_id": self.contrast_id,
            "baseline_profile_id": self.baseline_profile_id,
            "candidate_profile_id": self.candidate_profile_id,
            "delta_output_expression": self.delta_output_expression,
            "delta_parameter_expression": self.delta_parameter_expression,
            "action_disagreement_predicate": self.action_disagreement_predicate,
            "boundary_margin_expression": self.boundary_margin_expression,
            "atomic_contributions": dict(self.atomic_contributions),
            "exactness": self.exactness,
        }
        if self.graph_execution_verified:
            payload.update(
                {
                    "baseline_parameters": dict(self.baseline_parameters),
                    "candidate_parameters": dict(self.candidate_parameters),
                    "synthetic_fixture_digest": self.synthetic_fixture_digest,
                    "baseline_output_digest": self.baseline_output_digest,
                    "candidate_output_digest": self.candidate_output_digest,
                    "delta_output_digest": self.delta_output_digest,
                    "action_disagreement_digest": self.action_disagreement_digest,
                    "numeric_reconciliation_digest": self.numeric_reconciliation_digest,
                    "output_count": self.output_count,
                    "maximum_delta_identity_error": self.maximum_delta_identity_error,
                    "action_disagreement_count": self.action_disagreement_count,
                    "graph_execution_verified": True,
                }
            )
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> ParameterContrastDerivation:
        graph_execution_verified = payload.get("graph_execution_verified") is True
        expected_keys = (
            _PARAMETER_CONTRAST_KEYS | _PARAMETER_CONTRAST_EXECUTION_KEYS
            if graph_execution_verified
            else _PARAMETER_CONTRAST_KEYS
        )
        require_exact_keys(payload, expected_keys, label="parameter contrast")
        atomic_contributions = require_mapping(payload, "atomic_contributions")
        _validate_string_mapping(
            atomic_contributions,
            label="parameter contrast atomic contributions",
        )
        maximum_delta_identity_error = 0.0
        if graph_execution_verified:
            _validate_parameter_map(
                require_mapping(payload, "baseline_parameters"),
                label="parameter contrast baseline parameters",
            )
            _validate_parameter_map(
                require_mapping(payload, "candidate_parameters"),
                label="parameter contrast candidate parameters",
            )
            raw_error = payload.get("maximum_delta_identity_error")
            if isinstance(raw_error, bool) or not isinstance(raw_error, (int, float)):
                raise ValidationError(
                    "maximum_delta_identity_error must be numeric"
                )
            maximum_delta_identity_error = float(raw_error)
        return cls(
            contrast_id=require_text(payload, "contrast_id"),
            baseline_profile_id=require_text(payload, "baseline_profile_id"),
            candidate_profile_id=require_text(payload, "candidate_profile_id"),
            delta_output_expression=require_text(payload, "delta_output_expression"),
            delta_parameter_expression=require_text(payload, "delta_parameter_expression"),
            action_disagreement_predicate=require_text(payload, "action_disagreement_predicate"),
            boundary_margin_expression=require_text(payload, "boundary_margin_expression"),
            atomic_contributions=cast(Mapping[str, str], atomic_contributions),
            exactness=cast(
                Literal["symbolic_exact", "deterministic_numeric"],
                require_text(payload, "exactness"),
            ),
            baseline_parameters=(
                require_mapping(payload, "baseline_parameters") if graph_execution_verified else {}
            ),
            candidate_parameters=(
                require_mapping(payload, "candidate_parameters") if graph_execution_verified else {}
            ),
            synthetic_fixture_digest=str(payload.get("synthetic_fixture_digest", "")),
            baseline_output_digest=str(payload.get("baseline_output_digest", "")),
            candidate_output_digest=str(payload.get("candidate_output_digest", "")),
            delta_output_digest=str(payload.get("delta_output_digest", "")),
            action_disagreement_digest=str(payload.get("action_disagreement_digest", "")),
            numeric_reconciliation_digest=str(payload.get("numeric_reconciliation_digest", "")),
            output_count=(
                _integer(payload, "output_count") if graph_execution_verified else 0
            ),
            maximum_delta_identity_error=maximum_delta_identity_error,
            action_disagreement_count=(
                _integer(payload, "action_disagreement_count") if graph_execution_verified else 0
            ),
            graph_execution_verified=graph_execution_verified,
        )


@dataclass(frozen=True, slots=True)
class FormulaNativeAttributeSpec:
    """A formula-derived attribute that must bind to the internal factor pool."""

    attribute_id: str
    upstream_node_ids: tuple[str, ...]
    causal_formula: str
    unit: str
    availability: Literal["after_close", "static"]
    factor_registration_status: Literal["bound_existing", "registered_new", "blocked"]
    factor_spec_id: str | None = None
    registration_blocker: str | None = None
    evidence_level: EvidenceLevel = "structural_dependency"

    def __post_init__(self) -> None:
        if (
            not self.attribute_id.strip()
            or not self.upstream_node_ids
            or not self.causal_formula.strip()
            or not self.unit.strip()
        ):
            raise ValidationError("formula-native attribute is incomplete")
        if self.availability not in {"after_close", "static"}:
            raise ValidationError("formula-native attribute availability is invalid")
        if self.factor_registration_status not in {
            "bound_existing",
            "registered_new",
            "blocked",
        }:
            raise ValidationError("formula-native registration status is invalid")
        if self.evidence_level != "structural_dependency":
            raise ValidationError("formula-native attributes are structural claims only")
        if self.factor_registration_status == "blocked":
            if self.factor_spec_id is not None or not self.registration_blocker:
                raise ValidationError("blocked attribute requires only a registration blocker")
        elif not self.factor_spec_id or self.registration_blocker is not None:
            raise ValidationError("registered attribute requires FactorSpec and no blocker")

    def to_dict(self) -> dict[str, object]:
        return {
            "attribute_id": self.attribute_id,
            "upstream_node_ids": list(self.upstream_node_ids),
            "causal_formula": self.causal_formula,
            "unit": self.unit,
            "availability": self.availability,
            "factor_registration_status": self.factor_registration_status,
            "factor_spec_id": self.factor_spec_id,
            "registration_blocker": self.registration_blocker,
            "evidence_level": self.evidence_level,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> FormulaNativeAttributeSpec:
        require_exact_keys(
            payload,
            _FORMULA_NATIVE_ATTRIBUTE_KEYS,
            label="formula-native attribute",
        )
        factor_spec_id = payload.get("factor_spec_id")
        blocker = payload.get("registration_blocker")
        if factor_spec_id is not None and not isinstance(factor_spec_id, str):
            raise ValidationError("factor_spec_id must be string or null")
        if blocker is not None and not isinstance(blocker, str):
            raise ValidationError("registration_blocker must be string or null")
        return cls(
            attribute_id=require_text(payload, "attribute_id"),
            upstream_node_ids=_text_sequence(payload, "upstream_node_ids", unique=True),
            causal_formula=require_text(payload, "causal_formula"),
            unit=require_text(payload, "unit"),
            availability=cast(Literal["after_close", "static"], require_text(payload, "availability")),
            factor_registration_status=cast(
                Literal["bound_existing", "registered_new", "blocked"],
                require_text(payload, "factor_registration_status"),
            ),
            factor_spec_id=factor_spec_id if isinstance(factor_spec_id, str) else None,
            registration_blocker=blocker if isinstance(blocker, str) else None,
            evidence_level=cast(EvidenceLevel, require_text(payload, "evidence_level")),
        )


@dataclass(frozen=True, slots=True)
class InteractionStateMachineTemplate:
    """A bounded formula-native interaction/state topology, not a fitted policy."""

    template_id: str
    atom_attribute_ids: tuple[str, ...]
    allowed_operators: tuple[FormulaOperator, ...]
    heredity_requirement: HeredityRequirement
    marginal_admission_required: bool
    complexity_budget: Mapping[str, int]
    state_topology: Mapping[str, object]
    execution_lag_bars: int = 1

    def __post_init__(self) -> None:
        if not self.template_id.strip() or not self.atom_attribute_ids:
            raise ValidationError("interaction template identity/atoms are required")
        if self.heredity_requirement not in _HEREDITY:
            raise ValidationError("interaction template heredity is invalid")
        if self.marginal_admission_required:
            raise ValidationError("V3 formula-native templates cannot require marginal admission")
        if not self.allowed_operators or any(operator not in _TEMPLATE_OPERATORS for operator in self.allowed_operators):
            raise ValidationError("interaction template contains an invalid operator")
        required_budget = {
            "operator_count",
            "coefficient_count",
            "exponent_count",
            "branch_count",
            "threshold_count",
            "scale_count",
            "state_memory_count",
        }
        if set(self.complexity_budget) != required_budget:
            raise ValidationError("interaction template complexity budget is incomplete")
        if any(isinstance(value, bool) or value < 1 for value in self.complexity_budget.values()):
            raise ValidationError("interaction template complexity budget must be positive")
        if self.execution_lag_bars != 1 or not self.state_topology:
            raise ValidationError("interaction template must execute next-bar with a frozen topology")

    def to_dict(self) -> dict[str, object]:
        return {
            "template_id": self.template_id,
            "atom_attribute_ids": list(self.atom_attribute_ids),
            "allowed_operators": list(self.allowed_operators),
            "heredity_requirement": self.heredity_requirement,
            "marginal_admission_required": self.marginal_admission_required,
            "complexity_budget": dict(self.complexity_budget),
            "state_topology": dict(self.state_topology),
            "execution_lag_bars": self.execution_lag_bars,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> InteractionStateMachineTemplate:
        require_exact_keys(
            payload,
            _INTERACTION_TEMPLATE_KEYS,
            label="interaction state-machine template",
        )
        if payload.get("marginal_admission_required") is not False:
            raise ValidationError("interaction template marginal admission changed")
        budget = require_mapping(payload, "complexity_budget")
        state_topology = require_mapping(payload, "state_topology")
        _validate_state_topology(state_topology)
        return cls(
            template_id=require_text(payload, "template_id"),
            atom_attribute_ids=_text_sequence(payload, "atom_attribute_ids", unique=True),
            allowed_operators=tuple(
                cast(FormulaOperator, value)
                for value in _text_sequence(payload, "allowed_operators", unique=True)
            ),
            heredity_requirement=cast(HeredityRequirement, require_text(payload, "heredity_requirement")),
            marginal_admission_required=False,
            complexity_budget={key: _mapping_integer(budget, key) for key in budget},
            state_topology=_frozen_mapping(state_topology),
            execution_lag_bars=_integer(payload, "execution_lag_bars"),
        )


@dataclass(frozen=True, slots=True)
class FormulaDerivationPackage:
    """The zero-data Stage-1 handoff into joint-mechanism research."""

    package_id: str
    graph: FormulaComputationGraph
    parameter_contrasts: tuple[ParameterContrastDerivation, ...]
    formula_native_attributes: tuple[FormulaNativeAttributeSpec, ...]
    interaction_state_machine_templates: tuple[InteractionStateMachineTemplate, ...]
    source_artifact_digests: Mapping[str, str]
    sealed_interval: str = "2021-01-01/2026-12-31"
    readiness_status: Literal[
        "ready_for_joint_mechanism_identification",
        "formula_derivation_blocked",
    ] = "ready_for_joint_mechanism_identification"
    market_data_rows_read: int = 0
    return_rows_read: int = 0
    empirical_validation_executed: bool = False
    production_authority: bool = False
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False

    def __post_init__(self) -> None:
        if not self.package_id.strip() or not self.parameter_contrasts:
            raise ValidationError("formula derivation package identity/contrasts are required")
        if not self.formula_native_attributes or not self.interaction_state_machine_templates:
            raise ValidationError("formula derivation package requires attributes and templates")
        if not self.source_artifact_digests:
            raise ValidationError("formula derivation package source digests are required")
        for name, digest in self.source_artifact_digests.items():
            if not name.strip():
                raise ValidationError("formula derivation source name is required")
            _ = require_digest(digest, field=f"source_artifact_digests.{name}")
        if self.sealed_interval != "2021-01-01/2026-12-31":
            raise ValidationError("formula derivation sealed interval changed")
        attribute_ids = {item.attribute_id for item in self.formula_native_attributes}
        if any(
            atom_id not in attribute_ids for template in self.interaction_state_machine_templates for atom_id in template.atom_attribute_ids
        ):
            raise ValidationError("interaction template references an unknown formula-native attribute")
        has_blocker = any(item.factor_registration_status == "blocked" for item in self.formula_native_attributes)
        expected_status = "formula_derivation_blocked" if has_blocker else "ready_for_joint_mechanism_identification"
        if self.readiness_status != expected_status:
            raise ValidationError("formula derivation readiness disagrees with registration blockers")
        if self.market_data_rows_read != 0 or self.return_rows_read != 0 or self.empirical_validation_executed:
            raise ValidationError("Stage-1 derivation package must be zero-data and non-empirical")
        if self.production_authority or self.dynamic_parameter_authority or self.tool_routing_authority:
            raise ValidationError("formula derivation package cannot grant authority")

    def to_dict(self) -> dict[str, object]:
        return attach_semantic_digest(
            {
                "schema_id": FORMULA_DERIVATION_PACKAGE_SCHEMA_ID,
                "package_id": self.package_id,
                "graph": self.graph.to_dict(),
                "parameter_contrasts": [item.to_dict() for item in self.parameter_contrasts],
                "formula_native_attributes": [item.to_dict() for item in self.formula_native_attributes],
                "interaction_state_machine_templates": [item.to_dict() for item in self.interaction_state_machine_templates],
                "source_artifact_digests": dict(sorted(self.source_artifact_digests.items())),
                "sealed_interval": self.sealed_interval,
                "readiness_status": self.readiness_status,
                "market_data_rows_read": self.market_data_rows_read,
                "return_rows_read": self.return_rows_read,
                "empirical_validation_executed": self.empirical_validation_executed,
                "production_authority": self.production_authority,
                "dynamic_parameter_authority": self.dynamic_parameter_authority,
                "tool_routing_authority": self.tool_routing_authority,
                "field_labels_zh": dict(PACKAGE_LABELS_ZH),
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> FormulaDerivationPackage:
        require_exact_keys(
            payload,
            _FORMULA_DERIVATION_PACKAGE_KEYS,
            label="formula derivation package",
        )
        if payload.get("schema_id") != FORMULA_DERIVATION_PACKAGE_SCHEMA_ID:
            raise ValidationError("formula derivation package schema changed")
        validate_semantic_digest(payload)
        labels = require_mapping(payload, "field_labels_zh")
        _validate_string_mapping(labels, label="formula derivation package labels")
        if dict(labels) != PACKAGE_LABELS_ZH:
            raise ValidationError("formula derivation package labels changed")
        if any(
            payload.get(field) is not False
            for field in (
                "empirical_validation_executed",
                "production_authority",
                "dynamic_parameter_authority",
                "tool_routing_authority",
            )
        ):
            raise ValidationError("formula derivation package authority/data flags changed")
        source_digests = require_mapping(payload, "source_artifact_digests")
        _validate_string_mapping(
            source_digests,
            label="formula derivation package source digests",
        )
        return cls(
            package_id=require_text(payload, "package_id"),
            graph=FormulaComputationGraph.from_dict(require_mapping(payload, "graph")),
            parameter_contrasts=tuple(ParameterContrastDerivation.from_dict(row) for row in _mapping_rows(payload, "parameter_contrasts")),
            formula_native_attributes=tuple(
                FormulaNativeAttributeSpec.from_dict(row) for row in _mapping_rows(payload, "formula_native_attributes")
            ),
            interaction_state_machine_templates=tuple(
                InteractionStateMachineTemplate.from_dict(row) for row in _mapping_rows(payload, "interaction_state_machine_templates")
            ),
            source_artifact_digests=cast(Mapping[str, str], source_digests),
            sealed_interval=require_text(payload, "sealed_interval"),
            readiness_status=cast(
                Literal[
                    "ready_for_joint_mechanism_identification",
                    "formula_derivation_blocked",
                ],
                require_text(payload, "readiness_status"),
            ),
            market_data_rows_read=_integer(payload, "market_data_rows_read"),
            return_rows_read=_integer(payload, "return_rows_read"),
            empirical_validation_executed=False,
            production_authority=False,
            dynamic_parameter_authority=False,
            tool_routing_authority=False,
        )


def _integer(payload: Mapping[str, object], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{key} must be an integer")
    return value


def _mapping_integer(payload: Mapping[str, object], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{key} must be an integer")
    return value


__all__ = [
    "FORMULA_COMPUTATION_GRAPH_SCHEMA_ID",
    "FORMULA_DERIVATION_PACKAGE_SCHEMA_ID",
    "EvidenceLevel",
    "FormulaComputationGraph",
    "FormulaDerivationPackage",
    "FormulaNativeAttributeSpec",
    "FormulaNode",
    "FormulaOperator",
    "HeredityRequirement",
    "InteractionStateMachineTemplate",
    "ParameterContrastDerivation",
]
