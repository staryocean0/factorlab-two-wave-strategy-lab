# 广义反转与均值回归研究白皮书 v2

日期：2026-09-08  
项目：`broad_reversal_mean_reversion_discovery_program_v1`

## 1. 本仓库现在研究什么

本仓库不是“某一个两浪策略仓”，也不是“开盘跳空回补仓”。

仓库级任务是：

> **建立广义反转 / 均值回归的方向发现框架：用因果多尺度状态判断一次偏离更像暂时波动，还是父级状态本身已经改变；用小预算同时筛多个机制，强的交给专门身份，弱的及时关闭。**

所谓“均值”不一定是一条均线。它可以是：

- 价格中心或区间；
- 趋势通道；
- 已完成波浪形成的父级结构；
- 某个状态下的正常轨迹；
- 多资产正常相对关系；
- 某个统计属性的正常区域。

所有策略问题最终都归结为：

1. 当前研究尺度是什么？
2. 父级状态是什么？
3. 当前偏离的对象是什么？
4. 什么算恢复，什么算父状态失败？

## 2. M0 两浪体系的角色

历史 `v0.4.3 -> v0.6.17` 两浪研究全部保留，但统一归为：

`M0_two_wave_structure_measurement_foundation`

M0 的职责是提供：

- 因果拐点和完整波；
- 多尺度表示；
- 两个完整波形成的 parent structure；
- drift / overlap / width / efficiency / roughness / duration / density；
- publication time；
- streaming/replay/prefix 不被未来改写；
- session/source information-set 语义。

M0 是**测量语言**，不是交易方向。

全局 morphology 仍为：

`morphology_replication_not_yet_accepted`

操作基线仍为 `v0.4.3`。

## 3. v0.6.17 已经闭合，但闭合的是“可识别性”

`CL-20260908-005` 已完成本地 formal replay 并通过云端独立复核。

Cloud-reviewed verdict：

`session_aware_bounds_valid_but_structural_gap_nonidentifiability_is_material`

关键结果：

- authoritative 1m source rows = `349,923`；
- 五个 native 5m views label/OHLC exact replay；
- published legs = `737,104`；
- registered N mismatch = `0`；
- J / C_inf / C_1 / C_2 oracle coverage = `100%`；
- fully enveloped legs = `528,360`；
- actual structural-gap legs = `208,744`，约 `28.3%`。

因此 v0.6.17 被接受为：

`interval_valued_session_aware_path_information_bounds`

它没有证明 morphology 正确，也没有给出第三浪方向。

真正的新规则是：

> **native 5m OHLC 不能被默认当成已经知道 fine path。**

以后用路径效率、粗糙度、集中度等变量时，必须明确它属于：

- 真实 finer-source 直接观测；
- fully-enveloped 情况下的有限区间；
- structural-gap 情况下的 partial-identification / universal interval。

禁止把区间偷偷压成一个伪精确点值。

云端 review：

`docs/research/two_wave_session_aware_information_set_bounds_cloud_review_20260908.md`

测量能力 admission：

`docs/governance/reversal_mean_reversion_v0617_measurement_capability_admission_v1.json`

## 4. Round-1：四类机制的结果

共同 evidence roles 在结果前冻结：

- BUILD：2015–2018；
- chronological check：2019、2020；
- 全部是 consumed development / not fresh；
- post-2020 未打开。

最终总裁决：

`BROAD_RMR_STAGE1_ROUND1_CLOSED_NO_PROMOTED_MECHANISM`

### R1 — 趋势中的跨尺度回撤

核心问题：父级趋势尚完整时，突然的反向冲击是不是低级别回撤？

最终状态：

`unresolved_evidence_insufficient_after_one_results_blind_measurement_revision`

一次结果盲 measurement revision 后，trigger supply 足够，但 resolved first-passage 只有：

- BUILD `168`；
- 2019 `40`；
- 2020 `39`。

冻结门槛要求 check 每年 >=50，因此 R1 **没有被证伪，也没有通过**。

这是目前最值得在 materially new data 到来后优先重检的方向。

### R2 — 震荡边界 / 假突破回归

供给充分：`657 / 161 / 151`。

