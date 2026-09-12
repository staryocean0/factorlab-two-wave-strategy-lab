# BDCI / K线方向连续度指标白皮书

日期：2026-05-20
状态：已实现 V1
范围：`factor_lab.indicators.bar_direction_continuity`

---

## 1. 一句话定义

**BDCI（Bar Direction Continuity Index，K线方向连续度）** 衡量一段 K 线里
“上涨/下跌方向是否经常反复切换”。

它回答的是：

> 这段行情更像“方向有惯性、适合顺势观察”，还是“方向频繁反复、偏震荡”？

BDCI 首先是 **Metric / regime diagnostic（度量 / 状态诊断）**，不是默认 alpha 因子。
它不直接回答“未来收益会不会上涨”，而是描述过去一段价格路径的方向连续性。

---

## 2. 为什么不用蜡烛红绿

用户已确认：本项目第一版“K线方向”默认使用 **收盘价相对上一根收盘价**，不使用蜡烛红绿。

原因很简单：

| 口径 | 计算 | 问题 / 适用性 |
|---|---|---|
| 蜡烛红绿 | 本根 `close > open` 为红，`close < open` 为绿 | 更像本根内部形态；会被开盘跳空影响。 |
| close-to-close | 本根 `close` 相对上一根 `close` | 更像连续行情路径；更适合衡量一段行情方向是否延续。 |

例如某股票每天都跳空高开后回落，单根可能是阴线，但收盘价每天仍高于上一天收盘价。
BDCI 会把它识别为连续上行，而不是被单根阴线误判为方向反复。

---

## 3. 数学定义

给定一段按时间排序的收盘价序列：

\[
C_1, C_2, \ldots, C_n
\]

默认计算 close-to-close 对数收益：

\[
r_t = \ln(C_t / C_{t-1}), \quad t=2,\ldots,n
\]

给定中性带 \(\epsilon \ge 0\)：

\[
d_t =
\begin{cases}
+1, & r_t > \epsilon \\
-1, & r_t < -\epsilon \\
0, & |r_t| \le \epsilon
\end{cases}
\]

第一版默认把 \(d_t = 0\) 视为“方向不明确”，从切换统计中剔除。

设剔除中性后的方向序列为：

\[
D_1, D_2, \ldots, D_m, \quad D_i \in \{+1,-1\}
\]

如果 \(m < 2\)，样本不足，输出 `insufficient`。

否则切换次数为：

\[
S = \sum_{i=2}^{m} \mathbf{1}(D_i \ne D_{i-1})
\]

可切换机会数为：

\[
M = m - 1
\]

切换率为：

\[
SwitchRate = S / M
\]

BDCI 分数定义为：

\[
BDCI = 100 \times (1 - SwitchRate)
\]

---

## 4. 白话解释

| BDCI | 路径形态 | 解释 |
|---:|---|---|
| 100 | 一直涨或一直跌，中间不换方向 | 方向最连续。 |
| 约 50 | 涨跌切换接近随机 | 没有明显方向惯性。 |
| 0 | 每一步都反向 | 强锯齿、强震荡。 |

因此第一版分类为：

| 条件 | 分类 | 白话解释 |
|---|---|---|
| 有效方向少于 2 个 | `insufficient` | 数据太少，别判断。 |
| `BDCI >= trend_threshold` | `trend_friendly` | 方向比较连续，适合观察顺势结构。 |
| `BDCI <= oscillation_threshold` | `oscillation_friendly` | 方向频繁切换，更像震荡。 |
| 其他 | `observe` | 中间状态，先观察。 |

默认阈值：

```text
trend_threshold = 60
oscillation_threshold = 40
```

这只是第一版工程默认值，不是永久定理。代码通过 `BarDirectionContinuityConfig`
保留 `trend_threshold`、`oscillation_threshold`、`epsilon`、`window` 等配置入口，
未来可以按资产类别、K线周期、噪声水平、市场 regime 做微调。

---

## 5. 置信辅助项

代码同时输出一个简单的方向切换 z-score：

\[
Z = (0.5 - SwitchRate) / \sqrt{0.25/M}
  = (1 - 2 \times SwitchRate)\sqrt{M}
\]

