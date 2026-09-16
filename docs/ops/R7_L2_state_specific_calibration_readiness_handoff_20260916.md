# R7 × Layer2 — state-specific calibration readiness handoff

日期：2026-09-16

Next identity：`R7_L2_state_specific_calibration_readiness_v1`

Parent：`R7_native_1m_rejected_excursion_v1`

State diagnostic：`R7_L2_5m_risk_bucket_calibration_diagnostic_v1`

状态：`AUTHORIZED WITHOUT BLACKBOX / STATIC STATE PARAMETERS NOT FINAL`

## 已知事实

Layer2 finalized 5m state engine 已作为 read-only dependency 对齐并通过：

- `LOW_RISK = NORMAL`
- `RISK_ACTIVE = UNSAFE or RECOVERING`
- 2020 canonical cross-repo state agreement = 100%
- R7 candidate state match = 99.9019%
- 两桶供给充足。

State-conditioned diagnostic：

- G1 state-parameter heterogeneity = true；
- G2 pooled/year prediction robustness = true；
- G3 calibration clean = false；
- adjudication=`R7_L2_state_conditioning_supported_residual_drift`。

TRAIN static parameters：

- LOW_RISK `[intercept,endpoint,rejection]=[-0.002411,+0.082805,-0.552275]`
- RISK_ACTIVE `[+0.028729,+0.018067,-0.463648]`

这些是 TRAIN 条件最小二乘参数，不是生产参数，也不应称为跨期“最优参数”。

## 下一阶段问题

固定 Layer2 bucket 后，能否通过一个预注册、因果、低容量的系数更新机制，使每个状态桶的参数适应时间变化，同时在 reusable VALIDATION 中稳定优于：

1. frozen parent B1 global；
2. frozen TRAIN-static B2 state model。

## 首选规则族

第一候选只允许：`bucket-specific expanding OLS`。

约束建议在 preanalysis 中冻结：

- 不改变 Layer2 状态定义或 bucket map；
- 不改变 R7 features / path / horizon / sigma；
- 每次预测只能使用该时点之前已经观测完成的数据；
- minimum history 与 update cadence 在任何新 outcome 之前固定；
- 不允许搜索 rolling window、decay/half-life、regularization、bucket threshold、time-of-day 或 favorable years；
- 同一套更新规则同时用于 LOW_RISK 与 RISK_ACTIVE，除非另有事前机制理由；
- VALIDATION 只用于诊断这个固定 rule，不用来穷举选择 cadence。

## 重要现象

当前 static B2 的增益很小，且 RISK_ACTIVE 在 pooled VALIDATION 与 2019 的 bucket-specific MSE 略差于 global B1；因此下一阶段的成功标准不能只要求 pooled MSE 略改善。应预注册更严格的 state-specific robustness，例如要求 2019/2020 的总体比较都通过，并对两个 bucket 的 improvement breadth / calibration 分开报告。

另一个关键事实：2019/2020 local rejection loading 在两个状态内相当稳定：

- 2019 LOW_RISK `-0.38872`, RISK_ACTIVE `-0.43672`
- 2020 LOW_RISK `-0.39438`, RISK_ACTIVE `-0.43747`

而 TRAIN ordering 不同，因此真正要解决的是时间校准与状态交互共同存在，而不是简单固定两套 TRAIN 参数。

## 禁止

BLACKBOX、post-2020 Layer3 selection、PnL/Sharpe model selection、parameter grid search、Layer2 mutation、复杂 regime rescue、paper trading、production 均未授权。
