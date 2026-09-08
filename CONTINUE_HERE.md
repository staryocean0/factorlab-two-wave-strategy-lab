# CONTINUE HERE — 广义反转 / 均值回归研究入口（2026-09-08）

**本文件是判断本仓库“现在研究什么、下一步做什么”的第一权威。**

仓库名 `factorlab-two-wave-strategy-lab` 保留历史名称，但仓库级任务已经从“无限继续优化一个两浪识别器”升级为：

> **建立广义反转 / 均值回归研究框架，用因果的多尺度父结构区分“完整状态中的暂时偏离”与“父状态真正改变”，并用小预算并行筛选多个机制方向。**

## 1. M0：两浪结构测量底座

现有 `v0.4.3 -> v0.6.17` 的两浪、同尺度、跨 offset、path property、roughness、concentration、qualification、session-aware information-set bounds 等研究全部保留原证据身份，统一归类为：

`M0_two_wave_structure_measurement_foundation`

M0 提供因果完整波浪、尺度表示、父结构、drift / overlap / width / efficiency / roughness / duration / density、publication time，以及 streaming/replay/prefix 不被未来重写的保证。

M0 **不是最终交易策略**。

当前 morphology 全局状态仍为：

`morphology_replication_not_yet_accepted`

操作基线仍为 **v0.4.3**。旧 Direction/D1/D2/PAWCT、第三浪、收益/P&L、fresh OOS、paper trading、production 权限继续冻结。

### M0 v0.6.17 并行任务仍有效

v0.6.17 authoritative-source formal replay 没有取消：

- DataHub bar-support provenance blocker 已解除；
- frozen preanalysis / protocol 已在 real-data result 前冻结；
- `CL-20260908-005` 仍是 M0 的合法本地执行任务；
- 必须使用 accepted DataHub `349,923` row source surface，不能拿 FactorLab `350,561` row `1m_official` 冒充 exact source support。

M0 未闭合不阻止与 morphology acceptance 无关的 broad results-blind research；任何需要“已接受形态学”的结论仍必须等 M0 自己闭合。

## 2. Broad program 的公共问题

“均值”不等于移动平均线。它可以是价格中心、震荡包络、父级波形结构、状态条件轨迹、统计分布、相对关系或某个统计属性的正常区域。

所有反转假说都必须先声明：

1. **Scale**：lower / current / parent；
2. **Parent state**：trend / range / transition / unknown；
3. **Deviation object**：到底什么发生了异常偏离；
4. **Recovery / failure**：什么算回归，什么算父状态改变。

核心判别问题：

> **眼前的反向运动只是父状态中的低一级 fluctuation，还是父级行情真正翻转的开始？**

## 3. 已冻结的公共 Stage-1 数据与父结构

- BUILD：2015-01-05..2018-12-31，已消费 development；
- chronological check：2019-01-01..2020-12-31，不是 fresh；
- post-2020：当前 broad Stage-1 未打开；
- primary view：`5m_offset_0`；
- parent representation：结果盲选择后的 mature M0 birth level `L5`；
- parent temporal maturity：沿用旧 v0.4.3 的 12–48 / 96 bar 规则；
- 不允许根据后续结果重新搜索 parent level / offset。

## 4. R1 / R2 / R3 当前最终状态

### R1 — 趋势中的跨尺度回撤

v1 用完整 L3 two-wave 作为 lower deviation，样本过稀；随后按 results-blind measurement revision 改为：

- parent 仍为 mature L5；
- parent publication 后维护同向 running extreme；
- 第一次反向 close move 达 `0.5 × parent amplitude` 触发；
- `0.5` 来自旧 v0.4.3 `amplitude_ratio=2.0` 的 reciprocal，不是从结果调出来的；
- recovery = pre-trigger running extreme；
- failure = frozen parent structural failure boundary。

M1 trigger supply 足够：BUILD `275`，2019=`57`，2020=`69`。

但真正 first-passage resolved supply 为：

- BUILD `168`；
- 2019 `40`；
- 2020 `39`。

2019/2020 均未达到预注册最小 `50`，所以最终状态是：

`R1_unresolved_evidence_insufficient_after_one_measurement_revision`

不能据此宣称 R1 机制被证伪，也不能降低门槛、改变 0.5、换 level/offset 或继续 M2/M3 事件工程来救它。未来只有在有**实质新增数据**，或有独立理论先定义的新 identity 时，才可重开。

M1 receipt：

`docs/research/cloud_session_20260908_broad_rmr_M1_R1_R2_outcome_receipt_v1.json`

