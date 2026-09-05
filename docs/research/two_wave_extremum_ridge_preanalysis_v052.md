# v0.5.2 前置研究：Extremum-Level Scale-Space Ridge / Persistence Skeleton

日期：2026-09-05

状态：`preanalysis_before_protocol_and_code`

操作基线：**v0.4.3**。本文件只做数学选型与金融需求映射，不建立新 recognizer，不修改资格/D1，不进入第三浪、收益、交易或生产。

## 1. 为什么必须从 v0.5.1 返到“feature identity”

v0.5.0 已证明 TCSS 作为因果多尺度表示成立：尺度增加时细 extrema 被系统吞掉，中尺度可以出现 case_00、2018、2019、2020 的目标父级结构。

v0.5.1 又证明：把“连续五 extrema 的 sliding candidate window”跨尺度连接后做 automatic scale selection，会失去父级成员身份。微 extrema 在尺度空间湮灭后，连续五点窗口自然滑向邻近成员，因此 candidate family 不是稳定的 scale-space feature。

金融需求要求的是：

> **同一父级尺度上真实存在的五个父级 extrema，构成两个相邻完整波。**

所以数学层下一步必须先回答：

> **“同一个 extremum”如何跨尺度保持身份、何时死亡、哪些细 extrema 被父层真正吸收？**

只有这个问题解决后，五点两浪 identity 才能稳定。

## 2. Scale-space 理论与本问题的直接对应

### 2.1 非创造/非增强 extrema 是父子层级的基础

一维 scale-space 的核心要求之一是随着尺度增大不创造新的局部 extrema / zero-crossings。Time-causal temporal scale-space 中，级联一阶递归核是满足 variation-diminishing / non-creation 要求的自然离散实现。

这与本项目金融语义高度一致：

- fine scale：允许多个子级摆动；
- coarse scale：子摆只能消失/合并，不能凭空新增；
- parent structure 应是 fine structure 的简化，而不是重新切割出的另一条路径。

参考：

- Lindeberg & Fagerström, *Scale-Space with Causal Time Direction* (ECCV 1996)
- Lindeberg, *Temporal Scale Selection in Time-Causal Scale Space*, JMIV 58, 57–101 (2017), DOI `10.1007/s10851-016-0691-3`

### 2.2 经典方法追踪的是 critical-point trajectories，不是窗口中心

Lindeberg 对 scale-space 中 critical points 的研究明确分析：

- local extrema 随 scale 的 trajectory；
- extrema 的 drift velocity；
- bifurcation；
- annihilation / merge / split / creation 等事件的分类。

`Scale-space primal sketch` 进一步把不同尺度的 extrema / critical points 显式 linking，构成跨尺度 feature trajectories，再依据其 scale life / extent 提取 stable scales 与 significant structures。

这与 v0.5.1 的失败形成直接对照：

- v0.5.1：先造五点 window，再用 window center 匹配；
- primal-sketch 思路：先给单个 extremum 建 trajectory identity，再由稳定 feature identity 组合更高层结构。

参考：

- Lindeberg, *Scale-Space Behaviour of Local Extrema and Blobs*, JMIV 1, 65–99 (1992), DOI `10.1007/BF00135225`
- Lindeberg & Eklundh, *On the computation of a scale-space primal sketch*, JVCIR 2(1), 55–78 (1991), DOI `10.1016/1047-3203(91)90035-E`
- Lindeberg, *Detecting Salient Blob-Like Image Structures and Their Scales with a Scale-Space Primal Sketch*, IJCV 11, 283–318 (1993), DOI `10.1007/BF01469346`
- Lindeberg, *Scale-Space Theory in Computer Vision*, chapter on primal sketch / deep structure / algorithm, Springer/Kluwer.

### 2.3 一维 topological persistence 是独立 oracle，但不能直接当生产事件

对 1-D function，topological persistence 可以把 local maxima/minima 配对并用 persistence 衡量 extrema 对扰动的稳定性；低-persistence extrema 可以系统简化。

它很适合验证金融直觉：

> 造成父级碎片化的微摆是否应被视为短寿命/低显著性结构，而父级 extrema 是否更稳定？

但标准 1-D persistence 通常可能使用整个定义域，属于 global quantity；因此本项目首轮只能作为 offline hierarchy oracle / sanity check，不能在未证明 prefix-native 前产生 production two-wave event。

参考：

- Zheng et al., *Topological Persistence on a Jordan Curve*, ICASSP 2012：1-D persistence 直接衡量 local extrema stability；
- Chung et al. 1-D min-max/persistence diagram 实现；
- persistent homology time-series applications 作为方法参照。

