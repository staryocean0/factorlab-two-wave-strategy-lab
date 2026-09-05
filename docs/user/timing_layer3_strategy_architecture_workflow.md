# Timing Layer 3 三类身份与策略重新注册工作流

入口顺序：

```text
infrastructure
  -> strategy_research
  -> registered_usable_strategy
```

先读[当前@2.2](../ops/timing_layer3_strategy_architecture@2.2.json)、
[权威身份注册表](../ops/timing_strategy_identity_registry@2.2.json)、
[必要性与材料迁移](../ops/timing_layer3_necessity_registry@1.0.json)和
[白皮书](../ops/timing_layer3_strategy_architecture_whitepaper.md)。

基础设施不得输出具体策略仓位或反向导入策略研究实现。研究资产允许做实验性回测，
但不得被当作已注册、纸交易或实盘策略。

研究“某个具体策略/tool在什么Layer 2属性下效果好”时，唯一入口是
`factor_lab.strategy.research.timing.conditional_effect_research`。禁止将tool/position/action-role/策略效果
送回Layer 2 causal provider。

重新注册顺序为：冻结公式和数据边界 → 建立当前四层AssemblyManifest →
Layer 3冻结结果前参数家族 → Layer 4账户回放选参 → A0--A7 → 真正未见挑战 →
显式注册回执。行为变化还必须执行十二个逐年整案重建会话。

当前`registered_usable_strategy`为空。V4 Router、Explosive V3和Crash Rebound R1均在
`research_pending_requalification`；`csi1000_lat_p8_l2_matched_bucket_prototype`是
`unfinished_strategy_prototype`（半成品，不是Layer 2基础设施）；A12为`historical_closed`。本工作流不授予交易或生产权。
