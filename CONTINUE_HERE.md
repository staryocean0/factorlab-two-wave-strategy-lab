# CONTINUE HERE — 广义反转 / 均值回归研究入口（2026-09-16）

**本文件是判断本仓库“现在研究什么、下一步做什么”的第一权威。**

仓库级任务：

> 用因果、多尺度、低容量框架发现广义反转 / 均值回归机制；核心是区分暂时偏离与父状态改变，并避免用复杂模型救简单机制失败。

当前状态：

`R7_DIAGNOSTIC_SUPPORTED_SPECIALIST_HANDOFF_ESTABLISHED_BROAD_DISCOVERY_CONTINUES`

## 1. 数据治理

```text
TRAIN      = 2015-01-05..2018-12-31
VALIDATION = 2019-01-01..2020-12-31
BLACKBOX   = none
```

TRAIN/VALIDATION 都是 reusable research data，不是 fresh OOS。真正稀缺的是 never-seen BLACKBOX qualification；当前仍未分配 BLACKBOX。

禁止：post-2020、PnL/Sharpe model selection、paper trading、production、FactorLab registry mutation，除非后续另有明确授权。

## 2. 已关闭或受限的旧方向

- R1：旧 identity 后续 M1 方向证据不支持，不 rescue 同一 identity。
- R2：旧 low-capacity range identity closed。
- R3：预注册方向 falsified。
- R4：无 candidate qualified。
- R5-B1：CL008 曾支持 specialist，但更严格 specialist Stage 1 时间稳定性失败，transport closed。
- R6 close-boundary rejection：供给足，但 VALIDATION upper/lower 明显方向不对称；裁决 `R6_direction_not_supported`，禁止 upper-only outcome rescue。
- T1 old transitory shock：历史 identity closed。

## 3. 1m native path 数据已通过 inventory

本仓已有官方 development 数据：

- `data/development/1m_official.parquet`
- rows = `350561`
- SHA256 = `755217afce9dec383e48cd46d591402fa90dc50897abeb3dc7097c9a18a109d4`

与 official 5m endpoint：

- endpoints = `70114`
- 同 timestamp 1m endpoint = `70112`
- 完整 native 5x1m chain = `70108`
- aligned endpoint close 最大差异 = `0`
- 不做 local resampling。

Inventory run：`35041427672`。

## 4. R7 parent broad screen 已通过

Identity：`R7_native_1m_rejected_excursion_v1`

研究问题：在相同 official 5m endpoint displacement 下，native 1m 路径若曾走得更远又在 endpoint 前回撤，这个 continuous rejected excursion 是否对下一段 5m return 提供额外反向信息。

Parent model：

- B0 = endpoint displacement only；
- B1 = B0 + continuous `rejection_signed_z`；
- past path = 5 native 1m returns；
- outcome = next 5 native 1m returns；
- sigma = previous 240 exact-1m returns RMS, shift(1)。

冻结执行 run：`35041836335`。

关键结果：

```text
candidate rows = 64215
TRAIN rejection coefficient      = -0.532770
VALIDATION local coefficient     ≈ -0.39545
2019 local coefficient           ≈ -0.39384
2020 local coefficient           ≈ -0.39696

VALIDATION MSE B0/B1 = 1.65984729 / 1.63497129
2019 relative improvement ≈ 1.35%
2020 relative improvement ≈ 1.66%
```

正/负 rejected excursion 的 pooled residual symmetry 同时通过。

Parent adjudication：

`R7_supported_for_one_bounded_diagnostic`

## 5. R7 唯一 bounded diagnostic 已完成并通过

Diagnostic：`R7_rejected_excursion_stability_shape_diagnostic_v1`

Execution freeze：`docs/governance/R7_rejected_excursion_stability_shape_diagnostic_execution_freeze_v1.json`

Run：`35042530618`；job=`104625259981`；4/4 frozen synthetic tests passed；entry reproduction 1e-12 passed。

Receipt：`docs/research/local_R7_rejected_excursion_stability_shape_diagnostic_receipt_v1.json`

Cloud review：`docs/research/R7_rejected_excursion_stability_shape_diagnostic_cloud_review_20260916.md`

### D1 — fixed half-year stability

`D1_time_stability_supported = true`

```text
TRAIN:      7/8 half-years coefficient < 0
TRAIN median coefficient = -0.753228

VALIDATION: 4/4 half-years coefficient < 0
VALIDATION median coefficient = -0.395287
VALIDATION: 4/4 half-years frozen B1 improvement > 0
```

2015H2 是唯一 TRAIN coefficient >0 的固定块，保留原样，不删除、不筛选。

### D2 — TRAIN-fixed magnitude shape

`D2_magnitude_shape_supported = true`

TRAIN-only magnitude quintile edges：

`[0.0854063, 0.2019050, 0.3714535, 0.6597429]`

aligned reversal score 随 rejected-excursion magnitude 的线性 trend：

```text
TRAIN       +0.269913
VALIDATION  +0.287181
2019        +0.266837
2020        +0.310699
```

VALIDATION bottom/top mean score：`0.07183 -> 0.38269`。

VALIDATION top bin：

```text
positive rejection mean residual = -0.43850
negative rejection mean residual = +0.33788
```

四组都通过 top>bottom、top>0、top-bin sign symmetry。

正式裁决：

`R7_diagnostic_supported_for_specialist_research`

## 6. R7 specialist handoff 已建立

Specialist：`R7_native_1m_rejected_excursion_specialist_v1`

Handoff：`docs/ops/R7_native_1m_rejected_excursion_specialist_handoff_20260916.md`

状态：`AUTHORIZED WITHOUT BLACKBOX`

Specialist 必须保持 parent identity，不允许把 path length / horizon / sigma / feature search 混进同一个验证身份。

第一阶段只做：

1. day-clustered uncertainty，不挑 favorable days；
2. calibration / residual sufficiency，不做 threshold rescue；
3. 只有数据治理明确授权后才做跨市场 transport；
4. 机制与 transport 稳定后再设计经济映射。

仍不允许 HMM/rSLDS/Koopman rescue，不允许 BLACKBOX，不允许 PnL/Sharpe 反向选模型。

## 7. 跨指数数据现状

`factorlab-trend-reversion-regime-lab` 中存在 STAR50/CSI1000 5m 数据，但该仓当前数据治理说明没有授权新的实证候选，因此本仓不跨仓偷用。

CSI300/CSI500/CSI1000 common-vs-idiosyncratic shock 方向继续保留，但必须等明确 source-governance authorization。

## 8. 母仓下一步

R7 已进入 specialist lane；母仓继续 broad-and-shallow discovery，且新方向必须与 R7 native-path rejection 不同源，不能换名字继续调 R5/R6/R7。

下一步顺序：

1. specialist 冻结 inferential-readiness Stage 1；
2. 母仓并行选择新的 independent low-capacity reversal identity；
3. 跨市场 transport 仅在 source governance 明确授权后进行；
4. 小型 never-seen BLACKBOX 只在 specialist model/features/evaluation 成熟并重新冻结后讨论。

## 9. 权限边界

当前仍为：

```text
BLACKBOX_assigned          = false
post_2020_authorized       = false
trading_PnL_authorized     = false
paper_trading_authorized   = false
fresh_OOS_claim_authorized = false
production_authority       = false
```
