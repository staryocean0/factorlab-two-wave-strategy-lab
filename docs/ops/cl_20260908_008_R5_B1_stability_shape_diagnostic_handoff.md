# CL-20260908-008 — R5-B1 anti-persistence 稳定性/形状诊断

日期：2026-09-08

状态：`LOCAL EXECUTION REQUIRED / CLOUD REVIEW PENDING`

Diagnostic identity：`R5_B1_stability_shape_diagnostic_v1`

Parent identity：`R5_multiscale_serial_dependence_state_v1`

## 1. 任务目的

只回答两个 post-R5 diagnostic 问题：

1. CL-007 的 B1 小幅 MSE 改善是否广泛分布在 VALIDATION trading days，而不是少数日期贡献；
2. anti-persistence 越强时，经验 next-return slope 是否大体向更负方向移动。

不改 B1 模型，不增加 feature，不使用 BLACKBOX，不读 2021+，不做 PnL。

## 2. 冻结身份

执行前核对：

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
  blob 539b6bba9f76ebf00584a40b9483bd6c692c30b2

execution freeze
  docs/governance/reversal_mean_reversion_R5_B1_diagnostic_execution_freeze_v1.json
```

Pre-execution incident 已记录在 execution freeze：初版 D2 synthetic fixture 把两个年份放在不同 anti 半区间，导致每年缺 quintiles；已在任何 real diagnostic 前修复为两个年份都覆盖完整 anti range。**科学协议和 runner 均未改变。**

任何 frozen blob mismatch：停止。

## 3. Parent entry reproduction gate

必须精确复现 CL-007：

```text
TRAIN rows      = 41,685
VALIDATION rows = 21,428
B0 beta = [0.005567078395256155, 0.03487451881755519]
B1 beta = [0.004947147092300985, 0.01303609638446463, -1.069228621037033]
B0 VALIDATION MSE = 1.011653266505294
B1 VALIDATION MSE = 1.0101116108135515
```

absolute tolerance = `1e-12`。

失败则停止 D1/D2，输出：

`R5_B1_diagnostic_execution_drift_or_insufficient`

## 4. Stage 1 — synthetic tests

```bash
pytest -q tests/unit/test_broad_rmr_R5_B1_stability_shape.py
```

期望：4 passed。

失败只允许修 implementation bug，不能改 protocol / D1/D2 gate / B1 / source identity。

## 5. Stage 2 — frozen diagnostic

```bash
python scripts/diagnose_broad_rmr_R5_B1_stability_shape.py \
  --output docs/research/local_broad_rmr_R5_B1_stability_shape_diagnostic_receipt_v1.json
```

### D1 — day breadth

固定 TRAIN-fit B0/B1，按 VALIDATION trading day：

`day_improvement = MSE_B0_day - MSE_B1_day`

2019、2020 都必须：

```text
fraction_B1_better > 0.50
median day_improvement > 0
```

才有 `D1=true`。

### D2 — mechanism shape

TRAIN anti-persistence 的 20/40/60/80% quantile 固定 5 个 bins，再原样应用 VALIDATION。

每个 bin 描述：

`next_z = alpha + slope * z_t`

VALIDATION、2019、2020 都必须：

```text
top quintile slope < bottom quintile slope
5-bin slope vs mean anti trend < 0
```

才有 `D2=true`。

## 6. 允许 adjudication

- `R5_B1_diagnostic_supported_for_specialist_research`
- `R5_B1_mechanism_shape_supported_but_day_breadth_weak`
- `R5_B1_day_breadth_supported_but_shape_weak`
- `R5_B1_small_gain_not_robust_enough_to_specialize`
- `R5_B1_diagnostic_execution_drift_or_insufficient`

只有 D1=true 且 D2=true 才允许 specialist handoff。其它结果不允许 HMM/rSLDS/Koopman rescue。

## 7. 禁止事项

- 不改 lag/window/B0/B1；
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

commit message 写明：test/diagnostic command、exit code、passed count、source identity、entry reproduction、BLACKBOX=false、post_2020=false、PnL=false，以及 `local_reported / cloud review pending`。
