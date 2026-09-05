# 三层双向择时策略路由基础设施白皮书

> 历史研究设计。其`architecture_locked`和`installed`表述已被
> `timing_strategy_identity_registry@2.0`撤销。当前V4只是
> `research_pending_requalification`，无已注册使用、纸交易、实盘或生产权限。

> 四层归属：Layer 3b 时效原型；可被更完整 Layer 2 测量取代，不是长期底座。
> 路由 V4 与第一层 V3 的既有认领、入场和退出公式保持不变。

## 当前架构裁决

`timing_strategy_router_v4` 取代旧 V3，固定三层责任瀑布，但只锁定第一层：

1. 高斜率行情：暴跌反弹优先，P48→P96 真通道负责余集的上涨与下跌；
2. 低斜率普通趋势：只处理第一层严格余集，负责人未选；
3. 横盘尺度下钻：只处理前两层严格余集，负责人未选。

第一层当前版本是 `timing_explosive_layer_v3`。完整三层策略仍未完成。

## 为什么替换旧 W12/W24 通用通道

W12/W24 可以识别高斜率短脉冲，却会把长通道切碎；普通反弹容易结束一次持有，因此
它更接近短趋势工具。三阶段归因显示它在 2021—2026 对长下跌生命周期的覆盖明显
退化，不能继续代表基础设施的通用通道。

P48→P96 使用多尺度轨道和反向轨退出。入场由因果速度、加速度与外轨突破共同授权；
进入后，通道内回撤或反弹不夺走持有权，只有穿越另一侧轨道才退出。两层在现有市场
样本中已经覆盖主要可用级别；P192只保留为大级别下跌专用研究，P384不进入通用层。

## 为什么 W12/W24 仍然出现在暴跌反弹内部

V3替换的是反弹的入场质量测量，不是删除其“先跌后弹”形态。已经完成的W12/W24
下跌第一腿仍是反弹工具的内生上下文，不是独立背景桶，也不产生通用通道路由权；
FDA速度/加速度只决定随后弧线反弹是否值得参加。

## 第一层公式

```text
R  = registered_arc_lifecycle(
       recent_completed_W12_W24_down,
       prior_FDA_velocity>0 AND prior_FDA_acceleration>0
     )
TC = FDA_true_channel(P48 -> P96, opposite_rail_exit)

RU = R
TU = (TC == up)   AND NOT R
TD = (TC == down) AND NOT R

remaining = NOT (RU OR TU OR TD)
```

三个责任掩码互斥，真通道始终影子计算。暴跌反弹结束后可直接交还上涨通道；反弹
失败后也可直接交还下跌通道，不要求重新形成一次通道入场边缘。

## 三阶段证据

| 路由 | 2009—17年均净价值 | 2018—20 | 2021—26 |
|---|---:|---:|---:|
| 暴跌反弹 up | +0.1002 | +0.1068 | +0.0128 |
| P48→P96 通道 up | +0.2037 | +0.0766 | +0.1496 |
| P48→P96 通道 down | +0.1382 | +0.1399 | +0.1285 |
| 第一层组合 | +0.4475 | +0.3275 | +0.2929 |

九个方向—区间交叉项全部为正；最终责任重叠为0，余集恒等式通过。V3相较V2三段
年均净价值和夏普都提高；外部期反弹桶本身基本持平，没有包装成显著增益。

代价也必须保留：V3开发期最大回撤28.22%，高于V2的26.28%；2018—2020则由
25.08%降至18.43%，外部期同为16.06%。这仍是第一层账户，不是完整三层组合结论。

## 工程权威和历史谱系

- 第一层：`src/factor_lab/market_state/timing_explosive_layer_v3.py`；
- 三层合同：`src/factor_lab/market_state/timing_strategy_routing_v4.py`；
- 构建：`scripts/build_market_state_timing_strategy_router_v4.py`；
- Schema：`docs/schemas/json/market_state_timing_strategy_router@4.0.json`；
- 复算：`scripts/research_market_state_timing_explosive_layer_v3.py`；
- 证据：`docs/ops/evidence/market_state_timing_explosive_layer_v3_20260804.md`。

旧 `context_free_explosive_two_bucket.py`、`timing_strategy_routing_v2.py`、旧三桶和
V62 构建继续作为历史复现/兼容入口，不得被解释为当前项目级权威。

`timing_three_bucket_iir_reference_v1` 是后来建立的基础设施级组合复现样板，采用不同
的专门桶和动态 IIR 剩余负责人。它不继承本白皮书的 V5 身份，也不替换 V4 或第一层
V3；详情见其[独立白皮书](market_state_timing_three_bucket_iir_reference_v1_whitepaper.md)。

## 权限

第一层 `research_authority=true`、`architecture_lock_authority=true`。参数权、生产权、
V62 运行时修改权均为 `false`；第二、第三层保持 `owner_not_selected`，不得在没有独立
证据的情况下填入任何工具负责人。
