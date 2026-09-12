# 择时经验公式注册与使用工作流

> 当前状态：`current / research-only`
>
> 本文是“经验公式”基础设施的唯一用户入口。经验公式不是因子、不是13工具、
> 不是参数默认值，也不是生产路由。

## 第0层：先判断该知识应该放在哪里

项目现在区分三类资产：

| 资产 | 回答的问题 | 入口 |
|---|---|---|
| 因子基础设施 | 某个可物化特征能否服务选股或择时 | [特征—因子工作流](feature_factor_library_workflow.md) |
| K线属性—工具关系基础设施 | 哪些K线属性可能改变13个择时工具的参数或相对能力 | [市场状态地基](market_state_foundation_workflow.md) |
| 经验公式基础设施 | 多次研究中出现了什么可复算关系、适用边界和反例 | 本文 |

经验公式保存的是“关系和边界”。它只有在以后被实现为严格因果输入、通过独立验证并
另行授权后，才可能进入因子或路由链；不得从本文直接跨过去。

## 第1层：当前经验公式

当前登记一条：

```text
short_scale_relative_churn_crossover_u_shape_v1
短周期跨尺度相对换手凹坑经验公式
```

白话定义：选一个短周期基准频段，例如S5；再让它逐个进入S10、S15、S20、S25、
S30等更慢频段认定的上涨桶里，与该慢频段battle。净相对价值有时不是单向增加或减少，
而是“近处能赢—中间失败—更远又能赢”的凹坑。

这里最容易算错的是成本。要比较的不是S5和S10谁的**绝对手续费**高，而是同一个
目标上涨桶里，S5比目标频段**多付了多少成本**。S10和S5会共享许多转向，所以两者
绝对换手都高时，相对额外成本仍可能很小；到S15/S20，目标线过滤掉许多反复而S5仍
切换，相对额外成本才明显上升；更远处成本差趋于饱和，S5规避大回撤的毛价值若继续
上升，净值便重新转正。

统一公式是：

```text
F_b(t,m)=G_b(t)-mC_b(t)
```

- `b`：基准频段；
- `t`：更慢目标频段；
- `G_b(t)`：目标上涨、基准空仓时，基准相对目标避开后续收益的毛方向价值；
- `C_b(t)`：同一目标上涨桶内，基准相对目标的额外交易成本；
- `m`：成本压力倍数；
- `F_b(t,m)`：成本后的净相对价值。

离散凹坑至少要有三个按周期递增的目标频段满足：

```text
t1 < t2 < t3
F_b(t1) > 0, F_b(t2) <= 0, F_b(t3) > 0
```

这比“手续费越高越差”的单向解释多了一次必要的右侧恢复。

## 第2层：候选增强怎么用

如果某个基准频段确实存在经过跨期验证的失败目标频段，候选增强才是：

```text
target_up            -> target_scale 负责
target_flat_or_down  -> base_scale 负责
```

也就是用户提出的做法：本频段打不赢的那个目标频段，其上涨桶交给目标频段自己；
目标频段的横盘和下跌桶仍由本频段负责。

但这只是研究模板。启用前必须同时满足：

1. 基准和目标使用相同公式、滞回、成本、执行时钟及目标桶；
2. 失败关系在预注册的开发期、前向期和压力面保持同方向；
3. `target_up`可由当时信息识别，不能事后回填；
4. 路由自身的增量价值另做回测和图形归因；
5. 另行申请工具路由权限。

任一项失败，就只保留经验公式，不创建路由。

## 第3层：怎样新增下一条经验公式

新增条目时必须同时保存：

- 会计恒等式或可执行判据；
- 适用的信号家族、K线频率、尺度、成本和时钟；
- 至少一个可复算观察切片；
- 支持证据和反证；
- 不适用范围；
- 候选用途及稳定性门；
- 四类权限字段和中文字段标签。

禁止只写一句自然语言“规律”。也禁止把一次回测的最佳参数登记成经验公式。

## 第4层：机器入口与复算

- 白皮书：[择时经验公式基础设施白皮书](../ops/market_state_empirical_formula_whitepaper.md)
- 当前机器快照：[`market_state_empirical_formula_registry@1.0.json`](../ops/evidence/market_state_empirical_formula_registry@1.0.json)
- 机器注册：`src/factor_lab/market_state/empirical_formula_registry.py`
- Schema：[`market_state_empirical_formula_registry@1.0.json`](../schemas/json/market_state_empirical_formula_registry@1.0.json)
- 构建：`scripts/build_market_state_empirical_formula_registry.py`
- 验证：`scripts/validate_market_state_empirical_formula_registry.py`
- 测试：`tests/unit/test_market_state_empirical_formula_registry.py`
- 原始证据：[S5高频段上涨桶Battle](../ops/evidence/risk_off_paper_kernel_s5_higher_scale_uptrend_battle_20260802.md)与[通用频段审计](../ops/evidence/risk_off_paper_kernel_universal_scale_crossover_20260802.md)

```bash
PYTHONPATH=src python scripts/build_market_state_empirical_formula_registry.py \
  --output output/market-state-foundation/empirical-formulas/current/registry.json

PYTHONPATH=src python scripts/validate_market_state_empirical_formula_registry.py \
  --input output/market-state-foundation/empirical-formulas/current/registry.json
```

构建注册表本身读取行情0行、收益0行；它只把已经存在的有界知识确定性发布出来。

## 当前结论边界

当前证据支持“部分短中周期中可能出现跨尺度凹坑”，不支持“任意频段必然有一个固定
倍数凹坑”。147组频段对中，只有S10与S20在开发和前向两段同时满足严格的单一失败
前缀定义；按周期比值拟合的约2.14或2.56倍边界，前向准确率还低于简单基线。

所以本条目的正确用法是**逐基准频段测量失败集合**，不是写死`5倍`、`2倍`或某个
固定目标周期。它不是因子，也不是生产路由。
