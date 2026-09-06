# v0.6.7 qualification disagreement decomposition：正式结果与云端裁决

日期：2026-09-06

状态：`decomposition_valid_path_sampling_sensitivity_dominant`

操作基线仍为 **v0.4.3**。全局状态仍为 `morphology_replication_not_yet_accepted`。本轮只分解 v0.6.6 已冻结的 qualification disagreement；没有修改 projection、publication、matcher、任何 v0.5.4 threshold、direction、packing、outcome 或 trading logic。

## 1. 结果前冻结

结果前文件：

- `docs/research/two_wave_qualification_disagreement_preanalysis_v067.md`
- `docs/research/two_wave_qualification_disagreement_protocol_v067.md`

正式 helper：

`src/factor_lab/visual_structure/two_wave/qualification_disagreement_v067.py`

Git blob：`6db7edd79d5e05d5efa4e40d0dfde0ad1794ab09`。

Synthetic tests：**9/9 PASS**。

## 2. Hard controls 全部复现

v0.6.5 published raw strict pairs：

```text
offset1 8,381
offset2 5,770
offset3 6,204
offset4 9,098
```

v0.6.6 qualification disagreements：

```text
offset1 179
offset2 158
offset3 187
offset4 175
aggregate 699
```

预注册 repaired strata：

```text
current-control repaired:            103 / 3,986 disagreement
v0.6.3 residual repaired:             63 / 2,390
v0.6.1 projection target repaired:    24 /    80
v0.6.3 target-residual repaired:      16 /    50
```

Rejected-side hard reasons 也精确复现：

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

无 control drift。

## 3. Primary family decomposition

每个 disagreement 按 rejected-side 的 frozen hard reasons 归入互斥 primary family：

| primary family | count | fraction |
|---|---:|---:|
| **path_metric_only** | **404** | **57.80%** |
| mixed_multi_family | 142 | 20.31% |
| duration_geometry_only | 82 | 11.73% |
| confirmation_clock_only | 46 | 6.58% |
| amplitude_only | 25 | 3.58% |

把 mixed 中涉及的 family 也计入后：

```text
path_metric involved        538 / 699 = 76.97%
duration_geometry involved  188 / 699 = 26.90%
confirmation_clock involved   76 / 699 = 10.87%
amplitude involved            50 / 699 =  7.15%
```

所以 path metric 是第一主导机制，不是一个小的边缘现象。

## 4. 最强证据：canonical 1m path 让所有 path-reason disagreement 收敛

v0.6.7 没有把 1m 当 runtime input。只在双方各自已经冻结的 published raw-anchor absolute intervals 上读取 supplied `1m_official` close path，并按原公式计算 efficiency / jump share / flat share。

### `jump_dominated_leg`

368 次 rejected-side jump disagreement：

```text
canonical-1m relation: both_pass = 368 / 368
```

即：在 canonical 1m 路径上，双方都 **不** 触发 `jump_share > 0.5`；只有某一个 5m slicing 把同一底层路径压缩成“单根变化占路径过大”的 rejection。

这支持：`jump_dominated_leg` 的跨 slicing disagreement 是 **5m sampling-lattice false rejection**，不是底层 fine path 真正一边 jump-dominated、一边不是。

### `inefficient_leg`

211 次 rejected-side efficiency disagreement：

```text
canonical-1m relation: both_fail = 211 / 211
```

即：在 canonical 1m 路径上，双方都触发 `efficiency < 0.5`；某一个 5m slicing 因较粗采样把路径曲折度压掉，从而错误通过了 frozen efficiency gate。

这支持：`inefficient_leg` 的跨 slicing disagreement同样是 **5m sampling-lattice sensitivity**，但方向与 jump 相反——不是一侧假拒绝，而是一侧 5m 采样产生假通过。

因此两大 path reasons 在 1m 上 579/579 reason-observations 都不再保持“rejected-only”分叉。

注意：该结论只证明当前 5m path metrics 不是 slicing-invariant；它**不授权**直接把 1m qualification 变成新 runtime rule。

## 5. 这不是纯 threshold epsilon 噪声

Signed frozen-threshold margins 显示 path disagreement 并非全部擦线：

### jump share

Rejected side：

- median `+0.0504`
- p90 `+0.1527`
- max `+0.4047`

Qualified side：

- median `-0.0662`
- p90 `-0.0130`

### efficiency

Rejected side：

- median violation `+0.0299`
- p90 `+0.0974`
- max `+0.2064`

Qualified side：

- median margin `-0.0397`
- p90 `-0.0075`

所以不能把 path instability 简单归结为浮点误差或极小阈值擦边。Canonical-1m 100% collapse 是更直接的机制证据。

## 6. Secondary mechanism：duration geometry 是离散 bar-boundary sensitivity

Duration family 涉及 **188 / 699** disagreements，其中 82 对纯 duration-only。

其 frozen margins 高度离散：

