# pyright: reportAny=false, reportArgumentType=false
# pyright: reportImplicitStringConcatenation=false, reportMissingTypeStubs=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnusedCallResult=false
"""Unified causal measurement layer for spectral-tool K-line attributes.

The 33 attributes in this module are measurements, not certified factors.
Four formula families may consume the measurements as research hypotheses, but
this module grants no parameter-selection, routing, trading, or production
authority.

All calculations use completed bars at or before the row's ``available_at``.
There are no centered windows, full-sample normalizers, or future extrema.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Final, cast

import numpy as np
import pandas as pd
from scipy.signal import butter, sosfilt, sosfreqz

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.attributes_v1 import compute_market_attributes_v1
from factor_lab.market_state.causal_scale_ladder import (
    completed_bar_session_slots,
    validate_causal_filter_input,
)
from factor_lab.market_state.horizons import normalize_bar_panel
from factor_lab.market_state.time_scale_catalog import build_time_scale_catalog_v2

CONTRACT_SCHEMA_ID: Final[str] = "market_state_spectral_kline_attribute_contract@1.0"
CALCULATION_VERSION: Final[str] = "spectral_kline_attribute_measurement_v2"
RESEARCH_TABLE_SCHEMA_ID: Final[str] = "market_state_spectral_attribute_research_table@2.0"
TOOL_PROFILE_VERSION: Final[str] = "spectral_tool_measurement_profile@2.0"
HYPOTHESIS_STATUS: Final[str] = "pending_empirical_validation"
BLACKBOX_EXCLUSION: Final[tuple[str, str]] = ("2021-01-01", "2026-12-31")

SPECTRAL_TOOL_IDS: Final[tuple[str, ...]] = (
    "laplace_iir_mixed_bandpass",
    "butterworth_clean_bandpass",
    "rolling_fourier_bandpass",
    "causal_haar_wavelet_bandpass",
)

FREQUENCY_PHYSICAL_SCALE: Final[dict[str, tuple[int, int, int]]] = {
    # frequency: (completed bars/session, bar minutes, default target period bars)
    "1d": (1, 240, 40),
    "60m": (4, 60, 160),
    "15m": (16, 15, 640),
}

EXISTING_ATTRIBUTE_IDS: Final[tuple[str, ...]] = (
    "cross_scale_direction_agreement",
    "direction_slope",
    "directional_run_age",
    "jrr",
    "max_standardized_bar",
    "neighbor_activation_ratio",
    "noise_ratio",
    "own_scale_activation",
    "path_efficiency",
    "realized_volatility",
    "residence_fraction",
    "sign_flip_rate",
    "tail_energy_concentration",
    "volatility_expansion",
)

NEW_ATTRIBUTE_IDS: Final[tuple[str, ...]] = (
    "cycle_phase_age",
    "dominant_period_persistence",
    "flat_bar_share",
    "frequency_drift_rate",
    "group_delay_to_run_age",
    "harmonic_concentration",
    "jump_scale_alignment",
    "local_stationarity_break_score",
    "passband_phase_coherence",
    "piecewise_constant_fit_error",
    "sampling_alias_energy_ratio",
    "signal_margin_to_noise",
    "spectral_bandwidth",
    "spectral_centroid_period",
    "spectral_edge_leakage",
    "spectral_entropy",
    "spectral_slope_at_edges",
    "transfer_weighted_energy_share",
    "window_endpoint_discontinuity",
)

CONTRACT_FIELD_LABELS_ZH: Final[dict[str, str]] = {
    "attribute_id": "属性机器编号",
    "name_zh": "中文名称",
    "explanation_zh": "中文解释",
    "mathematical_formula": "数学公式",
    "input_fields": "输入字段",
    "output_unit": "输出单位",
    "direction_meaning_zh": "数值方向含义",
    "applicable_scale": "适用频段或尺度",
    "observation_window_rule": "观察窗口规则",
    "warmup_rule": "预热规则",
    "missing_value_rule": "缺失值规则",
    "outlier_rule": "异常值规则",
    "causal_timestamp_rule": "严格因果时间戳口径",
    "available_at_rule": "信号可用时点",
    "cross_frequency_comparable": "是否允许跨频段直接比较",
    "applicable_tools": "适用工具",
    "sources": "来源",
    "contract_version": "合同版本",
    "current_status": "当前实现状态",
    "empirical_status": "实证状态",
    "calculator_id": "计算器编号",
    "reuse_implementation_ref": "复用实现位置",
    "definition_dispute_zh": "数学定义争议",
    "aliases": "合并别名",
    "field_labels_zh": "机器字段中文标签",
}

RESEARCH_TABLE_FIELD_LABELS_ZH: Final[dict[str, str]] = {
    "observation_time": "观察时间",
    "available_at": "最早可用时间",
    "bar_frequency": "K线频率",
    "natural_time_span_sessions": "自然时间跨度（交易日）",
    "measurement_window_bars": "观察窗口K线根数",
    "tool_id": "工具编号",
    "parameter_id": "广义参数编号",
    "attribute_id": "K线属性编号",
    "attribute_value": "属性值",
    "output_unit": "输出单位",
    "data_quality_status": "数据质量状态",
    "data_version": "数据版本",
    "calculation_version": "计算版本",
    "tool_profile_version": "工具测量配置版本",
    "tool_parameter_digest": "工具参数向量摘要",
    "required_history_sessions": "属性所需物理交易会话数",
    "observed_history_sessions": "当前连续有效物理交易会话数",
    "required_history_bars": "属性所需最少有效K线根数",
    "observed_history_bars": "当前连续有效K线根数",
    "contract_version": "属性合同版本",
    "hypothesis_status": "公式假说状态",
    "evidence_level": "证据等级",
    "relation_scope": "关系适用范围",
    "expected_relation": "公式预期关系",
    "hypothesis_id": "公式假说编号",
}


@dataclass(frozen=True, slots=True)
class ScaleContext:
    """Physical-time-first scale conversion for one completed-bar frequency."""

    frequency: str
    bar_duration_minutes: int
    expected_bars_per_session: int
    target_period_bars: int
    target_period_sessions: float
    observation_sessions: int
    observation_bars: int
    high_neighbor_sessions: int | None
    high_neighbor_bars: int | None
    low_neighbor_sessions: int | None
    low_neighbor_bars: int | None
    existing_scale_id: str

    @property
    def natural_time_span_minutes(self) -> int:
        return self.observation_sessions * 240

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AttributeContract:
    attribute_id: str
    name_zh: str
    explanation_zh: str
    mathematical_formula: str
    input_fields: tuple[str, ...]
    output_unit: str
    direction_meaning_zh: str
    applicable_scale: str
    observation_window_rule: str
    warmup_rule: str
    missing_value_rule: str
    outlier_rule: str
    causal_timestamp_rule: str
    available_at_rule: str
    cross_frequency_comparable: bool
    applicable_tools: tuple[str, ...]
    sources: tuple[str, ...]
    contract_version: str
    current_status: str
    empirical_status: str
    calculator_id: str
    reuse_implementation_ref: str | None = None
    definition_dispute_zh: str | None = None
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.current_status not in {"existing", "completed", "pending_validation", "rejected"}:
            raise ValidationError(f"invalid attribute status: {self.current_status}")
        if self.empirical_status != HYPOTHESIS_STATUS:
            raise ValidationError("spectral attributes must remain pending empirical validation")
        if not self.applicable_tools:
            raise ValidationError(f"{self.attribute_id} has no applicable tool")
        unknown = set(self.applicable_tools) - set(SPECTRAL_TOOL_IDS)
        if unknown:
            raise ValidationError(f"{self.attribute_id} has unknown tools: {sorted(unknown)}")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["field_labels_zh"] = dict(CONTRACT_FIELD_LABELS_ZH)
        return payload


@dataclass(frozen=True, slots=True)
class ToolMeasurementProfile:
    tool_id: str
    target_period_sessions: float
    short_period_sessions: float
    long_period_sessions: float
    q: float = 1.0
    order: int = 4
    fourier_window_sessions: int = 256
    haar_window_sessions: int = 128
    haar_level: int = 2
    haar_slow_level: int = 5
    profile_version: str = TOOL_PROFILE_VERSION
    parameter_source_ref: str = "00_formula_parameter_foundation/foundation_bundle.json"

    def __post_init__(self) -> None:
        if self.tool_id not in SPECTRAL_TOOL_IDS:
            raise ValidationError(f"unknown spectral tool profile: {self.tool_id}")
        if self.target_period_sessions < 1.0 or self.short_period_sessions < 1.0 or self.long_period_sessions <= self.short_period_sessions:
            raise ValidationError(f"invalid physical-period profile: {self.tool_id}")
        if not self.profile_version.strip() or not self.parameter_source_ref.strip():
            raise ValidationError("tool profile version and parameter source are required")

    def parameter_vector(self) -> dict[str, object]:
        common: dict[str, object] = {
            "tool_id": self.tool_id,
            "target_period_sessions": self.target_period_sessions,
            "short_period_sessions": self.short_period_sessions,
            "long_period_sessions": self.long_period_sessions,
        }
        if self.tool_id == "laplace_iir_mixed_bandpass":
            common["q"] = self.q
        elif self.tool_id == "butterworth_clean_bandpass":
            common["order"] = self.order
        elif self.tool_id == "rolling_fourier_bandpass":
            common["fourier_window_sessions"] = self.fourier_window_sessions
        else:
            common.update(
                {
                    "haar_window_sessions": self.haar_window_sessions,
                    "haar_level": self.haar_level,
                    "haar_slow_level": self.haar_slow_level,
                }
            )
        return common

    def parameter_digest(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.parameter_vector(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()


TOOL_PROFILES: Final[dict[str, ToolMeasurementProfile]] = {
    "laplace_iir_mixed_bandpass": ToolMeasurementProfile("laplace_iir_mixed_bandpass", 40.0, 28.0, 57.0, q=1.0),
    "butterworth_clean_bandpass": ToolMeasurementProfile("butterworth_clean_bandpass", math.sqrt(28.0 * 57.0), 28.0, 57.0, order=4),
    "rolling_fourier_bandpass": ToolMeasurementProfile("rolling_fourier_bandpass", 40.0, 20.0, 80.0, fourier_window_sessions=256),
    "causal_haar_wavelet_bandpass": ToolMeasurementProfile(
        "causal_haar_wavelet_bandpass", 16.0, 4.0, 32.0, haar_window_sessions=128, haar_level=2, haar_slow_level=5
    ),
}

_APPLICABLE_TOOLS: Final[dict[str, tuple[str, ...]]] = {
    "cross_scale_direction_agreement": ("causal_haar_wavelet_bandpass", "laplace_iir_mixed_bandpass"),
    "cycle_phase_age": ("causal_haar_wavelet_bandpass",),
    "direction_slope": ("rolling_fourier_bandpass",),
    "directional_run_age": SPECTRAL_TOOL_IDS,
    "dominant_period_persistence": ("causal_haar_wavelet_bandpass", "rolling_fourier_bandpass"),
    "flat_bar_share": SPECTRAL_TOOL_IDS,
    "frequency_drift_rate": ("laplace_iir_mixed_bandpass", "rolling_fourier_bandpass"),
    "group_delay_to_run_age": ("butterworth_clean_bandpass", "laplace_iir_mixed_bandpass"),
    "harmonic_concentration": ("butterworth_clean_bandpass", "laplace_iir_mixed_bandpass", "rolling_fourier_bandpass"),
    "jrr": SPECTRAL_TOOL_IDS,
    "jump_scale_alignment": ("causal_haar_wavelet_bandpass",),
    "local_stationarity_break_score": SPECTRAL_TOOL_IDS,
    "max_standardized_bar": SPECTRAL_TOOL_IDS,
    "neighbor_activation_ratio": ("butterworth_clean_bandpass", "causal_haar_wavelet_bandpass", "rolling_fourier_bandpass"),
    "noise_ratio": ("causal_haar_wavelet_bandpass",),
    "own_scale_activation": ("causal_haar_wavelet_bandpass",),
    "passband_phase_coherence": ("rolling_fourier_bandpass",),
    "path_efficiency": ("causal_haar_wavelet_bandpass",),
    "piecewise_constant_fit_error": ("causal_haar_wavelet_bandpass",),
    "realized_volatility": ("causal_haar_wavelet_bandpass",),
    "residence_fraction": ("laplace_iir_mixed_bandpass",),
    "sampling_alias_energy_ratio": SPECTRAL_TOOL_IDS,
    "sign_flip_rate": SPECTRAL_TOOL_IDS,
    "signal_margin_to_noise": SPECTRAL_TOOL_IDS,
    "spectral_bandwidth": ("butterworth_clean_bandpass", "causal_haar_wavelet_bandpass", "laplace_iir_mixed_bandpass"),
    "spectral_centroid_period": SPECTRAL_TOOL_IDS,
    "spectral_edge_leakage": ("butterworth_clean_bandpass", "laplace_iir_mixed_bandpass", "rolling_fourier_bandpass"),
    "spectral_entropy": ("butterworth_clean_bandpass", "laplace_iir_mixed_bandpass", "rolling_fourier_bandpass"),
    "spectral_slope_at_edges": ("butterworth_clean_bandpass",),
    "tail_energy_concentration": ("causal_haar_wavelet_bandpass",),
    "transfer_weighted_energy_share": ("butterworth_clean_bandpass", "laplace_iir_mixed_bandpass", "rolling_fourier_bandpass"),
    "volatility_expansion": ("butterworth_clean_bandpass", "laplace_iir_mixed_bandpass"),
    "window_endpoint_discontinuity": ("butterworth_clean_bandpass", "rolling_fourier_bandpass"),
}

_SOURCE_FOUNDATION = (
    "docs/ops/evidence/market_state_spectral_bandpass_parameter_foundation_20260731.md",
    "foundation_bundle.json:attribute_catalog",
)
_REUSE_REF = "src/factor_lab/market_state/attributes_v1.py:compute_market_attributes_v1"


def resolve_scale_context(
    frequency: str,
    *,
    target_period_bars: int | None = None,
    observation_cycles: float = 3.0,
) -> ScaleContext:
    """Resolve windows from physical sessions, never from equal bar counts."""

    if frequency not in FREQUENCY_PHYSICAL_SCALE:
        raise ValidationError(f"unsupported spectral attribute frequency: {frequency}")
    if observation_cycles < 3.0:
        raise ValidationError("spectral measurement requires at least three target cycles")
    bars_per_session, bar_minutes, default_target = FREQUENCY_PHYSICAL_SCALE[frequency]
    target_bars = default_target if target_period_bars is None else int(target_period_bars)
    if target_bars < 3:
        raise ValidationError("target_period_bars must be >= 3")
    target_sessions = target_bars / float(bars_per_session)
    raw_observation_sessions = max(20, int(math.ceil(target_sessions * observation_cycles)))
    catalog = build_time_scale_catalog_v2()
    governed_windows = tuple(sorted(catalog.factor_lookback_sessions(alias) for alias in catalog.legacy_measurement_scale_ids()))
    eligible_windows = tuple(value for value in governed_windows if value >= raw_observation_sessions)
    if not eligible_windows:
        raise ValidationError(
            f"target period cannot fit three complete cycles in the governed {max(governed_windows)}-session V1 measurement scale"
        )
    observation_sessions = eligible_windows[0]
    existing_scale_id = {20: "fast_20d", 60: "medium_60d", 120: "slow_120d"}[observation_sessions]
    position = governed_windows.index(observation_sessions)
    high_sessions = governed_windows[position - 1] if position > 0 else None
    low_sessions = governed_windows[position + 1] if position + 1 < len(governed_windows) else None
    return ScaleContext(
        frequency=frequency,
        bar_duration_minutes=bar_minutes,
        expected_bars_per_session=bars_per_session,
        target_period_bars=target_bars,
        target_period_sessions=target_sessions,
        observation_sessions=observation_sessions,
        observation_bars=observation_sessions * bars_per_session,
        high_neighbor_sessions=high_sessions,
        high_neighbor_bars=(high_sessions * bars_per_session if high_sessions is not None else None),
        low_neighbor_sessions=low_sessions,
        low_neighbor_bars=(low_sessions * bars_per_session if low_sessions is not None else None),
        existing_scale_id=existing_scale_id,
    )


def _contract(
    attribute_id: str,
    name_zh: str,
    explanation_zh: str,
    formula: str,
    output_unit: str,
    direction_zh: str,
    *,
    current_status: str,
    inputs: tuple[str, ...] = ("close",),
    comparable: bool = True,
    applicable_scale: str = "目标频段的拖尾物理时间窗",
    dispute: str | None = None,
    aliases: tuple[str, ...] = (),
) -> AttributeContract:
    reused = current_status == "existing"
    return AttributeContract(
        attribute_id=attribute_id,
        name_zh=name_zh,
        explanation_zh=explanation_zh,
        mathematical_formula=formula,
        input_fields=inputs,
        output_unit=output_unit,
        direction_meaning_zh=direction_zh,
        applicable_scale=applicable_scale,
        observation_window_rule=(
            "先把目标周期换算为交易日，再向上量化到能完整覆盖至少3个目标周期的"
            "V2 TimeScaleCatalog 20/60/120交易日尺度；1d、60m、15m分别按"
            "1、4、16根已完成K线/交易日换算"
        ),
        warmup_rule=("至少完整覆盖属性观察窗；复用own_scale_activation时还需252个先验交易日，工具分量属性还需覆盖工具自身严格因果预热"),
        missing_value_rule=(
            "保留缺失输入对应的时间行并输出NaN；当前缺失标记missing_input，缺失仍在属性观察窗内标记missing_input_in_window；不删行、不前填"
        ),
        outlier_rule="不删除、不缩尾；尺度量只用当前及以前拖尾窗口的MAD或标准差",
        causal_timestamp_rule="仅使用observation_time不晚于当前已完成K线的记录",
        available_at_rule="at_completed_bar_timestamp_Asia/Shanghai",
        cross_frequency_comparable=comparable,
        applicable_tools=_APPLICABLE_TOOLS[attribute_id],
        sources=_SOURCE_FOUNDATION + ((_REUSE_REF,) if reused else ()),
        contract_version=CONTRACT_SCHEMA_ID,
        current_status=current_status,
        empirical_status=HYPOTHESIS_STATUS,
        calculator_id=f"{CALCULATION_VERSION}:{attribute_id}",
        reuse_implementation_ref=_REUSE_REF if reused else None,
        definition_dispute_zh=dispute,
        aliases=aliases,
    )


ATTRIBUTE_CONTRACTS: Final[tuple[AttributeContract, ...]] = (
    _contract(
        "cross_scale_direction_agreement",
        "跨尺度方向一致",
        "目标尺度与相邻尺度方向符号是否一致。",
        "1[sign(WBI_target)=sign(WBI_neighbor)]",
        "ratio_0_1",
        "越大表示邻频方向越一致。",
        current_status="existing",
    ),
    _contract(
        "cycle_phase_age",
        "当前周期相位年龄",
        "工具分量方向自最近一次因果翻转以来占目标周期的比例。",
        "run_age(sign(Δcomponent_t))/target_period_bars",
        "target_cycle_fraction",
        "越大表示当前分量方向已运行更久。",
        current_status="completed",
        comparable=False,
        dispute="它是因果方向年龄代理，不等于由未来峰谷定义的真实相位。",
    ),
    _contract(
        "direction_slope",
        "方向斜率",
        "拖尾窗口对数价格端点斜率。",
        "(log(close_t)-log(close_start))/(N-1)",
        "log_return_per_bar",
        "正值偏上行，负值偏下行；不同K线频率不可直接比较。",
        current_status="existing",
        comparable=False,
    ),
    _contract(
        "directional_run_age",
        "同向段年龄",
        "当前收盘收益符号连续段长度。",
        "run_age(sign(log(close_t/close_(t-1))))",
        "bars",
        "越大表示当前方向连续更久；跨频率先换算物理时间。",
        current_status="existing",
        comparable=False,
    ),
    _contract(
        "dominant_period_persistence",
        "主导周期持续度",
        "历史子窗频谱重心与当前重心落在同一25%容差带的比例。",
        "mean(|log(P_sub/P_current)|<=log(1.25))",
        "ratio_0_1",
        "越大表示主导周期在历史子窗中更稳定。",
        current_status="completed",
        dispute="25%同带容差是测量合同，不是已验证的最优市场分箱。",
    ),
    _contract(
        "flat_bar_share",
        "零变动K线占比",
        "收盘对数收益精确为零的拖尾占比。",
        "mean(log(close_t/close_(t-1))=0)",
        "ratio_0_1",
        "越大表示方向继承规则被触发更频繁。",
        current_status="completed",
    ),
    _contract(
        "frequency_drift_rate",
        "主导频率漂移率",
        "快半窗与完整窗频谱重心频率的对数差，按交易日年齿化。",
        "|log(f_centroid_fast/f_centroid_full)|/(window_sessions/2)",
        "log_frequency_change_per_session",
        "越大表示主导频率迁移更快。",
        current_status="completed",
    ),
    _contract(
        "group_delay_to_run_age",
        "群延迟/行情年龄比",
        "工具参考频响在中心频率附近的群延迟除以当前方向年龄。",
        "group_delay_bars/run_age_bars",
        "ratio_nonnegative",
        "越大表示工具延迟相对行情已运行寿命更高。",
        current_status="completed",
        dispute="群延迟随频率变化；V1固定采用参考参数中心频率的数值导数。",
    ),
    _contract(
        "harmonic_concentration",
        "谐波集中度",
        "主峰整数倍频率附近一个频点的能量占正频总能量比例。",
        "Σ I(k*f_peak within one-bin tolerance)/ΣI(f)",
        "ratio_0_1",
        "越大表示能量更接近离散谐波列。",
        current_status="completed",
        dispute="离散频点容差依赖窗长；V1固定为每个整数谐波最近一个频点。",
    ),
    _contract(
        "jrr",
        "跳变反转风险",
        "前一棒异常跳变后当前棒反向的拖尾发生率。",
        "mean(1[prior jump above prior volatility and current reversal])",
        "ratio_0_1",
        "越大表示跳变后反转更常见。",
        current_status="existing",
    ),
    _contract(
        "jump_scale_alignment",
        "跳变—尺度方向对齐",
        "当前单棒收益相对先验波动的标准化值与工具分量方向的乘积。",
        "(r_t/std(r_<t))*sign(Δcomponent_t)",
        "standardized_signed_alignment",
        "正值表示跳变与工具尺度同向，负值表示冲突。",
        current_status="completed",
    ),
    _contract(
        "local_stationarity_break_score",
        "局部平稳断点分数",
        "当前拖尾窗前半与后半归一化功率谱的Jensen-Shannon距离。",
        "JSD(p_spectrum_first_half,p_spectrum_second_half)",
        "ratio_0_1",
        "越大表示窗口更可能混合了两个频谱制度。",
        current_status="completed",
    ),
    _contract(
        "max_standardized_bar",
        "最大标准化单棒",
        "窗口最大绝对收益除以实现波动。",
        "max(|r|)/std(r)",
        "standard_deviations",
        "越大表示单棒冲击相对常态波动更极端。",
        current_status="existing",
    ),
    _contract(
        "neighbor_activation_ratio",
        "邻尺度激活比",
        "目标尺度波动与相邻尺度波动之比。",
        "realized_volatility_target/realized_volatility_neighbor",
        "ratio_nonnegative",
        "越大表示目标尺度相对邻尺度更活跃。",
        current_status="existing",
    ),
    _contract(
        "noise_ratio",
        "路径噪声比",
        "路径效率的严格补集。",
        "1-abs(sum(r))/sum(abs(r))",
        "ratio_0_1",
        "越大表示往返噪声相对净位移更多。",
        current_status="existing",
        aliases=("path_inefficiency",),
    ),
    _contract(
        "own_scale_activation",
        "本尺度激活",
        "目标尺度波动除以仅使用过去值的252日滚动中位数。",
        "RV_t/median(RV_(t-252:t-1))",
        "ratio_nonnegative",
        "越大表示本尺度相对自身历史更活跃。",
        current_status="existing",
    ),
    _contract(
        "passband_phase_coherence",
        "通带相位一致度",
        "频响加权的正频端点复贡献相位合向量长度。",
        "|Σ w_f exp(i*phase(endpoint contribution_f))|/Σw_f",
        "ratio_0_1",
        "越大表示保留频率在当前端点更同相叠加。",
        current_status="completed",
        dispute="V1采用端点复贡献，不宣称等价于解析信号瞬时相位。",
    ),
    _contract(
        "path_efficiency",
        "路径效率",
        "净位移占总绝对路径长度比例。",
        "abs(sum(r))/sum(abs(r))",
        "ratio_0_1",
        "越大表示方向路径更直接。",
        current_status="existing",
    ),
    _contract(
        "piecewise_constant_fit_error",
        "分段常数拟合误差",
        "对数价格相对严格拖尾Haar块均值的MAD标准化绝对误差。",
        "mean(|x-block_mean(x)|)/(1.4826*MAD(x))",
        "robust_scale_ratio",
        "越大表示分段常数Haar基对路径曲率失配更强。",
        current_status="completed",
    ),
    _contract(
        "realized_volatility",
        "实现波动",
        "对数收益拖尾样本标准差。",
        "std(log(close_t/close_(t-1)),ddof=1)",
        "log_return_per_bar",
        "越大表示单棒实现波动更高；跨频率不可直接比较。",
        current_status="existing",
        comparable=False,
    ),
    _contract(
        "residence_fraction",
        "同向驻留占比",
        "当前方向年龄占观察窗比例。",
        "directional_run_age/window_bars",
        "ratio_0_1",
        "越大表示当前同向段占窗口更多。",
        current_status="existing",
    ),
    _contract(
        "sampling_alias_energy_ratio",
        "采样混叠能量比",
        "正频谱中0.4至0.5 cycles/bar的Nyquist邻域能量占比。",
        "ΣI(f>=0.4)/ΣI(f>0)",
        "ratio_0_1",
        "越大表示当前载体存在更多无法稳定分辨的高频能量。",
        current_status="completed",
        comparable=False,
    ),
    _contract(
        "sign_flip_rate",
        "方向翻转率",
        "非零收益符号相邻翻转率。",
        "count(sign(r_t) != sign(r_(t-1)))/valid_pairs",
        "ratio_0_1",
        "越大表示方向更频繁翻转。",
        current_status="existing",
    ),
    _contract(
        "signal_margin_to_noise",
        "分量方向边际信噪比",
        "当前工具分量差分绝对值除以拖尾分量差分MAD。",
        "|Δcomponent_t|/(1.4826*MAD(Δcomponent_window))",
        "robust_standard_deviations",
        "越大表示当前方向符号离零边界更远。",
        current_status="completed",
    ),
    _contract(
        "spectral_bandwidth",
        "有效频谱宽度",
        "正频功率对数频率的能量加权标准差。",
        "sqrt(Σp_f(log(f)-Σp_f log(f))^2)",
        "log_frequency_ratio",
        "越大表示有效频带更宽。",
        current_status="completed",
    ),
    _contract(
        "spectral_centroid_period",
        "频谱能量重心周期",
        "正频功率谱重心频率的倒数。",
        "1/(Σf*I(f)/ΣI(f))",
        "bars",
        "越大表示能量重心位于更慢周期；跨频率先换算交易日。",
        current_status="completed",
        comparable=False,
    ),
    _contract(
        "spectral_edge_leakage",
        "工具边缘泄漏",
        "工具归一化增益位于0.1至-3dB肩部的频谱能量占比。",
        "ΣI(f)*1[0.1<=|H(f)|/max|H|<sqrt(0.5)]/ΣI(f)",
        "ratio_0_1",
        "越大表示更多能量位于参数边界易错分的肩部。",
        current_status="completed",
        dispute="肩部阈值是V1工程定义，后续可版本化挑战但不得事后改写。",
    ),
    _contract(
        "spectral_entropy",
        "归一化频谱熵",
        "正频功率分布的归一化Shannon熵。",
        "-Σp_f log(p_f)/log(number_of_positive_bins)",
        "ratio_0_1",
        "越大表示频谱更分散、多峰歧义更强。",
        current_status="completed",
    ),
    _contract(
        "spectral_slope_at_edges",
        "通带边缘谱斜率",
        "候选上下边界最近三个正频点的log功率-log频率斜率绝对值均值。",
        "mean(|d log(I(f))/d log(f)| at lower and upper edges)",
        "absolute_log_log_slope",
        "越大表示真实能量边界更陡。",
        current_status="completed",
        dispute="边界附近只有离散频点；V1固定使用最近三个点。",
    ),
    _contract(
        "tail_energy_concentration",
        "尾部能量集中度",
        "最大单棒平方收益占总平方收益比例。",
        "max(r^2)/sum(r^2)",
        "ratio_0_1",
        "越大表示能量更集中于单个尾部事件。",
        current_status="existing",
    ),
    _contract(
        "transfer_weighted_energy_share",
        "工具原生频响加权能量份额",
        "工具参考参数幅频响应平方加权后的能量占总正频能量比例。",
        "Σ|H(f)|^2 I(f)/(max|H|^2 ΣI(f))",
        "ratio_0_1",
        "越大表示工具参考频响覆盖更多当前能量。",
        current_status="completed",
    ),
    _contract(
        "volatility_expansion",
        "波动扩张率",
        "短窗波动相对目标窗波动的增量比例。",
        "std(r,window/3)/std(r,window)-1",
        "signed_ratio",
        "正值表示波动扩张，负值表示收缩。",
        current_status="existing",
    ),
    _contract(
        "window_endpoint_discontinuity",
        "窗口端点不连续度",
        "拖尾窗首尾对数价格差除以收益MAD乘根号窗长。",
        "|x_t-x_start|/(1.4826*MAD(r)*sqrt(N))",
        "robust_scale_ratio",
        "越大表示周期延拓或启动锚点的人为跳点风险更高。",
        current_status="completed",
    ),
)

ATTRIBUTE_CONTRACT_BY_ID: Final[dict[str, AttributeContract]] = {item.attribute_id: item for item in ATTRIBUTE_CONTRACTS}


def build_attribute_contract_catalog() -> pd.DataFrame:
    rows = []
    for contract in ATTRIBUTE_CONTRACTS:
        row = contract.to_dict()
        row.pop("field_labels_zh")
        for key in ("input_fields", "applicable_tools", "sources", "aliases"):
            row[key] = json.dumps(row[key], ensure_ascii=False, separators=(",", ":"))
        rows.append(row)
    return pd.DataFrame(rows).sort_values("attribute_id", kind="mergesort").reset_index(drop=True)


def audit_attribute_implementations() -> pd.DataFrame:
    """Return the frozen 14-reuse/19-new audit without claiming effectiveness."""

    rows: list[dict[str, object]] = []
    for contract in ATTRIBUTE_CONTRACTS:
        reused = contract.attribute_id in EXISTING_ATTRIBUTE_IDS
        rows.append(
            {
                "attribute_id": contract.attribute_id,
                "name_zh": contract.name_zh,
                "disposition": "reuse_existing" if reused else "implement_new",
                "implementation_ref": contract.reuse_implementation_ref
                if reused
                else "factor_lab.market_state.spectral_kline_attribute_measurement",
                "strict_causal_audit": "passed_by_prefix_and_replay_tests",
                "duplicate_resolution": (
                    "canonical_alias_of_noise_ratio" if contract.attribute_id == "noise_ratio" and contract.aliases else "none"
                ),
                "definition_dispute_zh": contract.definition_dispute_zh or "",
                "empirical_status": HYPOTHESIS_STATUS,
            }
        )
    return pd.DataFrame(rows).sort_values("attribute_id", kind="mergesort").reset_index(drop=True)


def _prepare_completed_panel(
    panel: pd.DataFrame,
    *,
    frequency: str,
    expected_open_session_days: Iterable[object] | None,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Normalize identities without deleting invalid measurements.

    ``normalize_bar_panel`` intentionally removes invalid OHLC rows for its
    production callers.  The measurement contract instead preserves those
    timestamps and emits an explicit quality state, so a positive proxy close
    is used only for identity/session normalization.  Calculators never see
    that proxy as a measurement.
    """

    required = {"trading_day", "timestamp", "close"}
    missing = sorted(required - set(panel))
    if missing:
        raise ValidationError(f"spectral attribute panel missing columns: {missing}")
    causal_gate_fields = {"available_at", "bar_complete", "sampling_status"}
    if {"bar_complete", "sampling_status"} & set(panel):
        if not causal_gate_fields <= set(panel):
            raise ValidationError("partial causal completed-bar gate metadata")
        validate_causal_filter_input(panel.loc[:, sorted(causal_gate_fields | {"timestamp"})])
    elif "available_at" in panel:
        available = pd.to_datetime(panel["available_at"], errors="coerce", utc=True)
        timestamp = pd.to_datetime(panel["timestamp"], errors="coerce", utc=True)
        if bool(available.isna().any()) or not available.equals(timestamp):
            raise ValidationError("spectral measurement is available only at the completed bar timestamp")
    working = panel.copy()
    source_close = np.asarray(
        pd.to_numeric(cast(pd.Series, working["close"]), errors="coerce"),
        dtype=np.float64,
    )
    source_valid = np.isfinite(source_close) & (source_close > 0.0)
    working["_spectral_source_close"] = source_close
    working["_spectral_source_valid"] = source_valid
    working["_spectral_source_row"] = np.arange(len(working), dtype=np.int64)
    proxy_close = np.where(source_valid, source_close, 1.0)
    for column in ("open", "high", "low", "close"):
        working[column] = proxy_close
    normalized = normalize_bar_panel(working, frequency=frequency)
    frame = normalized.frame
    if len(frame) != len(panel):
        raise ValidationError("spectral measurement rejects invalid or duplicate bar identities; timestamps may not be silently removed")
    source_rows = frame["_spectral_source_row"].to_numpy(dtype=np.int64)
    if len(np.unique(source_rows)) != len(source_rows):
        raise ValidationError("spectral measurement bar identities are not unique")
    source_close = frame["_spectral_source_close"].to_numpy(dtype=np.float64)
    source_valid = frame["_spectral_source_valid"].to_numpy(dtype=bool)
    frame["close"] = source_close

    observed_days = tuple(pd.DatetimeIndex(cast(pd.Series, frame["trading_day"]).drop_duplicates()).strftime("%Y-%m-%d"))
    if frequency in {"60m", "15m"} and expected_open_session_days is None:
        raise ValidationError(
            f"{frequency} spectral measurement requires expected_open_session_days "
            "to distinguish exchange closure from a missing open session"
        )
    if expected_open_session_days is not None:
        expected_days = tuple(sorted(pd.Timestamp(value).normalize().strftime("%Y-%m-%d") for value in expected_open_session_days))
        if len(expected_days) != len(set(expected_days)):
            raise ValidationError("expected_open_session_days contains duplicates")
        if tuple(sorted(observed_days)) != expected_days:
            raise ValidationError("spectral measurement rejects missing or unexpected open sessions")

    if frequency in {"60m", "15m"}:
        if "one_minute_count" not in frame:
            raise ValidationError(f"{frequency} spectral measurement requires one_minute_count to prove every source bar is complete")
        minute_count = pd.Series(
            pd.to_numeric(cast(pd.Series, frame["one_minute_count"]), errors="coerce"),
            index=frame.index,
            dtype=float,
        )
        expected_minutes = FREQUENCY_PHYSICAL_SCALE[frequency][1]
        if not bool(minute_count.eq(expected_minutes).all()):
            raise ValidationError(f"{frequency} spectral measurement rejects incomplete source bars")
        templates = (
            frame["session_template_id"].astype(str)
            if "session_template_id" in frame
            else pd.Series("full_day", index=frame.index, dtype=str)
        )
        if not bool(templates.isin({"full_day", "half_day"}).all()):
            raise ValidationError("unknown spectral session_template_id")
        frame["_spectral_session_template"] = templates
        for group_key, positions in frame.groupby(["trading_day", "_spectral_session_template"], sort=True).groups.items():
            if not isinstance(group_key, tuple) or len(group_key) != 2:
                raise ValidationError("invalid spectral session group identity")
            template = str(group_key[1])
            expected_slots = completed_bar_session_slots(frequency, template)
            actual_slots = tuple((pd.Timestamp(value).hour, pd.Timestamp(value).minute) for value in frame.loc[positions, "timestamp"])
            if actual_slots != expected_slots:
                raise ValidationError(f"{frequency} spectral measurement rejects missing, duplicate, or off-template completed bars")
    return frame.reset_index(drop=True), source_valid


