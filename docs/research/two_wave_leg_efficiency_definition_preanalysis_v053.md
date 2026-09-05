# v0.5.3 前置方法研究：父级腿效率的尺度定义竞争协议

日期：2026-09-06

状态：`pre_protocol_definition_competition_frozen_no_qualification_change`

目的：在 v0.5.2 已通过 parent identity、且只读归因已把 `inefficient_leg` 识别为下一优先单组件之后，**先确定一个非同义反复、具有明确 hierarchy 语义的 path-efficiency 测量方法**。本轮不是 v0.5.3 recognizer 实验；不得改变资格、阈值、D1、ledger 或发布。

## 1. 为什么不能直接实现旧公式

现行 raw ER：

`ER_raw(a,b) = |x_b - x_a| / sum_{t=a+1..b}|x_t-x_{t-1}|`。

它的问题是父级 candidate 已由 TCSS hierarchy 吸收细级 oscillations，但 denominator 又在 raw bar 上把所有细级往返重新累计。

然而直接改成 birth-scale filtered extrema-to-extrema ER 也有相反问题：如果两个端点本来就是该尺度上相邻局部 extrema，则 filtered path 在两点间近似单调，`ER≈1` 很可能由 representation 定义本身保证，成为 tautology。

因此本轮必须在结果前冻结多个候选定义，并用**无收益、无标签、无案例调参**的结构诊断选择。

## 2. 冻结候选定义

所有定义：

- 使用 v0.5.2 已冻结的 exact-ridge tuple、birth level、ridge IDs 和 raw projection；
- 不允许重新选 scale；
- 使用同一 geometric sigma lattice；
- TCSS 仅由 prefix-causal recursive filters 计算；
- 数值门 `0.5` 只作为诊断对比，不改变任何正式 qualification。

### D0 — `raw_er`（现行对照）

使用 raw close，在 raw projected leg `[a_raw,b_raw]` 上计算现行 ER。

### D1 — `birth_scale_raw_interval_er`

取 record 已冻结的 `birth_scale_id` 对应 TCSS 序列 `L_j`，仍在 raw projected leg 时间区间 `[a_raw,b_raw]` 上计算：

`ER = |L_j(b_raw)-L_j(a_raw)| / TV(L_j[a_raw:b_raw])`。

这是旧 preanalysis 最接近的方案。必须检查 time-causal filter delay 是否造成 filtered displacement 与 raw leg direction 大量不一致，以及是否出现过度饱和。

### D2 — `prebirth_scale_raw_interval_er`

取固定相邻细层 `j-1`，仍在 raw projected leg 区间计算 ER。

这里 `j-1` 不是可调尺度：v0.5.2 的 tuple 正是在 `j-1 → j` transition 中，由 internal child ridge death 使同一五条 parent ridges 首次成为 consecutive tuple。因此 `j-1` 是 parent birth 前**最后仍包含被吸收 child structure 的尺度**。

### D3 — `prebirth_ridge_interval_er`（理论首选，仍需数据否证）

在 `j-1` 层找到 record 五条 parent ridge IDs 的实际 ancestor nodes，以相邻 parent ridge ancestor occurrence 作为每条腿的端点，在 `L_(j-1)` 上计算 ER。

这使：

- endpoint identity 仍由同一 parent ridges 决定；
- 区间内允许存在即将在 `j` 层死亡的 child ridges；
- ER 测量的是“父腿在 birth 前最后一个细层上还有多曲折”，而不是 raw micro-noise，也不是 birth 后已被定义成 monotone 的路径。

### D4 — `birth_ridge_interval_er`（tautology control）

在 birth level `j` 的五个 ridge nodes 之间计算 ER。它不是候选生产定义，只用来量化“在自身相邻 extrema 间 ER 接近 1”的同义反复程度。

## 3. 结果前诊断指标

对五个 native 5m offset 分别输出，并给 cross-view 汇总。

### 3.1 非 tautology

每种定义对 record-level `min_leg_er` 输出 quantiles，以及：

- `min_leg_er >= 0.99` 的 saturation fraction；
- 四条腿全部 `ER>=0.99` 的 fraction。

若一种定义在大多数 candidate 上机械接近 1，则淘汰。

### 3.2 raw financial direction consistency

每条腿比较：

`sign(filtered endpoint displacement)` vs `sign(raw endpoint displacement)`。

输出 disagreement fraction。一个尺度度量不能靠大量方向反转来“提高效率”。

对 D3 还要比较 parent ridge ancestor endpoint phase 与 raw projected leg direction；若方向一致性差，淘汰。

### 3.3 parent-like subset 的机制性改善

parent-like subset 固定为：v0.5.2 candidate 内 `v043_excess_local_pivots_beyond_five > 0`。

比较各定义相对 D0 的 `min_leg_er` delta，以及在固定诊断线 `0.5` 上：

- 全体 candidate pass fraction；
- parent-like subset pass fraction；
- 非 parent-like subset pass fraction。

希望看到 parent-like subset 获得更明显、可解释的改善，而不是所有对象无差别饱和。

### 3.4 当前 `inefficient_leg` single-failure subset

这是归因阶段最有辨识力的群体。统计每种定义下有多少对象的四腿效率全部越过 0.5。

该数字只证明“该定义会影响归因所识别的瓶颈”，**不是越大越好**；必须与非 tautology、方向一致性和安全语义联合判断。

### 3.5 preservation audit

对冻结 v0.5.2 已 qualified records，统计新定义在 0.5 下仍通过效率门的比例。若一个定义无机制地大量推翻已经合格的对象，应谨慎或淘汰。

## 4. 固定反例 / 窗口

只做诊断，不允许用于选择参数：

- case_00：重点看 +4 micro-pivot parent 的四腿 D0–D4；不要求它最终 qualified，因为 duration/jump 仍冻结失败；
- 2018-06-20、2019-04-15、2020-07-15；
- case_02：90/3 安全反例；
- case_11/14：巨型跨周安全反例。

## 5. 定义晋级原则

一个定义只有同时满足以下条件，才允许写入真正 v0.5.3 结果前协议：

1. 完全由 v0.5.2 已知 birth/ridge identity 决定，无结果后尺度选择；
2. prefix-causal；
3. 不在自身 extrema 定义下机械饱和；
4. raw direction disagreement 足够低且可解释；
5. 相对 raw ER 的改善明显集中在 parent-like / inefficient-single subset，而不是无差别放行；
6. 已 qualified 对象大体保留；
7. 不修改 raw jump/flat safety gates；
8. 不使用收益、D1、selected count 或 case 是否“变好看”作为选择依据。

若 D1/D2/D3 均不能满足这些门，则**不启动 v0.5.3**，而不是退回阈值放松。
