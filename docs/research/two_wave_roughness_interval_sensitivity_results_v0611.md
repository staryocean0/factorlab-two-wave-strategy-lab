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

全五视图 published legs = **737,104**。全量 single-view 25-cell erosion availability：

- 25/25 cells defined：**641,645** legs；
- 0/25 defined：仅 **19** legs；
- decisive pair-leg comparison 仍完整保留 **117,805** observations。

Undefined cells 的原因全部按冻结语义保留；零 TV / 零 displacement 显式 undefined，没有 epsilon 修补。

## 6. Exact decomposition 证实 endpoint displacement 是核心机制之一

原始 counterpart roughness 满足：`ΔR = ΔlogTV - ΔlogD`。

全量最大 identity error：**2.22e-15**。

## 7. Common-support oracle 支持 boundary-effect 解释，但不进入候选

对全部 **117,805** pair-legs，counterpart-dependent common-support interval 都可以定义。各 side 原始 fine roughness 到 common-support roughness的 absolute deviation median = **0.02648**。

Common-support 需要 counterpart information，因此严格保持 audit-only，不能成为 single-view recognizer input。

## 8. Boundary-sliver diagnostics

在全部 published legs 的可定义样本上，前后四分钟会移除非平凡 fine TV：

```text
left 4m removed-TV fraction median  = 0.1379
right 4m removed-TV fraction median = 0.1467
both 4m removed-TV fraction median  = 0.2703
```

因此一个名义 5m bar 内的 endpoint displacement 可以 materially 改变 TV/D，不是微小浮点效应。

## 9. Frozen strata 没有反转主结论

| stratum | pair-legs | original median | erosion median | candidate smaller fraction |
|---|---:|---:|---:|---:|
| both-qualified | 1,928 | 0.05244 | 0.02803 | 64.32% |
| qualification disagreement | 2,796 | 0.06341 | 0.03412 | 66.27% |
| target repaired | 320 | 0.06184 | 0.02564 | 65.31% |
| target agreement | 224 | 0.05828 | 0.02354 | 63.39% |
| target disagreement | 96 | 0.07394 | 0.03018 | 69.79% |

## 10. 正式裁决

> **`endpoint_erosion_ensemble_materially_reduces_roughness_interval_sensitivity`**

解释：v0.6.10 的 fine-roughness instability 确有强 endpoint/interval component；固定、单视图、向内、25-cell erosion median 在四个 offsets 上一致显著降低 cross-slicer difference；改善没有通过 decisive coverage shrinkage 获得；common-support oracle 仅用于机制支持。

## 11. 下一步

Roughness interval-sensitivity workstream 已得到 positive structural result。按 workstream 隔离规则，下一正式版本转到**独立的 fine concentration / origin-ensemble concentration native-5m deployable proxy + aliasing/error-bound preanalysis**。

仍禁止拟合任何 path qualification threshold、修改 matcher/projection/publication、使用 direction/outcome/P&L，或进入第三浪、fresh OOS、paper trading、production。

当前全局状态仍为：`morphology_replication_not_yet_accepted`。
