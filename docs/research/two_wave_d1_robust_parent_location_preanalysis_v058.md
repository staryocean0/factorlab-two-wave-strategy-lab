# v0.5.8 D1 robust whole-window parent-location estimator — 金融/数学预分析（代码前）

日期：2026-09-06  
状态：`preanalysis_only_no_classifier_no_real_result`

## 1. 为什么必须换表示，而不是调 v0.5.6

冻结证据链：

- v0.5.2 exact-ridge parent identity：通过；
- v0.5.4 full-cycle-scale qualification：通过；
- v0.5.5：旧 D1 的大量 uncertain 来自局部 same-phase step 冲突；
- v0.5.6：whole-envelope endpoint translation 在主视图语义合理、18/18 causal PASS，但 multiview label stability 四项全部下降；
- v0.5.7a：94.3% 的 D2 harm 来自 D1 原本在两个 slicing 上都稳定为 uncertain；
- v0.5.7b：`endpoint_D2_route_rejected`。

v0.5.7b 的关键不是 `far` 比例高，而是：

- shared-D1-uncertain harm 的 far 仅 10.187%；
- 但 **所有 far harm 都发生至少一条 envelope sign flip**；
- `far + sign flip = 10.187% > 10%`，触发事前冻结死亡门；
- harm 的 max cancellation index median 0.753；
- harm 的 `|Δnet|` median 0.388，显著高于 both-agree 的 0.102；
- harm 的 endpoint/scale 重定位也明显更大。

所以失败不是单纯“0.15 附近需要 buffer”，而是：

> **以少数 exact extrema endpoint displacement 直接承担父级 hard state 的责任，对 native bar slicing 过敏。**

下一步必须用整个两周期 span 的信息估计父级 location/translation，而不是继续给 endpoint D2 加阈值。

## 2. 金融语义重新表述

已经冻结的五点只负责确认：

1. 两个连续完整 raw-price reversal cycles 存在；
2. 两周期属于同一 parent family / same-scale qualification。

D1 需要回答的不是“某几个端点是否逐点抬高”，而是：

> **第二个完整周期相对于第一个完整周期，整个 raw-price oscillatory structure 的中心位置是否发生稳定向上/向下平移？**

设第一个周期为 `C1`，第二个为 `C2`。若能在相同波动相位 `u` 上比较两条曲线：

`Δ(u) = C2(u) - C1(u)`

那么：

- range：`Δ(u)` 的整体 location 接近 0，允许局部正负摆动；
- uptrend：`Δ(u)` 的稳健 location 明显 >0；
- downtrend：明显 <0；
- uncertain：不同相位的 translation evidence 冲突，或 location 相对不确定度不足。

这比 D1/D2 更直接表达“父级整体漂移”。

## 3. 必须满足的 estimator 性质

任何候选 estimator 必须同时满足：

### 3.1 raw-price 语义

只估计原价格两周期之间的父级平移；不得由 detrended residual 自行产生趋势。

### 3.2 使用整段结构

不能只依赖 L0/L1/L2 或 H1/H2 的 endpoint difference。单个 extrema 可以定义 cycle/phase anchors，但最终 location estimate 必须由 span 内多点共同决定。

### 3.3 phase-allocation 鲁棒

v0.5.4 已证明对应半浪时长不应定义 same-scale。新 estimator 不能因为第一周期上涨腿 5 bars、第二周期上涨腿 15 bars 就把速度差误认为不同 parent state。

### 3.4 bar-slicing 鲁棒

5m offset 改变时，少数 endpoint 可以移动，但若 underlying parent structure 相同，估计量应尽量保持符号与相对量级。

### 3.5 causal

第二周期最后一个 extremum 被确认后，只能使用当时已经出现的 bars。append future 不得改写 confirmed estimate。

### 3.6 不把 uncertainty 消灭

若两周期在不同相位上给出相反 parent translation，必须允许 uncertain；不能为了提升 coverage 强行 majority vote。

## 4. 候选方法比较

### P0：Phase-Aligned Whole-Cycle Translation（PAWCT）

**核心思想**：分别把两个完整 reversal cycles 映射到统一的波动相位坐标，再比较整条 raw-price path。

对于 low-start：

- C1：`L0 -> H1 -> L1`
- C2：`L1 -> H2 -> L2`

对于 high-start 对称。

不是按绝对 bar time 对齐，而是按**两条 leg 分段相位**对齐：

- reversal start -> opposite extremum：phase `u in [0,1]`
- opposite extremum -> next same-kind extremum：phase `u in [1,2]`

每条 leg 在自己的实际 duration 上单调映射到固定 phase interval。这样上涨/下跌腿可以有不同 bar 数，不会因 phase allocation 不同而错位。

