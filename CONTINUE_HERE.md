# CONTINUE HERE — 广义反转 / 均值回归研究入口（2026-09-08）

**本文件是判断本仓库“现在研究什么、下一步做什么”的第一权威。**

仓库名 `factorlab-two-wave-strategy-lab` 保留历史名称，但当前仓库级任务已经从“无限继续优化一个两浪识别器”升级为：

> **建立广义反转 / 均值回归研究框架，用多尺度父结构区分“完整状态中的暂时偏离”与“父状态真正改变”，并并行浅测多个机制方向。**

## 1. 两浪研究的新角色：M0 结构测量底座

现有 `v0.4.3 -> v0.6.17` 的两浪、同尺度、跨 offset、path property、roughness、concentration、qualification、session-aware information-set bounds 等研究全部保留原证据身份。

它们现在仓库级统一归类为：

`M0_two_wave_structure_measurement_foundation`

M0 负责回答：

- 什么是因果完整波浪；
- 什么是同尺度；
- 两个完整波如何形成局部父结构；
- 父结构的 drift / overlap / width / efficiency / roughness / duration / event density 如何测量；
- 如何保证 streaming、replay、prefix 不被未来行情重写；
- 不同 bar support / offset / session 信息集是否真的可比。

M0 **不是最终交易策略**，也不能因为某个结构量稳定就自动推出价格会反转或延续。

当前 morphology 全局状态仍为：

`morphology_replication_not_yet_accepted`

操作基线仍为 **v0.4.3**。旧的 Direction/D1/D2/PAWCT、第三浪、收益/P&L、fresh OOS、paper trading、production 权限继续冻结。

## 2. M0 当前独立前沿：v0.6.17 继续保留

v0.6.17 的权威任务没有取消。

当前状态：

- DataHub bar-support provenance blocker 已解除；
- frozen preanalysis / protocol 已在 real-data result 前冻结；
- cloud Stage-1 preflight 已完成；
- implementation conformance bug 已在 formal result 前修复；
- authoritative-source formal replay 尚未闭合；
- `CL-20260908-005` 仍是 M0 的合法本地执行任务。

继续读取：

- `docs/ops/datahub_bar_support_provenance_cloud_review_20260907.md`
- `docs/ops/v0617_session_aware_bounds_freeze_receipt_20260908.md`
- `docs/ops/v0617_stage1_cloud_preflight_20260908.md`
- `docs/research/two_wave_session_aware_information_set_bounds_preanalysis_v0617.md`
- `docs/research/two_wave_session_aware_information_set_bounds_protocol_v0617.md`
- `docs/ops/cloud_local_communication.md` 中 `CL-20260908-005`

M0 formal replay 必须继续使用 accepted DataHub `349,923` row authoritative source surface，不能拿 FactorLab `350,561` row `1m_official` 冒充 exact source support。

**但是：M0 未闭合不再阻止整个仓库做与其结果无关的 broad results-blind preanalysis。**

只有当某个后续策略结论明确需要“accepted morphology / v0.6.17 accepted bound”时，才必须先等 M0 完成。

## 3. 仓库级核心科学问题

所谓“均值”不等于一条移动平均线。

它可以是：

- 价格中心或通道；
- 震荡包络；
- 两个已完成波形成的父结构；
- 某 market state 下的正常轨迹；
- 分布中心/区间；
- 多资产相对关系；
- 路径效率、波动率、振幅、事件密度等统计属性的正常状态。

所有反转假说都必须先回答四件事：

1. **Scale：** lower / current / parent；
2. **Parent state：** trend / range / transition / unknown；
3. **Deviation object：** 到底什么发生了异常偏离；
4. **Recovery / failure：** 什么事件算回归，什么事件算父状态改变。

最核心的判别问题是：

> **低一级的剧烈反向波动，究竟只是完整父状态里的 fluctuation，还是父级行情真正翻转的开始？**

## 4. 第一批三条主研究路线

### R1 — Cross-scale pullback：趋势中的次级回撤

