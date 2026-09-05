# pyright: reportAny=false, reportArgumentType=false, reportAssignmentType=false
# pyright: reportAttributeAccessIssue=false, reportIndexIssue=false
# pyright: reportImportCycles=false
# pyright: reportMissingTypeStubs=false, reportOperatorIssue=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Source-backed formula feature materialization and immutable receipts.

This is the executable boundary that Stage 1 declares without reading data and
Stage 2 invokes on an authorized pre-2021 data set.  It starts from raw OHLC
bars, calls the frozen public benchmark adapter, derives formula-native
attributes, and binds all row-level material to digests without persisting it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Final, cast

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.factor_engine.models.factor_spec import FactorSpec
from factor_lab.filtering.cloudridge_3_0_hybrid_filter_bank import (
    butterworth_bandpass_component,
)
from factor_lab.filtering.timing_validation import FilterSpec, apply_filter_spec
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.formula_derivation.attribute_contracts import (
    FormulaNativeAttributeBlueprint,
    attribute_blueprints_for_tool,
)
from factor_lab.market_state.formula_derivation.compiler import (
    SOURCE_PANEL_EXECUTOR_REF,
)
from factor_lab.market_state.formula_derivation.models import (
    FormulaComputationGraph,
    FormulaDerivationPackage,
    FormulaNode,
)
from factor_lab.market_state.formula_derivation.validation import (
    require_digest,
    require_exact_keys,
    require_zero_authority,
    validate_semantic_digest,
)
from factor_lab.market_state.tool_benchmark_adapters import run_tool_benchmark_profile
from factor_lab.market_state.tool_formula_mechanisms import (
    ToolFormulaSpec,
    build_tool_formula_mechanism_bundle,
)
from factor_lab.market_state.tool_registry import ToolBenchmarkSpec
from factor_lab.strategy.services.risk_off_v57_asymmetric_arc_envelope import (
    AsymmetricArcEnvelopeSpec,
    build_causal_asymmetric_arc_envelope,
)
from factor_lab.strategy.services.risk_off_v58_frequency_bollinger import (
    FrequencyBollingerSpec,
    build_frequency_bollinger,
)
from factor_lab.strategy.services.risk_off_v58_lowpass_residual_envelope import (
    LowpassResidualEnvelopeSpec,
    build_causal_lowpass_residual_envelope,
)

FEATURE_MATERIALIZATION_RECEIPT_SCHEMA_ID: Final[str] = "market_state_formula_feature_materialization_receipt@1.0"
_FEATURE_MATERIALIZATION_RECEIPT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_id",
        "receipt_id",
        "tool_id",
        "frequency",
        "materialization_mode",
        "graph_digest",
        "derivation_package_digest",
        "factor_spec_digests",
        "benchmark_spec_digest",
        "parameters",
        "parameters_digest",
        "dataset_ref",
        "dataset_sha256",
        "raw_kline_content_digest",
        "raw_kline_input_fields",
        "provenance_binding_digest",
        "row_count",
        "feature_columns",
        "observation_dates_digest",
        "feature_rows_digest",
        "baseline_action_digest",
        "forward_return_digest",
        "sample_start_date",
        "sample_end_date",
        "source_adapter_equivalent",
        "graph_execution_equivalent",
        "graph_target_digest",
        "benchmark_target_digest",
        "graph_cost_digest",
        "benchmark_cost_digest",
        "signal_clock",
        "execution_lag_bars",
        "cost_bps",
        "post_2020_rows_read",
        "trade_or_event_rows_persisted",
        "action_detail_exposed",
        "production_authority",
        "dynamic_parameter_authority",
        "tool_routing_authority",
        "field_labels_zh",
        "semantic_digest",
    }
)
RAW_KLINE_FIELDS: Final[tuple[str, ...]] = (
    "timestamp",
    "open",
    "high",
    "low",
    "close",
)
ROUND3_ROLLING_FORMULA_TOOL_IDS: Final[frozenset[str]] = frozenset(
    {
        "bollinger_volatility_channel",
        "butterworth_clean_bandpass",
        "causal_haar_wavelet_bandpass",
        "donchian_price_channel",
        "laplace_iir_mixed_bandpass",
        "r3_nested_moving_average_component",
        "simple_moving_average_trend",
    }
)
RECEIPT_LABELS_ZH: Final[Mapping[str, str]] = {
    "schema_id": "Schema标识",
    "receipt_id": "物化收据标识",
    "tool_id": "择时工具标识",
    "materialization_mode": "物化模式",
    "graph_digest": "公式图语义摘要",
    "derivation_package_digest": "公式派生包语义摘要",
    "factor_spec_digests": "FactorSpec语义摘要集合",
    "benchmark_spec_digest": "冻结基准工具规格摘要",
    "frequency": "冻结基准频率",
    "parameters": "冻结基准参数",
    "parameters_digest": "冻结参数摘要",
    "dataset_ref": "数据集引用",
    "dataset_sha256": "实际输入原始K线规范内容摘要",
    "raw_kline_content_digest": "原始K线内容摘要",
    "provenance_binding_digest": "权威来源绑定摘要",
    "raw_kline_input_fields": "原始K线输入字段",
    "row_count": "物化行数",
    "sample_start_date": "样本开始日期",
    "sample_end_date": "样本结束日期",
    "observation_dates_digest": "观测时点摘要",
    "feature_columns": "公式属性列",
    "feature_rows_digest": "公式属性行摘要",
    "baseline_action_digest": "冻结基线动作摘要",
    "forward_return_digest": "下一根收益摘要",
    "source_adapter_equivalent": "是否等价调用冻结公开适配器",
    "graph_target_digest": "计算图目标仓位摘要",
    "benchmark_target_digest": "公开基准目标仓位摘要",
    "graph_cost_digest": "计算图成本摘要",
    "benchmark_cost_digest": "公开基准成本摘要",
    "graph_execution_equivalent": "计算图与公开基准是否数值等价",
    "signal_clock": "信号时钟",
    "execution_lag_bars": "执行滞后K线数",
    "cost_bps": "交易成本基点",
    "post_2020_rows_read": "2020年后读取行数",
    "trade_or_event_rows_persisted": "持久化交易或事件行数",
    "action_detail_exposed": "是否暴露动作明细",
    "production_authority": "生产权限",
    "dynamic_parameter_authority": "动态参数权限",
    "tool_routing_authority": "工具路由权限",
    "field_labels_zh": "中文字段标签",
    "semantic_digest": "语义摘要",
}
_PROVENANCE_FIELDS: Final[tuple[str, ...]] = (
    "receipt_id",
    "tool_id",
    "materialization_mode",
    "graph_digest",
    "derivation_package_digest",
    "factor_spec_digests",
    "benchmark_spec_digest",
    "frequency",
    "parameters",
    "parameters_digest",
    "dataset_ref",
    "dataset_sha256",
    "raw_kline_content_digest",
)


@dataclass(frozen=True, slots=True)
class FormulaFeatureMaterialization:
    """In-memory attributes plus the only serializable aggregate receipt."""

    feature_frame: pd.DataFrame
    baseline_actions: tuple[float, ...]
    forward_returns: tuple[float, ...]
    observation_dates: tuple[str, ...]
    receipt: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class SourceFormulaGraphPanel:
    """Executable raw-OHLC graph outputs before any research label is used."""

    feature_frame: pd.DataFrame
    target_position: pd.Series
    next_bar_position: pd.Series
    transaction_cost: pd.Series
    forward_return: pd.Series
    decision_time: pd.Series


