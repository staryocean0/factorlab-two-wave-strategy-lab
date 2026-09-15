# R5-B1 anti-persistence interaction — specialist research handoff

日期：2026-09-15

Parent identity：`R5_multiscale_serial_dependence_state_v1`

Specialist research identity：`R5_B1_anti_persistence_interaction_specialist_v1`

Admission basis：`R5_B1_diagnostic_supported_for_specialist_research`

Cloud review：`docs/research/reversal_mean_reversion_R5_B1_stability_shape_diagnostic_cloud_review_20260915.md`

## 1. 为什么允许进入 specialist research

CL-008 已按 frozen protocol 完成：entry reproduction 通过，D1 day breadth = true，D2 mechanism shape = true。

当前证据只支持一个窄结论：在 R5 的固定 construction 下，`z_t × anti_persistence` interaction 对 next-5m normalized return 有一个很小、跨 2019/2020 且具有预注册形状的增量。

这不是交易策略，也不是 fresh OOS / BLACKBOX qualification。

## 2. specialist 第一阶段问题

只按以下顺序研究，不直接升级复杂 regime model：

1. **时间稳定性**：在 TRAIN / VALIDATION 内做预定义时间块描述，确认 interaction coefficient / empirical slope shape 是否持续，而不是由少数时期主导。时间块只用于稳定性诊断，不用于挑 favorable period。
2. **effect shape**：研究 anti-persistence 与 next-return slope 的连续形状、近似线性范围和可能的饱和区；不得用结果反向筛选交易时段或符号。
3. **transport**：有真实同步数据时，检查不同基础频率以及 CSI300 / CSI500 / CSI1000 的可迁移性。不同数据源必须保留各自 information-set semantics。
4. **经济映射**：只有前面机制仍稳定后，才研究是否存在有经济意义的可交易映射；不能用 PnL/Sharpe 反向选择早期机制定义。

## 3. 明确不做

- 不分配 BLACKBOX；
- 不读未经授权的 post-2020 数据；
- 不把 TRAIN / VALIDATION 叫 fresh OOS；
- 不把 `mixed_state = short<0 & long>0` 升级成稳定离散 regime classifier；
- 不用 HMM / rSLDS / Koopman 救或放大小增量；
- 不加入新的 lag/window/feature 搜索来追求更漂亮结果；
- 不筛 favorable day/month/sign/time；
- 不把 R5-C 的失败改写成成功；
- 不做 paper trading / production / Layer 4；
- 不修改 FactorLab current registry。

## 4. 数据治理

```text
TRAIN      = 2015-01-05..2018-12-31, reusable
VALIDATION = 2019-01-01..2020-12-31, reusable and diagnosable
BLACKBOX   = none_assigned
```

specialist 可以反复使用 TRAIN / VALIDATION 做模型诊断、时间稳定性和失败分析。只有模型、特征和评价体系明显成熟并再次冻结后，才讨论划出小段 never-seen BLACKBOX。

## 5. 必须保留的 parent construction

在任何 transport 研究之前，CSI1000/native-5m baseline 必须保持：

- exact-5m same-day continuous segment；午休/隔夜/gap 切断；
- 240-return causal volatility history；
- 960 valid normalized-return state history；
- short lags 1..3；
- long lags 12..18；
- anti_persistence = -short_memory；
- parent B0/B1 definitions 与 CL-007/CL-008 一致。

任何新 identity 若改变这些 construction，必须明确改名并重新冻结，不能冒充原 B1 的 replication。

## 6. 母仓职责

本 handoff 把 R5-B1 交给 specialist research lane，但不改变本仓的总角色。本仓继续作为广义反转 / 均值回归方向发现器，同时探索独立的 broad hypotheses；不得因为 B1 得到有限支持而把整个仓库锁死在 R5。

Production authority = false。
