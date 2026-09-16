# R7 bounded diagnostic — stability + rejection-magnitude shape

日期：2026-09-16

Parent identity：`R7_native_1m_rejected_excursion_v1`

Diagnostic identity：`R7_rejected_excursion_stability_shape_diagnostic_v1`

状态：`FROZEN BEFORE DIAGNOSTIC OUTCOME / REUSABLE TRAIN+VALIDATION / NO BLACKBOX`

## 1. 为什么允许

R7 broad shallow screen 已按 outcome-blind protocol 执行并 cloud-reviewed：candidate supply 充足；TRAIN/VALIDATION/2019/2020 rejection coefficient 均为负；fixed TRAIN B1 在 VALIDATION、2019、2020 都改善；正负 rejected excursion residual symmetry 均通过。

Parent adjudication=`R7_supported_for_one_bounded_diagnostic`。

本次是 R7 唯一一次 bounded diagnostic，不改变 parent model，不新增交易条件。

## 2. Entry reproduction

必须复用 frozen R7 sources / construction / models，并在 diagnostic 前复现：

- candidate rows=`64215`；
- TRAIN B0 beta=`[0.0137526453386167, 0.04853230586734814]`；
- TRAIN B1 beta=`[0.0014301524091757736, 0.06384569479627833, -0.5327696198414718]`；
- VALIDATION B0/B1 MSE=`1.6598472863016687 / 1.6349712859035168`；
- 2019 B0/B1 MSE=`1.7444187739434946 / 1.720788967326843`；
- 2020 B0/B1 MSE=`1.5749277678465021 / 1.5488004452973783`。

absolute tolerance=`1e-12`。失败即停止为 `R7_diagnostic_execution_drift_or_insufficient`。

## 3. D1 — fixed half-year stability

不搜索月份，固定 calendar half-years：TRAIN=2015H1..2018H2 共 8 块；VALIDATION=2019H1..2020H2 共 4 块。每块至少 4,000 candidate rows。

每块报告：n、local B1 rejection coefficient（只作描述）、frozen global TRAIN-fit B0/B1 MSE 与 improvement。

D1=true 仅当全部满足：

- TRAIN 8 块至少 6 块 local rejection coefficient <0，且 TRAIN block median coefficient <0；
- VALIDATION 4 块至少 3 块 local rejection coefficient <0，且 VALIDATION block median coefficient <0；
- VALIDATION 4 块至少 3 块 frozen B1 MSE improvement >0。

不允许按 diagnostic 结果挑 favorable half-year。

## 4. D2 — TRAIN-fixed rejection-magnitude shape

只在 nonzero `rejection_signed_z` rows 上，用 TRAIN feature distribution 的 `abs(rejection_signed_z)` 20/40/60/80% quantiles 冻结 5 个 magnitude bins；edges 不读取 next5 outcome，并原样应用到 VALIDATION/2019/2020。

用 frozen TRAIN-B0 prediction 定义 residual：`next5_z - B0_prediction`。

定义 `aligned_reversal_score = -sign(rejection_signed_z) * residual`。正值表示 residual 朝 rejected excursion 的反方向。

每个 group/bin 至少 total 300 rows，且 positive/negative rejection 各至少 100 rows。每 bin 报 n、sign counts、mean abs rejection、mean aligned score、positive/negative mean residual。

对 TRAIN、VALIDATION pooled、2019、2020 各自计算：

- 5-bin `mean_score` 对 `mean_abs_rejection` 的线性 trend；
- top-bin mean score 与 bottom-bin mean score；
- top-bin positive-rejection mean residual；
- top-bin negative-rejection mean residual。

每组 support rule：

- trend >0；
- top mean score > bottom mean score；
- top mean score >0；
- top positive-rejection mean residual <0；
- top negative-rejection mean residual >0。

四组全部满足才 D2=true。不要求五个 bins 严格逐点单调。

## 5. 裁决

- D1=true & D2=true：`R7_diagnostic_supported_for_specialist_research`；
- D1=true & D2=false：`R7_diagnostic_time_stable_but_magnitude_shape_weak`；
- D1=false & D2=true：`R7_diagnostic_shape_supported_but_time_stability_weak`；
- D1=false & D2=false：`R7_diagnostic_not_robust_enough_for_specialist`；
- entry/supply failure：`R7_diagnostic_execution_drift_or_insufficient`。

只有第一种允许 specialist handoff。即使通过，也不自动授权 BLACKBOX/PnL/production/complex regime model。

Production authority=false。
