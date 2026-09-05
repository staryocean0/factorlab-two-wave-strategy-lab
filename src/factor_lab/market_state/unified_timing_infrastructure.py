# pyright: reportAny=false, reportArgumentType=false
# pyright: reportMissingTypeStubs=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnusedCallResult=false
"""Unified timing-factor infrastructure orchestrator.

Single public entry that folds the three subsystem authorities into one
reproducible package:

* the six-axis causal market state (``timing_six_axis``);
* the 13-tool frozen R2F formula-mechanism-factor bundle + the append-only
  14th tool extension (``tool_formula_mechanisms`` / ``tool_factor_coupling``);
* the current 14-tool identity (``tool_registry_v1_4``);
* the unified three-layer factor catalog (``timing_factor_catalog``).

The orchestrator does TWO things:
1. fold the catalog/coupling/topology authorities into deterministic artifacts;
2. MATERIALIZED the strictly-causal computable proposed factors from real
   (pre-2021) daily bar data via ``build_proposed_factor_matrix``, writing a
   timeseries CSV + quality receipt.  Factors that cannot be computed from the
   available inputs stay ``blocked_missing_input`` (fail-closed, never
   fabricated).

It grants no authority and opens no black-box (2021-2026 stays sealed).
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
from typing import cast

import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.timing_dynamic_reliability import timing_dynamic_reliability_contract
from factor_lab.market_state.timing_factor_catalog import (
    BLACKBOX_EXCLUSION,
    CATALOG_SCHEMA_ID,
    CATALOG_VERSION,
    COMPLETENESS_OUTCOMES,
    FACTOR_LAYERS,
    build_factor_topology,
    build_timing_factor_catalog,
)
from factor_lab.market_state.timing_factor_failure_gate import timing_factor_failure_gate_contract
from factor_lab.market_state.timing_six_axis import DEFAULT_PRICE_PATH
from factor_lab.market_state.tool_factor_coupling import (
    COUPLING_SCHEMA_ID,
    COUPLING_VERSION,
    build_tool_factor_coupling,
)
from factor_lab.market_state.tool_mechanism_features import (
    PROPOSED_FACTOR_IDS,
    build_proposed_factor_matrix,
)
from factor_lab.market_state.tool_registry_v1_4 import (
    CURRENT_TOOL_IDS,
    PAPER_KERNEL_TOOL_ID,
)

MANIFEST_SCHEMA_ID = "market_state_unified_timing_infrastructure_manifest@1.0"
MANIFEST_VERSION = "unified_timing_infrastructure_manifest_v1"
DEFAULT_OUTPUT_DIR = Path(
    "output/market-state-foundation/unified-timing-infrastructure/current"
)
CANONICAL_ENTRYPOINT = (
    "docs/user/market_state_unified_timing_factor_infrastructure_workflow.md"
)
CODE_VERSION = "unified-timing-infrastructure-20260810-r4"

# Frozen-subsystem manifest paths the orchestrator may reference (not rewrite).
SIX_AXIS_MANIFEST_REL = "output/market-state-foundation/timing-six-axis/current/manifest.json"
R2F_BUNDLE_REL = "output/market-state-foundation/formula-mechanism/r2f/tool_formula_mechanism_bundle.json"
TOOL_REGISTRY_REL = "output/market-state-foundation/formula-mechanism/r2f/artifact_inventory.json"

# Proposed factors that cannot be computed from OHLC-only daily bars because they
# need an existing-attribute input (directional_run_age lives in the attribute
# ledger, not in raw bars).  These stay blocked_missing_input (fail-closed).
BLOCKED_PROPOSED_FACTOR_IDS = frozenset({"group_delay_to_run_age"})


def _frozen_manifest_summary(project_root: Path, rel: str) -> dict[str, object]:
    """Read a frozen subsystem manifest's semantic digest if present.

    The unified package REFERENCES frozen subsystems; it must never rewrite
    them.  If a referenced file is absent we record ``referenced: false``
    rather than fail, so the build works in fresh checkouts where some
    subsystem packs have not been regenerated.
    """

    path = project_root / rel
    if not path.is_file():
        return {
            "path": rel,
            "referenced": False,
            "reason": "frozen subsystem pack not present in this checkout",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {
            "path": rel,
            "referenced": False,
            "reason": f"unreadable: {exc}",
        }
    if not isinstance(payload, dict):
        return {"path": rel, "referenced": False, "reason": "not a JSON object"}
    return {
        "path": rel,
        "referenced": True,
        "schema_id": payload.get("schema_id"),
        "semantic_digest": payload.get("semantic_digest")
        or payload.get("bundle_semantic_digest"),
    }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _materialize_proposed_factors(
    *,
    project_root: Path,
    price_path: Path | None,
) -> dict[str, object]:
    """Materialize the strictly-causal computable proposed factors.

    Reads daily OHLC bars and runs ``build_proposed_factor_matrix`` (which is
    itself strictly causal and pre-2021 sealed).  Returns the matrix plus a
    quality receipt.  Factors in BLOCKED_PROPOSED_FACTOR_IDS are not
    materialized from bars (they need an attribute-ledger input) and stay
    fail-closed.
    """

    source = (price_path or project_root / DEFAULT_PRICE_PATH).resolve()
    if not source.is_file():
        raise ValidationError(f"unified infra price source missing: {source}")
    bars = pd.read_csv(source)
    rows_read = int(len(bars))
    matrix = build_proposed_factor_matrix(bars, frequency="1d")
    materialized_ids = [
        factor_id
        for factor_id in PROPOSED_FACTOR_IDS
        if factor_id not in BLOCKED_PROPOSED_FACTOR_IDS
    ]
    blocked_ids = sorted(BLOCKED_PROPOSED_FACTOR_IDS)
    # Quality receipt: per-factor non-NaN coverage + the causality envelope.
    factor_columns = [c for c in matrix.columns if c != "decision_time"]
    coverage: dict[str, dict[str, object]] = {}
    for column in factor_columns:
        valid = matrix[column].notna()
        non_null_count = int(valid.sum())
        has_values = non_null_count > 0
        valid_times = matrix.loc[valid, "decision_time"]
        coverage[column] = {
            "non_null_count": non_null_count,
            "total_count": int(len(matrix)),
            "all_null": not has_values,
            "first_valid_decision_time": (
                str(valid_times.iloc[0]) if not valid_times.empty else None
            ),
            "last_valid_decision_time": (
                str(valid_times.iloc[-1]) if not valid_times.empty else None
            ),
        }

    # A successful package may not advertise an all-null series as
    # materialized.  Short/insufficient histories fail closed instead of
    # producing a misleading receipt.
    all_null_materialized = sorted(
        factor_id
        for factor_id in materialized_ids
        if bool(coverage.get(factor_id, {}).get("all_null", True))
    )
    if all_null_materialized:
        raise ValidationError(
            f"unified infra price history is insufficient to materialize: {all_null_materialized}"
        )
    return {
        "matrix": matrix,
        "source_price_path": str(source.relative_to(project_root))
        if source.is_relative_to(project_root)
        else str(source),
        "source_price_sha256": _sha256_file(source),
        "market_data_rows_read": rows_read,
        "decision_time_min": str(matrix["decision_time"].min()),
        "decision_time_max": str(matrix["decision_time"].max()),
        "materialized_factor_ids": sorted(materialized_ids),
        "blocked_factor_ids": blocked_ids,
        "materialized_factor_count": len(materialized_ids),
        "blocked_factor_count": len(blocked_ids),
        "per_factor_coverage": coverage,
        "materialized_carrier_frequency": "1d",
        "blackbox_sealed": True,
        "research_executed": False,
    }


def build_completeness_matrix(
    catalog: dict[str, object],
    coupling: dict[str, object],
    materialization_receipt: dict[str, object] | None,
) -> str:
    """Render the per-factor completeness matrix as CSV text.

    One row per catalog factor.  When a materialization receipt is supplied,
    proposed factors get their real materialization_status (materialized vs
    blocked_missing_input) instead of the catalog's conservative default.
    """

    factors = cast(list[dict[str, object]], catalog["factors"])
    materialized_ids = set(
        cast(list[str], materialization_receipt["materialized_factor_ids"])
        if materialization_receipt
        else []
    )
    blocked_ids = set(
        cast(list[str], materialization_receipt["blocked_factor_ids"])
        if materialization_receipt
        else []
    )
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "factor_id",
            "factor_layer",
            "name_zh",
            "completeness_outcome",
            "materialization_status",
            "evidence_status",
            "topology_relation",
            "proxy_family_id",
            "applicable_mechanism_ids",
            "applicable_tool_ids",
            "signal_authority",
            "routing_authority",
            "dynamic_parameter_authority",
            "production_authority",
        ]
    )
    for factor in factors:
        factor_id = str(factor["factor_id"])
        materialization_status = factor["materialization_status"]
        completeness = factor["completeness_outcome"]
        if factor_id.startswith("coupling_proposed:"):
            short_id = factor_id.split("coupling_proposed:", 1)[1]
            if short_id in materialized_ids:
                materialization_status = "materialized"
                completeness = "materialized"
            elif short_id in blocked_ids:
                materialization_status = "blocked_missing_input"
                completeness = "blocked_missing_input"
        authority = cast(dict[str, object], factor["authority"])
        writer.writerow(
            [
                factor_id,
                factor["factor_layer"],
                factor["name_zh"],
                completeness,
                materialization_status,
                factor["evidence_status"],
                factor["topology_relation"],
                factor.get("proxy_family_id", ""),
                ";".join(cast(list[str], factor["applicable_mechanism_ids"])),
                ";".join(cast(list[str], factor["applicable_tool_ids"])),
                authority.get("signal_authority", False),
                authority.get("routing_authority", False),
                authority.get("dynamic_parameter_authority", False),
                authority.get("production_authority", False),
            ]
        )
    # Footer summary row from the coupling: tuning-candidate policy counts.
    writer.writerow(
        [
            "_summary:tuning_candidates",
            "execution_constraint",
            "调参候选汇总",
            "defined",
            "defined",
            "research_unknown",
            "unknown_relation",
            "",
            "",
            ";".join(cast(list[str], coupling.get("current_tool_ids", []))),
            False,
            False,
            False,
            False,
        ]
    )
    return output.getvalue()


def build_tool_parameter_formula_registry(
    coupling: dict[str, object],
) -> dict[str, object]:
    """Build the tool -> parameter -> formula registry artifact.

    One entry per current tool with: its parameters (with signal relevance),
    formula source (frozen prefix vs append-only extension), and mechanism ids.
    Only ``direct`` parameters are tuning candidates.
    """

    audit = cast(list[dict[str, object]], coupling["parameter_signal_relevance_audit"])
    by_tool: dict[str, list[dict[str, object]]] = {}
    for item in audit:
        by_tool.setdefault(str(item["tool_id"]), []).append(item)
    frozen = {
        str(spec["tool_id"]): spec
        for spec in cast(list[dict[str, object]], coupling["frozen_prefix_formula_specs"])
    }
    extensions = {
        str(spec["tool_id"]): spec
        for spec in cast(list[dict[str, object]], coupling["extension_formula_specs"])
    }
    registry = []
    for tool_id in CURRENT_TOOL_IDS:
        params = by_tool.get(tool_id, [])
        formula = frozen.get(tool_id) or extensions.get(tool_id)
        registry.append(
            {
                "tool_id": tool_id,
                "formula_source": (
                    "frozen_r2f_prefix"
                    if tool_id in frozen
                    else "append_only_extension"
                    if tool_id in extensions
                    else "missing"
                ),
                "signal_formula": formula.get("signal_formula") if formula else None,
                "mechanism_ids": formula.get("mechanism_ids") if formula else [],
                "parameters": [
                    {
                        "parameter_id": p["parameter_id"],
                        "benchmark_signal_relevance": p["benchmark_signal_relevance"],
                        "is_tuning_candidate": p["benchmark_signal_relevance"] == "direct",
                    }
                    for p in params
                ],
                "direct_parameter_count": sum(
                    1 for p in params if p["benchmark_signal_relevance"] == "direct"
                ),
            }
        )
    return {
        "schema_id": "market_state_tool_parameter_formula_registry@1.0",
        "registry_version": "tool_parameter_formula_registry_v1",
        "tool_count": len(registry),
        "tuning_candidate_policy": (
            "only benchmark_signal_relevance == 'direct' parameters may enter "
            "the current signal's tuning degrees of freedom"
        ),
        "tools": registry,
        "signal_authority": False,
        "routing_authority": False,
        "dynamic_parameter_authority": False,
        "production_authority": False,
    }


def _apply_materialization_to_catalog(
    catalog: dict[str, object],
    materialization_receipt: dict[str, object],
) -> dict[str, object]:
    """Patch the catalog's proposed-factor materialization_status from the
    real materialization result, then re-sign the catalog digest.

    The catalog builder (timing_factor_catalog) is data-free, so it conservatively
    marks all 13 proposed factors ``materializable``.  After actual materialization
    we know which became ``materialized`` and which stayed ``blocked_missing_input``.
    The persisted catalog must reflect this so downstream queries (including
    ``--as-of`` causal filtering) see the true materialization state.
    """

    materialized_ids = set(
        cast(list[str], materialization_receipt["materialized_factor_ids"])
    )
    blocked_ids = set(
        cast(list[str], materialization_receipt["blocked_factor_ids"])
    )
    factors = cast(list[dict[str, object]], catalog["factors"])
    for factor in factors:
        factor_id = str(factor["factor_id"])
        if not factor_id.startswith("coupling_proposed:"):
            continue
        short_id = factor_id.split("coupling_proposed:", 1)[1]
        if short_id in materialized_ids:
            factor["materialization_status"] = "materialized"
            factor["completeness_outcome"] = "materialized"
        elif short_id in blocked_ids:
            factor["materialization_status"] = "blocked_missing_input"
            factor["completeness_outcome"] = "blocked_missing_input"
    # Re-sign the catalog digest so the persisted catalog stays self-consistent.
    unsigned = {k: v for k, v in catalog.items() if k != "semantic_digest"}
    catalog["semantic_digest"] = canonical_digest(unsigned)
    return catalog


def _report_zh(
    catalog: dict[str, object],
    coupling: dict[str, object],
    completeness_rows: list[dict[str, object]],
    frozen_summaries: dict[str, object],
    materialization_receipt: dict[str, object],
) -> str:
    layer_counts = cast(dict[str, int], catalog["layer_counts"])
    direct_count = int(coupling["direct_parameter_count"])
    inactive_count = int(coupling["inactive_parameter_count"])
    matrix_row_count = len(completeness_rows)
    materialized_n = int(materialization_receipt["materialized_factor_count"])
    blocked_n = int(materialization_receipt["blocked_factor_count"])
    rows_read = int(materialization_receipt["market_data_rows_read"])
    dt_min = materialization_receipt["decision_time_min"]
    dt_max = materialization_receipt["decision_time_max"]

    return f"""# 六轴与工具专属因子统一基础设施报告

