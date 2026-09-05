# Timing Layer 3 四类策略架构执行计划

状态：`execution_authorized`  
任务：`bd://fl-olbwf`  
权限：研究基础设施；`production_authority=false`

## 目标

把冻结清单中的12个第三类资产从“3a/3b混装”整理为四个单向依赖类别：

```text
3.1 策略语言与身份
  -> 3.2 研究构造与验收
  -> 3.3 通用编排内核
  -> 3.4 策略插件与历史样板
```

通用内核不得进口具体策略实现；插件通过profile、合同引用和digest接入。分类整理
不改变任何认领、入场、退出、参数或生产公式。

## 四类冻结

### 3.1 策略语言与身份

`tool_registry_v1_5`、`tool_relative_coupling`、`paper_kernel_tool_identity`、
`formula_derived_tool_inversion`。V1.5十五工具是唯一身份真源；十四工具耦合和十三
工具公式编译覆盖必须显式暴露gap。论文核工具身份折叠为注册表lineage view。

### 3.2 研究构造与验收

`evaluation_platform_v4`、`formula_derived_joint_state_machine`，并强制组合
`strategy_progressive_development@1.0`与`post_training_account_audit@1.0`。研究引擎
负责预注册、progression保留、promotion和A0--A7，不是运行时状态机。

### 3.3 通用编排内核

`volatility_three_state_machine`、`priority_composition_waterfall`、
`timing_strategy_router_v4`。内核只负责measurement→state adapter、互斥认领、余集
下传和冲突仲裁；不内置具体策略公式。

### 3.4 策略插件与历史样板

`explosive_layer_v3`、`crash_rebound_current_best`、`timing_research_samples_rN`。
分别登记为current owner profile、未安装research candidate、historical exemplar；
禁止把整个`market_state/`目录当current资产。

## 实施阶段

1. 发布四类架构合同、Schema和12资产唯一归属validator。
2. 发布策略语言facade，锁定15/14/13覆盖及论文核lineage合并。
3. 发布研究验收facade，组合评价平台、公式研究、progression和A0--A7。
4. 发布不进口策略实现的generic orchestration kernel。
5. 发布显式plugin registry和V4兼容profile；不安装current-best候选。
6. 发布版本注册表、白皮书、证据和全量测试。

## 硬门

- 12项资产恰好出现一次；无mixed。
- 注册表15工具顺序不变；14/13覆盖不得冒充完整。
- 研究引擎不获得运行时路由权。
- generic orchestration源码不得进口explosive/current-best实现。
- 插件状态与是否安装分开；research candidate不得因current-best名字自动安装。
- 任何策略结果研究仍须十二年度会话、progression/promotion分离和A0--A7。
- `production_authority=false`。
