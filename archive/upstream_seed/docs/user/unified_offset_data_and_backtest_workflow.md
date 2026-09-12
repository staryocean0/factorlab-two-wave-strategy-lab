# 默认差分拉数与统一回测工作流

> **第 1 层 · 数据时钟。** 只负责切 bar、收线时刻、信号价/成交价和闸。不算 K 线属性，不认领方向，不选合约。第 2 层测量消费本层时钟，不得反过来改本层。归属清单 asset `unified_offset_data_and_backtest`。

项目级口径见 [`../ops/unified_offset_data_and_backtest_whitepaper.md`](../ops/unified_offset_data_and_backtest_whitepaper.md)。 造 bar 分工见 [`timing_layer1_datahub_clock_split_workflow.md`](timing_layer1_datahub_clock_split_workflow.md)。

## 新研究默认

1. 确认 DataHub 能查加法产品：`session_offset_minutes` / `close_anchor=11:30`。
2. 拉数不要传官方 15:00 dataset version。
3. 日线研究直接：

```bash
factor-lab datahub-fetch-bars \
  --symbol 000001 --market cn_a --frequency 1d \
  --start-time 2014-01-01T00:00:00Z --end-time 2014-12-31T15:00:00Z \
  --source-id datahub_cn_a_prices --dataset-name cn_a_daily_noon \
  --schema-version ds_pit@1.0 --layer pit
```

未传 `--close-anchor` 时，日线 fetch 回落到 `11:30` + `same_day_afternoon`；这只是菜单第一档，14:00 / 14:30 仍可选。

4. 60m 不传 offset 回落到 `+30`（完整收线 11:00/14:30，不是 14:00）；15m 不传 offset 回落到 `+5`。小时菜单只有 `+15/+30/+45`，没有 `60m+5`；15 分钟还可选 `+10`，没有 `15m+15` 研究默认。这些都是问 DataHub 的菜单，不是 FactorLab 本地切 bar。
5. 回测读 dataset metadata 的 `data_contract` / `execution_window`，不要再手填 `next_session`。
6. 需要旧对照时才加 `--legacy-official-session`，结果必须标明 `data_contract=official_1500`。

1 分钟 T+0 研究使用 `frequency=1m`、`fill_view=raw_canonical`，默认执行窗为
`next_tradable_after_bar_close`。统一账本允许 `-1..1` 双向信号并在下一棒
生效；负信号不会再被删除。现金指数本身不可交易时，结果仍只能标作方向归因，
不能因为账本支持双向就获得执行权限。

## 禁止

- 11:30 日线配 `next_session`
- 15:00 日线配 `same_day_afternoon`
- 用 qfq 当成交价
- 把 `backtest_signal()` 的 close-to-close 数字当成生产候选
- 新脚本硬编码 V9 15:00 却不标 legacy

## 验收

```bash
uv run pytest tests/unit/test_session_offset_defaults.py tests/unit/test_headless_cli.py -k datahub_fetch -q
```


## 旧择时基础设施可选重做

不要改旧 CSV / 旧回测包。按原生频率选菜单：

```text
旧日线结论 -> 60m 收到 14:00，和/或 30m 收到 14:30
旧小时结论 -> 30m 偏 15，和/或 60m 偏 45
旧 15 分钟结论 -> 15m 偏 5，和/或 15m 偏 10（5 分钟步进，K 线仍是 15 分钟）
```

Python：

```python
from factor_lab.data.session_offset_defaults import optional_remake_variants
optional_remake_variants("1d")
```

拉数时显式传目标 `frequency` 和 `session_offset_minutes`，不要指望默认 fetch 自动变成 14:00。

第一条竖切：[`market_state_daily_afternoon_remake_workflow.md`](market_state_daily_afternoon_remake_workflow.md)。

小时 / 15 分钟已按同一打样切出价格和测量包，并重做：

- `hourly_to_60m_offset_30/group2_envelope` 与 `hourly_to_60m_offset_45/group2_envelope`：四个 envelope 工具并列包
- `quarter_to_15m_offset_5/10/paper_kernel_15m_factor_timeseries`：15m 论文核因子完整性并列包
- 账本 `intraday_foundation_ledger.json`

官方 `*/current` 只读。
