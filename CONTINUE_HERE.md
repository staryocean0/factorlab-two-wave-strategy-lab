# CONTINUE HERE — 广义反转 / 均值回归研究入口（2026-09-08）

**本文件是判断本仓库“现在研究什么、下一步做什么”的第一权威。**

仓库 `factorlab-two-wave-strategy-lab` 的仓库级任务是：

> **用因果多尺度结构研究广义反转 / 均值回归，区分“完整父状态中的暂时偏离”与“父状态本身改变”，并用小预算筛选多个机制，而不是无限优化一个 recognizer 或一个策略。**

当前总状态：

`ROUND1_CLOSED_CL005_CLOUD_REVIEWED_T1_CLOSED_SUPPLY_INSUFFICIENT_WAITING_NEW_DATA_OR_INDEPENDENT_THEORY`

## 1. M0：两浪结构测量底座

历史 `v0.4.3 -> v0.6.17` 两浪研究全部保留，统一角色：

`M0_two_wave_structure_measurement_foundation`

M0 提供因果完整波、尺度、父结构、drift / overlap / width / efficiency / roughness / duration / density、publication time、streaming/replay/prefix 不被未来重写，以及 session/source information-set 语义。

M0 是**测量底座，不是自动成立的交易 alpha**。

全局 morphology 继续是：

`morphology_replication_not_yet_accepted`

操作基线继续是 `v0.4.3`。Direction / D1 / D2 / PAWCT、第三浪、outcome/PnL、fresh OOS、paper trading、production 均未解冻。

## 2. CL-20260908-005 已完成云端验收

本地 formal replay 已由云端独立复核。

状态：

`CL-20260908-005 = CLOUD REVIEWED / COMPLETED`

正式接受的 frozen verdict：

`session_aware_bounds_valid_but_structural_gap_nonidentifiability_is_material`

云端 review：

`docs/research/two_wave_session_aware_information_set_bounds_cloud_review_20260908.md`

关键事实：

- authoritative DataHub 1m source rows = `349,923`；
- 2015-01-05..2020-12-31；2021+ loaded = `0`；
- five native 5m views exact label/OHLC replay；
- published legs = `737,104`；
- N mismatch = `0`；
- J / C_inf / C_1 / C_2 oracle coverage = `100%`；
- fully enveloped legs = `528,360`；
- structural-gap universal-bound legs = `208,744`，约 `28.3%`。

因此 v0.6.17 被接受为新的 M0 **interval-valued measurement capability**，而不是 morphology acceptance。

新硬规则：

> **native 5m OHLC 不能默认等同于已知 fine path。**

以后任何 path efficiency / roughness / concentration 类研究都必须声明：

1. 真实 finer-source 直接测量；或
2. fully-enveloped 下的 finite interval；或
3. structural-gap 下的 partial-identification / universal interval。

禁止把 interval midpoint 或其它 proxy 偷换成真实 fine-path point value。

能力 admission：

`docs/governance/reversal_mean_reversion_v0617_measurement_capability_admission_v1.json`

项目含义：

`docs/research/reversal_mean_reversion_v0617_measurement_implications_20260908.md`

## 3. Broad Round-1 已正式收口

共同证据身份：

- BUILD = 2015–2018 consumed development；
- chronological check = 2019、2020，not fresh；
- post-2020 未打开；
- primary view = `5m_offset_0`；
- parent representation = results-blind 选择的 mature M0 L5。

总裁决：

`BROAD_RMR_STAGE1_ROUND1_CLOSED_NO_PROMOTED_MECHANISM`

### R1 — Cross-scale pullback

状态：

`unresolved_evidence_insufficient_after_one_results_blind_measurement_revision`

M1 trigger supply：`275 / 57 / 69`；resolved supply：`168 / 40 / 39`（BUILD / 2019 / 2020）。2019/2020 未达到 frozen `50` minimum。

**R1 未被证伪。** materially new data 到来后，它是优先重检 lane；但不能利用旧 2015–2020 结果改 0.5 shock、scale、offset 或 sample gate。

### R2 — Range-boundary / failed-breakout reversion

状态：`closed_with_adequate_evidence_under_M1`。

供给充分，但 parent range state 让 Brier / log-loss 和 2019/2020 都变差。禁止同 identity rescue。

### R3 — Structural exhaustion / transition