在固定、非数据调参的 phase grid `u_j` 上，由 raw closes 作线性插值：

`C1(u_j), C2(u_j)`

得到：

`Δ_j = C2(u_j)-C1(u_j)`

然后估计 normalized parent translation：

`T = robust_location({Δ_j}) / A`

其中 `A` 必须复用冻结 qualification/D1 已有的 causal amplitude normalization 口径，不新发明按结果选出的尺度。

#### 推荐的 robust location

第一优先不是普通均值，而是：

- weighted median；或
- fixed trimmed mean；

但二者不能同时试很多参数。最干净的首个 POC 是 **median of phase-aligned differences**：无 trimming ratio 超参数，breakdown point 高，单个 endpoint/局部异常无法支配结果。

#### 金融 fit

非常高。

它直接回答：

> 在同一个 wave phase 上，第二个完整波形相对第一个整体上移还是下移？

这与“两个同尺度完整波的父级漂移”高度一致。

#### 对当前失败的针对性

- endpoint 仍用于定义相位边界，但不会直接决定最终 translation；
- 每个 leg 内所有 raw bars 都参与；
- corresponding-leg duration 不同通过 phase normalization 被吸收；
- s0/s1 cancellation 不再以两个 endpoint 的代数和承担最终方向。

#### 风险

1. 若两个周期波形形状变化极大，`Δ(u)` 可能高度不一致；这应表现为 uncertainty，而不是强行趋势。
2. phase interpolation 仍依赖 extremum anchors；需要 multiview 验证其改善程度。
3. 不可偷偷用 DTW 自由扭曲，因为过度 warping 会把真实父级结构差异“对齐掉”。

**排序：P0。**

---

### P1：Robust raw-path drift regression with phase nuisance basis

拟合整个 pair span：

`P(t) = a + b*t + wave_phase_terms + error`

其中 `b` 表示 parent drift，wave terms 表示两个 reversal cycles。

可考虑：

- 固定 piecewise phase basis；
- robust regression / Huber / Theil-type slope。

#### 优点

- 所有 bars 参与；
- 直接估计 drift slope；
- 可理论上分离 parent trend 与 oscillation。

#### 风险

- 只有两个 cycles，wave basis 与 trend 容易共线；
- basis 选择本身会引入模型自由度；
- 若使用 harmonic sine/cosine，会把非正弦真实波形强行参数化；
- Huber tuning / basis degree 很容易形成新的参数搜索空间。

**排序：P1，作为 PAWCT 的竞争 POC，而不是首个实现。**

---

### P2：Per-cycle robust location shift

分别对 C1/C2 的 raw prices 计算 median / trimmed center：

`T = median(C2) - median(C1)`

#### 优点

- 极简单；
- 不依赖 precise endpoint values；
- robust。

#### 缺点

- cycle 内上涨/下跌腿 duration 不同会改变 raw price 的时间占比；
- 同一个几何波形只因 phase allocation 不同，median price 就可能变化；
- v0.5.4 已证明 phase allocation 是 morphology diagnostic，不应轻易进入 same-state hard definition。

**排序：P2 control，不作为主候选。**

---

### P3：Upper/lower local quantile-envelope regression

在整个 pair span 上构造 rolling/local upper/lower quantiles，再分别估计两条 envelope slope。

#### 优点

- 语义接近 higher-high / higher-low channel；
- 不只使用 exact extrema。

#### 缺点

- window bandwidth / quantile level 引入新尺度参数；
- 只有两个 cycles 时边界效应强；
- 容易重新混淆 direction 与 channel width；
- causal local quantile 会有显著 lag。

**排序：P2/P3 级备选，暂不首发。**

---

### P4：DTW / free curve matching

把 C1/C2 用动态时间规整后比较 translation。

#### 不推荐作为首轮

虽然可处理 phase allocation，但自由 warping 有过度对齐风险：

- 真实的 acceleration / asymmetry 可能被 warping 消除；
- Sakoe-Chiba band 等又引入超参数；
- 可解释性弱于固定两-leg phase normalization。

**排序：reference / later only。**

## 5. 首选数学对象：PAWCT

当前最符合金融语义、参数最少的方案是：

> **固定两-leg phase alignment + whole-path paired translation + median location。**

### 5.1 为什么 median 优先

Stage B 显示 endpoint exact positions 可以发生大幅重定位。若最终方向仍由少数 edge samples 支配，就会重演 D2。

median 的作用不是“平滑市场”，而是让父级 location 由大多数同相位 raw-price differences 决定。

它自然提供一个第二个非常重要的量：

`phase_translation_dispersion`

例如 median absolute deviation（MAD）：

`MAD_Δ = median(|Δ_j - median(Δ)|)`

这有潜力把“direction evidence”和“resolution confidence”分开：

