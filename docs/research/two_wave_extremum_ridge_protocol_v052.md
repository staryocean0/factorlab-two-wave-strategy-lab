# v0.5.2 TCSS Extremum Trajectory / Exact-Ridge Tuple：结果前冻结协议

日期：2026-09-05

协议状态：`frozen_before_v052_results`

操作基线：**v0.4.3**。v0.5.0 TCSS 仅为表示层候选；v0.5.1 candidate-window characteristic selector 已正式否定。本协议只授权一个新的**层级关系组件**，不修改资格阈值、D1、第三浪、收益、交易或生产。

## 1. 唯一研究问题

> 能否在 v0.5.0 已通过的 time-causal scale-space 上，先给单个 extrema 建立严格因果、不可滑移的跨尺度 trajectory / ridge identity，再用 exact five-ridge tuple 的自然 birth 形成父级两浪，使 v0.5.0 已存在的父级粗结构稳定传入 raw-price candidate layer？

本轮不回答哪个结构赚钱，也不优化 D1/资格。

## 2. 结果前冻结的核心改变

v0.5.1：跨尺度原子 = five-extrema sliding candidate window。

v0.5.2：跨尺度原子 = **single confirmed extremum node**。

除此之外全部冻结：

- 14 层 TCSS scale lattice 不变；
- raw-price reversal financial semantics 不变；
- v0.4.3 qualification 数值/定义不变；
- D1 不变；
- non-overlap ledger 不变；
- 2015–2020 development views 不变；
- fixed cases/windows 不变；
- `12—48` 不参与 ridge linking / tuple birth。

## 3. Extremum node

每个 scale level 使用 v0.5.0 的同一 causal TCSS series 与 confirmed-extrema detector。

node 保存：

- `node_id = stable_id(scale_id, kind, occurrence, confirmation)`；
- level / sigma / scale_id；
- `kind` high/low；
- filtered occurrence index；
- confirmation index；
- filtered value；
- cumulative causal-kernel mean age（只作 matching correction / audit，不左移生产时间）。

## 4. Adjacent-scale ridge linking：结果前冻结

首轮实现不做 global Hungarian / dynamic programming，因为全序列全局匹配会让未来 coarse node 改写历史。

采用**streaming monotone same-phase greedy continuation**，但原子是单 extremum，而不是 candidate window：

对每一对 adjacent scale `j -> j+1`，high 与 low 分开：

1. coarse nodes 按 confirmation time、corrected occurrence time、node id 顺序处理；
2. 一个 coarse node 只能连接到：
   - same kind；
   - 已在该 coarse node confirmation 前 confirmed；
   - 尚未被该 coarse scale 其他 node 使用；
   - temporal order 不早于上一个已匹配 ancestor；
3. 候选 fine ancestors 用 corrected occurrence distance 排序；距离相同以 confirmation/node id 确定；
4. **不设置从真实 case 反推的任意 duration gate。** 首轮允许在可用 monotone ancestor 中取最近者；距离完整报告；
5. 如果 coarse extrema 数在任何 prefix/scale 出现 non-creation 违例导致无法给 coarse node 找到合法 ancestor，记录 `lineage_anomaly` 并令该相关 tuple 无生产资格，不创建“凭空 coarse root”；
6. fine node 未被 coarse node 继承，视为其 ridge 在该 adjacent-scale transition 终止；这只是 scale death，不等于交易事件。

### 4.1 Immutable ridge id

finest scale node 各自拥有 root ridge id。

coarse node 继承其 matched fine ancestor 的 ridge id。

一旦 node/ridge continuation confirmed，未来不得重分配。

## 5. 为什么不在首轮加入 persistence threshold

ridge survival levels / log-scale span 全部报告，但**不设最少生存层数阈值**。

理由：首轮唯一要检验的是 identity 与 topology/adjacency birth 是否能修复 v0.5.1 的 sliding-family 错误。若同时用 persistence threshold 筛选，会无法区分成功来自 identity 还是阈值。

