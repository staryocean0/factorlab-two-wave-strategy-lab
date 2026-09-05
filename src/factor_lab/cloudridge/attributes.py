# pyright: reportAny=false, reportArgumentType=false
# pyright: reportAttributeAccessIssue=false, reportImplicitStringConcatenation=false
# pyright: reportMissingTypeStubs=false, reportReturnType=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""CloudRidge index attribute infrastructure.

This module promotes CloudRidge's low-level K-line diagnostics from strategy
research helpers into a reusable data surface.  It builds daily attribute time
series, multi-window moving averages, a human-readable dictionary, and a
manifest that future strategy work can consume without rediscovering where the
attributes came from.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd

from factor_lab.cloudridge.paper_kernel import (
    PAPER_KERNEL_SPAN_DAYS,
    build_paper_kernel_panel,
)
from factor_lab.indicators.directional_impulse import (
    DirectionalImpulseConfig,
    rolling_directional_impulse,
)
from factor_lab.indicators.jump_reversal_risk import (
    JumpReversalRiskConfig,
    rolling_jump_reversal_risk,
)
from factor_lab.indicators.path_weighted_bar_color_imbalance import (
    PathWeightedBarColorImbalanceConfig,
    rolling_path_weighted_bar_color_imbalance,
)

ATTRIBUTE_WINDOWS: Final[tuple[int, ...]] = (20, 50, 100, 200, 300, 400, 500)
ATTRIBUTE_MA_WINDOWS: Final[tuple[int, ...]] = (20, 50, 100, 200, 300, 400, 500)
DEFAULT_OUTPUT_DIR: Final[Path] = Path("output/cloudridge-attributes/current")
DEFAULT_LATEST_5M_SOURCE: Final[Path] = Path(
    "output/cloudridge_full_datahub_20260618/cloudridge_5m_qfq_service_confirmed_20080101_20260615_levels.csv"
)
DEFAULT_DAILY_SOURCE: Final[Path] = Path(
    "output/filter-parameter-workflow/cloudridge_20260521/"
    "service_confirmed_qfq_levels/"
    "cloudridge_1d_qfq_service_confirmed_20080101_20260519_levels.csv"
)


@dataclass(frozen=True, slots=True)
class CloudRidgeAttributeSpec:
    """Dictionary row for one CloudRidge attribute family."""

    attribute_id: str
    family: str
    plain_meaning_zh: str
    high_value_meaning_zh: str
    low_value_meaning_zh: str
    short_window_read_zh: str
    long_window_read_zh: str
    market_structure_read_zh: str
    formula_summary: str
    default_windows: str
    raw_column_pattern: str
    timing_role: str
    source_module: str
    caveat: str


