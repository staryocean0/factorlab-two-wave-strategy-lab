# v0.6.6 published raw identity qualification stability：正式结果与云端裁决

日期：2026-09-06

状态：`mixed_qualification_stability_requires_decomposition`

操作基线仍为 **v0.4.3**。全局状态仍为 `morphology_replication_not_yet_accepted`。本轮只对 v0.6.5 immutable published raw identity 应用冻结 v0.5.4 qualification；没有修改 projection、predecessor、publication、matcher、threshold、direction、packing、outcome 或 trading logic。

## 1. 冻结问题

结果前文件：

- `docs/research/two_wave_published_identity_qualification_preanalysis_v066.md`
- `docs/research/two_wave_published_identity_qualification_protocol_v066.md`

只回答：

> 已经被 v0.6.5 定义为 strict same financial event 的 published raw identities，在 harmless native-5m slicing 下是否得到一致的 frozen v0.5.4 binary qualification？

Pair identity 在 qualification 之前已经冻结；qualification 不参与 matching。

## 2. Qualification 实现与执行证据

正式 helper：`src/factor_lab/visual_structure/two_wave/published_identity_qualification_v066.py`，Git blob `538860bc070efaf6d5f3fe8bbdc5bb47e8773495`。

Synthetic tests：**5/5 PASS**。

全量运行时，完整 frozen helper 会继续计算 v0.6.6 明确禁用的 direction/geometry，因此执行层另做 qualification-only fast path。第一次 cumulative-sum 加速因约 `1e-12` 浮点差异被拒绝；最终版本保留原始逐-leg numpy `sum/max/mean` 计算，只省略 downstream direction/geometry。

在 **500 个真实 published identities** 上与完整 frozen helper 逐项比较：

- `scale_qualified`
- v0.4.3 / v0.5.4 rejection reasons
- leg / cycle durations
- amplitude ratio
- efficiencies / jump shares / flat shares
- observed days / wall days / confirmation delay

结果：**500/500 exact-equivalence PASS**。

## 3. Frozen pair hard controls

v0.6.5 published raw strict pairs 精确复现：

```text
offset1  8,381
offset2  5,770
offset3  6,204
offset4  9,098
aggregate 29,453
```

四个预注册 repaired strata 也精确复现：

```text
current-control repaired             3,986
v0.6.3 residual repaired            2,390
v0.6.1 projection target repaired      80
v0.6.3 target-residual repaired        50
```

无 control drift。

## 4. Decisive qualification matrix

### offset0 vs offset1

```text
both_qualified                  135
both_rejected                 8,067
main_qualified_other_rejected    89
main_rejected_other_qualified    90
agreement = 8,202 / 8,381 = 97.8642%
```

### offset0 vs offset2

```text
both_qualified                   93
both_rejected                 5,519
main_qualified_other_rejected    90
main_rejected_other_qualified    68
agreement = 5,612 / 5,770 = 97.2617%
```

### offset0 vs offset3

```text
both_qualified                   93
both_rejected                 5,924
main_qualified_other_rejected    89
main_rejected_other_qualified    98
agreement = 6,017 / 6,204 = 96.9858%
```

### offset0 vs offset4

```text
both_qualified                  161
both_rejected                 8,762
main_qualified_other_rejected    84
main_rejected_other_qualified    91
agreement = 8,923 / 9,098 = 98.0765%
```

### Aggregate

```text
both_qualified                  482
both_rejected                28,272
main_qualified_other_rejected   352
main_rejected_other_qualified   347
agreement                    28,754 / 29,453 = 97.6267%
disagreement                    699 / 29,453 = 2.3733%
```

## 5. 为什么不能简单裁决为 broadly stable

总体 97.63% binary agreement 很高，但它主要由 **28,272 个 both-rejected pairs** 驱动。

在至少一边 qualified 的 pair union 中：

```text
union qualified pairs = 1,181
both qualified        =   482
both-qualified / union = 40.8129%
```

Main side qualified 834 对，其中 other side 也 qualified 482 对：**57.79%**。

