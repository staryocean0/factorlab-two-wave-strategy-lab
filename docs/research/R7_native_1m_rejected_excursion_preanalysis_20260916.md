# R7 — native 1m rejected-excursion path information

日期：2026-09-16

Identity：`R7_native_1m_rejected_excursion_v1`

状态：`FROZEN BEFORE REAL OUTCOME / BROAD SHALLOW SCREEN / NO BLACKBOX`

## 1. 研究问题

R7 不研究新的 shock threshold，也不是旧 T1 的复活。它回答一个连续型 path-information 问题：

> 在相同 official-5m endpoint displacement 下，如果 native 1m 路径曾经沿某方向走得更远、随后在 5m endpoint 前回撤，这个“被拒绝的 excursion”是否对下一段 5m return 提供额外的反向信息？

只使用 000852.SH 的 official 1m close 与 official 5m endpoint timestamp identity；不重采样价格，不读取 M0 structure cache，不使用 R5-B1 anti-persistence。

## 2. 数据

1m source：`data/development/1m_official.parquet`；rows=`350561`；SHA256=`755217afce9dec383e48cd46d591402fa90dc50897abeb3dc7097c9a18a109d4`。

5m endpoint reference：`data/development/5m_offset_0.parquet`；rows=`70114`；SHA256=`bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`。

TRAIN=2015-01-05..2018-12-31；VALIDATION=2019-01-01..2020-12-31；BLACKBOX=none。

Inventory 已在 outcome-blind 状态确认：official 5m endpoint 与 1m close timestamp/price identity 几乎完整；runner 只接受 exact same-day 1m contiguous path，任何缺口自动排除，不填补、不 resample。

## 3. Causal normalization

用 exact 1m close-to-close returns。`sigma_past_t` 固定为之前 240 个 admissible exact-1m returns 的 RMS，计算时 shift(1)，因此不包含 t 当前 1m return。

不搜索 sigma window。

## 4. Path construction

候选 endpoint `t` 必须同时满足：

- t 是 official 5m endpoint；
- t-5min 与 t+5min 也都是 official 5m endpoints；
- 从 t-5min 到 t+5min 的 11 个 native 1m closes 全部存在、同 trading day、每步 exact 1 minute；
- `sigma_past_t` 可用。

过去 path 从 `P[t-5]` 到 `P[t]`，共 5 个 native 1m returns。令：

- `d_k = log(P[t-5+k]/P[t-5])`, k=1..5；
- `e = d_k*`，其中 `k*` 是 `|d_k|` 最大的位置；若并列取最早位置；
- `endpoint_z = d_5 / (sigma_past_t * sqrt(5))`；
- `rejection_signed_z = sign(e) * (|e| - sign(e)*d_5) / (sigma_past_t*sqrt(5))`。

若 path extreme 就是 endpoint，则 rejection=0。正 rejection 表示上行 excursion 后向下回撤；负 rejection 表示下行 excursion 后向上回撤。

Outcome：

`next5_z = log(P[t+5]/P[t]) / (sigma_past_t*sqrt(5))`

## 5. Frozen models

B0：`next5_z = alpha + beta_endpoint * endpoint_z`

B1：`next5_z = alpha + beta_endpoint * endpoint_z + beta_rejection * rejection_signed_z`

只在 TRAIN 拟合 B0/B1，再固定系数评估 VALIDATION。VALIDATION/2019/2020 的本地 B1 fit 只用于描述 coefficient sign，不用于重新训练 fixed prediction。

机制方向预注册：`beta_rejection < 0`。

## 6. Frozen supply gate

全部满足才 supply=true：

- TRAIN candidates >= 30,000；VALIDATION >= 15,000；
- 2019、2020 各 >= 7,000；
- TRAIN positive-rejection >= 2,000 且 negative-rejection >= 2,000；
- VALIDATION positive-rejection >= 1,000 且 negative-rejection >= 1,000。

这些只约束 feature supply，不根据 outcome 选样本。

## 7. Frozen support gate

全部满足才记 `R7_supported_for_one_bounded_diagnostic`：

1. TRAIN B1 `beta_rejection < 0`；
2. local B1 `beta_rejection < 0` 在 VALIDATION pooled、2019、2020 都成立；
3. fixed TRAIN-fit B1 MSE < B0 MSE 在 VALIDATION pooled、2019、2020 都成立；
4. VALIDATION B0 residual symmetry：
   - `rejection_signed_z > 0` 的 mean residual `<0`；
   - `rejection_signed_z < 0` 的 mean residual `>0`。

Residual=`next5_z - fixed_TRAIN_B0_prediction`。该对称 gate 防止像 R6 一样由单方向事后支撑 pooled 结果。

不设置最小 MSE 改善幅度；若仅有极小增量，下一步只能做一次预注册 bounded stability/shape diagnostic，不能直接 specialist/BLACKBOX。

## 8. 裁决

只允许：

- `R7_supported_for_one_bounded_diagnostic`；
- `R7_supply_insufficient`；
- `R7_coefficient_direction_not_supported`；
- `R7_fixed_prediction_not_supported`；
- `R7_directional_symmetry_not_supported`；
- `R7_execution_drift_or_insufficient`。

## 9. 禁止事项

不得 outcome 后：改 5-return path、5-return outcome、240-return sigma、官方 endpoint anchor、模型项、rejection 定义、正负方向 gate、年份 gate；不得 threshold 搜索；不得按时段/年份/方向筛 favorable subset；不得加入 B1/M0/volume/high-low；不得 BLACKBOX/post-2020；不得 PnL/Sharpe；不得复杂模型 rescue。

Production authority=false。
