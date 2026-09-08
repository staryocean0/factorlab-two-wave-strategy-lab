# CONTINUE HERE — 广义反转 / 均值回归研究入口（2026-09-08）

**本文件是判断本仓库“现在研究什么、下一步做什么”的第一权威。**

仓库 `factorlab-two-wave-strategy-lab` 的仓库级任务是：

> **用因果多尺度结构研究广义反转 / 均值回归，区分“完整父状态中的暂时偏离”与“父状态本身改变”，并用小预算筛选多个机制，而不是无限优化一个 recognizer 或一个策略。**

当前总状态：

`BROAD_RMR_ACTIVE_WITH_REUSABLE_TRAIN_VALIDATION_BLACKBOX_POLICY`

## 1. 数据不是一次性消耗品

从现在起采用三层数据角色：

1. **TRAIN / Research corpus**：训练、机制设计、参数估计、事件级拆解、失败分析，可反复使用；
2. **VALIDATION / Diagnostic validation**：做跨时期验证，也允许失败后打开细节诊断并继续改模型，可反复使用；
3. **BLACKBOX / Confirmation reserve**：只给已经成熟、冻结好的候选做独立最终确认，默认只返回预先定义的 aggregate 结果。

关键原则：

> **数据不会因为被看过就失去研究价值；失去的只是“完全未见黑箱确认”的资格。**

如果一个 BLACKBOX 失败后决定拆细节，它只会从 `BLACKBOX -> VALIDATION`，以后仍可继续研究，不是“报废”。

当前角色：

- 2015-01-05..2018-12-31 = **TRAIN**；
- 2019-01-01..2020-12-31 = **VALIDATION**；
- 当前尚未正式指定新的 BLACKBOX 日期块。

详细政策：

`docs/governance/reversal_mean_reversion_data_reuse_validation_policy_v1.md`

这也 supersede 之前“同一 2015–2020 consumed window 原则上不能继续研究”的仓库级表述。历史已经冻结并执行过的 R1/R2/R3/R4/T1 裁决继续保留，不追溯改写；但 2015–2020 数据本身可以继续作为 TRAIN/VALIDATION 研究资产使用。

## 2. M0：两浪结构测量底座

历史 `v0.4.3 -> v0.6.17` 两浪研究全部保留，统一角色：

`M0_two_wave_structure_measurement_foundation`

M0 提供因果完整波、尺度、父结构、drift / overlap / width / efficiency / roughness / duration / density、publication time、streaming/replay/prefix 不被未来重写，以及 session/source information-set 语义。

M0 是**测量底座，不是自动成立的交易 alpha**。

全局 morphology 继续是：

`morphology_replication_not_yet_accepted`

操作基线继续是 `v0.4.3`。Direction / D1 / D2 / PAWCT、第三浪、PnL、paper trading、production 均未解冻。

## 3. CL-20260908-005 已完成云端验收

状态：

`CL-20260908-005 = CLOUD REVIEWED / COMPLETED`

正式接受 verdict：

`session_aware_bounds_valid_but_structural_gap_nonidentifiability_is_material`

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

Cloud review：

`docs/research/two_wave_session_aware_information_set_bounds_cloud_review_20260908.md`

能力 admission：

`docs/governance/reversal_mean_reversion_v0617_measurement_capability_admission_v1.json`

## 4. 已执行 Round-1 的历史结论

这些是**历史 identity 的结果**，继续保留，不因新数据复用政策而倒改。

### R1 — Cross-scale pullback

历史状态：

`unresolved_evidence_insufficient_after_one_results_blind_measurement_revision`

M1 trigger supply：`275 / 57 / 69`；resolved supply：`168 / 40 / 39`（TRAIN / 2019 / 2020）。旧 frozen gate 要求 2019/2020 各 >=50，因此该次 identity 只能 unresolved。

**但 R1 研究本身没有关闭。**

在新的 TRAIN/VALIDATION 政策下，可以继续利用 2015–2020 做模型开发、事件拆解和验证；只是这些结果必须标记为 reused TRAIN/VALIDATION，不能叫 fresh OOS。

### R2 — Range-boundary / failed-breakout reversion

历史低容量 identity：`closed_with_adequate_evidence_under_M1`。

这只关闭当时那套具体定义，不代表“所有震荡边界均值回归永久禁止研究”。如果未来有独立的新理论/新定义，可以作为新的 identity 在 TRAIN/VALIDATION 上研究，但不能把旧失败改名成成功。

### R3 — Structural exhaustion / transition

