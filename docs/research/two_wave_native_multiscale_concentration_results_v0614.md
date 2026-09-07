# v0.6.14 native multiscale/refinement-aware concentration：正式结果与云端裁决

日期：2026-09-07

状态：`native_multiscale_response_is_stable_but_not_informative_of_fine_refinement`

操作基线仍为 **v0.4.3**；全局状态仍为 `morphology_replication_not_yet_accepted`。本轮只审计 native-only deterministic coarsening response；没有修改 qualification、threshold、identity、matcher、projection、publication、roughness candidate、direction、outcome 或 trading logic。

## 1. 结果前冻结

- `docs/research/two_wave_native_multiscale_concentration_preanalysis_v0614.md`
- `docs/research/two_wave_native_multiscale_concentration_protocol_v0614.md`
- helper blob `cf3274a765e9b577841fe7fc468ca9d2aa8c7e8d`
- test blob `880a77dfa13c790917536c956c5b3ae5faea33b0`

Synthetic tests：**8/8 PASS**。

注册 native response：对每条 closed native-5m leg，固定 stride `1/2/3/4`，枚举各 stride 所有 phase，始终保留 published endpoints；对 `C_inf/C_1/C_2` 记录 phase median/range，并以 stride1 为基线输出 `delta_2/3/4`、`range_2/3/4`。没有 best stride / best phase / fitted score。

## 2. Hard controls 全部闭合

```text
published identities = 38,176 / 36,737 / 36,619 / 36,480 / 36,264
published raw strict pairs = 8,381 / 5,770 / 6,204 / 9,098 = 29,453
both-qualified = 482
qualification disagreements = 699
target repaired = 80 = 56 agreement + 24 disagreement
v0.6.13 native/fine profile availability = 664,001 / 737,070 / both 663,972
```

无 upstream behavioral drift。

## 3. Native coarsening response 对真实 native→fine gap 几乎没有正向信息

Aggregate Spearman，`abs(delta_s)` vs native→fine absolute profile gap：

```text
C_inf: stride2 -0.077 / stride3 -0.077 / stride4 -0.065
C_1:   stride2 -0.148 / stride3 -0.193 / stride4 -0.205
C_2:   stride2 -0.108 / stride3 -0.133 / stride4 -0.138
```

`phase_range_s` vs native→fine gap 同样弱：大多约 `-0.14 ... 0.00`。

更关键的是 `phase_range_s` vs supplied-1m five-origin range 也没有形成正向 tracking：

```text
C_inf: -0.145 / -0.168 / -0.200
C_1:   -0.105 / -0.143 / -0.176
C_2:   -0.123 / -0.153 / -0.187
```

所以“native path 对进一步抽稀有多敏感”不是“native bar 内隐藏了多少 fine refinement”的有效 proxy。

## 4. Native response 反而明显受 step count 调制

`abs(delta_s)` vs native step count Spearman：

```text
C_inf: 0.452 / 0.532 / 0.602
C_1:   0.287 / 0.326 / 0.352
C_2:   0.313 / 0.366 / 0.399
```

`range_s` vs step count 也约 `0.25 ... 0.50`。

`1-3` movement legs 的大部分 coarsening response median 直接为 0，因为 further-coarsening subpartitions退化为相同 endpoint path；随 leg 变长 response 才展开。这进一步表明 registered response 更像 native-duration/coarsening geometry，而非 hidden fine uncertainty。

## 5. Cross-slicer stability 确实有所改善

相对于 v0.6.13 native profile本身，所有四个 offsets、三个 components、全部 `delta/range` coordinates 的 median counterpart difference 都一致更低。

Aggregate例子：

```text
native C_inf profile median diff = 0.1659
C_inf delta/range medians         = 0.1140–0.1367 / 0.1153–0.1232

native C_1 profile median diff    = 0.0922
C_1 delta/range medians           = 0.0660–0.0731 / 0.0740–0.0857

native C_2 profile median diff    = 0.1293
C_2 delta/range medians           = 0.0904–0.1032 / 0.0990–0.1066
```

因此这套 response 是“较稳定的 native descriptor”，但稳定本身不等于它对 fine refinement 有信息。

## 6. Frozen strata 没有救回信息性

Both-qualified、qualification-disagreement、target repaired 与 target disagreement 中，native response 与真实 native→fine gap / fine-origin range 的 associations 仍然弱、符号混杂或为负。Target disagreement 中也没有出现一致的正向 uncertainty tracking。

所以不能根据某个关键 failure subset 把这套 response promoted。

## 7. 正式裁决

> **`native_multiscale_response_is_stable_but_not_informative_of_fine_refinement`**

解释：

1. deterministic native coarsening response 在 cross-slicer 上确实比 native profile scalar 更稳定；
2. 但 response magnitude / phase range 几乎不追踪实际 native→fine gap，也不追踪 supplied-1m origin uncertainty；
3. response 对 native step count 的依赖反而明显；
4. therefore further coarsening of already-coarse closes cannot recover information that was lost inside the bars；
5. v0.6.14 不允许 property promotion，也不允许基于这些 response 拟合 fine correction。

## 8. 下一步

本轮排除了“只靠 native close 的进一步 temporal subsampling”来估计 hidden refinement uncertainty。若继续 concentration workstream，下一步必须回到**native bar 内可观测的信息边界**：研究 OHLC/true-range/intrabar range 等是否能够给出对 hidden variation concentration 的结构性 bounds，而不是 point estimate；或者正式接受该 property 在仅有 native 5m close/OHLC 下不可识别，并重新评估 production data requirement。

任何下一版仍须 results-blind，且不得拟合 qualification threshold、duration correction或 outcome。

当前全局状态仍为：`morphology_replication_not_yet_accepted`。
