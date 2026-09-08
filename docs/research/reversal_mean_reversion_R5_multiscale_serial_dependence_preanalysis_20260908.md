# R5 — 多尺度序列依赖：趋势与均值回归共存的浅层研究预分析

日期：2026-09-08

Research identity：`R5_multiscale_serial_dependence_state_v1`

状态：`RESULTS BLIND / TRAIN+VALIDATION REUSABLE / NO BLACKBOX`

## 1. 动机

本轮不是旧 R1/R2/R3/R4/T1 的 rescue，也不依赖已接受 morphology。

独立理论入口来自 Sepp & Lucic (2026) 的 trend-following / autocorrelation 框架：收益过程可以同时具有**短期负自相关（均值回归）**与**较长尺度正记忆（趋势）**；因此“趋势还是反转”不应该被视为资产的永久二元属性，而应首先被视为**尺度相关的序列依赖状态**。

这与本仓广义问题一致：同一次短期反向运动，只有放进更慢尺度的状态坐标后，才可能判断它更像暂时波动还是状态改变。

本轮只做低容量统计机制筛选，不做交易 PnL，不上 HMM/rSLDS/Koopman。

## 2. 数据角色

按照 `reversal_mean_reversion_data_reuse_validation_policy_v1.md`：

- TRAIN：2015-01-05..2018-12-31，可反复研究/拟合/诊断；
- VALIDATION：2019-01-01..2020-12-31，可反复验证并拆细节；
- BLACKBOX：本轮不指定、不读取。

数据：`data/development/5m_offset_0.parquet`，CSI1000 `000852.SH`。

本轮只使用 native 5m close-to-close log returns。只保留同一 trading_day 内、相邻 bar_end 相差 5 分钟的连续转移；午休、隔夜、缺 bar transition 不构造 return，不填补。

## 3. 共同因果标准化

令原始连续 5m return 为 `r_t = log(C_t/C_{t-1})`。

使用严格过去窗口估计尺度：

- trailing volatility window = 240 个**已完成连续 return**；
- `sigma_t = sqrt(mean(r^2))`，不中心化；
- `z_t = r_t / sigma_{t-1}`；当前 return 不进入自己的标准化尺度。

若过去窗口不足、尺度非有限或 <=0，该时点 unavailable。

所有 rolling state 在预测/事件时点都只使用当前时点之前已经完成的 `z`。

## 4. 冻结尺度

为了直接对应“短期均值回归 + 较慢趋势记忆”，本轮只允许一组尺度，不做 span 搜索：

- state reference window：过去 960 个可用 z（约 20 个交易日的 5m observations）；
- short-memory lags：1..3；
- long-memory lags：12..48。

定义过去窗口内 lag-k normalized covariance：

`rho_hat(k) = mean(z_i * z_{i-k}) / mean(z_i^2)`。

由于 z 已做 causal volatility normalization，这里只作低容量 serial-dependence score，不声明严格 population ACF。

- `short_memory = mean(rho_hat(1..3))`
- `long_memory = mean(rho_hat(12..48))`
- `anti_persistence = -short_memory`
- `mixed_state = (short_memory < 0) and (long_memory > 0)`

没有 quantile search、没有 favorable year/sign/time-of-day filter。

## 5. 三个等预算问题

### R5-A — memory sign map（现象层）

只回答：

1. TRAIN 与 VALIDATION 中 short<0、long>0 的 mixed state 占比是否都非零且数量充分；
2. short_memory / long_memory 的符号结构是否跨 TRAIN/VALIDATION 保持可观察；
3. mixed state 是否具有超过单个 observation 的持续性。

这是描述性 phenomenon screen，不读取未来 outcome。

最低供给仅用于判断“值得继续测试”，不是 alpha gate：

- TRAIN mixed-state observations >= 500；
- VALIDATION mixed-state observations >= 200。

若不满足，R5 当前 identity 直接判 `state_supply_insufficient`，不调 lag/window。

### R5-B — anti-persistence 是否改变下一步反转强度（连续预测层）

在所有 candidate-available observations 上，用 TRAIN 拟合、VALIDATION 复用参数：

Baseline B0：

`z_{t+1} = a + b*z_t`

Candidate B1：

