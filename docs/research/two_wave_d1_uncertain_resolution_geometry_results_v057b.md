# v0.5.7b D1/D2 uncertain-resolution geometry attribution — formal result

日期：2026-09-06  
最终状态：`endpoint_D2_route_rejected`  
研究层级：只读 D1/D2 稳健性归因；**不是新 classifier 结果**

## 1. 目的

v0.5.6 D2 whole-envelope translation 在主 `5m_offset_0` 的金融语义与 18/18 prefix causality 均通过，但在四个 native 5m offset 上 label agreement 全部低于 D1。

v0.5.7a 进一步证明，D2 新制造的 `23,118` harm bars 中，`21,802`（94.307%）来自 main/other D1 原本都一致为 `uncertain` 的区间。因此 Stage B 的问题被冻结为：

> D2 对这些 stable-uncertain 的过度解析，主要只是靠近 `±0.15` 决策边界，还是即使远离边界仍发生 endpoint translation 的符号/类别翻转？

结果前协议：

`docs/research/two_wave_d1_uncertain_resolution_geometry_protocol_v057b.md`

协议在真实 Stage B 数字产生前冻结，并明确路线优先级 `B -> A -> C`。

## 2. 执行证据

正式 run：`34010814782`  
job：`101426200482`  
execution commit：`d1524ad005783649c546c135d9e8b263e21c8a59`

正式 artifact：

- id：`9982490147`
- name：`two-wave-d1-uncertain-resolution-geometry-v057b-d1524ad005783649c546c135d9e8b263e21c8a59`
- SHA256：`a68e5d643bb388406d9574c991d17bf05705051e911a35f406011924f9f19335`

工程/因果保护：

- full pytest regression：PASS
- 五个 native 5m frozen v0.5.6 full-view rebuild：PASS
- rebuilt selected record IDs / start/end intervals 与正式 v0.5.6 artifacts：五视图逐条 exact match
- v0.5.7a Stage-A per-view / pooled four-way counts：exact match
- 未改变 parent / qualification / ledger / D1 / D2 formula / `phase_tolerance=0.15`
- `future_outcome_used=false`
- `trade_authority=false`

因此本结果只描述已冻结 D2 的几何失稳机制。

## 3. 结果前冻结的 route gates

`t=0.15`。

对每个 envelope drift：

`d_boundary(E)=min(|E-t|, |E+t|)`

`d_norm=d_boundary/t`

pair 使用 main/other 两条 envelope 共四个值中的最小 boundary distance。

固定诊断 bins：

- very_near：`d_norm<=0.25`
- near：`0.25<d_norm<=0.50`
- mid：`0.50<d_norm<=1.00`
- far：`d_norm>1.00`

事前路线门：

- A `confidence_gate_route_supported`：near+very-near >= 2/3，且 far+任一 envelope sign flip <=10%
- B `endpoint_D2_route_rejected`：far >=25%，**或** far+任一 envelope sign flip >10%
- C：其余继续 attribution
- 若 A/B 同时成立，**B 优先**。

## 4. 主体样本

pooled shared-D1-uncertain D2-harm：

- record pairs：`194`
- bar-weight：`21,802`

这与 v0.5.7a frozen Stage-A `21,802` bars 完全一致。

## 5. Boundary-distance 结果

| bin | bars | fraction |
|---|---:|---:|
| very_near | 9,503 | 43.588% |
| near | 4,223 | 19.370% |
| mid | 5,855 | 26.855% |
| far | 2,221 | 10.187% |

因此：

- near + very_near = `13,726 / 21,802 = 62.958%`
- 未达到结果前 A 门要求的 `>= 2/3`
- far = `10.187%`，本身没有达到 B 门的 `>=25%`

boundary-distance 的 bar-weighted quantiles：

- p25 `d_norm=0.111`
- p50 `0.303`
- p75 `0.627`
- p90 `1.049`
- p99 `1.867`
- max `3.927`

所以大多数 harm 确实接近决策边界，但不能把失败简化为“只差一个 confidence margin”。

## 6. 决定路线的关键：far sign flip

shared-D1-uncertain harm 全体：

- upper envelope sign flip：`9,699` bars（44.487%）
- lower envelope sign flip：`8,818`（40.446%）
- 任一 envelope sign flip：`13,587`（62.320%）
- `net=s0+s1` sign flip：`7,237`（33.194%）
- direct `uptrend <-> downtrend`：`2,652`（12.164%）
- `uncertain <-> trend`：`15,745`（72.218%）
- range involved：`3,405`（15.618%）

更关键的是：

- `far` bars = `2,221`
- `far + any envelope sign flip` bars = **`2,221`**
- fraction of target = **`10.1871%`**

也就是 **所有 far harm 都伴随至少一条完整 envelope 的符号翻转**。

结果前 B 门规定 `far + sign flip >10%` 即判 endpoint-D2 直接分类路线失败；实际 `10.1871%`，机械触发 B。