直觉：如果完全没有方向结构，涨跌切换率大致可能接近 50%。
当 BDCI 高于 50 时，Z 为正；当 BDCI 低于 50 时，Z 为负。

V1 只输出该值，不把它作为硬门槛。未来如果要更严谨，可以把“BDCI 阈值 + Z 显著性”组合成二级分类规则。

---

## 6. 项目分类位置

本项目现在建议把研究对象按角色先分清楚：

| 角色 | 问题 | 例子 |
|---|---|---|
| Asset / 资产 | 谁在产生价格或收益序列？ | 股票、ETF、外部指数、自建指数、自建组合。 |
| Feature / Factor / 特征或因子 | 每个资产在某时点有什么暴露值？ | 动量、波动率、行业、市值、latent exposure。 |
| Metric / 指标度量 | 用来评价序列、因子、模型或环境状态。 | IC、RankIC、turnover、coverage、BDCI。 |
| Signal / 信号 | 根据特征/指标生成操作倾向。 | top-N、趋势门控、风险开关。 |
| Label / 标签 | 未来验证目标。 | forward return、未来波动、未来回撤。 |

BDCI 的默认位置是 **Metric / regime diagnostic**：

- 它可以计算在单只股票、指数、自建指数或组合上；
- 它可以评价“过去一段是否有方向连续性”；
- 它不自动成为 CandidateFactor，也不自动进入 EffectiveFactor / AdmittedFactor；
- 它当前是 library-level 指标，不暴露独立 REST / CLI / Workbench 控制面；如果未来产品化控制面，必须另补 API/CLI/UI 文档与测试；
- 若未来要把 BDCI 变成真正因子，必须像其他因子一样走 FactorSpec、验证、治理和准入流程。

---

## 7. 代码契约

实现位置：

```text
src/factor_lab/indicators/bar_direction_continuity.py
```

主要入口：

```python
from factor_lab.indicators.bar_direction_continuity import (
    BarDirectionContinuityConfig,
    compute_bar_direction_continuity,
    compute_bar_direction_continuity_from_rows,
)

result = compute_bar_direction_continuity(
    [100.0, 101.0, 102.0, 101.0, 100.0, 101.0],
    config=BarDirectionContinuityConfig(
        window=None,
        epsilon=0.0,
        trend_threshold=60.0,
        oscillation_threshold=40.0,
    ),
)
```

`result` 关键字段：

| 字段 | 含义 |
|---|---|
| `score` | BDCI 分数；样本不足时为 `None`。 |
| `regime` | `trend_friendly` / `oscillation_friendly` / `observe` / `insufficient`。 |
| `switch_count` | 方向切换次数。 |
| `opportunity_count` | 可切换机会数。 |
| `switch_rate` | 切换率。 |
| `switches_per_unit` | 默认每 100 次机会的切换次数。 |
| `valid_direction_count` | 非中性有效方向数。 |
| `neutral_direction_count` | 被 epsilon 中性带剔除的方向数。 |
| `invalid_pair_count` | close 无效导致跳过的相邻 pair 数。 |
| `z_score` | 相对 50% 随机切换率的辅助统计。 |

---

## 8. 滤波评估用法

当 BDCI 用来评价滤波效果时，推荐只把它当作“方向连续性是否改善”的一项指标：

\[
FilterContinuityGain（滤波连续度增益） = BDCI_{filtered} - BDCI_{raw}
\]

白话解释：

- 如果滤波后 BDCI 明显升高，说明滤波让方向更连续；
- 如果滤波后 BDCI 没升高，说明滤波没有改善方向连续性；
- 如果 BDCI 升高但价格严重滞后或收益结构被抹平，不能只凭 BDCI 说滤波有效。

因此 BDCI 适合作为滤波评估第一项，但未来还应配合滞后、收益保真度、换手、回撤、端点稳定性等指标。

---

## 9. 边界与风险

1. BDCI 描述过去路径，不预测未来收益。
2. BDCI 高不等于一定能赚钱；它只说明方向连续性较强。
3. BDCI 低不等于不能交易；它可能更适合震荡/均值回归框架。
4. 过度平滑可能人为提高 BDCI，所以滤波评估不能只看 BDCI。
5. 默认 60/40 是第一版直观阈值，未来可通过历史分布和策略需求微调。
