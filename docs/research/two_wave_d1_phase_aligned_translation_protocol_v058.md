# v0.5.8 PAWCT phase-aligned whole-cycle translation — POC protocol（结果前冻结）

日期：2026-09-06  
状态：`representation_poc_protocol_frozen_no_parent_classifier`

## 1. 研究问题

v0.5.7b 已按结果前冻结规则判定：

> `endpoint_D2_route_rejected`

这只判死“exact endpoint whole-envelope displacement 直接输出 parent hard state”路线，不判死整个 D1。

v0.5.8 首个问题严格限制为：

> **将两个完整 raw reversal cycles 进行固定两-leg phase alignment 后，使用 whole-path paired translation 的 robust location，能否得到比 endpoint D2 更 slicing-stable 的连续 parent translation representation？**

本 POC 不输出最终 `range/uptrend/downtrend/uncertain`，不引入 confidence gate。

## 2. 冻结上游

完全冻结：

- v0.5.2 TCSS exact-ridge parent identity
- v0.5.4 full-cycle-scale qualification
- raw projection
- deterministic ledger
- confirmation clock
- D1/D2 历史输出

必须复用 v0.5.6 formal selected IDs/intervals 作 exact identity audit。

## 3. PAWCT 固定定义

对任一 selected pair 的 raw occurrence bars：

`i0 < i1 < i2 < i3 < i4`

第一个完整 cycle：`i0 -> i1 -> i2`  
第二个完整 cycle：`i2 -> i3 -> i4`

low-start / high-start 使用同一数学操作；phase 只决定金融解释，不改变算法。

### 3.1 两-leg phase coordinate

每个 cycle 分成两条 leg：

- leg A：same-kind start -> opposite extremum，映射到 `u∈[0,1]`
- leg B：opposite extremum -> same-kind end，映射到 `u∈[1,2]`

每条 leg 内使用 **bar-order** 坐标线性映射，不使用 wall-clock gap。

### 3.2 fixed phase grid

为近似连续 piecewise-linear raw path 的 phase-uniform location，固定：

- 每条 leg `65` 个包含端点的等距 phase samples；
- 合并时共享 `u=1` 只保留一次；
- 总 grid size = `129`。

`65` 只作为数值积分/分位近似分辨率，**本研究不搜索 grid size**。

### 3.3 interpolation

在每个 leg 的实际 raw close sequence 上作线性插值到固定 phase grid。

不使用：

- DTW
- spline
- future bars
- smoothing bandwidth
- filter residual

### 3.4 paired translation

得到：

`C1(u_j), C2(u_j)`

定义：

`Δ_j = C2(u_j) - C1(u_j)`

robust parent-location representation：

`T_raw = median_j(Δ_j)`

归一化：

`T = T_raw / amplitude_unit_price`

其中 `amplitude_unit_price` 必须直接复用冻结 record 的同一口径。

辅助诊断，但**不参与本轮 pass/fail classifier**：

- `MAD_Δ = median(|Δ_j - T_raw|) / amplitude_unit_price`
- phase-grid 正/负/近零 share
- first/second leg 各自 median translation

## 4. 为什么本轮不用阈值分类

v0.5.7b 已证明 hard threshold 会把连续几何差异放大成 categorical instability。

因此本轮只测试 `T` 本身是否成为更稳健的 parent location representation。

`phase_tolerance=0.15` 只允许用于**事前固定的大幅 sign-flip diagnostic**：

> large-margin scalar sign flip = main/other `T` 符号相反，且两者 `|T| > 2*0.15 = 0.30`。

`0.30` 不是新 classifier threshold，只是与 v0.5.7b `far` 概念对齐的诊断边界。

## 5. synthetic hard gates

在任何真实结果前，PAWCT 必须通过：

