# CSI1000 MO连续Quote-Change BBO绑定白皮书

> 四层归属：`4 执行标的/账户测试`。当前统一入口见 [`timing_layer4_execution@1.0`](timing_layer4_execution_registry@1.0.json)。

状态：FactorLab独立验收通过连续一档BBO、L1 quote-change OFI与有界一档可执行成本；逐订单真相和大单反事实冲击不在当前研究范围。

## 1. 已闭合部分

DataHub固定研究包覆盖2025-09-01至2026-08-25，MO quote-change BBO共有556,911,166行。每行保留事件ID、有效区间、Bid/Ask一档价格与数量、checkpoint/delta、源序列和历史回放时间语义。它取代旧3秒成交后快照作为“连续MO一档状态”的正式研究数据源；旧3秒产品只保留成交后经验响应用途。

## 2. 未闭合部分

源只有quote-change L1，没有逐订单新增、撤单、成交事件分类和主动买卖方向。DataHub的partial-impact样本明确为`trade_direction_unidentified`、`partially_identified`、`true_counterfactual_impact_ready=false`。因此：

- 可以计算连续价差、mid、一档容量和报价状态变化；
- 可以构造“quote-change imbalance”研究变量，但不得命名为真实订单事件OFI；
- partial impact只能作为流动性响应描述，不得进入完整all-in cost或生产冲击模型。

上述两项是对大单、逐订单归因和生产冲击的更高阶能力，不再阻塞当前有界一档研究。

用户于2026-09-01进一步冻结市场背景：MO当前成交不活跃，做市商是主要对手；显示挂单较小，成交后做市商可能重新补单并改价。因此可见一档是当时可执行容量，但不是未来可补充流动性的硬上限。在没有冻结新的期权执行方案前，硬拟合跨档大单冲击函数会制造伪精度；该能力正式撤出当前需求，无需DataHub补齐。

## 3. 当前采用的有界口径

- OFI采用连续最优Bid/Ask价格和数量变化的标准L1 BBO event imbalance，measurement kind固定为`l1_bbo_quote_change_ofi`；
- 买入以当时Ask1、卖出以当时Bid1计价；
- 只有`order_units <= displayed opposite-side L1 size`时才接纳，超出一档数量立即fail closed；
- 不推断二档以后VWAP，不宣称自身订单对未来盘口的反事实冲击。

## 4. 权限

本绑定只授予固定版本历史研究基础设施。无latest alias、无receipt-exact PIT、无实时/生产授权，也不自动切换任何策略或路由器。
