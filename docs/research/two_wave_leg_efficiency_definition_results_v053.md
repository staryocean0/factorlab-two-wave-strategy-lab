# v0.5.3 前置：父级腿效率定义竞争 POC 正式结果

日期：2026-09-06

状态：`all_scale_aligned_er_definitions_rejected_no_v053_protocol_yet`

操作基线：**v0.4.3（不变）**。父级 candidate identity 仍保留 v0.5.2 exact-ridge tuple birth。本轮完全只读，不改变 qualification、阈值、D1、ledger、发布或交易。

## 1. 正式证据

- protocol：`docs/research/two_wave_leg_efficiency_definition_preanalysis_v053.md`
- script：`scripts/run_two_wave_leg_efficiency_definition_poc_v053.py`
- workflow：`.github/workflows/two-wave-leg-efficiency-definition-poc-v053.yml`
- formal run：`33978345965`，**success**
- artifact id：`9973069689`
- artifact SHA256：`eb85c1d5d766da0b71723f864ce61d6f1c2ff34cd9eb63f1bde323631cad0c97`
- full regression：**387 / 0 failures / 0 errors / 0 skipped**
- bounded package / frozen data validation：passed

## 2. 五个冻结定义

- D0 `raw_er`：现行 raw-close ER，对照。
- D1 `birth_scale_raw_interval_er`：birth TCSS 序列，raw projected 时间区间。
- D2 `prebirth_scale_raw_interval_er`：birth 前一层 TCSS，raw projected 时间区间。
- D3 `prebirth_ridge_interval_er`：birth 前一层 TCSS，同一 parent ridge ancestors 之间。
- D4 `birth_ridge_interval_er`：birth TCSS，同一 parent ridge nodes 之间；预先声明为 tautology control。

固定诊断线仍为 0.5；没有为任何定义重新调阈值。

## 3. 跨五个 native 5m 的核心结果

以下为五视图平均比例（各 offset 方向一致）：

| definition | record 全四腿 ER>=.99 | 单腿 ER>=.99 | raw 方向错配 | parent-like 过 0.5 | non-parent 过 0.5 | inefficient-only 被解除 | 现有 qualified 保留 |
|---|---:|---:|---:|---:|---:|---:|---:|
| D0 raw | 0.90% | 41.25% | 0% | 10.94% | 83.25% | 0% | 100% |
| D1 birth/raw interval | 7.75% | 38.60% | **21.02%** | 27.64% | 48.54% | 19.86% | **29.43%** |
| D2 prebirth/raw interval | 2.36% | 36.56% | **10.96%** | 24.30% | 62.60% | 24.08% | **51.61%** |
| D3 prebirth/ridge interval | 12.57% | **73.70%** | 0% | **99.97%** | **99.89%** | **99.88%** | 100% |
| D4 birth/ridge interval | **100%** | **100%** | 0% | 100% | 100% | 100% | 100% |

## 4. D4：完全同义反复，正式淘汰

D4 在五个 offset 上：

- 所有 record 的四腿全部 `ER=1`；
- parent / non-parent / inefficient-only / already-qualified 全部 100% 通过。

这验证了结果前预警：在 birth-scale 的相邻 parent extrema 之间测同尺度路径效率，本质上由 extrema 定义自身保证，不能再作为独立腿质量门。

**D4 reject。**

## 5. D3：理论语义好，但实证退化为近常量，正式淘汰

D3 使用 birth 前一层，理论上保留 child ridges，并且有两个优点：

- raw direction disagreement = 0；
- already-qualified preservation = 100%。

但真正判别力几乎消失：

- 全体 candidate `min_leg_er>=0.5` 平均 **99.90%**；
- parent-like **99.97%**；
- non-parent **99.89%**；
- `inefficient_leg` single-failure **99.88%** 被解除；
- 单腿 `ER>=.99` 高达 **73.70%**。

主 5m 的 min-leg ER 中位数约 `0.953`。

这不是选择性修复 raw ER 的尺度错配，而是几乎取消了这一维的判别能力。

**D3 reject。**

## 6. D1 / D2：time-causal filtered endpoint 与 raw financial leg 不一致，正式淘汰

D1、D2 仍在 raw projected 时间区间测 filtered path，希望避免 extrema-to-extrema tautology，但产生明显 causal-filter delay / phase mismatch：

- D1 raw direction disagreement ≈ **21%**；
- D2 ≈ **11%**；
- D1 仅保留约 **29%** 的现有 qualified；
- D2 仅保留约 **52%**。

更重要的是，它们并没有呈现“parent-like selective improvement”：

- D1 parent-like 的 min-ER 相对 raw 中位变化约 **-0.017**；
- D2 约 **-0.038**；
- D2 对 non-parent 反而有轻微正向中位变化（约 +0.014）。

因此它们既破坏 raw-price 父腿方向语义，也不能解释 attribution 中父级 candidate 的 raw-efficiency 瓶颈。

**D1 / D2 reject。**

## 7. case_00 固定审计

目标 parent：

- raw `[48720,48749,48754,48768,48801]`
- birth level 6 / sigma 4
- absorbed extra v0.4.3 pivots = 4
- frozen reasons：duration mismatch + inefficient leg + jump dominated

四腿 ER：

- D0 raw：`[0.471, 0.984, 0.696, 0.469]`
- D1：`[0.406, 0.695, 0.485, 0.634]`，2 腿 raw-direction disagreement
- D2：`[0.476, 0.353, 0.190, 0.786]`，1 腿 direction disagreement
- D3：`[0.993, 1, 1, 1]`
- D4：`[1,1,1,1]`

case_00 很好地展示了两端失败模式：raw ER 把合法 child oscillation 累计进父腿；而 ridge-level ER 又几乎被 parent-extrema 定义保证为 1。

本轮不以 case_00 是否越过 0.5 选择定义。

## 8. 数学解释

Time-causal scale-space 的核心公理之一是从细到粗**不创造新的局部极值/零交叉**，粗尺度是细尺度的结构简化。参考 Tony Lindeberg / Lindeberg & Fagerström 的 time-causal scale-space 理论，以及基于 Schoenberg variation-diminishing kernels 的相关结果。

因此，一旦 v0.5.2 已用 ridge survival / child-ridge death 定义 parent extrema，若再在同一或邻近 coarse representation 的 surviving parent extrema 之间用 straightness/ER 做硬门，很容易把“parent leg 是该尺度的单方向段”重复编码一次。D3/D4 的近饱和正是这一理论问题在本项目数据上的直接证据。

## 9. 正式判定

本轮结论不是“选 D3”。而是：

**D1–D4 全部不晋级。当前不冻结真正 v0.5.3 same-scale ER 实现。**

同时，结合上一轮 qualification attribution，出现了一个更基础的结构性假说：

> `inefficient_leg` 在 v0.4.x 没有层级 parent representation 时，是防止 raw five-pivot leg 内部过度曲折的代理门；在 v0.5.2 exact-ridge hierarchy 已经定义 parent leg 后，这个 raw ER 门可能已经成为尺度错配的遗留重复约束，而不是应该寻找另一个平滑 ER 来替换。

因此下一步不是调 0.5，也不是再从 D1–D4 中选一个，而是做**legacy raw-ER redundancy ablation**：只移除 `inefficient_leg`，其它所有资格、安全门、D1、identity、ledger 完全不动，检查它是否真正改善 parent-like morphology，还是造成噪声泛滥和 offset 稳定性退化。

该 ablation 必须先作为结果前冻结的 POC；通过前操作基线仍为 v0.4.3，v0.5.2 仍只保留为 parent-identity representation。
