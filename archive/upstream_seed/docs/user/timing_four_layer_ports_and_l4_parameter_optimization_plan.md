# 四层端口与Layer 4参数优化顺序执行计划

状态：`execution_authorized`  
任务：`bd://fl-bvyeu`

## 核心顺序

```text
Layer 1  PreStrategy BarView
  -> Layer 2 PreStrategy FeatureBundle
  -> Layer 3 StrategyPolicyFamily（只冻结公式和参数族，不选最终参数）
  -> Layer 4 AfterStrategy AccountFamilyReplay
  -> Layer 4 ParameterSelectionReceipt
  -> Final StrategyAssemblyManifest
```

参数调优必须发生在Layer 4完整账户、工具、执行、成本、资金和风险口径接入之后。
Layer 3不得先选择参数再要求Layer 4背书。

## 接口而非固定连接

项目只冻结四类Port及其Schema。组件声明`provides/requires`能力；具体连接由每个
策略自己的AssemblyManifest选择。白皮书解释允许连接，validator校验语义和digest。
不存在全项目唯一Layer1→2→3→4组件链。

## 实施

1. 发布BarViewPort、FeatureProviderPort、StrategyPolicyFamilyPort、
   AccountFamilyReplayPort、ParameterSelectionReceipt。
2. 发布Capability/Requirement匹配器与TransportReceipt。
3. 强制Layer 3输出完整参数候选族且`selected_parameter_id=null`。
4. 强制Layer 4完整重放候选族后才可产生参数选择收据。
5. 发布每策略AssemblyManifest、CAS和rollback边界。
6. 用CSI1000 ETF LAT P49做reference identity migration：映射现有身份，不重调P49；
   因ETF完整Layer 4成本仍缺，明确阻断新参数选择。
7. 参考迁移通过后，再逐个迁移近期current策略；行为变化一律转为新策略研发。

## 硬门

- L1/L2均为PreStrategy，不含策略参数选择。
- L4为AfterStrategy账户评价和参数选择权威。
- Layer 3候选族必须完整、结果为空、未选择。
- 无Layer 4 receipt不得产生新selected参数或更新策略指针。
- reference migration只允许行为等价适配，不得借迁移优化公式。
- 生产权始终false。