def _session_window_bounds(session_ordinals: np.ndarray, window_sessions: int) -> tuple[np.ndarray, np.ndarray]:
    starts = np.searchsorted(
        session_ordinals,
        np.maximum(0, session_ordinals - window_sessions + 1),
        side="left",
    ).astype(np.int64)
    ends = np.arange(len(session_ordinals), dtype=np.int64) + 1
    return starts, ends


def _session_history_counts(session_ordinals: np.ndarray) -> np.ndarray:
    first = int(session_ordinals[0])
    return session_ordinals - first + 1


def _tool_component(
    log_close: np.ndarray,
    *,
    profile: ToolMeasurementProfile,
    scale: ScaleContext,
) -> tuple[np.ndarray, int]:
    bars_per_session = scale.expected_bars_per_session
    anchored = log_close - log_close[0]
    if profile.tool_id == "laplace_iir_mixed_bandpass":
        period = profile.target_period_sessions * bars_per_session
        omega = 2.0 * math.pi / period
        alpha = math.sin(omega) / (2.0 * profile.q)
        b0 = alpha / (1.0 + alpha)
        b1 = 0.0
        b2 = -b0
        a1 = -2.0 * math.cos(omega) / (1.0 + alpha)
        a2 = (1.0 - alpha) / (1.0 + alpha)
        result = np.zeros(len(log_close), dtype=float)
        x1 = x2 = y1 = y2 = 0.0
        for index, value in enumerate(anchored):
            y0 = b0 * value + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
            result[index] = y0
            x2, x1, y2, y1 = x1, value, y1, y0
        return result, _tool_warmup_bars(profile, scale)
    if profile.tool_id == "butterworth_clean_bandpass":
        short = profile.short_period_sessions * bars_per_session
        long = profile.long_period_sessions * bars_per_session
        sos = butter(
            profile.order,
            [1.0 / long, 1.0 / short],
            btype="bandpass",
            fs=1.0,
            output="sos",
        )
        return np.asarray(sosfilt(sos, anchored), dtype=float), _tool_warmup_bars(profile, scale)
    if profile.tool_id == "rolling_fourier_bandpass":
        window = profile.fourier_window_sessions * bars_per_session
        low = profile.short_period_sessions * bars_per_session
        high = profile.long_period_sessions * bars_per_session
        result = np.full(len(log_close), np.nan, dtype=float)
        for end in range(window - 1, len(log_close)):
            values = log_close[end - window + 1 : end + 1]
            transformed = np.fft.fft(values - values.mean())
            frequencies = np.fft.fftfreq(window)
            mask = (np.abs(frequencies) >= 1.0 / high) & (np.abs(frequencies) <= 1.0 / low)
            mask[0] = False
            result[end] = float(np.fft.ifft(transformed * mask)[-1].real)
        return result, _tool_warmup_bars(profile, scale)
    if profile.tool_id == "causal_haar_wavelet_bandpass":
        window = profile.haar_window_sessions * bars_per_session
        fast = 2**profile.haar_level
        slow = 2**profile.haar_slow_level
        fast_mean = pd.Series(log_close).rolling(fast, min_periods=fast).mean()
        slow_mean = pd.Series(log_close).rolling(slow, min_periods=slow).mean()
        result = np.asarray(fast_mean - slow_mean, dtype=float)
        result[: window - 1] = np.nan
        return result, _tool_warmup_bars(profile, scale)
    raise ValidationError(f"unknown spectral tool: {profile.tool_id}")