def execute_source_formula_graph_panel(
    *,
    graph: FormulaComputationGraph,
    bars: pd.DataFrame,
    benchmark: ToolBenchmarkSpec,
    frequency: str,
    parameters: Mapping[str, float | int | str],
) -> SourceFormulaGraphPanel:
    """Execute the graph's raw inputs, attributes, decision, lag and cost path."""

    frame = _validated_bars(bars)
    if not frequency.strip():
        raise ValidationError("source formula graph frequency is required")
    if graph.tool_id != benchmark.tool_id or graph.decision_output_id != "target_position":
        raise ValidationError("source formula graph is bound to another benchmark")
    if graph.raw_kline_input_fields != RAW_KLINE_FIELDS:
        raise ValidationError("source formula graph raw K-line fields changed")
    _validate_implementation_bound_source_graph(graph)
    native = _native_attributes(frame, benchmark.tool_id, parameters)
    source_target = _formula_target_from_raw(frame, benchmark.tool_id, parameters).astype(float)
    source_target = source_target.clip(0.0, 1.0).fillna(0.0)
    values: dict[str, pd.Series | float] = {}
    raw_node_ids: set[str] = set()
    attribute_node_ids: dict[str, str] = {}
    for node in graph.nodes:
        values[node.node_id] = _execute_source_panel_node(
            node=node,
            values=values,
            frame=frame,
            native_attributes=native,
            source_target=source_target,
            graph=graph,
            parameters=parameters,
        )
        if node.operator == "input":
            raw_node_ids.add(node.node_id)
        elif node.operator == "source_attribute":
            attribute_node_ids[str(node.domain_guard["attribute_id"])] = node.node_id
    if len(raw_node_ids) != len(RAW_KLINE_FIELDS) or set(attribute_node_ids) != set(native.columns):
        raise ValidationError("source formula graph execution surface differs from its declared outputs")
    try:
        target = _series_value(values[graph.decision_output_id], graph.decision_output_id)
        next_bar = _series_value(values["next_bar_position"], "next_bar_position")
        cost = _series_value(values["transaction_cost"], "transaction_cost")
        decision_time_node = next(
            node.node_id for node in graph.nodes if node.operator == "input" and node.kline_field_refs == ("timestamp",)
        )
        decision_time = _series_value(values[decision_time_node], "decision_time")
    except (KeyError, StopIteration) as exc:
        raise ValidationError("source formula graph execution path is incomplete") from exc
    forward = np.log(frame["close"].shift(-1) / frame["close"])
    result = pd.DataFrame(
        {
            "decision_time": decision_time,
            "target_position": target,
            "next_bar_position": next_bar,
            "transaction_cost": cost,
            "forward_return": forward,
        }
    ).dropna(subset=["forward_return"])
    native.index = frame.index
    return SourceFormulaGraphPanel(
        feature_frame=native.iloc[: len(result)].reset_index(drop=True),
        target_position=cast(pd.Series, result["target_position"]).reset_index(drop=True),
        next_bar_position=cast(pd.Series, result["next_bar_position"]).reset_index(drop=True),
        transaction_cost=cast(pd.Series, result["transaction_cost"]).reset_index(drop=True),
        forward_return=cast(pd.Series, result["forward_return"]).reset_index(drop=True),
        decision_time=cast(pd.Series, result["decision_time"]).reset_index(drop=True),
    )


def _validate_implementation_bound_source_graph(
    graph: FormulaComputationGraph,
) -> None:
    """Bind every serialized witness to the registered panel dispatch contract.

    V1 benchmark graphs are implementation-bound IR, not a portable formula
    interpreter.  A rehashed mutation of formula text, witness metadata, node
    shape, or executor identity must therefore fail before any values are read.
    """

    formulas = {item.tool_id: item for item in build_tool_formula_mechanism_bundle().tool_formulas}
    try:
        source = formulas[graph.tool_id]
    except KeyError as exc:
        raise ValidationError("source formula graph tool is not registered") from exc
    if (
        graph.tool_version != "v1_benchmark"
        or graph.graph_id != f"formula-graph:{graph.tool_id}:v1"
        or dict(graph.source_formula_contract or {}) != source.to_dict()
        or graph.source_materializer_ref != SOURCE_PANEL_EXECUTOR_REF
    ):
        raise ValidationError("source formula graph is not bound to its authoritative implementation contract")
    blueprints = attribute_blueprints_for_tool(graph.tool_id)
    expected_nodes = _expected_source_graph_nodes(source, blueprints)
    actual_nodes = tuple(node.to_dict() for node in graph.nodes)
    expected_outputs = (
        *(item.output_node_id for item in blueprints),
        "target_position",
        "next_bar_position",
        "transaction_cost",
    )
    if actual_nodes != expected_nodes or graph.output_node_ids != expected_outputs:
        raise ValidationError("source formula graph serialized semantics differ from its panel executor")


def _expected_source_graph_nodes(
    source: ToolFormulaSpec,
    blueprints: tuple[FormulaNativeAttributeBlueprint, ...],
) -> tuple[dict[str, object], ...]:
    witness = {
        "formula_id": source.formula_id,
        "implementation_ref": source.implementation_ref,
    }
    raw_ids = tuple(f"raw_{field}" for field in RAW_KLINE_FIELDS)
    rows: list[dict[str, object]] = [
        {
            "node_id": f"raw_{field}",
            "operator": "input",
            "input_node_ids": [],
            "kline_field_refs": [field],
            "parameter_refs": [],
            "unit": "timestamp" if field == "timestamp" else "price",
            "availability": "after_close",
            "warmup_bars": 0,
            "missing_policy": "warmup_or_missing_is_null",
            "domain_guard": {},
            "source_witness": witness,
            "evidence_level": "structural_dependency",
        }
        for field in RAW_KLINE_FIELDS
    ]
    rows.extend(
        {
            "node_id": item.output_node_id,
            "operator": "source_attribute",
            "input_node_ids": list(raw_ids),
            "kline_field_refs": [],
            "parameter_refs": [],
            "unit": item.unit,
            "availability": "after_close",
            "warmup_bars": 0,
            "missing_policy": "source_warmup_or_domain_guard_yields_null",
            "domain_guard": {
                "attribute_id": item.attribute_id,
                "causal_formula": item.formula,
            },
            "source_witness": witness,
            "evidence_level": "structural_dependency",
        }
        for item in blueprints
    )
    rows.extend(
        (
            {
                "node_id": "target_position",
                "operator": "source_target_position",
                "input_node_ids": list(raw_ids),
                "kline_field_refs": [],
                "parameter_refs": [],
                "unit": "dimensionless",
                "availability": "after_close",
                "warmup_bars": 0,
                "missing_policy": "frozen_source_validity_then_cash",
                "domain_guard": {"signal_formula": source.signal_formula},
                "source_witness": witness,
                "evidence_level": "structural_dependency",
            },
            {
                "node_id": "cost_bps",
                "operator": "constant",
                "input_node_ids": [],
                "kline_field_refs": [],
                "parameter_refs": ["cost_bps"],
                "unit": "bps",
                "availability": "static",
                "warmup_bars": 0,
                "missing_policy": "fail_closed",
                "domain_guard": {},
                "source_witness": witness,
                "evidence_level": "structural_dependency",
            },
            {
                "node_id": "next_bar_position",
                "operator": "execution_lag",
                "input_node_ids": ["target_position"],
                "kline_field_refs": [],
                "parameter_refs": [],
                "unit": "dimensionless",
                "availability": "after_close",
                "warmup_bars": 0,
                "missing_policy": "cash_until_decision_available",
                "domain_guard": {"lag_bars": 1},
                "source_witness": witness,
                "evidence_level": "structural_dependency",
            },
            {
                "node_id": "transaction_cost",
                "operator": "transaction_cost",
                "input_node_ids": [
                    "target_position",
                    "next_bar_position",
                    "cost_bps",
                ],
                "kline_field_refs": [],
                "parameter_refs": [],
                "unit": "log_return",
                "availability": "after_close",
                "warmup_bars": 0,
                "missing_policy": "fail_closed",
                "domain_guard": {"formula": "abs(position_t-position_(t-1))*cost_bps/10000"},
                "source_witness": witness,
                "evidence_level": "structural_dependency",
            },
        )
    )
    return tuple(rows)


