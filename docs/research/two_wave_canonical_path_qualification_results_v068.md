# v0.6.8 canonical fine-path qualification representation：正式结果与云端裁决

日期：2026-09-06

状态：`shared_fine_path_mainly_increases_joint_rejection_without_solving_positive_stability`

操作基线仍为 **v0.4.3**。全局状态仍为 `morphology_replication_not_yet_accepted`。本轮只把 v0.5.4 的三个 path hard reasons 改为在 supplied `1m_official` canonical path 上重算；没有修改 raw identity、projection、publication、matcher、duration/amplitude/calendar/confirmation metric、任何 threshold、direction、packing、outcome 或 trading logic。

## 1. 结果前冻结

结果前文件：

- `docs/research/two_wave_canonical_path_qualification_preanalysis_v068.md`
- `docs/research/two_wave_canonical_path_qualification_protocol_v068.md`

单一 registered representation：

`supplied_1m_canonical_path_for_path_gates_v068`

对每个 v0.6.5 immutable published identity 的四条 absolute anchor-time legs，只从 supplied `1m_official` 读取 close path，按 frozen 公式重算：

- efficiency；
- jump share；
- flat share。

仍使用 frozen `0.5 / 0.5 / 0.5` path thresholds。所有 non-path hard reasons 逐条保留。

Helper：`src/factor_lab/visual_structure/two_wave/canonical_path_qualification_v068.py`，Git blob `5096e8b4806e216845164a6ce3079029a69e4281`。

Synthetic tests：**8/8 PASS**。

## 2. Hard controls 全部复现

Published raw strict same-event pairs：

```text
offset1 8,381
offset2 5,770
offset3 6,204
offset4 9,098
aggregate 29,453
```

v0.6.6 control matrix 精确复现：

```text
both_qualified                    482
both_rejected                  28,272
main_qualified_other_rejected     352
main_rejected_other_qualified     347
```

四个 repaired strata 的 denominator / control disagreement 也精确复现：

```text
3,986 / 103
2,390 / 63
80 / 24
50 / 16
```

v0.6.7 path controls 精确复现：

```text
jump_dominated_leg 368
inefficient_leg    211
```

无 control drift。

## 3. Canonical 1m 数据可用性

五个视图的全部 v0.6.5 published identities 都能构造四条 canonical-1m leg path：

```text
canonical_path_unavailable = 0
```

大多数 published anchor timestamps 在 1m source 上精确存在；非全部端点精确的 identity 很少：

```text
offset0 0
offset1 4
offset2 5
offset3 7
offset4 5
```

本轮没有插值、填充或合成端点；candidate 只使用 supplied rows in closed interval。

## 4. Per-view candidate qualification：qualified population 大幅收缩

Control v0.6.6 qualified counts 约为 768–835 / view。

Canonical-1m path candidate：

```text
offset0 127 / 38,176
offset1 113 / 36,737
offset2 129 / 36,619
offset3 136 / 36,480
offset4 120 / 36,264
```

总体现象是：在更细 shared path 上，`inefficient_leg` 大量增加，而 `jump_dominated_leg` 大量减少。

例如 offset0：

```text
control inefficient_leg 10,066
candidate inefficient_leg 29,669

control jump_dominated_leg 28,975
candidate jump_dominated_leg 3,399
```

这与 v0.6.7 的机制一致：sampling refinement 会暴露更多路径曲折度，同时减少单步变化占总路径的比例。

但这也说明 frozen 0.5 thresholds 本身绑定于 measurement resolution；不能把“共享 1m path”与“原 5m threshold”简单组合后当作新 morphology rule。

## 5. Candidate pair matrix

在完全相同的 29,453 strict same-event pairs 上：

```text
both_qualified                    103
both_rejected                  29,177
main_qualified_other_rejected      81
main_rejected_other_qualified      92
```

Binary disagreement 从 control：

`699 / 29,453 = 2.3733%`

下降到 candidate：

`173 / 29,453 = 0.5874%`

表面上 agreement 升到 **99.4126%**。

但该改善主要来自双方一起被拒绝。

## 6. Positive qualification stability 没有改善，反而变差

Control：

```text
union-qualified = 1,181
both-qualified  =   482
positive overlap = 40.8129%
main survival = 57.79%
other survival = 58.14%
```

Candidate：

