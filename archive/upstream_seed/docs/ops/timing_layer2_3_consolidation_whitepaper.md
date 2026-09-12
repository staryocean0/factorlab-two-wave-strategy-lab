# 择时基础设施第 2/3 层收口白皮书

状态：Lane 2 类别 facade 已完成，研究用途；`production_authority=false`  
机器注册表：[`timing_layer2_3_registry@1.0.json`](timing_layer2_3_registry@1.0.json)

## 结论

本次没有把二十九个资产实现搬进一个大包，也没有创造第五层。现有实现仍在原
模块中；新增 facade 只给它们一个稳定的类别入口：

```text
Layer 2  K线测量
    ↓ 只传连续量、关系、频段和诊断
Layer 3a 工具词汇与评价考卷
Layer 3b 余集、三态、状态机和桶政策
```

Layer 2 不能返回责任认领、动作或仓位。Layer 3a 固定消费现役十五工具表
`tool_registry_v1_5` 与评价平台 `market_state_timing_evaluation_platform@4.0`。
Layer 3b 的统一生命周期是
`replaceable_by_more_complete_layer2_measurement_not_a_long_term_foundation`：它是测量
尚未充分时的时效原型，可以坐冷板凳，不是长期底座。

## 四组 2/3 内部剥离

| 原半吊子 | Layer 2 / 3a | 另一身份 | 实现办法 |
|---|---|---|---|
| 六轴目录 | `six_axis_common_market_state` | `tool_relative_coupling`（3a） | 复用现有 `timing_six_axis.py` 与 `tool_factor_coupling.py`，不复制公式 |
| 论文核 | `paper_kernel_timeseries` | `paper_kernel_tool_identity`（3a） | 16 尺度时序只测量；第十四工具继续由注册表身份承接 |
| 波动识别器 V2 | `volatility_continuous_features` | `volatility_three_state_machine`（3b） | 两个公共 adapter；先测连续面，再由独立 API 切三态 |
| 公式派生 V3 | `formula_derived_tool_inversion`（3a） | `formula_derived_joint_state_machine`（3b） | 倒推合同与联合策略工作流分开登记 |

属性池是跨车道拆分：Lane 2 只拥有 K 线/频谱/论文核/载体关系四池的 source
登记；衍生品 overlay 属于 Lane 3；共享框架
`attribute_pool_infrastructure.py` 未修改。

## 测量边界

波动率历史实现为了家族 Battle 同时保存连续特征、未来评价目标和三态函数。新
Layer 2 adapter 复用其连续公式，但在公共返回面主动删除 `future_rv_16` 以及任何
包含 state/position/claim/action 的字段。Layer 3b adapter 只接收该连续面，返回
`volatility_state_raw` 与 `volatility_state`；它不返回仓位。

全频段 V2.1 的类别入口固定为测量，合同继续明确
`automatic_strategy_frequency_selection=forbidden`。执行运输与费用信息在该历史
实现中只作为诊断/预检数据，不构成 Layer 4 路由权。

## 3b 生命周期与公式身份

优先级瀑布、路由 V4、第一层 V3、crash-rebound current best、研究样板、三态机
和公式联合状态机统一登记为 3b。现役对象只增加归属与生命周期元数据；认领、
入场、退出、状态转移和桶公式没有改变。

优先级瀑布此前文档已指向十五工具，但代码仍绑定 V1.4 十四工具前缀。本次只把
空瀑布的合法工具白名单对齐现役 `tool_registry_v1_5`；没有预填优先级，也没有
改变任何认领条件公式。

## 权限

本次没有读取收益、候选排名、交易或 lockbox 明细；没有新增工具、策略或经济
结论。`strategy_selection=false`、`parameter_selection=false`、
`fresh_oos=false`、`production_authority=false`。