父级上涨/下跌结构仍完整，低一级突然反向运动。

研究：

> 在 counter-move severity 相近时，父级结构完整度能否事前提高“先恢复、后破坏父结构”的区分能力？

这是“上涨趋势急跌后是否值得逢低买 / 下跌趋势急涨后是否值得逢高卖”的机制版，不先做交易收益优化。

### R2 — Range-boundary reversion：震荡边界 / 假突破

父级是低漂移震荡包络，价格突然越界。

研究：

> 越界是暂时 overshoot / 假突破，还是震荡已经变成新趋势？

先比较 parent drift / overlap / efficiency、break severity、break speed 与 local volatility，不允许结果出来后不断换 range 定义救策略。

### R3 — Structural exhaustion / transition：趋势衰竭与状态切换

父级仍有方向，但结构质量逐步恶化。

研究：

> 能否在明确反向突破发生前，用结构退化识别 reversal / transition risk 上升？

候选现象包括：推进减弱、overlap 增加、效率下降、振幅异常、反向低级别事件密度上升等；第一轮只允许极小候选预算。

## 5. 次级方向

### R4 — Statistical-state extremes

路径效率、波动率、频带振幅、事件密度、波浪时长等属性本身可能均值回归。

必须牢记：

> **统计量自己回归，不等于价格均值回归。**

只有当状态变量对 price recovery/extension 或 parent transition 有稳定增量信息时，才升级。

### R5 — Relative-value / overnight dislocation

跨指数、跨资产、隔夜 gap 属于广义均值回归的一个子类，但已有兄弟专题在研究。

本仓可引用，不把它重新变成本仓主线。

## 6. 新研究方式

本仓现在是：

`direction_finder_not_single_strategy_optimizer`

默认规则：

- 同时保留 2–3 个机制方向；
- 给每条路线相近的小预算；
- 先做 phenomenon -> causal observability -> chronological stability；
- 不在 Stage-1 用 PnL 选模型；
- 不在其他路线没浅测前连续几十轮深挖一条；
- strong lane 毕业给 dedicated identity；
- ambiguous lane 暂存；
- failed lane 关闭，不靠后验加条件救活。

## 7. 当前仓库级 next action

**不是继续设计 v0.6.18 / v0.6.19。**

当前顺序：

1. 权威叙事重置到 broad reversal program；
2. 冻结公共 `scale / parent state / deviation / recovery` measurement vocabulary；
3. 给 R1 / R2 / R3 分别写 results-blind shallow preanalysis；
4. 盘点现有 2015–2020 DataHub views 和分支中已计算的 causal two-wave artifacts，选择三条路线都能公平使用的最小数据面；
5. 在不声称 fresh OOS 的前提下做第一轮 equal-budget shallow screen；
6. 比较路线后再决定哪个值得专门深挖。

M0 v0.6.17 formal replay 可由本地 authoritative-source 执行链并行推进，不阻断以上 1–4。

## 8. Authority order

以后发生上下文压缩或新助手接管，按以下顺序决定仓库级方向：

1. `CONTINUE_HERE.md`
2. `docs/governance/reversal_mean_reversion_program_charter_v1.json`
3. `docs/governance/reversal_mean_reversion_program_state_v1.json`
4. `docs/research/reversal_mean_reversion_program_whitepaper_v1.md`
5. `AGENTS.md`
6. post-reset lane protocols / preanalysis
7. 旧两浪 v0.x 文档——只在 M0 / 历史具体 identity 内有权威性

若旧文件写“唯一下一动作是继续 v0.6.17”，它只对 **M0 子项目**有效，不再控制整个仓库。

## 9. 权限边界

仍然禁止：

- FactorLab current registry mutation；
- Layer 4 economic routing；
- real trading / paper trading；
- fresh-OOS 声称；
- 用 trading PnL 挑 recognizer / parent-state formula；
- 把 algorithm-generated labels 当 morphology ground truth。

Production authority = `false`。
