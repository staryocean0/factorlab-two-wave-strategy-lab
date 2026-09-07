# v0.6.11 endpoint/interval sensitivity of fine roughness：正式结果与云端裁决

日期：2026-09-07

状态：`endpoint_erosion_ensemble_materially_reduces_roughness_interval_sensitivity`

操作基线仍为 **v0.4.3**；全局状态仍为 `morphology_replication_not_yet_accepted`。本轮只研究 v0.6.10 已定位的 fine-roughness endpoint sensitivity；没有修改 qualification、threshold、identity、matcher、projection、publication、direction、outcome 或 trading logic。Fine concentration/origin-ensemble 的 native-5m deployable proxy 明确留给后续独立版本。

## 1. 结果前冻结

- `docs/research/two_wave_roughness_interval_sensitivity_preanalysis_v0611.md`
- `docs/research/two_wave_roughness_interval_sensitivity_protocol_v0611.md`
- helper：`src/factor_lab/visual_structure/two_wave/roughness_interval_sensitivity_v0611.py`，Git blob `bc3275c6c94ec8b5d5cc7c4979c278c4f74169b9`
- test：`tests/unit/test_two_wave_roughness_interval_sensitivity_v0611.py`，Git blob `10b99bb63b3d378ce6c3a7513e89865bba154dc9`

Synthetic semantics gate：**9/9 PASS**。

注册候选只有一个：对每条 published leg 单视图、向内枚举 `(start erosion, end erosion) ∈ {0..4}²` 的 25 个 supplied-1m 子区间，取定义良好的 roughness 的 median 和 range。没有 best-cell selection；没有 counterpart information；没有 threshold。

`common_support = [max(start_A,start_B), min(end_A,end_B)]` 只作为 counterpart-dependent audit oracle，不是候选。

## 2. Hard controls 全部闭合

当前 Chat runtime 重置后，从冻结数据和研究链重新构造上游，精确复现：

```text
tuple births       38,636 / 37,176 / 37,062 / 36,937 / 36,689
publications       38,176 / 36,737 / 36,619 / 36,480 / 36,264
filtered pairs     14,784 / 12,725 / 13,412 / 16,108
raw strict pairs    8,381 /  5,770 /  6,204 /  9,098 = 29,453
```

v0.6.6 qualification matrix再次精确复现：

```text
both-qualified                  482
both-rejected                28,272
main-qualified/other-rejected   352
main-rejected/other-qualified   347
```

v0.6.1 target repaired：`28 / 20 / 12 / 20 = 80`；其中 qualification disagreement `10 / 7 / 3 / 4 = 24`。

无 behavioral control drift。

## 3. v0.6.10 fine-roughness reference 精确恢复

在相同 29,453 strict same-event pairs 的对应四腿上，原始 fine roughness 可比较 pair-leg universe 精确恢复为 **117,805**。

原始 `fine_roughness = log(TV1/D)` cross-slicer absolute difference：

```text
median = 0.08314519
p90    = 0.39279614
p99    = 1.00639124
mean   = 0.15669478
```

这与 v0.6.10 aggregate reference 一致，因此 v0.6.11 decisive comparison 使用的是同一个 universe，没有 availability-selection 换样本。

## 4. Registered endpoint-erosion ensemble 显著降低 interval sensitivity

`erosion_roughness_median` absolute pair difference：

```text
median = 0.02808574
p90    = 0.17739900
p99    = 0.54414068
mean   = 0.06748595
```

相对原始 fine roughness：

- median 降低 **66.22%**；
- p90 降低 **54.84%**；
- 117,805 pair-legs 中 candidate difference 更小 **83,901 = 71.22%**；
- equal 162；
- larger 33,742；
- decisive pair-leg universe仍为 **117,805 / 117,805**，没有因为候选 availability 丢样本。

四个 harmless offsets 全部同向：

| pair | n pair-leg | original median | erosion median | smaller / equal / larger |
|---|---:|---:|---:|---:|
| offset0 vs 1 | 33,524 | 0.07521 | 0.02210 | 24,326 / 59 / 9,139 |
| offset0 vs 2 | 23,080 | 0.10472 | 0.03992 | 16,293 / 6 / 6,781 |
| offset0 vs 3 | 24,814 | 0.10340 | 0.04052 | 17,413 / 38 / 7,363 |
| offset0 vs 4 | 36,387 | 0.06506 | 0.01991 | 25,869 / 59 / 10,459 |

因此改善不是某一个 offset 的偶然现象。

## 5. Availability 没有解释改善

在 decisive pair-leg 两侧共 235,610 个 side-leg observations 中，registered 25-cell ensemble 的 defined-count 分布为：

```text
25 cells: 209,776
20 cells:   1,031
15 cells:  18,714
10 cells:   1,556
5 cells:    4,060
其余少量：9/13/14/19/24 cells
```

没有任何 decisive side-leg 出现 zero-defined ensemble。