def _tool_warmup_bars(profile: ToolMeasurementProfile, scale: ScaleContext) -> int:
    bars_per_session = scale.expected_bars_per_session
    if profile.tool_id == "laplace_iir_mixed_bandpass":
        return max(
            5,
            int(math.ceil(3.0 * profile.target_period_sessions * bars_per_session)),
        )
    if profile.tool_id == "butterworth_clean_bandpass":
        return int(math.ceil(profile.long_period_sessions * bars_per_session))
    if profile.tool_id == "rolling_fourier_bandpass":
        return profile.fourier_window_sessions * bars_per_session
    if profile.tool_id == "causal_haar_wavelet_bandpass":
        return profile.haar_window_sessions * bars_per_session
    raise ValidationError(f"unknown spectral tool: {profile.tool_id}")


def _frequency_response(
    frequencies: np.ndarray,
    *,
    profile: ToolMeasurementProfile,
    scale: ScaleContext,
) -> np.ndarray:
    bars_per_session = scale.expected_bars_per_session
    if profile.tool_id == "laplace_iir_mixed_bandpass":
        period = profile.target_period_sessions * bars_per_session
        omega = 2.0 * math.pi / period
        alpha = math.sin(omega) / (2.0 * profile.q)
        b = np.array([alpha, 0.0, -alpha], dtype=float) / (1.0 + alpha)
        a = np.array(
            [1.0, -2.0 * math.cos(omega) / (1.0 + alpha), (1.0 - alpha) / (1.0 + alpha)],
            dtype=float,
        )
        z = np.exp(-2j * math.pi * frequencies)
        return (b[0] + b[1] * z + b[2] * z**2) / (a[0] + a[1] * z + a[2] * z**2)
    if profile.tool_id == "butterworth_clean_bandpass":
        short = profile.short_period_sessions * bars_per_session
        long = profile.long_period_sessions * bars_per_session
        sos = butter(
            profile.order,
            [1.0 / long, 1.0 / short],
            btype="bandpass",
            fs=1.0,
            output="sos",
        )
        _, response = sosfreqz(sos, worN=frequencies, fs=1.0)
        return np.asarray(response, dtype=np.complex128)
    if profile.tool_id == "rolling_fourier_bandpass":
        short = profile.short_period_sessions * bars_per_session
        long = profile.long_period_sessions * bars_per_session
        return ((frequencies >= 1.0 / long) & (frequencies <= 1.0 / short)).astype(np.complex128)
    fast = 2**profile.haar_level
    slow = 2**profile.haar_slow_level
    return _moving_average_response(frequencies, fast) - _moving_average_response(frequencies, slow)


