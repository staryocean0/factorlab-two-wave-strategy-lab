# v0.5.6 D1 whole-envelope translation：金融/数学适配预分析

日期：2026-09-06  
状态：`preanalysis_before_v056_protocol_and_results`

冻结上游：**v0.5.2 TCSS exact-ridge parent identity + v0.5.4 full-cycle-scale qualification**。

输入证据：v0.5.5 只读 attribution；本文件在任何 v0.5.6 真实分类结果之前冻结概念边界。

## 1. 金融问题不是“每个局部子步是否单调”

目标始终是：两个连续、完整、同尺度 raw-price reversal cycles 构成的父级状态，是：

- 上涨趋势；
- 下跌趋势；
- 震荡 / 非趋势；
- 或证据冲突、不足而 uncertain。

对低点起算：

`L0 -> H1 -> L1 -> H2 -> L2`

父级几何天然有两条 envelope：

- lower envelope：`L0, L1, L2`
- upper envelope：`H1, H2`

高点起算完全对称。

经典技术分析对趋势的基本定义就是 higher highs + higher lows / lower highs + lower lows。CFA Institute 的 Technical Analysis refresher 明确把 uptrend 定义为 successive higher highs and higher lows，把 downtrend 定义为 successive lower highs and lower lows。

这与本研究的金融目标一致：**父级 direction 应由 upper/lower envelope 的整体迁移决定。**

## 2. 当前 D1 的职责混叠

冻结 D1 使用：

- `s0=(P2-P0)/A`
- `s1=(P4-P2)/A`
- `s2=(P3-P1)/A`

其中：

- `s0/s1` 是同一条 envelope 上的两个连续局部子步；
- `s2` 是另一条 envelope 的完整一步。

于是当前 D1 实际要求一个有三点的 envelope 提供两个独立 directional votes，而另一个只有两个点的 envelope 只提供一个 vote。

这会把：

`lower envelope: up then down, but L2 still above L0`

与：

`upper envelope: H2 above H1`

这种“父级两条边界整体都上移，但中间 lower anchor 有局部回返”的结构判为 uncertain。

v0.5.5 已确认这是主失败模式：371 个 qualified uncertain 中 243 个是 s0/s1 明确反号；其中 136 个上下 envelope 总迁移已经同向且都越过原 0.15。

所以问题不是阈值微调，而是**局部 path shape 与 parent translation 被赋予了同一 hard-vote 权力。**

## 3. v0.5.6 的第一性状态变量

仍使用冻结 amplitude unit `A`，不引入新归一化参数。

定义：

`E_same = (P4-P0)/A = s0+s1`

`E_other = (P3-P1)/A = s2`

映射到 upper/lower：

### low-start

- `E_lower = E_same`
- `E_upper = E_other`

### high-start

- `E_upper = E_same`
- `E_lower = E_other`

无论起始相位，价格方向的符号保持一致：两条都正表示两条 envelope 向上迁移，两条都负表示向下迁移。

## 4. 为什么首轮不做时间 slope normalization

可以定义每 bar slope，但首轮不推荐。

理由：

1. v0.5.4 已先验保证两个完整 cycle 属于同一时间尺度资格：cycle duration 有固定范围且 ratio<=2；
2. D1 的问题是父级状态 direction / range，不是速度预测；
3. 原 D1 的 0.15 本来就是 displacement / amplitude 单位，若改成 per-bar slope 就必须重新定义阈值，混入第二个组件；
4. 用户目标是判断两个完整波构成的父级 trend vs range，完整波结束后的 envelope displacement 是更直接的状态变量。

因此首轮保持 displacement/amplitude 语义与旧阈值完全一致。

`net / mean_cycle_duration` 等 slope 继续只作 diagnostic。

## 5. 为什么 `P2` 大幅偏移后回归，不自动否定 range

一个潜在反例：

- `L0` 与 `L2` 接近；
- `H1` 与 `H2` 接近；
- 但中间 `L1` 有大幅位移。

