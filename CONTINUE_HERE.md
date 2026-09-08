# CONTINUE HERE — 广义反转 / 均值回归研究入口（2026-09-08）

**本文件是判断本仓库“现在研究什么、下一步做什么”的第一权威。**

仓库 `factorlab-two-wave-strategy-lab` 的历史核心是两浪父结构识别，但当前仓库级任务已经升级为：

> **用因果多尺度结构研究广义反转 / 均值回归：区分“完整父状态中的暂时偏离”与“父状态本身真正改变”，并用小预算比较多个机制，而不是无限优化一个 recognizer 或一个策略。**

## 1. M0：两浪结构测量底座

现有 `v0.4.3 -> v0.6.17` 两浪、同尺度、path property、roughness、concentration、qualification、session-aware information-set bounds 等研究全部保留原证据身份，统一归类为：

`M0_two_wave_structure_measurement_foundation`

M0 提供因果完整波浪、尺度表示、父结构、drift / overlap / width / efficiency / roughness / duration / density、publication time，以及 streaming/replay/prefix 不被未来重写的保证。

M0 **是测量基础，不是自动成立的交易 alpha**。

当前 morphology 状态仍为：

`morphology_replication_not_yet_accepted`

操作基线仍为 v0.4.3。旧 Direction/D1/D2/PAWCT、第三浪、收益/P&L、fresh OOS、paper trading、production 权限继续冻结。

### M0 v0.6.17 继续并行

v0.6.17 authoritative-source formal replay 没有取消：

- `CL-20260908-005` 仍是 M0 合法本地执行任务；
- 当前 formal result / `cloud_results/cloud_chat_v0617_session_aware_bounds/` 仍未回传；
- 必须使用 accepted DataHub `349,923` row source surface；
- 不能拿 FactorLab `350,561` row `1m_official` 冒充 exact source support；
- compact refresh handoff：`docs/ops/cl_20260908_005_v0617_formal_replay_refresh_20260908.md`。

M0 未闭合不阻止不依赖 morphology acceptance 的 results-blind broad research，但任何声称“形态学已接受”的结论仍必须等 M0 自己闭合。

## 2. Broad program 公共坐标

所有反转假说都必须在结果前声明：

1. **Scale**：lower / current / parent；
2. **Parent state**：trend / range / transition / unknown；
3. **Deviation object**：什么发生了异常偏离；
4. **Recovery / failure**：什么算回归，什么算父状态改变。

“均值”可以是价格中心、震荡包络、父级波形结构、状态条件轨迹、统计分布、相对关系或某个统计属性的正常区域。

## 3. Round-1 已冻结的数据与父结构

- BUILD：2015-01-05..2018-12-31，已消费 development；
- chronological check：2019-01-01..2020-12-31，不是 fresh；
- post-2020：本轮从未打开；
- primary view：`5m_offset_0`；
- parent representation：结果盲结构供给选择后的 mature M0 L5；
- temporal maturity：旧 v0.4.3 的 12–48 / 96 bar 规则；
- 不允许根据结果重选 parent level / offset。

## 4. Round-1 最终路线裁决

权威 closeout：

`docs/research/reversal_mean_reversion_stage1_round1_closeout_20260908.md`

最终决策：

`BROAD_RMR_STAGE1_ROUND1_CLOSED_NO_PROMOTED_MECHANISM`

### R1 — Cross-scale pullback

最终状态：

`unresolved_evidence_insufficient_after_one_results_blind_measurement_revision`

v1 要求 lower deviation 本身也是完整 L3 two-wave，样本过稀。M1 按结果盲方式改成：parent publication 后第一次反向 close move 达 `0.5 × parent amplitude` 即触发；0.5 来自旧 v0.4.3 `amplitude_ratio=2.0` reciprocal，并非结果调参。

M1 trigger supply：BUILD `275`，2019=`57`，2020=`69`。

但 resolved first-passage 只有：

- BUILD `168`；
- 2019 `40`；
- 2020 `39`。

2019/2020 未达到预注册最小 `50`，所以 **R1 不能叫失败，也不能叫成功，只能 unresolved**。