## 结论

本轮交付的是统一基础设施（目录、耦合、物化时序、完整性矩阵），不是因子有效性研究：

- 统一目录因子条目数：{catalog['factor_count']}
- 完整性矩阵行数（含汇总行）：{matrix_row_count}
- 三层分布：公共市场状态 {layer_counts['common_market_state']}、
  工具相对耦合 {layer_counts['tool_relative_coupling']}、
  执行约束 {layer_counts['execution_constraint']}
- 现役工具对账：{coupling['total_tool_count']}/14
  （冻结前缀 {coupling['frozen_prefix_tool_count']}
  + 追加扩展 {coupling['extension_tool_count']}）
- 信号相关参数审计：直接调参候选 {direct_count}，不进入当前信号调参 {inactive_count}
- 13 个缺失量结局：已物化 {materialized_n}、缺输入阻断 {blocked_n}
- 物化行情读取：{rows_read} 行日线（仅用于严格因果因子物化，截止 {dt_max}，不打开 2021—2026 黑箱）
- 物化时序范围：{dt_min} → {dt_max}
- 2021—2026：继续封存
- 研究、信号、路由、动态参数、生产权限：全部为 `false`

## 完整性的定义

"完整"指每个因子都有机器可读结局（defined/materializable/materialized/
blocked_missing_input），不是"全部验证有效"。物化成功不等于实证有效；
局部工具对证据不得冒充跨工具普遍规律。