Undefined cells 的原因全部按冻结语义保留：

```text
interval_collapse       179,010
missing_shifted_start   121,100
zero_net_displacement       259
zero_total_variation         230
```

因此 candidate 改善不是通过删除困难 legs 获得。

## 6. Exact decomposition 证实 endpoint displacement 是核心机制之一

原始 counterpart roughness 满足：

`ΔR = ΔlogTV - ΔlogD`。

全量最大 identity error：**2.22e-15**。

117,805 pair-legs：

```text
median |ΔlogTV| = 0.05373
median |ΔlogD|  = 0.07337

|ΔlogTV| > |ΔlogD| : 37,527
|ΔlogTV| < |ΔlogD| : 80,147
                         equal : 131
```

所以 roughness 分叉通常不只是 fine TV 不同；published endpoint 轻微错位导致的 endpoint displacement `D` 变化在多数 pair-leg 上是更大的对数项。

这与 v0.6.10 的“shared fine path 仍 interval-sensitive”结论一致。

## 7. Common-support oracle 支持 boundary-effect 解释，但不进入候选

对全部 **117,805** pair-legs，counterpart-dependent common-support interval 都可以定义。

各 side 原始 fine roughness 到 common-support roughness 的 absolute deviation（235,610 sides）：

```text
median = 0.02648
p90    = 0.27389
p99    = 0.83146
```

这说明两侧 fine roughness 的差异可以通过“比较的是略不同绝对区间”得到实质解释。

但 common-support 需要 counterpart information，因此严格保持 audit-only，不能成为 single-view recognizer input。

## 8. Boundary-sliver diagnostics 显示前后 4 分钟足以 materially 改变 TV/D

在可定义 side-legs 上：

```text
left 4m removed-TV fraction  median 0.1477
right 4m removed-TV fraction median 0.1587
both 4m removed-TV fraction  median 0.3016
```

对应 absolute roughness change median：

```text
left4  0.0671
right4 0.0785
both4  0.1392
```

因此一个名义 5m bar 内的 endpoint displacement 可以改变相当比例的 fine total variation 与 endpoint displacement，不是微小浮点效应。

## 9. Frozen strata 没有反转主结论

| stratum | pair-legs | original median | erosion median | candidate smaller fraction |
|---|---:|---:|---:|---:|
| both-qualified | 1,928 | 0.05244 | 0.02803 | 64.32% |
| qualification disagreement | 2,796 | 0.06341 | 0.03412 | 66.27% |
| target repaired | 320 | 0.06184 | 0.02564 | 65.31% |
| target agreement | 224 | 0.05828 | 0.02354 | 63.39% |
| target disagreement | 96 | 0.07394 | 0.03018 | 69.79% |

没有任何预注册关键 strata 出现“aggregate 改善、target 反向恶化”的结构。

## 10. Native roughness 仍只是 resolution-specific reference

原 native `-log(E5)` absolute difference median 约 **0.02166**，仍低于 erosion candidate 的 0.02809。

这不构成 v0.6.11 失败：冻结 protocol 的 decisive comparison 是 endpoint-robust candidate 与原始 **fine roughness**，因为 native roughness 在 v0.6.9 已证明是 resolution-specific measurement。v0.6.11 只回答“能否 materially 减少 fine property 的 endpoint sensitivity”，并不授权用 candidate 替代 native qualification。

未来若 candidate 进入真正 property POC，必须重新比较完整 slicing invariance、resolution semantics、deployability 和 qualification behavior。

## 11. 正式裁决

正式裁决：

> **`endpoint_erosion_ensemble_materially_reduces_roughness_interval_sensitivity`**

解释：

1. v0.6.10 的 fine-roughness instability 确实有强 endpoint/interval component；
2. 固定、单视图、向内、25-cell 的 erosion median 在四个 offsets 上一致显著降低 cross-slicer difference；
3. 改善没有通过丢样本获得；
4. common-support oracle 与 boundary-sliver diagnostics 提供独立机制支持；
5. candidate 仍只是 continuous-property structural candidate，不是 qualification rule，也尚未被 promoted 为 production morphology property。

## 12. 下一步

本轮正向结果只授权一个**单独冻结的 endpoint-robust roughness property POC**：验证 erosion-median roughness 在更完整的 representation invariance、prefix causality、resolution-response 与 downstream qualification audit 中是否保持结构优势。

Fine concentration/origin-ensemble 的 native-5m deployable proxy仍是另一个独立 workstream，不得与 roughness POC 混在同一轮。

在新的 POC 结果前，仍禁止：

- 拟合任何 path qualification threshold；
- 修改 matcher / projection / publication；
- 回到 direction/D1/D2/PAWCT；
- 使用 outcome/P&L；
- 进入第三浪、fresh OOS、paper trading 或 production。

当前全局状态仍为：

`morphology_replication_not_yet_accepted`