def _execute_source_panel_node(
    *,
    node: FormulaNode,
    values: Mapping[str, pd.Series | float],
    frame: pd.DataFrame,
    native_attributes: pd.DataFrame,
    source_target: pd.Series,
    graph: FormulaComputationGraph,
    parameters: Mapping[str, float | int | str],
) -> pd.Series | float:
    """Evaluate one declared panel node; no execution-path metadata is ignored."""

    if any(parent not in values for parent in node.input_node_ids):
        raise ValidationError("source formula graph is not topologically executable")
    if node.operator == "input":
        if len(node.kline_field_refs) != 1 or node.input_node_ids or node.parameter_refs:
            raise ValidationError("source graph input node shape changed")
        field = node.kline_field_refs[0]
        if field not in RAW_KLINE_FIELDS:
            raise ValidationError("source graph input escaped the raw K-line contract")
        return cast(pd.Series, frame[field]).reset_index(drop=True)
    if node.operator == "constant":
        if len(node.parameter_refs) != 1 or node.input_node_ids or node.kline_field_refs:
            raise ValidationError("source graph constant node shape changed")
        parameter_id = node.parameter_refs[0]
        if parameter_id != graph.cost_parameter_id:
            raise ValidationError("source graph constant is not the frozen cost parameter")
        try:
            return float(parameters[parameter_id])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError("source graph cost parameter is missing or non-numeric") from exc
    if node.operator in {"source_attribute", "source_target_position"}:
        if len(node.input_node_ids) != len(RAW_KLINE_FIELDS) or node.kline_field_refs or node.parameter_refs:
            raise ValidationError(f"{node.operator} node shape changed")
        parent_fields = {
            graph_node.kline_field_refs[0]
            for graph_node in graph.nodes
            if graph_node.node_id in node.input_node_ids and graph_node.operator == "input" and len(graph_node.kline_field_refs) == 1
        }
        if parent_fields != set(RAW_KLINE_FIELDS):
            raise ValidationError(f"{node.operator} does not consume the five declared raw inputs")
        if node.operator == "source_target_position":
            return source_target.reset_index(drop=True)
        attribute_id = node.domain_guard.get("attribute_id")
        if not isinstance(attribute_id, str) or attribute_id not in native_attributes:
            raise ValidationError("source_attribute node is not executable")
        return cast(pd.Series, native_attributes[attribute_id]).reset_index(drop=True)
    if node.operator == "execution_lag":
        if node.input_node_ids != (graph.decision_output_id,) or node.domain_guard.get("lag_bars") != 1:
            raise ValidationError("execution_lag node lost its frozen next-bar dependency")
        return _series_value(values[node.input_node_ids[0]], node.node_id).copy()
    if node.operator == "transaction_cost":
        if node.input_node_ids != (graph.decision_output_id, "next_bar_position", graph.cost_parameter_id):
            raise ValidationError("transaction_cost node lost its decision/position/cost dependencies")
        position = _series_value(values["next_bar_position"], node.node_id)
        cost_bps = values[graph.cost_parameter_id]
        if isinstance(cost_bps, pd.Series):
            raise ValidationError("transaction_cost parameter must be scalar")
        return position.diff().abs().fillna(position.abs()) * (float(cost_bps) / 10_000.0)
    raise ValidationError(f"source formula panel operator is not executable: {node.operator}")


def _series_value(value: pd.Series | float, field: str) -> pd.Series:
    if not isinstance(value, pd.Series):
        raise ValidationError(f"source formula graph {field} must be a series")
    return value


def materialize_formula_native_panel(
    *,
    bars: pd.DataFrame,
    benchmark: ToolBenchmarkSpec,
    frequency: str,
    parameters: Mapping[str, float | int | str],
    derivation_package: FormulaDerivationPackage,
    registered_factor_specs: Sequence[FactorSpec],
    dataset_ref: str,
    dataset_sha256: str,
    tail_rows: int | None = None,
) -> FormulaFeatureMaterialization:
    """Materialize one frozen tool from raw K-lines and prove adapter identity."""

    frame = _validated_bars(bars)
    if not dataset_ref.strip():
        raise ValidationError("formula materialization dataset_ref is required")
    graph = derivation_package.graph
    graph_digest = require_digest(graph.to_dict()["semantic_digest"], field="materialization graph digest")
    derivation_package_digest = require_digest(
        derivation_package.to_dict()["semantic_digest"],
        field="materialization derivation package digest",
    )
    _ = require_digest(dataset_sha256, field="materialization dataset digest")
    raw_kline_content_digest = raw_kline_content_digest_for_bars(frame)
    if dataset_sha256 != raw_kline_content_digest:
        raise ValidationError("formula materialization dataset digest does not match input K-line content")
    if not registered_factor_specs:
        raise ValidationError("formula materialization requires registered FactorSpecs")
    normalized_factor_digests = tuple(
        require_digest(
            canonical_digest(spec.to_dict()),
            field="materialization factor spec digest",
        )
        for spec in registered_factor_specs
    )
    frozen_parameters = benchmark.parameters_by_frequency.get(frequency)
    if frozen_parameters is None or dict(parameters) != dict(frozen_parameters):
        raise ValidationError("formula materialization parameters are not the frozen benchmark profile")
    graph_panel = execute_source_formula_graph_panel(
        graph=graph,
        bars=frame,
        benchmark=benchmark,
        frequency=frequency,
        parameters=parameters,
    )
    benchmark_panel = run_tool_benchmark_profile(
        frame,
        benchmark,
        frequency=frequency,
        parameters=parameters,
        benchmark_id=f"formula-materialization:{benchmark.tool_id}",
    )
    decision_index = pd.DatetimeIndex(pd.to_datetime(benchmark_panel["decision_time"], errors="raise"))
    features = graph_panel.feature_frame.copy()
    features.index = decision_index
    baseline = benchmark_panel["target_position"].to_numpy(dtype=float)
    returns = benchmark_panel["forward_market_log_return"].to_numpy(dtype=float)
    if len(features) != len(baseline) or bool(features.isna().to_numpy().any()):
        valid = features.notna().all(axis=1).to_numpy(dtype=bool)
        features = features.loc[valid]
        baseline = baseline[valid]
        returns = returns[valid]
        decision_index = decision_index[valid]
    if features.empty:
        raise ValidationError("formula materialization has no causally complete rows")
    if tail_rows is not None:
        if tail_rows < 1 or len(features) < tail_rows:
            raise ValidationError("formula materialization tail row bound is invalid")
        features = features.iloc[-tail_rows:]
        baseline = baseline[-tail_rows:]
        returns = returns[-tail_rows:]
        decision_index = decision_index[-tail_rows:]
    if not np.isfinite(features.to_numpy(dtype=float)).all():
        raise ValidationError("formula materialization produced non-finite attributes")
    if not np.isfinite(baseline).all() or not np.isfinite(returns).all():
        raise ValidationError("formula materialization benchmark alignment is non-finite")
    graph_target = graph_panel.target_position.to_numpy(dtype=float)
    graph_cost = graph_panel.transaction_cost.to_numpy(dtype=float)
    benchmark_target = benchmark_panel["target_position"].to_numpy(dtype=float)
    benchmark_cost = benchmark_panel["transaction_cost_log_return"].to_numpy(dtype=float)
    equivalent = np.array_equal(benchmark_target, graph_target) and np.allclose(benchmark_cost, graph_cost, rtol=0.0, atol=1e-15)
    if not equivalent:
        raise ValidationError("formula materializer and frozen benchmark target diverged")
    observation_dates = tuple(timestamp.isoformat() for timestamp in decision_index)
    feature_rows = tuple({column: float(value) for column, value in row.items()} for row in features.to_dict(orient="records"))
    normalized_parameters = dict(sorted(parameters.items()))
    parameters_digest = canonical_digest(normalized_parameters)
    receipt_labels = dict(RECEIPT_LABELS_ZH)
    receipt_labels.update({key: f"冻结基准参数：{key}" for key in normalized_parameters if key not in receipt_labels})
    payload: dict[str, object] = {
        "schema_id": FEATURE_MATERIALIZATION_RECEIPT_SCHEMA_ID,
        "receipt_id": f"formula-materialization:{benchmark.tool_id}:{frequency}",
        "tool_id": benchmark.tool_id,
        "materialization_mode": "source_backed_frozen_adapter",
        "graph_digest": graph_digest,
        "derivation_package_digest": derivation_package_digest,
        "factor_spec_digests": list(normalized_factor_digests),
        "benchmark_spec_digest": canonical_digest(benchmark.to_dict()),
        "frequency": frequency,
        "parameters": normalized_parameters,
        "parameters_digest": parameters_digest,
        "dataset_ref": dataset_ref,
        "dataset_sha256": dataset_sha256,
        "raw_kline_content_digest": raw_kline_content_digest,
        "raw_kline_input_fields": list(RAW_KLINE_FIELDS),
        "row_count": len(feature_rows),
        "sample_start_date": observation_dates[0][:10],
        "sample_end_date": observation_dates[-1][:10],
        "observation_dates_digest": canonical_digest(list(observation_dates)),
        "feature_columns": list(features.columns),
        "feature_rows_digest": canonical_digest(list(feature_rows)),
        "baseline_action_digest": canonical_digest(list(map(float, baseline))),
        "forward_return_digest": canonical_digest(list(map(float, returns))),
        "source_adapter_equivalent": equivalent,
        "graph_target_digest": canonical_digest(list(map(float, graph_target))),
        "benchmark_target_digest": canonical_digest(list(map(float, benchmark_target))),
        "graph_cost_digest": canonical_digest(list(map(float, graph_cost))),
        "benchmark_cost_digest": canonical_digest(list(map(float, benchmark_cost))),
        "graph_execution_equivalent": equivalent,
        "signal_clock": "after_close",
        "execution_lag_bars": 1,
        "cost_bps": float(parameters["cost_bps"]),
        "post_2020_rows_read": int(sum(date[:10] > "2020-12-31" for date in observation_dates)),
        "trade_or_event_rows_persisted": 0,
        "action_detail_exposed": False,
        "production_authority": False,
        "dynamic_parameter_authority": False,
        "tool_routing_authority": False,
        "field_labels_zh": receipt_labels,
    }
    payload["provenance_binding_digest"] = _provenance_binding_digest(payload)
    payload["semantic_digest"] = canonical_digest(payload)
    validate_feature_materialization_receipt(
        payload,
        derivation_package=derivation_package,
        registered_factor_specs=registered_factor_specs,
        benchmark=benchmark,
        raw_bars=frame,
    )
    return FormulaFeatureMaterialization(
        feature_frame=features.reset_index(drop=True),
        baseline_actions=tuple(map(float, baseline)),
        forward_returns=tuple(map(float, returns)),
        observation_dates=observation_dates,
        receipt=payload,
    )