若研究目标是“稳定水平通道”，这可能需要额外 curvature / width 约束。

但当前金融合同是更上一级的 **trend vs oscillatory/range state**，不是“恒定宽度矩形通道”。

在两个完整波的观察窗内：

- 两条父 envelope 首末都没有持续迁移；
- 同一 envelope 中间先偏移再回归；

本质上恰好是“缺乏持续单向父级漂移”的证据。

因此首轮允许它成为 range candidate；`s0/s1 reversal magnitude`、amplitude change、upper-lower width change 继续保留为 morphology diagnostics，未来如果要细分：

- stationary range
- expanding / contracting range
- triangle / wedge
- irregular oscillation

应另开子状态，不应把这些形状先全部塞进 `uncertain` 来代替父级 trend/range 判断。

## 6. 单组件最小公式

首轮唯一 hard-decision 变化：

使用原冻结：

`phase_tolerance = 0.15`

定义：

### uptrend

`E_upper > 0.15 and E_lower > 0.15`

### downtrend

`E_upper < -0.15 and E_lower < -0.15`

### range

`abs(E_upper) <= 0.15 and abs(E_lower) <= 0.15`

### uncertain

其余情况：

- 一条明确上、一条明确下；
- 一条明确迁移，另一条尚不明确；
- 其它 envelope evidence mixed。

不保留旧 `strong_drift=0.5 + two-of-three + opposite_tolerance=0.05` 作为 v0.5.6 hard fallback；否则局部 s0/s1 voting 会通过侧门重新进入 parent decision。

0.5 与 0.05 仍保留为 legacy diagnostic，不删除历史证据。

## 7. `s0/s1` 不删除，只降级职责

v0.5.6 继续记录：

- same-phase reversal conflict；
- s0/s1 最大局部 excursion；
- P2 相对 P0/P4 的 curvature；
- corresponding-leg duration allocation；
- amplitude change；
- width / envelope divergence。

这些描述“父状态内部怎么走”，而不是“父状态往哪里整体迁移”。

这是 direction 与 channel/morphology 的职责分离。

## 8. 结果前 synthetic 金融语义门

正式协议必须包含至少：

1. parallel higher-high + higher-low -> uptrend；
2. parallel lower-high + lower-low -> downtrend；
3. 两条 envelope 首末稳定 -> range；
4. lower path 先反向再恢复，但 upper/lower 总体都上移 -> uptrend；
5. upper/lower 一上一下 -> uncertain；
6. 只有一条 envelope 明确迁移 -> uncertain；
7. 原 D0 反例 `[-0.2335,-0.2639,-0.3512]` 仍必须为 downtrend；
8. low-start/high-start 对称；
9. 对价格平移与正比例缩放不改变分类；
10. append future 不改已 confirmed record classification。

## 9. main-5m 机制审计不能用什么判通过

禁止用：

- range 数量变多；
- uncertain 数量变少；
- 类别看起来更均衡；
- coverage；
- 收益 / 第三浪表现。

只能检查：

1. parent candidate identity 完全不变；
2. v0.5.4 qualification 完全不变；
3. selected intervals / ledger 完全不变；
4. 变化只来自 D1 decision basis；
5. synthetic semantics 全过；
6. 旧 D0 明确反例不回归；
7. fixed windows / legacy cases 只解释变化，不用于修改 0.15；
8. future outcome / trade authority 仍 false。

## 10. multiview 后续门

只有 main5m 机制审计通过后才允许：

- 五个 native 5m full + 25/50/75% prefix；
- 1m official causal diagnostic；
- selected interval IoU 应与冻结上游完全相同，因为 D1 不重排 ledger；
- 重点新增审计应是**重叠区间上的 D1 label agreement / envelope-state agreement**是否不系统性恶化。

在独立 morphology acceptance 前仍不得进入 H1/H2、returns、trading。
