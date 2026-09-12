# CSI1000 MO连续Quote-Change BBO工作流

> 四层归属：`4 执行标的/账户测试`。当前统一入口：[Layer 4 执行工作流](timing_layer4_execution_workflow.md)。

## 验收

```bash
PYTHONPATH=src python scripts/validate_csi1000_datahub_gap_closure.py
PYTHONPATH=src pytest -q tests/unit/test_csi1000_datahub_gap_closure.py
```

固定版本为`factorlab_csi1000_multi_carrier_v2p1_research_bundle_20250901_20260825_ready_v1_20260831`。只允许按handoff中的精确路径、dataset version和hash读取，禁止扫描latest。

`components/mo_bbo/events/**/*.parquet`是连续一档状态研究源。旧3秒成交后快照不能继续冒充连续BBO。用`compute_l1_quote_change_ofi`计算标准L1报价变化OFI；用`price_bounded_l1_marketable_fill`执行一档容量门。订单数超过对手一档数量时必须fail closed，不推断跨档VWAP。`partial_impact`只用于流动性响应描述。

该绑定不改变策略、路由、参数或生产状态。