def materialize_registered_formula_factor(
    *,
    bars: pd.DataFrame,
    tool_id: str,
    attribute_id: str,
    parameters: Mapping[str, float | int | str],
) -> pd.Series:
    """Execute one registered formula-native FactorSpec from raw K-line rows."""

    frame = _validated_bars(bars)
    attributes = _native_attributes(frame, tool_id, parameters)
    if attribute_id not in attributes.columns:
        raise ValidationError(f"registered formula-native attribute is unavailable: {tool_id}:{attribute_id}")
    return pd.Series(
        attributes[attribute_id].to_numpy(dtype=float),
        index=pd.DatetimeIndex(frame["timestamp"]),
        name=attribute_id,
    )


def materialize_round3_rolling_formula_attributes(
    *,
    bars: pd.DataFrame,
    tool_id: str,
    parameters: Mapping[str, float | int | str],
) -> pd.DataFrame:
    """Materialize the seven Round-3 daily tools beyond the sealed pilot era.

    The original registered materializer remains deliberately sealed before
    2021 because its receipts are historical evidence.  Round 3 instead uses
    this separate, research-only path over an ordered raw-OHLC prefix.  It has
    no target, return, portfolio, or production-authority input.
    """

    if tool_id not in ROUND3_ROLLING_FORMULA_TOOL_IDS:
        raise ValidationError(f"tool is not admitted to Round-3 rolling materialization: {tool_id}")
    frame = _validated_round3_rolling_bars(bars)
    attributes = _native_attributes(frame, tool_id, parameters).copy()
    if attributes.empty or attributes.columns.empty:
        raise ValidationError("Round-3 rolling formula attributes are empty")
    if attributes.columns.duplicated().any():
        raise ValidationError("Round-3 rolling formula attribute ids are duplicated")
    attributes.index = pd.DatetimeIndex(frame["timestamp"], name="timestamp")
    return attributes


def validate_feature_materialization_receipt(
    payload: Mapping[str, object],
    *,
    derivation_package: FormulaDerivationPackage | None = None,
    registered_factor_specs: Sequence[FactorSpec] = (),
    benchmark: ToolBenchmarkSpec | None = None,
    raw_bars: pd.DataFrame | None = None,
    allow_frozen_digest_only: bool = False,
) -> None:
    """Reject unbound, post-2020, non-equivalent, or authority-bearing receipts."""

    if payload.get("schema_id") != FEATURE_MATERIALIZATION_RECEIPT_SCHEMA_ID:
        raise ValidationError("formula feature materialization schema changed")
    require_exact_keys(
        payload,
        _FEATURE_MATERIALIZATION_RECEIPT_KEYS,
        label="formula feature materialization receipt",
    )
    validate_semantic_digest(payload)
    require_zero_authority(payload)
    mode = payload.get("materialization_mode")
    if mode not in {
        "source_backed_frozen_adapter",
        "deterministic_counterexample_fixture",
        "deterministic_stage1_bound_counterexample_fixture",
    }:
        raise ValidationError("formula materialization mode is invalid")
    if mode == "deterministic_counterexample_fixture" and not str(payload.get("tool_id", "")).startswith("synthetic_"):
        raise ValidationError("counterexample receipts are restricted to synthetic tools")
    if mode == "deterministic_stage1_bound_counterexample_fixture" and str(payload.get("tool_id", "")).startswith("synthetic_"):
        raise ValidationError("Stage-1-bound fixtures require a registered real tool")
    labels = payload.get("field_labels_zh")
    if not isinstance(labels, Mapping) or not set(RECEIPT_LABELS_ZH).issubset(labels):
        raise ValidationError("formula materialization Chinese field labels are incomplete")
    for field in ("receipt_id", "tool_id", "dataset_ref"):
        if not isinstance(payload.get(field), str) or not str(payload[field]).strip():
            raise ValidationError(f"formula materialization requires {field}")
    factor_digests = payload.get("factor_spec_digests")
    if not isinstance(factor_digests, list) or not factor_digests:
        raise ValidationError("formula materialization requires FactorSpec digests")
    for value in cast(list[object], factor_digests):
        _ = require_digest(value, field="factor_spec_digests")
    for field in (
        "graph_digest",
        "derivation_package_digest",
        "benchmark_spec_digest",
        "parameters_digest",
        "dataset_sha256",
        "raw_kline_content_digest",
        "provenance_binding_digest",
        "observation_dates_digest",
        "feature_rows_digest",
        "baseline_action_digest",
        "forward_return_digest",
        "graph_target_digest",
        "benchmark_target_digest",
        "graph_cost_digest",
        "benchmark_cost_digest",
    ):
        _ = require_digest(payload.get(field), field=field)
    if payload.get("provenance_binding_digest") != _provenance_binding_digest(payload):
        raise ValidationError("formula materialization provenance binding drifted")
    if payload.get("raw_kline_input_fields") != list(RAW_KLINE_FIELDS):
        raise ValidationError("formula materialization raw K-line contract changed")
    row_count = payload.get("row_count")
    feature_columns = payload.get("feature_columns")
    if isinstance(row_count, bool) or not isinstance(row_count, int) or row_count < 1:
        raise ValidationError("formula materialization row count is invalid")
    if (
        not isinstance(feature_columns, list)
        or not feature_columns
        or len(feature_columns) != len(set(cast(list[object], feature_columns)))
        or any(not isinstance(value, str) or not value for value in feature_columns)
    ):
        raise ValidationError("formula materialization feature columns are invalid")
    try:
        sample_start = date.fromisoformat(str(payload.get("sample_start_date", "")))
        sample_end = date.fromisoformat(str(payload.get("sample_end_date", "")))
    except ValueError as exc:
        raise ValidationError("formula materialization sample dates are invalid") from exc
    if sample_start > sample_end or sample_end > date(2020, 12, 31):
        raise ValidationError("formula materialization sample dates cross the sealed boundary")
    if mode == "source_backed_frozen_adapter":
        if payload.get("source_adapter_equivalent") is not True:
            raise ValidationError("formula materialization lacks frozen-adapter equivalence")
        if (
            payload.get("graph_execution_equivalent") is not True
            or payload.get("graph_target_digest") != payload.get("benchmark_target_digest")
            or payload.get("graph_cost_digest") != payload.get("benchmark_cost_digest")
        ):
            raise ValidationError("formula graph does not numerically reproduce target and cost")
    elif payload.get("source_adapter_equivalent") is not False or payload.get("graph_execution_equivalent") is not False:
        raise ValidationError("no-market fixture cannot claim source/graph execution equivalence")
    if payload.get("execution_lag_bars") != 1 or payload.get("signal_clock") != "after_close":
        raise ValidationError("formula materialization clock changed")
    cost = payload.get("cost_bps")
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not isfinite(float(cost)) or float(cost) < 0.0:
        raise ValidationError("formula materialization cost is invalid")
    if payload.get("post_2020_rows_read") != 0:
        raise ValidationError("formula materialization opened the sealed interval")
    if payload.get("trade_or_event_rows_persisted") != 0 or payload.get("action_detail_exposed") is not False:
        raise ValidationError("formula materialization exposed row detail")
    if any(
        payload.get(field) is not False
        for field in (
            "production_authority",
            "dynamic_parameter_authority",
            "tool_routing_authority",
        )
    ):
        raise ValidationError("formula materialization granted authority")
    if mode == "source_backed_frozen_adapter":
        if payload.get("dataset_sha256") != payload.get("raw_kline_content_digest"):
            raise ValidationError("formula materialization dataset digest is caller-asserted rather than content-derived")
        if derivation_package is None or benchmark is None:
            derivation_package, registered_factor_specs, benchmark = resolve_authoritative_formula_materialization_objects(
                str(payload["tool_id"])
            )
        _validate_authoritative_source_provenance(
            payload,
            derivation_package=derivation_package,
            registered_factor_specs=registered_factor_specs,
            benchmark=benchmark,
        )
        if raw_bars is not None:
            actual_source_digest = raw_kline_content_digest_for_bars(raw_bars)
            if payload.get("dataset_sha256") != actual_source_digest or payload.get("raw_kline_content_digest") != actual_source_digest:
                raise ValidationError("formula materialization source rows do not reproduce the dataset digest")
        elif not allow_frozen_digest_only:
            raise ValidationError("source-backed receipt requires independent raw K-line reconstruction")
    elif mode == "deterministic_stage1_bound_counterexample_fixture":
        if derivation_package is None or benchmark is None:
            derivation_package, registered_factor_specs, benchmark = resolve_authoritative_formula_materialization_objects(
                str(payload["tool_id"])
            )
        _validate_authoritative_source_provenance(
            payload,
            derivation_package=derivation_package,
            registered_factor_specs=registered_factor_specs,
            benchmark=benchmark,
        )


