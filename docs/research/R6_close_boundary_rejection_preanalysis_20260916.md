# R6 — close-only failed-breakout / boundary-rejection preanalysis

日期：2026-09-16

Identity：`R6_close_boundary_rejection_v1`

状态：`FROZEN BEFORE REAL OUTCOME / BROAD SHALLOW SCREEN / NO BLACKBOX`

## 1. 机制

研究一个与 R5-B1 anti-persistence 不同源的简单机制：价格刚刚突破过去一小时的 close-only 边界，但下一根 5m bar 立即收回原边界内，是否意味着突破被拒绝，随后 15m 更偏向反转。

这不是旧 R2 的复活：R2 使用 M0/structure range state；R6 不读取 structure cache、wave morphology、parent range state，只使用 native 5m close 和 causal volatility normalization。

## 2. 数据与因果边界

Source：`data/development/5m_offset_0.parquet`；SHA256=`bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`；000852.SH；2015-01-05..2020-12-31。

TRAIN=2015-01-05..2018-12-31；VALIDATION=2019-01-01..2020-12-31；BLACKBOX=none。

只允许 exact same-day 5m contiguous segments。Vol normalization 固定复用 R5 的 240-return past RMS sigma，不搜索 window。

## 3. Event 定义

固定 boundary lookback = 12 bars = 60 minutes。

令 breakout bar 为 `t0`，其前 12 个 contiguous closes 的 max/min 分别为 upper/lower，且不包含 t0。

- upper breakout：`close[t0] > upper`，direction=+1；
- lower breakout：`close[t0] < lower`，direction=-1。

下一根 exact 5m bar 为 `t1`：

- failed/rejected：upper breakout 后 `close[t1] <= upper`，或 lower breakout 后 `close[t1] >= lower`；
- control/nonfailed：upper breakout 后 `close[t1] > upper`，或 lower breakout 后 `close[t1] < lower`。

不设 overshoot threshold，不搜索 boundary window，不按时段筛选。

## 4. Outcome

从 t1 已知 close 开始，固定观察未来 3 个 exact 5m returns（15m）：

`signed_forward_z3 = direction * (log(close[t1+3]) - log(close[t1])) / (sigma_past[t1] * sqrt(3))`

负值表示未来 15m 朝突破反方向运行，即 reversal。

主效应：

`mean_effect = mean(signed_forward_z3 | failed) - mean(signed_forward_z3 | control)`

预期 `<0`。

辅助方向：

`reversal_fraction_delta = P(signed_forward_z3<0 | failed) - P(...<0 | control)`

预期 `>0`。

## 5. Frozen gates

Supply 全部满足：

- TRAIN failed >=100，control >=200；
- VALIDATION failed >=50，control >=100；
- 2019、2020 各 failed >=20、control >=40；
- VALIDATION upper/lower 各 failed >=20、control >=40。

Direction 全部满足：

- TRAIN pooled：mean_effect<0 且 reversal_fraction_delta>0；
- VALIDATION pooled：mean_effect<0 且 reversal_fraction_delta>0；
- 2019 mean_effect<0；
- 2020 mean_effect<0；
- VALIDATION upper-only mean_effect<0；
- VALIDATION lower-only mean_effect<0。

只有 supply=true 且 direction=true 才记 `R6_supported_for_one_bounded_diagnostic`。

其它裁决：`R6_supply_insufficient`、`R6_direction_not_supported`、`R6_execution_drift_or_insufficient`。

## 6. 禁止事项

不得 outcome 后改变 12-bar boundary、1-bar rejection、3-bar horizon、sigma window、比较组、上下方向、年份或时段；不得加 B1 anti-persistence；不得用 M0 structure cache；不得 PnL/Sharpe；不得 BLACKBOX/post-2020；不得复杂模型 rescue。

Production authority=false。