禁止：降低 sample gate、改 0.5、换 level/offset 或继续在同一 2015–2020 结果上造 M2/M3 来救。未来重开要求实质新增数据，或独立理论先冻结的新 identity。

### R2 — Range-boundary / failed-breakout reversion

最终状态：

`closed_with_adequate_evidence_under_M1`

M1 resolved supply 足够：BUILD `657`，2019=`161`，2020=`151`。

但加入 parent range state 后明确变差：

- pooled Brier `0.2485738 -> 0.2512218`；
- pooled log-loss `0.6902362 -> 0.6956335`；
- 2019、2020 Brier 都恶化。

因此 R2 关闭。不能通过增加最小突破距离、break speed、波动过滤、另一个 range algorithm 或 favorable direction/year 来救同一 identity。

### R3 — Structural exhaustion / transition

最终状态：

`closed_predeclared_direction_falsified`

供给充足：BUILD `744`，2019=`172`，2020=`144`。

预注册假说要求 deterioration 越大 -> parent failure risk 越高，但实际：

- translation decay coefficient `-0.04937`；
- quality decay coefficient `-0.12734`。

方向相反，因此 R3 v1 关闭。不能翻转解释，也不能用 HMM/Koopman/deep model 救同一 identity。

### R4 — Statistical-state extremes

最终状态：

`closed_no_candidate_qualifies`

R4 用同一个 geometry baseline `abs_drift + log_amplitude` 分别测试三个结果前已冻结的统计状态：

1. path inefficiency；
2. lower-scale event density；
3. parent amplitude extremity。

三者供给都足够，但都让 parent failure vs extension 概率预测变差：

- inefficiency Brier `0.2505775 -> 0.2510705`；
- event density `0.2503372 -> 0.2536279`，且状态系数方向也错误；
- amplitude extremity `0.2505775 -> 0.2522137`；
- 三个候选在 2019、2020 都未同时改善。

R4 receipt：

`docs/research/cloud_session_20260908_broad_rmr_R4_statistical_state_receipt_v1.json`

R4 adjudication：

`docs/research/reversal_mean_reversion_R4_statistical_state_adjudication_20260908.md`

特别保留这个项目级结论：

> **统计属性自己持续、极端或回归，不等于价格均值回归。**

## 5. Round-1 科学结论

这一轮没有找到可晋级的低容量广义均值回归机制，这本身是有效结果：

- M0 两浪结构能提供严谨的 parent-state 坐标，但不会自动变成 alpha；
- R1 是 evidence-supply unresolved，不是机制证伪；
- R2、R3、R4 在供给充分情况下分别被当前低容量假说否定；
- 不应继续在同一 2015–2020 consumed window 上自动发明 R5/R6/R7，直到某个指标碰巧通过。

Authority reset 与 Round-1 evidence 已通过 PR #5 merge 回真正活跃分支，integration commit：

`9cded4c0e56e7d92232157699c0b569b39cabea4`

## 6. Round-2 的唯一已准入 theory intake：T1

一般性的：

`broad_new_lane_generation_authorized = false`

仍然成立。

但 Round-1 closeout 允许一个例外：**独立理论/文献驱动机制必须在 outcome 前定义并 review**。当前已按这个门准入一个且仅一个 T1：

`T1_transitory_component_after_extreme_intraday_shock_v1`

它不是 R1/R2/R3/R4 rescue，也不是“又加一个技术指标”。理论依据来自两类相反的公开证据：

- 极端短周期价格变化之后可能发生反转，常被讨论为 temporary price pressure / liquidity provision；
- 信息型 jump 也可能出现短期 continuation / underreaction。

因此 T1 不假设“大幅波动必然反转”，而只问：

> **在一个已经完成的极端 5m shock 内，如果最大定向位移在 5m 收盘前已经出现部分回吐，这个已观察到的 transitory-component symptom，是否增加后续同日完整回撤相对等距延续的概率？**

当前数据没有可靠 volume/order book/news，所以：

- 不允许把 T1 叫直接 liquidity identification；
- 不允许把 T1 叫 direct information-shock classifier；
- 唯一机制变量是 completed event bar 的 `within_bar_retrace_fraction`。

已冻结：

