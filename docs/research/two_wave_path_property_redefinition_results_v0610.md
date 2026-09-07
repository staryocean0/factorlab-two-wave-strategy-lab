# v0.6.10 threshold-free path-property redefinition：正式结果与云端裁决

日期：2026-09-07

状态：`origin_ensemble_reduces_origin_aliasing_but_fine_property_remains_interval_sensitive`

操作基线仍为 **v0.4.3**；全局状态仍为 `morphology_replication_not_yet_accepted`。本轮没有修改 qualification、threshold、identity、matcher、projection、publication、direction、outcome 或 trading logic。

## 1. 结果前冻结

- `docs/research/two_wave_path_property_redefinition_preanalysis_v0610.md`
- `docs/research/two_wave_path_property_redefinition_protocol_v0610.md`
- helper blob `a1c3bcf5e3c51d30729bb333c0ea31a38cf0d834`
- test blob `ca4d8bf0f2f281a68bd11fa2e815596a5a6af8d2`

Synthetic tests：**9/9 PASS**。

## 2. Hard controls 全部闭合

Tuple births：`38,636 / 37,176 / 37,062 / 36,937 / 36,689`。

v0.6.5 publications：`38,176 / 36,737 / 36,619 / 36,480 / 36,264`。

Filtered mutual-unique pairs：`14,784 / 12,725 / 13,412 / 16,108`。

Published raw strict pairs：`8,381 / 5,770 / 6,204 / 9,098 = 29,453`。

v0.6.6 qualification matrix 再次精确复现：

```text
both-qualified                  482
both-rejected                28,272
main-qualified/other-rejected   352
main-rejected/other-qualified   347
```

v0.6.1 target repaired：`28 / 20 / 12 / 20 = 80`，其中 disagreement `10 / 7 / 3 / 4 = 24`。

## 3. 执行证据

当前 Chat runtime 在本轮开始时发生过容器重置。数据仍来自用户已上传 main ZIP；五个 native-5m parquet 与 `1m_official` 的 SHA256 继续与冻结 manifest 一致。当前 runtime 无 pyarrow，因此用只读 Parquet Thrift/page decoder + system `libzstd` 读取 timestamp/close；没有 resampling、fill 或 interpolation。

五-origin ensemble 用 Numba O(n) 状态机加速；在 100 条随机真实腿上与冻结 Python helper 逐字段 **100/100 exact-equivalence PASS，max error=0**。

Published legs 共 **737,104**，descriptor 可用 **737,070**，仅 **34** 条因 exact supplied-1m endpoint 不完整而 unavailable。

两条代数 identity 的全量最大绝对误差均小于 `9e-16`，远低于只用于浮点 assertion 的 `1e-12`。

## 4. Fine concentration 明显优于 native jump 的 cross-slicer 稳定性

在 29,453 strict pairs 的对应四腿上，共有 117,805 个可比较 pair-leg observations。

Native `J5` absolute difference：median **0.053931**，p90 **0.220604**。

`fine_concentration = J1`：median **0.006474**，p90 **0.059680**。

逐 pair-leg 比较：descriptor 更小 **101,853/117,805 = 86.46%**；更大 15,948。四个 offsets 方向一致。

因此底层 fine-path variation concentration 是一个明显比 native-origin J5 更稳定的连续属性坐标。该结论不等于可以立刻把它变成 hard gate。

## 5. Origin ensemble 进一步证明 bar-origin aliasing 可被显式表示

`origin_jump_median` cross-slicer absolute difference：median **0.016958**、p90 **0.094801**，均明显低于 native J5 的 0.053931 / 0.220604。

逐 pair-leg 中，origin median 比 native J5 更稳定 **92,066/117,805 = 78.15%**。

Origin uncertainty 不是无意义噪声：

- `origin_log_tv_ratio_range` 与 native-origin 对 ensemble TV median 的绝对偏离 Spearman = **0.617**；
- `origin_jump_range` 与 native J5 对 origin-jump median 的绝对偏离 Spearman = **0.582**。

所以 origin range 可以作为 sampling-origin uncertainty descriptor，而不是事后挑一个最有利 origin。

## 6. Fine roughness 没有通过 cross-slicer promotion

Native `-log(E5)` absolute difference：median **0.021658**，p90 **0.181079**。

`fine_roughness = log(TV1/D)`：median **0.083145**，p90 **0.392796**。

逐 pair-leg 中 fine roughness 更大 **75,389/117,805 = 63.99%**。四个 offsets 都表现为同一方向。

因此共享 1m lattice 虽消除了 sampling-resolution 混淆，但 strict same-event pair 的 published raw leg endpoints 仍允许数分钟级错位，fine TV/D 会对 interval endpoints 敏感。**不能把 fine roughness 直接 promoted 成 invariant morphology property。**

## 7. 组件冗余与互补

Aggregate Spearman：

```text
fine_roughness vs hidden_variation          0.730
origin TV median vs hidden_variation         0.853
fine_concentration vs origin jump median    0.892
hidden_variation vs max_step_refinement     0.580
origin TV range vs origin jump range         0.090
```

短腿 `1-3 bars` 中 fine roughness 与 hidden variation 相关高达约 0.976，而 `24+` bars 降至约 0.370；说明 roughness 的 interval/resolution decomposition 随腿长度改变。Origin spread 两维之间相关很低，保留了不同的 uncertainty 信息。

## 8. Frozen strata 没有推翻主结论

- 482 both-qualified pairs：fine concentration / origin-jump 差异仍小；
- 699 qualification disagreements：同样如此；
- 80 target repaired（56 agreement / 24 disagreement）没有出现反向的 concentration instability；
- 但 fine roughness 在 target repaired 总体并未系统优于 native roughness。

因此不能根据某个 failure stratum 特调 descriptor，也不需要改变 same-event matcher。

## 9. 正式裁决

> **`origin_ensemble_reduces_origin_aliasing_but_fine_property_remains_interval_sensitive`**

解释：

1. roughness / hidden variation / concentration / max-step 的代数分解是结构上自洽的；
2. fine concentration 明显降低 native J5 的 bar-origin sensitivity；
3. origin ensemble median 也稳定改善，range 能显式表征 origin uncertainty；
4. 但 fine roughness 对双方 published leg interval 的轻微 endpoint 错位仍 materially sensitive；
5. 因此 v0.6.10 不允许 property promotion，更不允许直接开新的 qualification threshold。

## 10. 下一步

只允许另开结果前的 **interval-sensitivity / deployable-proxy preanalysis**。优先分成两个问题：

- 为什么 fine roughness 对 <=5m endpoint displacement 敏感，以及是否存在不改 financial identity 的 common-support / endpoint-robust roughness representation；
- 如何把已经较稳定的 fine concentration / origin-ensemble concentration 转化为 native-5m 可部署、因果、具有明确 aliasing/error-bound 的 proxy。

这两项仍是 continuous-property research；不得在下一轮直接拟合 qualification threshold。Duration-geometry 保持独立 secondary workstream。

Direction/D1/D2/PAWCT、第三浪、收益/P&L、fresh OOS、paper trading 和 production 继续冻结。