def _provenance_binding_digest(payload: Mapping[str, object]) -> str:
    return canonical_digest({field: payload.get(field) for field in _PROVENANCE_FIELDS})


def raw_kline_content_digest_for_bars(bars: pd.DataFrame) -> str:
    """Digest the validated raw OHLC rows exactly as materialization consumes them."""

    frame = _validated_bars(bars)
    rows = [
        {
            "timestamp": pd.Timestamp(timestamp).isoformat(),
            "open": float(open_value),
            "high": float(high_value),
            "low": float(low_value),
            "close": float(close_value),
        }
        for timestamp, open_value, high_value, low_value, close_value in frame.loc[:, list(RAW_KLINE_FIELDS)].itertuples(
            index=False, name=None
        )
    ]
    return canonical_digest(rows)


def resolve_authoritative_formula_materialization_objects(
    tool_id: str,
) -> tuple[FormulaDerivationPackage, tuple[FactorSpec, ...], ToolBenchmarkSpec]:
    # Local imports avoid making the derivation builder depend on itself at
    # module-import time.  Validation still reconstructs authority from the
    # current registries instead of trusting receipt strings.
    from factor_lab.market_state.formula_derivation.families import (
        TOOL_FAMILY_MEMBERS,
        build_formula_derivation_for_tool,
    )
    from factor_lab.market_state.tool_formula_mechanisms import (
        build_tool_formula_mechanism_bundle,
    )
    from factor_lab.market_state.tool_registry import tool_benchmark_specs

    formulas = {item.tool_id: item for item in build_tool_formula_mechanism_bundle().tool_formulas}
    benchmarks = {item.tool_id: item for item in tool_benchmark_specs()}
    family_ids = [family_id for family_id, members in TOOL_FAMILY_MEMBERS.items() if tool_id in members]
    if tool_id not in formulas or tool_id not in benchmarks or len(family_ids) != 1:
        raise ValidationError("formula materialization tool is absent from authoritative registries")
    derivation = build_formula_derivation_for_tool(
        formulas[tool_id],
        formula_family_id=family_ids[0],
        persist_factor_registration=False,
    )
    return (
        derivation.package,
        derivation.registered_factor_specs,
        benchmarks[tool_id],
    )


def _validate_authoritative_source_provenance(
    payload: Mapping[str, object],
    *,
    derivation_package: FormulaDerivationPackage,
    registered_factor_specs: Sequence[FactorSpec],
    benchmark: ToolBenchmarkSpec,
) -> None:
    tool_id = str(payload.get("tool_id", ""))
    graph = derivation_package.graph
    expected_factor_digests = [canonical_digest(spec.to_dict()) for spec in registered_factor_specs]
    expected_columns = [attribute.attribute_id for attribute in derivation_package.formula_native_attributes]
    frequency = payload.get("frequency")
    parameters = payload.get("parameters")
    if not isinstance(frequency, str) or not isinstance(parameters, Mapping):
        raise ValidationError("formula materialization frequency/parameters are missing")
    frozen_parameters = benchmark.parameters_by_frequency.get(frequency)
    if (
        graph.tool_id != tool_id
        or benchmark.tool_id != tool_id
        or payload.get("graph_digest") != graph.to_dict()["semantic_digest"]
        or payload.get("derivation_package_digest") != derivation_package.to_dict()["semantic_digest"]
        or payload.get("factor_spec_digests") != expected_factor_digests
        or payload.get("benchmark_spec_digest") != canonical_digest(benchmark.to_dict())
        or payload.get("feature_columns") != expected_columns
        or frozen_parameters is None
        or dict(parameters) != dict(frozen_parameters)
        or payload.get("parameters_digest") != canonical_digest(dict(sorted(frozen_parameters.items())))
        or float(str(payload.get("cost_bps"))) != float(frozen_parameters[graph.cost_parameter_id])
    ):
        raise ValidationError("formula materialization is not bound to authoritative source objects")