- theory intake：`docs/research/reversal_mean_reversion_round2_transitory_shock_theory_intake_20260908.md`；
- supply protocol：`docs/governance/reversal_mean_reversion_T1_transitory_shock_supply_protocol_v1.json`；
- execution freeze：`docs/governance/reversal_mean_reversion_T1_supply_execution_freeze_v1.json`；
- local task：`CL-20260908-006`；
- handoff：`docs/ops/cl_20260908_006_T1_transitory_shock_supply_handoff.md`。

### T1 当前只允许 supply/alignment audit

事件定义已经在供给前冻结：

- native `5m_offset_0`；
- `r5 = log(close/open)`；
- 只用当前 bar 前恰好 960 个 native 5m bars；
- median + `1.4826*MAD`；
- `abs(robust_z) >= 5.0`；
- 不允许 threshold / window / offset / sign-specific search。

事件自身的 1m path 只允许做 alignment 和 completed-bar retrace 描述；不得读事件后的 future return / reversal / continuation / Brier / log-loss / PnL。

Frozen aligned supply gate：

- BUILD >= `150`；
- 2019 >= `50`；
- 2020 >= `50`。

如果供给失败，T1 当前 2015–2020 identity 直接关闭，不降 5-sigma、不改 960。

如果供给通过，**outcomes 仍然 sealed**；必须先 cloud review receipt，再另写 outcome execution freeze。

## 7. Broad program 重开条件

除了已经 results-blind 冻结的 T1 supply-only intake，新的 broad mechanism screen 仍只有在以下任一条件成立后才能重开：

1. **实质新增数据**到位，并在看 outcome 前重新冻结 BUILD/check/holdout 角色；
2. 另一个**独立理论/文献驱动的新机制**在 outcome 前先被定义、review，并且不得只是本轮失败路线的改名 rescue；
3. M0 产生一个实质新的、被接受的因果测量对象，并先修改 program charter，再做 results-blind 研究。

R2/R3/R4 原样重跑不属于新机制。

## 8. 当前 next action

两个彼此独立的本地任务均已 `local_reported`，**云端复核尚未发生**：

1. **M0 / CL-20260908-005**：frozen v0.6.17 authoritative-source formal replay 已回传。裁决 `session_aware_bounds_valid_but_structural_gap_nonidentifiability_is_material`。正式报告 `docs/research/two_wave_session_aware_information_set_bounds_results_v0617.md`。不得把 local_reported 写成 cloud_reviewed，也不得改 morphology 全局状态。
2. **Broad T1 / CL-20260908-006**：supply/alignment audit 已回传。gate = `T1_current_data_event_supply_insufficient`（2019 aligned 48<50）。**不得执行 post-event outcome，不得降低 5-sigma / 960-bar 门槛。**

云端下一步固定为：

- 收到 CL-005 时先做 M0 source/blob/gate 独立复核；
- 收到 CL-006 时先做 T1 supply/source/blob 独立复核；
- T1 只有 supply cloud-reviewed PASS 后才可能另行授权 outcome；
- 你之后通知统一数据工具完成数据更新时，先做 source/role admission，再决定 R1 等 unresolved hypothesis 是否获得新 research budget；
- 在此之前不做 PnL、paper trading 或 production。

## 9. Authority order

以后发生上下文压缩或新助手接管，按以下顺序判断仓库级方向：

1. `CONTINUE_HERE.md`
2. `docs/governance/reversal_mean_reversion_program_charter_v1.json`
3. `docs/governance/reversal_mean_reversion_program_state_v1.json`
4. `docs/research/reversal_mean_reversion_program_whitepaper_v1.md`
5. `AGENTS.md`
6. post-reset lane / measurement protocols
7. 历史 v0.x 文档——只在 M0 / 对应具体 identity 内有权威性

旧文件若写“唯一下一动作是继续 v0.6.17”，只对 M0 子项目有效，不再控制整个仓库。

## 10. 权限边界

仍然禁止：

- FactorLab current registry mutation；
- Layer 4 economic routing；
- real / paper trading；
- fresh-OOS 声称；
- 用 PnL 挑 recognizer / parent-state formula；
- 把 algorithm-generated labels 当 morphology ground truth；
- 失败后不断加过滤器直到通过。

Production authority = `false`。
