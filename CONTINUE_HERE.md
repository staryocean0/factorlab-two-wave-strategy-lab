# 两浪研究继续入口：v0.6.6 qualification stability 已闭合，下一步 qualification disagreement decomposition（2026-09-06）

## 当前安全状态

冻结上游仍为：

> **v0.5.2 TCSS exact-ridge parent identity + v0.5.4 full-cycle-scale qualification**

操作基线仍为 **v0.4.3**。全局状态仍是：

`morphology_replication_not_yet_accepted`

PR #1 保持 Draft，不合并 main。Direction/D1/D2/PAWCT、H1/H2、第三浪、收益/P&L、fresh OOS、paper trading、production 全部继续冻结。

## 已闭合研究链

- v0.6.0：qualified financial identity 与 exclusive packing 解耦，正式 Route M；
- v0.6.1：unmatched identity decomposition，定位 raw projection displacement / upstream filtered instability；
- v0.6.2：raw projection identity audit，证明大量 5m displacement 属 sampling-lattice aliasing，但仍有 canonical-1m residual；
- v0.6.3：phase-window residual audit，定位 ordinal0 extrapolated left support 为主导 residual mechanism；
- v0.6.4：birth-scale predecessor ordinal0 POC，四 offset 均净改善，但因 birth-scale evidence 导致 5 个 multi-valued groups，candidate 不 promoted；
- v0.6.5：first-valid causal append-only publication，消除 multi-valued rewrite，完整保留 v0.6.4 的 strict-match gain；
- v0.6.6：对 v0.6.5 immutable published raw identity 重算 frozen v0.5.4 qualification，正式裁决 **mixed qualification stability**。

## v0.6.5 当前 immutable publication controls

Published raw strict pairs：

```text
offset1 8,381
offset2 5,770
offset3 6,204
offset4 9,098
aggregate 29,453
```

相对 frozen current projection，strict pair 净增加 `+2,702`。

预注册 repaired strata：

```text
control repaired               3,986
v0.6.3 residual repaired       2,390
v0.6.1 target repaired            80
v0.6.3 target-residual repaired   50
```

## v0.6.6 正式 qualification matrix

29,453 strict same-event pairs：

```text
both_qualified                  482
both_rejected                28,272
main_qualified_other_rejected   352
main_rejected_other_qualified   347
```

Binary agreement：`28,754 / 29,453 = 97.6267%`。

但该高 agreement 主要由 both-rejected 驱动。在至少一侧 qualified 的 1,181 对中，仅 482 对 both-qualified：

`both-qualified / union-qualified = 40.8129%`

Main-qualified survival to other：`57.79%`；other-qualified survival to main：`58.14%`。

## 预注册 repaired strata

```text
control repaired:            disagreement 103 / 3,986 = 2.584%
v0.6.3 residual repaired:    disagreement  63 / 2,390 = 2.636%
v0.6.1 target repaired:      disagreement  24 /    80 = 30.0%
v0.6.3 target-residual:      disagreement  16 /    50 = 32.0%
```

因此 rejection state broadly stable，但 positive qualification state 和原 v0.6.1 target repaired population materially less stable。

Formal v0.6.6 adjudication：

`mixed_qualification_stability_requires_decomposition`

正式结果：

`docs/research/two_wave_published_identity_qualification_results_v066.md`

Compact evidence：

`cloud_results/cloud_chat_v066_published_identity_qualification/`

## Disagreement reasons（可重叠）

699 个 disagreement pairs 的 rejected side：

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

这些是下一轮 decomposition 的候选机制，不授权调 threshold。

## 下一 formal research step

先另开 **qualification disagreement decomposition** 的 preanalysis + frozen protocol，只解释 qualification 为什么在 strict same-event pair 中分叉。

至少需要区分：

1. 5m sampling lattice 对 path efficiency / jump share 的影响；
2. anchor/window residual displacement 对腿长度、cycle duration、amplitude 的影响；
3. hard threshold boundary sensitivity；
4. publication confirmation clock 差异；
5. 为什么 v0.6.1 target repaired strata 强烈偏向 main-qualified / other-rejected。

禁止：

- 根据当前 disagreement 调任何 v0.5.4 threshold；
- 重新选择 projection evidence；
- 放宽 same-event matcher；
- 回到 D1/D2/PAWCT；
- 使用收益/outcome；
- 进入第三浪或交易层。

## 优先阅读

1. `docs/research/two_wave_published_identity_qualification_results_v066.md`
2. `cloud_results/cloud_chat_v066_published_identity_qualification/summary.json`
3. `cloud_results/cloud_chat_v066_published_identity_qualification/repaired_strata_qualification.json`
4. `docs/research/two_wave_published_identity_qualification_protocol_v066.md`
5. `docs/research/two_wave_scale_invariant_predecessor_publication_results_v065.md`
6. `docs/research/two_wave_ordinal0_predecessor_support_results_v064.md`

**当前下一步只允许 qualification disagreement decomposition；不得直接修 qualification。**
