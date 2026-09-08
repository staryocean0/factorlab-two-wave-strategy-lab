# 广义反转与均值回归研究白皮书 v2（2026-09-08 修订）

项目：`broad_reversal_mean_reversion_discovery_program_v1`

## 1. 项目定位

本仓库不是单一“两浪策略仓”，也不是开盘跳空专题仓。

仓库级任务是：

> **发现和比较广义反转 / 均值回归机制，研究在不同尺度和父级状态下，一个异常偏离究竟是暂时波动，还是状态本身已经改变。**

“均值”可以是价格中心、动态区间、趋势轨迹、父级结构、状态条件分布、跨资产相对关系或统计属性的正常区域。

两浪体系归入：

`M0_two_wave_structure_measurement_foundation`

M0 提供因果多尺度结构坐标，不自动提供交易 alpha。

## 2. 数据治理：数据是长期研究资产

项目不采用“每验证一次就烧掉一段历史”的做法。

### TRAIN

当前 `2015-01-05..2018-12-31`。

可以反复训练、调研、拆案例、诊断失败和修改模型。

### VALIDATION

当前 `2019-01-01..2020-12-31`。

可以反复做时间稳定性检验，也可以在失败后拆年份、事件和状态做诊断，再回到 TRAIN/VALIDATION 继续迭代。

### BLACKBOX

当前不分配。

只有候选足够成熟时，才划一小段尚未打开的数据做 aggregate-only 最终确认。若之后打开细节，这段数据降级成 VALIDATION，而不是“报废”。

因此：

> **数据本身不是消耗品；只有 never-seen BLACKBOX qualification 是稀缺的。**

旧的 `consumed / not fresh` 标签只说明它不能再被包装成第一次独立确认，不代表不能继续研究。

## 3. M0 当前状态

v0.6.17 authoritative-source replay 已完成云端独立复核。

接受 verdict：

`session_aware_bounds_valid_but_structural_gap_nonidentifiability_is_material`

接受能力：

`interval_valued_session_aware_path_information_bounds`

关键含义：native 5m OHLC 不足以天然确定 fine path。以后 path efficiency / roughness / concentration 等细路径量必须明确属于：

1. 真实 finer-source 直接测量；
2. fully-enveloped finite interval；
3. structural-gap partial-identification interval。

这不是 morphology acceptance。当前 morphology 仍 `morphology_replication_not_yet_accepted`，operational baseline 仍 v0.4.3。

## 4. 第一轮 broad research 的历史结论

### R1：趋势中的次级回撤

旧 identity 因旧年度样本门而 `unresolved`，不是机制被否定。它可以继续在 TRAIN / VALIDATION 上以新的、明确身份研究；只是不能追溯改写旧 receipt，也不能把 2019/2020 称 fresh。

### R2：震荡边界回归

旧 M1 低容量 identity 在充分样本下没有提供增量，历史 identity closed。未来可以提出真正独立的新 range-reversion 机制。

### R3：结构衰竭

旧 v1 的预注册方向被证伪，历史 identity closed。未来可以研究新的 transition 机制，但不能把旧负号重新讲成成功。

### R4：统计状态极端

旧 v1 三个 candidate 均无稳定增量。其重要教训仍然是：

> **统计属性自己回归，不等于价格必然均值回归。**

### T1：极端冲击暂时性成分

旧 5-sigma / 960-bar identity 在 outcome 前因旧 supply gate 关闭。这个结论保留，但不代表所有 shock-reversion 研究永久禁止。

## 5. 当前新方向：R5 多尺度序列依赖

当前 active identity：

`R5_multiscale_serial_dependence_state_v1`

独立理论基础来自 trend-following / autocorrelation 文献：**短期负自相关与较慢尺度正记忆可以同时存在。** 因此市场并不是简单地“现在趋势”或“现在震荡”二选一；更合理的问题是：不同尺度上的序列依赖符号是否不同，以及这种状态是否帮助判断短期反向波动。

R5 不依赖 M0 morphology acceptance，也不是旧 R1 的参数 rescue。

### R5-A：多尺度 memory sign map

用 causal normalized 5m returns 研究：

- short lags 1..3 是否为负；
- slower lags 12..18 是否为正；
- `short<0 & slower>0` mixed state 是否有足够供给和持续性。

### R5-B：局部 anti-persistence

检验短期 anti-persistence 是否稳定让当前 5m return 对下一 5m return 的斜率更负。

先用低容量 OLS；简单交互不成立，不允许直接用 HMM/rSLDS/Koopman 救。

### R5-C：慢趋势里的反向 shock

这是用户提出的核心场景的纯统计版本：

> 一段较慢方向运动之后，突然出现一个反方向 5m shock；在较慢正记忆与短期 anti-persistence 更强时，随后 15m 是否更容易回到原方向？

事件阈值只由 TRAIN 的 `abs(z)` 80% quantile 决定，不按 outcome 搜索。

## 6. R5 数据和时间语义

使用：

`data/development/5m_offset_0.parquet`

CSI1000 `000852.SH`，70,114 rows。

只构造同一 trading day 内、bar_end 相差恰好 5 分钟的 close-to-close log return。

午休、隔夜和缺 bar 都切断 continuous segment：

- autocorrelation lag pair 不跨 segment；
- parent drift 不跨 segment；
- future 15m recovery 不跨 segment。

冻结参数：

- causal volatility history = 240 valid returns；
- state history = 960 valid z；
- short lags = 1..3；
- slower lags = 12..18；
- each lag minimum pair count = 100；
- shock threshold = TRAIN 80% quantile of `abs(z)`。

## 7. 为什么现在不直接上状态模型

用户提供的多状态 / rSLDS / Koopman 文献非常重要，但本仓当前不应该跳到最复杂层。

正确阶梯是：

1. 先证明简单的 serial-dependence / state interaction 有稳定增量；
2. 再研究离散 regime routing；
3. 只有简单 regime 有价值时，才考虑 rSLDS；
4. 再之后才讨论 Switching-Koopman。

否则复杂模型只是在同一数据上扩大自由度。

## 8. 当前执行状态

R5 的 preanalysis、protocol、runner、tests 和 execution freeze 已全部写入。

本地任务：

`CL-20260908-007`

Handoff：

`docs/ops/cl_20260908_007_R5_multiscale_serial_dependence_handoff.md`

当前云端已实际尝试 raw-GitHub direct execution，DNS 解析失败，因此真实 Parquet run 由本地模型执行；GitHub Actions 未授权。

本地只需要跑冻结的 7 个 synthetic tests 和一次 TRAIN/VALIDATION runner，推 compact receipt。云端收到后再独立验收。

## 9. BLACKBOX 的使用时机

R5 即使在 VALIDATION 表现不错，也不会立刻吃掉一段黑箱。

先允许：

- TRAIN 反复建模；
- VALIDATION 反复拆解；
- 机制修订；
- 多年份稳定性诊断。

只有当模型形式、阈值、特征预算、评价指标都趋于稳定，才分配一个小 BLACKBOX，且默认只读取 aggregate pass/fail。

## 10. 权限边界

当前不授权：

- TRAIN/VALIDATION 上的 fresh-OOS 宣称；
- PnL/Sharpe 驱动的研究选择；
- paper trading；
- production；
- FactorLab registry mutation；
- 用 native OHLC 假装 fine path 已知；
- outcome 后的 favorable direction/year/time filter。

Production authority = `false`。
