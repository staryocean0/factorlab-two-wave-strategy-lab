# ruff: noqa: E402
"""暴跌反弹桶（crash 槽）主策略 rebound_3level：ema_h4 三档 K 路由（冻结构造）。

分支：``market_state_crash_rebound_long_ema_h4_routing_r1``（bead fl-h86rt）。

用户授权的锁定决策（2026-08-17）：暴跌反弹桶主策略从 two_bucket_stop_up（2Bucket）
升级为 rebound_3level（ema_h4 轴三档 K 路由）。证据链：

* 开发段组合过门（fl-ypkjm）：Δ净 +0.1805 / Δ夏普 +0.0128 / 分布门 8/12，
  2Bucket 权威版上任以来首个组合口径过门挑战者；
* 单桶黑箱（fl-ya7nj）：2021-2026 Δ净 +0.053 / Δ夏普 +0.015 / 6 年全正 →
  fresh_challenge_passed；
* 组合账户卫冕赛（fl-l4xyy）：2021-2026 Δ净 +0.457 / Δ夏普 +0.486 / 分布门通过
  → champion_dethroned（SYNC_WIDE 已扩展至 2026-06-24，前缀 5.8e-12 复现）；
* 控制变量卫冕赛（fl-qvr1d）：锁定版基座下（ols=width_k1p0、paper=B_path_eff_w8）
  唯一变量=crash 槽，Δ净 +0.466 / Δ夏普 +0.448 / 分布门通过 →
  controlled_champion_dethroned，与原始卫冕赛双口径互证。

冻结构造（与 lat_long K=1.5 同构，仅入场门槛随轴缩放）：

* 轴 ema_h4 = log(open).diff().ewm(halflife=4, min_periods=2).mean().shift(1)
  （严格因果，正值=向上动量）；
* 通道：P64 一阶因果 Butterworth 低通中轨 + 48 棒带通残差 RMS
  （EWMA 半衰期 8）宽度 ×1.5；
* K 映射：轴值高于 0.00074198 → K=1.0；介于 [7.5511e-05, 0.00074198] → K=1.5；
  低于 7.5511e-05 → K=2.0（高动量 → 窄 K，单调）；
* 入场：收盘突破上轨（middle + width × K/1.5）；出场：收盘跌破中轨；
* T+1 强制（enforce_true_t_plus_one side="up"）；全部严格因果
  （runtime_uses_future=False）。

边界冻结值来自开发段（2009-2020）非崩溃窗口棒 q33/67，黑箱段禁止重算。
权威状态：用户授权的架构锁定；研究产物不授予生产权、参数权、路由权。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from factor_lab.market_state.research.ols_paper_explosive_bucket_battle_v1 import (
    enforce_true_t_plus_one,
)
from factor_lab.market_state.timing_paper_up_channel_latency_surface_r1 import (
    FrequencyChannelSpec,
    build_channel_rails_frequency_param,
)

CENTRE_PERIOD_BARS = 64
FILTER_ORDER = 1
THICKNESS_RMS_WINDOW = 48
THICKNESS_SMOOTHING_HALF_LIFE = 8.0
BASE_WIDTH_MULTIPLIER = 1.5
EMA_HALF_LIFE = 4.0
K_GRID = (1.0, 1.5, 2.0)
FROZEN_BOUNDARIES = np.asarray([7.551096522681333e-05, 0.0007419783855075914])
CONSTRUCTION_ID = "lat_long_ema_h4_routing"


def _ema_h4_axis(opens: pd.Series) -> np.ndarray:
    """ema_h4 因果动量轴（正值=向上；只用 t-1 及之前完成棒）。"""
    log_open = pd.Series(np.log(opens.to_numpy(float)), index=opens.index)
    returns = log_open.diff()
    return (
        returns.ewm(halflife=EMA_HALF_LIFE, min_periods=2)
        .mean()
        .shift(1)
        .to_numpy(float)
    )


def _validated(closes: pd.Series, opens: pd.Series) -> tuple[pd.Series, pd.Series]:
    if not isinstance(closes.index, pd.DatetimeIndex):
        raise TypeError("ema_h4 routing requires a DatetimeIndex")
    if not closes.index.equals(opens.index):
        raise ValueError("closes and opens must share the same DatetimeIndex")
    if (
        closes.empty
        or closes.index.has_duplicates
        or not closes.index.is_monotonic_increasing
    ):
        raise ValueError("ema_h4 routing requires unique ordered prices")
    close_numeric = pd.to_numeric(closes, errors="coerce").astype(float)
    open_numeric = pd.to_numeric(opens, errors="coerce").astype(float)
    if bool(close_numeric.le(0.0).any()) or bool(open_numeric.le(0.0).any()):
        raise ValueError("prices must be positive")
    return close_numeric, open_numeric


def build_crash_rebound_long_ema_h4_routing(
    closes: pd.Series, opens: pd.Series
) -> pd.DataFrame:
    """暴跌反弹桶主策略做多账户：ema_h4 三档 K 路由（冻结构造）。"""

    close_numeric, open_numeric = _validated(closes, opens)
    log_close = pd.Series(
        np.log(close_numeric.to_numpy(float)), index=close_numeric.index
    )
    axis = _ema_h4_axis(open_numeric)

    spec = FrequencyChannelSpec(
        centre_period_bars=CENTRE_PERIOD_BARS,
        filter_order=FILTER_ORDER,
        thickness_rms_window=THICKNESS_RMS_WINDOW,
        thickness_smoothing_half_life=THICKNESS_SMOOTHING_HALF_LIFE,
        width_multiplier=BASE_WIDTH_MULTIPLIER,
    )
    rails = build_channel_rails_frequency_param(close_numeric, spec)
    close = rails["log_close"].to_numpy(float)
    upper = rails["upper_log"].to_numpy(float)
    centre = rails["middle_log"].to_numpy(float)
    valid = rails["valid"].to_numpy(bool)

    n_levels = len(K_GRID)
    bin_index = (n_levels - 1) - np.searchsorted(FROZEN_BOUNDARIES, axis, side="left")
    bin_index = np.clip(bin_index, 0, n_levels - 1)
    k_at_bar = np.asarray(K_GRID, dtype=float)[bin_index]
    scale = np.where(np.isfinite(axis), k_at_bar / BASE_WIDTH_MULTIPLIER, 1.0)
    upper_adj = centre + (upper - centre) * scale

    holding_arr = np.zeros(len(close_numeric), dtype=bool)
    holding = False
    for location in range(len(close_numeric)):
        if not bool(valid[location]):
            holding = False
        elif not holding:
            holding = bool(close[location] > upper_adj[location])
        else:
            holding = bool(close[location] >= centre[location])
        holding_arr[location] = holding

    active = pd.Series(holding_arr, index=close_numeric.index, name="active_long")
    locked = enforce_true_t_plus_one(active, side="up").astype(float)

    frame = pd.DataFrame(
        {
            "active_long": active.astype(bool),
            "locked_long": locked,
            "account_long": locked,
        },
        index=close_numeric.index,
    )
    frame.attrs["runtime_uses_future"] = False
    frame.attrs["runtime_authority"] = False
    frame.attrs["construction"] = CONSTRUCTION_ID
    return frame
