# 四层端口、策略装配与Layer 4参数选择白皮书

合同：[`timing_four_layer_port_contracts@1.2.json`](timing_four_layer_port_contracts@1.2.json)  
计划：[`../user/timing_four_layer_ports_and_l4_parameter_optimization_plan.md`](../user/timing_four_layer_ports_and_l4_parameter_optimization_plan.md)

## 边界

Layer 1与Layer 2是PreStrategy；Layer 3构造策略公式和完整参数候选族；Layer 4是
AfterStrategy账户评价，并拥有研究期参数选择权。最终参数只能由完整Layer 4账户族
重放后的receipt产生。

@1.1新增一条对称硬门：Layer 1和Layer 2的PreStrategy端口必须同时允许
Layer 3和Layer 4消费。Layer 4如需期权IV等市场测量，必须连接Layer 2 Provider，
不得内置并行计算器。当前参考是
[`timing_layer2_option_volatility@1.0`](timing_layer2_option_volatility@1.0.json)到
[`timing_layer4_execution@2.2`](timing_layer4_execution_registry@2.2.json)的绑定；V2.1保留为买方波动率绑定历史快照。

组件只声明capabilities和requirements，不绑定唯一上下游。每个策略自己的
`StrategyAssemblyManifest`选择组件、记录TransportReceipt、parity、CAS和rollback。

Layer 4 的盘口容量与冲击统一绑定
[`timing_layer4_recent_one_year_liquidity_impact_policy@1.0`](timing_layer4_recent_one_year_liquidity_impact_policy@1.0.json)。
历史价格路径只使用真实 PIT 价格/结算/制度坐标；股票、ETF、LOF、
可转债、期货和期权的容量、价差、book-walk、恢复与冲击只使用固定的
最近一年参考面。数量只决定请求规模是否可进入和执行代价，不得反向修改
Layer 3 方向或历史价格路径。

## 参数顺序

Layer 3必须输出`selected_parameter_id=null`。Layer 4开始前先冻结账户工具、标的、
成本、风险、资金、完整候选笛卡尔族和目标；全部候选账户重放后才能产生
`Layer4ParameterSelectionReceipt`。无receipt不得更新策略参数或current pointer。

旧策略接口迁移可携带历史参数做identity-only parity，但不得借迁移重调。若接口
适配改变decision或账户路径，立即转为新策略研发，走十二年度、progression/
promotion和A0--A7。

## 当前reference

CSI1000 ETF LAT P49已完成端口身份映射，但ETF完整Layer 4成本和账户adapter尚未
闭合，因此新参数调优保持blocked，P49不重选、策略指针不变。