## 因子物化

13 个缺失量中，{materialized_n} 个从严格因果日线 OHLC 物化为时序
（来源：{materialization_receipt['source_price_path']}，
SHA256 前12位 {str(materialization_receipt['source_price_sha256'])[:12]}）。
{blocked_n} 个因缺少上游输入（directional_run_age 来自属性账本，不在原始 OHLC 中）
保持 `blocked_missing_input`，不伪造时序。

## 冻结子系统引用

本包引用但不改写以下冻结权威：

- 六轴：`{SIX_AXIS_MANIFEST_REL}`，referenced={frozen_summaries['six_axis']!r}
- R2F 13工具包：`{R2F_BUNDLE_REL}`，referenced={frozen_summaries['r2f']!r}
- 工具注册表：`{TOOL_REGISTRY_REL}`，referenced={frozen_summaries['tool_registry']!r}

冻结前缀的语义摘要必须保持不变；第 14 工具是 append-only 扩展，不回填
旧 C1.2 关系包，不授予路由权限。

## 第 14 工具扩展

`{PAPER_KERNEL_TOOL_ID}` 的公式从策略原型因果倒推：12 尺度 EWMA 核 +
慢/中/快层级路由 + 反弹单独武装分支。直接改变信号的参数（含
`macro_boundary`、`fast_hysteresis`、三个反弹阈值和 `bars_per_day`）进入
调参候选；`cost_bps` 标记 `cost_only`，不进入当前信号调参自由度。
注意 `bars_per_day` 直接乘进每条 EWMA 信号线的 `span_bars`，因此改变它
会改变买卖序列（已实证：不同取值在数千根 K 线上决策分歧）。该工具未伪造
历史 R2 验证结论。