M1 adjudication：

`docs/research/reversal_mean_reversion_M1_R1_R2_adjudication_20260908.md`

### R2 — 震荡边界 / 假突破

M1 改为第一次 5m close 严格越出 frozen L5 parent envelope，不加额外 excursion threshold。

Resolved supply 足够：

- BUILD `657`；
- 2019 `161`；
- 2020 `151`。

但 parent range state 加入后明确变差：

- pooled Brier：`0.2485738 -> 0.2512218`；
- pooled log-loss：`0.6902362 -> 0.6956335`；
- 2019 Brier：`0.2478570 -> 0.2504643`；
- 2020 Brier：`0.2493380 -> 0.2520294`。

因此：

`R2_M1_closed_parent_range_state_adds_no_incremental_reentry_information`

供给充分、主 gate 明确失败，不允许通过加 break speed、波动过滤、最小突破距离、另一套 range algorithm 或 favorable direction/year 来救同一 identity。

### R3 — 结构衰竭 / 状态切换

R3 v1 供给充足，但预注册假说方向被证伪：

- translation decay coefficient `-0.04937`；
- quality decay coefficient `-0.12734`；
- frozen hypothesis 要求 deterioration 越大 -> parent failure risk 越高，即系数应为正。

因此：

`R3_stage1_v1_closed_predeclared_direction_falsified`

不能事后翻转解释，也不能用 HMM/Koopman/deep model 救同一 identity。

## 5. Broad program 当前结论

第一批 price-path 机制没有可升级者：

- R1：unresolved / evidence insufficient；
- R2：adequate evidence 下关闭；
- R3：adequate evidence 下关闭。

这不是继续修补 R1/R2/R3 的理由。方向发现器现在把研究预算转向一个**独立、在结果之前就存在于白皮书的统计状态方向**。

## 6. 当前主线：R4 statistical-state extremes

R4 不是 R1/R2/R3 rescue。

第一轮只允许三个预先存在的状态对象：

1. **Path-efficiency / roughness state**：当前 mature L5 `parent_eff` 相对过去同级 parent 的正常状态；
2. **Lower-scale event-density state**：当前 L5 publication 之前固定 96 个 5m bars 内 mature L3 publications 的数量；
3. **Parent amplitude-state displacement**：当前 L5 parent amplitude 相对过去同级 parent 的正常状态。

统一原则：

> **统计量自己回归，不等于价格回归。**

所以 R4 不以“指标下一期回到均值”为成功条件，而统一问：

> 在相同的 parent geometry baseline 下，这个 statistical state 是否稳定增加对后续 parent failure vs same-direction extension 的概率信息？

R4 只允许：

- 固定过去 100 个 mature L5 parent 的 past-only robust normalization；
- lower event density 固定 trailing 96 bars；
- 三个状态对象分别单独加到同一个低容量 geometry baseline；
- BUILD 2015–2018 fit；
- 2019 / 2020 原样 check；
- 不组合三个状态，不搜阈值，不开 post-2020，不用 PnL。

## 7. 当前 next action

1. 冻结 R4 三个 statistical-state 的 exact preanalysis / protocol；
2. 冻结统一 parent-failure-vs-extension outcome 和 geometry baseline；
3. 先做状态可用性 / event supply 检查，不看结果调窗口；
4. 在 supply 足够后执行一次 2015–2018 BUILD / 2019–2020 check；
5. 任何通过者只能进入 dedicated specialist handoff，不能在 broad repo 内继续深调；
6. 三个都失败则结束这一轮 broad mechanism sweep，而不是自动制造 R5/R6/R7；
7. M0 v0.6.17 formal replay 继续并行等待 authoritative local execution feedback。

## 8. Authority order

1. `CONTINUE_HERE.md`
2. `docs/governance/reversal_mean_reversion_program_charter_v1.json`
3. `docs/governance/reversal_mean_reversion_program_state_v1.json`
4. `docs/research/reversal_mean_reversion_program_whitepaper_v1.md`
5. `AGENTS.md`
6. post-reset lane / measurement protocols
7. 历史 v0.x 文档——只在 M0 / 对应具体 identity 内有权威性

## 9. 权限边界

仍然禁止：

- FactorLab current registry mutation；
- Layer 4 economic routing；
- real / paper trading；
- fresh-OOS 声称；
- 用 PnL 挑 recognizer / parent-state formula；
- 把 algorithm-generated labels 当 morphology ground truth；
- 失败后不断加过滤器直到通过。

Production authority = `false`。