- `short_leg` 105 次：rejected side **全部恰好少 1 bar**；qualified side median 恰好位于 threshold；
- `short_cycle` 54 次：rejected side median少 1 bar；qualified side median在 threshold；
- `long_cycle` 4 次：超出 1–2 bars；
- `cycle_duration_mismatch` 37 次：rejected median ratio excess `+0.0833`，qualified median在 threshold。

这说明 harmless slicing 的 1–几根 anchor/bar allocation 差异会跨越离散 duration gates。它是第二个真实 workstream，但不应与 path sampling 问题混成一个 repair。

## 7. Amplitude / confirmation 是较小但真实的独立层

Amplitude family 涉及 50/699；confirmation family 涉及 76/699。

`confirmation_too_late` rejected side median超阈值 4 bars，而 qualified side median低 3 bars；因此它也不是纯浮点擦边。但 confirmation-only 只有 46/699，且不是 v0.6.1 target repaired enrichment 的主要结构。

Amplitude mismatch 50 次，rejected median ratio excess约 `+0.0739`；需要保留为后续独立诊断，v0.6.7 不调 amplitude threshold。

## 8. v0.6.1 target repaired 的 30%–32% 富集来自哪里

### v0.6.1 projection target repaired

24 个 qualification disagreements：

```text
path_metric_only       12
duration_geometry_only  5
mixed_multi_family      7
```

orientation：

```text
main_qualified_other_rejected 23
main_rejected_other_qualified  1
```

### v0.6.3 target-residual repaired

16 个 disagreements：

```text
path_metric_only        8
duration_geometry_only  4
mixed_multi_family      4
```

orientation：

```text
main_qualified_other_rejected 15
main_rejected_other_qualified  1
```

所以 target enrichment 不是 confirmation-clock-only 主导；它集中在 path / duration geometry，并强烈偏向 offset0 main qualified、offset view rejected。

该偏置是预注册 target strata 中出现的真实结构，后续必须保留，不得用总体 both-rejected 多数去稀释。

## 9. Anchor displacement magnitude 本身不是解释

所有 published strict pairs 本来就满足五个 raw anchors 逐位置 `<=5m`。

在每个 offset 中，qualification-disagreement pairs 与 both-qualified control 的 anchor max/sum displacement 分布非常接近；v0.6.1 target repaired 内 agreement 与 disagreement 的 anchor displacement 也没有一致增大。

例如 offset1：

```text
disagreement max-delta median 4m, sum-delta median 8m
both-qualified max-delta median 4m, sum-delta median 8m
```

offset2/3/4 同样没有“disagreement 只是 anchors 离得更远”的稳定证据。

因此不能通过缩紧/放宽 same-event matcher 解决 qualification disagreement。

## 10. Session overlay 不作为 root cause

699 disagreements 中很多结构跨 lunch / 多交易日，也有较高 session-boundary-nearby prevalence；但这些只按协议保留 overlay，没有建立排除规则，也没有作为 primary attribution。

v0.6.7 不授权增加 session-specific qualification thresholds。

## 11. 正式裁决

正式裁决为：

> **`path_sampling_sensitivity_dominant_duration_boundary_secondary_target_orientation_persists`**

含义：

1. v0.6.6 的 mixed qualification instability 已被进一步定位；
2. 当前最大机制是 path metrics 对 5m slicing lattice 的分辨率依赖；
3. `jump_dominated_leg` 与 `inefficient_leg` 的 5m disagreement 在 supplied canonical 1m path 上分别 100% 收敛为 both-pass / both-fail；
4. duration geometry 是第二个离散边界 workstream；
5. target repaired 的 30%–32% disagreement 主要落在 path/duration，而非 confirmation-only；
6. 不允许通过调 `0.5 / 4 / 12 / 48 / 2 / 8` 等阈值来“修复”本轮发现。

## 12. 下一步允许做什么

下一步如果继续，必须另开结果前的 **slicing-invariant path qualification representation preanalysis**。

它首先要回答：

- qualification 的 path property 应定义在什么 sampling-invariant path 上；
- supplied `1m_official` 是否只应继续作为 audit oracle，还是可以成为可部署 morphology input；
- 若不允许依赖 1m，如何定义在不同 5m slicing 下等价的 path length / jump concentration / efficiency；
- jump 与 efficiency 是否应该继续是两个 hard gates，还是只是同一 underlying path irregularity 的不同观测投影；
- replacement representation 必须先通过 prefix causality、same-event slicing invariance 和 synthetic path counterexamples，再讨论 threshold。

Duration-geometry disagreement 应作为单独 secondary workstream，不得在同一个 repair experiment 中顺手改 duration thresholds。

Direction/D1/D2/PAWCT、H1/H2、第三浪、收益/P&L、fresh OOS、paper trading 和 production 全部继续冻结。

当前全局状态仍为：

`morphology_replication_not_yet_accepted`
