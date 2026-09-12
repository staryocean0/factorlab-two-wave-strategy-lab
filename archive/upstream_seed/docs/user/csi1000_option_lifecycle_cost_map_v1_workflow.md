# 中证1000 MO 生命周期成本地图 V1 工作流

> 四层归属：`4 执行标的/账户测试`。当前统一入口：[Layer 4 执行工作流](timing_layer4_execution_workflow.md)。

## 1. 构建

```bash
PYTHONPATH=src python scripts/build_csi1000_option_lifecycle_cost_map_v1.py
```

构建器必须先验证 DataHub 固定版本与哈希，然后逐月：

1. 将成交触发3秒快照投影到五分钟 route grid；
2. 每个合约/时点只保留 route time 前最后可见且不超过120秒的双边盘口；
3. 连接严格同月且严格早于 route time 的 IM；
4. 连接按到期时间插值的PIT国债曲线；
5. 求 Bid/Mid/Ask IV和Black-76 Delta；
6. 计算EAS、28元Delta等价费率和两者合计；
7. 写月度明细和生命周期聚合图谱。

输出：

```text
artifacts/market_state/csi1000_option_lifecycle_cost_map_v1/
```

## 2. 验证

```bash
PYTHONPATH=src pytest -q \
  tests/unit/test_csi1000_option_lifecycle_cost_map.py \
  tests/unit/test_csi1000_instrument_state.py \
  tests/unit/test_csi1000_datahub_market_chain.py

PYTHONPATH=src python scripts/validate_csi1000_option_lifecycle_cost_map_v1.py
```

## 3. 测量祖先，不是策略输入（已撤销）

当前期权路由前置是工具身份画像，不是把本地图的平均 hurdle 交给策略去比。

> 撤销：策略提供 `expected_underlying_move_bp`、地图提供 `identified_round_trip_hurdle_bp` 作为回测/路由输入。  
> 本地图只保留当时买一/卖一、费用、Delta/Greeks 的测量权。成交必须用当时盘口，不得用样本平均半价差改写。

后继：[`../ops/timing_layer4_option_instrument_profile_rebuild_plan.md`](../ops/timing_layer4_option_instrument_profile_rebuild_plan.md)。

## 3x. 历史单笔策略接入（已撤销，原文保留为负例）


策略只提供载体无关的预期指数运动：

```text
expected_underlying_move_bp
```

工具地图提供：

```text
identified_round_trip_hurdle_bp
```

接入层可以计算：

```text
cost_coverage_ratio
  = identified_round_trip_hurdle_bp / expected_underlying_move_bp
```

但在没有策略专属校准和市场冲击前，该比率只能做诊断，不能自动产生硬阈值。

### 3.1 无历史期权数据时的有限回推

只允许调用同一基础设施函数：

```python
from factor_lab.market_state.csi1000_option_cost_backcast import (
    delta_equivalent_proxy_net_bp,
)

proxy_net_bp = delta_equivalent_proxy_net_bp(
    signed_underlying_gross_bp,
    identified_round_trip_hurdle_bp,
)
```

这只扣除已识别的完整价差与固定手续费。不得补造早期合约、IV、Gamma、Theta、冲击或基差。正式迁移校准见 `docs/ops/evidence/csi1000_option_lifecycle_cost_map_v1_20260831/transport_validation.json`；若其任一门失败，历史回推必须失败关闭。

## 4. 失败关闭

- 无同月IM、利率、双边报价或完整Bid/Mid/Ask IV：不计算成本卡；
- Delta小于0.05：拒绝，不做分母floor；
- 盘口超过120秒：拒绝；
- 冲击未知：保持`complete_all_in_cost_ready=false`；
- 不得把交易触发快照称为连续BBO；
- 不得读取策略收益选择“最佳时间/期限/档位”。
