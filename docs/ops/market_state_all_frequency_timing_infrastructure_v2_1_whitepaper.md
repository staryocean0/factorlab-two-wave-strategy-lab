# 择时策略全频段共同基础设施 V2.1：属性盈利关系评价

> 四层归属：Layer 2 测量。执行运输/费用字段仅作诊断预检，不授予 Layer 4
> 路由权；自动选频、选策略、动作和仓位均禁止。

日期：2026-08-28  
合同：`market_state_all_frequency_timing_infrastructure@2.1`  
状态：Implemented / evidence-bound interpretation  
权限：无自动选频段、无策略选择、无 fresh-OOS、无生产权

## 1. V2.1解决什么问题

V2已经能计算收益率、波动率、自相关、协方差、高频噪声并执行ASK-BID期权
回测，但“能算”不等于“知道它与趋势盈利有什么关系”。V2.1增加统一评价层：

- 哪些属性对盈利差异有材料解释力；
- 哪些属性只有和其他层配对时才有用；
- 哪些属性单独使用会误导；
- 哪些已经是通用基础设施，哪些仍依赖具体策略账本。

评价证据绑定到一分钟P128亏损与15分钟盈利反例归因。它不是普适因果定律，
也不把任何属性自动升级成入场门、否决门或频段路由。

## 2. 对盈利关系较大的属性

以下统一标为`material_when_paired`，必须配对使用：

| 属性 | 当前落地 | 正确评价 |
|---|---|---|
| `path_efficiency` | V2.1通用snapshot；多尺度场已有provider | 同一物理时长内，净位移相对总路径越低，折返负担越大；必须同时看有符号边际 |
| `jump_variation_share` | 通用bipower诊断已落地 | 局部跳变负担；必须和路径效率、单笔边厚度一起看 |
| `faster_cost_to_positive_revenue` | 已有严格收益守恒研究；仍需策略账本 | 直接量化快波负担是否吃掉本频/慢频正收入，不是原始时间序列因子 |
| `mean_trade_edge_thickness` | 策略账户层已落地 | 聚合毛收益可能靠大量薄交易堆出；必须检查每笔边能否覆盖执行 |
| `executable_signed_edge` | V2.1运输阶梯可承载 | 先在可执行子样本重新测指数方向边，再谈衍生成本 |
| `execution_transport_ladder` | V2.1通用函数 | 依次分开信号/指数、期权参考价和ASK-BID，禁止合成一个“成本”数字 |

CSI1000实证中，一分钟2日路径效率0.087，15分钟0.223；jump share为
0.287对0.168；重复期快波成本/正收入为0.942对0.733；同轴平均单笔边为
2.77bp对25.00bp。这些差异共同解释盈利缓冲，而不是任何一列单独解释。

## 3. 条件诊断属性

| 属性 | 状态 | 边界 |
|---|---|---|
| `variance_ratio` | V2.1新增4/8/16棒snapshot | 只提示持续/均值回归，不能代替策略方向边 |
| `microstructure_noise_ratio` | 已落地 | 识别细网格污染；不能推出更慢策略也会亏 |
| `component_direction_bdci` | 滤波provider已落地，未并入全频原始价格面板 | 测分量状态连续度；必须配合实际边和单笔厚度 |

这些属性可用于提出机制问题或发现测量缺口，没有单独盈利门权限。

## 4. 单独使用弱相关或容易误导的属性

| 属性 | 为什么不能单独判断盈利 |
|---|---|
| `return_autocorrelation` | 亏损一分钟lag1 ACF约0.293，反而高于盈利15分钟的0.049 |
| `raw_sign_persistence` | 一分钟0.751，高于15分钟0.516；高连续不等于路径干净或可执行 |
| `static_neighbor_energy_ratio` | P43相邻频段benefit/friction约2.499对2.544，几乎相同但经济结果相反 |
| `raw_volatility_level` | 只量机会宽度，不给方向、路径质量或执行边 |
| `component_body_contraction` | 转折末段收缩是真实后验形态，但因果小实体也发生在起步与停顿，P128 battle没有转正 |
| `trade_count` | 高频可用大量薄交易堆出理想毛收益，同时降低执行存活率 |

这些字段继续保留诊断价值，但注册表统一标记
`weak_or_misleading_standalone`，禁止成为单字段策略通过/否决条件。

## 5. 强制评价顺序

任何“某频段为什么赚/亏”的研究必须按下列顺序：

```text
全量有符号趋势供给
  -> 路径噪声相对于单笔边厚度
  -> 可执行子样本有符号边
  -> 指数/衍生品/ASK-BID运输
  -> 盈利频段反例挑战
```

必须使用相同物理时长。最终经济比较还必须使用相同载体与执行口径。单属性推断
盈利、拿指数收益和期权收益直接比较、或者用高ACF替代边际测量，全部禁止。

## 6. 当前实现矩阵

V2.1在`diagnose_frequency_panel()`新增：

- `path_efficiency_window`；
- `variance_ratio[4/8/16]`；
- `direction_reversal_rate`；
- `directional_run_mean_bars`。

新增`build_execution_transport_ladder()`，按共同索引输出每层平均bp、胜率和相对
上一层的边际损耗。新增`timing_profitability_attribute_registry()`，把所有评价、
实现状态、证据路径和禁用权限写入机器注册表。

尚未通用化的两项保持明确：

- `faster_cost_to_positive_revenue`必须从完整策略收益守恒账本计算；
- `mean_trade_edge_thickness`必须从冻结完整交易账户计算。

它们不应被伪装成仅靠价格序列即可得到的通用因子。

## 7. ASK-BID与费用合同

V2的当前执行口径不变：同步L1 ASK买入、BID卖出，只额外扣14元/张/边；代理
价差、额外市场冲击和Theta二次扣减仍禁止。

## 8. 科学边界

属性评价只规定证据解释顺序，不选择策略或频段。新属性要进入策略，仍必须走
`$strategy-slice-rebuild`完整政策与未见期合同。
