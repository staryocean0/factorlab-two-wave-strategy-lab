# CONTINUE HERE — 广义反转 / 均值回归研究入口（2026-09-08）

**本文件是判断本仓库“现在研究什么、下一步做什么”的第一权威。**

仓库级任务：

> **用因果、多尺度、低容量的研究框架发现广义反转 / 均值回归机制；核心不是“跌多了就买”，而是判断眼前偏离属于完整父状态里的次级波动，还是父状态本身已经改变。**

当前总状态：

`R5_MULTISCALE_SERIAL_DEPENDENCE_FROZEN_LOCAL_EXECUTION_PENDING_UNDER_REUSABLE_TRAIN_VALIDATION_POLICY`

## 1. 数据治理：数据不是消耗品

当前采用三层角色。

### TRAIN

`2015-01-05..2018-12-31`

可反复用于训练、特征设计、参数估计、事件拆解、失败分析和模型修改。

### VALIDATION

`2019-01-01..2020-12-31`

可反复用于跨时期验证，也允许打开年份/事件/案例细节做诊断，并根据诊断继续改模型。

### BLACKBOX

当前**没有分配**。

只有当某个候选已经比较成熟时，才从尚未打开的新数据里划一小段 aggregate-only final confirmation reserve。若之后为了诊断打开 BLACKBOX 细节，该段自动降级成 VALIDATION；数据仍然可用，只是不再具有“从未看过”的资格。

所以：

> **可重复研究的数据不会被烧掉；真正稀缺的只有 never-seen BLACKBOX qualification。**

权威数据政策：

`docs/governance/reversal_mean_reversion_data_reuse_validation_policy_v1.md`

## 2. M0：两浪只是测量底座

历史 v0.4.3–v0.6.17 两浪工作继续保留为：

`M0_two_wave_structure_measurement_foundation`

它提供因果 complete wave、parent structure、scale、drift / overlap / width / efficiency / roughness / duration / density、publication time 和 session/source support 语义。

M0 **不是自动成立的 alpha**。

当前：

- operational baseline = `v0.4.3`
- morphology = `morphology_replication_not_yet_accepted`
- CL-20260908-005 = `CLOUD REVIEWED / COMPLETED`
- v0.6.17 accepted capability = `interval_valued_session_aware_path_information_bounds`

v0.6.17 的硬结论：native 5m OHLC 不能被默认当作已知 fine path。细路径特征必须声明 direct finer-source measurement、fully-enveloped finite interval 或 structural-gap partial identification。

云端 review：

`docs/research/two_wave_session_aware_information_set_bounds_cloud_review_20260908.md`

## 3. 历史 broad lanes 仍是历史证据，不限制数据复用

### R1 — Cross-scale pullback

旧 identity 的结论是 `unresolved`，不是 rejected；当时的 old gate 下 resolved supply 为 `168 / 40 / 39`。

**现在允许继续用 TRAIN / VALIDATION 研究 R1 或其独立新 identity。** 不能做的是把旧结论追溯改写成成功/失败，或把 TRAIN/VALIDATION 叫 fresh。

### R2 — Range-boundary reversion

旧 M1 identity 在 adequate supply 下表现变差，历史 identity closed。可以研究独立的新 range-reversion 机制，但不能改写旧结果。

### R3 — Structural exhaustion

旧 v1 preregistered direction 被证伪，历史 identity closed。可以研究独立的新 transition 机制，但不能把旧负号反解释成成功。

### R4 — Statistical-state extremes

旧 v1 三个 candidate 都没有增量，历史 identity closed。其它独立 statistical-state 问题仍可研究。

### T1 — Extreme-shock transitory component

旧 `5-sigma / 960-bar` identity 在 outcome 前因旧 supply gate 关闭；CL-006 已 cloud-reviewed。这个历史结果保留，但不表示所有 shock-reversion 研究永久禁止。

## 4. 当前正在执行：R5 多尺度序列依赖

Identity：

`R5_multiscale_serial_dependence_state_v1`

它来自独立理论，而不是旧 lane rescue：Sepp & Lucic 的 autocorrelation / long-memory 框架明确允许**短期负自相关与较慢正记忆同时存在**。因此“趋势”和“均值回归”可能在不同尺度同时成立。

本轮只用同一 native `5m_offset_0` 数据，先做三个低容量问题：

