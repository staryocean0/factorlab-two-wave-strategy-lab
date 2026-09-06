# v0.5.5 D1 父级震荡/趋势分类：只读语义归因协议

日期：2026-09-06  
状态：`result_before_code_readonly_attribution`  
上游冻结：**v0.5.2 TCSS exact-ridge parent identity + v0.5.4 full-cycle-scale qualification**

## 1. 研究问题

本轮不提出新的 D1 分类器，也不修改任何阈值。只回答：

> 当前冻结 D1 为什么会把 qualified two-wave records 分成 `range / uptrend / downtrend / uncertain`，尤其是大量 `uncertain` 到底是哪几类金融几何冲突或信息不足。

`uncertain` 不允许被默认解释为 `range`。

## 2. 冻结边界

本轮不得修改：

- TCSS representation；
- ridge linking / ridge death；
- exact five-ridge tuple / tuple birth；
- raw projection；
- v0.5.4 qualification；
- deterministic non-overlap ledger；
- confirmation / available-at clock；
- D1 原公式、原阈值、原 label；
- 任何收益、第三浪或未来结果。

只读取仓库既有 2015—2020 development 数据。

## 3. 当前 D1 的精确定义

对五个 raw extrema `P0..P4`，以两周期平均 detrended amplitude 为单位 `A`：

- `s0 = (P2-P0)/A`：起始同相位端点第一次迁移；
- `s1 = (P4-P2)/A`：同相位端点第二次迁移；
- `s2 = (P3-P1)/A`：另一相位包络端点迁移；
- `net = s0+s1 = (P4-P0)/A`。

冻结阈值：

- `phase_tolerance = 0.15`；
- `opposite_tolerance = 0.05`；
- `strong_drift = 0.50`。

冻结 D1：

1. `min(s0,s1,s2) > 0.15` -> `uptrend`；
2. `max(s0,s1,s2) < -0.15` -> `downtrend`；
3. 否则若 `abs(net)>0.5`，且按 net 方向至少两相 >0.15，同时没有任何一相反向超过 0.05 -> trend；
4. 否则若三相 `abs(si)<=0.15` 且 phase spans 小 -> `range`；
5. 其余 -> `uncertain`。

本轮必须验证 `range` 中 `phase_spans<=0.5` 是否在三相均小的条件下事实上冗余，而不能直接调大 0.15。

## 4. 新增的只读金融几何诊断

这些量只用于解释，不产生新 label。

### 4.1 同相位链与上下包络

保留：`s0 / s1 / s2 / net`。

若 P0 为 low：

- lower-envelope total drift = `net`；
- upper-envelope drift = `s2`。

若 P0 为 high：

- upper-envelope total drift = `net`；
- lower-envelope drift = `s2`。

进一步记录：

- `upper_minus_lower_drift`；
- 两条 envelope 是否同向；
- 同相位两步 `s0,s1` 是否同向。

### 4.2 父级中心漂移

定义仅作线性诊断：

`center_drift = 0.25*(s0+s1) + 0.5*s2`

它等价于比较两周期各自“同相位端点均值 + 对侧 apex”的 envelope center，不视为独立证据，也不用于本轮分类。

### 4.3 振幅 / 通道宽度变化

读取两周期既有 detrended amplitudes：

- `amplitude_change_fraction = (A2-A1)/mean(A1,A2)`；
- 绝对值与 D1 label / uncertain subtype 的关系。

### 4.4 时间 allocation

读取 v0.5.4 已降级为 diagnostic 的 corresponding-leg duration ratios：

- max corresponding-leg ratio；
- 与 D1 label / uncertain subtype 的关系。

它不得重新变成 same-scale hard gate。

### 4.5 归一化漂移速度

只读记录：

- `net / mean(cycle_duration)`；
- `center_drift / mean(cycle_duration)`。

不设阈值。

## 5. `uncertain` 的只读分型

对当前 D1=`uncertain`，按下列互斥优先级仅做 attribution：

1. `same_phase_reversal_conflict`：s0 与 s1 明确反号且二者都超过 phase tolerance；
2. `opposite_envelope_conflict`：net 与 s2 明确反号且二者都超过 phase tolerance；
3. `strong_net_with_opposed_phase`：abs(net)>0.5，但至少一相沿 net 反向超过 opposite tolerance；
4. `coherent_but_subthreshold`：三相总体方向一致/无明确反向，但达不到冻结 trend 强度门；
5. `single_phase_dominant`：只有一相明确迁移，其余相较小；
6. `large_migration_without_coherent_direction`：phase span / migration 大但没有一致父级方向；
7. `weak_mixed_migration`：其余弱混合状态。

这七类不是新分类结果，只是解释当前 `uncertain` 的组成。

## 6. 第一阶段正式输出：主 5m 只读归因

先只跑 `5m_offset_0`，对象同时分三层报告：

- 全部 v0.5.4 qualified records；
- v0.5.4 selected disjoint records；
- 当前 D1=`uncertain` 子集。

输出：

- D1 label counts / fractions；
- D1_reason counts；
- D0->D1 transition table；
- s0/s1/s2/net/center/envelope/amplitude/time-allocation/speed quantiles by label；
- uncertain subtype counts / quantiles；
- sign-pattern table；
- 到 0.15 / 0.05 / 0.50 三个冻结边界的距离分布；
- range 条件冗余性审计；
- 2018-06-20 / 2019-04-15 / 2020-07-15；
- legacy case_00/02/10/11/14 overlap audit。

固定窗口只用于解释，不用于发明阈值。

## 7. 晋级规则

本轮没有“模型通过”。完成主 5m attribution 后，只允许得出：

- 哪一种金融语义缺口是主要来源；
- 下一轮应该冻结哪一个**单组件** D1 假说；
- 或者现有证据不足，应继续只读诊断。

禁止根据 label balance、coverage 或任何未来收益把参数调到“看起来合理”。

只有下一轮新 D1 假说在代码前完成金融/数学 fit 预分析并冻结协议，才允许进入 main-5m mechanism audit；之后才是 multiview causal/stability adjudication。