1. **pure translation**：两个相同 piecewise-linear cycles，C2=C1+d，恢复 `T_raw=d`；
2. **phase allocation invariance**：两周期上涨/下跌腿 bar 数不同，但 phase-normalized shape 相同且 d=0，恢复 T≈0；
3. **translation + phase allocation**：bar 数不同且 C2=C1+d，恢复 d；
4. **single endpoint contamination robustness**：只污染一个 raw endpoint，whole-path median 不得被污染值同量级拖走；
5. low/high start 数学对称；
6. no NaN/inf；
7. 不存在 complete two-wave record 时 PAWCT 无权单独发布结构。

## 6. real-data identity hard gates

在 `5m_offset_0..4`：

- rebuild frozen v0.5.6 selected records；
- selected `record_id/start_time/end_time` 必须与 formal v0.5.6 artifacts 逐条 exact match；
- PAWCT 不得改变 qualification/selection；
- `future_outcome_used=false`
- `trade_authority=false`

任一失败，POC 无效。

## 7. 跨 offset pair 口径

完全复用 v0.5.7a/v0.5.7b 的 matched selected-overlap pair 定义与 1m bar weights；不重新寻找 correspondence。

保留四类：

- both_agree
- D2_harm
- D2_help
- both_disagree

特别报告：shared-D1-uncertain D2-harm（21,802 bars frozen reference）。

## 8. 事前冻结的 representation viability gates

本 POC 不晋级 classifier，只决定 PAWCT 是否值得进入下一轮 D1 direction/confidence 研究。

### Gate R1 — large-margin sign stability

在 pooled shared-D1-uncertain D2-harm 上：

- PAWCT large-margin scalar sign-flip fraction 必须 **<5%**。

理由：v0.5.7b endpoint D2 的 far+signflip 为 10.187%；若 whole-path estimator 连一半级别的改善都做不到，不值得继续。

### Gate R2 — stable controls 不得明显破坏

在 pooled D2-help 与 both-agree 两组分别：

- PAWCT large-margin scalar sign-flip fraction 必须各自 **<=5%**。

### Gate R3 — continuous pair dispersion 必须改善 endpoint-D2

对每个 matched pair 定义：

`D_endpoint = max(|ΔE_upper|, |ΔE_lower|)`

`D_PAWCT = |T_main - T_other|`

在 pooled shared-D1-uncertain D2-harm 上，bar-weighted median 必须：

`median(D_PAWCT) < median(D_endpoint)`

这只是同一 frozen normalized geometry 下的 representation stability 对比。

### Gate R4 — 不得靠删除困难样本

- matched pair/bar counts 必须与 v0.5.7b exact match；
- 不允许过滤 near/far、phase mismatch、scale mismatch 或 duration mismatch 后再计算 gates。

### 判定

只有 R1–R4 全 PASS：

`PAWCT_representation_candidate_pass`

否则：

`PAWCT_representation_candidate_fail`

失败后不得调 grid size、median 改 trimmed mean、过滤 endpoint cases 来救本轮；若仍认为 whole-window 路线合理，必须另立竞争 estimator 协议。

## 9. 必须保存的 diagnostics

按 pooled + per-offset 保存：

- T / MAD / per-leg median quantiles
- `|T_main-T_other|`
- endpoint D2 max-delta comparator
- large-margin scalar sign flips
- ordinary sign flips（仅 diagnostic）
- T sign agreement
- harm/help/both-agree 分组
- phase match/mismatch
- birth scale delta
- endpoint timestamp displacement
- cancellation index 对照

不得据此事后增加 pass 条件。

## 10. prefix causality

PAWCT 只读取已 confirmed frozen record span 内 raw bars，理论上继承上游 causal confirmation；但若本轮 R1–R4 PASS，下一正式方向实验仍必须重新做 prefix replay，不能仅靠理论声明。

本 POC 本身复用 v0.5.6 18/18 causal evidence，不把 PAWCT 发布为正式 classifier。

## 11. 后续路线

- 若 `PAWCT_representation_candidate_pass`：下一步才做金融/数学 preanalysis，决定如何从连续 T 与 dispersion 分离 `direction evidence` 和 `resolution confidence`；
- 若 FAIL：停止 PAWCT median，比较 P1 robust drift regression 或重新审视 cross-view parent correspondence；
- 无论哪种，都不进入 H1/H2、收益或交易。
