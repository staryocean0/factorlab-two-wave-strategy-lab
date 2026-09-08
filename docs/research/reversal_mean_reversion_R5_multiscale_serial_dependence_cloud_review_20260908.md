# R5 multiscale serial dependence — CL-20260908-007 云端独立复核

日期：2026-09-08

Research identity：`R5_multiscale_serial_dependence_state_v1`

本地回传 commit：`abf95c1c0dacfee487bf2c6ecaa920c697cbfaec`

本地执行基线：`619c3536c3707aa0d403a7328d3a318cb1e63223`

状态：`CLOUD REVIEWED / PARTIAL SUPPORT`

## 1. 执行身份验收

回传 commit 的 parent 是 `619c3536c3707aa0d403a7328d3a318cb1e63223`，与本地报告一致。

冻结 artifact blob 在回传 commit 中保持不变：

```text
preanalysis  e9f901e98485226678eb1324a3447df3472ea136
protocol     87446bd1d16baf280220cdd10ab53cd45193e649
runner       cd0ac94f7f8dc4fba7c9ee25701bcca02f551f2a
tests        cd3b91b528185912c085bab9b3e8caf6dba4c956
```

本地 commit message 报告：

```text
pytest -q tests/unit/test_broad_rmr_R5_multiscale_serial_dependence.py
exit 0 / 7 passed

python scripts/run_broad_rmr_R5_multiscale_serial_dependence.py \
  --output docs/research/local_broad_rmr_R5_multiscale_serial_dependence_receipt_v1.json
exit 0
```

Source identity：

```text
000852.SH
5m_offset_0.parquet
rows = 70,114
sha256 = bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48
2015-01-05..2020-12-31
```

Receipt flags：

```text
BLACKBOX_read = false
post_2020_rows_read = false
PnL_read = false
fresh_OOS_claim = false
```

因此本次执行可由 `local_reported` 升级为 `cloud_reviewed`。

用户另报告 compact receipt sha256：

`9f0e76c9955512d522c75674cd031f596289e76b71e6bbeb3a714bff1da833e9`

云端 connector 已确认 commit 中 receipt 的 Git blob 为 `d29efc202be4ab140c10fabb1321015e7e452944`；当前云端没有独立 raw-byte 下载面，因此不把用户报告的 sha256 误写成云端重新计算值。

## 2. R5-A — mixed-state phenomenon

Frozen supply gate 通过：

```text
TRAIN mixed_state      = 9,576 >= 500
VALIDATION mixed_state =   924 >= 200
```

但状态分布发生明显漂移：

```text
TRAIN mixed fraction      = 21.97%
VALIDATION mixed fraction =  4.12%

TRAIN short-negative fraction      = 27.08%
VALIDATION short-negative fraction = 16.26%

TRAIN long-positive fraction       = 63.95%
VALIDATION long-positive fraction  = 65.96%
```

解释：较慢正 memory 的正号频率比较稳定；主要变化来自 short-memory 负号显著减少。因此 `short<0 & long>0` 作为一个离散 regime 的出现频率不稳定。

裁决：

`R5_A_supply_passed_but_discrete_mixed_state_prevalence_is_not_stable_enough_for_regime_promotion`

它可以作为现象描述保留，但当前不升级为固定 regime classifier。

## 3. R5-B — anti-persistence interaction

Frozen B1 core gate 通过。

TRAIN interaction coefficient：

```text
c[z_t * anti_persistence] = -1.0692286210
```

符合预注册方向 `<0`。

VALIDATION pooled MSE：

```text
B0 = 1.0116532665
B1 = 1.0101116108
absolute improvement = 0.0015416557
relative improvement ≈ 0.1524%
```

逐年：

```text
2019: 0.9986089092 -> 0.9961336416   improvement ≈ 0.2479%
2020: 1.0247513043 -> 1.0241471025   improvement ≈ 0.0590%
```

所以方向在 2019、2020 都一致，但 effect size 很小。

B2 仅因 B1 通过才合法计算。其 VALIDATION MSE：

```text
B2 = 1.0105881396
```

B2 仍略优于 B0，但明显差于 B1。额外 slower-memory interaction 没有改善核心模型。

裁决：

`R5_B1_small_but_chronologically_consistent_incremental_support`

保留 B1 进入**一轮有限诊断**；不推广 B2，不上 HMM/rSLDS/Koopman。

## 4. R5-C — counter-trend shock recovery

Resolved supply 充分：

```text
TRAIN      = 1,323 >= 150
VALIDATION =   723 >= 100
2019       =   357
2020       =   366
```

C1 pooled MSE 虽有极小改善：

```text
C0 = 3.3148781474
C1 = 3.3131383320
relative improvement ≈ 0.0525%
```

但 frozen mechanism direction 明确失败：

```text
long_memory coefficient    = -2.3923096558   required > 0  -> FAIL
anti_persistence coefficient = +0.4310511578 required > 0  -> PASS
```

逐年也不稳定：2019 C1 改善，2020 C1 恶化。

更重要的是 raw recovery descriptive 在所有证据块均为负：

```text
TRAIN mean recovery      = -0.08983 ; positive fraction 47.85%
VALIDATION mean recovery = -0.03146 ; positive fraction 46.47%
2019 mean recovery       = -0.03380 ; positive fraction 44.54%
2020 mean recovery       = -0.02919 ; positive fraction 48.36%
```

因此当前纯统计定义下，不能声称“较慢趋势中的反向 5m shock 更容易在之后 15m 均值回归”。

裁决：

`R5_C_low_capacity_countertrend_recovery_mechanism_not_supported`

不得通过改变 80% threshold、12-bar parent drift、3-bar horizon、年份/方向筛选来把本 identity 救成成功。

## 5. 总裁决

接受 frozen overall adjudication：

`R5_partial_support_keep_researching_on_TRAIN_VALIDATION`

其精确含义是：

- R5-A：供给通过，但离散 mixed-state prevalence 漂移明显；不升级 classifier；
- R5-B1：小幅、方向正确、2019/2020 都改善，值得一轮有限 diagnostic；
- R5-B2：不优于 B1，关闭当前复杂升级；
- R5-C：机制方向失败，关闭当前 identity；
- BLACKBOX：仍不分配；
- PnL / trading：仍不授权。

## 6. 下一步预算

只给 R5-B1 **一次有限诊断预算**，回答两个问题：

1. B1 的小幅 MSE 改善是否广泛分布在 validation days，而不是少数日期贡献；
2. anti-persistence 越强时，经验 next-return slope 是否大体呈更负的单调形状。

诊断使用同一 TRAIN / VALIDATION，允许查看细节，因为 VALIDATION 不是 BLACKBOX。

若这两个诊断不支持稳定/单调机制，则关闭 B1，不上复杂 state model。

若支持，则可把 B1 作为一个**专门机制候选**继续 TRAIN/VALIDATION 研究；仍不自动分配 BLACKBOX。

Production authority = false。
