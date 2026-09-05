# 第 1 层数据时钟：DataHub 造 bar / FactorLab 消费白皮书

> **第 1 层 · 数据时钟。** 只负责切 bar、收线时刻、信号价/成交价和闸。不算 K 线属性，不认领方向，不选合约。
> 当前造 bar 真源在 DataHub。FactorLab 不再维护第二条墙上时钟切 bar 工厂。
> 机器合同：[`timing_layer1_datahub_clock_split@1.0.json`](timing_layer1_datahub_clock_split@1.0.json)

日期：2026-09-01
状态：Implemented as current interface authority / `production_authority=false`
范围：墙上时钟切 bar、中午收盘日线、按需 2/3/10/20m、研究菜单、成交配对、库存闸、云脊连续钟例外

---

## 一屏结论

这是同一条功能链，两边必须分工，禁止再各造一套 bar。

```text
DataHub 负责造 bar
  1m raw canonical
  官方会话端标签 v2（5/15/30/60m/1d）
  加法墙上时钟错位（session_wall_clock + session_offset_minutes）
  中午收盘日线（close_anchor=11:30）
  按需 2/3/10/20m offset_0
  按需 qfq/hfq
  first_tradable_slot 只提示，不成交

FactorLab 负责消费与配对
  研究菜单（问 DataHub 哪一档，而不是自己切）
  信号 qfq vs 成交 raw/pit
  成交窗配对（same_day_afternoon / next_tradable_after_bar_close / legacy next_session）
  库存闸（可减仓、推迟进、提前出，不能翻向）
  云脊午休连续钟 shifted_session_clock@1.0（研究载体，不是墙上时钟工厂）
  旧下午重做包只读；后继重做必须重新问 DataHub
```

DataHub 金样 `60m+5` / `15m+15` 只证明能力存在。FactorLab 研究默认没有这两档，也没有 `60m+5`、`15m+15`。不要把金样抄成菜单，也不要为了“更多花样”开 offset 选参。

---

## 为什么要切开

以前同时活着三条造 bar 路径：

1. DataHub `GET /api/v1/history/bars` 的加法查询（正确，墙上时钟）
2. FactorLab `derive-shifted-bars` 本地连续钟（云脊午休跨越，不是墙上时钟）
3. 从旧云脊 60m/15m 包下午重切（历史并列包，不是新构造器）

第 1 条已经能覆盖墙上时钟错位和中午收盘。第 2、3 条继续假装自己是通用切 bar，就会和 DataHub 重复，也会把连续钟、历史重做和研究菜单混成一个“第一层”。

本轮不新开 offset，不把第 2 条删掉（云脊还要用连续钟），但把它降权为**唯一允许的 FactorLab 造 bar 例外**。

---

## DataHub 做什么 / 不做什么

做：

| 产品 | 入口 | 合同 |
|---|---|---|
| 官方会话 K 线 | `GET /api/v1/history/bars` 不传新参数 | `cn_a_session_end_label_no_noon_partial_v2` |
| 墙上时钟错位 | 同入口 + `bar_align=session_wall_clock` + `session_offset_minutes` | `cn_a_session_wall_clock_offset_v1` |
| 中午收盘日线 | 同入口 + `frequency=1d` + `close_anchor=11:30` | 同上 |
| 2/3/10/20m | `GET /api/v1/history/on-demand-klines` | `factorlab_on_demand_kline_intervals.v1` |
| qfq/hfq | `/history/bars` 按需从 1m raw + 因子派生 | 既有 deriver |

不做：

- 自动套用 FactorLab 研究菜单
- `bar_align=session_clock_continuous`（午休连续钟）
- 把官方 latest 或钉死 V9 15:00 QFQ 改成 noon-close
- 成交、滑点、库存闸、方向

真源：`../../unified_datahub/docs/modules/history/session-offset-bars-whitepaper.md`

---

