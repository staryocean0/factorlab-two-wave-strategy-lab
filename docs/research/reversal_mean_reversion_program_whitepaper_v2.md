# 广义反转与均值回归研究白皮书 v2（2026-09-08 修订）

项目：`broad_reversal_mean_reversion_discovery_program_v1`

## 1. 项目定位

本仓库不是单一“两浪策略仓”，也不是开盘跳空专题仓。

仓库级任务是：

> **发现和比较广义反转 / 均值回归机制，研究在不同尺度和父级状态下，一个异常偏离究竟是暂时波动，还是状态本身已经改变。**

“均值”可以是价格中心、动态区间、趋势轨迹、父级结构、状态条件分布、跨资产相对关系或统计属性的正常区域。

两浪体系归入 `M0_two_wave_structure_measurement_foundation`：提供因果多尺度结构坐标，不自动提供交易 alpha。

## 2. 数据治理：数据是长期研究资产

项目不采用“每验证一次就烧掉一段历史”的做法。

- **TRAIN**：`2015-01-05..2018-12-31`，可以反复训练、调研、拆案例、诊断失败和修改模型。
- **VALIDATION**：`2019-01-01..2020-12-31`，可以反复做时间稳定性检验，也可以拆年份、事件和状态做诊断，再继续迭代。
- **BLACKBOX**：当前不分配。只有候选足够成熟时才划一小段尚未打开的数据做 aggregate-only 最终确认。

如果 BLACKBOX 后来被打开细节，它降级为 VALIDATION；数据仍然可用，只是不再具有“从未看过”的资格。

> **数据本身不是消耗品；只有 never-seen BLACKBOX qualification 是稀缺的。**

权威政策：`docs/governance/reversal_mean_reversion_data_reuse_validation_policy_v1.md`。

## 3. M0 当前状态

v0.6.17 authoritative-source replay 已完成云端独立复核。

接受 verdict：`session_aware_bounds_valid_but_structural_gap_nonidentifiability_is_material`。

接受能力：`interval_valued_session_aware_path_information_bounds`。

native 5m OHLC 不足以天然确定 fine path。以后 path efficiency / roughness / concentration 等细路径量必须明确属于：真实 finer-source 直接测量、fully-enveloped finite interval、或 structural-gap partial-identification interval。

这不是 morphology acceptance。当前 morphology 仍 `morphology_replication_not_yet_accepted`，operational baseline 仍 v0.4.3。

## 4. 历史 broad research 的正确解释

- **R1**：旧 identity 因旧样本门 `unresolved`，不是机制被否定；允许继续在 TRAIN / VALIDATION 研究新 identity，不能追溯改写旧 receipt。
- **R2**：旧 M1 低容量 identity 在充分样本下没有增量，历史 identity closed；独立的新 range-reversion 机制仍可研究。
- **R3**：旧 v1 预注册方向被证伪，历史 identity closed；独立的新 transition 机制仍可研究。
- **R4**：旧 v1 三个 candidate 均无稳定增量。重要教训：统计属性自己回归，不等于价格必然均值回归。
- **T1**：旧 5-sigma / 960-bar identity 在 outcome 前因旧 supply gate 关闭；不代表所有 shock-reversion 研究永久禁止。

这些结论是 identity-level evidence，不会“耗掉”底层数据。

## 5. 当前 active：R5 多尺度序列依赖

Identity：`R5_multiscale_serial_dependence_state_v1`。

独立理论基础来自 trend-following / autocorrelation 文献：**短期负自相关与较慢尺度正记忆可以同时存在。** 因此市场不是简单的“趋势/震荡”永久二选一，反转和趋势可能在不同尺度同时成立。

R5 不依赖 M0 morphology acceptance，也不是旧 R1 参数 rescue。

### R5-A：memory sign map

研究 short lags 1..3 与 slower lags 12..18 的符号状态，先确认 `short<0 & slower>0` 是否有足够供给和持续性。

### R5-B：anti-persistence routing

用低容量 OLS 检验短期 anti-persistence 是否稳定让当前 5m return 对下一 5m return 的有效斜率更负。

简单交互不成立，不允许直接用 HMM/rSLDS/Koopman 救。

### R5-C：慢趋势里的反向 shock

纯统计地研究：一段较慢方向运动之后，突然出现反方向 5m shock；在较慢正记忆与短期 anti-persistence 更强时，随后 15m 是否更容易回到原方向。

事件阈值只由 TRAIN 的 `abs(z)` 80% quantile 决定，不按 outcome 搜索。

## 6. R5 时间与数据合同

使用 `data/development/5m_offset_0.parquet`，CSI1000 `000852.SH`，70,114 rows。

只构造同一 trading day 内、bar_end 相差恰好 5 分钟的 close-to-close log return。午休、隔夜和缺 bar 都切断 continuous segment：autocorrelation lag pair、parent drift、future 15m recovery 均不得跨 segment。

冻结参数：

- causal volatility history = 240 valid returns；
- state history = 960 valid z；
- short lags = 1..3；
- slower lags = 12..18；
- each lag minimum pair count = 100；
- shock threshold = TRAIN 80% quantile of `abs(z)`。

## 7. 当前执行状态

R5 的 preanalysis、protocol、runner、tests 和 execution freeze 已全部写入。

本地任务：`CL-20260908-007`。

Handoff：`docs/ops/cl_20260908_007_R5_multiscale_serial_dependence_handoff.md`。

当前云端已实际尝试 raw-GitHub direct execution，DNS 解析失败；因此真实 Parquet run 由本地模型执行，GitHub Actions 未授权。

本地顺序：先跑冻结的 7 个 synthetic tests，再执行一次 TRAIN/VALIDATION runner，推 compact receipt。云端收到后独立验收。

## 8. 为什么不直接上状态模型

用户提供的 HMM / rSLDS / Koopman 框架很重要，但合理阶梯是：

1. 先证明简单 serial-dependence / state interaction 有稳定增量；
2. 再研究离散 regime routing；
3. 简单 regime 有价值后才考虑 rSLDS；
4. 再之后才讨论 Switching-Koopman。

否则复杂模型只是扩大同一数据上的研究自由度。

## 9. BLACKBOX 的使用时机

R5 即使 VALIDATION 表现不错，也不会立即分配 BLACKBOX。

先允许 TRAIN 反复建模、VALIDATION 反复拆解、机制修订和时间稳定性诊断。只有模型形式、阈值、特征预算和评价指标趋于稳定后，才分配一个小 BLACKBOX，默认只读 aggregate pass/fail。

## 10. 新数据的作用

新数据不是因为旧数据“用完了”。它主要用于扩展不同市场状态、增加稀有事件、提高 1m/3s/tick 细路径质量、加入 CSI300/500/1000 或横截面机制，以及最终给成熟候选留一小段 BLACKBOX。

## 11. 权限边界

当前不授权：TRAIN/VALIDATION 上的 fresh-OOS 宣称、PnL/Sharpe 驱动的研究选择、paper trading、production、FactorLab registry mutation、用 native OHLC 假装 fine path 已知、outcome 后 favorable direction/year/time filter。

Production authority = `false`。
