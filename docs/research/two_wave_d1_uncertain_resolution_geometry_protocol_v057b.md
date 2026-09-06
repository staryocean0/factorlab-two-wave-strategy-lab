# v0.5.7b D1/D2 uncertain-resolution geometry attribution protocol（结果前冻结）

日期：2026-09-06  
状态：`read_only_stageB_geometry_protocol_frozen_no_new_classifier`

## 1. 触发条件与已知事实

v0.5.7a 已按事前规则完成 Stage A，并触发 `stageB_uncertain_resolution_instability`：

- v0.5.6 D2 已正式因 multiview label stability 被否定；
- D2 18/18 prefix causality PASS；
- D1/D2 selected IDs 与区间完全一致；
- 四个 native offset pooled `D2_harm=23,118` bars；
- 其中 shared D1=`uncertain` 为 `21,802` bars，占 `94.307%`；
- D2 同时产生 `17,793` help bars，因此 D2 不是纯损害，而是 uncertain resolution 的净收益不足以覆盖新增分歧。

本协议在任何 v0.5.7 新 classifier 之前冻结，只回答：

> 当 D1 在两个 native slicing 上都一致保留为 `uncertain` 时，D2 为什么会把同一父级区间解析成不同状态？这种差异主要是决策边界附近的 resolution-confidence 问题，还是远离边界仍发生的大幅 endpoint translation 不一致？

## 2. 绝对禁止

本阶段禁止：

- 修改 `phase_tolerance=0.15`；
- 修改 D1/D2 公式；
- 输出 D3/v0.5.7 新标签；
- 依据结果寻找新阈值；
- 修改 v0.5.2 parent identity 或 v0.5.4 qualification；
- 使用 future return、第三浪、H1/H2、P&L；
- 把 cross-offset agreement 当作准确率。

本阶段允许**重新构建完全冻结的 v0.5.6 full-view records**，但只能读取几何特征；不得用重建结果改变历史 pass/fail。

## 3. 冻结数据与对象

数据仍只用仓库供应：

- `000852.SH`
- `5m_offset_0..4`
- 2015-01-05 至 2020-12-31 development material
- `1m_official` 仅提供共同时间轴，不价格重采样。

正式 harm 对象由 v0.5.7a 的定义固定：

- main 与 other selected interval 在 1m 时间轴上有非空交集；
- D1 在交集上标签相同；
- D2 在交集上标签不同；
- 本 Stage B 主体只分析其中 shared D1=`uncertain` 的 record pairs / bars。

Stage A source：run `34010153423`，artifact `9982207960`。

## 4. 冻结几何量

对每个 main/other record 读取：

- `s0, s1, s2 = phase_steps_in_amplitude_units`
- `net = s0+s1`
- D2 `E_upper/E_lower`
- `phase`（low/high）
- `amplitude_unit`
- `cycle_durations`
- `leg_durations`
- `birth_scale_level / birth_sigma_bars`
- `five_occurrence_bars` 及对应 occurrence timestamps
- corresponding-leg duration diagnostic（若字段可直接取得则读取；否则由 leg durations 只读重算）

不创造新训练特征，不做拟合。

## 5. 决策边界距离（只读）

冻结 `t = phase_tolerance = 0.15`。

对任一 envelope drift `E` 定义到 D2 单轴决策边界的距离：

`d_boundary(E) = min(|E-t|, |E+t|)`

归一化：

`d_norm(E) = d_boundary(E) / t`

对一个 main/other harm pair 定义：

`pair_min_boundary_distance = min(d_boundary(E_upper/main), d_boundary(E_lower/main), d_boundary(E_upper/other), d_boundary(E_lower/other))`

并报告连续分布与以下**事前固定、仅用于诊断描述**的 bins：

- `very_near`: `d_norm <= 0.25`
- `near`: `0.25 < d_norm <= 0.50`
- `mid`: `0.50 < d_norm <= 1.00`
- `far`: `d_norm > 1.00`