ATTRIBUTE_SPECS: Final[tuple[CloudRidgeAttributeSpec, ...]] = (
    CloudRidgeAttributeSpec(
        attribute_id="bdci",
        family="direction_continuity",
        plain_meaning_zh="K线方向连续度，衡量近期涨跌方向是否少切换。",
        high_value_meaning_zh="方向更连续，趋势/单边路径更友好。",
        low_value_meaning_zh="涨跌切换频繁，更偏震荡或噪声。",
        short_window_read_zh=(
            "20/50 日 BDCI 抬升通常表示最近一段行情开始沿同一方向推进；快速回落则表示短线涨跌切换变密，追随型滤波更容易被反复打断。"
        ),
        long_window_read_zh=(
            "200/300/500 日 BDCI 描述的是市场底层是否长期单向化。"
            "长窗高值不是买点，而是说明过去很长时间内参与者行为同向，"
            "趋势惯性和拥挤交易可能同时存在。"
        ),
        market_structure_read_zh=(
            "BDCI 只看方向切换，不看涨跌幅。它适合回答“市场是否有连续方向”，不适合单独回答“方向是否足够强”。需要和 WBI/DII/波动一起读。"
        ),
        formula_summary="100 * (1 - close-to-close direction switch rate)",
        default_windows=str(ATTRIBUTE_WINDOWS),
        raw_column_pattern="bdci_w{window}",
        timing_role="state_or_gate_candidate",
        source_module="factor_lab.indicators.bar_direction_continuity",
        caveat="诊断指标，不直接等于买卖点或风险信号。",
    ),
    CloudRidgeAttributeSpec(
        attribute_id="bci",
        family="bar_color",
        plain_meaning_zh="K线颜色比例，统计上涨/下跌K线占比和净偏斜。",
        high_value_meaning_zh="上涨K线占比或净偏斜更强。",
        low_value_meaning_zh="下跌K线占比或净偏斜更强。",
        short_window_read_zh=(
            "20/50 日 BCI 更像短线投票结果：最近上涨日多还是下跌日多。短窗突然转弱常代表局部承接开始变差，但不说明下跌幅度。"
        ),
        long_window_read_zh=(
            "300/400/500 日 bci_upshare 偏高时，常表示长期上涨日数量占优，"
            "市场积累了较长时间的顺风路径和潜在获利盘；一旦方向压力断裂，"
            "这种长期同向积累可能成为流动性踩踏的燃料。"
        ),
        market_structure_read_zh=(
            "BCI 是“颜色结构”而不是“力度结构”。它能刻画筹码和情绪是否长期偏多，"
            "但必须和 WBI、path_efficiency 或波动类指标确认这些颜色是否有幅度"
            "和路径强度。"
        ),
        formula_summary="up_share - down_share over close-to-close returns",
        default_windows=str(ATTRIBUTE_WINDOWS),
        raw_column_pattern="bci_{upshare|downshare|imbalance}_w{window}",
        timing_role="state_or_factor_candidate",
        source_module="factor_lab.indicators.bar_color_imbalance",
        caveat="BCI 不看路径强度，需和 WBI/PWBCI/DII 区分。",
    ),
    CloudRidgeAttributeSpec(
        attribute_id="wbi",
        family="weighted_direction",
        plain_meaning_zh="加权K线偏斜，用涨跌幅度权重衡量净方向压力。",
        high_value_meaning_zh="上涨幅度权重大于下跌幅度权重。",
        low_value_meaning_zh="下跌幅度权重大于上涨幅度权重。",
        short_window_read_zh=(
            "20/50 日 WBI 描述最近上涨幅度和下跌幅度谁在主导。短窗 WBI 从正转弱，通常比 BCI 更能说明局部卖压开始有实际幅度。"
        ),
        long_window_read_zh=(
            "200/300/500 日 WBI 是长期方向压力的背景。长窗仍偏强而短窗先转弱，常见于大周期尚未完全坏掉、但局部流动性已经开始断裂的阶段。"
        ),
        market_structure_read_zh=(
            "WBI 可以看作云脊指数的净方向压力表。它把上涨日/下跌日按幅度加权，"
            "所以比 BCI 更接近市场真实推动力，但仍然只是状态，不是未来收益标签。"
        ),
        formula_summary="sum(log_return) / sum(abs(log_return))",
        default_windows=str(ATTRIBUTE_WINDOWS),
        raw_column_pattern="wbi_w{window}",
        timing_role="state_or_gate_candidate",
        source_module="factor_lab.indicators.weighted_bar_imbalance",
        caveat="方向压力指标，不应和未来收益标签混淆。",
    ),
    CloudRidgeAttributeSpec(
        attribute_id="pwbci",
        family="path_weighted_bar_color",
        plain_meaning_zh="路径强度加权K线颜色偏斜，是 BCI 乘以路径强度分位。",
        high_value_meaning_zh="多根上涨K线且路径强度较高。",
        low_value_meaning_zh="多根下跌K线且路径强度较高。",
        short_window_read_zh=(
            "20/50 日 PWBCI 适合观察短期颜色偏斜是否真的伴随路径强度。它能过滤一部分“上涨日很多但每根都很弱”的虚弱状态。"
        ),
        long_window_read_zh=(
            "长窗 PWBCI 描述的是长期颜色偏斜是否持续带有路径能量。它更像趋势许可或反卖出保护候选，而不是单独的风险触发器。"
        ),
        market_structure_read_zh=(
            "PWBCI 把 BCI 的数量投票和路径强度结合，适合回答颜色偏斜"
            "有没有真实行进距离。"
            "但 path_rank 是历史秩，跨时期直接比较时要防止把秩当成绝对市场温度。"
        ),
        formula_summary="BCI imbalance * rolling path_abs_return rank",
        default_windows=str(ATTRIBUTE_WINDOWS),
        raw_column_pattern="pwbci_{score|path_rank|imbalance}_w{window}",
        timing_role="state_or_factor_candidate",
        source_module="factor_lab.indicators.path_weighted_bar_color_imbalance",
        caveat="path_rank 是历史滚动秩，不能当作绝对数值门独立使用。",
    ),
    CloudRidgeAttributeSpec(
        attribute_id="dii",
        family="directional_impulse",
        plain_meaning_zh="方向冲量，衡量净位移、路径能量和路径效率合成的方向强度。",
        high_value_meaning_zh="上涨冲量更强。",
        low_value_meaning_zh="下跌冲量更强。",
        short_window_read_zh=(
            "20/50 日 DII 对短期强位移很敏感，适合描述行情是否已经打出方向冲量。它可能接近同步指标，不能自动当成提前预警。"
        ),
        long_window_read_zh=(
            "长窗 DII 描述大周期是否存在持续净位移和路径能量。长窗高值更像大背景趋势强度，长窗低值更像长期路径缺乏方向效率。"
        ),
        market_structure_read_zh=(
            "DII 把方向、能量和效率合成，解释力强但也更容易混入已经发生的行情结果。"
            "适合作为状态侧写或触发候选，必须用事件前可见值做严格验证。"
        ),
        formula_summary="impulse * (0.5 + 0.5 * abs(efficiency))",
        default_windows=str(ATTRIBUTE_WINDOWS),
        raw_column_pattern="dii_{score|impulse|efficiency|energy}_w{window}",
        timing_role="state_or_trigger_candidate",
        source_module="factor_lab.indicators.directional_impulse",
        caveat="可能接近同步状态，做门控前必须用事件前可见值验证。",
    ),
    CloudRidgeAttributeSpec(
        attribute_id="jrr",
        family="jump_reversal",
        plain_meaning_zh="跳变反转风险，衡量强涨/强跌K线无缓冲快速反向的状态。",
        high_value_meaning_zh="滤波滞后和反转失败风险更高。",
        low_value_meaning_zh="强K线反向跳变压力较低。",
        short_window_read_zh=("20/50 日 JRR 抬升通常表示最近强K线后快速反向的情况变多，滤波跟随和追涨杀跌更容易遇到假突破或急反。"),
        long_window_read_zh=(
            "长窗 JRR 更像市场结构是否长期充满跳变和反杀。长期高值说明行情的连续性差、反转成本高；长期低值说明跳变反杀压力较小。"
        ),
        market_structure_read_zh=(
            "JRR 适合描述滤波失效风险和暴跌后反弹/再入场环境，但它含波动秩和反转率，常偏同步，不能被包装成独立领先因子。"
        ),
        formula_summary="no-buffer reversal rate scaled by volatility ranks",
        default_windows=str(ATTRIBUTE_WINDOWS),
        raw_column_pattern="jrr_{score|reversal_rate|volatility_rank}_w{window}",
        timing_role="state_or_risk_candidate",
        source_module="factor_lab.indicators.jump_reversal_risk",
        caveat="含波动秩成分，容易偏同步，必须防止未来函数。",
    ),
    CloudRidgeAttributeSpec(
        attribute_id="lag_autocorr",
        family="return_memory",
        plain_meaning_zh="收益记忆性，衡量日收益与 lag1/lag4 历史收益的滚动相关。",
        high_value_meaning_zh="同向延续性更强。",
        low_value_meaning_zh="反向修复或震荡更强。",
        short_window_read_zh=(
            "20/50 日 lag1 更偏日内到隔日的短记忆，正值表示涨跌容易延续，"
            "负值表示短线反向修复更强。短窗 lag4 可粗略观察一周节奏是否有延续或反杀。"
        ),
        long_window_read_zh=(
            "200/300/500 日 lag4 更像周节奏承接状态。"
            "长窗 lag4 明显偏低时，常表示周内方向性开始缺失，"
            "上涨和下跌互相打断，承接结构比表面趋势更脆。"
        ),
        market_structure_read_zh=(
            "lag memory 描述的是市场参与者行为的时间记忆。"
            "它不说明方向本身，而说明方向发生后是否容易被接力、被反向修复，"
            "因此适合作为流动性驱动行情的门控状态。"
        ),
        formula_summary="rolling corr(log_return, log_return.shift(lag))",
        default_windows=str(ATTRIBUTE_WINDOWS),
        raw_column_pattern="lag{1|4}_autocorr_w{window}",
        timing_role="state_or_gate_candidate",
        source_module="factor_lab.cloudridge.attributes",
        caveat="相关性不是因果；长窗可作门控状态，短窗更偏噪声。",
    ),
    CloudRidgeAttributeSpec(
        attribute_id="volatility",
        family="path_volatility",
        plain_meaning_zh="路径波动和波动变化，用于描述行情底层活跃度。",
        high_value_meaning_zh="市场运动更活跃，波动聚集或状态切换更明显。",
        low_value_meaning_zh="市场运动更钝化，流动性驱动暴跌空间可能更小。",
        short_window_read_zh=(
            "20/50 日波动抬升通常说明行情已经开始活跃或状态切换。它对暴跌很敏感，但往往和暴跌同步，不能直接当开门的领先理由。"
        ),
        long_window_read_zh=(
            "200/300/500 日波动和 mean_abs_return 描述长期市场弹性。"
            "长期低波动可能意味着市场被钝化、控盘或成交结构更稳定，"
            "流动性踩踏空间可能被压缩；长期高波动则说明市场更容易放大冲击。"
        ),
        market_structure_read_zh=(
            "波动族是市场活跃度和冲击放大器，不是方向。更适合做状态门或风险预算背景，不能用暴跌发生后的波动抬升反推暴跌前开门。"
        ),
        formula_summary="rolling std(abs/log_return), mean abs return, vol-of-vol",
        default_windows=str(ATTRIBUTE_WINDOWS),
        raw_column_pattern="volatility_w{window}; vol_of_vol_w{window}",
        timing_role="gate_candidate",
        source_module="factor_lab.cloudridge.attributes",
        caveat="波动率本身常偏同步；基础设施只暴露状态，不直接预测。",
    ),
    CloudRidgeAttributeSpec(
        attribute_id="path_efficiency",
        family="path_shape",
        plain_meaning_zh="路径效率，衡量净位移占总路径长度的比例。",
        high_value_meaning_zh="路径更单边。",
        low_value_meaning_zh="来回震荡抵消较多。",
        short_window_read_zh=("20/50 日路径效率抬升说明最近行情走得更直，回落则表示同样的波动里来回抵消更多，短线方向质量下降。"),
        long_window_read_zh=(
            "长窗路径效率描述大周期是否长期单边推进。"
            "长窗高效率叠加强 BCI/WBI 可能表示长期同向拥挤；"
            "长窗低效率则说明市场长期有波动但缺乏净方向。"
        ),
        market_structure_read_zh=(
            "path_efficiency 是形状指标，不带方向。它回答“走得直不直”，不回答“向上还是向下”；必须和 WBI/DII 或 bci_imbalance 合读。"
        ),
        formula_summary="abs(sum(log_return)) / sum(abs(log_return))",
        default_windows=str(ATTRIBUTE_WINDOWS),
        raw_column_pattern="path_efficiency_w{window}",
        timing_role="state_or_gate_candidate",
        source_module="factor_lab.cloudridge.attributes",
        caveat="只描述形态，不说明方向；需和 WBI/DII 搭配读。",
    ),
    CloudRidgeAttributeSpec(
        attribute_id="paper_ewma_kernel_return",
        family="return_process_realized_kernel",
        plain_meaning_zh=("论文欧式趋势系统在每个EWMA尺度上的当日实现毛收益核，一日一点。"),
        high_value_meaning_zh=("当日标准化收益与前一日该尺度EWMA信号同向，论文线性核当日为正。"),
        low_value_meaning_zh=("当日标准化收益与前一日该尺度EWMA信号反向，论文线性核当日为负。"),
        short_window_read_zh=("1/2/3/4/5/10/15/20日点反应快、峰度高，应当作为原始时序交给下游聚合，不得根据单日正负直接路由。"),
        long_window_read_zh=("100至500日依然是同一论文内核的不同EWMA尺度，不是额外估计窗。长尺度日点仍需在一段历史上聚合后才能解读。"),
        market_structure_read_zh=("这是论文原式的最小可审计数据点。它没有减去局部均值乘积，没有第二估计窗，也没有趋势/反转标签。"),
        formula_summary=("f_s,t=(0.15/sqrt(260))*sqrt((1+nu_s)/(1-nu_s))*EWMA_s(z)_(t-1)*z_t"),
        default_windows=str(PAPER_KERNEL_SPAN_DAYS),
        raw_column_pattern="paper_kernel_daily_gross_return_s{span}",
        timing_role="research_factor_timeseries_input",
        source_module="factor_lab.cloudridge.paper_kernel",
        caveat=("t日收盘后才可用，只能决定t+1；连续线性毛收益核不是第14工具实际收益，不授权调参、路由或生产交易。"),
    ),
)


