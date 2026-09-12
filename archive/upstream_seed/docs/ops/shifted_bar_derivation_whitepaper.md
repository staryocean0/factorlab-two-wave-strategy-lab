# Shifted Bar 派生数据接口白皮书

> **第 1 层 · 数据时钟。** 只负责切 bar、收线时刻、信号价/成交价和闸。不算 K 线属性，不认领方向，不选合约。第 2 层测量消费本层时钟，不得反过来改本层。归属清单 asset `shifted_bar_derivation`。

日期：2026-06-09  
状态：CloudRidge 午休连续钟研究载体 / 墙上时钟已归 DataHub  
范围：只覆盖 `shifted_session_clock@1.0`；墙上时钟请走 DataHub `/history/bars`

---

## 一屏结论

本接口不是通用错位 K 线工厂。它只从已发布的云脊路径构造 `shifted_session_clock@1.0` 午休连续钟，并重新发布为 Factor Lab dataset。

当前归属：

```text
DataHub：墙上时钟切 bar、中午收盘日线、按需 2/3/10/20m。
Factor Lab：只保留云脊午休连续钟 shifted_session_clock@1.0。
```

墙上时钟错位已经是 DataHub `/history/bars` 加法产品，不要再用本接口去造 `60m+30` / `15m+5`。
当前接口归 Factor Lab 研究载体；不得把 `derive-shifted-bars` 写成 DataHub 原生能力或 `/datahub/*` 路由。
分工见 [`timing_layer1_datahub_clock_split_whitepaper.md`](timing_layer1_datahub_clock_split_whitepaper.md)。

`shifted_session_clock@1.0` 是 CloudRidge 午休连续钟研究载体，不是墙上时钟差分菜单。FactorLab 研究菜单见 [`unified_offset_data_and_backtest_whitepaper.md`](unified_offset_data_and_backtest_whitepaper.md)：日线 11:30 / 14:00 / 14:30，小时 +15 / +30 / +45，15 分钟只有 +5 / +10。

墙上时钟错位已经下沉到 DataHub，不要再把本接口当通用工厂。午休连续钟若以后要下沉，必须另开 `bar_align=session_clock_continuous` 和新合同，不得污染 wall-clock。CloudRidge 的 12选1/2/3、BDCI、BCI/WBI、lag1 打分和近期窗口选择规则必须继续留在 Factor Lab。

---

## 接口

API：

```text
POST /api/v1/datasets/derive-shifted-bars
```

CLI：

```bash
factor-lab datasets derive-shifted-bars \
  --base-url http://127.0.0.1:18080 \
  --source-dataset-version cloudridge_5m_qfq_v1 \
  --source-id factor_lab_shifted_bars \
  --dataset-name cloudridge_60m_shifted \
  --schema-version ds_pit@1.0 \
  --layer pit \
  --market cn_a \
  --base-frequency 5m \
  --target-frequency 60m \
  --offset-minutes 35 \
  --session-template cn_a_regular \
  --view qfq_canonical
```

核心参数：

| 字段 | 含义 |
|---|---|
| `source_dataset_version` | 已发布的基础行情 dataset version，通常来自 `datahub-fetch-bars`。 |
| `base_frequency` | 源K线周期，例如 `5m`。 |
| `target_frequency` | 派生目标周期，例如 `60m`。 |
| `offset_minutes` | 相对交易会话开盘的错位分钟数，必须小于目标周期分钟数。 |
| `session_template` | 交易会话模板；当前支持 `cn_a_regular`。 |
| `include_tail_partial` | 是否保留尾盘不足一个完整目标周期的 partial bucket。 |
| `view` | 源行情视图标记，例如 `qfq_canonical`；用于元数据追踪。 |

输出是新的 dataset publish 结果，包含 `dataset_version`、`run_id`、`job_id`、`row_count` 和 `metadata`。

---

## K线构造口径

当前算法版本：

```text
bar_construction_version = shifted_session_clock@1.0
```

`cn_a_regular` 会话：

```text
09:30-11:30
13:00-15:00
```

分桶使用交易会话内累计分钟，不使用自然时钟分钟。这样 `11:00-11:30 + 13:00-13:30` 会被视为连续的 60 分钟交易时间，而不是被午休自然时间切断。

分桶口径沿用 CloudRidge offset 研究脚本的 endpoint 口径：

```text
offset 后的第一个完整桶 = (offset, offset + target_frequency]
```

例如 `target_frequency=60m, offset_minutes=30`：

```text
10:00-11:00
11:00-11:30 + 13:00-13:30
13:30-14:30
```

`include_tail_partial=false` 时不保留 `14:30-15:00`；设为 true 时保留。

OHLCV 聚合：

| 字段 | 规则 |
|---|---|
| `open` | bucket 第一行 open；若缺失则用第一行 close。 |
| `high` | bucket 内 high/close 最大值。 |
| `low` | bucket 内 low/close 最小值。 |
| `close` | bucket 最后一行 close。 |
| `volume` / `amount` | bucket 内求和。 |
| `timestamp` / `available_at` | bucket 最后一行时间。 |

每行会写入 `source_dataset_version`、`base_frequency`、`target_frequency`、`offset_minutes`、`session_template`、`include_tail_partial` 和 `bar_construction_version`，用于后续回测和审计。

---

## DataHub 边界

当前不把接口放到 `/datahub/*`。墙上时钟已经在 DataHub；本链路只服务云脊连续钟。

云脊连续钟链路：

```text
CloudRidge 5m 路径 dataset
  -> factor-lab datasets derive-shifted-bars   # 仅 session_clock_continuous
  -> shifted-bars dataset
  -> BDCI / BCI / WBI / lag1
```

墙上时钟链路不得经过本接口：

```text
DataHub GET /history/bars
  -> factor-lab datahub-fetch-bars
  -> 研究菜单 / 回测配对
```

已经下沉 DataHub 的是墙上时钟产品，不是本连续钟：

```text
GET /api/v1/history/bars
  frequency, bar_align=session_wall_clock|session_end_label_v2,
  session_offset_minutes, close_anchor
```

不得下沉：

```text
CloudRidge 当前推荐 35m
12选1/12选2/12选3
BDCI / BCI / WBI / lag1 打分
最近20/60/244交易日选择框架
```

这些仍由 Factor Lab 负责。

---

工作流：[`../user/shifted_bar_derivation_workflow.md`](../user/shifted_bar_derivation_workflow.md)

## 代码与测试

实现：

- `src/factor_lab/data/services/shifted_bar_service.py`
- `src/factor_lab/app/api/routers/datasets.py`
- `src/factor_lab/app/headless/cli.py`

测试：

- `tests/unit/test_shifted_bar_service.py`
- `tests/integration/test_shifted_bar_control_surface.py`
- `tests/unit/test_headless_cli.py`

相关治理白皮书：

- `docs/ops/cloudridge_bar_offset_robustness_whitepaper.md`
