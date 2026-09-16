# R7 specialist Stage 1 — inferential readiness

日期：2026-09-16

Identity：`R7_specialist_stage1_inferential_readiness_v1`

Parent：`R7_native_1m_rejected_excursion_v1`

状态：`FROZEN BEFORE STAGE1 OUTCOME / NO BLACKBOX / NO FEATURE SEARCH`

## 1. 目标

本阶段不寻找新 alpha，也不改 R7 parent。只回答：

1. rejected-excursion coefficient 在按 trading day 聚类后是否仍有稳定的负向不确定性边界；
2. frozen TRAIN-fit B1 的预测改善是否具有日级 breadth / uncertainty；
3. frozen B1 是否已经足够校准，还是机制仍成立但 fixed coefficient 存在 calibration drift。

## 2. Entry reproduction

必须用 parent runner 原样重建 `64215` candidates，并在 `1e-12` tolerance 内复现 TRAIN B0/B1 beta 与 VALIDATION/2019/2020 frozen MSE。任何失败直接 `R7_specialist_stage1_execution_drift_or_insufficient`。

## 3. C1 — day-clustered coefficient uncertainty

对 TRAIN、VALIDATION、2019、2020 分别本地拟合 parent B1：

`next5_z = intercept + beta_endpoint*endpoint_z + beta_rejection*rejection_signed_z`

标准误使用 trading-day cluster-robust CR1 sandwich，不按结果选择日期。

C1=true 当且仅当四组 `beta_rejection` 的双侧 95% CI upper 都 `<0`。

## 4. C2 — frozen prediction day robustness

使用 frozen TRAIN-fit B0/B1，不重新训练。每个 VALIDATION trading day 计算：

`day_improvement = mean((y-B0)^2) - mean((y-B1)^2)`。

分别对 VALIDATION pooled、2019、2020 报告 day count、mean、median、fraction positive、p10/p90；并用 deterministic nonparametric day bootstrap：seed=`20260916`，replicates=`10000`，对 mean improvement 给 percentile 95% CI。

C2=true 当且仅当 2019 和 2020 都满足：

- bootstrap mean-improvement 95% CI lower > 0；
- median day improvement > 0；
- fraction positive days > 0.50。

pooled 只报告，不额外改变 gate。

## 5. C3 — calibration / residual sufficiency

只对 frozen TRAIN-fit B1 检查，不生成替代模型。

对 VALIDATION pooled、2019、2020：

A. calibration regression：`y = a + b * frozen_B1_prediction`，trading-day cluster-robust 95% CI。

B. residual regression：`residual_B1 = c + g_endpoint*endpoint_z + g_rejection*rejection_signed_z`，同样使用 day-clustered CR1 95% CI。

单组 calibration_clean 当且仅当：

- calibration intercept CI 包含 0；
- calibration slope CI 包含 1；
- residual endpoint slope CI 包含 0；
- residual rejection slope CI 包含 0。

C3_clean=true 仅当 VALIDATION、2019、2020 三组全部 clean。

这里使用“CI 是否包含理论值”，不设置 outcome-informed arbitrary effect-size tolerance。C3 不用于否定已经通过的机制方向；它区分 fixed coefficients 是否可直接 transport。

## 6. 裁决

- C1=true & C2=true & C3_clean=true：`R7_specialist_stage1_inferentially_supported_calibration_clean`
- C1=true & C2=true & C3_clean=false：`R7_specialist_stage1_inferentially_supported_calibration_drift`
- C1=false 或 C2=false：`R7_specialist_stage1_inferential_support_insufficient`
- entry/data failure：`R7_specialist_stage1_execution_drift_or_insufficient`

只有第一种允许 fixed-coefficient transport readiness。第二种只允许继续研究“机制 transport / 预注册 calibration strategy”，不得把本地重拟合后的更好结果冒充 frozen parent。第三种关闭 specialist progression。

## 7. 禁止事项

不得改 path=5、forward=5、sigma=240、B0/B1 feature set；不得挑 day/year/half-year/sign/time/magnitude；不得 threshold rescue；不得 BLACKBOX/post-2020；不得 PnL/Sharpe；不得复杂模型 rescue；不得 production/paper trading。