def _moving_average_response(frequencies: np.ndarray, length: int) -> np.ndarray:
    omega = 2.0 * math.pi * frequencies
    numerator = 1.0 - np.exp(-1j * omega * length)
    denominator = length * (1.0 - np.exp(-1j * omega))
    result = np.ones(len(frequencies), dtype=np.complex128)
    valid = np.abs(denominator) > 1e-14
    result[valid] = numerator[valid] / denominator[valid]
    return result


def _run_age(sign_values: np.ndarray) -> np.ndarray:
    result = np.full(len(sign_values), np.nan, dtype=float)
    previous = math.nan
    age = 0
    for index, value in enumerate(sign_values):
        if not math.isfinite(value) or value == 0.0:
            age = 0
            previous = math.nan
        else:
            age = age + 1 if value == previous else 1
            previous = value
            result[index] = float(age)
    return result


def _robust_scale(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return math.nan
    median = float(np.median(finite))
    return 1.4826 * float(np.median(np.abs(finite - median)))


def _positive_spectrum(values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    centered = values - float(np.mean(values))
    transformed = np.fft.rfft(centered)
    frequencies = np.fft.rfftfreq(len(centered))
    positive = frequencies > 0.0
    return frequencies[positive], np.abs(transformed[positive]) ** 2, transformed[positive]


def _centroid_frequency(frequencies: np.ndarray, energy: np.ndarray) -> float:
    total = float(np.sum(energy))
    return math.nan if total <= 0.0 else float(np.sum(frequencies * energy) / total)


def _js_distance(left: np.ndarray, right: np.ndarray) -> float:
    if len(left) != len(right) or len(left) == 0:
        return math.nan
    left_total = float(left.sum())
    right_total = float(right.sum())
    if left_total <= 0.0 or right_total <= 0.0:
        return math.nan
    p = left / left_total
    q = right / right_total
    midpoint = 0.5 * (p + q)
    eps = np.finfo(float).tiny
    divergence = 0.5 * np.sum(p * np.log((p + eps) / (midpoint + eps)))
    divergence += 0.5 * np.sum(q * np.log((q + eps) / (midpoint + eps)))
    return float(math.sqrt(max(0.0, divergence / math.log(2.0))))


def _edge_slope(frequencies: np.ndarray, energy: np.ndarray, target_frequency: float) -> float:
    if len(frequencies) < 3:
        return math.nan
    nearest = np.argsort(np.abs(frequencies - target_frequency))[:3]
    x = np.log(frequencies[nearest])
    y = np.log(energy[nearest] + np.finfo(float).tiny)
    if float(np.ptp(x)) <= 0.0:
        return math.nan
    return float(abs(np.polyfit(x, y, 1)[0]))


def _group_delay_bars(*, profile: ToolMeasurementProfile, scale: ScaleContext) -> float:
    center = 1.0 / (profile.target_period_sessions * scale.expected_bars_per_session)
    delta = max(center * 1e-3, 1e-7)
    frequencies = np.array([max(1e-8, center - delta), center, center + delta])
    phase = np.unwrap(np.angle(_frequency_response(frequencies, profile=profile, scale=scale)))
    derivative = (phase[2] - phase[0]) / (2.0 * delta)
    return float(max(0.0, -derivative / (2.0 * math.pi)))


def _new_attribute_arrays(
    log_close: np.ndarray,
    component: np.ndarray,
    *,
    profile: ToolMeasurementProfile,
    scale: ScaleContext,
    session_ordinals: np.ndarray,
) -> dict[str, np.ndarray]:
    length = len(log_close)
    arrays = {attribute_id: np.full(length, np.nan, dtype=float) for attribute_id in NEW_ATTRIBUTE_IDS}
    component_delta = np.diff(component, prepend=np.nan)
    component_age = _run_age(np.sign(component_delta))
    raw_return = np.diff(log_close, prepend=np.nan)
    raw_age = _run_age(np.sign(raw_return))
    group_delay = _group_delay_bars(profile=profile, scale=scale)

    starts, _ = _session_window_bounds(session_ordinals, scale.observation_sessions)
    history_sessions = _session_history_counts(session_ordinals)
    for end in range(length):
        if history_sessions[end] < scale.observation_sessions:
            continue
        start = int(starts[end])
        path = log_close[start : end + 1]
        returns = np.diff(path)
        deltas = component_delta[start : end + 1]
        if not np.isfinite(path).all() or returns.size < 8:
            continue
        frequencies, energy, complex_spectrum = _positive_spectrum(returns)
        total_energy = float(energy.sum())
        if total_energy <= 0.0:
            arrays["flat_bar_share"][end] = float(np.mean(returns == 0.0))
            continue
        weights = energy / total_energy
        centroid = _centroid_frequency(frequencies, energy)
        response = _frequency_response(frequencies, profile=profile, scale=scale)
        gain = np.abs(response)
        max_gain = float(gain.max()) if gain.size else 0.0
        normalized_gain = gain / max_gain if max_gain > 0.0 else np.zeros_like(gain)

        arrays["flat_bar_share"][end] = float(np.mean(returns == 0.0))
        arrays["spectral_centroid_period"][end] = 1.0 / centroid if math.isfinite(centroid) and centroid > 0.0 else math.nan
        log_frequency = np.log(frequencies)
        mean_log_frequency = float(np.sum(weights * log_frequency))
        arrays["spectral_bandwidth"][end] = float(math.sqrt(max(0.0, np.sum(weights * (log_frequency - mean_log_frequency) ** 2))))
        entropy = -float(np.sum(weights * np.log(weights + np.finfo(float).tiny)))
        arrays["spectral_entropy"][end] = entropy / math.log(len(weights)) if len(weights) > 1 else 0.0
        arrays["sampling_alias_energy_ratio"][end] = float(energy[frequencies >= 0.4].sum() / total_energy)
        shoulder = (normalized_gain >= 0.1) & (normalized_gain < math.sqrt(0.5))
        arrays["spectral_edge_leakage"][end] = float(energy[shoulder].sum() / total_energy)
        arrays["transfer_weighted_energy_share"][end] = (
            float(np.sum((normalized_gain**2) * energy) / total_energy) if max_gain > 0.0 else math.nan
        )
        endpoint_phase = np.exp(1j * 2.0 * math.pi * frequencies * (len(returns) - 1))
        contributions = complex_spectrum * response * endpoint_phase
        contribution_weight = np.abs(contributions)
        arrays["passband_phase_coherence"][end] = (
            float(abs(np.sum(contribution_weight * np.exp(1j * np.angle(contributions)))) / contribution_weight.sum())
            if float(contribution_weight.sum()) > 0.0
            else math.nan
        )

        peak_index = int(np.argmax(energy))
        peak_frequency = float(frequencies[peak_index])
        harmonic_indices: set[int] = set()
        multiple = 1
        while multiple * peak_frequency <= 0.5:
            harmonic_indices.add(int(np.argmin(np.abs(frequencies - multiple * peak_frequency))))
            multiple += 1
        arrays["harmonic_concentration"][end] = float(energy[list(harmonic_indices)].sum() / total_energy)

        fast_path = path[len(path) // 2 :]
        fast_frequency, fast_energy, _ = _positive_spectrum(np.diff(fast_path))
        fast_centroid = _centroid_frequency(fast_frequency, fast_energy)
        arrays["frequency_drift_rate"][end] = (
            abs(math.log(fast_centroid / centroid)) / max(1.0, scale.observation_sessions / 2.0)
            if fast_centroid > 0.0 and centroid > 0.0
            else math.nan
        )

        half = len(returns) // 2
        first_frequency, first_energy, _ = _positive_spectrum(returns[:half])
        second_frequency, second_energy, _ = _positive_spectrum(returns[-half:])
        arrays["local_stationarity_break_score"][end] = (
            _js_distance(first_energy, second_energy) if np.array_equal(first_frequency, second_frequency) else math.nan
        )

        block = max(8, len(returns) // 4)
        subperiods: list[float] = []
        for sub_end in range(block, len(returns) + 1, block):
            sub_frequency, sub_energy, _ = _positive_spectrum(returns[sub_end - block : sub_end])
            sub_centroid = _centroid_frequency(sub_frequency, sub_energy)
            if sub_centroid > 0.0:
                subperiods.append(1.0 / sub_centroid)
        current_period = arrays["spectral_centroid_period"][end]
        arrays["dominant_period_persistence"][end] = (
            float(np.mean(np.abs(np.log(np.asarray(subperiods) / current_period)) <= math.log(1.25)))
            if subperiods and current_period > 0.0
            else math.nan
        )

        arrays["spectral_slope_at_edges"][end] = float(
            np.nanmean(
                [
                    _edge_slope(
                        frequencies,
                        energy,
                        1.0 / (profile.long_period_sessions * scale.expected_bars_per_session),
                    ),
                    _edge_slope(
                        frequencies,
                        energy,
                        1.0 / (profile.short_period_sessions * scale.expected_bars_per_session),
                    ),
                ]
            )
        )
        return_scale = _robust_scale(returns)
        arrays["window_endpoint_discontinuity"][end] = (
            abs(path[-1] - path[0]) / (return_scale * math.sqrt(len(path))) if return_scale > 0.0 else math.nan
        )
        fast_block = 2**profile.haar_level
        fitted = np.empty_like(path)
        for start in range(0, len(path), fast_block):
            stop = min(start + fast_block, len(path))
            fitted[start:stop] = float(np.mean(path[start:stop]))
        path_scale = _robust_scale(path)
        arrays["piecewise_constant_fit_error"][end] = float(np.mean(np.abs(path - fitted)) / path_scale) if path_scale > 0.0 else math.nan
        delta_scale = _robust_scale(deltas[:-1])
        arrays["signal_margin_to_noise"][end] = (
            abs(component_delta[end]) / delta_scale if delta_scale > 0.0 and math.isfinite(component_delta[end]) else math.nan
        )
        prior_std = float(np.std(returns[:-1], ddof=1))
        arrays["jump_scale_alignment"][end] = (
            raw_return[end] / prior_std * math.copysign(1.0, component_delta[end])
            if prior_std > 0.0 and math.isfinite(component_delta[end]) and component_delta[end] != 0.0
            else math.nan
        )
        arrays["cycle_phase_age"][end] = component_age[end] / scale.target_period_bars if math.isfinite(component_age[end]) else math.nan
        arrays["group_delay_to_run_age"][end] = (
            group_delay / raw_age[end] if math.isfinite(raw_age[end]) and raw_age[end] > 0.0 else math.nan
        )
    return arrays


MEASUREMENT_OUTPUT_COLUMNS: Final[tuple[str, ...]] = (
    "observation_time",
    "available_at",
    "bar_frequency",
    "tool_id",
    "attribute_id",
    "attribute_value",
    "output_unit",
    "natural_time_span_sessions",
    "measurement_window_bars",
    "target_period_bars",
    "required_history_sessions",
    "observed_history_sessions",
    "required_history_bars",
    "observed_history_bars",
    "tool_profile_version",
    "tool_parameter_digest",
    "calculation_version",
    "contract_version",
    "data_quality_status",
    "empirical_status",
)

_TOOL_COMPONENT_ATTRIBUTE_IDS: Final[frozenset[str]] = frozenset(
    {
        "cycle_phase_age",
        "jump_scale_alignment",
        "signal_margin_to_noise",
    }
)


def _attribute_history_requirement(
    attribute_id: str,
    *,
    scale: ScaleContext,
    tool_warmup_bars: int,
) -> tuple[int, int]:
    required_sessions = scale.observation_sessions
    if attribute_id == "own_scale_activation":
        required_sessions = 252
    elif attribute_id in {
        "neighbor_activation_ratio",
        "cross_scale_direction_agreement",
    }:
        required_sessions = {
            20: 60,
            60: 120,
            120: 120,
        }[scale.observation_sessions]
    required_bars = (required_sessions - 1) * scale.expected_bars_per_session + 1
    if attribute_id in _TOOL_COMPONENT_ATTRIBUTE_IDS:
        required_bars = max(required_bars, tool_warmup_bars)
        required_sessions = max(
            required_sessions,
            int(math.ceil(tool_warmup_bars / scale.expected_bars_per_session)),
        )
    return required_sessions, required_bars


def _compute_clean_segment(
    frame: pd.DataFrame,
    *,
    frequency: str,
    profile: ToolMeasurementProfile,
    scale: ScaleContext,
) -> tuple[dict[str, np.ndarray], int]:
    normalized = normalize_bar_panel(frame, frequency=frequency)
    clean = normalized.frame
    close = clean["close"].to_numpy(dtype=np.float64)
    log_close = np.log(close)
    component, tool_warmup = _tool_component(log_close, profile=profile, scale=scale)
    values_by_id = _new_attribute_arrays(
        log_close,
        component,
        profile=profile,
        scale=scale,
        session_ordinals=normalized.session_ordinals,
    )
    existing = compute_market_attributes_v1(clean, frequency=frequency)
    observation_index = pd.DatetimeIndex(pd.to_datetime(clean["timestamp"]))
    for attribute_id in EXISTING_ATTRIBUTE_IDS:
        rows = existing.loc[
            (existing["physical_attribute_id"] == attribute_id) & (existing["measurement_scale_id"] == scale.existing_scale_id)
        ].sort_values("observation_time", kind="mergesort")
        series = pd.Series(
            rows["raw_value"].to_numpy(dtype=float),
            index=pd.DatetimeIndex(pd.to_datetime(rows["observation_time"])),
            dtype=float,
        )
        values_by_id[attribute_id] = series.reindex(observation_index).to_numpy(dtype=float)
    return values_by_id, tool_warmup


def compute_spectral_kline_attributes(
    panel: pd.DataFrame,
    *,
    frequency: str,
    tool_id: str,
    target_period_bars: int | None = None,
    attribute_ids: Iterable[str] | None = None,
    expected_open_session_days: Iterable[object] | None = None,
) -> pd.DataFrame:
    """Compute any registered attributes through one deterministic interface."""

    if tool_id not in TOOL_PROFILES:
        raise ValidationError(f"unknown spectral tool: {tool_id}")
    applicable = {item.attribute_id for item in ATTRIBUTE_CONTRACTS if tool_id in item.applicable_tools}
    requested = applicable if attribute_ids is None else set(attribute_ids)
    unknown = requested - set(ATTRIBUTE_CONTRACT_BY_ID)
    if unknown:
        raise ValidationError(f"unknown attribute ids: {sorted(unknown)}")
    inapplicable = requested - applicable
    if inapplicable:
        raise ValidationError(f"attributes are not applicable to {tool_id}: {sorted(inapplicable)}")
    frame, source_valid = _prepare_completed_panel(
        panel,
        frequency=frequency,
        expected_open_session_days=expected_open_session_days,
    )
    base_profile = TOOL_PROFILES[tool_id]
    bars_per_session = FREQUENCY_PHYSICAL_SCALE[frequency][0]
    effective_target_bars = (
        int(round(base_profile.target_period_sessions * bars_per_session)) if target_period_bars is None else int(target_period_bars)
    )
    scale = resolve_scale_context(frequency, target_period_bars=effective_target_bars)
    profile = base_profile if target_period_bars is None else replace(base_profile, target_period_sessions=scale.target_period_sessions)
    tool_warmup = _tool_warmup_bars(profile, scale)
    values_by_id = {attribute_id: np.full(len(frame), np.nan, dtype=np.float64) for attribute_id in requested}
    valid_positions = np.flatnonzero(source_valid)
    if valid_positions.size:
        split_points = np.flatnonzero(np.diff(valid_positions) != 1) + 1
        for segment_positions in np.split(valid_positions, split_points):
            segment = frame.iloc[segment_positions].copy()
            segment_values, _ = _compute_clean_segment(
                segment,
                frequency=frequency,
                profile=profile,
                scale=scale,
            )
            for attribute_id in requested:
                values_by_id[attribute_id][segment_positions] = segment_values[attribute_id]

    session_ordinals = frame["session_ordinal"].to_numpy(dtype=np.int64)
    global_history_sessions = session_ordinals + 1
    segment_history_sessions = np.zeros(len(frame), dtype=np.int64)
    segment_history_bars = np.zeros(len(frame), dtype=np.int64)
    if valid_positions.size:
        split_points = np.flatnonzero(np.diff(valid_positions) != 1) + 1
        for segment_positions in np.split(valid_positions, split_points):
            segment_ordinals = session_ordinals[segment_positions]
            segment_history_sessions[segment_positions] = _session_history_counts(segment_ordinals)
            segment_history_bars[segment_positions] = np.arange(1, len(segment_positions) + 1, dtype=np.int64)
    invalid_prefix = np.r_[0, np.cumsum(~source_valid, dtype=np.int64)]

    records: list[pd.DataFrame] = []
    for attribute_id in sorted(requested):
        contract = ATTRIBUTE_CONTRACT_BY_ID[attribute_id]
        required_sessions, required_bars = _attribute_history_requirement(
            attribute_id,
            scale=scale,
            tool_warmup_bars=tool_warmup,
        )
        starts, ends = _session_window_bounds(session_ordinals, required_sessions)
        window_bars = ends - starts
        window_has_missing = (invalid_prefix[ends] - invalid_prefix[starts]) > 0
        values = values_by_id[attribute_id].copy()
        quality = np.full(len(frame), "ok", dtype=object)
        initial_warmup = (global_history_sessions < required_sessions) | (np.arange(len(frame), dtype=np.int64) + 1 < required_bars)
        quality[initial_warmup] = "warmup"
        quality[
            (~initial_warmup)
            & ((segment_history_sessions < required_sessions) | (segment_history_bars < required_bars) | window_has_missing)
        ] = "missing_input_in_window"
        quality[~source_valid] = "missing_input"
        quality[~np.isfinite(values) & (quality == "ok")] = "undefined_or_zero_denominator"
        values[quality != "ok"] = np.nan
        records.append(
            pd.DataFrame(
                {
                    "observation_time": frame["timestamp"],
                    "available_at": frame["available_at"],
                    "bar_frequency": frequency,
                    "tool_id": tool_id,
                    "attribute_id": attribute_id,
                    "attribute_value": values,
                    "output_unit": contract.output_unit,
                    "natural_time_span_sessions": required_sessions,
                    "measurement_window_bars": window_bars,
                    "target_period_bars": scale.target_period_bars,
                    "required_history_sessions": required_sessions,
                    "observed_history_sessions": segment_history_sessions,
                    "required_history_bars": required_bars,
                    "observed_history_bars": segment_history_bars,
                    "tool_profile_version": profile.profile_version,
                    "tool_parameter_digest": profile.parameter_digest(),
                    "calculation_version": CALCULATION_VERSION,
                    "contract_version": CONTRACT_SCHEMA_ID,
                    "data_quality_status": quality,
                    "empirical_status": HYPOTHESIS_STATUS,
                }
            )
        )
    if not records:
        return pd.DataFrame({column: pd.Series(dtype=object) for column in MEASUREMENT_OUTPUT_COLUMNS})
    result = pd.concat(records, ignore_index=True).loc[:, MEASUREMENT_OUTPUT_COLUMNS]
    return result.sort_values(["tool_id", "attribute_id", "observation_time"], kind="mergesort").reset_index(drop=True)


def load_formula_hypotheses(path: Path | str) -> pd.DataFrame:
    links = pd.read_csv(path, dtype=str, keep_default_na=False)
    required = {
        "tool_id",
        "parameter_id",
        "attribute_id",
        "relation_scope",
        "expected_relation",
        "evidence_level",
    }
    missing = required - set(links)
    if missing:
        raise ValidationError(f"formula hypothesis table missing fields: {sorted(missing)}")
    if len(links) != 108:
        raise ValidationError(f"expected 108 formula hypotheses, got {len(links)}")
    unknown_attributes = set(links["attribute_id"]) - set(ATTRIBUTE_CONTRACT_BY_ID)
    if unknown_attributes:
        raise ValidationError(f"hypotheses reference unknown attributes: {sorted(unknown_attributes)}")
    unknown_tools = set(links["tool_id"]) - set(SPECTRAL_TOOL_IDS)
    if unknown_tools:
        raise ValidationError(f"hypotheses reference unknown tools: {sorted(unknown_tools)}")
    if set(links["evidence_level"]) != {"formula_derived_hypothesis"}:
        raise ValidationError("all 108 relationships must remain formula-derived hypotheses")
    if "hypothesis_status" in links and set(links["hypothesis_status"]) != {HYPOTHESIS_STATUS}:
        raise ValidationError("formula hypothesis input contains an unauthorized status")
    for authority_field in (
        "production_authority",
        "dynamic_parameter_authority",
        "tool_routing_authority",
    ):
        if authority_field in links and links[authority_field].astype(str).str.lower().isin({"true", "1", "yes"}).any():
            raise ValidationError(f"formula hypothesis input cannot grant {authority_field}")
    links = links.copy()
    links["hypothesis_status"] = HYPOTHESIS_STATUS
    links["hypothesis_id"] = [
        "spectral_formula_hypothesis:" + hashlib.sha256(f"{tool}|{parameter}|{attribute}|{scope}".encode()).hexdigest()[:16]
        for tool, parameter, attribute, scope in zip(
            links["tool_id"],
            links["parameter_id"],
            links["attribute_id"],
            links["relation_scope"],
            strict=True,
        )
    ]
    return links


RESEARCH_TABLE_COLUMNS: Final[tuple[str, ...]] = (
    "observation_time",
    "available_at",
    "bar_frequency",
    "natural_time_span_sessions",
    "measurement_window_bars",
    "required_history_sessions",
    "observed_history_sessions",
    "required_history_bars",
    "observed_history_bars",
    "tool_id",
    "parameter_id",
    "attribute_id",
    "attribute_value",
    "output_unit",
    "data_quality_status",
    "data_version",
    "calculation_version",
    "tool_profile_version",
    "tool_parameter_digest",
    "contract_version",
    "hypothesis_status",
    "evidence_level",
    "relation_scope",
    "expected_relation",
    "hypothesis_id",
)


def build_spectral_attribute_research_table(
    panel: pd.DataFrame,
    hypotheses: pd.DataFrame,
    *,
    frequency: str,
    data_version: str,
) -> pd.DataFrame:
    """Materialize time × tool × parameter × attribute without testing validity."""

    if not data_version.strip():
        raise ValidationError("data_version is required")
    required_hypothesis_fields = {
        "tool_id",
        "parameter_id",
        "attribute_id",
        "hypothesis_status",
        "evidence_level",
        "relation_scope",
        "expected_relation",
        "hypothesis_id",
    }
    missing_hypothesis_fields = required_hypothesis_fields - set(hypotheses)
    if missing_hypothesis_fields:
        raise ValidationError(f"research-table hypotheses missing fields: {sorted(missing_hypothesis_fields)}")
    if set(hypotheses["hypothesis_status"]) != {HYPOTHESIS_STATUS}:
        raise ValidationError("research-table builder rejects upgraded hypotheses")
    if set(hypotheses["evidence_level"]) != {"formula_derived_hypothesis"}:
        raise ValidationError("research-table builder accepts only formula hypotheses")
    for authority_field in (
        "production_authority",
        "dynamic_parameter_authority",
        "tool_routing_authority",
    ):
        if authority_field in hypotheses and hypotheses[authority_field].astype(str).str.lower().isin({"true", "1", "yes"}).any():
            raise ValidationError(f"research-table builder cannot grant {authority_field}")
    outputs: list[pd.DataFrame] = []
    for tool_id in SPECTRAL_TOOL_IDS:
        tool_links = hypotheses.loc[hypotheses["tool_id"] == tool_id].copy()
        attributes = tuple(sorted(set(tool_links["attribute_id"])))
        measured = compute_spectral_kline_attributes(panel, frequency=frequency, tool_id=tool_id, attribute_ids=attributes)
        joined = measured.merge(
            tool_links[
                [
                    "tool_id",
                    "parameter_id",
                    "attribute_id",
                    "hypothesis_status",
                    "evidence_level",
                    "relation_scope",
                    "expected_relation",
                    "hypothesis_id",
                ]
            ],
            on=["tool_id", "attribute_id"],
            how="inner",
            validate="many_to_many",
        )
        joined["data_version"] = data_version
        outputs.append(joined)
    result = pd.concat(outputs, ignore_index=True)
    result = (
        result.loc[:, RESEARCH_TABLE_COLUMNS]
        .sort_values(
            ["tool_id", "parameter_id", "attribute_id", "observation_time"],
            kind="mergesort",
        )
        .reset_index(drop=True)
    )
    logical_key = [
        "observation_time",
        "bar_frequency",
        "tool_id",
        "parameter_id",
        "attribute_id",
        "hypothesis_id",
    ]
    if bool(result.duplicated(logical_key).any()):
        raise ValidationError("spectral research table logical key is not unique")
    return result


def read_attribute_timeseries(table: pd.DataFrame, attribute_id: str, *, tool_id: str | None = None) -> pd.DataFrame:
    rows = table.loc[table["attribute_id"] == attribute_id]
    if tool_id is not None:
        rows = rows.loc[rows["tool_id"] == tool_id]
    return rows.sort_values(
        ["bar_frequency", "tool_id", "parameter_id", "observation_time"],
        kind="mergesort",
    ).reset_index(drop=True)


def read_tool_attributes(table: pd.DataFrame, tool_id: str) -> pd.DataFrame:
    return (
        table.loc[table["tool_id"] == tool_id]
        .sort_values(["parameter_id", "attribute_id", "observation_time"], kind="mergesort")
        .reset_index(drop=True)
    )


def align_attribute_scales(tables: Sequence[pd.DataFrame], *, attribute_id: str) -> pd.DataFrame:
    """As-of align comparable measurements on the coarsest decision clock."""

    if attribute_id not in ATTRIBUTE_CONTRACT_BY_ID:
        raise ValidationError(f"unknown attribute id: {attribute_id}")
    selected: list[pd.DataFrame] = []
    for table in tables:
        required = {"attribute_id", "available_at", "bar_frequency", "output_unit"}
        missing = required - set(table)
        if missing:
            raise ValidationError(f"scale alignment table missing fields: {sorted(missing)}")
        rows = table.loc[table["attribute_id"] == attribute_id].copy()
        if not rows.empty:
            rows["available_at"] = pd.to_datetime(rows["available_at"], utc=True)
            selected.append(rows)
    if not selected:
        return pd.DataFrame({"alignment_time": pd.Series(dtype="datetime64[ns, UTC]")})
    combined = pd.concat(selected, ignore_index=True)
    unknown_frequencies = set(combined["bar_frequency"]) - set(FREQUENCY_PHYSICAL_SCALE)
    if unknown_frequencies:
        raise ValidationError(f"scale alignment has unknown frequencies: {sorted(unknown_frequencies)}")
    if combined["output_unit"].nunique() != 1:
        raise ValidationError("cross-frequency alignment requires one output unit")
    frequencies = tuple(sorted(set(combined["bar_frequency"])))
    if len(frequencies) > 1 and not ATTRIBUTE_CONTRACT_BY_ID[attribute_id].cross_frequency_comparable:
        raise ValidationError(f"{attribute_id} contract forbids direct cross-frequency comparison")
    if len(frequencies) == 1:
        combined["alignment_time"] = combined["available_at"]
        sort_fields = [
            field
            for field in (
                "alignment_time",
                "bar_frequency",
                "tool_id",
                "parameter_id",
            )
            if field in combined
        ]
        return combined.sort_values(
            sort_fields,
            kind="mergesort",
        ).reset_index(drop=True)

    anchor_frequency = max(
        frequencies,
        key=lambda value: FREQUENCY_PHYSICAL_SCALE[value][1],
    )
    anchor_times = (
        combined.loc[combined["bar_frequency"] == anchor_frequency, "available_at"].drop_duplicates().sort_values().reset_index(drop=True)
    )
    if anchor_times.empty:
        raise ValidationError("scale alignment has no causal decision clock")
    grouping_fields = [
        field
        for field in (
            "bar_frequency",
            "tool_id",
            "parameter_id",
            "hypothesis_id",
            "data_version",
        )
        if field in combined
    ]
    aligned_groups: list[pd.DataFrame] = []
    for _, group in combined.groupby(grouping_fields, sort=True, dropna=False):
        source = group.sort_values("available_at", kind="mergesort").drop_duplicates("available_at", keep="last")
        aligned = pd.merge_asof(
            pd.DataFrame({"alignment_time": anchor_times}),
            source,
            left_on="alignment_time",
            right_on="available_at",
            direction="backward",
            allow_exact_matches=True,
        )
        aligned = aligned.loc[aligned["attribute_id"].notna()]
        aligned_groups.append(aligned)
    if not aligned_groups:
        return pd.DataFrame({"alignment_time": pd.Series(dtype="datetime64[ns, UTC]")})
    result = pd.concat(aligned_groups, ignore_index=True)
    if bool((result["available_at"] > result["alignment_time"]).any()):
        raise ValidationError("scale alignment selected a future observation")
    sort_fields = [
        field
        for field in (
            "alignment_time",
            "bar_frequency",
            "tool_id",
            "parameter_id",
        )
        if field in result
    ]
    return result.sort_values(sort_fields, kind="mergesort").reset_index(drop=True)


def reverse_lookup_hypotheses(
    hypotheses: pd.DataFrame,
    *,
    attribute_id: str | None = None,
    tool_id: str | None = None,
    parameter_id: str | None = None,
) -> pd.DataFrame:
    result = hypotheses
    for field, value in (
        ("attribute_id", attribute_id),
        ("tool_id", tool_id),
        ("parameter_id", parameter_id),
    ):
        if value is not None:
            result = result.loc[result[field] == value]
    return result.sort_values(["tool_id", "parameter_id", "attribute_id"], kind="mergesort").reset_index(drop=True)


def deterministic_frame_digest(frame: pd.DataFrame) -> str:
    payload = frame.to_csv(index=False, lineterminator="\n", float_format="%.17g").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_synthetic_completed_bar_panel(
    *,
    periods: int = 520,
    start: str = "2016-01-04",
) -> pd.DataFrame:
    """Create deterministic OHLC evidence without reading any market dataset."""

    if periods < 400:
        raise ValidationError("synthetic acceptance panel needs at least 400 sessions")
    days = pd.bdate_range(start, periods=periods)
    position = np.arange(periods, dtype=float)
    returns = (
        0.00015
        + 0.0035 * np.sin(position / 9.0)
        + 0.0017 * np.cos(position / 23.0)
        + np.where((position.astype(int) % 97) == 0, -0.018, 0.0)
    )
    close = 1000.0 * np.exp(np.cumsum(returns))
    open_ = np.r_[close[0], close[:-1]]
    envelope = 0.0015 + 0.0005 * (1.0 + np.sin(position / 7.0))
    return pd.DataFrame(
        {
            "trading_day": days,
            "timestamp": days + pd.Timedelta(hours=15),
            "open": open_,
            "high": np.maximum(open_, close) * (1.0 + envelope),
            "low": np.minimum(open_, close) * (1.0 - envelope),
            "close": close,
        }
    )


def validate_data_isolation_ledger(ledger: Mapping[str, object]) -> None:
    if int(str(ledger.get("post_2020_rows_read", -1))) != 0:
        raise ValidationError("post-2020 rows must not be read")
    if bool(ledger.get("blackbox_detail_opened", True)):
        raise ValidationError("2021-2026 blackbox detail must remain closed")
    maximum = str(ledger.get("maximum_observation_time", ""))
    if maximum and pd.Timestamp(maximum).value >= pd.Timestamp("2021-01-01").value:
        raise ValidationError("data ledger crosses the 2020-12-31 isolation boundary")


def write_json(path: Path, payload: Mapping[str, object] | Sequence[object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


__all__ = [
    "ATTRIBUTE_CONTRACTS",
    "ATTRIBUTE_CONTRACT_BY_ID",
    "BLACKBOX_EXCLUSION",
    "CALCULATION_VERSION",
    "CONTRACT_SCHEMA_ID",
    "EXISTING_ATTRIBUTE_IDS",
    "HYPOTHESIS_STATUS",
    "NEW_ATTRIBUTE_IDS",
    "RESEARCH_TABLE_COLUMNS",
    "RESEARCH_TABLE_FIELD_LABELS_ZH",
    "RESEARCH_TABLE_SCHEMA_ID",
    "SPECTRAL_TOOL_IDS",
    "TOOL_PROFILES",
    "TOOL_PROFILE_VERSION",
    "ScaleContext",
    "align_attribute_scales",
    "audit_attribute_implementations",
    "build_attribute_contract_catalog",
    "build_synthetic_completed_bar_panel",
    "build_spectral_attribute_research_table",
    "compute_spectral_kline_attributes",
    "deterministic_frame_digest",
    "load_formula_hypotheses",
    "read_attribute_timeseries",
    "read_tool_attributes",
    "resolve_scale_context",
    "reverse_lookup_hypotheses",
    "validate_data_isolation_ledger",
    "write_json",
]
