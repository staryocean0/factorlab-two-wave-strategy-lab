# 择时资产类别成本边界工作流

> 四层归属：`4 执行标的/账户测试`。当前统一入口：[Layer 4 执行工作流](timing_layer4_execution_workflow.md)。

当前唯一机器口径：[`timing_asset_cost_boundary_registry@2.0.json`](../ops/timing_asset_cost_boundary_registry@2.0.json)。
V1 四合同注册表只保留历史复现，`current=false`。

## 先选资产身份

- 股票：使用`EQUITY_1BP_6BP`。
- 境内股票ETF：使用`STOCK_ETF_1BP_1BP`（佣金各1bp，不是完整成本）。
- 非可交易指数信号研究：使用`INDEX_SIGNAL_ZERO_EXPLICIT_COST`。
- 指数方向的个股复制敏感性：使用`INDEX_SIGNAL_EQUITY_7BP_SENSITIVITY`，不得当成可交易账户。
- MO长期权：使用`MO_LONG_OPTION_ASK_BID_CNY14`。
- MO短期权：使用`MO_SHORT_OPTION_BID_ASK_CNY14`。

禁止只看“都是择时策略”就共用一个成本数字。

## 价格和费用

长期权：

```text
价格收益 = exit_bid / entry_ask - 1
手续费后收益 = 价格收益 - 28 / (entry_ask × 100)
```

短期权的价格方向为Bid卖出、Ask买回。Bid/Ask只是价格，显式费用仍只有14元/边。

## 验证

```bash
PYTHONPATH=src pytest -q tests/unit/test_timing_asset_cost_boundary.py
ruff check src/factor_lab/market_state/timing_asset_cost_boundary.py tests/unit/test_timing_asset_cost_boundary.py
basedpyright src/factor_lab/market_state/timing_asset_cost_boundary.py tests/unit/test_timing_asset_cost_boundary.py
```

机器口径见`../ops/timing_asset_cost_boundary_registry@2.0.json`，原理见`../ops/timing_asset_cost_boundary_whitepaper.md`。V1 注册表不得再作为新研究入口。
