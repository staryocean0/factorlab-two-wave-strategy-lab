# R5-B1 specialist Stage 1 — 时间稳定性与连续效应形状预分析

日期：2026-09-16

Specialist identity：`R5_B1_anti_persistence_interaction_specialist_v1`

Stage identity：`R5_B1_specialist_stage1_stability_continuous_shape_v1`

状态：`FROZEN BEFORE REAL-DATA EXECUTION / REUSABLE TRAIN+VALIDATION / NO BLACKBOX`

## 1. 研究问题

CL-008 已支持 B1 进入 specialist research，但只证明了日度广度和 5-bin 机制形状。Stage 1 只回答两个更严格的问题：

1. `z_t × anti_persistence` interaction 是否在预定义时间块中持续存在，而不是由少数时期主导；
2. anti-persistence 增强时，经验 next-return slope 是否在更细的 TRAIN-fixed feature bins 中保持整体向下的连续形状。

本阶段不创建交易策略，不搜索 lag/window/feature，不读 BLACKBOX，不读 2021+，不做 PnL/Sharpe。

## 2. Parent construction 完全冻结

必须复用 R5/CL-008：CSI1000 `000852.SH` native 5m；source SHA256 `bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`；TRAIN=2015-01-05..2018-12-31；VALIDATION=2019-01-01..2020-12-31；exact-5m continuous segment；240-return causal volatility；960-row state history；short lags 1..3；long lags 12..18；anti_persistence=-short_memory；B0/B1 definitions unchanged。

执行入口必须先以 absolute tolerance `1e-12` 复现 CL-008 entry gate：TRAIN 41,685 rows；VALIDATION 21,428 rows；B0/B1 coefficients 与 validation MSE 均一致。失败立即停止。

## 3. S1 — 预定义半年块时间稳定性

不搜索月份，不按结果切块。固定 calendar half-year：2015H1..2018H2 共 8 个 TRAIN blocks；2019H1..2020H2 共 4 个 VALIDATION blocks。每块至少 1,000 candidate rows，否则判 execution insufficient。

每块报告：n；该块单独拟合 B1 的 interaction coefficient（只作描述）；以及 frozen global TRAIN-fit B0/B1 在该块的 MSE 与 `MSE_B0-MSE_B1`。

S1 support rule 全部满足才为 true：

- TRAIN 8 块中至少 6 块 local interaction coefficient < 0，且 TRAIN block coefficient median < 0；
- VALIDATION 4 块中至少 3 块 local interaction coefficient < 0，且 VALIDATION block coefficient median < 0；
- VALIDATION 4 块中至少 3 块 frozen B1 的 MSE improvement > 0。

不允许用本结果挑 favorable half-year。

## 4. S2 — TRAIN-fixed decile continuous-shape diagnostic

只用 TRAIN 的 `anti_persistence` feature distribution 冻结 10/20/.../90% quantile edges，形成 10 个 decile bins；edges 不看 next-return outcome，并原样应用于 VALIDATION。每个 group/bin 至少 100 rows，否则 execution insufficient。

对 TRAIN、VALIDATION pooled、2019、2020 分别在每个 bin 描述性拟合：`next_z = alpha_bin + slope_bin * z_t`。报告 n、mean anti、slope、MSE；再报告 10 个 `(mean_anti, slope)` 点的线性 trend、Spearman rank correlation，以及 bottom-20% 与 top-20% pooled empirical slope。

S2 support rule：

- TRAIN：trend < 0 且 top20 slope < bottom20 slope；
- VALIDATION pooled：trend < 0、Spearman <= -0.50、top20 slope < bottom20 slope；
- 2019：trend < 0 且 top20 slope < bottom20 slope；
- 2020：trend < 0 且 top20 slope < bottom20 slope。

不要求 10 bins 严格逐点单调，避免把抽样噪声变成伪门槛；也不把 decile bins 变成生产分段模型。

## 5. 预注册裁决

只允许：

- `R5_B1_specialist_stage1_stability_and_continuous_shape_supported`：S1=true 且 S2=true；
- `R5_B1_specialist_stage1_time_stable_but_shape_weak`：S1=true 且 S2=false；
- `R5_B1_specialist_stage1_shape_supported_but_time_stability_weak`：S1=false 且 S2=true；
- `R5_B1_specialist_stage1_not_robust_enough_for_transport`：S1=false 且 S2=false；
- `R5_B1_specialist_stage1_execution_drift_or_insufficient`：entry reproduction 或供给完整性失败。

只有第一种允许下一步进入 transport research；仍不自动分配 BLACKBOX，也不授权复杂 regime model 或经济交易映射。

Production authority = false。
