# 择时策略全频段共同基础设施 V2.1 工作流

> 四层归属：Layer 2 全频段测量。入口只允许连续诊断与执行可得性预检，禁止
> 自动选择频段、策略、动作或仓位；`production_authority=false`。

## 先查机器评价，不凭字段名猜盈利

```python
from factor_lab.market_state import timing_profitability_attribute_registry

registry = timing_profitability_attribute_registry()
relation = registry["path_efficiency"]["profit_relationship"]
```

分类只有三种：

- `material_when_paired`：有材料解释力，但必须和规定层级配对；
- `conditional_diagnostic`：用于提出问题或识别测量缺口；
- `weak_or_misleading_standalone`：单独推断盈利明确禁止。

所有属性的`standalone_profitability_gate_authority`均为`false`。

## 通用市场路径诊断

```python
diagnostic = diagnose_frequency_panel(
    prices,
    contract=frequency_contract,
    trading_day=trading_day,
    lookback_bars=lookback,
    minimum_observations=minimum,
)
```

每个标的现在同时输出：

- 收益、波动率、bipower jump share与microstructure noise ratio；
- `path_efficiency_window`；
- `variance_ratio`的4/8/16棒结果；
- `sign_persistence`、`direction_reversal_rate`与平均方向run长度；
- 收益、绝对收益、平方收益自相关。

## 执行运输阶梯

```python
from factor_lab.market_state import build_execution_transport_ladder

ladder = build_execution_transport_ladder(
    {
        "index_signal": signed_index_returns,
        "option_reference": option_last_returns,
        "ask_bid": ask_bid_returns,
    }
)
```

输入按完全共同索引内连接，不前向填充。输出每层平均bp、胜率以及相对前一层损耗。

## 禁止事项

- 不得用高ACF、高方向持续率或高静态能量比直接认定可盈利；
- 不得只报告总毛收益而不报告每笔边厚度；
- 不得跳过可执行子样本指数边，直接把亏损全部归因给期权成本；
- 不得拿不同物理时长、不同载体或不同执行合同作最终盈利比较；
- 不得由任何一个属性自动选频段、参数或策略。

## 构建与验收

```bash
PYTHONPATH=src python scripts/build_market_state_all_frequency_timing_infrastructure.py
PYTHONPATH=src python scripts/validate_market_state_all_frequency_timing_infrastructure.py
pytest -q tests/unit/test_timing_all_frequency_infrastructure.py
```

构建和验证只使用合成数据，读取市场数据0行。
