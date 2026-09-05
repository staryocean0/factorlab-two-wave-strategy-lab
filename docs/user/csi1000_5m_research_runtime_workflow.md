# CSI1000五分钟研究Runtime工作流

> **第 1 层 · 数据时钟。** 只负责切 bar、收线时刻、信号价/成交价和闸。不算 K 线属性，不认领方向，不选合约。第 2 层测量消费本层时钟，不得反过来改本层。归属清单 asset `csi1000_5m_research_runtime`。

1. 信号只读DataHub固定`5m_offset_0`；
2. offset1--4并列报告边界敏感性，不得按收益选相位；
3. 调用`attach_next_one_minute_open()`连接下一可交易1分钟raw open；
4. 策略参数、路由和生产权限保持关闭。

验证：

```bash
PYTHONPATH=src python scripts/build_csi1000_5m_research_runtime_v1.py --overwrite
PYTHONPATH=src python scripts/validate_csi1000_5m_research_runtime_v1.py
PYTHONPATH=src pytest -q tests/unit/test_csi1000_5m_research_runtime.py
```

5m 棒由 DataHub 造，本层只钉 `5m_offset_0` 并配对下一根可交易 1m open。禁止本地重采样。分工见 [`timing_layer1_datahub_clock_split_workflow.md`](timing_layer1_datahub_clock_split_workflow.md)。
