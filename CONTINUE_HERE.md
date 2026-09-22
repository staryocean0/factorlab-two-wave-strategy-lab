# 2026-09-22 current checkpoint — R7 cost-tempo prototype

New identity `R7_cost_tempo_reversal_research_v1` completed Stage-A index-proxy engineering replay. At fixed 2bp/side: +12.6960% cumulative, Sharpe 1.5544, episode-mark DD -3.4683%, turnover 3.4588/day. Both years positive; nominated adaptive arm exceeds fixed-fast and fixed-slow in pooled net return. This is NOT actual option PnL, full-package certification, positive-latency execution qualification, or production promotion. Low-vol slow leg has only 53 episodes.

Read `docs/research/R7_cost_tempo_stageA_review_20260922.md`, the matching receipt, protocol and execution freeze. Next: positive-latency/common-minute accounting audit, then separately admitted real-MO quote replay using read-only cost/Greeks measurement. No new horizon/quantile/fee search. Existing Layer2 engine and closed challenger remain unchanged.

---
## Archived previous entry (historical, not the current next action)

# CONTINUE HERE — 广义反转 / 均值回归研究入口（2026-09-16）

**本文件是判断本仓库“现在研究什么、下一步做什么”的第一权威。**

仓库级任务：

> 用因果、多尺度、低容量框架发现广义反转 / 均值回归机制；区分“机制存在”“校准可迁移”“经济可实现”三件事，并避免 outcome-driven rescue。

当前状态：

`R7_L2_CHALLENGER_EVALUATED_NOT_PROMOTED_TURNOVER_COST_FRAGILITY_REMAINS`

## 1. 数据治理

```text
TRAIN      = 2015-01-05..2018-12-31
VALIDATION = 2019-01-01..2020-12-31
BLACKBOX   = none
```

TRAIN/VALIDATION 都是 reusable research data，不是 fresh OOS。当前仍禁止 post-2020、paper trading、production、registry mutation；BLACKBOX 仍未分配。

## 2. 历史关闭/受限方向

- R1：旧 M1 方向证据不支持，不 rescue 同 identity。
- R2：旧 range identity closed。
- R3：predeclared direction falsified。
- R4：no candidate qualifies。
- R5-B1：specialist Stage 1 transport closed。
- R6：direction asymmetry，`R6_direction_not_supported`，禁止 upper-only rescue。
- T1：历史 shock identity closed。

## 3. R7 机制状态

Parent：`R7_native_1m_rejected_excursion_v1`

固定 identity：official native 1m + official 5m endpoint anchor；past path=5 native 1m returns；next outcome=5 native 1m returns；sigma=previous 240 exact-1m returns RMS shift(1)；B1=endpoint displacement + continuous `rejection_signed_z`。

Parent broad screen candidate rows=`64215`；TRAIN rejection beta≈`-0.53277`，VALIDATION local beta≈`-0.39545`。

Bounded diagnostic：`R7_rejected_excursion_stability_shape_diagnostic_v1` 通过，正式裁决：

`R7_diagnostic_supported_for_specialist_research`

Specialist Stage1：`R7_specialist_stage1_inferential_readiness_v1`。

- C1 clustered coefficient support=true；
- C2 day-level prediction robustness=true；
- C3 calibration clean=false；
- formal adjudication=`R7_specialist_stage1_inferentially_supported_calibration_drift`。

结论：R7 reversal mechanism 保留，但 fixed TRAIN coefficients 不是直接 transport-ready。

## 4. Layer2 外生风险状态已冻结并验证

Reference contract：`docs/governance/R7_layer2_5m_risk_state_reference_contract_v1.json`。

三态不变：`NORMAL / UNSAFE / RECOVERING`。

Consumer 两桶固定：

```text
LOW_RISK    = NORMAL
RISK_ACTIVE = UNSAFE or RECOVERING
```

Layer2 threshold/state semantics 不允许因 R7 outcome 修改；recovery probability 不允许作为策略信号。

Alignment inventory 通过；R7 candidate state match fraction≈`99.902%`，2019–2020 经济评估的 21,428 行全部有状态。

Static state diagnostic：`R7_L2_5m_risk_bucket_calibration_diagnostic_v1`。

- G1 state heterogeneity=true；
- G2 fixed TRAIN B2 prediction improvement=true，但幅度很小；
- G3 calibration clean=false；
- adjudication=`R7_L2_state_conditioning_supported_residual_drift`。

解释：Layer2 state 是有信息的 calibration coordinate，但静态 state split 不是 temporal drift 的完整解释。

## 5. Formal OLD BASELINE 已完成经济评估

Identity：`R7_trading_strategy_baseline_v1`。

Policy：每天用严格早于当日的数据做 global expanding B1；position=`clip(forecast_z,-1,+1)`；next native 1m open 入场，t+5 close 窗口退出；连续 5m block carry，非连续/日终 flatten，无隔夜。

