# CONTINUE HERE — 广义反转 / 均值回归研究入口（2026-09-16）

**本文件是判断本仓库“现在研究什么、下一步做什么”的第一权威。**

仓库级任务：

> 用因果、多尺度、低容量框架发现广义反转 / 均值回归机制；区分“机制是否存在”与“固定系数是否可迁移”，并避免用复杂模型或 outcome-driven 搜索救简单机制。

当前状态：

`R7_SPECIALIST_STAGE1_INFERENTIAL_SUPPORT_CALIBRATION_DRIFT_FIXED_COEFFICIENT_TRANSPORT_NOT_READY`

## 1. 数据治理

```text
TRAIN      = 2015-01-05..2018-12-31
VALIDATION = 2019-01-01..2020-12-31
BLACKBOX   = none
```

TRAIN/VALIDATION 都是 reusable research data，不是 fresh OOS。当前仍禁止 post-2020、PnL/Sharpe model selection、paper trading、production、registry mutation。

## 2. 已关闭/受限方向

- R1：旧 M1 方向证据不支持，不 rescue 同 identity。
- R2：旧 range identity closed。
- R3：predeclared direction falsified。
- R4：no candidate qualifies。
- R5-B1：CL008 后曾进 specialist，但更严格 Stage 1 时间稳定性失败，transport closed。
- R6：close-boundary rejection upper/lower 方向不对称，`R6_direction_not_supported`，禁止 upper-only rescue。
- T1：历史 shock identity closed。

## 3. R7 parent 与 bounded diagnostic 已通过

Parent：`R7_native_1m_rejected_excursion_v1`

固定 identity：

- official native 1m + official 5m endpoint anchor；
- past path = 5 native 1m returns；
- next outcome = 5 native 1m returns；
- sigma = previous 240 exact-1m returns RMS, shift(1)；
- B0 = endpoint displacement；
- B1 = B0 + continuous `rejection_signed_z`；
- no local resampling / no M0 cache / no R5-B1 feature。

Parent broad screen：candidate rows=`64215`；TRAIN rejection beta=`-0.532770`；VALIDATION local beta≈`-0.39545`；fixed B1 在 2019/2020 MSE 分别约改善 `1.35% / 1.66%`。

唯一 bounded diagnostic：`R7_rejected_excursion_stability_shape_diagnostic_v1`。

- D1 fixed half-year stability=true：TRAIN 7/8 negative；VALIDATION 4/4 negative、4/4 frozen improvement positive。
- D2 magnitude shape=true：TRAIN/VALIDATION/2019/2020 的 aligned reversal score 均随 magnitude 呈正 trend，高 magnitude 正负方向 symmetry 通过。

Diagnostic adjudication：

`R7_diagnostic_supported_for_specialist_research`

Specialist：`R7_native_1m_rejected_excursion_specialist_v1`，但 BLACKBOX 仍为空。

## 4. Specialist Stage 1 已完成：机制支持，但 fixed coefficients 有 calibration drift

Stage 1 identity：`R7_specialist_stage1_inferential_readiness_v1`

Protocol：`docs/governance/R7_specialist_stage1_inferential_readiness_protocol_v1.json`

有效 execution freeze：`docs/governance/R7_specialist_stage1_inferential_readiness_execution_freeze_v2.json`

有效 run：`35043298059`；job=`104627633019`；5/5 frozen synthetic tests passed；entry reproduction passed。

第一次 run `35043104558` 在 synthetic test 阶段因零方差退化样本的 machine-epsilon containment 问题停止，真实 runner **未执行**。只做了 `1e-12` 数值 containment 修正，C1/C2/C3 科学定义和 gate 未变，并在真实 outcome 前建立 v2 freeze。

Receipt：`docs/research/local_R7_specialist_stage1_inferential_readiness_receipt_v1.json`

Cloud review：`docs/research/R7_specialist_stage1_inferential_readiness_cloud_review_20260916.md`

Handoff：`docs/ops/R7_specialist_stage1_calibration_drift_handoff_20260916.md`

### C1 — trading-day clustered coefficient uncertainty

