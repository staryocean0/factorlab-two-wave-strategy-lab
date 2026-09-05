# pyright: reportAny=false, reportArgumentType=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
"""Current 14-tool registry view with the paper-kernel trend router.

V1.4 deliberately branches from the frozen V1.2 13-tool prefix.  It does not
inherit the historical V1.3 jump/gap specialist, whose independent routing
responsibility was revoked.  Registration provides identity and a runnable
comparison probe; it grants no priority, dynamic-parameter, or production
authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import cast

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.method_registry import method_family_specs
from factor_lab.market_state.tool_registry import (
    DISCOVERED_TOOL_IDS,
    REQUIRED_ACTION_ROLES,
    REQUIRED_EFFECT_METRICS,
    ToolSpec,
    build_tool_registry_payload,
)
from factor_lab.strategy.services.risk_off_paper_kernel_hierarchical_trend_v1 import (
    PaperKernelHierarchicalTrendV1Spec,
    build_paper_kernel_intraday_scale_state,
    paper_kernel_hierarchical_trend_v1_contract,
    route_paper_kernel_hierarchical_trend_v1,
)

PAPER_KERNEL_TOOL_ID = "paper_kernel_multiscale_trend_router"
TOOL_REGISTRY_V1_4_SCHEMA_ID = "market_state_tool_registry@1.4"
TOOL_REGISTRY_V1_4_VERSION = "tool_registry_v1_4"
CURRENT_TOOL_IDS = DISCOVERED_TOOL_IDS + (PAPER_KERNEL_TOOL_ID,)


@dataclass(frozen=True, slots=True)
class PaperKernelBenchmarkSpec:
    """Native 15-minute benchmark for the appended paper-kernel tool."""

    benchmark_id: str
    tool_id: str
    method_family_id: str
    name_zh: str
    signal_semantics: str
    parameters_by_frequency: MappingProxyType[str, MappingProxyType[str, float | int]]
    action_roles: tuple[str, ...] = REQUIRED_ACTION_ROLES
    effect_metric_ids: tuple[str, ...] = REQUIRED_EFFECT_METRICS
    comparator_method_id: str = "cash_zero_return"
    production_authority: bool = False

    def __post_init__(self) -> None:
        if self.tool_id != PAPER_KERNEL_TOOL_ID:
            raise ValidationError("V1.4 benchmark must belong to the paper-kernel tool")
        if self.method_family_id != "hybrid_router":
            raise ValidationError("paper-kernel tool must use the hybrid-router family")
        if set(self.parameters_by_frequency) != {"15m"}:
            raise ValidationError("paper-kernel benchmark is native 15m only")
        if tuple(self.action_roles) != REQUIRED_ACTION_ROLES:
            raise ValidationError("paper-kernel action roles are incomplete")
        if tuple(self.effect_metric_ids) != REQUIRED_EFFECT_METRICS:
            raise ValidationError("paper-kernel effect metrics are incomplete")
        if self.production_authority:
            raise ValidationError("registry benchmark cannot grant production authority")

    def to_dict(self) -> dict[str, object]:
        return {
            "benchmark_id": self.benchmark_id,
            "tool_id": self.tool_id,
            "method_family_id": self.method_family_id,
            "name_zh": self.name_zh,
            "signal_semantics": self.signal_semantics,
            "parameters_by_frequency": {
                frequency: dict(values)
                for frequency, values in sorted(self.parameters_by_frequency.items())
            },
            "action_roles": list(self.action_roles),
            "effect_metric_ids": list(self.effect_metric_ids),
            "comparator_method_id": self.comparator_method_id,
            "production_authority": self.production_authority,
        }


def paper_kernel_tool_spec() -> ToolSpec:
    """Return the reusable identity of the paper-kernel trend tool."""

    return ToolSpec(
        tool_id=PAPER_KERNEL_TOOL_ID,
        tool_category_id="trend",
        method_family_id="hybrid_router",
        name_zh="论文核多尺度趋势路由",
        aliases=("论文EWMA核", "十二尺度趋势", "paper-kernel trend"),
        mathematical_object=(
            "causal normalized-return EWMA bank with slow/middle/fast hierarchical routing"
        ),
        input_semantics="15m close through the closed decision bar",
        output_semantics=(
            "macro up/flat/down state plus next-bar long/cash decision; "
            "macro-down permits only a separately armed fast rebound"
        ),
        supported_action_roles=REQUIRED_ACTION_ROLES,
        benchmark_status="benchmarked",
        status_reason="",
        source_strategy_refs=(
            "src/factor_lab/strategy/services/risk_off_paper_kernel_hierarchical_trend_v1.py",
            "src/factor_lab/strategy/services/risk_off_paper_kernel_native_trend.py",
            "src/factor_lab/cloudridge/paper_kernel.py",
        ),
    )


def paper_kernel_benchmark_spec() -> PaperKernelBenchmarkSpec:
    spec = PaperKernelHierarchicalTrendV1Spec()
    parameters = MappingProxyType(
        {
            "15m": MappingProxyType(
                {
                    "bars_per_day": spec.bars_per_day,
                    "macro_boundary": spec.macro_boundary,
                    "fast_hysteresis": spec.fast_hysteresis,
                    "rebound_oversold_strength": spec.rebound_oversold_strength,
                    "rebound_entry_score": spec.rebound_entry_score,
                    "rebound_failure_score": spec.rebound_failure_score,
                    "cost_bps": 7.0,
                }
            )
        }
    )
    return PaperKernelBenchmarkSpec(
        benchmark_id="paper_kernel_multiscale_trend_router_benchmark_v1",
        tool_id=PAPER_KERNEL_TOOL_ID,
        method_family_id="hybrid_router",
        name_zh="15分钟论文核多尺度趋势路由基准",
        signal_semantics=(
            "causal twelve-scale normalized-return EWMA; decide at close and execute next bar"
        ),
        parameters_by_frequency=parameters,
    )


def paper_kernel_tool_contract() -> dict[str, object]:
    """Translate the strategy prototype into a strategy-neutral tool contract."""

    source = dict(paper_kernel_hierarchical_trend_v1_contract())
    return {
        "schema_id": "market_state_paper_kernel_multiscale_trend_tool@1.0",
        "tool_id": PAPER_KERNEL_TOOL_ID,
        "source_prototype_contract": source,
        "observable_states": ["macro_up", "macro_flat", "macro_down", "unavailable"],
        "consumer_lenses": {
            "upside_capture": "consume long decisions and upward state labels",
            "downside_protection": "consume cash decisions and downward state labels",
        },
        "architecture_status": "provisional_tool_not_priority_locked",
        "runtime_uses_future": False,
        "production_authority": False,
        "dynamic_parameter_authority": False,
        "tool_routing_authority": False,
    }


def build_tool_registry_v1_4_payload() -> dict[str, object]:
    """Build the current 14-tool view without treating V1.3 as its parent."""

    base = build_tool_registry_payload()
    payload: dict[str, object] = {
        **base,
        "schema_id": TOOL_REGISTRY_V1_4_SCHEMA_ID,
        "registry_version": TOOL_REGISTRY_V1_4_VERSION,
        "base_registry_version": str(base["registry_version"]),
        "historical_registry_not_inherited": "tool_registry_v1_3",
        "historical_exclusion_reason": (
            "causal_jump_gap_shock_independent_execution_owner_revoked"
        ),
        "extension_policy": "branch_from_v1_2_append_paper_kernel_only",
        "tool_count": len(CURRENT_TOOL_IDS),
        "current_tool_ids": list(CURRENT_TOOL_IDS),
        "capability_certificate_inherited": False,
        "dynamic_parameter_authority": False,
        "tool_routing_authority": False,
        "tools": [*list(base["tools"]), paper_kernel_tool_spec().to_dict()],
        "benchmarks": [*list(base["benchmarks"]), paper_kernel_benchmark_spec().to_dict()],
        "formula_contract_extensions": [paper_kernel_tool_contract()],
        "field_labels_zh": {
            **dict(cast(dict[str, object], base["field_labels_zh"])),
            "historical_registry_not_inherited": "未继承的历史注册表",
            "historical_exclusion_reason": "历史工具不进入现役表的原因",
            "current_tool_ids": "当前十四个工具身份",
            "tool_routing_authority": "工具路由授权",
        },
    }
    payload["semantic_digest"] = canonical_digest(payload)
    validate_tool_registry_v1_4_payload(payload)
    return payload


def validate_tool_registry_v1_4_payload(payload: dict[str, object]) -> None:
    """Fail closed on prefix drift, accidental 15th tool, or granted authority."""

    if payload.get("schema_id") != TOOL_REGISTRY_V1_4_SCHEMA_ID:
        raise ValidationError("V1.4 tool registry schema changed")
    if payload.get("registry_version") != TOOL_REGISTRY_V1_4_VERSION:
        raise ValidationError("V1.4 tool registry version changed")
    tools = payload.get("tools")
    benchmarks = payload.get("benchmarks")
    if not isinstance(tools, list) or not isinstance(benchmarks, list):
        raise ValidationError("V1.4 tools and benchmarks must be lists")
    tool_rows = cast(list[dict[str, object]], tools)
    benchmark_rows = cast(list[dict[str, object]], benchmarks)
    tool_ids = tuple(str(item.get("tool_id", "")) for item in tool_rows)
    benchmark_ids = tuple(str(item.get("tool_id", "")) for item in benchmark_rows)
    if tool_ids != CURRENT_TOOL_IDS or benchmark_ids != CURRENT_TOOL_IDS:
        raise ValidationError("V1.4 must preserve V1.2 and append only the paper-kernel tool")
    if int(payload.get("tool_count", -1)) != 14:
        raise ValidationError("V1.4 current tool count must equal 14")
    if payload.get("historical_registry_not_inherited") != "tool_registry_v1_3":
        raise ValidationError("V1.4 must explicitly isolate historical V1.3")
    if "causal_jump_gap_shock" in tool_ids:
        raise ValidationError("revoked jump/gap owner cannot enter the current 14-tool view")
    for authority in (
        "production_authority",
        "dynamic_parameter_authority",
        "tool_routing_authority",
    ):
        if payload.get(authority) is not False:
            raise ValidationError(f"V1.4 registry cannot grant {authority}")
    families = {item.method_family_id for item in method_family_specs()}
    if paper_kernel_tool_spec().method_family_id not in families:
        raise ValidationError("hybrid-router method family is not registered")
    stored_digest = payload.get("semantic_digest")
    unsigned = dict(payload)
    _ = unsigned.pop("semantic_digest", None)
    if stored_digest != canonical_digest(unsigned):
        raise ValidationError("V1.4 semantic digest mismatch")


def run_paper_kernel_multiscale_trend_benchmark(
    bars: pd.DataFrame,
    *,
    frequency: str = "15m",
) -> pd.DataFrame:
    """Run the registered next-bar comparison benchmark."""

    if frequency != "15m":
        raise ValidationError("paper-kernel benchmark supports only 15m")
    required = {"timestamp", "close"}
    missing = sorted(required.difference(bars.columns))
    if missing:
        raise ValidationError(f"paper-kernel benchmark missing columns: {missing}")
    benchmark = paper_kernel_benchmark_spec()
    params = dict(benchmark.parameters_by_frequency[frequency])
    frame = bars.reset_index(drop=True)
    timestamp = pd.DatetimeIndex(pd.to_datetime(frame["timestamp"], errors="raise"))
    if timestamp.duplicated().any() or not timestamp.is_monotonic_increasing:
        raise ValidationError("paper-kernel timestamps must be ordered and unique")
    close = pd.Series(
        np.asarray(pd.to_numeric(frame["close"], errors="raise"), dtype=float),
        index=timestamp,
    )
    spec = PaperKernelHierarchicalTrendV1Spec(
        bars_per_day=int(params["bars_per_day"]),
        macro_boundary=float(params["macro_boundary"]),
        fast_hysteresis=float(params["fast_hysteresis"]),
        rebound_oversold_strength=float(params["rebound_oversold_strength"]),
        rebound_entry_score=float(params["rebound_entry_score"]),
        rebound_failure_score=float(params["rebound_failure_score"]),
    )
    state = build_paper_kernel_intraday_scale_state(close, spec)
    routed = route_paper_kernel_hierarchical_trend_v1(state, spec)
    target = pd.Series(
        routed.loc[:, "decision_long_for_next_bar"],
        index=close.index,
        dtype=float,
    )
    forward_return = np.log(close.shift(-1) / close)
    turnover = target.diff().abs().fillna(target.abs())
    cost = turnover * (float(params["cost_bps"]) / 10_000.0)
    panel = pd.DataFrame(
        {
            "benchmark_panel_schema_id": "market_state_tool_benchmark_panel@1.0",
            "benchmark_id": benchmark.benchmark_id,
            "tool_id": benchmark.tool_id,
            "method_family_id": benchmark.method_family_id,
            "bar_frequency": frequency,
            "decision_time": timestamp.to_numpy(),
            "target_position": target.to_numpy(),
            "forward_market_log_return": forward_return.to_numpy(),
            "turnover": turnover.to_numpy(),
            "transaction_cost_log_return": cost.to_numpy(),
            "long_capture_value": (target * forward_return - cost).to_numpy(),
            "cash_avoidance_value": (-(1.0 - target) * forward_return - cost).to_numpy(),
            "causal": True,
            "execution_lag_bars": 1,
        }
    )
    return panel.dropna(subset=["forward_market_log_return"])


__all__ = [
    "CURRENT_TOOL_IDS",
    "PAPER_KERNEL_TOOL_ID",
    "TOOL_REGISTRY_V1_4_SCHEMA_ID",
    "TOOL_REGISTRY_V1_4_VERSION",
    "PaperKernelBenchmarkSpec",
    "build_tool_registry_v1_4_payload",
    "paper_kernel_benchmark_spec",
    "paper_kernel_tool_contract",
    "paper_kernel_tool_spec",
    "run_paper_kernel_multiscale_trend_benchmark",
    "validate_tool_registry_v1_4_payload",
]
