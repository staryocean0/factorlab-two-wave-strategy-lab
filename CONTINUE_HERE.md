# 两浪研究继续入口：v0.6.8 canonical fine-path POC 已闭合（2026-09-06）

## 当前安全状态

冻结上游仍为：

> **v0.5.2 TCSS exact-ridge parent identity + v0.5.4 full-cycle-scale qualification**

操作基线仍为 **v0.4.3**。全局状态仍为：

`morphology_replication_not_yet_accepted`

PR #1 保持 Draft，不合并 main。Direction/D1/D2/PAWCT、H1/H2、第三浪、收益/P&L、fresh OOS、paper trading、production 全部继续冻结。

## 已闭合链条

- v0.6.0：financial identity / exclusive packing 解耦 = Route M；
- v0.6.1：unmatched decomposition；
- v0.6.2：raw projection identity audit；
- v0.6.3：ordinal0 left-support residual 定位；
- v0.6.4：birth-scale predecessor POC，机制有效但 identity 多值，不 promoted；
- v0.6.5：first-valid causal append-only publication，消除 rewrite 并保留 strict-match gain；
- v0.6.6：published strict identity 上 frozen v0.5.4 qualification = mixed stability；
- v0.6.7：qualification disagreement decomposition = path sampling sensitivity dominant；
- v0.6.8：canonical 1m path representation POC = **binary disagreement 下降，但主要来自 joint rejection inflation，不 promoted**。

## v0.6.5 immutable identity controls

Published raw strict pairs：

```text
offset1 8,381
offset2 5,770
offset3 6,204
offset4 9,098
aggregate 29,453
```

## v0.6.6 control qualification

```text
both_qualified                    482
both_rejected                  28,272
main_qualified_other_rejected     352
main_rejected_other_qualified     347
```

Control disagreement = `699 / 29,453 = 2.3733%`。

Control positive metrics：

```text
union-qualified 1,181
both-qualified    482
positive overlap 40.8129%
main survival    57.79%
other survival   58.14%
```

## v0.6.7 机制结论

699 disagreements：

```text
path_metric_only          404
mixed_multi_family        142
duration_geometry_only     82
confirmation_clock_only    46
amplitude_only             25
```

Path family involved `538 / 699 = 76.97%`。

Canonical 1m audit：

```text
jump_dominated_leg 368/368 -> both_pass
inefficient_leg    211/211 -> both_fail
```

因此 5m path gates materially sampling-lattice sensitive。

## v0.6.8 已正式闭合

结果前：

- `docs/research/two_wave_canonical_path_qualification_preanalysis_v068.md`
- `docs/research/two_wave_canonical_path_qualification_protocol_v068.md`

正式结果：

- `docs/research/two_wave_canonical_path_qualification_results_v068.md`
- `cloud_results/cloud_chat_v068_canonical_path_qualification/summary.json`
- `cloud_results/cloud_chat_v068_canonical_path_qualification/execution_receipt.json`

Helper blob：`5096e8b4806e216845164a6ce3079029a69e4281`。

Synthetic tests：**8/8 PASS**。

所有 hard controls 精确复现；supplied 1m canonical path 对所有 published identities 可用，未 resample / interpolate。

## v0.6.8 candidate matrix

Candidate 只在 supplied 1m path 上重算 frozen efficiency/jump/flat reasons，所有 non-path reasons 和 thresholds 不变。

```text
both_qualified                    103
both_rejected                  29,177
main_qualified_other_rejected      81
main_rejected_other_qualified      92
```

Binary disagreement：

`173 / 29,453 = 0.5874%`

虽然比 control 2.37% 低，但 positive state 变差：

```text
control union-qualified    1,181 -> candidate 276
control both-qualified       482 -> candidate 103
positive overlap          40.81% -> 37.32%
main survival             57.79% -> 55.98%
other survival            58.14% -> 52.82%
```

482 个 control both-qualified 中：

```text
candidate both-qualified  53
candidate both-rejected  388
candidate disagreement    41
```

699 个 control disagreement 中，574 个变成 candidate both-rejected，只有 38 个变成 both-qualified。

因此正式裁决：

`shared_fine_path_mainly_increases_joint_rejection_without_solving_positive_stability`

## 数学含义

简单把 path measurement 从 5m 换成 shared 1m，并保留原 5m thresholds，不是合法修复。

更细 sampling 会系统性改变 path metrics：

- observed total variation 通常增加；
- efficiency 通常下降；
- jump share 通常下降。

所以 `metric + threshold` 是一个 resolution-specific measurement system。v0.6.8 说明问题已经从“不同 slicing lattice”推进到“path metric 的 sampling-resolution semantics”。

## 下一 formal research step

只允许另开 **path-metric sampling-resolution semantics preanalysis**。

必须先回答：

1. efficiency / jump share / flat share 随 sampling refinement 的数学行为与可识别性；
2. 当前 hard gates 真正想表达的 morphology property 是什么，而不是直接继承某个 lattice 的数值；
3. 是否存在 threshold-free / scale-normalized path representation；
4. 若 1m 只做 audit oracle，5m runtime 能否构造有 invariance/error-bound 的代理；
5. replacement metric 在任何 threshold 讨论前必须先证明 prefix causality、resolution semantics、cross-slicing stability 和 synthetic counterexamples。

Duration-geometry 仍是独立 secondary workstream；不得在 path experiment 中顺手改 4/12/48/2 等 duration thresholds。

禁止：

- 直接采用 1m path + 原 0.5 threshold；
- 根据 v0.6.8 拟合新的 path threshold；
- 修改 matcher / projection / publication；
- 回 D1/D2/PAWCT；
- 使用收益/outcome；
- 进入第三浪或交易层。

**当前下一步只允许 path-metric sampling-resolution semantics preanalysis；不得直接改 qualification threshold。**
