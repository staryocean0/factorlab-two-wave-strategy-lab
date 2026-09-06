# 两浪研究继续入口：v0.6.7 qualification disagreement decomposition 已闭合（2026-09-06）

## 当前安全状态

冻结上游仍为：

> **v0.5.2 TCSS exact-ridge parent identity + v0.5.4 full-cycle-scale qualification**

操作基线仍为 **v0.4.3**。全局状态仍为：

`morphology_replication_not_yet_accepted`

PR #1 保持 Draft，不合并 main。Direction/D1/D2/PAWCT、H1/H2、第三浪、收益/P&L、fresh OOS、paper trading、production 全部继续冻结。

## 已闭合链条

- v0.6.0：financial identity / exclusive packing 解耦 = Route M；
- v0.6.1：unmatched decomposition，定位 filtered tuple → raw projection displacement 与 upstream filtered instability；
- v0.6.2：raw projection identity audit，证明大量 5m displacement 属 sampling-lattice aliasing；
- v0.6.3：canonical-1m residual audit，ordinal0 extrapolated left support 为主导 residual；
- v0.6.4：real predecessor POC 四 offset 净改善，但 birth-scale evidence 导致 5 个 multi-valued groups，candidate 不 promoted；
- v0.6.5：first-valid causal append-only publication，消除 rewrite 并保留全部 strict-match gain；
- v0.6.6：published strict identity 上 frozen v0.5.4 qualification = mixed stability；
- v0.6.7：qualification disagreement decomposition = **path sampling sensitivity dominant，duration boundary secondary**。

## v0.6.5 immutable identity controls

Published raw strict pairs：

```text
offset1 8,381
offset2 5,770
offset3 6,204
offset4 9,098
aggregate 29,453
```

相对 frozen current projection 净增加 `+2,702` strict pairs。

## v0.6.6 qualification matrix

29,453 strict same-event pairs：

```text
both_qualified                    482
both_rejected                  28,272
main_qualified_other_rejected     352
main_rejected_other_qualified     347
```

Binary agreement = **97.6267%**，但 positive qualification overlap 只有：

`482 / 1,181 = 40.8129%`。

预注册 target repaired strata 的 disagreement 为 `24/80 = 30%` 与 `16/50 = 32%`，因此 v0.6.6 正式裁决：

`mixed_qualification_stability_requires_decomposition`。

## v0.6.7 已正式闭合

结果前文件：

- `docs/research/two_wave_qualification_disagreement_preanalysis_v067.md`
- `docs/research/two_wave_qualification_disagreement_protocol_v067.md`

正式结果：

- `docs/research/two_wave_qualification_disagreement_results_v067.md`
- `cloud_results/cloud_chat_v067_qualification_disagreement_decomposition/summary.json`
- `cloud_results/cloud_chat_v067_qualification_disagreement_decomposition/one_minute_path_diagnostics.json`
- `cloud_results/cloud_chat_v067_qualification_disagreement_decomposition/execution_receipt.json`

Helper blob：`6db7edd79d5e05d5efa4e40d0dfde0ad1794ab09`。

Synthetic tests：**9/9 PASS**。

Hard controls 全部精确复现：

```text
qualification disagreements: 179 / 158 / 187 / 175 = 699
control repaired disagreement:       103 / 3,986
v0.6.3 residual repaired:             63 / 2,390
v0.6.1 target repaired:               24 / 80
v0.6.3 target-residual repaired:      16 / 50
```

Rejected-side reason counts 也精确复现。

## v0.6.7 primary decomposition

```text
path_metric_only          404 / 699 = 57.80%
mixed_multi_family        142 / 699 = 20.31%
duration_geometry_only     82 / 699 = 11.73%
confirmation_clock_only    46 / 699 =  6.58%
amplitude_only             25 / 699 =  3.58%
```

若统计 mixed 中 family involvement：

```text
path metric          538 / 699 = 76.97%
duration geometry    188 / 699 = 26.90%
confirmation clock    76 / 699 = 10.87%
amplitude             50 / 699 =  7.15%
```

## 决定性 canonical-1m path 证据

仅使用 supplied `1m_official` 作为 audit path，不作为 runtime input：

```text
jump_dominated_leg: 368 / 368 -> both_pass on canonical 1m
inefficient_leg:    211 / 211 -> both_fail on canonical 1m
```

即 path-reason 的 5m qualification 分叉在 canonical fine path 上 **579/579 全部收敛**：

- jump disagreement 是某个 5m slicing 压缩路径后产生的 false rejection；
- efficiency disagreement 是某个 5m slicing 压掉曲折度后产生的 false pass。

因此正式裁决：

`path_sampling_sensitivity_dominant_duration_boundary_secondary_target_orientation_persists`

Duration geometry 是第二 workstream：short-leg / short-cycle 等多为 1-bar 级离散边界变化，但 v0.6.7 不授权改 4/12/48/2 等 threshold。

v0.6.1 target repaired 的 qualification disagreement 仍强烈偏向：

`main_qualified_other_rejected = 23/24`，target-residual 为 `15/16`。

## 下一 formal research step

只允许另开 **slicing-invariant path qualification representation** 的 preanalysis + frozen protocol。

必须先回答：

1. qualification 的 path property 应定义在哪个 sampling-invariant path representation 上；
2. `1m_official` 继续只做 audit oracle，还是具备成为 morphology input 的数据/时钟资格；
3. 若 runtime 不能依赖 1m，如何让 path length / jump concentration / efficiency 在不同 5m slicings 下表达同一底层路径属性；
4. jump 与 efficiency 是否是两个独立 hard properties，还是同一 underlying path irregularity 的不同采样投影；
5. replacement representation 必须先证明 prefix causality、same-event slicing invariance 与 synthetic counterexamples，再讨论任何 threshold。

Duration-geometry 作为独立 secondary workstream，不得在同一个 repair experiment 中顺手修改 duration thresholds。

禁止：

- 调 v0.5.4 path/duration threshold；
- 把 1m audit 结果直接当新 qualification rule；
- 修改 matcher / projection evidence / publication；
- 回 D1/D2/PAWCT；
- 使用收益/outcome；
- 进入第三浪或交易层。

**当前下一步只允许 slicing-invariant path qualification representation preanalysis；不得直接修 qualification。**
