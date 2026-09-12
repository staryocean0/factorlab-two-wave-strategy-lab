# 统一多尺度 K 线与属性基础设施入口

这是“七载体 × 十四个真实时钟视图 × 年度 K 线属性 atlas”的唯一渐进入口。
它负责跨指数、跨 K 线级别的可比研究数据面，不负责选择 LAT 主频段、调参、
生成买卖信号或授予生产权。

如果任务只是普通 DataHub 拉数或回测配对，先读
[`第1层 DataHub 造 bar 分工`](timing_layer1_datahub_clock_split_workflow.md) 与 [`统一 offset 数据与回测工作流`](unified_offset_data_and_backtest_workflow.md)。
如果任务是已有择时方向、只需决定隔夜/早盘/13:00–14:00 库存，改走
[`中证1000 时段时钟参考层`](market_state_session_clock_reference_workflow.md)。
如果任务只使用旧 Cloudridge 日线属性字典与 MA 面板，仍读
[`CloudRidge 属性基础设施`](cloudridge_attribute_infrastructure.md)。
只有涉及 Cloudridge 与市场指数的多尺度比较、LAT K 线归因或统一属性 atlas
时，才沿本入口继续。

## Layer 0：先确认它是什么

- 载体：Cloudridge、上证50、沪深300、中证500、中证1000、科创50、创业板指。
- T+0 低层视图：`1m_official` 与 `5m+0/+1/+2/+3/+4`。
- 继承视图：`15m+5/+10`、`30m+15`、`60m+30/+45`、`1d@11:30`、
  官方 `60m+0` 选择 14:00、`30m+30` 选择 14:30；V2八视图只读未覆盖。
- 信号/成交：Cloudridge 信号用 qfq，fill 用 raw；市场指数点位是 identity signal，
  fill 仍标为 raw/pit。
- 当前统一比较终点：`2026-06-24`，由 Cloudridge qfq/raw 共同权威窗口决定。
- 市场指数高频权威起点：`2015-01-01`；严重缺口日和熔断日从1m/5m atlas排除。
- 高频频带：V3在P29—P95之外新增P10（约0.61日）和P17（约1.08日）。
- 研究权限：只产 K 线与属性素材，不产策略结论。

## Layer 1：再读权威合同

1. [统一多尺度 K 线与属性基础设施白皮书](../ops/market_state_unified_kline_attribute_infrastructure_whitepaper.md)：
   本设施的身份、职责、数据血缘、代码、测试、重建和升级门禁。
2. [项目级 offset 数据与回测白皮书](../ops/unified_offset_data_and_backtest_whitepaper.md)：
   wall-clock 分桶、qfq/raw 配对和成交窗口的上位合同。
3. [CloudRidge 属性基础设施白皮书](../ops/cloudridge_attribute_infrastructure_whitepaper.md)：
   旧单载体日线属性字典的独立身份；它不是本设施的旧版本。

## Layer 2：查看物化数据

DataHub 六指数 manifest：

```text
/home/starryocean/桌面/量化/unified_datahub/.runtime/live/exports/
factorlab_unified_index_kline_v3_20260824/manifest.json
```

FactorLab Cloudridge manifest：

```text
artifacts/market_state/unified_kline_attribute_infrastructure_v3_20260824/
cloudridge/manifest.json
```

两者都必须满足 `research_ready=true`，并通过时钟、覆盖、OHLC、重复键和
确定性重放门禁。禁止只看到 Parquet 文件存在就声称 ready。

## Layer 3：消费属性 atlas

```text
artifacts/market_state/unified_kline_attribute_infrastructure_v3_20260824/
attribute_atlas/annual_kline_attribute_atlas.parquet
```

主键是 `carrier + year + view_id`；同时携带 `frequency`、
`session_offset_minutes`、`bars_per_day`、物理日尺度合同和构造合同。
当前 V3 atlas 为 98/98 个 carrier-view 对、1204 行、重复键 0，并含
P10/P17/P29/P38/P43/P48/P53/P67/P95 九个频带。

属性只能作为跨载体/跨时钟描述材料。要把某个属性、频段或视图用于 LAT
选择或策略变更，必须另启 `$strategy-slice-rebuild`，不得在本设施内直接寻优。

## Layer 4：重建、测试与证据

代码与脚本：

- `src/factor_lab/data/session_offset_defaults.py`
- `src/factor_lab/data/unified_kline_v2.py`
- `src/factor_lab/market_state/lat_kline_attribute_atlas.py`
- `scripts/build_cloudridge_full_datahub_levels.py`
- `scripts/materialize_cloudridge_unified_kline_v2.py`
- `scripts/materialize_lat_unified_kline_attribute_atlas_v2.py`
- `scripts/materialize_cloudridge_unified_kline_v3.py`
- `scripts/materialize_lat_unified_kline_attribute_atlas_v3.py`

最小测试：

```bash
.venv/bin/pytest -q \
  tests/unit/test_build_cloudridge_full_datahub_levels.py \
  tests/unit/test_session_offset_defaults.py \
  tests/unit/test_unified_kline_v2.py \
  tests/unit/test_lat_kline_attribute_atlas.py \
  tests/unit/test_materialize_cloudridge_unified_kline_v3.py \
  tests/unit/test_materialize_lat_unified_kline_attribute_atlas_v3.py \
  tests/unit/test_unified_kline_infrastructure_documentation.py
```

本轮验收证据：

- [最终报告](../ops/evidence/market_state_unified_kline_attribute_infrastructure_20260824/final_report.md)
- [预注册边界](../ops/evidence/market_state_unified_kline_attribute_infrastructure_20260824/preregistration.json)
- `cloudridge_result.json` / `attribute_atlas_result.json`
- [V3 T+0下钻报告](../ops/evidence/market_state_unified_kline_attribute_infrastructure_v3_20260824/final_report.md)

证据报告记录一次物化事实；白皮书负责长期合同；本入口负责导航。三者不得互相替代。