固定成本 panel：0/1/2/5 bps one-way per absolute turnover；primary=`2 bps`。

2 bps OLD BASELINE：

```text
total return           -2.6713%
Sharpe                 -0.2671
max drawdown          -13.2702%
avg daily turnover       9.6918x
2019 return             -3.5607%
2020 return             +0.9222%
```

0 bps gross total return=`+150.143%`，说明问题不是没有 gross edge，而是高换手/成本敏感。

Formal adjudication：

`R7_OLD_BASELINE_EVALUATED_NOT_SUPPORTED_AT_2BPS_NO_RESCUE`

它现在只是**固定比较基准**，不是 promoted trading/research baseline。

## 6. R7 × Layer2 state-specific calibration challenger 已完成并关闭

Identity：`R7_L2_state_specific_calibration_challenger_v1`。

Preanalysis：`docs/research/R7_L2_state_specific_calibration_challenger_preanalysis_20260916.md`

Protocol：`docs/governance/R7_L2_state_specific_calibration_challenger_protocol_v1.json`

Execution freeze：`docs/governance/R7_L2_state_specific_calibration_challenger_execution_freeze_v1.json`

Receipt：`docs/research/local_R7_L2_state_specific_calibration_challenger_receipt_v1.json`

Cloud review：`docs/research/R7_L2_state_specific_calibration_challenger_cloud_review_20260916.md`

Dedicated execution：

```text
head      40c19410319b8c75959b1abeb439d424942d095c
run       35058115791
job       104672459346
artifact  10431138239
5/5 frozen synthetic tests passed
OLD_BASELINE exact reproduction passed
strict-prior/full-rank state fit passed
```

Frozen challenger 只改一件事：从一个 global daily expanding B1，变成 `LOW_RISK` 与 `RISK_ACTIVE` 两个桶各自 daily expanding B1；R7 features、Layer2 state、position map、执行、成本、评估行完全不动。

### Predictive diagnostic

```text
                  OLD MSE       L2 challenger MSE
VALIDATION       1.63310934       1.63217590
2019             1.71971749       1.71956168
2020             1.54614478       1.54443052
```

三个组都有小幅改善，但幅度只有约 `0.009%–0.111%`。

### 2 bps 同口径经济结果

```text
                         OLD BASELINE     L2 challenger
Total return               -2.6713%          -1.0704%
Sharpe                      -0.2671           -0.0978
Max drawdown               -13.2702%         -13.0276%
Avg daily turnover           9.6918x           9.9608x
2019 return                 -3.5607%          -3.9546%
2020 return                 +0.9222%          +3.0029%
```

Challenger pooled loss、Sharpe、max DD 都相对 OLD 改善，但：

- total return 仍 <0；
- Sharpe 仍 <0；
- 2019 仍 <0 且比 OLD 更差；
- avg daily turnover **反而上升约 2.78%**。

因此最关键的 turnover/cost fragility 没有解决。

冻结 promotion gates 中失败：

```text
challenger_total_return_gt_0                 false
challenger_sharpe_gt_0                       false
challenger_2019_return_gt_0                  false
challenger_average_daily_turnover_lt_old     false
```

Formal adjudication：

`R7_L2_CHALLENGER_EVALUATED_NOT_PROMOTED_NO_RESCUE`

**不得**在这个 identity 下调 Layer2 threshold/state map、risk multiplier、rolling window、decay、regularization、update cadence、年份/时段、成本或执行规则进行救援。

## 7. 当前研究含义

已经分清三层：

1. **Mechanism**：R7 rejected-excursion reversal 有支持；
2. **Calibration**：Layer2 state 有增量信息，但 fixed/static calibration 不干净；
3. **Economics**：global expanding 与 state-specific expanding 在 2 bps 都没有达到经济支持，核心约束仍是高换手/成本敏感。

所以本次不能把 Layer2 challenger 晋升成新的 research baseline。

OLD BASELINE 继续仅作为冻结 comparator；Layer2 继续保留为外生状态描述器，但不是单独的交易开关或已支持的 production regime router。

## 8. 下一步顺序

1. 关闭 `R7_L2_state_specific_calibration_challenger_v1`，no rescue；
2. 母仓恢复独立、低容量 broad reversal / mean-reversion direction discovery；
3. 如果未来继续做 R7 经济层，必须创建**新的 outcome-blind identity**，研究 turnover/execution architecture，而不是继续调本次 coefficient challenger；
4. 跨指数 mechanism transport 仍需上游 source governance 明确授权；
5. BLACKBOX 继续不分配，直到机制、校准、经济设计都成熟并重新冻结。

当前权限：

```text
fixed_coefficient_transport = false
new_R7_research_baseline     = false
BLACKBOX_assigned            = false
post_2020_authorized         = false
fresh_OOS_claim_authorized   = false
paper_trading_authorized     = false
production_authority         = false
```
