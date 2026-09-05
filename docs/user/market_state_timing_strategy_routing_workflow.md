# 三层双向择时策略路由历史研究工作流

> 当前权限由`timing_strategy_identity_registry@2.0`管理。V4已迁入
> `src/factor_lab/strategy/research/timing/`并处于`research_pending_requalification`；
> 本文下方的历史锁定语义不是当前注册或交易权限。

> 四层归属：整段属于 Layer 3b 时效原型；可被更完整 Layer 2 测量取代，不是
> 长期底座。本次只增加归属/生命周期标签，不修改认领、入场或退出公式。

## 1. 当前唯一权威结构

当前项目级路由合同是 `timing_strategy_router_v4`，三层顺序固定，但只锁定第一层：

```text
第一层：高斜率行情（已锁定）
  1A 暴跌反弹 up，第一优先
  1B P48→P96 真通道 up/down，消费 1A 严格余集
  -> remaining_after_explosive_layer

第二层：低斜率普通趋势（V0工具筛选完成，组合路由未锁定）
  -> remaining_after_ordinary_trend_layer

第三层：横盘震荡后的尺度下钻（负责人未选）
  -> remaining_after_timing_router
```

这不是完整三层策略的发布：当前完成的是第一层，不得用第一层账户冒充完整组合。

## 2. 第一层 V3

### 1A 暴跌反弹

暴跌反弹只输出 `up`，并拥有第一优先级。W12/W24只在公式内部表示“最近已完成的
下跌第一腿”；入场质量由论文FDA机制要求前序速度与加速度同时为正，之后仍持有注册
弧线的完整生命周期。

### 1B P48→P96 高斜率真通道

通道负责 `up/down` 两个方向，只消费暴跌反弹未认领的严格余集。P48 可因果晋升到
P96；通道内的普通反弹或回调不触发退出，只有突破反向轨才结束持有：

- 做多突破下轨退出；
- 做空突破上轨退出。

因此它替代的是旧 W12/W24 的通用上涨/下跌延续职责，而不是重写暴跌反弹工具。

### 已撤销或降级的旧责任

- `explosive_w12_w24_continuation`：撤销通用路由权，只保留历史复现和暴跌反弹的
  内生第一腿；
- S20 有背景通道：保留历史消融，不进入当前第一层；
- 冲高回落：重复审计失败，不输出当前责任；
- 旧 V1、旧三桶和 V62 运行时：仅作兼容对照，不代表最新基础设施。

## 3. 严格余集和方向语义

三个执行掩码必须互斥；第一层剩余集必须严格等于三个掩码并集的补集。第二层只能
消费 `remaining_after_explosive_layer`，第三层只能消费第二层的余集。未锁定的层
保持 `owner_not_selected`，禁止静默填入历史赢家。

路由层只输出 `up/down/flat/unassigned`。仓位消费者再选择多空、只多、只空或其他
映射；方向事实不能被仓位偏好反向污染。收线后形成的决策只在下一根执行一次。

## 4. 复算和机器合同

```bash
PYTHONPATH=src:. python scripts/research_market_state_timing_explosive_layer_v3.py
PYTHONPATH=src:. python scripts/build_market_state_timing_strategy_router_v4.py
PYTHONPATH=src:. pytest -q \
  tests/unit/test_market_state_fda_recent_down_rebound_bridge.py \
  tests/unit/test_market_state_timing_explosive_layer_v3.py \
  tests/unit/test_market_state_fda_multiscale_channel_v1.py \
  tests/unit/test_market_state_context_free_explosive_two_bucket_v1.py
```

权威入口：

- 第一层代码：`src/factor_lab/market_state/timing_explosive_layer_v3.py`；
- 三层合同：`src/factor_lab/market_state/timing_strategy_routing_v4.py`；
- Schema：`docs/schemas/json/market_state_timing_strategy_router@4.0.json`；
- 持久化快照：`artifacts/market_state/timing_strategy_router_v4/`；
- 回测与图形：`artifacts/market_state/timing_explosive_layer_v3/`。

旧V3路由合同、第一层V2及更早产物只保留为历史版本，不能覆盖当前V4。

另有一个独立的[三桶加动态 IIR 基础设施样板 V1](market_state_timing_three_bucket_iir_reference_v1_workflow.md)，
用于展示严格余集、动态剩余负责人和统一 T+1 账户的可复现组合方法。它不属于 V4
升级，不改变本页的项目级路由权威。

## 5. 权限和完成度

第一层拥有研究与架构锁定权；参数权、生产权、V62 运行时修改权均为 `false`。
第二、第三层的工具选择权也是 `false`，直到各自完成分桶、Battle、三阶段评价和图形
归因。

第二层V0已完成14工具的固定基准Battle。上涨母桶的15分钟频率选择布林通过三段研究
审计；下跌母桶的60分钟因果Haar虽三段为正，但外部单位能力仅保留48.25%。更重要的
是，当前P48/P96通道若无条件前置，会消费82%—86%的普通方向棒，并使上涨赢家在
2018—2020最终余集转负。因此第二层尚不能锁定：下一步不是调参，而是验证“普通趋势
先做基准、高斜率通道只抢普通工具失败区间”的联合路由。

进一步阅读：[第一层 V3 工作流](market_state_timing_explosive_layer_v3_workflow.md)、
[三层路由白皮书](../ops/market_state_timing_strategy_routing_whitepaper.md)和
[第一层 V3 冻结回执](../ops/evidence/market_state_timing_explosive_layer_v3_20260804.md)、
[温和趋势工具筛选V0](market_state_ordinary_trend_tool_battle_v0_workflow.md)。