历史 v1：`closed_predeclared_direction_falsified`。

两个 deterioration 系数方向与预注册相反。该 v1 不可翻转故事；但更广义的状态切换研究并未被永久禁止。

### R4 — Statistical-state extremes

历史 v1：`closed_no_candidate_qualifies`。

Path inefficiency、lower-scale event density、amplitude extremity 三个候选在当时定义下无增量。

项目级结论继续保留：

> **统计属性自身的持续、极端或均值回归，不等于价格存在均值回归 alpha。**

## 5. T1 历史结论

`CL-20260908-006 = CLOUD REVIEWED / COMPLETED`

历史 supply gate：

| partition | aligned | minimum | result |
|---|---:|---:|---|
| BUILD 2015–2018 | 364 | 150 | PASS |
| 2019 | 48 | 50 | **FAIL** |
| 2020 | 87 | 50 | PASS |

所以历史 identity：

`T1_current_data_event_supply_insufficient / CLOSED_BEFORE_OUTCOME`

这次裁决不追溯修改。

但从新政策起，未来 sample gate 不再机械默认“每个自然年都 >= N”。优先根据总有效样本、跨时期稳定性和统计精度事前设计；逐年结果更多作为稳定性诊断。

## 6. 当前研究可以继续，不需要等新数据才能动

现在合法且推荐的 next actions 是：

1. **继续使用 2015–2018 TRAIN + 2019–2020 VALIDATION 做广义反转方向研究。**
2. R1 仍是高优先方向，可继续拆解“父趋势中的突然反向冲击”问题；允许查看 VALIDATION 细节、定位失败、迭代模型。
3. 也可以并行研究真正独立的新机制，不要求每个方向都拥有一块全新的未见数据。
4. 新数据到来后，绝大多数新历史优先加入 TRAIN/VALIDATION，扩大 regime 和稀有事件覆盖；**不要一到新数据就整段烧成黑箱。**
5. 只有当某个候选已经在 TRAIN + VALIDATION 上基本成熟，才从最新数据中留一小块连续区间做 BLACKBOX。
6. BLACKBOX 只看 aggregate frozen outputs；若要拆细节，则明确把该 block 降级成 VALIDATION，再另留未来黑箱。
7. 不做 PnL、paper trading、production。

## 7. 本仓真正缺的数据

当前数据已经足够继续做研究。新增数据主要解决三类问题：

### A. 更长时间覆盖

优先希望 CSI1000 以及可比较宽基指数的稳定 1m 历史覆盖更长年份，以增加：

- 牛市；
- 熊市；
- 横盘；
- 高波动；
- 低波动；
- 稀有急跌/急涨事件。

这主要提高机制样本量和 regime 覆盖，不是因为旧数据“过期”。

### B. 更细路径数据

对“突然冲击到底是次级波动还是父级反转”这类研究，最有价值的是：

- 真实 1m 完整路径；
- 若能取得，3s / tick / observation-level 指数源；
- 明确 timestamp / session / source provenance；
- 不 silent-fill。

这样可以减少 5m OHLC 下的 partial-identification 问题。

### C. 更丰富的状态信息

后续若研究机制来源，可补：

- CSI300 / CSI500 / CSI1000 同步 1m；
- point-in-time constituents / weights；
- 全市场 A 股 1m（中央数据湖即可，不必复制入仓）；
- IF / IC / IM 真实合约分钟线，后期做可交易性；
- 若能得到 volume / order book / spread / news timestamp，则可研究 liquidity-vs-information shock；没有就不伪造代理。

## 8. Authority order

上下文压缩或新助手接管时，按以下顺序：

1. `CONTINUE_HERE.md`
2. `docs/governance/reversal_mean_reversion_program_charter_v1.json`
3. `docs/governance/reversal_mean_reversion_data_reuse_validation_policy_v1.md`
4. `docs/governance/reversal_mean_reversion_program_state_v1.json`
5. `docs/research/reversal_mean_reversion_program_whitepaper_v2.md`
6. `AGENTS.md`
7. post-reset protocols / cloud reviews
8. 历史 v0.x 文档——只在 M0 / 对应具体 identity 内有权威性

## 9. 权限边界

仍然禁止：

- 把 TRAIN/VALIDATION 包装成 fresh OOS；
- 把 algorithm-generated labels 当 morphology ground truth；
- empirical interval shrinkage；
- structural-gap favorable filtering；
- 用 PnL 挑 recognizer / parent-state formula；
- real / paper trading；
- production。

Production authority = `false`。