## 3. 推荐的生产主线：TCSS Extremum Trajectory Skeleton

### 3.1 原子单位

不再定义 candidate family 为五点窗口。

每一个已确认 TCSS extremum 建立：

- `extremum_node_id`
- scale level / sigma
- kind = high / low
- filtered occurrence index
- confirmation index
- value / signed curvature

相邻 scale 间只连接**同 kind 的单个 extrema**。

### 3.2 Ridge identity

同一条跨尺度 trajectory 使用 immutable `ridge_id`。

初步冻结原则应是：

1. adjacent scales only；
2. same phase only；
3. one-to-one；
4. temporal order preserving；
5. coarse node 只能连接到截至 coarse confirmation 已经 confirmed 的 fine node；
6. 不允许未来 coarse extrema 回头重新分配已经 confirmed 的 ridge membership；
7. unmatched fine extrema 允许在尺度维终止，表示被 coarse scale 吞掉；
8. 因一维 scale-space non-creation 性，coarse scale 不应出现没有 fine ancestor 的新 extrema；若出现，应作为实现/离散化异常审计，而不是悄悄建立新 root。

### 3.3 为什么单个 extrema matching 比 v0.5.1 更合理

当一个 fine child extremum 死亡时：

- 邻近 surviving extrema 仍保留原 ridge IDs；
- “连续五点”集合可以改变，但**已有 ridge identity 不变**；
- parent candidate 可以明确知道自己在 coarse scale 吞掉了哪些 child ridges。

这样可以阻止：

`[e1,e2,e3,e4,e5] -> [e1,e2,e5,e6,e7]`

被误记为同一个 family。

## 4. 五点两浪应定义为 Exact-Ridge Tuple，而不是 scale-local sliding window

在任一 scale level，按时间顺序取相邻五个 extrema nodes：

`r0 -> r1 -> r2 -> r3 -> r4`

其中 `r*` 是 ridge IDs，而不是该层临时五点位置。

一个结构 family 的 identity：

`tuple_id = stable_id([r0,r1,r2,r3,r4])`

只有当相同五个 ridges 在一个连续 scale interval 中：

- 都仍然 alive；
- 在该层仍是相邻 extrema；
- phase 交替；

该 exact tuple 才继续存活。

任何成员 ridge 死亡，或者中间出现/保留另一个 ridge 导致它们不再相邻，该 tuple lifetime 结束；**不得把邻近第六个 ridge 换进来续命。**

## 5. Structural scale：首选不再强迫“唯一 local derivative max”先行

v0.5.1 的另一个教训是：金融上我们真正要的是“自然父级结构”，而不一定要求每个结构先有一个唯一 scalar sigma。

更自然的对象是：

> **exact five-ridge tuple 的 scale lifetime / structural interval。**

候选结构可以保存：

- birth scale：五条 ridges 首次同时成为相邻五点的尺度；
- death scale：tuple 中 ridge 死亡或相邻性破坏的尺度；
- log-scale survival span；
- 每条 ridge 的 birth/death；
- tuple 内各 scale 的 common curvature response；
- 吞掉的 child ridge 数。

首轮 POC 应**全部输出 structural intervals，不先用 case 选唯一 representative sigma。**

如果后续 raw projection/qualification 必须绑定一个 representative scale，结果前可比较两个数学上自然、彼此独立的方案，但不能看真实 case 后再选：

A. `tuple_birth_scale`：child ridges 刚被吞掉、五 parent ridges 首次成为相邻的最细自然父级；

B. `tuple_internal_response_max`：只允许在 exact tuple lifetime 内，对冻结的 scale-normalized common response 取局部/全局最大；因为成员不再改变，v0.5.1 的 sliding-family 问题被消除。

预分析先验：**A 更适合作为首个单组件 production POC**，原因是它直接把 parent birth 定义为 topology/adjacency change，而不是再次引入 response optimization。B 可作为独立消融。

## 6. Parent birth 的金融解释

假设 fine scale 上有：

`P0 - c1 - c2 - P1 - c3 - P2 ...`

随着 scale 增大，`c*` child extrema 成对 annihilate，直到五个 parent ridges 首次成为连续相邻 extrema。

此时 parent birth 表示：

> **在不创造新结构的多尺度简化过程中，造成该父级两浪碎片化的子摆已经自然消失，而五个父级 turning structures 首次成为直接邻接。**

这比：

- “第一次周期达到12根”；
- “window center 最接近”；
- “case 看起来最漂亮的 sigma”；

更直接对应用户的金融需求。

