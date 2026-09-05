# 波动率识别器等预算嵌套优化 V2 工作流

> 四层拆分：连续波动特征由 Layer 2 adapter 输出；低/中/高三态、滞回与驻留
> 由独立 Layer 3b adapter 消费。3b 可被更完整 Layer 2 测量取代，不是长期底座。

当前唯一识别器入口。默认参数 Battle `@1.0` 只保留历史复现。

当前权威结论：简单滞回家族第一，简单分位第二，Bipower硬分桶第三，Bipower-CUSUM最后。

证据根：`docs/ops/evidence/market_state_volatility_regime_recognizer_nested_v2_20260829/`。

复现命令依次为：构建预注册、按年运行`--outer-year 2016..2020`并人工封存、`--freeze-final`、按年运行`--repeat-year 2022..2024`，最后运行`finalize_volatility_regime_recognizer_nested_v2.py`与`validate_volatility_regime_recognizer_nested_v2.py`。

下一阶段使用简单滞回作为三桶完整策略根，简单分位作为必须保留的对照。