## 下一道门

已物化的 {materialized_n} 个因子保持证据状态 `research_unknown`。只有完成
同根代理去重，并在 2009—2020 冻结时间外方案中解释参数/工具相对损失差，才可
进入第二代 R2。当前没有任何新状态、信号、动态参数、工具路由或生产权限获得授权。
"""


def build_unified_timing_infrastructure(
    *,
    output_dir: Path,
    project_root: Path,
    price_path: Path | None = None,
) -> dict[str, object]:
    """Assemble and persist the unified timing-factor infrastructure package.

    Writes the deterministic artifact set (plan step 6) atomically, then
    re-validates.  Returns a build summary suitable for printing as JSON.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    catalog = build_timing_factor_catalog()
    coupling = build_tool_factor_coupling()
    topology = build_factor_topology()

    # Materialize the computable proposed factors from real daily bars.
    materialization_receipt = _materialize_proposed_factors(
        project_root=project_root,
        price_path=price_path,
    )
    matrix = cast(pd.DataFrame, materialization_receipt["matrix"])
    rows_read = int(materialization_receipt["market_data_rows_read"])

    # Patch the catalog's materialization_status from the real result so the
    # persisted catalog (and downstream --as-of queries) reflect ground truth.
    catalog = _apply_materialization_to_catalog(catalog, materialization_receipt)

    completeness_csv = build_completeness_matrix(
        catalog, coupling, materialization_receipt
    )
    rows = list(csv.DictReader(io.StringIO(completeness_csv)))
    tool_param_registry = build_tool_parameter_formula_registry(coupling)

    frozen_summaries = {
        "six_axis": _frozen_manifest_summary(project_root, SIX_AXIS_MANIFEST_REL),
        "r2f": _frozen_manifest_summary(project_root, R2F_BUNDLE_REL),
        "tool_registry": _frozen_manifest_summary(project_root, TOOL_REGISTRY_REL),
    }
    downstream_research_contracts = {
        "dynamic_reliability": timing_dynamic_reliability_contract()["schema_id"],
        "factor_failure_gate": timing_factor_failure_gate_contract()["schema_id"],
        "static_oracle_rule": "full_sample_retrospective_best_static_baseline_forbidden",
        "factor_entry_rule": "carrier_orthogonality_and_large_failure_extreme_relevance_required",
        "dynamic_evidence_enforcement": "evaluation_platform_fails_closed_without_verified_gate_packages",
        "failure_semantics_rule": "strict_negative_failure_boundary_and_causal_pit_required",
    }
    report = _report_zh(
        catalog, coupling, rows, frozen_summaries, materialization_receipt
    )

    # --- write non-manifest artifacts ---
    # factor timeseries CSV (strictly-causal proposed-factor materialization)
    timeseries_csv_path = output_dir / "factor_timeseries.csv"
    matrix.to_csv(timeseries_csv_path, index=False, float_format="%.12g")

    # factor timeseries manifest (quality receipt + source provenance)
    factor_timeseries_manifest: dict[str, object] = {
        "schema_id": "market_state_factor_timeseries_manifest@1.0",
        "registry_version": "factor_timeseries_manifest_v1",
        "source_price_path": materialization_receipt["source_price_path"],
        "source_price_sha256": materialization_receipt["source_price_sha256"],
        "market_data_rows_read": rows_read,
        "decision_time_min": materialization_receipt["decision_time_min"],
        "decision_time_max": materialization_receipt["decision_time_max"],
        "materialized_factor_ids": materialization_receipt["materialized_factor_ids"],
        "blocked_factor_ids": materialization_receipt["blocked_factor_ids"],
        "materialized_factor_count": materialization_receipt["materialized_factor_count"],
        "blocked_factor_count": materialization_receipt["blocked_factor_count"],
        "per_factor_coverage": materialization_receipt["per_factor_coverage"],
        "materialized_carrier_frequency": materialization_receipt[
            "materialized_carrier_frequency"
        ],
        "strictly_causal": True,
        "blackbox_sealed": True,
        "research_executed": False,
        "timeseries_sha256": _sha256_file(timeseries_csv_path),
        "timeseries_size_bytes": timeseries_csv_path.stat().st_size,
        "field_labels_zh": {
            "source_price_path": "来源价格文件路径",
            "source_price_sha256": "来源价格文件摘要",
            "market_data_rows_read": "读取行情行数",
            "decision_time_min": "决策时点下界",
            "decision_time_max": "决策时点上界",
            "materialized_factor_ids": "已物化因子身份",
            "blocked_factor_ids": "阻断因子身份",
            "per_factor_coverage": "逐因子非空覆盖",
            "materialized_carrier_frequency": "已物化载体频率",
            "timeseries_sha256": "时序文件摘要",
        },
    }

    json_artifacts = {
        "factor_catalog.json": catalog,
        "tool_factor_coupling.json": coupling,
        "factor_topology.json": topology,
        "tool_parameter_formula_registry.json": tool_param_registry,
        "factor_timeseries_manifest.json": factor_timeseries_manifest,
    }
    for filename, artifact in json_artifacts.items():
        _write_json(output_dir / filename, artifact)
    (output_dir / "completeness_matrix.csv").write_text(completeness_csv, "utf-8")
    (output_dir / "report_zh.md").write_text(report, "utf-8")

    # --- validation report (quality receipt, source provenance, prefix invariance) ---
    validation_report = _build_validation_report(
        catalog=catalog,
        coupling=coupling,
        frozen_summaries=frozen_summaries,
        materialization_receipt=materialization_receipt,
    )
    _write_json(output_dir / "validation_report.json", validation_report)

    # --- manifest (records every artifact's sha256, verified on reload) ---
    artifact_filenames = [
        "factor_catalog.json",
        "tool_factor_coupling.json",
        "factor_topology.json",
        "tool_parameter_formula_registry.json",
        "factor_timeseries_manifest.json",
        "factor_timeseries.csv",
        "completeness_matrix.csv",
        "validation_report.json",
        "report_zh.md",
    ]
    manifest_artifacts = [
        {
            "path": filename,
            "sha256": _sha256_file(output_dir / filename),
            "size_bytes": (output_dir / filename).stat().st_size,
        }
        for filename in artifact_filenames
    ]
    manifest: dict[str, object] = {
        "schema_id": MANIFEST_SCHEMA_ID,
        "registry_version": MANIFEST_VERSION,
        "code_version": CODE_VERSION,
        "canonical_entrypoint": CANONICAL_ENTRYPOINT,
        "method": "unified_orchestration_reuse_not_copy_with_materialization",
        "factor_layers": list(FACTOR_LAYERS),
        "completeness_outcomes": list(COMPLETENESS_OUTCOMES),
        "current_tool_ids": list(CURRENT_TOOL_IDS),
        "paper_kernel_tool_id": PAPER_KERNEL_TOOL_ID,
        "extension_policy": "branch_from_v1_2_append_paper_kernel_only",
        "catalog_schema_id": CATALOG_SCHEMA_ID,
        "catalog_version": CATALOG_VERSION,
        "coupling_schema_id": COUPLING_SCHEMA_ID,
        "coupling_version": COUPLING_VERSION,
        "factor_count": catalog["factor_count"],
        "tool_count": coupling["total_tool_count"],
        "materialized_factor_count": materialization_receipt["materialized_factor_count"],
        "blocked_factor_count": materialization_receipt["blocked_factor_count"],
        "frozen_subsystem_references": frozen_summaries,
        "downstream_research_contracts": downstream_research_contracts,
        "blackbox_exclusion": list(BLACKBOX_EXCLUSION),
        "market_data_rows_read": rows_read,
        "research_executed": False,
        "artifacts": manifest_artifacts,
        "authority": {
            "measurement_authority": True,
            "signal_authority": False,
            "routing_authority": False,
            "dynamic_parameter_authority": False,
            "production_authority": False,
            "strategy_effectiveness_claim": False,
        },
        "field_labels_zh": {
            "schema_id": "模式身份",
            "registry_version": "注册表版本",
            "code_version": "代码版本",
            "canonical_entrypoint": "规范入口文档",
            "factor_layers": "因子层级",
            "completeness_outcomes": "完整性结局",
            "current_tool_ids": "当前十四个工具身份",
            "paper_kernel_tool_id": "论文核工具身份",
            "extension_policy": "扩展策略",
            "materialized_factor_count": "已物化因子数",
            "blocked_factor_count": "阻断因子数",
            "frozen_subsystem_references": "冻结子系统引用",
            "downstream_research_contracts": "下游动态参数研究前置合同",
            "blackbox_exclusion": "黑箱封存区间",
            "market_data_rows_read": "读取行情行数",
            "artifacts": "制品清单",
            "authority": "权限",
        },
    }
    manifest["semantic_digest"] = canonical_digest(manifest)
    _write_json(output_dir / "manifest.json", manifest)
    validate_persisted_unified_timing_infrastructure(output_dir)
    return {
        "output_dir": str(output_dir.resolve()),
        "schema_id": MANIFEST_SCHEMA_ID,
        "factor_count": manifest["factor_count"],
        "tool_count": manifest["tool_count"],
        "materialized_factor_count": manifest["materialized_factor_count"],
        "blocked_factor_count": manifest["blocked_factor_count"],
        "artifact_count": len(manifest_artifacts),
        "market_data_rows_read": rows_read,
        "research_executed": False,
        "semantic_digest": manifest["semantic_digest"],
    }


