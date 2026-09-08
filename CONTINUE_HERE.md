# CONTINUE HERE — 广义反转 / 均值回归研究入口（2026-09-08）

**本文件是判断本仓库“现在研究什么、下一步做什么”的第一权威。**

仓库名 `factorlab-two-wave-strategy-lab` 保留历史名称，但仓库级任务已经从“无限继续优化一个两浪识别器”升级为：

> **建立广义反转 / 均值回归研究框架，用因果的多尺度父结构区分“完整状态中的暂时偏离”与“父状态真正改变”，并用小预算并行筛选多个机制方向。**

## 1. M0：两浪结构测量底座

现有 `v0.4.3 -> v0.6.17` 的两浪、同尺度、跨 offset、path property、roughness、concentration、qualification、session-aware information-set bounds 等研究全部保留原证据身份。

它们现在仓库级统一归类为：

`M0_two_wave_structure_measurement_foundation`

M0 负责提供因果的：

- 完整波浪；
- 尺度表示；
- 两个完整波形成的父结构；
- drift / overlap / width / efficiency / roughness / duration / density；
- publication time；
- streaming / replay / prefix 不被未来重写的保证；
- bar-support / offset / session 信息集语义。

M0 **不是最终交易策略**。

当前 morphology 全局状态仍为：

`morphology_replication_not_yet_accepted`

操作基线仍为 **v0.4.3**。旧 Direction/D1/D2/PAWCT、第三浪、收益/P&L、fresh OOS、paper trading、production 权限继续冻结。

## 2. M0 v0.6.17 并行任务仍有效

v0.6.17 authoritative-source formal replay 没有取消：

- DataHub bar-support provenance blocker 已解除；
- frozen preanalysis / protocol 已在 real-data result 前冻结；
- cloud Stage-1 preflight 已完成；
- authoritative-source formal replay 尚未闭合；
- `CL-20260908-005` 仍是 M0 的合法本地执行任务；
- 必须使用 accepted DataHub `349,923` row source surface，不能拿 FactorLab `350,561` row `1m_official` 冒充 exact source support。

M0 未闭合不阻止与 morphology acceptance 无关的 broad results-blind research；但任何需要“已接受形态学”的结论仍必须等 M0 自己闭合。

## 3. Broad program 的公共问题

“均值”不等于移动平均线。它可以是价格中心、震荡包络、父级波形结构、状态条件轨迹、统计分布、相对关系或某个统计属性的正常区域。

所有反转假说都必须先声明：

1. **Scale**：lower / current / parent；
2. **Parent state**：trend / range / transition / unknown；
3. **Deviation object**：到底什么发生了异常偏离；
4. **Recovery / failure**：什么算回归，什么算父状态改变。

核心判别问题：

> **眼前的反向运动只是父状态中的低一级 fluctuation，还是父级行情真正翻转的开始？**

## 4. 已完成的第一轮 R1 / R2 / R3 Stage-1

Evidence roles 已在结果前冻结：

- BUILD：2015-01-05..2018-12-31，已消费 development；
- chronological check：2019-01-01..2020-12-31，不是 fresh；
- post-2020：本轮未打开。

主视图与尺度也在 outcome 前通过结构供给冻结：

- primary view：`5m_offset_0`；
- parent representation：M0 birth level `L5`，sigma≈`2.828` bars；
- finer representation v1：`L3`，sigma≈`1.414` bars；
- 两级相差一个完整八度；
- parent/finer 都必须满足旧 v0.4.3 的 12–48 / 96 bar temporal maturity。

正式执行：GitHub Actions run `34188765085`。Direct cloud clone 在当前会话因 `github.com` DNS 失败，且没有可直接调用的本地模型工具，所以 Actions 是最后可用执行位置。

完整 receipt：

`docs/research/cloud_session_20260908_broad_rmr_stage1_R1_R2_R3_receipt_v1.json`

裁决：

`docs/research/reversal_mean_reversion_stage1_R1_R2_R3_adjudication_20260908.md`

### R1 — 趋势中的跨尺度回撤

状态：

`stage1_v1_evidence_insufficient_not_mechanism_rejected`

事件供给：

- BUILD resolved = `9`；
- 2019 = `5`；
- 2020 = `3`。