def build_counterexample_feature_receipt(
    *,
    tool_id: str,
    graph_digest: str,
    derivation_package_digest: str,
    feature_rows: Sequence[Mapping[str, float]],
    forward_returns: Sequence[float],
    baseline_actions: Sequence[float],
    observation_dates: Sequence[str],
    cost_bps: float,
    factor_spec_digests: Sequence[str] = (),
    benchmark_spec_digest: str | None = None,
    frequency: str = "counterexample",
    parameters: Mapping[str, float | int | str] | None = None,
) -> dict[str, object]:
    """Build a no-market fixture, optionally bound to registered Stage-1 objects."""

    if not feature_rows or not (len(feature_rows) == len(forward_returns) == len(baseline_actions) == len(observation_dates)):
        raise ValidationError("counterexample receipt rows are not aligned")
    rows = [{str(key): float(value) for key, value in row.items()} for row in feature_rows]
    dates = [str(value) for value in observation_dates]
    synthetic = tool_id.startswith("synthetic_")
    mode = "deterministic_counterexample_fixture" if synthetic else "deterministic_stage1_bound_counterexample_fixture"
    frozen_parameters = dict(parameters or {"cost_bps": float(cost_bps)})
    if not synthetic and (not factor_spec_digests or benchmark_spec_digest is None):
        raise ValidationError("Stage-1-bound fixture requires factor and benchmark digests")
    normalized_factor_digests = (
        [canonical_digest({"synthetic_tool": tool_id})]
        if synthetic
        else [require_digest(value, field="counterexample factor spec digest") for value in factor_spec_digests]
    )
    normalized_benchmark_digest = (
        canonical_digest({"synthetic_tool": tool_id})
        if synthetic
        else require_digest(benchmark_spec_digest, field="counterexample benchmark digest")
    )
    payload: dict[str, object] = {
        "schema_id": FEATURE_MATERIALIZATION_RECEIPT_SCHEMA_ID,
        "receipt_id": f"formula-materialization:{tool_id}:counterexample",
        "tool_id": tool_id,
        "materialization_mode": mode,
        "graph_digest": require_digest(graph_digest, field="counterexample graph digest"),
        "derivation_package_digest": require_digest(
            derivation_package_digest,
            field="counterexample derivation package digest",
        ),
        "factor_spec_digests": normalized_factor_digests,
        "benchmark_spec_digest": normalized_benchmark_digest,
        "frequency": frequency,
        "parameters": frozen_parameters,
        "parameters_digest": canonical_digest(dict(sorted(frozen_parameters.items()))),
        "dataset_ref": f"fixture://{mode}/no-market-rows",
        "dataset_sha256": canonical_digest({"fixture": tool_id}),
        "raw_kline_content_digest": canonical_digest(rows),
        "raw_kline_input_fields": list(RAW_KLINE_FIELDS),
        "row_count": len(rows),
        "sample_start_date": dates[0][:10],
        "sample_end_date": dates[-1][:10],
        "observation_dates_digest": canonical_digest(dates),
        "feature_columns": list(rows[0]),
        "feature_rows_digest": canonical_digest(rows),
        "baseline_action_digest": canonical_digest(list(map(float, baseline_actions))),
        "forward_return_digest": canonical_digest(list(map(float, forward_returns))),
        "source_adapter_equivalent": False,
        "graph_target_digest": canonical_digest(list(map(float, baseline_actions))),
        "benchmark_target_digest": canonical_digest(list(map(float, baseline_actions))),
        "graph_cost_digest": canonical_digest([0.0 for _ in baseline_actions]),
        "benchmark_cost_digest": canonical_digest([0.0 for _ in baseline_actions]),
        "graph_execution_equivalent": False,
        "signal_clock": "after_close",
        "execution_lag_bars": 1,
        "cost_bps": float(cost_bps),
        "post_2020_rows_read": 0,
        "trade_or_event_rows_persisted": 0,
        "action_detail_exposed": False,
        "production_authority": False,
        "dynamic_parameter_authority": False,
        "tool_routing_authority": False,
        "field_labels_zh": dict(RECEIPT_LABELS_ZH),
    }
    payload["provenance_binding_digest"] = _provenance_binding_digest(payload)
    payload["semantic_digest"] = canonical_digest(payload)
    validate_feature_materialization_receipt(payload)
    return payload


def validate_materialized_rows_against_receipt(
    *,
    receipt: Mapping[str, object],
    feature_rows: Sequence[Mapping[str, float]],
    forward_returns: Sequence[float],
    baseline_actions: Sequence[float],
    observation_dates: Sequence[str],
    expected_graph_digest: str,
) -> None:
    """Bind generic Stage-2/3 inputs back to their immutable receipt."""

    validate_feature_materialization_receipt(
        receipt,
        allow_frozen_digest_only=True,
    )
    if receipt.get("graph_digest") != expected_graph_digest:
        raise ValidationError("feature receipt is bound to another formula graph")
    if receipt.get("row_count") != len(feature_rows):
        raise ValidationError("feature receipt row count changed")
    canonical_rows = [{str(key): float(value) for key, value in row.items()} for row in feature_rows]
    if receipt.get("feature_rows_digest") != canonical_digest(canonical_rows):
        raise ValidationError("feature rows differ from their materialization receipt")
    if receipt.get("forward_return_digest") != canonical_digest(list(map(float, forward_returns))):
        raise ValidationError("forward returns differ from their materialization receipt")
    if receipt.get("baseline_action_digest") != canonical_digest(list(map(float, baseline_actions))):
        raise ValidationError("baseline actions differ from their materialization receipt")
    dates = tuple(str(value) for value in observation_dates)
    if receipt.get("observation_dates_digest") != canonical_digest(list(dates)):
        raise ValidationError("observation dates differ from their materialization receipt")
    if not dates or dates[-1][:10] != receipt.get("sample_end_date") or any(value[:10] > "2020-12-31" for value in dates):
        raise ValidationError("feature receipt observation boundary changed")


