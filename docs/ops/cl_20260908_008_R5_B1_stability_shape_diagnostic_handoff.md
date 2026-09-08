# CL-20260908-008 — R5-B1 anti-persistence 稳定性/形状诊断

日期：2026-09-08

状态：`LOCAL EXECUTION REQUIRED / CLOUD REVIEW PENDING`

Diagnostic identity：`R5_B1_stability_shape_diagnostic_v1`

Parent identity：`R5_multiscale_serial_dependence_state_v1`

## 1. 任务目的

只回答两个 post-R5 diagnostic 问题：

1. CL-007 的 B1 小幅 MSE 改善是否广泛分布在 VALIDATION trading days，而不是少数日期贡献；
2. anti-persistence 越强时，经验 next-return slope 是否大体向更负方向移动。

本任务**不改 B1 模型**，不增加任何 feature，不使用 BLACKBOX，不读 2021+，不做 PnL。

## 2. 分支与冻结身份

仓库：`staryocean0/factorlab-two-wave-strategy-lab`

分支：`codex/two-wave-phase1-20260905`

执行前必须更新到包含下列 freeze 的最新分支并核对 blob：

```text
preanalysis
  docs/research/reversal_mean_reversion_R5_B1_stability_diagnostic_preanalysis_20260908.md
  blob 6407af17c2815685677cd261deebe1606d340cd3

protocol
  docs/governance/reversal_mean_reversion_R5_B1_stability_diagnostic_protocol_v1.json
  blob 34ae31a18a3e470f6374d1490a0826c98cd46bc1

runner
  scripts/diagnose_broad_rmr_R5_B1_stability_shape.py
  blob a5f1f4dea7fb46a6d42c7d91f3404b1ec8022f28

tests
  tests/unit/test_broad_rmr_R5_B1_stability_shape.py
  blob 221d08e87894b2947848259af4f1b5d31b41f000

execution freeze
  docs/governance/reversal_mean_reversion_R5_B1_diagnostic_execution_freeze_v1.json
```

任何 blob mismatch：停止，不执行 diagnostic。

## 3. Parent result entry gate

Diagnostic runner 必须先重建并精确复现 CL-007：

```text
TRAIN rows      = 41,685
VALIDATION rows = 21,428

B0 beta = [0.005567078395256155, 0.03487451881755519]
B1 beta = [0.004947147092300985, 0.01303609638446463, -1.069228621037033]

B0 VALIDATION MSE = 1.011653266505294
B1 VALIDATION MSE = 1.0101116108135515
```

absolute tolerance = `1e-12`。

任何 reproduction 失败：停止 D1/D2，并输出：

`R5_B1_diagnostic_execution_drift_or_insufficient`

## 4. Stage 1 — synthetic tests

```bash
pytest -q tests/unit/test_broad_rmr_R5_B1_stability_shape.py
```

期望：4 passed。

若失败，只允许修 implementation bug；不得修改 diagnostic protocol、D1/D2 support rule、B1 模型、数据窗口或 source identity。

## 5. Stage 2 — frozen diagnostic

```bash
python scripts/diagnose_broad_rmr_R5_B1_stability_shape.py \
  --output docs/research/local_broad_rmr_R5_B1_stability_shape_diagnostic_receipt_v1.json
```

### D1

固定 TRAIN-fit B0/B1，按 VALIDATION trading day 计算：

`day_improvement = MSE_B0_day - MSE_B1_day`

报告 pooled、2019、2020 的：days / mean / median / p10 / p90 / fraction_B1_better / weighted MSE。

Frozen D1 support：2019 和 2020 都必须：

```text
fraction_B1_better > 0.50
median day_improvement > 0
```

### D2

只用 TRAIN `anti_persistence` feature 分布生成 20/40/60/80% quintile edges，然后原样应用 VALIDATION。

每个 quintile 描述：

`next_z = alpha + slope * z_t`

报告 TRAIN / VALIDATION / 2019 / 2020 的 5-bin n、mean anti、slope、MSE。

Frozen shape support：VALIDATION、2019、2020 都要：

```text
top quintile slope < bottom quintile slope
linear trend of 5 slopes vs mean anti < 0
```

## 6. 允许 adjudication

只允许：

- `R5_B1_diagnostic_supported_for_specialist_research`
- `R5_B1_mechanism_shape_supported_but_day_breadth_weak`
- `R5_B1_day_breadth_supported_but_shape_weak`
- `R5_B1_small_gain_not_robust_enough_to_specialize`
- `R5_B1_diagnostic_execution_drift_or_insufficient`

只有第一种允许 specialist handoff。其它结果都不允许升级 HMM/rSLDS/Koopman。

## 7. 禁止事项

- 不改 lag/window；
- 不改 B0/B1；
- 不新增 feature；
- 不筛 favorable day/month/sign/time；
- 不做 PnL/Sharpe；
- 不读 2021+；
- 不分配 BLACKBOX；
- 不叫 fresh OOS；
- 不触发 GitHub Actions。

## 8. 回传

使用 `[skip ci]` 推回：

```text
docs/research/local_broad_rmr_R5_B1_stability_shape_diagnostic_receipt_v1.json
```

commit message 至少写：

- test command / exit / passed count；
- diagnostic command / exit；
- source SHA/rows；
- entry reproduction pass/fail；
- BLACKBOX_read=false；
- post_2020_rows_read=false；
- PnL_read=false；
- `local_reported / cloud review pending`。

大数据不推回。