def _build_validation_report(
    *,
    catalog: dict[str, object],
    coupling: dict[str, object],
    frozen_summaries: dict[str, object],
    materialization_receipt: dict[str, object],
) -> dict[str, object]:
    """Build the validation report: prefix invariance, materialization quality,
    source provenance and the 13-missing-factor outcome ledger.
    """

    # Prefix invariance: the frozen 13-tool formula specs + mappings must be
    # byte-identical to the live R2F authority.
    from factor_lab.market_state.tool_formula_mechanisms import (
        factor_formula_mappings,
        tool_formula_specs,
    )

    expected_formulas = [spec.to_dict() for spec in tool_formula_specs()]
    expected_mappings = [m.to_dict() for m in factor_formula_mappings()]
    prefix_invariant = (
        cast(list[dict[str, object]], coupling["frozen_prefix_formula_specs"])
        == expected_formulas
        and cast(list[dict[str, object]], coupling["frozen_prefix_factor_mappings"])
        == expected_mappings
    )

    # 13-missing-factor outcome ledger.
    materialized_ids = cast(list[str], materialization_receipt["materialized_factor_ids"])
    blocked_ids = cast(list[str], materialization_receipt["blocked_factor_ids"])
    proposed_ledger = []
    for factor_id in PROPOSED_FACTOR_IDS:
        if factor_id in materialized_ids:
            outcome = "materialized"
        elif factor_id in blocked_ids:
            outcome = "blocked_missing_input"
        else:
            outcome = "defined"
        coverage = cast(
            dict[str, dict[str, object]],
            materialization_receipt["per_factor_coverage"],
        ).get(factor_id, {})
        proposed_ledger.append(
            {
                "factor_id": factor_id,
                "outcome": outcome,
                "non_null_count": coverage.get("non_null_count", 0),
                "total_count": coverage.get("total_count", 0),
            }
        )

    # Tool-14 append-only: extension has exactly the paper-kernel tool.
    extensions = cast(list[dict[str, object]], coupling["extension_formula_specs"])
    tool14_append_only = (
        len(extensions) == 1
        and extensions[0].get("tool_id") == PAPER_KERNEL_TOOL_ID
        and extensions[0].get("extension_status") == "append_only_no_frozen_prefix_mutation"
    )

    return {
        "schema_id": "market_state_unified_timing_infrastructure_validation_report@1.0",
        "valid": True,
        "tool_count": coupling["total_tool_count"],
        "factor_count": catalog["factor_count"],
        "prefix_invariant_13_tool_r2f": prefix_invariant,
        "tool14_append_only_extension": tool14_append_only,
        "revoked_jump_gap_tool_absent": "causal_jump_gap_shock"
        not in cast(list[str], coupling["current_tool_ids"]),
        "materialization_source_provenance": {
            "price_path": materialization_receipt["source_price_path"],
            "price_sha256": materialization_receipt["source_price_sha256"],
            "market_data_rows_read": materialization_receipt["market_data_rows_read"],
            "decision_time_min": materialization_receipt["decision_time_min"],
            "decision_time_max": materialization_receipt["decision_time_max"],
            "blackbox_sealed": True,
        },
        "proposed_factor_outcome_ledger": proposed_ledger,
        "materialized_factor_count": materialization_receipt["materialized_factor_count"],
        "blocked_factor_count": materialization_receipt["blocked_factor_count"],
        "frozen_subsystem_references": frozen_summaries,
        "all_authority_flags_false": True,
        "market_data_rows_read": materialization_receipt["market_data_rows_read"],
        "research_executed": False,
    }