- `median(Δ)`：父级 translation location；
- `MAD_Δ` / sign-consistency：不同 wave phases 是否支持同一个 parent shift。

但 **v0.5.8 首个单组件不能同时修改 location estimator 和 confidence gate**。

因此首轮 POC 只测试 representation：

> PAWCT median translation 本身是否比 endpoint D2 更 slicing-stable、同时保持金融方向语义。

MAD 只记录为 diagnostic，不参与 label。

## 6. 首个 POC 应该如何限制自由度

为了避免另一次“看结果调模型”，首轮在代码前应固定：

1. phase mapping：两条 legs 分别线性映射到 `[0,1]` / `[1,2]`；
2. phase grid：固定等距 grid，grid size 由数值积分精度需求事前指定，不按结果搜索；
3. interpolation：线性；
4. translation location：median；
5. normalization：复用冻结 D1/v0.5.4 amplitude unit；
6. 不加 confidence gate；
7. 不改变 `phase_tolerance=0.15`，若首个 POC需要生成 shadow label，只允许用原阈值作纯可比性控制，不据此直接晋级；
8. D1/D2 历史标签完整保留；新输出必须是另一个 version key，不覆盖历史；
9. candidate / qualification / ledger IDs/intervals exact unchanged；
10. prefix replay 仍是硬门。

## 7. 首轮真正要验证的问题

首轮不是问“range 数量是否更漂亮”，而是问：

### Representation gate R1

PAWCT translation 在 synthetic raw waves 上是否满足：

- pure translation：精确恢复符号；
- range + phase-allocation change：location 应接近 0；
- trend + asymmetric legs：仍恢复正确 parent translation；
- one endpoint contaminated：median 不应被单点主导；
- strict monotonic raw price：上游仍不产生 complete two-wave，PAWCT 无权单独造波。

### Real main-5m mechanism R2

在冻结 v0.5.4 selected structures 上：

- upstream identity/interval exact unchanged；
- 与 D1/D2 disagreement cases 比较时，PAWCT 的 raw `T` 是否对 same parent pair 给出更一致的符号/量级；
- 只看 geometry，不看收益。

### Multiview R3

最终必须比较 PAWCT raw continuous translation 的跨 offset 稳定性，而不只比较 thresholded label。

建议同时报告：

- signed correlation on matched/common-owned intervals；
- median absolute difference in normalized T；
- sign agreement away from zero；
- label agreement（若使用 frozen 0.15 shadow threshold）仅作辅助。

不能只用 label agreement，因为 Stage B 已证明 hard threshold 会把连续 estimator 的边界行为放大。

## 8. 关键设计约束：alternate offsets 只能验收，不能成为输入

生产/单视图 classifier 不可能依赖“同时看另外四个 offset 再投票”。

因此：

- PAWCT 每个 view 独立计算；
- multiview 只用于验收 representation invariance；
- 不允许 ensemble offsets 作为新 confidence signal。

这保留了单流因果金融语义。

## 9. 如果 PAWCT 也失败，意味着什么

若 whole-path phase-aligned median translation 仍表现出：

- 大量 large-margin sign flips；
- matched continuous T 在 native offsets 上低稳定；
- disagreement 主要来自 parent tuple 的大幅跨-slicing re-identity，而不是 endpoint-only sensitivity；

则问题将不再属于 D1 estimator，而应回到一个更高层问题：

> native 5m slicing 下，虽然 v0.5.2/v0.5.4 interval IoU 改善，但“被视为同一个经济 parent structure”的 cross-view correspondence 是否足够强，能支持稳定 state classification？

那时不能继续堆 D1 公式，需研究 cross-view parent correspondence / scale-space state object。

但当前 Stage B 的证据尚未要求回退到这里；先测试 whole-window estimator 是合理下一步。

## 10. 推荐顺序

1. 冻结 PAWCT POC protocol；
2. synthetic representation tests；
3. main-5m shadow continuous estimator audit；
4. 若 main mechanism 合理，再 five-view continuous stability；
5. 只有 continuous estimator 自身通过，才单独研究 resolution confidence / categorical D1；
6. D1 独立通过后才进入 morphology acceptance。

当前仍禁止 H1/H2、第三浪、收益、交易。

## 11. 当前结论

v0.5.7b 没有把整个方向研究判死；它判死的是：

> **“用 exact endpoint whole-envelope displacement 直接给父状态 hard label”这条具体路线。**

最值得继续验证的下一数学对象是：

> **PAWCT：以两条完整 raw reversal cycles 的 phase-aligned whole-path paired translation，估计 robust parent location shift。**

它比 endpoint D2 更符合当前失败证据，也更忠实于最初金融需求：根据两个完整同尺度波形的整体漂移判断父级趋势/震荡。