加入 parent range state 后，pooled Brier / log-loss 和 2019、2020 都变差。

结论：当前低容量 R2 identity 关闭。

### R3 — 结构衰竭 / 状态切换

供给充分：`744 / 172 / 144`。

预注册要求 deterioration 越大，parent failure risk 越高；实际两个核心系数均为负。

结论：预注册方向被证伪，R3 v1 关闭。

### R4 — 统计状态极端

测试：

- path inefficiency；
- lower-scale event density；
- parent amplitude extremity。

三者供给都足够，但全部让 common geometry baseline 变差。

结论：R4 关闭。

Round-1 最重要的项目级结论之一：

> **统计属性自身的持续、极端或均值回归，不等于价格存在均值回归 alpha。**

## 5. Round-2 T1：独立理论方向在 outcome 前关闭

T1：

`T1_transitory_component_after_extreme_intraday_shock_v1`

它来自独立文献问题：极端价格冲击可能包含暂时性价格压力，也可能是信息冲击；不能预设“大波动一定反转”。

当前数据没有可靠 volume/order book/news，因此 T1 只允许研究 completed 5m shock 内部已经观察到的：

`within_bar_retrace_fraction`

结果前冻结：

- past-only 960 native 5m bars；
- median + 1.4826 MAD；
- extreme threshold = 5 robust sigma；
- exact 5×1m event-bar support；
- supply minimum = BUILD 150 / 2019 50 / 2020 50。

本地 supply audit 经云端复核：

- BUILD aligned = `364`；
- 2019 aligned = `48`；
- 2020 aligned = `87`。

因为 `48 < 50`，所以：

`T1_current_data_event_supply_insufficient / CLOSED_BEFORE_OUTCOME`

没有读取 post-event reversal/continuation outcome，也不能通过降低 5σ 或改 960 来救。

Cloud review：

`docs/research/reversal_mean_reversion_T1_supply_cloud_review_20260908.md`

## 6. 当前科学地图

现在不是“没有方向”，而是方向的证据身份已经分清：

- **R1：unresolved** —— 新数据来后优先复核；
- **R2：closed**；
- **R3：closed**；
- **R4：closed**；
- **T1：当前 identity 在 outcome 前因供给不足 closed**；
- relative-value / overnight：兄弟专题，不控制本仓主线；
- M0：继续作为测量底座，v0.6.17 interval capability 已 cloud-reviewed，但 morphology 未 accepted。

## 7. 下一轮研究怎样启动

本仓现在暂停在同一 2015–2020 consumed window 上继续自动发明指标。

新的 outcome budget 只有三个入口：

### A. Materially new data

新数据到来后，必须先：

1. source/provenance 验证；
2. timestamp/session semantics 验证；
3. missing/duplicate/unexpected ledger；
4. 在 outcome 前冻结新的 BUILD / check / holdout；
5. 声明 fine-path variable 是 direct measurement 还是 interval-valued measurement。

随后优先重检 R1，因为 R1 是 unresolved 而不是 rejected。

### B. 真正独立的新理论

必须先写理论、机制方向、变量、失败条件、候选预算，再看 outcome。

不能把 R2/R3/R4/T1 换名字重新跑。

### C. 新的 M0 测量对象

只有当 M0 产生一个实质新的、被接受的 causal measurement object，才可以先修改 program charter，再给新的 broad lane 一个 results-blind 小预算。

## 8. 研究节奏

继续坚持：

**多个方向浅测 > 一个方向无限优化。**

一条线只能有小候选预算。失败必须保留；样本不足必须写 unresolved；供给门失败不能降门槛；结果方向错了不能事后改故事。

一个方向真正值得深入时，应毕业给 dedicated specialist identity，而不是让 broad repo 自己变成单策略优化仓。

## 9. 当前禁止项

仍然禁止：

- fresh-OOS 虚假声明；
- FactorLab current registry mutation；
- Direction / D1 / D2 / PAWCT 解冻；
- 第三浪假说仓库级解冻；
- PnL 驱动筛选；
- paper trading / production；
- structural-gap favorable filtering；
- empirical interval shrinkage；
- 在同一 consumed 数据里不断造新指标直到通过。

Production authority = `false`。
