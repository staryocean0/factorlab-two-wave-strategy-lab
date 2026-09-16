# R7 × Layer2 5m risk bucket — state-conditioned calibration diagnostic

日期：2026-09-16

Identity：`R7_L2_5m_risk_bucket_calibration_diagnostic_v1`

Parent：`R7_native_1m_rejected_excursion_v1`

Layer2 reference：`R7_layer2_5m_risk_state_reference_contract_v1`

状态：`FROZEN BEFORE ANY STATE-CONDITIONED R7 OUTCOME / NO BLACKBOX / NO PARAMETER GRID SEARCH`

## 1. 问题

R7 specialist Stage 1 已确认：rejected-excursion mechanism 在 day-clustered inference 与 day-level prediction breadth 上成立，但 2015–2018 frozen coefficient 直接搬到 2019–2020 有 calibration drift。

本次只检验一个预注册解释：**Layer2 5m risk state 是否对应两套不同的 R7 线性参数，从而解释部分 calibration drift。**

状态定义完全来自已冻结 Layer2，不允许按 R7 outcome 修改：

- `LOW_RISK = NORMAL`
- `RISK_ACTIVE = UNSAFE or RECOVERING`

## 2. 数据与 entry

仅使用当前 R7 reusable data：

- TRAIN = 2015-01-05..2018-12-31
- VALIDATION = 2019-01-01..2020-12-31
- BLACKBOX = none

必须复现 parent R7：candidate rows=`64215`；TRAIN B1 beta=`[0.0014301524091757736, 0.06384569479627833, -0.5327696198414718]`；原 parent VALIDATION/2019/2020 B1 MSE 与既有 receipt 在 `1e-12` tolerance 内一致。

必须复现 outcome-blind state attachment：matched candidates=`64152`，match fraction=`0.9990189208128942`；固定 bucket supply 不低于 inventory receipt。

不匹配的 63 个 candidate 只从 state-conditioned comparison 中排除；不得填充、猜测或按 outcome 分配状态。原 global B1 coefficient 不重新训练，因此 baseline 仍是 frozen parent。

## 3. 模型

Baseline `B1_global`：

`y = a + bE*endpoint_z + bR*rejection_signed_z`

使用 parent 的 frozen TRAIN beta。

唯一 challenger `B2_state`：

`y = a + bE*endpoint_z + bR*rejection_signed_z + c0*risk + cE*(risk*endpoint_z) + cR*(risk*rejection_signed_z)`

其中 `risk=1` 仅表示 `RISK_ACTIVE`。

B2 只在 matched TRAIN 拟合一次，然后固定应用到 VALIDATION / 2019 / 2020。不存在 threshold、window、decay、regularization 或模型搜索。

LOW_RISK 参数向量为 `[a,bE,bR]`；RISK_ACTIVE 参数向量为 `[a+c0,bE+cE,bR+cR]`。

## 4. G1 — TRAIN state-parameter heterogeneity

对 B2 TRAIN 拟合使用 trading-day cluster-robust CR1 covariance。

对三个 interaction `[c0,cE,cR]` 做预注册 joint Wald test：

`W = c' Cov(c)^(-1) c`

固定 df=3，95% chi-square critical=`7.814727903251179`。

G1=true 当且仅当 `W > 7.814727903251179`。

单个 interaction 的 coefficient/CI 以及 VALIDATION/2019/2020 local state-conditioned vectors只报告，不参与 G1，避免用 validation local refit 选模型。

## 5. G2 — frozen TRAIN state model prediction robustness

在 state-matched rows 上比较 frozen parent `B1_global` 与 TRAIN-fit `B2_state` MSE。

G2=true 当且仅当以下三组全部 `MSE_B2 < MSE_B1`：

- VALIDATION pooled
- 2019
- 2020

不允许只挑某一年或某个桶作为通过理由。

同时报告 LOW_RISK 与 RISK_ACTIVE 各桶的 B1/B2 MSE，但仅作机制解释，不允许只凭一个 favorable bucket 通过。

## 6. G3 — state-conditioned calibration / residual sufficiency

G3 不决定是否存在有用的 state conditioning，只区分 B2 是否已经 calibration-clean。

对 VALIDATION pooled、2019、2020 分别：

1. calibration regression：`y = alpha + slope * frozen_B2_prediction`，day-clustered CR1 95% CI；
2. residual regression：`residual_B2` 对 B2 的五个非截距 explanatory coordinates 回归：`endpoint, rejection, risk, risk*endpoint, risk*rejection`，day-clustered CR1 95% CI。

单组 clean 当且仅当：

- calibration intercept CI 包含 0；
- calibration slope CI 包含 1；
- 五个 residual feature slope CI 全部包含 0。

G3_clean=true 仅当 VALIDATION、2019、2020 三组全部 clean。

## 7. 描述性 bucket evidence

固定报告 TRAIN / VALIDATION / 2019 / 2020 的 LOW_RISK 与 RISK_ACTIVE：

- n / trading days；
- local `[intercept, endpoint, rejection]`；
- rejection coefficient；
- frozen parent B1 MSE；
- frozen TRAIN B2 MSE。

这些结果不得用于重新定义桶、阈值或挑选方向。

## 8. 裁决

- G1=true & G2=true & G3=true：`R7_L2_state_conditioning_supported_calibration_clean`
- G1=true & G2=true & G3=false：`R7_L2_state_conditioning_supported_residual_drift`
- G1=true & G2=false：`R7_L2_state_heterogeneity_supported_but_prediction_not_robust`
- G1=false：`R7_L2_state_conditioning_not_supported`
- entry/state/supply failure：`R7_L2_state_diagnostic_execution_drift_or_insufficient`

只有前两种允许进入下一阶段的 bounded state-specific calibration strategy。即使通过，也不授权 BLACKBOX、PnL/Sharpe、post-2020、paper trading 或 production。

## 9. 禁止事项

禁止：修改 Layer2 1.5/1.1/3σ 语义；重映射 NORMAL/UNSAFE/RECOVERING；使用 Phase-1 未通过的 recovery probability；搜索更多 risk buckets；搜索 rolling window / decay / regularization；新增 R7 feature；按年份/方向/时段挑 favorable subset；BLACKBOX；post-2020；PnL/Sharpe；复杂模型 rescue。