Other side qualified 829 对，其中 main side 也 qualified 482 对：**58.14%**。

因此 frozen qualification 的“拒绝态”跨 slicing 很稳定，但稀有的 **positive qualification state 并没有同等稳定地 survive harmless slicing**。

## 6. 预注册 repaired strata

| stratum | n | both Q | both reject | main-only Q | other-only Q | disagreement |
|---|---:|---:|---:|---:|---:|---:|
| control repaired | 3,986 | 62 | 3,821 | 55 | 48 | 2.584% |
| v0.6.3 residual repaired | 2,390 | 32 | 2,295 | 39 | 24 | 2.636% |
| v0.6.1 target repaired | 80 | 27 | 29 | 23 | 1 | **30.0%** |
| v0.6.3 target-residual repaired | 50 | 15 | 19 | 15 | 1 | **32.0%** |

前两个大样本 repaired strata 的 binary agreement 与总体一致；但最关键的 v0.6.1 target strata 出现显著不同的结构，而且高度偏向 `main_qualified_other_rejected`。

该 target 分层在结果前已经注册，因此不能用总体 both-rejected 占比把它事后忽略。

## 7. Disagreement hard reasons

699 个 disagreement pairs 的 rejected side hard reasons（可重叠）：

```text
jump_dominated_leg       368
inefficient_leg          211
short_leg                105
confirmation_too_late     76
short_cycle               54
amplitude_mismatch        50
cycle_duration_mismatch   37
long_cycle                 4
```

最大两项是 `jump_dominated_leg` 和 `inefficient_leg`。本轮不允许据此调阈值；这些只定义下一轮 decomposition 的候选机制。

## 8. Per-view qualification 只是描述，不是成功门槛

Published identity 的 frozen v0.5.4 qualified fraction 约 2.09%–2.27%：

```text
offset0 835 / 38,176 = 2.187%
offset1 768 / 36,737 = 2.091%
offset2 796 / 36,619 = 2.174%
offset3 815 / 36,480 = 2.234%
offset4 822 / 36,264 = 2.267%
```

低 coverage 本身不构成失败；本轮 decisive evidence 是 strict same-event pair 上 binary survival 的异质性。

## 9. 正式裁决

v0.6.6 不能裁决为纯 `qualification_broadly_stable_on_strict_identity_pairs`，因为 positive qualification overlap 与预注册 target strata 暴露了 materially different behavior。

也不能简单写成所有 qualification 都失稳，因为：

- 全 pair binary disagreement 只有 2.37%；
- control-repaired / v0.6.3-residual-repaired 两个大样本 strata 的 disagreement 也只有约 2.6%。

因此正式裁决为：

> **`mixed_qualification_stability_requires_decomposition`**

解释：

1. rejection state broadly stable；
2. positive qualification state materially less stable；
3. original v0.6.1 projection-target repaired population 中 qualification instability 明显富集；
4. qualification 因此是一个需要独立 decomposition 的下游不稳定层，但还不能据此修改任何 hard threshold。

## 10. 下一步

如果继续，只允许另开结果前的 **qualification disagreement decomposition**。优先分解：

- `jump_dominated_leg`；
- `inefficient_leg`；
- short-leg / short-cycle；
- confirmation delay；
- amplitude / cycle-duration disagreement；
- 为什么 v0.6.1 target repaired strata 明显偏向 main-qualified / other-rejected。

必须首先区分：

- raw 5m sampling-lattice 对 path metrics 的影响；
- anchor/window 位移留下的 residual geometry 差异；
- hard threshold boundary sensitivity；
- publication-confirmation clock 差异。

不得在 decomposition 前调任何阈值，也不得回到 D1/D2/PAWCT。

## 11. 当前全局状态

`morphology_replication_not_yet_accepted`

v0.4.3 继续作为 operational baseline。Direction/D1/D2/PAWCT、H1/H2、第三浪、收益/P&L、fresh OOS、paper trading、production 全部继续冻结。