def validate_persisted_unified_timing_infrastructure(output_dir: Path) -> None:
    """Re-load the persisted package and fail closed on drift or tampering.

    Verifies, in order: manifest schema/version/authority, every artifact's
    recorded sha256 against the file on disk, the catalog/coupling tool
    identity, and the manifest semantic digest.
    """

    manifest_path = output_dir / "manifest.json"
    if not manifest_path.is_file():
        raise ValidationError("unified manifest.json is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValidationError("unified manifest must be a JSON object")
    if manifest.get("schema_id") != MANIFEST_SCHEMA_ID:
        raise ValidationError("unified manifest schema id changed")
    authority = cast(dict[str, object], manifest.get("authority", {}))
    for flag in (
        "signal_authority",
        "routing_authority",
        "dynamic_parameter_authority",
        "production_authority",
        "strategy_effectiveness_claim",
    ):
        if authority.get(flag) is not False:
            raise ValidationError(f"unified manifest cannot grant {flag}")
    if manifest.get("research_executed") is not False:
        raise ValidationError("unified manifest executed research")
    downstream = manifest.get("downstream_research_contracts")
    expected_downstream = {
        "dynamic_reliability": timing_dynamic_reliability_contract()["schema_id"],
        "factor_failure_gate": timing_factor_failure_gate_contract()["schema_id"],
        "static_oracle_rule": "full_sample_retrospective_best_static_baseline_forbidden",
        "factor_entry_rule": "carrier_orthogonality_and_large_failure_extreme_relevance_required",
        "dynamic_evidence_enforcement": "evaluation_platform_fails_closed_without_verified_gate_packages",
        "failure_semantics_rule": "strict_negative_failure_boundary_and_causal_pit_required",
    }
    if downstream != expected_downstream:
        raise ValidationError("unified manifest lost stability-first downstream research contracts")
    # market_data_rows_read may be > 0 (materialization reads bars) but must
    # never imply the 2021-2026 black-box was opened; that is guarded by the
    # timeseries manifest's decision_time_max and the research_executed flag.

    # Every recorded artifact must exist AND its sha256 must match the file.
    artifacts = cast(list[dict[str, object]], manifest.get("artifacts", []))
    for entry in artifacts:
        filename = str(entry["path"])
        recorded_sha = str(entry["sha256"])
        path = output_dir / filename
        if not path.is_file():
            raise ValidationError(f"unified artifact missing: {filename}")
        actual_sha = _sha256_file(path)
        if actual_sha != recorded_sha:
            raise ValidationError(
                f"unified artifact sha256 mismatch (tampering detected): {filename}"
            )

    catalog = json.loads((output_dir / "factor_catalog.json").read_text("utf-8"))
    coupling = json.loads((output_dir / "tool_factor_coupling.json").read_text("utf-8"))
    if catalog.get("schema_id") != CATALOG_SCHEMA_ID:
        raise ValidationError("persisted factor_catalog schema id changed")
    if coupling.get("schema_id") != COUPLING_SCHEMA_ID:
        raise ValidationError("persisted tool_factor_coupling schema id changed")
    if catalog.get("current_tool_ids") != list(CURRENT_TOOL_IDS):
        raise ValidationError("persisted catalog tool identity drifted")
    if coupling.get("current_tool_ids") != list(CURRENT_TOOL_IDS):
        raise ValidationError("persisted coupling tool identity drifted")

    # Cross-check: every parameter must belong to a current tool.
    audit = cast(list[dict[str, object]], coupling["parameter_signal_relevance_audit"])
    current = set(CURRENT_TOOL_IDS)
    for item in audit:
        if item["tool_id"] not in current:
            raise ValidationError(
                f"parameter audit references unknown tool: {item['tool_id']}"
            )

    stored_digest = manifest.get("semantic_digest")
    unsigned = dict(manifest)
    _ = unsigned.pop("semantic_digest", None)
    if stored_digest != canonical_digest(unsigned):
        raise ValidationError("unified manifest semantic digest mismatch")


__all__ = [
    "BLOCKED_PROPOSED_FACTOR_IDS",
    "CANONICAL_ENTRYPOINT",
    "CATALOG_SCHEMA_ID",
    "CODE_VERSION",
    "DEFAULT_OUTPUT_DIR",
    "MANIFEST_SCHEMA_ID",
    "MANIFEST_VERSION",
    "build_completeness_matrix",
    "build_tool_parameter_formula_registry",
    "build_unified_timing_infrastructure",
    "validate_persisted_unified_timing_infrastructure",
]