状态：`closed_predeclared_direction_falsified`。

供给充分，但两个 deterioration 系数均为负，与结果前冻结的正 failure-risk 方向相反。禁止翻转故事或 deep-model rescue。

### R4 — Statistical-state extremes

状态：`closed_no_candidate_qualifies`。

Path inefficiency、lower-scale event density、amplitude extremity 三个状态全部没有在 common geometry baseline 之上增加稳定价格信息。

项目级结论继续保留：

> **统计属性自身的持续、极端或均值回归，不等于价格存在均值回归 alpha。**

## 4. Round-2 T1 已在 outcome 前关闭

Identity：

`T1_transitory_component_after_extreme_intraday_shock_v1`

`CL-20260908-006` 的 supply/alignment-only 本地执行已由云端独立复核。

状态：

`CL-20260908-006 = CLOUD REVIEWED / COMPLETED`

但 frozen supply gate 失败：

| partition | aligned | minimum | result |
|---|---:|---:|---|
| BUILD 2015–2018 | 364 | 150 | PASS |
| 2019 | 48 | 50 | **FAIL** |
| 2020 | 87 | 50 | PASS |

因此：

`T1_current_data_event_supply_insufficient / CLOSED_BEFORE_OUTCOME`

云端 review：

`docs/research/reversal_mean_reversion_T1_supply_cloud_review_20260908.md`

Post-event future return / reversal / continuation / Brier / log-loss / PnL 均未打开。

禁止因为 `48` 接近 `50` 就降低 5 robust-sigma threshold、缩短 960-bar reference、换 offset、分方向或筛时段。

## 5. 当前科学地图

- **M0**：v0.6.17 interval measurement capability 已 cloud-reviewed；morphology 仍未 accepted。
- **R1**：unresolved，未来 materially new data 优先重检。
- **R2**：closed。
- **R3**：closed。
- **R4**：closed。
- **T1**：current identity closed before outcome due supply failure。
- relative-value / overnight：兄弟专题，不控制本仓主线。

## 6. 当前合法 next actions

现在**没有**合法理由继续在同一 2015–2020 consumed window 上自动制造新的 R5/R6/R7 指标。

下一步按优先级只有：

1. **等待统一数据工具的新数据更新。** 数据到达后先做 source/provenance、timestamp/session、missing/duplicate/unexpected ledger；
2. 在任何 outcome 前冻结新的 BUILD / chronological check / holdout；
3. 明确 fine-path feature 属于 direct measurement 还是 interval/partial-identification；
4. materially new data 通过 admission 后，优先给 unresolved R1 一个新的 results-blind research budget；
5. 若出现真正独立的新理论，可在 outcome 前 preregister 一个新 identity；禁止把 R2/R3/R4/T1 改名重跑；
6. 不做 PnL、paper trading、production。

## 7. 新数据到来时对本仓最重要的要求

除了更长年份，更重要的是 **真实 finer source completeness**：

- CSI1000 / CSI300 / CSI500 完整、可追溯 1m source；
- timestamp label / timezone / session semantics；
- missing / duplicate / unexpected clock ledger；
- source SHA / lineage；
- 若有 3s 或更细 observations，保留原始 observation identity，不只保留重采样 OHLC。

这样可以减少未来 path research 对 partial-identification interval 的依赖。

## 8. Authority order

上下文压缩或新助手接管时，按以下顺序：

1. `CONTINUE_HERE.md`
2. `docs/governance/reversal_mean_reversion_program_charter_v1.json`
3. `docs/governance/reversal_mean_reversion_program_state_v1.json`
4. `docs/research/reversal_mean_reversion_program_whitepaper_v2.md`
5. `AGENTS.md`
6. post-reset protocols / cloud reviews
7. 历史 v0.x 文档——只在 M0 / 对应具体 identity 内有权威性

旧文件若写“唯一下一动作是继续 v0.6.17”，已被本文件 supersede；CL-005 已完成 cloud review。

## 9. 权限边界

仍然禁止：

- FactorLab current registry mutation；
- Layer 4 economic routing；
- fresh-OOS 虚假声明；
- 用 PnL 挑 recognizer / parent-state formula；
- 把 algorithm-generated labels 当 morphology ground truth；
- empirical interval shrinkage；
- structural-gap favorable filtering；
- real / paper trading；
- production。

Production authority = `false`。