`C1_clustered_coefficient_supported = true`

```text
TRAIN       beta -0.53277   95% CI [-0.58946, -0.47608]
VALIDATION  beta -0.39545   95% CI [-0.44499, -0.34591]
2019        beta -0.39384   95% CI [-0.47022, -0.31746]
2020        beta -0.39696   95% CI [-0.46104, -0.33289]
```

四组 day-clustered CI upper 全部 <0。

### C2 — frozen prediction day robustness

`C2_day_prediction_robustness_supported = true`

2019：244 days，positive days=`61.07%`，median improvement=`+0.01676`，bootstrap mean 95% CI=`[+0.00943,+0.03750]`。

2020：243 days，positive days=`61.32%`，median improvement=`+0.02459`，bootstrap mean 95% CI=`[+0.01331,+0.03942]`。

因此 R7 的机制/预测增量在 trading-day dependence 下仍有支持，但并非每天都改善。

### C3 — calibration / residual sufficiency

`C3_calibration_clean = false`

VALIDATION pooled：

```text
calibration slope        = 0.80744
95% CI                   = [0.71494, 0.89993]   # 不含 1
residual endpoint slope  = +0.03108
95% CI                   = [0.01316, 0.04899]   # 不含 0
residual rejection slope = +0.13732
95% CI                   = [0.08777, 0.18686]   # 不含 0
```

2019/2020 分开后 calibration slope 约 `0.811 / 0.804`，residual endpoint/rejection slopes 同方向。

解释：TRAIN frozen B1 的方向是对的，但 amplitude 在 VALIDATION 上系统性过强；尤其 rejection beta 从 TRAIN `-0.533` 漂到 VALIDATION local `-0.395` 左右。

正式裁决：

`R7_specialist_stage1_inferentially_supported_calibration_drift`

## 5. 当前权限含义

允许：

- 保留 R7 specialist mechanism；
- 研究一个新的、事前冻结的低容量 coefficient calibration rule；
- 在 source governance 明确授权后做 mechanism transport，并把 mechanism transport 与 coefficient transport 分开。

不允许：

- 宣称 fixed TRAIN coefficients transport-ready；
- 直接用 2019/2020 full-period local re-fit 替换 TRAIN coefficients；
- 搜 rolling window、half-life/decay、regularization、threshold、favorable period；
- 增加 feature 后仍称同一 R7；
- BLACKBOX/post-2020；
- PnL/Sharpe 选择 calibration；
- HMM/rSLDS/Koopman rescue；
- paper trading / production。

## 6. Specialist 下一步

下一 identity：`R7_calibration_strategy_readiness_v1`。

**必须在任何 calibration outcome 前重新冻结。**

研究目标只允许是 coefficient-updating rule，不改 parent features/path/horizon/sigma。优先采用低自由度方案：固定 expanding OLS，预声明 minimum history 与 update cadence；先用 TRAIN 内固定 calendar forward-chaining 做 readiness，再使用 VALIDATION 作 reusable diagnostic。

不得在 VALIDATION 上搜索窗口或超参后称为 transport qualification。

## 7. 跨市场与 broad lane

跨指数 common-vs-idiosyncratic / R7 mechanism transport 仍因上游数据治理未明确授权而暂缓。

母仓 broad lane 继续独立寻找与 R7 native-path rejection 不同源的低容量机制；不得换名字继续调 R5/R6/R7。

## 8. 下一步顺序

1. outcome-blind 冻结 `R7_calibration_strategy_readiness_v1`；
2. 保持 parent feature/path/horizon/sigma 不变；
3. 母仓并行 broad discovery；
4. source governance 明确授权后才做跨市场 mechanism transport；
5. calibration 与 transport 都成熟且重新冻结后，才讨论小型 never-seen BLACKBOX。

当前权限：

```text
fixed_coefficient_transport = false
BLACKBOX_assigned           = false
post_2020_authorized        = false
trading_PnL_authorized      = false
paper_trading_authorized    = false
fresh_OOS_claim_authorized  = false
production_authority        = false
```
