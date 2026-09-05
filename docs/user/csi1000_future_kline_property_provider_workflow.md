# CSI1000未来K线属性Provider工作流

1. 只从已完成K线构建`build_causal_property_features()`；
2. `build_future_property_target()`只能在训练/评价离线标签路径调用；
3. 明确截断训练前缀后调用`fit_research_property_provider()`；
4. 使用最新完整特征调用`forecast_property()`；
5. 输出卡不得直接触发LAT/IIR、仓位或生产动作。

验证：

```bash
PYTHONPATH=src python scripts/build_csi1000_future_kline_property_provider_v1.py --overwrite
PYTHONPATH=src python scripts/validate_csi1000_future_kline_property_provider_v1.py
PYTHONPATH=src pytest -q tests/unit/test_csi1000_future_kline_property_provider.py
```

