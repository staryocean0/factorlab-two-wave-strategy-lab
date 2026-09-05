# Timing Layer 3 策略身份与权限白皮书

状态：Implemented / strategy conditional-effect boundary current  
合同：[`timing_layer3_strategy_architecture@2.2.json`](timing_layer3_strategy_architecture@2.2.json)  
身份注册表：[`timing_strategy_identity_registry@2.2.json`](timing_strategy_identity_registry@2.2.json)  
必要性：[`timing_layer3_necessity_registry@1.0.json`](timing_layer3_necessity_registry@1.0.json)  
插件：[`timing_layer3_strategy_plugin_registry@2.1.json`](timing_layer3_strategy_plugin_registry@2.1.json)  
权限：`production_authority=false`

## 一屏结论

当前权威分类只有三种：`infrastructure`、`strategy_research`和
`registered_usable_strategy`。当前15项恰好归属一次：10个通用基础设施，
5个策略研究资产，0个已注册可用策略。P8 L2分桶原型属于`unfinished_strategy_prototype`，不是Layer 2基础设施。@1.0/@1.1的四个内部基础设施表面
仍作历史设计证据，但不再是策略权限分类。

## 旧权限重置

四层基础设施重建后，历史`installed`、`current`、`current_best`和
`architecture_locked`不能自动继承。V4 Router、Explosive V3和Crash Rebound R1
都是`research_pending_requalification`；A12是`historical_closed`。所有资产的已注册使用、
参数选择、纸交易、实盘和生产权限均为false。

三个当前具体实现的权威路径已迁入`src/factor_lab/strategy/research/timing/`。
`src/factor_lab/market_state/`下的同名模块只是历史导入兼容层，目录位置不能赋予
基础设施身份。

## 15/14/13覆盖裁决

唯一工具身份真源是`tool_registry_v1_5`十五工具。现有coupling只覆盖V1.4十四
工具，公式编译器只覆盖原始十三工具。新合同不伪造LAT耦合或论文核/LAT公式编译
能力，而是显式列出uncovered；后续补齐必须升版各自合同。

论文核已经是十五工具注册表中的第十四工具，因此`paper_kernel_tool_identity`只保留
lineage view，不再作为独立current组件重复计数。

## 研究与运行边界

`StrategyConditionalEffectResearch`现为Layer 3正式一等入口。它回答：“某一具体
策略/tool在什么Layer 2属性条件下有效？”它必须同时读取具名tool/策略身份、
decision/position/action-role/account-effect证据和Layer 2属性，因此不属于Layer 2测量。

`tool_conditioned_relationships`和`tool_attribute_relationship_maps`已迁入该入口。历史
`market_state/` 实现路径只用于保持源digest和导入兼容；当前公开权威是
`src/factor_lab/strategy/research/timing/conditional_effect_research.py`。

公式联合状态机迁入研究构造与验收类。它负责候选家族、嵌套验证和机械验收，没有
运行时路由权。评价平台V4必须与progression retention、candidate promotion和
A0--A7账户审计组合，不能把晋级失败误写成没有测量进步。

通用编排内核只接收state adapter、owner profile和eligibility；输出责任归属与余集，
不输出仓位。源码不进口第一层V3或current-best策略实现。

原`all_frequency_timing_v2_1`已分成三个权威facade：市场频率测量归Layer 2，
策略账户/盈利条件诊断归Layer 3，可执行价、期权费用和execution transport归Layer 4。

## 策略研究生命周期

- V4 Router：研究装配快照，未安装。
- Explosive V3：待重新资格审查的研究策略，不是current owner。
- Crash Rebound R1：保留历史证据的研究候选，`current-best`名称没有当前权限。
- A12：已封存的历史反例/样例，不是正在竞争的候选。

重新注册必须建立当前四层`StrategyAssemblyManifest`，在Layer 4账户回放中
选参，完成A0--A7和真正未见挑战，然后取得显式注册回执。若公式或行为发生变化，
还必须完整执行年度整案重建。研究结论不能直接赋予纸交易、实盘或生产权限。

## 状态机降权前的材料回迁

固定三态等状态机降权前先逐项拆材料。波动连续面此前已在Layer 2；本轮新增回迁
EMA H4连续速度轴、FDA局部二次速度/加速度和公式原生连续属性。K边界、阈值、
滞回、驻留、authority period、owner、entry/exit和状态模板仍留Layer 3。

因此降权表示“研究证据保留，当前使用权重置”，不是删除研究成果。在新流程完整走通前，
不存在任何已安装的Timing策略插件。