## FactorLab 做什么 / 不做什么

做：

| 能力 | 现役入口 | 说明 |
|---|---|---|
| 研究菜单 / fetch 回落 | `session_offset_defaults.py` | 日线 11:30 / 14:00 / 14:30；小时 +15/+30/+45；15m 只有 +5/+10 |
| 成交配对 | `standard_backtest_service.py` | 信号可 qfq，成交必须 raw/pit |
| 按需 2/3/10/20m 消费 | `csi1000_datahub_on_demand_kline_binding` | 只问 DataHub，禁止本地重采样 |
| 5m 研究运行时 | `csi1000_5m_research_runtime` | 消费 DataHub 5m，不另切 |
| 时段闸 | `session_clock_reference` | 指数 / IM / MO 分地图，不能翻向 |
| 云脊连续钟 | `shifted_bar_service` | 只允许 `shifted_session_clock@1.0` |
| 历史下午重做 | `daily_afternoon_remake` | 旧包只读；后继必须 DataHub fetch |

不做：

- 本地把 1m/5m 重采样成墙上时钟 5/15/30/60m/1d
- 本地造 2/3/10/20m
- 把 `derive-shifted-bars` 当成 `60m+30` / `15m+5` 工厂
- 从旧云脊包再切一版当作新的 DataHub 兼容层
- 把 `60m+5` 或 `15m+15` 写成研究默认

日线 14:00 代理尤其不是新切 bar：DataHub 给官方 `60m+0`，FactorLab 只**挑选** 14:00 那根。`60m+30` 的完整标签是 `11:00/14:30`，不能改名成 14:00。

---

## 现役七个时钟资产怎么读

它们不是七个造 bar 引擎。切开之后：

```text
造 bar（DataHub）
  unified_offset_data_and_backtest     -> 只保留菜单和配对，fetch 问 DataHub
  datahub_on_demand_kline_binding      -> 消费 2/3/10/20m
  csi1000_5m_research_runtime          -> 消费 5m

例外造 bar（FactorLab 研究载体）
  shifted_bar_derivation               -> 仅午休连续钟

不是造 bar
  daily_afternoon_remake               -> 历史并列包 / 后继改走 DataHub
  session_clock_reference              -> 闸
  cloudridge_beta_index_reference      -> 指数算法，只引用
```

---

## 后继禁令

1. 不为整齐把连续钟下沉 DataHub；要下沉必须另开 `bar_align=session_clock_continuous` 和新合同。
2. 不把第 1 层扩成策略中台。
3. 不改十五工具公式、第一层 V3 认领、绿波 / Risk-Off / LAT。
4. `production_authority=false`。

## 合成路径适配器，不是第二工厂

`src/factor_lab/data/unified_kline_v2.py` 只把 DataHub `session_offset_contract.py` 的分桶函数应用到云脊自己的 1m 合成路径。云脊指数不是 DataHub 上市品种，所以不能改问 `/history/bars`。这不是第二条墙上时钟产品。上市标的的新研究仍必须走 DataHub。

## 五位一体

| | FactorLab | DataHub |
|---|---|---|
| 合同 | `docs/ops/timing_layer1_datahub_clock_split@1.0.json` | `config/reliability/consumer_contracts/factorlab_timing_layer1_clock.v1.json` |
| 白皮书 | 本文 | `docs/modules/history/session-offset-bars-whitepaper.md` |
| 工作流 | `docs/user/timing_layer1_datahub_clock_split_workflow.md` | `docs/modules/history/session-offset-bars-workflow.md` |
| 代码 | `session_offset_defaults.py`、`datahub_fetch_service.py`、连续钟例外 `shifted_bar_service.py` | `session_offset_contract.py`、`bars_deriver.py` |
| 测试 | `tests/unit/test_timing_layer1_datahub_clock_split.py` | `tests/unit/storage/test_factorlab_timing_layer1_clock_split.py` |
