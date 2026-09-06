# v0.5.5 D1 父级震荡/趋势分类：主 5m 只读语义归因结果

日期：2026-09-06  
状态：`readonly_attribution_complete_next_component_envelope_translation`

冻结上游：**v0.5.2 TCSS exact-ridge parent identity + v0.5.4 full-cycle-scale qualification**。

本轮没有提出、训练或采用新的 D1 classifier；没有修改现有 label、threshold、qualification、ledger，也没有使用任何收益或未来结果。

## 1. 结果前协议与正式执行

协议：`docs/research/two_wave_d1_semantic_attribution_protocol_v055.md`

首个 workflow run `34008502863` 在真实 attribution 前被 synthetic 单元测试挡住。失败原因是测试构造了“所有 phase steps 都小、但手工 span=0.60”的代数不一致记录，却错误期待 `weak_mixed_migration`；诊断逻辑按协议将其归入 `large_migration_without_coherent_direction`。只修正测试期望，没有改诊断逻辑、D1 公式或阈值。

正式 run：

- commit：`a5d07b318cb1620c70005600fa86c3cd2dcb07fb`
- workflow run：`34008607545` — success
- artifact：`9981766256`
- SHA256：`019fc3365ff6ed1633ce734e2257949ba2c7979360ba50ae5d0b25b45e9cc95e`
- bounded package validation：通过
- full regression：通过
- read-only main-5m attribution：通过

## 2. 当前 D1 的真实主 5m 分布

`5m_offset_0`，v0.5.4：

- evaluated：38,049
- qualified：734
- selected：404

### qualified 734

- uptrend：187（25.48%）
- downtrend：172（23.43%）
- range：**4（0.54%）**
- uncertain：**371（50.54%）**

### selected 404

- uptrend：101（25.00%）
- downtrend：82（20.30%）
- range：**3（0.74%）**
- uncertain：**218（53.96%）**

这些比例不是准确率，也不用于要求类别均衡。

## 3. range 稀少不是 `span<=0.5` 造成的

冻结 D1 range 条件要求：

- `|s0|, |s1|, |s2| <= 0.15`
- phase spans `<=0.5`

但从定义可直接推出：

- 若 `|s0|,|s1|<=0.15`，同相位三点的最大 span 至多 `0.30`；
- 若 `|s2|<=0.15`，另一相位 span 至多 `0.15`。

所以在“全部 phase steps 小”的前提下，`span<=0.5` 是代数冗余门。

真实数据验证：

- qualified 中 `all_steps_small_records = 4`
- span-gate counterexamples = **0**
- selected 中 `all_steps_small_records = 3`
- span-gate counterexamples = **0**

因此不能通过调整 `0.5` span gate 来解释或修复 range 稀少。

真正限制 range 的是：**要求共享相位链的两个局部步骤 s0/s1 与另一 envelope 的 s2 三者都同时落在 ±0.15。**

## 4. uncertain 的主因不是“差一点到阈值”，而是结构冲突

qualified uncertain = 371：

| subtype | count |
|---|---:|
| same_phase_reversal_conflict | **243** |
| strong_net_with_opposed_phase | 40 |
| coherent_but_subthreshold | 36 |
| opposite_envelope_conflict | 18 |
| large_migration_without_coherent_direction | 17 |
| single_phase_dominant | 17 |

按语义大类：

- explicit geometry conflict：**318 / 371 = 85.7%**
- insufficient / weak direction evidence：53 / 371 = 14.3%

selected uncertain = 218：

- explicit geometry conflict：**192 / 218 = 88.1%**
- `same_phase_reversal_conflict`：**151 / 218 = 69.3%**

所以当前 D1 的主要问题不是大量对象恰好卡在 0.15 附近；而是它把真实存在的几何反号直接兜底为 uncertain。

qualified uncertain 到最近 `phase_tolerance=0.15` 边界的绝对距离：

- p10 0.0126
- p25 0.0389
- median 0.0821
- p75 0.1865
- p90 0.3876

存在边界附近对象，但不能解释主体。

## 5. 最大失败模式：`s0/s1` 局部反号

371 个 qualified uncertain 中，**243（65.5%）**属于：

`same_phase_reversal_conflict`

也就是共享相位链：

`P0 -> P2 -> P4`

的两个局部迁移 `s0=P2-P0`、`s1=P4-P2` 明确反号且都超过 0.15。

冻结 D1 把这视为无法判断父状态。

但 parent-level 金融语义真正关心的并不是“共享 envelope 的每一小段都必须同向”，而是两个完整波形组成的父级上下边界是否整体迁移。

## 6. whole-envelope diagnostic 暴露出 D1 的职责错位

定义只读、无新阈值：

低点起算：

- lower-envelope total drift = `net = s0+s1 = (P4-P0)/A`
- upper-envelope drift = `s2 = (P3-P1)/A`

