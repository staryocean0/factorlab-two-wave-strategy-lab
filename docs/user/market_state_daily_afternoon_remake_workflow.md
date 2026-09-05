# 市场状态日线下午收盘并列重做工作流

> **第 1 层 · 数据时钟。** 只负责切 bar、收线时刻、信号价/成交价和闸。不算 K 线属性，不认领方向，不选合约。第 2 层测量消费本层时钟，不得反过来改本层。归属清单 asset `daily_afternoon_remake`。

旧 15:00 日线包只读。本工作流留下的 `dual-scale-remakes/` 是历史并列包，不是新的造 bar 工厂。后继下午/相位重做必须通过 DataHub `/history/bars` 拉官方 `60m+0` 选 14:00、或 `30m+30` 选 14:30，不得再从旧云脊包重切。分工见 [`timing_layer1_datahub_clock_split_workflow.md`](timing_layer1_datahub_clock_split_workflow.md)。

白皮书：[`../ops/unified_offset_data_and_backtest_whitepaper.md`](../ops/unified_offset_data_and_backtest_whitepaper.md)  
身份账本：`src/factor_lab/market_state/timing_artifact_identity.py`

## 产物

```text
output/market-state-foundation/dual-scale-remakes/
  daily_to_60m_close_1400.csv
  daily_to_60m_close_1400.manifest.json
  daily_to_30m_close_1430.csv
  daily_to_30m_close_1430.manifest.json
  ledger.json
```

每个 manifest 都带：

- `parent_artifact_id`
- `data_contract` / `close_time`
- `execution_window=same_day_afternoon`
- `optimistic_research_only=false`

## 命令

```bash
uv run python scripts/build_market_state_daily_afternoon_remakes.py
uv run pytest tests/unit/test_timing_artifact_identity.py -q
```

## 禁止

- 改 `output/baylum-data-update/current/cloudridge_1d_qfq_service_confirmed_*.csv`
- 把 14:00 / 14:30 说成新的项目默认日线
- 拿新数字覆盖旧回测表

## 对照规则

官方 1d 与 60m/15m 云脊包方向一致，但指数基数不同（约 8.7 倍）。并列时只比收益、回撤、成交窗口，不比原始 close。14:00 / 14:30 两版之间可以比 close，因为它们来自同一套 1 分钟路径包。

## 日线基础设施并列重做

日线切出来之后，用同一套 14:00 / 14:30 价格重做六轴、论文核、统一择时基础设施：

```bash
uv run python scripts/build_market_state_daily_infrastructure_remakes.py
```

输出在：

```text
output/market-state-foundation/dual-scale-remakes/<variant_id>/
  timing_six_axis/
  paper_kernel_multiscale/
  unified_timing_infrastructure/
output/market-state-foundation/dual-scale-remakes/daily_infrastructure_ledger.json
```

`output/market-state-foundation/*/current` 仍是旧 15:00 权威，只读。

## 小时 / 15 分钟对齐

```bash
uv run python scripts/build_market_state_intraday_phase_remakes.py
uv run python scripts/build_market_state_intraday_infrastructure_remakes.py
```

- 小时：`hourly_to_30m_offset_15` 只作为价格并列（A2 不认 30m）；`hourly_to_60m_offset_30` / `hourly_to_60m_offset_45` 各出测量包，并按日线打样重做 group2 envelope 四工具并列包。
- 15 分钟：`quarter_to_15m_offset_5` / `quarter_to_15m_offset_10` 仍是 15 分钟 K 线，5 分钟步进相位；测量包之外，再各出一份 15m 论文核因子完整性并列包。
- 账本：`intraday_phase_ledger.json`、`intraday_infrastructure_ledger.json`、`intraday_foundation_ledger.json`。
- `output/market-state-foundation/current`、官方 60m/15m levels、以及 `*/current` 只读，不覆盖。

envelope 四个工具必须齐：

```text
bollinger_volatility_channel          # 60m
frequency_selective_bollinger_channel # 15m
butterworth_lowpass_residual_envelope # 15m
causal_asymmetric_arc_state_space_envelope # 15m
```