def _validated_bars(bars: pd.DataFrame) -> pd.DataFrame:
    if not set(RAW_KLINE_FIELDS).issubset(bars.columns):
        raise ValidationError("formula materialization raw bars are incomplete")
    frame = bars.loc[:, list(RAW_KLINE_FIELDS)].copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    for column in ("open", "high", "low", "close"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna().sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    if frame.empty or frame["timestamp"].max() >= pd.Timestamp("2021-01-01"):
        raise ValidationError("formula materialization bars cross the sealed boundary")
    if not bool((frame["close"] > 0.0).all()):
        raise ValidationError("formula materialization closes must be positive")
    return frame


def _validated_round3_rolling_bars(bars: pd.DataFrame) -> pd.DataFrame:
    if not set(RAW_KLINE_FIELDS).issubset(bars.columns):
        raise ValidationError("Round-3 rolling formula raw bars are incomplete")
    frame = bars.loc[:, list(RAW_KLINE_FIELDS)].copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    for column in ("open", "high", "low", "close"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame.isna().any().any():
        raise ValidationError("Round-3 rolling formula bars contain invalid values")
    if frame["timestamp"].duplicated().any():
        raise ValidationError("Round-3 rolling formula timestamps are duplicated")
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    if frame.empty:
        raise ValidationError("Round-3 rolling formula bars are empty")
    prices = frame.loc[:, ["open", "high", "low", "close"]]
    if not bool(prices.gt(0.0).all().all()):
        raise ValidationError("Round-3 rolling formula prices must be positive")
    if not bool(
        frame["high"].ge(prices[["open", "low", "close"]].max(axis=1)).all()
        and frame["low"].le(prices[["open", "high", "close"]].min(axis=1)).all()
    ):
        raise ValidationError("Round-3 rolling formula OHLC geometry is invalid")
    return frame


def _formula_target_from_raw(
    frame: pd.DataFrame,
    tool_id: str,
    params: Mapping[str, float | int | str],
) -> pd.Series:
    """Independently execute the frozen decision formula from raw OHLC."""

    native = _native_attributes(frame, tool_id, params)
    if tool_id in {
        "laplace_iir_mixed_bandpass",
        "butterworth_clean_bandpass",
        "rolling_fourier_bandpass",
        "causal_haar_wavelet_bandpass",
        "r3_nested_moving_average_component",
    }:
        delta_column = "r3_component_delta" if tool_id == "r3_nested_moving_average_component" else "component_direction_delta"
        return _component_direction_state(native[delta_column])
    if tool_id in {
        "laplace_iir_lowpass",
        "butterworth_lowpass_residual_envelope",
        "causal_asymmetric_arc_state_space_envelope",
    }:
        if tool_id != "laplace_iir_lowpass":
            unmasked = _lowpass_center(frame, tool_id, params, mask_source_validity=False)
            valid = _lowpass_center(frame, tool_id, params).notna()
            return cast(
                pd.Series,
                (unmasked.diff().gt(0.0) & unmasked.notna() & valid).astype(float),
            )
        return cast(pd.Series, native["lowpass_center_slope"].gt(0.0).astype(float))
    if tool_id == "simple_moving_average_trend":
        return cast(pd.Series, native["exact_sma_kernel_gap"].gt(0.0).astype(float))
    if tool_id in {
        "bollinger_volatility_channel",
        "frequency_selective_bollinger_channel",
    }:
        upper_margin = native["signed_upper_rail_margin"]
        width = native["channel_width"]
        if tool_id == "bollinger_volatility_channel":
            return _stateful_long_cash(
                upper_margin.gt(0.0),
                (upper_margin + width).lt(0.0),
                valid=upper_margin.notna() & width.notna(),
            )
        action = str(params["action"])
        if action == "trend_breakout":
            return _stateful_long_cash(
                upper_margin.gt(0.0),
                (upper_margin + 2.0 * width).lt(0.0),
                valid=upper_margin.notna() & width.notna(),
            )
        return _mean_repair_state(
            lower_margin=upper_margin + 2.0 * width,
            middle_margin=upper_margin + width,
            valid=upper_margin.notna() & width.notna(),
        )
    if tool_id == "donchian_price_channel":
        return _stateful_long_cash(
            native["donchian_entry_margin"].gt(0.0),
            native["donchian_exit_margin"].lt(0.0),
            valid=native.notna().all(axis=1),
        )
    if tool_id == "causal_trendline_channel":
        values = np.log(frame["close"].to_numpy(dtype=float))
        slope, _, rail = _rolling_ols(
            values,
            int(params["window_bars"]),
            float(params["rail_sigma"]),
        )
        slope_series = pd.Series(slope, index=frame.index)
        rail_margin = pd.Series(values - rail, index=frame.index)
        return _stateful_long_cash(
            slope_series.gt(0.0) & rail_margin.ge(0.0),
            slope_series.le(0.0) | rail_margin.lt(0.0),
            valid=slope_series.notna() & rail_margin.notna(),
        )
    raise ValidationError(f"formula target executor does not support tool {tool_id}")


def _component_direction_state(delta: pd.Series) -> pd.Series:
    signs = pd.Series(np.sign(delta.to_numpy(dtype=float)), index=delta.index)
    carried = signs.replace(0.0, np.nan).ffill().fillna(-1.0)
    return carried.gt(0.0).astype(float)


def _stateful_long_cash(
    enter: pd.Series,
    exit_: pd.Series,
    *,
    valid: pd.Series | None = None,
) -> pd.Series:
    state = False
    values: list[float] = []
    validity = valid if valid is not None else pd.Series(True, index=enter.index)
    for is_valid, should_enter, should_exit in zip(
        validity.fillna(False).to_numpy(dtype=bool),
        enter.fillna(False).to_numpy(dtype=bool),
        exit_.fillna(False).to_numpy(dtype=bool),
        strict=True,
    ):
        if not is_valid:
            state = False
        elif should_exit:
            state = False
        elif should_enter:
            state = True
        values.append(float(state))
    return pd.Series(values, index=enter.index, dtype="float64")


def _mean_repair_state(
    *,
    lower_margin: pd.Series,
    middle_margin: pd.Series,
    valid: pd.Series,
) -> pd.Series:
    holding = False
    armed = False
    values: list[float] = []
    for is_valid, below_lower, above_lower, above_middle in zip(
        valid.fillna(False).to_numpy(dtype=bool),
        lower_margin.lt(0.0).fillna(False).to_numpy(dtype=bool),
        lower_margin.ge(0.0).fillna(False).to_numpy(dtype=bool),
        middle_margin.ge(0.0).fillna(False).to_numpy(dtype=bool),
        strict=True,
    ):
        if not is_valid:
            holding = False
            armed = False
        elif not holding:
            if below_lower:
                armed = True
            elif armed and above_lower:
                holding = True
                armed = False
        elif above_middle:
            holding = False
        values.append(float(holding))
    return pd.Series(values, index=lower_margin.index, dtype="float64")


def _native_attributes(
    frame: pd.DataFrame,
    tool_id: str,
    params: Mapping[str, float | int | str],
) -> pd.DataFrame:
    if tool_id in {
        "laplace_iir_mixed_bandpass",
        "butterworth_clean_bandpass",
        "rolling_fourier_bandpass",
        "causal_haar_wavelet_bandpass",
    }:
        component = _bandpass_component(frame, tool_id, params)
        window = _window(params, 40)
        return pd.DataFrame(
            {
                "component_direction_delta": component.diff(),
                "target_band_energy": component.pow(2).rolling(window, min_periods=window).sum(),
            }
        )
    if tool_id in {
        "laplace_iir_lowpass",
        "butterworth_lowpass_residual_envelope",
        "causal_asymmetric_arc_state_space_envelope",
    }:
        center = _lowpass_center(frame, tool_id, params)
        innovation = np.log(frame["close"].astype(float)) - center
        scale = innovation.rolling(_window(params, 40), min_periods=_window(params, 40)).std(ddof=0)
        return pd.DataFrame(
            {
                "lowpass_center_slope": center.diff(),
                "normalized_innovation": innovation / scale.where(scale.abs() >= 1e-12),
            }
        )
    if tool_id == "simple_moving_average_trend":
        fast = int(params["fast_window_bars"])
        slow = int(params["slow_window_bars"])
        close = frame["close"].astype(float)
        fast_average = close.rolling(fast, min_periods=fast).mean()
        slow_average = close.rolling(slow, min_periods=slow).mean()
        path = close.diff().abs().rolling(slow, min_periods=slow).sum()
        displacement = close.diff(slow).abs()
        return pd.DataFrame(
            {
                "exact_sma_kernel_gap": fast_average - slow_average,
                "kernel_path_noise": path / displacement.where(displacement >= 1e-12),
            }
        )
    if tool_id == "r3_nested_moving_average_component":
        log_close = np.log(frame["close"].astype(float))
        fast = int(params["fast_window_bars"])
        slow = int(params["slow_window_bars"])
        component = (log_close - log_close.rolling(fast, min_periods=fast).mean()).rolling(slow, min_periods=slow).mean()
        return pd.DataFrame(
            {
                "r3_component_delta": component.diff(),
                "r3_component_energy": component.pow(2).rolling(slow, min_periods=slow).mean(),
            }
        )
    if tool_id in {"bollinger_volatility_channel", "frequency_selective_bollinger_channel"}:
        center, width, upper, valid = _volatility_geometry(frame, tool_id, params)
        price = frame["close"].astype(float) if tool_id == "bollinger_volatility_channel" else np.log(frame["close"].astype(float))
        return pd.DataFrame(
            {
                "signed_upper_rail_margin": (price - upper).where(valid),
                "channel_width": width.where(valid),
                "channel_center_direction": center.diff().where(valid),
            }
        )
    if tool_id == "donchian_price_channel":
        upper = frame["high"].rolling(int(params["entry_window_bars"]), min_periods=int(params["entry_window_bars"])).max().shift(1)
        lower = frame["low"].rolling(int(params["exit_window_bars"]), min_periods=int(params["exit_window_bars"])).min().shift(1)
        close = frame["close"].astype(float)
        return pd.DataFrame(
            {
                "donchian_entry_margin": close - upper,
                "donchian_exit_margin": close - lower,
                "donchian_channel_width": upper - lower,
            }
        )
    if tool_id == "causal_trendline_channel":
        values = np.log(frame["close"].to_numpy(dtype=float))
        slope_40, sigma_40, rail_40 = _rolling_ols(values, 40, float(params["rail_sigma"]))
        slope_160, sigma_160, _ = _rolling_ols(values, 160, float(params["rail_sigma"]))
        return pd.DataFrame(
            {
                "ols_slope_gap_40_160": slope_40 - slope_160,
                "ols_residual_scale_ratio_40_160": sigma_40 / np.where(np.abs(sigma_160) >= 1e-12, sigma_160, np.nan),
                "ols_rail_margin_40": values - rail_40,
            }
        )
    raise ValidationError(f"formula materializer does not support tool {tool_id}")


def _bandpass_component(frame: pd.DataFrame, tool_id: str, params: Mapping[str, float | int | str]) -> pd.Series:
    values = pd.Series(
        np.log(frame["close"].to_numpy(dtype=float)),
        index=pd.DatetimeIndex(frame["timestamp"]),
    )
    if tool_id == "butterworth_clean_bandpass":
        component = butterworth_bandpass_component(
            values,
            short_period_bars=int(params["short_period_bars"]),
            long_period_bars=int(params["long_period_bars"]),
            order=int(params["order"]),
        )
    else:
        if tool_id == "laplace_iir_mixed_bandpass":
            family = "laplace_iir"
            filter_params = {
                "period": float(params["period_bars"]),
                "q": float(params["q"]),
            }
        elif tool_id == "rolling_fourier_bandpass":
            family = "fourier_rolling"
            filter_params = {
                "window": int(params["window_bars"]),
                "low_period": float(params["low_period_bars"]),
                "high_period": float(params["high_period_bars"]),
            }
        else:
            family = "wavelet_haar"
            filter_params = {
                "window": int(params["window_bars"]),
                "level": int(params["level"]),
                "slow_level": int(params["slow_level"]),
            }
        component = apply_filter_spec(
            values,
            FilterSpec(
                name=f"formula-materializer:{tool_id}",
                family=family,
                mode="bandpass",
                params=filter_params,
                output_kind="component",
            ),
        )
    return pd.Series(component.to_numpy(dtype=float), index=frame.index)


def _lowpass_center(
    frame: pd.DataFrame,
    tool_id: str,
    params: Mapping[str, float | int | str],
    *,
    mask_source_validity: bool = True,
) -> pd.Series:
    if tool_id == "laplace_iir_lowpass":
        values = pd.Series(
            np.log(frame["close"].to_numpy(dtype=float)),
            index=pd.DatetimeIndex(frame["timestamp"]),
        )
        center = apply_filter_spec(
            values,
            FilterSpec(
                name="formula-materializer:laplace-iir-lowpass",
                family="laplace_iir",
                mode="lowpass",
                params={"period": float(params["period_bars"]), "q": float(params["q"])},
                output_kind="level",
            ),
        )
        return pd.Series(center.to_numpy(dtype=float), index=frame.index)
    if tool_id == "butterworth_lowpass_residual_envelope":
        spec = LowpassResidualEnvelopeSpec(
            cutoff_period_bars=int(params["cutoff_period_bars"]),
            lowpass_order=int(params["lowpass_order"]),
            thickness_window_bars=int(params["thickness_window_bars"]),
            thickness_lower_quantile=float(params["thickness_lower_quantile"]),
            thickness_upper_quantile=float(params["thickness_upper_quantile"]),
            thickness_smoothing_half_life_bars=float(params["thickness_smoothing_half_life_bars"]),
            warmup_bars=int(params["warmup_bars"]),
        )
        geometry = build_causal_lowpass_residual_envelope(frame, spec)
        values = pd.Series(geometry["lowpass_mid_log"].to_numpy(dtype=float), index=frame.index)
        valid = pd.Series(geometry["v58_geometry_valid"].to_numpy(dtype=bool), index=frame.index)
        return values.where(valid) if mask_source_validity else values
    spec = AsymmetricArcEnvelopeSpec(
        candidate_periods_bars=tuple(int(params[f"candidate_period_{index}"]) for index in range(1, 5)),
        round_top_sharp_bottom_ratio=float(params["round_top_sharp_bottom_ratio"]),
        initial_amplitude_log=float(params["initial_amplitude_log"]),
        initial_observation_sigma_log=float(params["initial_observation_sigma_log"]),
        score_half_life_bars=float(params["score_half_life_bars"]),
        model_weight_half_life_bars=float(params["model_weight_half_life_bars"]),
        model_score_temperature=float(params["model_score_temperature"]),
        observation_variance_half_life_bars=float(params["observation_variance_half_life_bars"]),
        thickness_window_bars=int(params["thickness_window_bars"]),
        thickness_lower_quantile=float(params["thickness_lower_quantile"]),
        thickness_upper_quantile=float(params["thickness_upper_quantile"]),
        thickness_smoothing_half_life_bars=float(params["thickness_smoothing_half_life_bars"]),
        warmup_bars=int(params["warmup_bars"]),
    )
    geometry = build_causal_asymmetric_arc_envelope(frame, spec)
    values = pd.Series(np.log(geometry["arc_mid"].to_numpy(dtype=float)), index=frame.index)
    valid = pd.Series(geometry["arc_geometry_valid"].to_numpy(dtype=bool), index=frame.index)
    return values.where(valid) if mask_source_validity else values


def _volatility_geometry(
    frame: pd.DataFrame, tool_id: str, params: Mapping[str, float | int | str]
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    if tool_id == "bollinger_volatility_channel":
        close = cast(pd.Series, frame["close"]).astype(float)
        window = int(params["window_bars"])
        center = cast(pd.Series, close.rolling(window, min_periods=window).mean().shift(1))
        width = cast(
            pd.Series,
            close.rolling(window, min_periods=window).std(ddof=0).shift(1),
        ) * float(params["width_sigma"])
        valid = center.notna() & width.notna()
        return center, width, center + width, valid
    close = pd.Series(
        frame["close"].to_numpy(dtype=float),
        index=pd.DatetimeIndex(frame["timestamp"]),
    )
    spec = FrequencyBollingerSpec(
        period_bars=int(params["period_bars"]),
        thickness_source=str(params["thickness_source"]),
        window_multiplier=float(params["window_multiplier"]),
        width_multiplier=float(params["width_multiplier"]),
        action=str(params["action"]),
        filter_order=int(params["filter_order"]),
        band_upper_frequency_ratio=float(params.get("band_upper_frequency_ratio", 2.0)),
    )
    geometry = build_frequency_bollinger(close, spec).reset_index(drop=True)
    return (
        cast(pd.Series, geometry["middle_log"]),
        cast(pd.Series, geometry["width_log"]),
        cast(pd.Series, geometry["upper_log"]),
        cast(pd.Series, geometry["valid"]).astype(bool),
    )


def _rolling_ols(values: np.ndarray, window: int, rail_sigma: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    slope = np.full(len(values), np.nan, dtype=float)
    residual_scale = np.full(len(values), np.nan, dtype=float)
    lower_rail = np.full(len(values), np.nan, dtype=float)
    x = np.arange(window, dtype=float)
    centered = x - x.mean()
    denominator = float(np.dot(centered, centered))
    for position in range(window, len(values)):
        history = values[position - window : position]
        mean = float(history.mean())
        beta = float(np.dot(centered, history - mean) / denominator)
        intercept = mean - beta * float(x.mean())
        fitted = intercept + beta * x
        sigma = float(np.std(history - fitted, ddof=0))
        slope[position] = beta
        residual_scale[position] = sigma
        lower_rail[position] = intercept + beta * float(window) - rail_sigma * sigma
    return slope, residual_scale, lower_rail


def _window(params: Mapping[str, float | int | str], default: int) -> int:
    for key in (
        "period_bars",
        "window_bars",
        "cutoff_period_bars",
        "warmup_bars",
        "slow_window_bars",
    ):
        if key in params:
            return max(2, min(int(params[key]), 512))
    return default


__all__ = [
    "FEATURE_MATERIALIZATION_RECEIPT_SCHEMA_ID",
    "FormulaFeatureMaterialization",
    "RAW_KLINE_FIELDS",
    "ROUND3_ROLLING_FORMULA_TOOL_IDS",
    "SourceFormulaGraphPanel",
    "build_counterexample_feature_receipt",
    "execute_source_formula_graph_panel",
    "materialize_formula_native_panel",
    "materialize_registered_formula_factor",
    "materialize_round3_rolling_formula_attributes",
    "raw_kline_content_digest_for_bars",
    "resolve_authoritative_formula_materialization_objects",
    "validate_feature_materialization_receipt",
    "validate_materialized_rows_against_receipt",
]
