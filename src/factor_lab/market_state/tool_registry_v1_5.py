# pyright: reportAny=false, reportArgumentType=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
"""Current 15-tool registry view with the LAT channel tool appended.

V1.5 branches from the frozen V1.4 14-tool prefix and appends exactly one
tool: ``lowpass_bandpass_lat_channel`` (the frozen LAT channel, research
candidate for the high-slope up/down buckets).  The V1.3 jump/gap specialist
remains excluded.  Registration provides identity and a runnable comparison
probe; it grants no priority, dynamic-parameter, or production authority.
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
    REQUIRED_ACTION_ROLES,
    REQUIRED_EFFECT_METRICS,
    ToolSpec,
)
from factor_lab.market_state.tool_registry_v1_4 import (
    CURRENT_TOOL_IDS as V1_4_TOOL_IDS,
)
from factor_lab.market_state.tool_registry_v1_4 import (
    build_tool_registry_v1_4_payload,
)

LAT_TOOL_ID = "lowpass_bandpass_lat_channel"
TOOL_REGISTRY_V1_5_SCHEMA_ID = "market_state_tool_registry@1.5"
TOOL_REGISTRY_V1_5_VERSION = "tool_registry_v1_5"
CURRENT_TOOL_IDS = V1_4_TOOL_IDS + (LAT_TOOL_ID,)

# Registered LAT incumbent (arena control), not a settled optimum:
# P64 first-order causal Butterworth low-pass centre, band-pass residual
# thickness (RMS window 48, EWMA half-life 8, width k=1.5). Tax-ruler seam
# and k were reopened on 2026-08-20; do not retune inside this registry row.
LAT_CENTRE_PERIOD_BARS = 64
LAT_FILTER_ORDER = 1
LAT_THICKNESS_RMS_WINDOW = 48
LAT_THICKNESS_HALF_LIFE = 8.0
LAT_WIDTH_MULTIPLIER = 1.5


@dataclass(frozen=True, slots=True)
class LatChannelBenchmarkSpec:
    """Native 15-minute benchmark for the appended LAT channel tool."""

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
        if self.tool_id != LAT_TOOL_ID:
            raise ValidationError("V1.5 benchmark must belong to the LAT channel tool")
        if self.method_family_id != "volatility_channel":
            raise ValidationError("LAT tool must use the volatility-channel family")
        if set(self.parameters_by_frequency) != {"15m"}:
            raise ValidationError("LAT benchmark is native 15m only")
        if tuple(self.action_roles) != REQUIRED_ACTION_ROLES:
            raise ValidationError("LAT action roles are incomplete")
        if tuple(self.effect_metric_ids) != REQUIRED_EFFECT_METRICS:
            raise ValidationError("LAT effect metrics are incomplete")
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


def lat_channel_tool_spec() -> ToolSpec:
    """Return the reusable identity of the LAT channel tool."""

    return ToolSpec(
        tool_id=LAT_TOOL_ID,
        tool_category_id="channel",
        method_family_id="volatility_channel",
        name_zh="低通带通LAT通道",
        aliases=("LAT通道", "低通中轨带通宽度", "lat channel"),
        mathematical_object=(
            "causal P64 first-order low-pass centre plus band-pass residual "
            "RMS width (RMS window 48, EWMA half-life 8, k=1.5)"
        ),
        input_semantics="15m close through the closed decision bar",
        output_semantics=(
            "enter when close is above the prior upper rail; "
            "exit when close is below the prior centre"
        ),
        supported_action_roles=REQUIRED_ACTION_ROLES,
        benchmark_status="benchmarked",
        status_reason="",
        source_strategy_refs=(
            "src/factor_lab/market_state/timing_paper_up_channel_latency_surface_r1.py",
            "src/factor_lab/market_state/timing_paper_up_short_battle_dynamic_exit_r1.py",
            "src/factor_lab/market_state/timing_paper_up_exit_line_position_grid_r1.py",
        ),
    )


def lat_channel_benchmark_spec() -> LatChannelBenchmarkSpec:
    parameters = MappingProxyType(
        {
            "15m": MappingProxyType(
                {
                    "centre_period_bars": LAT_CENTRE_PERIOD_BARS,
                    "filter_order": LAT_FILTER_ORDER,
                    "thickness_rms_window": LAT_THICKNESS_RMS_WINDOW,
                    "thickness_smoothing_half_life": LAT_THICKNESS_HALF_LIFE,
                    "width_multiplier": LAT_WIDTH_MULTIPLIER,
                    "thickness_source": "bandpass",
                    "cost_bps": 7.0,
                }
            )
        }
    )
    return LatChannelBenchmarkSpec(
        benchmark_id="lowpass_bandpass_lat_channel_benchmark_v1",
        tool_id=LAT_TOOL_ID,
        method_family_id="volatility_channel",
        name_zh="15分钟低通带通LAT通道基准",
        signal_semantics=(
            "causal P64 first-order low-pass centre with band-pass RMS width; "
            "decide at close and execute next bar"
        ),
        parameters_by_frequency=parameters,
    )


def lat_channel_tool_contract() -> dict[str, object]:
    """Translate the LAT channel prototype into a strategy-neutral tool contract."""

    return {
        "schema_id": "market_state_lowpass_bandpass_lat_channel_tool@1.0",
        "tool_id": LAT_TOOL_ID,
        "source_prototype_contract": {
            "centre": "causal Butterworth low-pass, period 64 bars, order 1",
            "thickness": (
                "band-pass residual RMS over 48 bars smoothed by EWMA "
                "half-life 8 bars, width multiplier 1.5"
            ),
            "entry": "close above prior upper rail",
            "exit": "close below prior centre",
            "execution": "close of bar t, executed bar t+1",
        },
        "observable_states": ["channel_hold", "channel_flat", "unavailable"],
        "consumer_lenses": {
            "upside_capture": "consume long decisions inside the channel lifecycle",
            "downside_protection": "consume cash decisions outside the channel lifecycle",
        },
        "architecture_status": "provisional_tool_not_priority_locked",
        "runtime_uses_future": False,
        "production_authority": False,
        "dynamic_parameter_authority": False,
        "tool_routing_authority": False,
    }


def build_tool_registry_v1_5_payload() -> dict[str, object]:
    """Build the current 15-tool view without treating V1.3 as its parent."""

    base = build_tool_registry_v1_4_payload()
    payload: dict[str, object] = {
        **base,
        "schema_id": TOOL_REGISTRY_V1_5_SCHEMA_ID,
        "registry_version": TOOL_REGISTRY_V1_5_VERSION,
        "base_registry_version": str(base["registry_version"]),
        "historical_registry_not_inherited": "tool_registry_v1_3",
        "historical_exclusion_reason": (
            "causal_jump_gap_shock_independent_execution_owner_revoked"
        ),
        "extension_policy": "branch_from_v1_4_append_lat_channel_only",
        "tool_count": len(CURRENT_TOOL_IDS),
        "current_tool_ids": list(CURRENT_TOOL_IDS),
        "capability_certificate_inherited": False,
        "dynamic_parameter_authority": False,
        "tool_routing_authority": False,
        "tools": [*list(base["tools"]), lat_channel_tool_spec().to_dict()],
        "benchmarks": [*list(base["benchmarks"]), lat_channel_benchmark_spec().to_dict()],
        "formula_contract_extensions": [lat_channel_tool_contract()],
        "field_labels_zh": {
            **dict(cast(dict[str, object], base["field_labels_zh"])),
            "historical_registry_not_inherited": "未继承的历史注册表",
            "historical_exclusion_reason": "历史工具不进入现役表的原因",
            "current_tool_ids": "当前十五个工具身份",
            "tool_routing_authority": "工具路由授权",
        },
    }
    _ = payload.pop("semantic_digest", None)
    payload["semantic_digest"] = canonical_digest(payload)
    validate_tool_registry_v1_5_payload(payload)
    return payload


def validate_tool_registry_v1_5_payload(payload: dict[str, object]) -> None:
    """Fail closed on prefix drift, accidental 16th tool, or granted authority."""

    if payload.get("schema_id") != TOOL_REGISTRY_V1_5_SCHEMA_ID:
        raise ValidationError("V1.5 tool registry schema changed")
    if payload.get("registry_version") != TOOL_REGISTRY_V1_5_VERSION:
        raise ValidationError("V1.5 tool registry version changed")
    tools = payload.get("tools")
    benchmarks = payload.get("benchmarks")
    if not isinstance(tools, list) or not isinstance(benchmarks, list):
        raise ValidationError("V1.5 tools and benchmarks must be lists")
    tool_rows = cast(list[dict[str, object]], tools)
    benchmark_rows = cast(list[dict[str, object]], benchmarks)
    tool_ids = tuple(str(item.get("tool_id", "")) for item in tool_rows)
    benchmark_ids = tuple(str(item.get("tool_id", "")) for item in benchmark_rows)
    if tool_ids != CURRENT_TOOL_IDS or benchmark_ids != CURRENT_TOOL_IDS:
        raise ValidationError("V1.5 must preserve V1.4 and append only the LAT channel tool")
    if tool_ids[:-1] != V1_4_TOOL_IDS or benchmark_ids[:-1] != V1_4_TOOL_IDS:
        raise ValidationError("V1.5 prefix drifted from the frozen V1.4 14-tool view")
    if int(payload.get("tool_count", -1)) != 15:
        raise ValidationError("V1.5 current tool count must equal 15")
    if payload.get("historical_registry_not_inherited") != "tool_registry_v1_3":
        raise ValidationError("V1.5 must explicitly isolate historical V1.3")
    if "causal_jump_gap_shock" in tool_ids:
        raise ValidationError("revoked jump/gap owner cannot enter the current 15-tool view")
    for authority in (
        "production_authority",
        "dynamic_parameter_authority",
        "tool_routing_authority",
    ):
        if payload.get(authority) is not False:
            raise ValidationError(f"V1.5 registry cannot grant {authority}")
    families = {item.method_family_id for item in method_family_specs()}
    if lat_channel_tool_spec().method_family_id not in families:
        raise ValidationError("volatility-channel method family is not registered")
    stored_digest = payload.get("semantic_digest")
    unsigned = dict(payload)
    _ = unsigned.pop("semantic_digest", None)
    if stored_digest != canonical_digest(unsigned):
        raise ValidationError("V1.5 semantic digest mismatch")


def run_lowpass_bandpass_lat_channel_benchmark(
    bars: pd.DataFrame,
    *,
    frequency: str = "15m",
) -> pd.DataFrame:
    """Run the registered next-bar comparison benchmark for the LAT tool."""

    from factor_lab.market_state.research.ols_paper_explosive_bucket_battle_v1 import (
        enforce_true_t_plus_one,
    )
    from factor_lab.market_state.timing_paper_up_channel_latency_surface_r1 import (
        FrequencyChannelSpec,
        build_channel_rails_frequency_param,
    )

    if frequency != "15m":
        raise ValidationError("LAT benchmark supports only 15m")
    required = {"timestamp", "close"}
    missing = sorted(required.difference(bars.columns))
    if missing:
        raise ValidationError(f"LAT benchmark missing columns: {missing}")
    benchmark = lat_channel_benchmark_spec()
    params = dict(benchmark.parameters_by_frequency[frequency])
    frame = bars.reset_index(drop=True)
    timestamp = pd.DatetimeIndex(pd.to_datetime(frame["timestamp"], errors="raise"))
    if timestamp.duplicated().any() or not timestamp.is_monotonic_increasing:
        raise ValidationError("LAT timestamps must be ordered and unique")
    close = pd.Series(
        np.asarray(pd.to_numeric(frame["close"], errors="raise"), dtype=float),
        index=timestamp,
    )
    spec = FrequencyChannelSpec(
        centre_period_bars=int(params["centre_period_bars"]),
        filter_order=int(params["filter_order"]),
        thickness_rms_window=int(params["thickness_rms_window"]),
        thickness_smoothing_half_life=float(params["thickness_smoothing_half_life"]),
        width_multiplier=float(params["width_multiplier"]),
    )
    rails = build_channel_rails_frequency_param(close, spec)
    close_log = rails["log_close"].to_numpy(float)
    upper = rails["upper_log"].to_numpy(float)
    centre = rails["middle_log"].to_numpy(float)
    valid = rails["valid"].to_numpy(bool)
    holding = False
    state = np.zeros(len(close), dtype=bool)
    for location in range(len(close)):
        if not bool(valid[location]):
            holding = False
        elif not holding:
            if close_log[location] > upper[location]:
                holding = True
        else:
            if close_log[location] < centre[location]:
                holding = False
        state[location] = holding
    decision = pd.Series(state, index=timestamp, dtype=bool)
    target = enforce_true_t_plus_one(decision, side="up").astype(float)
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
    "LAT_TOOL_ID",
    "TOOL_REGISTRY_V1_5_SCHEMA_ID",
    "TOOL_REGISTRY_V1_5_VERSION",
    "LatChannelBenchmarkSpec",
    "build_tool_registry_v1_5_payload",
    "lat_channel_benchmark_spec",
    "lat_channel_tool_contract",
    "lat_channel_tool_spec",
    "run_lowpass_bandpass_lat_channel_benchmark",
    "validate_tool_registry_v1_5_payload",
]
