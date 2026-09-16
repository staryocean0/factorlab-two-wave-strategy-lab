# R7 × Layer2 5m risk-state alignment inventory

日期：2026-09-16

Identity：`R7_L2_5m_risk_state_alignment_inventory_v1`

状态：`OUTCOME_BLIND INVENTORY / LAYER2 READ-ONLY / NO BLACKBOX`

## 目标

在不读取 R7 `next5_z`、不拟合任何 R7 系数、不计算 PnL 的前提下，确认冻结 Layer2 5m 风险状态能否作为 R7 specialist 的外生状态桶。

本阶段只回答：

1. Layer3 `000852.SH` 2015–2020 official 5m endpoint 能否按冻结 V9 finalized-state 语义重放；
2. 与 Layer2 Phase-1 固定 canonical 5m 数据的唯一重叠年 2020 是否在 timestamp/close/state 上一致；
3. TRAIN、VALIDATION、2019、2020 各桶是否有足够候选供给，允许后续预注册 state-conditioned calibration 研究。

## 冻结 Layer2 语义

引用合同：`docs/governance/R7_layer2_5m_risk_state_reference_contract_v1.json`。

三态保持为 `NORMAL / UNSAFE / RECOVERING`。Primary consumer 两桶固定：

- `LOW_RISK = NORMAL`
- `RISK_ACTIVE = UNSAFE or RECOVERING`

这只是 Layer2 自身 risk-state 集合的固定合并，不允许按 R7 outcome 改阈值或重映射。

## 数据处理

- Layer3 source：`data/development/5m_offset_0.parquet`，SHA256 已冻结；
- Layer2 canonical overlap source：`factorlab-trend-reversion-regime-lab@1d760ea.../data/market/5m/000852.SH/2020.parquet`；
- 5m finalized state 只使用 close history；
- 每个交易日必须恰好 48 根 5m bar 才进入 replay；异常日整日标为 unavailable，不填充、不重采样；
- state 每日从 NORMAL 开始，volatility history 按冻结 V9 定义使用 valid 5m returns；
- 2020 external-vs-Layer3 比较只看共同完整日与共同 timestamp。

## Inventory gates

Alignment 可接受仅当：

- Layer3 source SHA 正确、symbol 唯一为 `000852.SH`、max day <= 2020-12-31；
- 2020 external overlap 的共同 timestamp close 最大绝对差 <= `1e-12`；
- 2020 在共同 timestamp 上 replayed `risk_state` agreement = 100%；
- R7 candidate timestamp 可匹配 replayed state 的比例 >= 99%；
- TRAIN、VALIDATION、2019、2020 每组 `RISK_ACTIVE` candidate >= 500；
- TRAIN、VALIDATION、2019、2020 每组 `LOW_RISK` candidate >= 5000；
- 不读取 `next5_z`、不拟合 R7 model、不计算 PnL/Sharpe。

如果供给不足，只允许停止或重新设计独立研究问题；不允许降低阈值去追 outcome。

## 下一阶段（仅 inventory 通过后）

冻结 `R7_L2_5m_risk_bucket_calibration_diagnostic_v1`，检验外生 risk bucket 是否解释 R7 calibration drift。先检验异质性与 out-of-sample fixed TRAIN state-conditioned coefficients，再讨论任何桶内 calibration rule；不直接做参数网格搜索。