## 7. Raw-price projection 仍是必须过的独立门

Ridge/TCSS extrema 本身仍发生在 causal smoothed signal 上；production contract 是 raw reversal。

因此首轮仍必须：

- 严格单调 raw price => 0 raw two-wave；
- 每个 parent ridge 必须投影到一个 actual raw high/low；
- 五个 raw anchors 必须严格时间有序、phase 交替、实际价格反转；
- projection 一旦在 tuple birth confirmation 时冻结，未来不得改写。

但 v0.5.2 应优先测试**ridge identity 是否解决结构滑移**；不在同一实验中重新设计 qualification / D1。

## 8. Causality / prefix-native 的关键风险

标准 primal-sketch / persistence 文献大多不是为金融 online event ledger 设计，因此本项目必须额外加：

1. scale linking 只能读当前时间以前已经 confirmed extrema；
2. ridge ID 一旦发布不得因未来 node 出现而重新分配；
3. death / annihilation 只有在 coarser scale 确认该 ancestor 不再存在时才能发布；
4. exact tuple birth 只有在五 ridges 的 adjacency 已经可确认时才能发布；
5. 25/50/75% prefix replay 对 ridge nodes、ridge IDs、death events、tuple IDs、raw projection 全字段一致；
6. offline persistence 只能用于对照，不得参与 production identity。

## 9. 结果前 synthetic hard gates

代码前协议至少需要冻结：

### R0 monotonic

严格上涨/下跌；所有 scale 0 complete raw two-wave。

### R1 clean single sine

单一周期：extremum ridges 应长寿、顺序保持；exact five-ridge tuple 应跨多个 scale level 保持同一成员。

### R2 parent + child sine

最关键：

- fine scale 有 parent + child extrema；
- child ridges 随尺度终止；
- parent ridges 保持 immutable IDs；
- child death 后 parent five-ridge tuple 首次成为相邻；
- tuple member IDs 不得滑移。

### R3 unequal amplitudes/frequencies

覆盖多个固定 amplitude/frequency ratios，验证不是只对一个合成比例成立。

### R4 chirp

允许 ridge temporal position/scale lifetime 平滑变化，不要求固定周期；不能因局部周期变化大面积换 identity。

### R5 jump + noise

滤波结构不能把一个 jump 变成稳定 parent five-ridge tuple；raw projection / raw jump gate 后续必须继续拒绝。

### R6 intermittent oscillation

ridge birth/death 与 oscillation on/off 对应；尾部 provisional 必须明确。

### R7 prefix replay

固定前缀扩展后，所有已经 confirmed 的 node/ridge/death/tuple/raw anchor 完全一致。

## 10. 真实数据硬门（不新增正例窗口）

继续只用已经冻结的观察面：

- case_00：v0.5.0 证明存在目标父层；检查 ridge birth 是否自然形成该父层，而不是用 case 选 scale；
- 2018-06-20：检查 v0.5.0 的中尺度规整父结构是否以 exact ridge tuple 进入候选层；
- 2019-04-15：防止再次跳到 sigma 8/11/22 的错误超粗 family；
- 2020-07-15：检查合理中尺度结构是否可进入候选层；
- case_02：90/3 假浪不得复活；
- case_11/14：不得发布跨数周巨型五点；
- case_10：只观察结构是否稳定，不修改 qualification/D1。

跨 offset：五个原生 5m 的发布边界 IoU 不得再次四项系统性低于 v0.4.3。

## 11. 与 tSSA / causal wavelet 的关系

当前不立即切换方法，原因是 v0.5.0 已经提供强正证据：**TCSS representation 能产生目标 parent coarse structure。**

因此再做一次“feature identity / deep structure”修复是有明确数学依据的，不是继续调参。

但设定明确止损：

> 若 extremum-ridge / exact-tuple 路线仍不能把 v0.5.0 已存在的父级结构稳定传入 production candidate layer，TCSS 路线停止继续深挖；下一步正式让 trailing SSA 与 causal wavelet/filter-bank 做独立竞争 POC。

## 12. 当前推荐

下一版应冻结为：

**v0.5.2 = TCSS extremum trajectory + exact-ridge tuple birth 单组件 POC**

不是 qualification v0.5.2。

首个 production POC 只验证：

`TCSS extrema nodes -> causal ridge IDs -> ridge death/annihilation -> exact five-ridge tuple birth -> frozen raw projection -> frozen v0.4.3 qualification/D1/ledger`

不要同时加入 persistence threshold、scale-response max、资格改造或 D1 改造。

只有这个单组件过关后，才重新激活资格层预分析。