```text
union-qualified = 276
both-qualified  = 103
positive overlap = 37.3188%
main survival = 55.98%
other survival = 52.82%
```

因此 candidate 并没有解决 v0.6.6 的核心问题：“positive qualification 是否能跨 harmless slicing survive”。

它只是把 qualified union 从 1,181 压缩到 276，同时把 both-qualified 从 482 压缩到 103。

## 7. Control → candidate transition 证明 agreement 改善主要来自 joint rejection

699 个 control disagreement 中：

- 转成 candidate both-rejected：**574**；
- 转成 candidate both-qualified：**38**；
- 仍 disagreement：**87**。

也就是说，control disagreement 的大多数“修复”来自双方共同拒绝，而不是双方共同认可同一个 morphology。

更重要的是，482 个 control both-qualified 中：

```text
retained both-qualified   53
became both-rejected     388
became disagreement       41
```

即原来双方都通过的 strict same-event pairs 只有约 **11%** 仍 both-qualified。

这直接否决“canonical 1m path + frozen 5m thresholds”作为可 promotion 的 path qualification representation。

## 8. Repaired strata 也没有获得正向稳定性

### current-control repaired，n=3,986

Candidate：

```text
both-qualified 13
both-rejected 3,943
main-only 15
other-only 15
positive overlap 30.23%
```

### v0.6.3 residual repaired，n=2,390

```text
both-qualified 9
both-rejected 2,361
main-only 10
other-only 10
positive overlap 31.03%
```

### v0.6.1 target repaired，n=80

Control positive overlap = `27/(27+23+1) = 52.94%`。

Candidate：

```text
both-qualified 3
both-rejected 65
main-only 5
other-only 7
positive overlap 20.0%
```

### v0.6.3 target-residual repaired，n=50

Candidate：

```text
both-qualified 3
both-rejected 40
main-only 3
other-only 4
positive overlap 30.0%
```

所以最重要的 target strata 也被 joint rejection 明显压缩，而不是得到更强的 positive morphology agreement。

## 9. 数学解释：path metrics 与 sampling resolution 绑定

对同一底层路径，在更细 partition 上：

- observed total variation 通常增加或不减；
- 因此 `efficiency = net displacement / observed variation` 通常下降；
- 单步变化相对 total variation 的 `jump_share` 通常下降。

v0.6.7 已经观察到：5m jump split 在 1m 上全部变 both-pass，而 5m efficiency split 在 1m 上全部变 both-fail。

v0.6.8 全体 published identity replay 进一步证明，直接保留原 5m threshold 会系统性改变 qualification population。

因此问题不只是“5m lattice 不共享”；**metric + threshold 共同定义了一个 resolution-specific measurement system**。

这不授权事后修改 0.5 threshold。它要求先重新研究 path property 的 resolution semantics。

## 10. 正式裁决

按冻结四选一规则，正式裁决为：

> **`shared_fine_path_mainly_increases_joint_rejection_without_solving_positive_stability`**

理由：

1. candidate 显著减少 binary disagreement；
2. 但 disagreement reduction 主要来自 both-rejected inflation；
3. both-qualified 与 union-qualified 大幅收缩；
4. positive overlap / survival 没有改善；
5. target repaired strata 反而显著失去 positive qualification；
6. 因此不能把 supplied 1m path + 原 5m path thresholds promoted 成新 qualification representation。

## 11. 下一步允许做什么

下一步只能另开 **path-metric sampling-resolution semantics preanalysis**。

必须先回答：

- efficiency / jump share / flat share 在不同 sampling resolution 下的数学尺度行为；
- 哪些 path properties 是真正要表达的 morphology invariants，哪些只是某个 lattice 的测量代理；
- 是否存在 threshold-free 或 scale-normalized representation；
- 1m 继续只能作为 audit oracle，除非另行通过 live data-clock eligibility；
- 若 runtime 只能使用 5m，必须先证明任何 approximation 的 invariance/error bounds，不能按 v0.6.8 结果拟合阈值。

Duration-geometry 仍是独立 secondary workstream，不在下一 path experiment 中修改。

Direction/D1/D2/PAWCT、H1/H2、第三浪、收益/P&L、fresh OOS、paper trading、production 全部继续冻结。

当前全局状态仍为：

`morphology_replication_not_yet_accepted`