`z_{t+1} = a + b*z_t + c*(z_t * anti_persistence_t)`

预注册方向：`c < 0`。含义：anti-persistence 越强，当前 return 对下一 return 的有效斜率应越向负方向移动。

Candidate B2（唯一允许的多尺度升级，只有 B1 未明显失败时才解释）：

`z_{t+1} = a + b*z_t + c1*(z_t*anti_persistence_t) + c2*(z_t*long_memory_t) + c3*(z_t*anti_persistence_t*long_memory_t)`

不加其它变量。

主要评价：VALIDATION pooled MSE。辅助：2019/2020 分年 MSE、系数方向、预测相关。VALIDATION 可拆解诊断，因为它不是 BLACKBOX。

B1 作为核心低容量机制，如果 VALIDATION pooled MSE 不优于 B0，且/或 `c>=0`，则不因 B2 局部改善而宣称“短期反持久机制成立”。

### R5-C — 慢趋势中的反向 shock 是否更容易短期恢复（策略原型层）

这是对用户提出的“父级上涨中突然急跌，到底是次级回撤还是同级反转”的**非两浪、纯统计版本**。

Parent direction：当前时点之前 12 个连续 5m z 的和 `parent_drift_12`；只使用 past。

Shock severity：`abs(z_t)`。

事件 threshold 不根据 outcome 选择：在 TRAIN 的 `abs(z_t)` 边际分布上固定 80% quantile `q80_abs_z`，之后对 TRAIN/VALIDATION 原样应用。

Counter-trend shock：

- `abs(z_t) >= q80_abs_z`
- `sign(z_t) == -sign(parent_drift_12)`
- `parent_drift_12 != 0`

Outcome：之后 3 个**连续 5m returns**的累计方向恢复：

`recovery_15m = sign(parent_drift_12) * sum(z_{t+1:t+3})`

若事件后 3 个连续 bars 不完整，事件 unresolved；不跨午休/隔夜补齐。

比较两个 TRAIN-fit / VALIDATION-evaluate 低容量模型：

C0 severity-only：
`recovery_15m = a + b*abs(z_t)`

C1 state-aware：
`recovery_15m = a + b*abs(z_t) + d*long_memory_t + e*anti_persistence_t`

预注册方向：`d > 0`、`e > 0`。解释为：更强的较慢正记忆与更强短期反持久，都应提高 counter-trend shock 后回到 parent direction 的程度。

主要评价：VALIDATION pooled MSE；辅助报告 mean recovery、positive-recovery fraction、2019/2020 分解。不给 PnL。

最低 resolved supply：TRAIN >=150，VALIDATION pooled >=100。分年数量只做诊断，不作为机械 50/year gate。

## 6. 进阶规则

本轮的目标不是选一个交易参数，而是回答机制是否值得下一步。

- R5-A supply 不足：整个 R5 identity 停止；
- R5-B B1 不支持：不升级 HMM/rSLDS/Koopman 去救“anti-persistence routing”；
- R5-C 若 state-aware 没有超过 severity-only：不把 counter-trend pullback 解释成已支持；
- 若至少一个核心机制在 VALIDATION 有清晰增量，可继续在 TRAIN/VALIDATION 诊断和改进，但必须保留本轮 receipt；
- 只有候选成熟后才单独分配 BLACKBOX。

## 7. 禁止事项

- 不读取/占用任何 BLACKBOX；
- 不把 2019/2020 称 fresh OOS；
- 不做 PnL/Sharpe/交易成本；
- 不搜索 lag bands、960 window、240 vol window、80% shock quantile；
- 不做 favorable sign/year/time-of-day 筛选；
- 不用未来收益选择 HMM state number；
- 不直接上 HMM/rSLDS/Koopman；
- 不把旧 R1/R2/R3/R4/T1 的历史结论改写掉。

## 8. 本轮允许裁决

- `R5_multiscale_serial_dependence_supported_for_deeper_validation`
- `R5_partial_support_keep_researching_on_TRAIN_VALIDATION`
- `R5_state_supply_insufficient`
- `R5_low_capacity_mechanisms_not_supported`

任何正结论都仍只是 reusable TRAIN/VALIDATION evidence，不是 BLACKBOX confirmation，不是生产策略。