这不是“效果差”，而是事件定义过严。v1 同时要求：完整 L5 parent、完整 L3 two-wave 反向结构、L3 从 parent publication 后才开始、在 96bar parent validity 内发布、并且随后 first-passage 可解析。

结论：**不能据此否定“趋势中急跌/急涨只是低级别回撤”的机制。**

### R2 — 震荡边界 / 假突破

状态：

`stage1_v1_evidence_insufficient_and_small_sample_unstable`

事件供给：

- BUILD resolved = `37`；
- 2019 = `11`；
- 2020 = `10`。

小样本 pooled 有轻微改善，但 2020 方向不稳定且远低于预注册供给门，所以不能升级，也不能从这些小样本里挑参数。

### R3 — 结构衰竭 / 状态切换

状态：

`stage1_v1_closed_predeclared_direction_falsified`

供给充足：

- BUILD resolved = `744`；
- 2019 = `172`；
- 2020 = `144`。

`translation_decay` 和 `quality_decay` 都对 Brier/logloss 有很小的改善，但预注册要求“deterioration 越大 -> parent failure risk 越高”。实际 standardized coefficient 分别为：

- translation decay：`-0.04937`；
- quality decay：`-0.12734`。

负号与预注册科学方向相反。因此 **R3 v1 关闭**。不能因为指标变好就事后把负号解释成成功，也不能用 HMM/Koopman/deep model 救同一 identity。

## 5. 第一轮最重要的结构性结论

这轮明确区分了两种失败：

1. **R1/R2：event measurement / supply failure，不能当成 mechanism failure。**
2. **R3：样本充足，但预注册方向被证伪，是真正的 hypothesis failure。**

更重要的是，它揭示了 M0 的正确分工：

> **完整两波结构非常适合描述 parent state；但“突然偏离”不应该也被强迫等到另一套完整两波结构才确认。**

用户原始问题是“大级别趋势里突然出现一个极短时间反向冲击”。如果必须等低一级也形成两个完整波，事件已经太晚，而且样本被压得极少。

## 6. 当前授权的 M1 measurement revision

新身份：

`M1_parent_structure_plus_single_shock_event_adapter_v1`

它只修 R1/R2 的**lower deviation measurement**，不改 parent state，不用旧 v1 小样本表现挑参数。

### Parent 保持不变

- `5m_offset_0`；
- mature published L5 M0 structure；
- 同一 parent drift / overlap / efficiency / envelope / structural failure boundary；
- 同一 96bar parent validity 与年度 evidence censor；
- 不重新搜索 level / offset。

### R1 M1 — 单次 counter-shock

不再等待完整 L3 two-wave。

Parent publication 后维护 parent-direction running extreme；当 5m close 首次反向移动达到：

`0.5 × parent amplitude`

即触发 lower-scale shock。

`0.5` 不是从本轮结果调出来的：它来自旧 M0 v0.4.3 早已冻结的 `amplitude_ratio=2.0` 的 reciprocal lower bound。

然后仍然比较：

- recovery to pre-shock running extreme；
- parent structural failure boundary；
- parent integrity 是否在同样 shock severity 下提供增量信息。

### R2 M1 — 第一次 parent-envelope close excursion

不再等待完整 L3 two-wave。

Parent publication 后第一次 5m close 出现在 frozen parent envelope 外即触发：

- re-entry boundary = 原 envelope edge；
- continuation boundary = 与 outside distance 等距的同向扩展；
- parent range state 是否相对 raw excursion severity 提供增量信息。

R3 不进入 M1；R3 v1 已关闭。

## 7. 当前 next action

1. 冻结 M1 R1/R2 exact protocol / runner / tests；
2. 先检查 event supply；
3. 供给达到原预注册最低标准后，才执行 R1/R2 的 2015–2018 BUILD / 2019–2020 check；
4. 不改 parent L5、view、0.5 shock 常数、first-passage、日期或 gate；
5. 比较 R1/R2 M1 后，再决定是否有值得 dedicated deep identity 的方向；
6. 如果仍然没有方向通过，再考虑一个独立的 R4 statistical-state mechanism，而不是继续 post-hoc 修 R1/R2；
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