def load_cloudridge_daily_panel(source_path: Path | str | None = None) -> pd.DataFrame:
    """Load CloudRidge close data as one daily row per trading day.

    If no explicit source is supplied, the newest 5m DataHub export is preferred
    and collapsed to the last bar of each trading day.  The older confirmed 1d
    export is the fallback.
    """

    source = _resolve_source_path(source_path)
    raw = pd.read_csv(source)
    required = {"timestamp", "trading_day", "close"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"CloudRidge source missing columns: {sorted(missing)}")
    frame = raw.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame["trading_day"] = pd.to_datetime(frame["trading_day"], errors="coerce")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.dropna(subset=["timestamp", "trading_day", "close"])
    frame = frame.sort_values(["trading_day", "timestamp"])
    daily = frame.groupby("trading_day", as_index=False).tail(1)
    daily = daily[["trading_day", "timestamp", "close"]].copy()
    daily["source_path"] = str(source)
    daily["source_frequency"] = _infer_source_frequency(raw)
    return daily.reset_index(drop=True)


def build_attribute_dictionary() -> pd.DataFrame:
    """Return the canonical CloudRidge attribute dictionary."""

    return pd.DataFrame([asdict(spec) for spec in ATTRIBUTE_SPECS])


def build_cloudridge_attribute_panel(
    daily_panel: pd.DataFrame,
    *,
    windows: tuple[int, ...] = ATTRIBUTE_WINDOWS,
) -> pd.DataFrame:
    """Build raw CloudRidge attribute time series from daily closes."""

    frame = _normalize_daily_panel(daily_panel)
    close = frame["close"]
    log_return = _log_return(close)
    panel = pd.DataFrame(
        {
            "trading_day": frame["trading_day"],
            "timestamp": frame["timestamp"],
            "close": close,
            "log_return": log_return,
            "abs_log_return": log_return.abs(),
        }
    )
    attribute_columns: dict[str, pd.Series | np.ndarray] = {}
    sign = np.sign(log_return).replace(0.0, np.nan)
    for window in windows:
        upshare = (log_return > 0.0).rolling(window).mean()
        downshare = (log_return < 0.0).rolling(window).mean()
        path_abs = log_return.abs().rolling(window).sum()
        net = log_return.rolling(window).sum()
        volatility = log_return.rolling(window).std()
        attribute_columns.update(
            {
                f"bdci_w{window}": _bdci(sign=sign, window=window),
                f"bci_upshare_w{window}": upshare,
                f"bci_downshare_w{window}": downshare,
                f"bci_imbalance_w{window}": upshare - downshare,
                f"wbi_w{window}": net / path_abs.replace(0.0, np.nan),
                f"path_efficiency_w{window}": (net.abs() / path_abs.replace(0.0, np.nan)),
                f"lag1_autocorr_w{window}": log_return.rolling(window).corr(log_return.shift(1)),
                f"lag4_autocorr_w{window}": log_return.rolling(window).corr(log_return.shift(4)),
                f"volatility_w{window}": volatility,
                f"vol_of_vol_w{window}": volatility.rolling(window).std(),
                f"mean_abs_return_w{window}": (log_return.abs().rolling(window).mean()),
            }
        )

        pwbci = rolling_path_weighted_bar_color_imbalance(
            close,
            config=PathWeightedBarColorImbalanceConfig(
                window=window,
                path_rank_window=max(252, window),
            ),
        )
        attribute_columns[f"pwbci_score_w{window}"] = pwbci["score"].to_numpy()
        attribute_columns[f"pwbci_path_rank_w{window}"] = pwbci["path_rank"].to_numpy()
        attribute_columns[f"pwbci_imbalance_w{window}"] = pwbci["imbalance"].to_numpy()

        dii = rolling_directional_impulse(
            close,
            config=DirectionalImpulseConfig(window=window),
        )
        attribute_columns[f"dii_score_w{window}"] = dii["score"].to_numpy()
        attribute_columns[f"dii_impulse_w{window}"] = dii["impulse"].to_numpy()
        attribute_columns[f"dii_efficiency_w{window}"] = dii["efficiency"].to_numpy()
        attribute_columns[f"dii_energy_w{window}"] = dii["energy"].to_numpy()

        jrr = rolling_jump_reversal_risk(
            close,
            config=JumpReversalRiskConfig(window=window, rank_window=max(252, window)),
        )
        attribute_columns[f"jrr_score_w{window}"] = jrr["score"].to_numpy()
        attribute_columns[f"jrr_reversal_rate_w{window}"] = jrr["no_buffer_reversal_rate"].to_numpy()
        attribute_columns[f"jrr_volatility_rank_w{window}"] = jrr["volatility_rank"].to_numpy()
        attribute_columns[f"jrr_vol_of_vol_rank_w{window}"] = jrr["vol_of_vol_rank"].to_numpy()
    paper_kernel = build_paper_kernel_panel(frame[["timestamp", "close"]]).drop(columns=["timestamp", "normalized_return_z_t"])
    return_columns = paper_kernel.filter(like="paper_kernel_daily_gross_return_s")
    attribute_columns.update({column: return_columns[column].to_numpy(dtype=float) for column in return_columns.columns})
    return pd.concat([panel, pd.DataFrame(attribute_columns)], axis=1)


