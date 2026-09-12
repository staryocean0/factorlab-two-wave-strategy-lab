# CSI1000 DataHub按需多周期K线工作流

> **第 1 层 · 数据时钟。** 只负责切 bar、收线时刻、信号价/成交价和闸。不算 K 线属性，不认领方向，不选合约。第 2 层测量消费本层时钟，不得反过来改本层。归属清单 asset `datahub_on_demand_kline_binding`。
> 禁止 FactorLab 本地重采样 2m/3m/10m/20m。不改 DataHub 产品身份。

## 验收

```bash
PYTHONPATH=src python scripts/validate_csi1000_datahub_gap_closure.py
PYTHONPATH=src pytest -q tests/unit/test_csi1000_datahub_gap_closure.py
```

## 正式读取

只使用`build_on_demand_kline_cli_command`生成DataHub CLI参数。运行必须显式给出`source_snapshot`、标的、品种、周期、起止时间和`as_of`。消费者固定`completeness_policy=fail`，不得读取`latest`，不得在FactorLab重采样。

返回payload必须先通过`validate_on_demand_kline_payload`；任一不完整棒、跨午休、跨日、错误源分钟数或超过`as_of`立即失败。

本接口提供K线输入，不提供策略成交语义。策略研究另行冻结信号完成时点和下一根可交易1分钟open。

造 bar 分工见 [`timing_layer1_datahub_clock_split_workflow.md`](timing_layer1_datahub_clock_split_workflow.md)。2/3/10/20m 只问 DataHub `on-demand-klines`。