高点起算对称交换 upper/lower。

仍用旧 `phase_tolerance=0.15` 仅作诊断：

- 两条 envelope 都 >0.15 -> coherent up translation
- 都 <-0.15 -> coherent down translation
- 两条绝对值都 <=0.15 -> low total envelope translation
- 其余 -> mixed envelope translation

在 **当前 D1=uncertain 的 371 个 qualified records** 中：

- 两条 envelope 已 coherent up/down：**185（49.9%）**
- 两条 envelope 总迁移都小：18
- 剩余 mixed：168

在 selected uncertain 218 中：

- coherent envelope up/down：**108（49.5%）**
- low total envelope translation：14
- mixed：96

特别对 `same_phase_reversal_conflict` 243：

- envelope coherent up：75
- envelope coherent down：61
- 两条 envelope 总迁移都小：18
- mixed：89

即 **136 / 243 = 56.0%** 的最大 uncertain 子类，在父级上下 envelope 的总迁移上其实已经明确同向；它们之所以 uncertain，仅因为共享 envelope 的中间锚点 `P2` 让 `s0/s1` 局部反号。

这说明当前 D1 把**局部 envelope path allocation / curvature**与**父级 envelope translation direction**混成了同一 hard vote。

## 7. 固定窗口只读审计

这些窗口不用于选阈值。

### 2018-06-20

唯一 qualified/selected：

- raw `[40397,40408,40421,40442,40450]`
- D1 = uncertain
- subtype = `strong_net_with_opposed_phase`
- `s0=-0.087, s1=1.711, s2=0.876`
- `net=1.625`
- whole-envelope diagnostic = coherent up translation

当前 D1 被很小的第一个局部反向 `s0=-0.087` 阻止，而两条父级 envelope 总迁移都明显向上。

### 2019-04-15

唯一 qualified/selected：

- raw `[49927,49934,49943,49961,49967]`
- D1 = uncertain
- subtype = `same_phase_reversal_conflict`
- `s0=-0.539, s1=2.345, s2=2.083`
- `net=1.806`
- whole-envelope diagnostic = coherent up translation

局部共享-envelope path 先下后大幅上，但两个完整波组成的上下 envelope 总体都向上。

### 2020-07-15

两个 qualified：

1. `[64511,64517,64532,64543,64549]`：uncertain / single-phase-dominant，whole-envelope mixed；
2. `[64581,64605,64611,64642,64654]`：downtrend，whole-envelope coherent down。

说明 whole-envelope diagnostic 并不是简单把所有 uncertain 强制改成 trend。

### legacy case_10 stable-range 区间

当前 v0.5.4 在该宽 overlap 区间存在一个 qualified/selected uncertain：

- raw `[8691,8699,8709,8716,8724]`
- `s0=0.208, s1=-0.624, s2=-0.652`
- `net=-0.415`

它只覆盖 legacy target 的前段，并不是旧五点 `[8691,8699,8724,8739,8751]` 本身，因此不能拿 legacy case 名称直接给这个新 candidate 贴真值标签。该案例继续只作审计，不用于否定或接受新公式。

## 8. 归因结论

v0.5.5 不产生新 classifier，因此没有“模型通过/失败”。它完成了下一单组件的根因定位：

> **当前 D1 的首要职责错位，是把共享 envelope 的局部路径 `s0/s1` 一致性当成 parent trend direction 的必要条件。**

而对于两个已经确认的完整同尺度 raw-price reversal cycles，父级趋势/震荡的第一性几何对象更应该是：

> **upper-envelope total translation 与 lower-envelope total translation。**

`s0/s1` 的局部反号仍然是重要 morphology diagnostic，可表示 curvature、phase allocation、内部回返或非平稳性，但不应在未经证明时直接拥有 parent direction 的否决权。

## 9. 下一步允许冻结的单组件

下一轮应做 **whole-envelope translation D1** 的金融/数学 fit 预分析，优先保持旧归一化单位和 `phase_tolerance=0.15`，不搜索新数值。

最小候选形式：

- `E_upper` / `E_lower` 使用完整 parent window 的两条 envelope 总迁移；
- 两条同向明确迁移 -> trend；
- 两条总迁移都小 -> range；
- 一上一下 / 一条明确另一条未明确 -> uncertain；
- `s0/s1` reversal 从 parent-direction hard veto 降为 morphology diagnostic。

但这还不是冻结协议。必须先单独写 preanalysis，检查：

1. 为什么两条 envelope 是 parent state 的自然状态变量；
2. 是否需要 slope/time normalization 而不是只看 endpoint displacement；
3. 如何避免把一次巨大局部 envelope excursion 后回归原位误判为稳定 range；
4. low-start/high-start 完全对称；
5. 不使用 label balance 或未来收益选阈值。

完成 preanalysis 后才能冻结 v0.5.6 单组件协议和 main-5m mechanism audit。