def build_cloudridge_attribute_ma_panel(
    attribute_panel: pd.DataFrame,
    *,
    ma_windows: tuple[int, ...] = ATTRIBUTE_MA_WINDOWS,
) -> pd.DataFrame:
    """Build multi-window moving averages for every numeric attribute column."""

    id_columns = ["trading_day", "timestamp"]
    numeric_columns = [
        column
        for column in attribute_panel.select_dtypes(include=[np.number]).columns
        if column not in {"close"} and not column.startswith("paper_kernel_daily_gross_return_")
    ]
    ma_columns: dict[str, pd.Series] = {}
    for column in numeric_columns:
        for window in ma_windows:
            ma_columns[f"{column}_ma{window}"] = attribute_panel[column].rolling(window).mean()
    return pd.concat(
        [attribute_panel[id_columns].copy(), pd.DataFrame(ma_columns)],
        axis=1,
    )


def build_cloudridge_attribute_bundle(
    *,
    source_path: Path | str | None = None,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    windows: tuple[int, ...] = ATTRIBUTE_WINDOWS,
    ma_windows: tuple[int, ...] = ATTRIBUTE_MA_WINDOWS,
    write_plots: bool = True,
) -> dict[str, object]:
    """Build and write the full CloudRidge attribute infrastructure bundle."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    daily = load_cloudridge_daily_panel(source_path)
    dictionary = build_attribute_dictionary()
    attributes = build_cloudridge_attribute_panel(daily, windows=windows)
    moving_averages = build_cloudridge_attribute_ma_panel(
        attributes,
        ma_windows=ma_windows,
    )
    dictionary_path = output / "cloudridge_attribute_dictionary.csv"
    attribute_path = output / "cloudridge_attribute_panel_1d.csv"
    ma_path = output / "cloudridge_attribute_ma_panel_1d.csv"
    manifest_path = output / "cloudridge_attribute_manifest.json"
    dictionary.to_csv(dictionary_path, index=False)
    attributes.to_csv(attribute_path, index=False)
    moving_averages.to_csv(ma_path, index=False)
    plot_files: list[str] = []
    if write_plots:
        plot_files = _write_attribute_plots(
            attributes,
            moving_averages,
            output / "plots",
        )
    non_id_columns = {"trading_day", "timestamp"}
    manifest: dict[str, object] = {
        "schema_version": "cloudridge_attribute_infrastructure_v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "source_path": str(daily["source_path"].iloc[0]) if not daily.empty else None,
        "source_frequency": (str(daily["source_frequency"].iloc[0]) if not daily.empty else None),
        "row_count": int(len(attributes)),
        "attribute_column_count": int(len([c for c in attributes.columns if c not in non_id_columns])),
        "ma_column_count": int(len([c for c in moving_averages.columns if c not in non_id_columns])),
        "latest_trading_day": (str(pd.to_datetime(attributes["trading_day"]).dt.date.iloc[-1]) if not attributes.empty else None),
        "attribute_windows": list(windows),
        "moving_average_windows": list(ma_windows),
        "files": {
            "dictionary": str(dictionary_path),
            "attribute_panel_1d": str(attribute_path),
            "moving_average_panel_1d": str(ma_path),
            "manifest": str(manifest_path),
            "plots": plot_files,
        },
        "authority_note": (
            "This bundle is an infrastructure surface. It describes CloudRidge "
            "K-line attributes and their moving averages; it does not promote "
            "any attribute into a production strategy signal by itself."
        ),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def _resolve_source_path(source_path: Path | str | None) -> Path:
    if source_path is not None:
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(source)
        return source
    if DEFAULT_LATEST_5M_SOURCE.exists():
        return DEFAULT_LATEST_5M_SOURCE
    if DEFAULT_DAILY_SOURCE.exists():
        return DEFAULT_DAILY_SOURCE
    raise FileNotFoundError(f"No CloudRidge source found. Expected one of: {DEFAULT_LATEST_5M_SOURCE}, {DEFAULT_DAILY_SOURCE}")


def _infer_source_frequency(raw: pd.DataFrame) -> str:
    if "frequency" not in raw.columns or raw.empty:
        return "unknown"
    values = raw["frequency"].dropna().astype(str).unique()
    if len(values) == 1:
        return values[0]
    return "mixed"


def _normalize_daily_panel(daily_panel: pd.DataFrame) -> pd.DataFrame:
    required = {"trading_day", "timestamp", "close"}
    missing = required - set(daily_panel.columns)
    if missing:
        raise ValueError(f"daily_panel missing columns: {sorted(missing)}")
    frame = daily_panel.copy()
    frame["trading_day"] = pd.to_datetime(frame["trading_day"], errors="coerce")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.dropna(subset=["trading_day", "timestamp", "close"])
    frame = frame.sort_values(["trading_day", "timestamp"]).drop_duplicates(
        "trading_day",
        keep="last",
    )
    frame = frame.reset_index(drop=True)
    if frame.empty:
        raise ValueError("daily_panel has no valid CloudRidge rows")
    return frame


def _log_return(close: pd.Series) -> pd.Series:
    ratio = close / close.shift(1)
    return ratio.apply(
        lambda value: math.log(value) if value is not None and math.isfinite(float(value)) and float(value) > 0.0 else math.nan
    )


def _bdci(*, sign: pd.Series, window: int) -> pd.Series:
    valid_pair = sign.notna() & sign.shift(1).notna()
    switch = valid_pair & sign.ne(sign.shift(1))
    denominator = valid_pair.astype(float).rolling(window).sum()
    switch_rate = switch.astype(float).rolling(window).sum() / denominator
    return 100.0 * (1.0 - switch_rate)


def _write_attribute_plots(
    attributes: pd.DataFrame,
    moving_averages: pd.DataFrame,
    plot_dir: Path,
) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plot_dir.mkdir(parents=True, exist_ok=True)
    candidates = [
        "bdci_w300",
        "bci_imbalance_w300",
        "wbi_w300",
        "pwbci_score_w300",
        "dii_score_w300",
        "lag1_autocorr_w300",
        "lag4_autocorr_w300",
        "volatility_w300",
        "vol_of_vol_w300",
        "jrr_score_w300",
        "path_efficiency_w300",
        "paper_kernel_daily_gross_return_s60",
    ]
    x = pd.to_datetime(attributes["trading_day"])
    files: list[str] = []
    for column in candidates:
        if column not in attributes.columns:
            continue
        fig, ax = plt.subplots(figsize=(12, 4.5))
        ax.plot(x, attributes[column], label=column, linewidth=0.9, alpha=0.65)
        for ma_window in (100, 300, 500):
            ma_column = f"{column}_ma{ma_window}"
            if ma_column in moving_averages.columns:
                ax.plot(
                    x,
                    moving_averages[ma_column],
                    label=f"MA{ma_window}",
                    linewidth=1.0,
                )
        ax.set_title(f"CloudRidge {column}")
        ax.set_xlabel("trading_day")
        ax.legend(loc="best", fontsize=8)
        ax.grid(True, alpha=0.2)
        fig.tight_layout()
        path = plot_dir / f"{column}.png"
        fig.savefig(path, dpi=140)
        plt.close(fig)
        files.append(str(path))
    return files
