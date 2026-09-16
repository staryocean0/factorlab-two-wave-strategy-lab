# R7 specialist Stage 1 — calibration-drift handoff

日期：2026-09-16

Parent specialist：`R7_native_1m_rejected_excursion_specialist_v1`

Stage 1：`R7_specialist_stage1_inferential_readiness_v1`

Stage 1 adjudication：`R7_specialist_stage1_inferentially_supported_calibration_drift`

## 1. 结论

R7 mechanism 保留：day-clustered rejection coefficient 在 TRAIN、VALIDATION、2019、2020 的 95% CI 均完全低于 0；frozen TRAIN-fit B1 的日级 MSE improvement 在 2019/2020 都有正 bootstrap lower bound、正 median、>50% positive days。

但 frozen TRAIN coefficients 不允许直接 transport：VALIDATION/2019/2020 的 calibration slope 均约 0.80，CI 不含 1；B1 residual 对 endpoint 和 rejection 仍有显著线性依赖。

## 2. 下一阶段唯一合理目标

下一阶段不是 feature search，而是 `R7_calibration_strategy_readiness_v1`：研究一个事前冻结、低自由度、只改变 coefficient updating rule 的 calibration strategy。

设计原则：

- parent features、path=5、forward=5、sigma=240 全部固定；
- calibration 只能使用过去数据，不能使用待预测期；
- 不搜索时间窗口、half-life、threshold 或 favorable subperiod；
- 先用 TRAIN 内部固定 calendar forward-chaining 选择/验证一个极简 updating rule；
- VALIDATION 只能作为 reusable diagnostic，不能被称为 fresh OOS；
- 若 calibration rule 需要在 VALIDATION 上调超参，则它只能继续作为研究材料，不能获得 transport qualification。

优先候选不是复杂模型，而是单一低容量方案，例如：固定 expanding OLS calibration of the same B1 coefficients with a predeclared minimum history and update cadence。具体规则必须在下一次 outcome 前另行冻结。

## 3. 暂不允许

- fixed TRAIN coefficients transport；
- 直接用 2019/2020 full-period local coefficients 替换 parent；
- 搜 rolling window / decay / regularization / feature interaction；
- 按 day/year/time/sign/magnitude 选择 calibration；
- BLACKBOX 或 post-2020；
- PnL/Sharpe model selection；
- HMM/rSLDS/Koopman；
- paper trading / production。

## 4. 跨市场 transport

Mechanism transport 仍可作为平行方向，但必须先取得目标数据源的明确研究授权。跨市场测试必须区分：

1. mechanism sign/shape transport；
2. coefficient calibration transport。

当前不得因为 mechanism 稳定就假设原系数可直接搬运。

## 5. BLACKBOX

`BLACKBOX_assigned = false`

在 calibration strategy 与 transport protocol 成熟并再次冻结前，不讨论 never-seen qualification。

Production authority=false。
