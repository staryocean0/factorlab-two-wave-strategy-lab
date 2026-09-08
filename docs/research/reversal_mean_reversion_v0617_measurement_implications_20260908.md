# v0.6.17 对广义反转 / 均值回归研究的测量含义

日期：2026-09-08

本文件不是新的策略结果，而是把 `CL-20260908-005` 已 cloud-reviewed 的 M0 测量结论翻译成后续策略研究必须遵守的规则。

## 1. 新得到的能力是什么

v0.6.17 没有证明“两浪形态有效”，也没有产生买卖方向。

它真正建立的是：

> **给定 native 5m bar 与 authoritative finer source support，可以因果地给细路径信息量/集中度构造 session-aware 的可行区间，并验证真实 fine path 落在区间内。**

这是一种 interval-valued measurement capability。

正式 cloud-reviewed verdict：

`session_aware_bounds_valid_but_structural_gap_nonidentifiability_is_material`

## 2. 为什么这对反转研究重要

广义反转研究经常会问：

- 一次急跌是顺滑的单向冲击，还是来回拉扯？
- 父级趋势的路径效率是否下降？
- 一段行情的能量是否集中在少数局部移动？
- lower-scale path 是否已经开始破坏 parent state？

这些问题都隐含一个前提：**细路径到底被我们观察到了多少。**

v0.6.17 证明 native 5m OHLC 并不总能唯一确定细路径。五个 slicer 中，offset1–4 存在真实 source rows 落在 native envelope 外；总计 `208,744 / 737,104 ≈ 28.3%` published legs 必须使用 universal partial-identification interval。

因此以后不能把一个从 5m OHLC 反推出来的“粗糙度/集中度点值”当成真实 fine path。

## 3. 后续只有三种合法测量方式

### A. 真实 finer source 已准入

若 DataHub 提供完整、可追溯、时间语义明确的 1m/更高频 source rows，可直接计算 path property。

但必须先完成：source identity、timestamp/session contract、缺失/重复台账、evidence role freeze。

### B. Native bar fully enveloped

可以使用 v0.6.17 已验收的 finite interval bounds。

策略研究应把该变量视为区间，而不是偷偷取 midpoint 当 ground truth。

### C. 存在 actual source gap

必须承认 partial identification。

允许：

- universal interval；
- 事前冻结的 partial-identification 方法。

禁止：

- 删除这些事件以提高结果；
- 将 gap rows 并入邻 bar；
- 用 oracle 事后收窄；
- 发明一个 concentration point proxy 代替区间。

## 4. 对 Round-1 的解释

Round-1 R1/R2/R3/R4 的结论不因此被改写。

尤其不能说：“以前失败是因为 measurement 不够好，所以现在都重跑。”

当前状态仍是：

- R1：unresolved，原因是独立 check 年度 resolved supply 不足；
- R2：adequate evidence 下关闭；
- R3：预注册方向被证伪；
- R4：三个统计状态均未提供增量；
- T1：2019 supply `48 < 50`，在 outcome 前关闭。

v0.6.17 只是给未来新研究增加更严格的 measurement language。

## 5. 对 R1 的特殊意义

R1 是当前唯一因 evidence supply 而 unresolved、不是 mechanism rejected 的主 lane。

当 materially new data 到来时，R1 应优先获得新的 results-blind budget；但不能把旧 2015–2020 结果拿来改参数。

新数据下的 R1 至少要做到：

1. 先冻结新的 BUILD / chronological check / holdout；
2. parent state 必须是当时可见的 causal state；
3. lower counter-shock 定义要在 outcome 前冻结；
4. 若用 fine-path property，必须明确属于 direct-source measurement、finite interval 还是 partial-identification interval；
5. 不允许用 structural-gap status 做后验 favorable filter；
6. 不能把历史 consumed period 重新叫 fresh。

## 6. 对数据工具的直接需求

未来统一数据更新中，对本仓最有价值的不只是“更多年份”，还有**真实 finer source completeness**。

优先希望得到：

- CSI1000 / CSI300 / CSI500 的完整 native 1m source；
- 明确 bar label / timezone / session semantics；
- missing / duplicate / unexpected clock ledger；
- source-level SHA / lineage；
- 若存在 3s 或更细 point observations，保留原始 observation identity，而不是只给重采样后的 OHLC。

这会直接降低 broad reversal research 对 interval-only inference 的依赖。

## 7. 当前研究边界

这个 measurement capability **不会自动重开新的策略 lane**。

当前仍禁止：

- 在同一 2015–2020 consumed window 自动制造更多指标；
- 重救 R2/R3/R4/T1；
- PnL 选择；
- fresh OOS 声称；
- paper trading / production。

下一次策略 outcome budget 等待：

- materially new data 完成 source/role admission；或
- 真正独立的新理论在结果前完成 preregistration。
