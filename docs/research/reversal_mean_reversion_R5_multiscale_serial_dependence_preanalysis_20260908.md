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

本轮只使用 native 5m close-to-close log returns。只保留同一 trading_day 内、相邻 bar_end 相差恰好 5 分钟的连续转移；午休、隔夜、缺 bar transition 不构造 return，不填补。

这些有效 return 被分成 maximal exact-5m continuous segments。**任何 autocorrelation lag pair、12-bar parent drift 和未来 3-bar recovery 都不得跨 segment。**

## 3. 共同因果标准化

令有效连续 5m return 为：

`r_t = log(C_t/C_{t-1})`。

使用严格过去的 240 个已完成有效 return 做尺度：

- `sigma_t = sqrt(mean(r^2))`，不中心化；
- `z_t = r_t / sigma_{t-1}`；
- 当前 return 不进入自己的标准化尺度。

240-return volatility history 可以跨多个过去 segment 聚合，因为它只是过去波动尺度；但任何 lag product 仍必须发生在同一 exact-5m segment 内。

若过去有效 return 不足 240、尺度非有限或 <=0，该时点 unavailable。

所有 rolling state 在预测/事件时点都只使用当前时点之前已经完成的 z。

## 4. 冻结尺度

本轮只允许一组尺度，不做 span 搜索：

- state reference window：过去 960 个可用 z；
- short-memory lags：1..3 个 exact 5m steps；
- long-memory lags：12..18 个 exact 5m steps（约 60–90 分钟）。

早期草稿曾写 12..48；在任何 R5 outcome 打开前发现 48-step 会与午休/隔夜 exact-support 语义冲突，因此 results-blind 收紧为 12..18。这个修订只为保证所有 lag pair 都有真实连续 5m support，不是结果调参。

对每个 lag k，只在过去 960 个 z 中使用“两个端点属于同一 continuous segment”的 pair：

`rho_hat(k) = mean(z_i * z_{i-k}) / mean(z_i^2)`。

每个 lag 至少要求 100 个合法 pair；否则该 lag unavailable。short 或 long band 中只要有任何预定 lag unavailable，则对应 state unavailable，不临时删 lag。

由于 z 已做 causal volatility normalization，这里只作低容量 serial-dependence score，不声明严格 population ACF。

- `short_memory = mean(rho_hat(1..3))`
- `long_memory = mean(rho_hat(12..18))`
- `anti_persistence = -short_memory`
- `mixed_state = (short_memory < 0) and (long_memory > 0)`

没有 quantile search、favorable year/sign/time-of-day filter。

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

只使用 `t -> t+1` 仍位于同一 exact-5m segment 的 observation。

TRAIN 拟合，VALIDATION 原样复用参数。

Baseline B0：

`z_{t+1} = a + b*z_t`

Candidate B1：

`z_{t+1} = a + b*z_t + c*(z_t * anti_persistence_t)`

预注册方向：`c < 0`。含义：anti-persistence 越强，当前 return 对下一 return 的有效斜率应越向负方向移动。

Candidate B2 是唯一允许的多尺度升级，只在 B1 没有明确失败时解释：

`z_{t+1} = a + b*z_t + c1*(z_t*anti_persistence_t) + c2*(z_t*long_memory_t) + c3*(z_t*anti_persistence_t*long_memory_t)`

不加其它变量。

主要评价：VALIDATION pooled MSE。辅助：2019/2020 分年 MSE、系数方向、预测相关。VALIDATION 可以拆解诊断，因为它不是 BLACKBOX。

B1 是核心低容量机制。如果 VALIDATION pooled MSE 不优于 B0，且/或 `c>=0`，则不能因为 B2 某个局部分段好看而宣称“短期反持久机制成立”。

### R5-C — 慢趋势中的反向 shock 是否更容易短期恢复（策略原型层）

这是用户提出的“父级上涨中突然急跌，到底是次级回撤还是同级反转”的**非两浪、纯统计版本**。

Parent direction：当前 return 发生前、同一 continuous segment 中最近 12 个 z 的和 `parent_drift_12`。不足 12 个则事件 unavailable。

Shock severity：`abs(z_t)`。

事件 threshold 不根据 outcome 选择：在 TRAIN 的 `abs(z_t)` 边际分布固定 80% quantile `q80_abs_z`，之后对 TRAIN/VALIDATION 原样应用。

Counter-trend shock：

- `abs(z_t) >= q80_abs_z`
- `sign(z_t) == -sign(parent_drift_12)`
- `parent_drift_12 != 0`

Outcome：之后 3 个仍在同一 continuous segment 的 z 的累计方向恢复：

`recovery_15m = sign(parent_drift_12) * sum(z_{t+1:t+3})`

事件后 3 个 exact-5m returns 不完整则 unresolved；不跨午休/隔夜补齐。

比较两个 TRAIN-fit / VALIDATION-evaluate 低容量模型：

C0 severity-only：

`recovery_15m = a + b*abs(z_t)`

C1 state-aware：

`recovery_15m = a + b*abs(z_t) + d*long_memory_t + e*anti_persistence_t`

预注册方向：`d > 0`、`e > 0`。即：较慢正记忆越强、短期反持久越强，counter-trend shock 后回到 parent direction 的程度应越高。

主要评价：VALIDATION pooled MSE；辅助报告 mean recovery、positive-recovery fraction、2019/2020 分解。不报告 PnL。

最低 resolved supply：TRAIN >=150，VALIDATION pooled >=100。分年数量只做诊断，不作为机械 50/year gate。

## 6. 进阶规则

- R5-A supply 不足：整个 R5 identity 停止；
- R5-B B1 不支持：不升级 HMM/rSLDS/Koopman 去救 anti-persistence routing；
- R5-C state-aware 未超过 severity-only：不把 counter-trend pullback 解释成已支持；
- 至少一个核心机制在 VALIDATION 有清晰增量时，可继续在 TRAIN/VALIDATION 诊断和改进，但必须保留本轮 receipt；
- 只有候选成熟后才单独分配 BLACKBOX。

## 7. 禁止事项

- 不读取/占用任何 BLACKBOX；
- 不把 2019/2020 称 fresh OOS；
- 不做 PnL/Sharpe/交易成本；
- 不搜索 lag bands、960 state window、240 vol window、80% shock quantile；
- 不做 favorable sign/year/time-of-day 筛选；
- 不用未来收益选择 HMM state number；
- 不直接上 HMM/rSLDS/Koopman；
- 不把旧 R1/R2/R3/R4/T1 历史结论改写掉。

## 8. 本轮允许裁决

- `R5_multiscale_serial_dependence_supported_for_deeper_validation`
- `R5_partial_support_keep_researching_on_TRAIN_VALIDATION`
- `R5_state_supply_insufficient`
- `R5_low_capacity_mechanisms_not_supported`

任何正结论都仍只是 reusable TRAIN/VALIDATION evidence，不是 BLACKBOX confirmation，不是生产策略。
