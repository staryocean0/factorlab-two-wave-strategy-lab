# R7 × Layer2 5m risk bucket — cloud review

日期：2026-09-16

Identity：`R7_L2_5m_risk_bucket_calibration_diagnostic_v1`

正式裁决：`R7_L2_state_conditioning_supported_residual_drift`

## 1. 执行身份

- execution head: `109c53162476bc673034963785d8fb59b698e650`
- dedicated run: `35046290393`
- job: `104636700326`
- workflow conclusion: success
- frozen synthetic tests: 5/5 passed
- artifact id: `10426629412`
- artifact digest: `sha256:18537317bb5ed16ae375e9c4e1af15f3a50f1bd7aacb87a5d3f051acd3275f1a`
- entry reproduction / state supply / authority boundaries: passed

No BLACKBOX, post-2020 Layer3 outcome, PnL/Sharpe, fresh-OOS claim, or production authority was used.

## 2. 两桶参数

TRAIN-fit B2 derived parameters `[intercept, endpoint, rejection]`：

- LOW_RISK: `[-0.002411, +0.082805, -0.552275]`
- RISK_ACTIVE: `[+0.028729, +0.018067, -0.463648]`

因此 TRAIN 内风险状态主要改变了 endpoint loading，同时 rejected-excursion reversal loading 在 RISK_ACTIVE 绝对值更小。

## 3. G1 — state heterogeneity

`G1_heterogeneity_supported = true`

三个预注册 interactions 的 joint Wald(df=3)=`10.512853`，高于固定 95% critical=`7.814728`。

所以在 TRAIN 内，`LOW_RISK` 与 `RISK_ACTIVE` 使用完全相同三参数向量的限制被拒绝；Layer2 风险状态与 R7 参数存在可检测的联合异质性。

注意：这只说明参数异质性，不等于每个 interaction 单独稳定，也不等于已经得到可生产的 state-switching strategy。

## 4. G2 — frozen TRAIN state model prediction

`G2_prediction_supported = true`

B2 在三组 pooled comparison 都严格优于 frozen parent B1：

- VALIDATION: `1.634971286 -> 1.634145467`，relative improvement=`0.0505%`
- 2019: `1.720788967 -> 1.720622754`，relative improvement=`0.00966%`
- 2020: `1.548800445 -> 1.547312307`，relative improvement=`0.0961%`

因此预注册的 pooled/year robustness gate 通过。

但增益很小，且 bucket-specific descriptive evidence 不能忽略：

- LOW_RISK 在 VALIDATION、2019、2020 都改善；
- RISK_ACTIVE 在 pooled VALIDATION 与 2019 反而略差，2020 才改善。

所以不能把当前 TRAIN 两桶静态参数称为“各风险状态最优参数”。当前证据只支持：Layer2 state conditioning 含有一些可迁移增益，但主要增益并未在 RISK_ACTIVE 子桶中跨年份稳定显现。

## 5. G3 — calibration remains unclean

`G3_calibration_clean = false`

Frozen B2 prediction 的 calibration slope：

- VALIDATION `0.80027`, CI `[0.71182, 0.88871]`
- 2019 `0.79573`, CI `[0.65960, 0.93185]`
- 2020 `0.80472`, CI `[0.69063, 0.91880]`

三组均不包含 1。

VALIDATION residual regression 仍显示 endpoint slope=`+0.02762`、rejection slope=`+0.16071`，其 95% CI 均不含 0。

所以 Layer2 两桶没有消除原有 temporal calibration drift。状态是有信息的，但静态 state split 不是 calibration 的全部解释。

## 6. Local vectors（仅描述）

2019 local：
- LOW_RISK rejection=`-0.38872`
- RISK_ACTIVE rejection=`-0.43672`

2020 local：
- LOW_RISK rejection=`-0.39438`
- RISK_ACTIVE rejection=`-0.43747`

这两个年份的 local vectors 本身非常接近，且都显示 RISK_ACTIVE reversal loading 比 LOW_RISK 更负；这与 TRAIN 的相对 ordering（RISK_ACTIVE `-0.46365` 比 LOW_RISK `-0.55228` 更弱）不同。

这进一步说明：不能把 TRAIN 的静态两套系数直接解释成永恒的 regime-specific optimum。更合理的下一步是固定 Layer2 bucket 后研究**因果、低容量的桶内系数更新规则**。

## 7. 权限结论

允许下一阶段：`R7_L2_state_specific_calibration_readiness_v1`。

下一阶段必须：

- Layer2 state engine / thresholds / bucket map 保持不变；
- R7 parent features、path=5m、forward=5m、sigma=240 保持不变；
- 只研究低容量 causal coefficient updating；
- 优先 fixed expanding OLS / predeclared update cadence；
- 与 frozen global B1 和 frozen TRAIN-static B2 同时比较；
- 不允许 rolling-window / decay / regularization / threshold grid search。

仍禁止 BLACKBOX、post-2020、PnL/Sharpe selection、paper trading、production、复杂模型 rescue。