标准 1-D topological persistence 只作 offline oracle，不参与 production output。

## 6. Exact five-ridge tuple

在每个 scale level，把该层已确认 extrema nodes 按 occurrence 排序；任意连续五个交替 nodes 构成一个 scale-local five tuple。

其结构 identity 不用 occurrence/window center，而用：

`tuple_id = stable_id([ridge0, ridge1, ridge2, ridge3, ridge4])`

同一 tuple_id 在相邻 scale level 再次出现时，表示**同一五条 ridge**仍同时 alive 且相邻。

禁止：

- 成员 ridge 死后用邻近 ridge 替换继续沿用 tuple_id；
- 只因中心接近就把不同 ridge tuple 合并；
- 看 case/D1/12—48/收益决定 tuple membership。

## 7. Tuple birth：首轮唯一 structural-scale 规则

首轮 production POC 使用：

**`exact_ridge_tuple_birth_scale`**

定义：同一个 exact five-ridge tuple 在 TCSS lattice 上**首次出现**的最细 level。

其金融解释：造成这五个 parent ridges 不相邻的 child ridges 已经在更细→当前 scale transitions 中自然死亡；此处是这五个 parent extrema 第一次成为直接邻接的自然层级。

不再计算 candidate-family local derivative maximum。

每个 tuple birth event 保存：

- tuple_id / five ridge ids；
- birth level / sigma；
- five birth-scale filtered extrema nodes；
- prior finer scale 中这些 ridges为何不构成相邻五点（若可审计）；
- child ridge deaths between tuple outer bounds since previous scale；
- tuple later survival levels（只作结果/诊断，不影响 birth event）。

### 7.1 重要：finest-scale tuple 不是“新父级 birth”

finest scale level 本来所有局部五点都天然相邻。为了避免把全部微五点都当“父级 birth”，production birth event 要求：

- `birth_level >= 1`；并且
- 在 `birth_level-1`，至少有一个额外 alive ridge 位于 birth tuple 的 outer ridges 之间，导致这五 ridge 不是连续五点；
- 从 finer 到 birth level 至少有一个内部 child ridge death。

所以 parent birth 必须由**真实的跨尺度简化事件**产生，而不是 finest local window。

## 8. Causality / confirmation clock

一个 tuple birth 只有在以下都已确认后才发布：

- birth level 五个 extrema nodes 已确认；
- 五条 ridge continuation 到 birth level 已确认；
- finer level 的内部 child ridges / adjacency 状态已确认；
- 所需 scale transition death 状态已可确定。

`birth_confirmation_bar = max(all required node confirmations)`。

不得把 filtered occurrence 或 kernel delay 左移成 known_at。

25/50/75% prefix replay 必须对已经 confirmed 的：

- node IDs；
- ridge IDs / continuation edges；
- ridge deaths；
- tuple IDs；
- tuple birth scale；
- tuple members；
- raw projection；
- qualification / ledger；

逐字段一致。

## 9. Raw-price projection：冻结 v0.5.1 口径作为对照

为了保持单组件归因，首轮继续使用 v0.5.1 已冻结的：

`sequential_raw_close_extreme_inside_filtered_phase_bounds`

但输入对象改为 tuple birth scale 的 exact five ridge nodes。

projection 仍必须：

- actual raw alternating turns；
- occurrence strict order；
- strict monotonic raw => 0；
- projection frozen at information time；
- invalid projection retained with reason。

如果 v0.5.2 在 ridge identity 上明显成功、raw projection 又成为主要独立失败源，raw projection 才能在下一单组件实验研究；本轮不混改。

## 10. 冻结 qualification / D1 / ledger

valid raw five points 直接调用 v0.4.3 `evaluate_pair` 与同配置：

