# CONTINUE HERE — 广义反转 / 均值回归研究入口（2026-09-08）

**本文件是判断本仓库“现在研究什么、下一步做什么”的第一权威。**

仓库级任务：

> **用因果、多尺度、低容量框架发现广义反转 / 均值回归机制；核心是区分“完整父状态中的暂时偏离”和“父状态本身改变”。**

当前状态：

`R5_PARTIAL_SUPPORT_B1_BOUNDED_DIAGNOSTIC_FROZEN_CL008_LOCAL_EXECUTION_PENDING`

## 1. 数据治理

当前：

```text
TRAIN      = 2015-01-05..2018-12-31
VALIDATION = 2019-01-01..2020-12-31
BLACKBOX   = none
```

TRAIN 和 VALIDATION 都是可反复研究的长期资产。VALIDATION 可以拆年份/事件/状态做诊断，并根据诊断继续改模型。

BLACKBOX 只在候选成熟后才分配，默认只返回 aggregate confirmation。若打开细节，它降级为 VALIDATION，而不是报废。

> **数据不是消耗品；真正稀缺的是 never-seen BLACKBOX qualification。**

权威政策：`docs/governance/reversal_mean_reversion_data_reuse_validation_policy_v1.md`。

## 2. M0 两浪底座

M0 继续作为 `M0_two_wave_structure_measurement_foundation`，不是交易 alpha。

- operational baseline = v0.4.3
- morphology = `morphology_replication_not_yet_accepted`
- CL-005 = cloud-reviewed completed
- v0.6.17 accepted capability = `interval_valued_session_aware_path_information_bounds`

native 5m OHLC 不能默认等同于真实 fine path。

## 3. 历史 broad evidence

- R1 old identity：unresolved，不是 rejected；可继续在 TRAIN/VALIDATION 研究新 identity。
- R2 old M1：closed。
- R3 old v1：predeclared direction falsified。
- R4 old v1：no candidate qualifies。
- T1 old 5-sigma/960-bar：closed before outcome under its historical supply gate。

这些是 identity-level 历史结论，不限制底层数据重复使用。

## 4. R5 已完成 CL-007 云端验收

Identity：`R5_multiscale_serial_dependence_state_v1`

CL-007 local feedback commit：

`abf95c1c0dacfee487bf2c6ecaa920c697cbfaec`

Cloud review：

`docs/research/reversal_mean_reversion_R5_multiscale_serial_dependence_cloud_review_20260908.md`

正式总裁决：

`R5_partial_support_keep_researching_on_TRAIN_VALIDATION`

### R5-A

供给充分，但离散 mixed-state 的 prevalence 漂移很大：

```text
TRAIN mixed fraction      = 21.97%
VALIDATION mixed fraction =  4.12%
```

所以不把 `short<0 & long>0` 直接升级为稳定 regime classifier。

### R5-B1

当前唯一值得继续的一小块：

```text
TRAIN interaction coefficient = -1.06923
VALIDATION MSE B0 = 1.01165327
VALIDATION MSE B1 = 1.01011161
relative improvement ≈ 0.152%
```

2019、2020 两年 B1 都优于 B0。

这是**小而跨年的增量**，不能直接叫策略成功。

### R5-B2

额外 slow-memory interaction 不优于 B1：

`VALIDATION MSE = 1.01058814`

不升级。

### R5-C

当前“慢趋势中的反向 5m shock 后 15m 恢复”纯统计机制不支持。

- resolved supply 很足：TRAIN 1323 / VALIDATION 723；
- long-memory coefficient = `-2.3923`，与预注册 `>0` 相反；
- VALIDATION mean recovery = `-0.03146`；
- 2019、2020 mean recovery 都为负。

因此当前 R5-C identity 关闭，不通过改 threshold / horizon / parent window 救。

## 5. 当前唯一 R5 后续预算：B1 一次性诊断

Diagnostic identity：

`R5_B1_stability_shape_diagnostic_v1`

目的只有两个：

1. B1 的小幅 improvement 是否广泛出现在 validation trading days，而不是少数日期贡献；
2. anti-persistence 越强时，经验 next-return slope 是否整体更负。

冻结文件：

- `docs/research/reversal_mean_reversion_R5_B1_stability_diagnostic_preanalysis_20260908.md`
- `docs/governance/reversal_mean_reversion_R5_B1_stability_diagnostic_protocol_v1.json`
- `docs/governance/reversal_mean_reversion_R5_B1_diagnostic_execution_freeze_v1.json`
- `scripts/diagnose_broad_rmr_R5_B1_stability_shape.py`
- `tests/unit/test_broad_rmr_R5_B1_stability_shape.py`

## 6. 当前任务：CL-20260908-008

Handoff：

`docs/ops/cl_20260908_008_R5_B1_stability_shape_diagnostic_handoff.md`

本地顺序：

```bash
pytest -q tests/unit/test_broad_rmr_R5_B1_stability_shape.py
```

期望 4 passed，然后：

```bash
python scripts/diagnose_broad_rmr_R5_B1_stability_shape.py \
  --output docs/research/local_broad_rmr_R5_B1_stability_shape_diagnostic_receipt_v1.json
```

只推 compact receipt，使用 `[skip ci]`。

## 7. CL-008 的裁决规则

### D1 — day breadth

2019 和 2020 都必须：

```text
fraction_days_B1_better > 0.50
median day improvement > 0
```

### D2 — mechanism shape

TRAIN feature distribution 固定 anti-persistence 5 个 quintile。VALIDATION、2019、2020 都必须满足：

```text
top-quintile empirical next-return slope < bottom-quintile slope
5-bin slope vs mean anti-persistence trend < 0
```

只有 D1=true 且 D2=true 才允许把 B1 交给专门 research identity。

其它结果都不允许直接升级 HMM/rSLDS/Koopman。

即使 D1+D2 都通过，也仍不自动分配 BLACKBOX。

## 8. 新数据的作用

新数据不是为了替换“用完”的旧数据，而是用于：扩展市场状态、增加稀有事件、提高 1m/3s/tick 路径质量、做跨指数/横截面研究，以及最后给成熟候选留小 BLACKBOX。

## 9. 权限边界

仍禁止：

- 把 TRAIN/VALIDATION 称 fresh OOS；
- 当前 discovery 阶段用 PnL/Sharpe 选模型；
- paper trading / production / Layer 4；
- FactorLab registry mutation；
- outcome 后 favorable day/year/sign/time 筛选；
- native OHLC 伪装 fine path。

Production authority = false。
