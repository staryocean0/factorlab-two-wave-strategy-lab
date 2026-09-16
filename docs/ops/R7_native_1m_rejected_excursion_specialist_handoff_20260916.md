# R7 native-1m rejected excursion — specialist handoff

日期：2026-09-16

Specialist identity：`R7_native_1m_rejected_excursion_specialist_v1`

Parent identity：`R7_native_1m_rejected_excursion_v1`

Diagnostic identity：`R7_rejected_excursion_stability_shape_diagnostic_v1`

状态：`AUTHORIZED WITHOUT BLACKBOX`

## 1. 为什么进入 specialist

R7 broad screen 先通过：

- TRAIN/VALIDATION/2019/2020 rejection coefficient 均为负；
- fixed TRAIN B1 在 VALIDATION、2019、2020 都改善；
- pooled directional symmetry 通过。

随后唯一一次 bounded diagnostic 再通过：

- D1 fixed half-year stability = true；
- D2 TRAIN-fixed rejection-magnitude shape = true；
- adjudication = `R7_diagnostic_supported_for_specialist_research`。

因此允许从 broad discovery 移交 specialist，但不等于策略成功、fresh OOS 或 BLACKBOX qualification。

## 2. Specialist 必须保留的 parent identity

必须保持：

- source 仍是 official 1m + official 5m endpoint timestamp identity；
- exact same-day 1m continuity；
- past path = 5 native 1m returns；
- forward outcome = next 5 native 1m returns；
- sigma = previous 240 exact-1m returns RMS with shift(1)；
- B0 = endpoint displacement only；
- B1 = B0 + continuous `rejection_signed_z`；
- no M0 structural cache；
- no R5-B1 anti-persistence；
- no local resampling。

改变这些定义必须生成新 identity，不能借用 R7 当前验证资格。

## 3. Specialist 第一阶段优先级

第一阶段不继续搜 feature，而是做 inferential/transport readiness：

1. **day-clustered uncertainty**：对 frozen B1 rejection coefficient、VALIDATION MSE improvement、day-level improvement breadth 做按 trading day 聚类的不确定性描述；不改变模型，不据此挑日子。
2. **calibration / residual sufficiency**：检查 B1 residual 是否仍系统性依赖 endpoint displacement 或 rejection magnitude；只允许预注册连续诊断，不用 threshold rescue。
3. **cross-market transport only when authorized data exists**：优先 CSI300/CSI500/CSI1000/STAR50 的真实 official/native 1m transport，但必须先取得对应仓库数据治理授权并冻结 source identity。
4. **economic mapping later**：只有机制/transport 仍稳定后，才允许单独设计交易可行性研究；PnL/Sharpe 不能反向决定本机制是否成立。

## 4. 当前禁止事项

不得：

- 分配或读取 BLACKBOX；
- 读取 post-2020；
- 按结果选 favorable year / half-year / direction / time-of-day / magnitude threshold；
- 搜 path length、forward horizon、sigma window；
- 新增 volume/high-low/order-book 特征后仍称为同一 R7；
- 用 HMM/rSLDS/Koopman rescue；
- paper trading / production / Layer4；
- FactorLab registry mutation。

## 5. 母仓职责

R7 specialist 与母仓 broad discovery 分离：

- specialist 负责 R7 的稳定性、可迁移性与后续经济映射；
- 母仓继续寻找与 R7 不同源的新低容量 reversal/mean-reversion mechanism；
- specialist 不应吞噬 broad discovery 预算。

## 6. BLACKBOX

`BLACKBOX_assigned = false`

只有 specialist model/features/evaluation 进一步成熟并再次冻结后，才讨论一个小型 never-seen BLACKBOX qualification。

Production authority=false。