这些 bins 不是参数搜索，也不是新 classifier threshold。

## 6. 符号与类别翻转

逐 pair 记录：

- upper envelope 是否 sign flip；
- lower envelope 是否 sign flip；
- `net` 是否 sign flip；
- D2 是否直接 `uptrend <-> downtrend`；
- 是否只发生 `uncertain <-> trend`；
- 是否涉及 `range`；
- phase low/high 是否一致。

同时将 sign flip 与 boundary-distance bins 交叉统计，尤其分离：

1. threshold-near flip；
2. large-margin sign flip；
3. direct up/down reversal。

## 7. `net=s0+s1` cancellation / endpoint sensitivity

为检验 whole-envelope net 是否因两个局部 same-phase steps 的抵消而放大 slicing 敏感性，定义：

`cancellation_index = 1 - |s0+s1| / (|s0|+|s1|)`，分母为 0 时记 0。

范围 `[0,1]`：越接近 1，s0/s1 越强烈互相抵消。

同时报告：

- `|Δs0|, |Δs1|, |Δs2|`
- `|Δnet|`
- `|Δnet| / max(|Δs0|, |Δs1|)`（分母 0 时按 0 处理）
- main/other cancellation index
- harm vs help vs both-agree 的分布对照。

这一步只做机制归因，不据此选择 cut-off。

## 8. endpoint / scale 辅助归因

按 bar-weighted 正式口径、record-pair 辅助口径分别报告：

- birth scale level / sigma
- mean cycle duration
- full-cycle duration ratio
- max corresponding-leg duration ratio
- occurrence endpoint timestamp displacement
- amplitude unit ratio（main/other）

目标是区分：

- threshold-margin 主导；
- endpoint selection / phase allocation 主导；
- coarse/fine scale 特定主导；
- 广泛结构性不稳定。

## 9. 事前冻结的路线判定

Stage B 不接受任何新 classifier，但为下一步路线预先固定三种结论：

### A. `confidence_gate_route_supported`

仅当以下两点同时成立时，才允许下一步研究“方向证据 + resolution confidence”单组件：

1. pooled shared-D1-uncertain harm 中，`very_near + near`（pair min boundary distance <= 0.5*t）占**至少 2/3**；
2. `far` 且发生任一 envelope sign flip 的 harm 占**不超过 10%**。

这里 2/3 与 10% 只是路线选择门，不是未来 classifier 参数。

### B. `endpoint_D2_route_rejected`

若任一成立：

- `far` harm 占 pooled shared-D1-uncertain harm **至少 25%**；或
- `far` 且任一 envelope sign flip 占 **超过 10%**；

则停止 endpoint whole-envelope D2 的直接分类路线。下一步只能研究使用整个两周期窗口的 robust parent-location / envelope estimator，不得调 0.15 复活 D2。

### C. `mixed_geometry_requires_more_attribution`

若 A、B 都不满足，则不创建 classifier，继续做几何/endpoint attribution。

### 路线优先级（结果前冻结）

若 A 与 B 的数值条件理论上同时成立，**B 优先**。原因是 B 表示已经存在不可忽略的 large-margin endpoint instability；不能因为同时存在大量 near-boundary 样本，就用 confidence gate 掩盖远离边界的结构性风险。

因此机械判定顺序固定为：`B -> A -> C`。

这些门在真实 Stage B 数字产生之前冻结。

## 10. 输出与状态

必须保存：

- source run/artifact 与代码 commit；
- frozen full-view rebuild identity checks；
- shared-D1-uncertain harm pair/bar 总量；
- boundary-distance 连续 quantiles 与 fixed bins；
- upper/lower/net sign flips；
- direct up/down reversals；
- cancellation / delta-step 分布；
- phase/scale/duration/amplitude/endpoint 辅助归因；
- harm/help/both-agree 对照；
- 按第 9 节机械得到的 next-route verdict。

状态固定为：

`read_only_uncertain_resolution_geometry_attribution_not_classifier_result`
