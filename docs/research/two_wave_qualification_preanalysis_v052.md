# v0.5.2 资格层预分析：父级腿质量应与 characteristic scale 对齐

日期：2026-09-05

状态：`conditional_preanalysis_not_protocol_frozen`

本文件**不是 v0.5.2 结果前协议，也不授权修改资格层**。只有 v0.5.1 characteristic-scale 真实数据实验通过其晋级门后，才允许据此冻结下一轮单组件实验。当前操作基线仍为 v0.4.3；不进入第三浪、收益、交易或生产。

## 1. 已知资格层问题

v0.4.3 固定窗口 2018-06-20 的近似同尺度五点：

- 五点 `[40397,40408,40421,40436,40450]`
- 四腿 `11/13/15/14`
- 两周期 `24/29`
- 周期时长比 `1.208`
- 对应腿时长比最大 `1.364`
- 去漂移振幅比 `1.013`
- 唯一拒绝原因：某腿 raw-close 路径效率 `0.308 < 0.5`

case_09 另有一个独立边界：对应腿时长比 `43/21 = 2.0476`，仅略超过现行 `duration_ratio=2.0`。

这些证据只能说明硬边界值得审计，不能直接授权放松阈值。

## 2. 当前 `leg_efficiency` 的数学含义

现行路径效率：

`ER = |x_end - x_start| / sum_i |x_i - x_{i-1}|`

它等价于一维轨迹的 straightness index / Kaufman efficiency ratio：端点位移除以实际路径总长度。`ER=1` 表示完全直行；内部往返越多，ER 越低。

相关跨学科定义：

- Perry Kaufman 的 Efficiency Ratio 用同一公式衡量趋势路径相对噪声；
- 轨迹分析中的 straightness index 同样定义为起终点距离 / 实际路径长度；文献同时强调该指标适用于“有定向目标的路径”，而不是把所有复杂路径统一解释为无效。

参考：

- https://kaufmansignals.com/matching-the-markets-to-the-strategy/
- https://link.springer.com/article/10.1007/s10109-021-00370-6
- https://pubmed.ncbi.nlm.nih.gov/15207476/

## 3. 为什么 raw-close ER 与新父级语义可能冲突

如果 v0.5.1 成功，父级波浪身份来自 TCSS characteristic scale：更细微摆在更粗尺度被系统吸收，父级五点仍投影回真实 raw-price extrema。

此时继续用**逐根 raw close 的总变差**作为父级腿完整性的硬门，会产生语义冲突：

> 一个已经被数学表示认定为“父级方向腿”的区间，可以因为内部存在合法子级往返而得到很低的 raw ER；于是资格层又把刚刚被父级表示吸收的子尺度摆动重新当成拒绝父级的证据。

这会把“层级表示”和“资格质量”放在不同尺度上测量。

因此下一轮真正应验证的不是 `0.5 -> 0.3`，而是：**路径效率的测量尺度是否应该与 characteristic scale 对齐。**

## 4. 首选单组件假说（只有 v0.5.1 通过后才可冻结）

候选 v0.5.2 单组件：

### `same-scale leg efficiency`

- raw 五个父级 extrema、characteristic-scale identity、D1、互斥账本全部冻结；
- `min_leg_efficiency=0.5` 数值阈值首轮保持不变；
- 唯一改变：腿效率分母不再使用逐根 raw-close 总变差，而使用**该对象已确认 characteristic scale 的因果 TCSS 序列**在同一 raw occurrence 区间内的总变差；
- 端点方向仍由 raw-price 父级 extrema 约束，不能让平滑序列凭空制造 raw reversal；
- 不做群延迟左移；TCSS 值必须只使用该 event 确认时已经存在的因果历史。

定义示意：

`ER_parent_scale = |L_sigma(b) - L_sigma(a)| / sum_{t=a+1..b} |L_sigma(t)-L_sigma(t-1)|`

其中 `sigma` 是 v0.5.1 自动选择并已确认的 characteristic scale，不由资格结果、case、D1 或收益选择。

## 5. 必须继续保留 raw-price 安全门

尺度对齐只针对“父级腿的路径直线性/粗糙度”。以下约束仍应保持 raw-price 口径，首轮不改：

- `jump_share`：防止一个大跳构成伪腿；
- `flat_share`：防止停牌/长时间不动等伪结构；
- actual alternating raw turns；
- min/max cycle、max pair；
- confirmation delay / information clock；
- amplitude consistency；
- D1。

因此即使 TCSS 平滑后路径很直，单次跳跃仍不能借平滑获得资格。

## 6. 结果前应设置的反例门

若 v0.5.2 被正式冻结，至少应包含：

1. **父波 + 高频子摆**：父级 ER 应明显高于 raw ER，并允许父结构保留；
2. **单次 jump**：scale-aware ER 即使很高，也必须继续被 raw `jump_share` 拒绝；
3. **真实 zigzag 无父级方向性**：不能仅因平滑而把无明确父腿的 raw 路径变成合格结构；
4. **严格单调 + detrended cycle**：不得凭空产生 raw 两浪；
5. **prefix invariance**：追加未来样本不得改变已确认对象的 characteristic scale、scale-aware ER、资格或发布；
6. **2018-06-20**：只作为既有固定审计窗口，不允许以它是否刚好越过 0.5 来反调公式；
7. **case_02 / 11 / 14**：安全性不得退化。

## 7. 为什么首轮不同时改 `duration_ratio=2.0`

case_09 的 `2.0476` 确实提示时长比硬阈值可能有边界问题，但它与 raw-path efficiency 是不同数学维度。

为了保持单组件可归因：

- 若 v0.5.2 启动，首轮只改 path-efficiency 的**尺度口径**，不改 `0.5` 数值；
- `duration_ratio` 是否应从固定硬比值改为 characteristic-scale / phase-duration 的连续相似度，应留作下一独立实验；
- 不允许把多个阈值一起放松后用候选数量或覆盖增长宣称成功。

## 8. 晋级判据

v0.5.2 只有在以下条件同时成立时才值得保留：

- 仍为 raw-reversal 金融语义；
- 六视图 18 次固定前缀零重写；
- 2018 类型“父级成立但内部有子摆”的结构得到机制上可解释的改善；
- jump/flat/巨型跨周/90-3 假浪安全门不退化；
- 五个原生 5m offset 的发布边界稳定性至少不系统性恶化；
- 改善来自 scale-aligned path quality，而不是阈值放松或覆盖膨胀。

若 v0.5.1 未通过真实 morphology 晋级门，本文件自动保持预分析状态，不启动 v0.5.2。