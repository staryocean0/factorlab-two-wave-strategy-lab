# R5-B1 anti-persistence interaction — 有限稳定性诊断预分析

日期：2026-09-08

Parent identity：`R5_multiscale_serial_dependence_state_v1`

Diagnostic identity：`R5_B1_stability_shape_diagnostic_v1`

状态：`POST-R5 VALIDATION DIAGNOSTIC / REUSABLE TRAIN+VALIDATION / NO BLACKBOX`

## 1. 为什么允许做这一步

CL-20260908-007 已 cloud-reviewed。

R5-B1 满足原 frozen core gate：TRAIN interaction coefficient `<0`，且 VALIDATION pooled MSE 比 B0 更低；2019、2020 两年也都改善。

但 improvement 很小（pooled 约 0.152%），因此不能直接把它升级成 regime model 或策略候选。

本诊断使用已明确可反复查看的 TRAIN / VALIDATION。它**不是新的独立验证证据**，而是判断当前小幅增量是否具有足够广度与机制形状，值得继续研究。

## 2. 数据和模型必须完全复用 R5

不得改变：

- source：`data/development/5m_offset_0.parquet`；
- source SHA / 70,114 rows；
- TRAIN = 2015-01-05..2018-12-31；
- VALIDATION = 2019-01-01..2020-12-31；
- BLACKBOX = none；
- exact-5m continuous-segment semantics；
- 240-return causal volatility normalization；
- 960-row state history；
- short lags 1..3；
- long lags 12..18；
- B0 / B1 TRAIN fit definition。

必须重新得到与 CL-007 receipt 数值一致的 B0/B1 TRAIN coefficients 和 VALIDATION pooled MSE，作为 diagnostic entry gate。若不一致，停止诊断并报告 implementation drift。

## 3. Diagnostic D1 — 改善是否广泛分布在交易日

对每一个 VALIDATION trading day，用固定 TRAIN-fit B0/B1 预测，计算：

`day_improvement = MSE_B0_day - MSE_B1_day`

正值表示 B1 当天更好。

分别报告 pooled VALIDATION、2019、2020：

- number of trading days；
- mean day_improvement；
- median day_improvement；
- p10 / p90；
- fraction_days_B1_better；
- sample-weighted total MSE improvement（必须复现 CL-007 aggregate）。

### D1 support flag

只作为研究预算 gate，预先定义：

- 2019 `fraction_days_B1_better > 0.50` 且 median day_improvement > 0；
- 2020 `fraction_days_B1_better > 0.50` 且 median day_improvement > 0。

两年都满足才记：

`D1_day_breadth_supported = true`

否则说明 aggregate gain 可能较集中，不自动否定 B1，但不满足专门化所需的“广度”条件。

不搜索 favorable days / months / time-of-day。

## 4. Diagnostic D2 — anti-persistence 是否呈机制一致的形状

使用 TRAIN 的 B-candidate rows 中 `anti_persistence` 分布，冻结 20/40/60/80% quantile edges，得到 5 个固定 quintile bins。

这些 edge 只由 TRAIN feature distribution 决定，不看 next-return outcome。

把 TRAIN-fixed edges 原样应用到 VALIDATION。

在每个 quintile 内单独估计描述性经验关系：

`next_z = alpha_q + slope_q * z_t`

分别报告：

- TRAIN pooled；
- VALIDATION pooled；
- VALIDATION 2019；
- VALIDATION 2020。

每个 bin 报：n、mean anti_persistence、slope_q、MSE of within-bin fit。

本诊断不把 bin model 当生产模型，只检查机制形状。

### D2 support flag

对 VALIDATION pooled、2019、2020 分别计算：

1. `top_quintile_slope < bottom_quintile_slope`；
2. 对 5 个 `(mean_anti, slope)` 点做简单线性趋势，trend coefficient `<0`。

三组都满足才记：

`D2_shape_supported = true`

不要求 5 个 bin 严格逐点单调，避免把抽样噪声当硬门槛。

## 5. 最终诊断裁决

只允许：

- `R5_B1_diagnostic_supported_for_specialist_research`：D1=true 且 D2=true；
- `R5_B1_mechanism_shape_supported_but_day_breadth_weak`：D1=false 且 D2=true；
- `R5_B1_day_breadth_supported_but_shape_weak`：D1=true 且 D2=false；
- `R5_B1_small_gain_not_robust_enough_to_specialize`：D1=false 且 D2=false；
- `R5_B1_diagnostic_execution_drift_or_insufficient`：entry reproduction 或数据完整性失败。

只有第一种允许把 B1 交给专门 research identity；其它三种都不允许直接上 HMM/rSLDS/Koopman。

即使第一种成立，也仍然只是 TRAIN/VALIDATION research，不自动分配 BLACKBOX。

## 6. 禁止事项

- 不改 B1 模型；
- 不搜索新的 lag/window；
- 不按 diagnostic 结果挑 favorable day/month/sign/time；
- 不新增 volatility、trend、M0、volume 等特征；
- 不做 PnL / Sharpe；
- 不读 2021+；
- 不指定 BLACKBOX；
- 不把本诊断叫 fresh OOS。

Production authority = false。