因此正式 verdict：

> **`endpoint_D2_route_rejected`**

这不是因为阈值挑选，也不是事后解释；10% 门和 B>A>C 优先级都在 Stage B 数字产生前写入协议。

## 7. 为什么不能把 D2 只加 confidence gate 复活

若只是 boundary-near instability，则应看到：

- near/very-near 占绝对主导；
- far 区域 sign 稳定；
- confidence gate 可以只保守化临界样本。

实际并非如此：

1. near+very-near 只有 62.958%，低于 2/3 的事前要求；
2. far 虽只有 10.187%，但其中 100% 发生 envelope sign flip；
3. 全体 harm 的任一-envelope sign flip 达 62.32%；
4. direct up/down reversal 仍有 12.16%。

因此“保留 endpoint-D2 方向、只增加 margin gate”会掩盖一部分真正的 endpoint/identity sensitivity。

v0.5.6 仍保持正式 reject，不能通过调 `0.15`、另找 confidence cutoff、删掉 multiview hard gate 或按收益选参复活。

## 8. 机制线索：cancellation 与几何差异

harm 的 bar-weighted `max_cancellation_index`：

- p25 `0.498`
- p50 `0.753`
- p75 `0.899`
- p90 `0.945`

相比 both-agree：

- p25 `0`
- p50 `0`
- p75 `0.459`
- p90 `0.772`

说明 D2-harm 强烈富集在 `s0/s1` 互相抵消的共享相位路径中；`net=s0+s1` 虽是 endpoint total drift，但它所代表的方向在 slicing 改变后容易被 endpoint allocation 改写。

同时 harm 的 `|Δnet|`：

- median `0.388`
- p75 `1.151`
- p90 `2.158`

而 both-agree：

- median `0.102`
- p75 `0.241`
- p90 `0.559`

所以问题并非仅由一个很小的 `±0.15` 数值扰动造成。

## 9. endpoint / scale 线索

harm 与 both-agree 相比还表现出更大的跨 slicing 几何重定位：

### amplitude-unit ratio

- harm median `1.145`；p90 `1.629`
- both-agree median `1.050`；p90 `1.196`

### birth scale level delta

- harm median `1` level；p90 `2`
- both-agree median `0`；p90 `1`

### occurrence endpoint displacement

`max occurrence timestamp abs delta`：

- harm median `1206` minutes；p90 `4072`
- both-agree median `7` minutes；p90 `1214`

first/last endpoint displacement 的 harm median 也约 `67/68` minutes，而 both-agree 仅约 `3/2` minutes。

这些统计不证明某一项单独是因果根源，但明确说明 D2-harm 不只是分类边界问题：在不少 pair 上，两个 native 5m slicing 对“对应父波的五个 exact extrema”发生了实质性的 endpoint/scale 重定位。

## 10. D2 仍有真实 help，但不足以保留该直接分类路线

v0.5.7a 已证明 D2-help = `17,793` bars。

Stage B comparator 显示 help 的 boundary distance 反而通常很大：

- far = 70.590%
- any envelope sign flip 仅 3.383%

其 D2 标签主要是稳定的：

- `uptrend -> uptrend` 10,447 bars
- `downtrend -> downtrend` 5,342
- `uncertain -> uncertain` 2,004

所以 whole-envelope translation 确实捕捉到了一部分有价值的父级方向语义；问题不是它“毫无信息”，而是 **exact endpoint displacement 作为最终 hard classifier 的表示不够 slicing-invariant**。

这一区分决定下一步不能简单回滚 D1，也不能直接保留 D2。

## 11. 下一安全路线

按结果前协议，下一步只能进入：

> **whole-window robust parent-location / envelope estimator 的金融与数学预分析**

目标不是再找一个 D2 threshold，而是寻找一个在已经冻结的两周期 span 内，使用**整段结构**而非少数 exact endpoint 差值估计父级平移/漂移的状态变量。

必须满足：

- 不修改 v0.5.2 parent identity；
- 不修改 v0.5.4 qualification；
- 不使用 alternate offsets 作为生产输入；offset 仍只作稳健性验收；
- 不使用未来 outcome；
- 先金融语义/数学 fit，再冻结单组件 protocol；
- 新 estimator 必须在 main mechanism、prefix causality、native-offset stability 三层重新验收。

在 preanalysis 完成前，不创建 v0.5.8 classifier。

## 12. 当前状态链

**v0.5.2 parent identity ✅ → v0.5.4 qualification ✅ → v0.5.5 D1 attribution ✅ → v0.5.6 endpoint D2 main/causal ✅ but multiview ❌ → v0.5.7a harm attribution ✅ → v0.5.7b endpoint-D2 direct route ❌ → robust whole-window parent estimator preanalysis next。**

整个 morphology 仍未验收；PR #1 保持 Draft；不进入 H1/H2、收益或交易。
