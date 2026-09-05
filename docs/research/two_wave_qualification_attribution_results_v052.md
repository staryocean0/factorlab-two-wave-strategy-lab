# v0.5.2 Qualification Failure Attribution：正式只读归因结果

日期：2026-09-06

状态：`qualification_single_component_identified_efficiency_definition_pending`

操作基线：**v0.4.3（不变）**。父级 representation / identity 候选层保留 v0.5.2。本文只做冻结 v0.5.2 candidate 的失败原因分解；没有修改阈值、公式、D1、ledger、ridge linking、tuple birth、raw projection 或任何交易输出。

## 1. 正式证据

- analysis script：`scripts/run_two_wave_v052_qualification_attribution.py`
- workflow：`.github/workflows/two-wave-v052-qualification-attribution.yml`
- formal run：`33977684181`，**success**
- artifact id：`9972882023`
- artifact SHA256：`c9050ddabb7154472abdc03b6b455aa10660328a33f8c936eadc6e176e1cc45e`
- full regression before attribution：**387 tests / 0 failures / 0 errors / 0 skipped**
- data and bounded-package validation：passed

归因口径：

1. 对 `5m_offset_0..4` 完整重建冻结 v0.5.2；
2. 对每个 rejected record 统计 reason frequency；
3. 更关键地统计 **single-reason failure**：若一个 record 的 rejection reasons 只有某一项，则“仅移除这一门”会精确新增一个 qualified record；
4. 同样对“已吸收额外 v0.4.3 micro pivots”的 parent-like subset 重复统计；
5. 固定窗口和 legacy cases 只做 audit，不参与组件选择。

## 2. 全体 candidate：efficiency 与 corresponding-leg duration 接近，但 efficiency 第一

五视图 single-reason totals：

| rejection gate | o0 | o1 | o2 | o3 | o4 | total |
|---|---:|---:|---:|---:|---:|---:|
| `inefficient_leg` | 355 | 338 | 309 | 331 | 346 | **1,679** |
| `corresponding_leg_duration_mismatch` | 309 | 315 | 300 | 315 | 328 | **1,567** |
| `jump_dominated_leg` | 150 | 154 | 161 | 148 | 155 | 768 |
| `confirmation_too_late` | 125 | 129 | 128 | 134 | 134 | 650 |
| `short_cycle` | 110 | 116 | 120 | 124 | 102 | 572 |
| `amplitude_mismatch` | 79 | 64 | 64 | 70 | 70 | 347 |
| `short_leg` | 38 | 46 | 41 | 39 | 29 | 193 |
| `long_cycle` | 6 | 6 | 4 | 4 | 6 | 26 |
| `wall_span_too_long` | 4 | 6 | 4 | 2 | 3 | 19 |

仅看全体 candidate，efficiency 与 duration 很接近，因此还不足以单独冻结下一轮。

## 3. 真正关键的 parent-like subset：efficiency 约为 duration 的两倍

“吸收了至少一个额外 v0.4.3 micro pivot”的 candidate 更贴近本项目的父级结构语义。在这个子集中，single-reason totals 为：

| rejection gate | o0 | o1 | o2 | o3 | o4 | total |
|---|---:|---:|---:|---:|---:|---:|
| `inefficient_leg` | 109 | 100 | 105 | 93 | 101 | **508** |
| `corresponding_leg_duration_mismatch` | 49 | 60 | 47 | 45 | 50 | **251** |
| `confirmation_too_late` | 24 | 27 | 27 | 32 | 28 | 138 |
| `jump_dominated_leg` | 12 | 1 | 14 | 6 | 12 | 45 |
| `amplitude_mismatch` | 8 | 2 | 6 | 9 | 9 | 34 |
| `long_cycle` | 2 | 4 | 2 | 2 | 3 | 13 |
| others | very small | | | | | |

结论非常稳定：

- 五个 offset **每一个**都是 `inefficient_leg` 第一；
- 合计 `508`，超过 duration `251` 的两倍；
- 因此 raw-bar path efficiency 是最有证据的下一单组件研究对象。

这不是“哪个阈值拒绝得多就放松哪个阈值”。这里筛的是**仅因这一维失败**的对象，并进一步限制到已经表现出父级微摆吸收的结构。

## 4. birth-level 分层：efficiency 问题在父级尺度明显增强

以 offset_0 为例，`inefficient_leg` single failures：

- level 3：21
- level 4：73
- level 5：115
- level 6：117
- level 7：26

对应 duration single failures：

- level 3：52
- level 4：116
- level 5：106
- level 6：23
- level 7：2

其余 offsets 呈同一模式：duration 更偏中等层级，raw efficiency 在 level 5–6 仍保持大量独立拒绝。

这与机制假说一致：结构尺度越粗，内部合法 child oscillations 越多；逐 bar raw-close 的总变差会越来越容易把这些 child oscillations 重新计入父腿“低效率”，从而抵消 v0.5.2 hierarchy 已完成的微摆吸收。

## 5. 固定 cases 证明不能用单一案例决定组件

case_00 的目标 parent candidate：

- raw `[48720,48749,48754,48768,48801]`
- birth sigma ≈ 4
- absorbed extra v0.4.3 pivots = 4
- reasons：`corresponding_leg_duration_mismatch + inefficient_leg + jump_dominated_leg`

因此 **任何单组件实验都不应以“让 case_00 通过”为成功条件**。即使下一轮正确修复 efficiency，case_00 仍应继续被其他冻结门拒绝，除非那些门以后分别通过独立实验。

固定窗口也说明近邻对象多为多重失败，不能从单一窗口的高频 reason 直接挑阈值。正式组件选择必须依赖上面的 cross-view single-failure evidence。

## 6. 下一组件已识别，但旧 same-scale ER 公式不能直接照搬

归因结论：**v0.5.3 应研究 leg efficiency 的尺度语义，不研究 duration，不降低 0.5。**

但旧 `two_wave_qualification_preanalysis_v052.md` 提出的简单公式仍需一轮定义预分析。原因：

- 如果直接在 birth-scale filtered series 的两个相邻 parent extrema 之间计算 `net displacement / total variation`，由于它们在该尺度上本身就是相邻局部极值，区间通常近似单调；
- 该 ER 会机械趋近 1，可能成为由 representation 自身保证的 tautological gate，而不再测量“父腿质量”。

因此在冻结 v0.5.3 协议前，必须只读比较至少三种定义：

1. **raw ER**：现行基线；
2. **birth-scale ER over raw leg interval**：旧预分析方案，需检查 causal filter delay / direction disagreement 和是否过度饱和；
3. **pre-birth-scale ER**：使用 `birth_level-1` 的 TCSS 序列测量父腿残余 tortuosity。该层是 exact tuple 在 child ridge death 发生前的最后细层，具有明确 hierarchy 语义，而不是结果后选择任意平滑尺度。

这轮 definition POC 仍不得改变资格、发布或任何阈值。只有一个定义同时满足：

- 非 tautological；
- 对 absorbed-parent subset 相对 raw ER 有机制性改善；
- 不把所有 candidate 无差别推向 1；
- 与 raw leg direction 保持高一致性；
- 已 qualified 对象不出现大规模无解释反转；
- 完全 prefix-causal；

才允许冻结成 v0.5.3 单组件协议。