- `min_leg=4`
- `min_cycle=12`
- `max_cycle=48`
- `max_pair=96`
- duration ratio 2
- amplitude ratio 2
- raw leg efficiency .5
- raw jump share .5
- raw flat share .5
- same delays / days / wall-span
- D1 unchanged

`12—48` 因此只是在自然 tuple birth 已生成后判目标时间尺度，不定义 parent hierarchy。

互斥发布继续按 causal confirmation 排序，不按 direction/fit/outcome 排名。

## 11. Synthetic hard gates（先于真实数据）

### S0 monotonic

strict up/down raw series：0 production tuple birth raw two-wave。

### S1 single sine

- ridges same-phase order stable；
- no unexplained coarse roots；
- exact tuple IDs across scales不滑移；
- clean single-scale sine 不要求产生大量 parent births；若没有 child deaths，允许 0 parent births。

### S2 parent + child sine

至少三组事前固定 frequency/amplitude ratios：

- fine scale parent + child extrema；
- child ridges die with scale；
- parent ridges keep same IDs；
- after internal child deaths, parent exact five-ridge tuple birth occurs；
- tuple member IDs correspond to the same parent ridges before/after birth；
- parent birth 不靠删空全部结构。

### S3 unequal / asymmetric nested waves

避免只对完美谐波比例成立。

### S4 chirp

允许 occurrence drift；ridge identity 必须保持大体连续，不因未来追加重写 confirmed history。

### S5 single jump + noise

不得生成通过 raw projection/qualification 的 parent two-wave。

### S6 intermittent oscillation

on/off 区间的 ridge death/provisional tail 明确；不能跨长空白随意连接。

### S7 prefix replay

full vs 25/50/75% prefix：confirmed node/ridge/death/tuple/raw/ledger exact equality。

## 12. 真实数据与验收面冻结

数据：仓库现有六视图，不新增 case，不重采样：

- `5m_offset_0..4`
- `1m_official`

固定审计：

- case_00
- case_02
- case_10
- case_11
- case_14
- 2018-06-20
- 2019-04-15
- 2020-07-15

### 12.1 晋级硬门

v0.5.2 只有在以下条件同时不出现明确反证时才可保留：

1. 18 次真实 prefix replay 全过；
2. ridge lineage anomaly 不得成为大规模正常现象；
3. selected / qualified parent tuples 必须比 v0.5.1 更实质地吸收 v0.4.3 微 extrema；重点看 median/p90 与 `with_absorbed_micro_pivots`，但不设事后优化阈值；
4. case_00 不允许继续仅得到 v0.5.1 那类滑动 `5/14/33/5` / `52/5/5/25` family；应能审计到 v0.5.0 中间尺度已存在的 parent ridge identity，是否过资格另行报告；
5. 2018 / 2019 不应再次因为 selector identity 跳到与 v0.5.0 中间尺度完全不同的粗 family；
6. case_02 的 90/3 不复活；
7. case_11/14 不发布跨数周巨型五点；
8. 五个 native 5m offset 发布 IoU 不得像 v0.5.1 一样四项系统性低于 v0.4.3；
9. 不以发布数量、覆盖、range 数或收益作为晋级理由。

如果结构 identity 明显改善但仍被 frozen qualification 拒绝，可以判为 `parent_identity_pass_qualification_pending`，然后才重新激活资格单组件实验。

如果 exact-ridge identity 仍不能把 v0.5.0 的 parent coarse structure稳定传入 candidate layer，则判 TCSS hierarchy route failed，停止继续深挖，转 tSSA / causal wavelet competitive POC。

## 13. 禁止项

- 不看 case 后加 matching gate；
- 不用 12/48 反推 ridge；
- 不用 v0.5.1 common response 选 birth scale；
- 不加 persistence cutoff；
- 不改 raw projection；
- 不改 qualification/D1；
- 不看收益/未来；
- 不合并 main；
- 不进入 H1/H2。

本协议必须先于任何 v0.5.2 真实结果。