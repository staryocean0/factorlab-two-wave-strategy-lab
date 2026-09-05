# 择时策略组合优先级工作流

> 四层归属：Layer 3b 时效原型。当前合同 `@1.1` 消费十五工具表；可被更完整
> Layer 2 测量取代，不是长期底座，且不授予生产权。

## 1. 这层解决什么

本层把 Risk-Off V62 的下跌防护和滤波择时的上涨捕获放回同一套基础设施。
它不再把“做多策略”和“空仓/做空策略”当成两套工具，而是让同一个择时工具
分别从两个职责观察：

- `upside_capture`：哪些上涨机会应由哪个工具优先认领；
- `downside_protection`：哪些下跌风险应由哪个工具优先认领。

消费者再把认领结果映射为自己的动作。Risk-Off 可以映射为空仓，滤波择时可以
映射为做多/持有；基础设施本身不规定必须做空或必须做多。

## 2. 当前十五工具

当前机器入口是 `tool_registry_v1_5`：冻结 V1.4 的十四工具作为前缀，并追加
`lowpass_bandpass_lat_channel`（低通带通 LAT 通道）。V1.4 本身已经把论文核
多尺度趋势登记为第十四工具。

历史 V1.3 的 `causal_jump_gap_shock` 没有进入当前表。它曾被试作第十四工具，
但独立执行责任已被撤销，只保留历史诊断身份。因此当前是十五个现役研究工具：
十三工具前缀 + 论文核 + LAT，不是十三加两个跳过论文核。

LAT 注册身份仍是无缝 P64 / k=1.5 对照，不是六桶配方，也不是参数终局。
六桶方法见 [做多](market_state_lat_six_bucket_hf_method_workflow.md) 与
[做空](market_state_lat_short_six_bucket_hf_method_workflow.md)。

构建：

```bash
PYTHONPATH=src python scripts/build_market_state_tool_registry_v1_5.py
```

## 3. 优先级如何工作

每一侧各有一条独立的瀑布：

```text
全部待分配K线 R0
  -> 第一优先工具认领 C1，剩余 R1
  -> 第二优先工具只看 R1，认领 C2，剩余 R2
  -> ……
  -> 仍无人认领的K线保持 unassigned
```

形式化为：`Ck = R(k-1) ∩ E(tool_k, side)`，
`Rk = R(k-1) \ Ck`。因此同一方向上一根K线最多只有一个责任工具，后层不能
抢回前层已认领的K线。

当前 V1 只冻结上述组合语义，两个 `priority_ladder` 都是空列表；没有读取收益，
没有选出任何具体顺序，也没有定义做多侧和风险侧同时命中时的跨侧仲裁。

构建：

```bash
PYTHONPATH=src python scripts/build_market_state_timing_priority_composition.py
```

输出：

- `artifacts/market_state/tool_registry_v1_5/tool_registry.json`
- `artifacts/market_state/timing_priority_composition_v1/framework.json`

## 4. 后续填优先级的最低要求

以后每加入一层，必须先明确：工具身份、方向职责、因果状态条件、优先级、可认领
K线、被前层拿走后的剩余样本，以及训练外稳定性和图形归因。两侧分别研究，不能
把 Risk-Off 的空仓收益与滤波策略的持有收益混为同一个评价口径。

未通过这些证据前，只能形成候选顺序；不得修改 V62、滤波择时或生产动作。

## 5. 权限边界

当前状态是 `framework_only_no_priority_selected`。生产权、动态参数权、工具路由权
全部为 `false`。论文核工具已有严格因果实现和可运行基准，但其架构仍是 provisional，
注册为工具不等于锁定其参数或授予第一优先级。

原理与治理边界见
[择时策略组合优先级基础设施白皮书](../ops/market_state_timing_priority_composition_whitepaper.md)。

空瀑布之上的首个具体架构原型进入
[三层双向择时策略路由工作流](market_state_timing_strategy_routing_workflow.md)：固定三级顺序，
其最新顶层已冻结为“暴跌反弹up优先 + P48→P96真通道up/down接严格余集”；旧
W12/W24通用通道路由只保留历史兼容。普通趋势与横盘下钻负责人仍由后续同桶Battle决定。