1. **R5-A memory sign map**：短期负记忆、较慢正记忆的 mixed state 是否真实存在且有足够供给；
2. **R5-B anti-persistence routing**：短期反持久程度是否稳定增强下一步反转；
3. **R5-C counter-trend shock**：较慢正记忆状态里，反向 5m shock 是否更容易在随后 15m 回到原 parent direction。

冻结尺度：

- causal volatility history = 240 valid 5m returns；
- state history = 960 valid z；
- short lags = 1..3 exact 5m steps；
- slower lags = 12..18 exact 5m steps；
- lag pair / parent drift / future recovery 都不能跨午休、隔夜或其它非 exact-5m segment；
- shock threshold = TRAIN `abs(z)` 80% quantile；
- 不搜索 lag/window/quantile。

本轮不做 HMM/rSLDS/Koopman，不做 PnL。

冻结文件：

- `docs/research/reversal_mean_reversion_R5_multiscale_serial_dependence_preanalysis_20260908.md`
- `docs/governance/reversal_mean_reversion_R5_multiscale_serial_dependence_protocol_v1.json`
- `docs/governance/reversal_mean_reversion_R5_execution_freeze_v1.json`
- `scripts/run_broad_rmr_R5_multiscale_serial_dependence.py`
- `tests/unit/test_broad_rmr_R5_multiscale_serial_dependence.py`

## 5. 当前执行任务：CL-20260908-007

当前云端已实际尝试 direct raw-GitHub execution surface，DNS 解析失败，因此真实 Parquet run 交给本地模型，而不是 GitHub Actions。

Handoff：

`docs/ops/cl_20260908_007_R5_multiscale_serial_dependence_handoff.md`

本地顺序：

```bash
pytest -q tests/unit/test_broad_rmr_R5_multiscale_serial_dependence.py
```

期望 7 passed；通过后：

```bash
python scripts/run_broad_rmr_R5_multiscale_serial_dependence.py \
  --output docs/research/local_broad_rmr_R5_multiscale_serial_dependence_receipt_v1.json
```

只需 `[skip ci]` 推 compact receipt；大数据不推。

本地结果只能叫 `local_reported`。云端收到 receipt 后必须先核对 frozen blobs、source SHA、R5-A supply gate、B1→B2 顺序、C sample gate 和 BLACKBOX/PnL flags，再改成 `cloud_reviewed`。

## 6. R5 后续规则

- R5-A state supply 不够：当前 identity 停止，不改 lag/window 救；
- R5-B 核心 B1 不支持：不直接升级 HMM/rSLDS/Koopman 去救；
- R5-C state-aware 不优于 severity-only：不宣称“趋势中的回撤均值回归成立”；
- 若 R5 有 partial/full support，可以继续在**同一 TRAIN / VALIDATION**上拆细节、改模型、重新验证；这是合法研究，不需要新数据续命；
- 只有候选成熟后才分配小 BLACKBOX。

## 7. 下一批新数据的作用

新数据不是因为旧数据“用完了”。它主要用来：

- 扩展牛/熊/震荡/高低波动状态覆盖；
- 增加稀有 shock/event 样本；
- 提供 CSI300/500/1000 同步比较；
- 提供更完整 1m/3s/tick fine path；
- 最后给成熟候选留一小段 BLACKBOX。

## 8. Authority order

上下文压缩或新助手接管时：

1. `CONTINUE_HERE.md`
2. `docs/governance/reversal_mean_reversion_program_charter_v1.json`
3. `docs/governance/reversal_mean_reversion_data_reuse_validation_policy_v1.md`
4. `docs/governance/reversal_mean_reversion_program_state_v1.json`
5. `docs/research/reversal_mean_reversion_program_whitepaper_v2.md`
6. `AGENTS.md`
7. 当前 lane protocols / cloud reviews
8. 历史 v0.x 文档只在对应 identity 内有效

## 9. 权限边界

仍然禁止：

- 把 TRAIN/VALIDATION 称 fresh OOS；
- 当前阶段用 PnL/Sharpe 挑研究模型；
- Layer 4 / paper trading / production；
- FactorLab current registry mutation；
- 用 native OHLC 伪造 fine path；
- outcome 后有利分方向/年份/时段筛选。

Production authority = `false`。
