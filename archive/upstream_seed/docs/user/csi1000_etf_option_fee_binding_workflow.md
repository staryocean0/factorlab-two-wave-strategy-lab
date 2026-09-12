# ETF期权手续费绑定工作流

> 四层归属：`4 执行标的/账户测试`。当前统一入口：[Layer 4 执行工作流](timing_layer4_execution_workflow.md)。

普通买卖成本使用`price_etf_option_trade_cost`：报价乘10,000和张数得到权利金现金，手续费按4.5元×张数×交易边数计算。`transaction_side_count=1`表示单边，`2`表示普通买卖往返。

本合同不允许行权/指派路径，也不授予ETF期权行情读取权。只有DataHub固定版本盘口产品通过FactorLab独立验收后，才能把价格、五档深度或quote-change状态接入回放。

验证：

```bash
PYTHONPATH=src pytest -q tests/unit/test_csi1000_datahub_gap_closure.py
PYTHONPATH=src python scripts/validate_csi1000_datahub_gap_closure.py
```
