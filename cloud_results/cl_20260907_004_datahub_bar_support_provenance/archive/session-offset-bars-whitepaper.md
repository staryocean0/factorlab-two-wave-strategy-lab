---
doc_id: WP-HISTORY-SESSION-OFFSET-BARS-001
truth_role: whitepaper
module_primary: history
module_related: [platform]
governed_surface: additive session-offset / close-anchor bars product
---

# 会话相位 / 收盘锚点 K 线白皮书

状态：Implemented for on-demand query (v1 wall-clock)
默认合同不变：`cn_a_session_end_label_no_noon_partial_v2`
加法合同：`cn_a_session_wall_clock_offset_v1`

## 一屏结论

DataHub 对外 bars 默认仍是官方会话端标签：

```text
60m: 10:30 / 11:30 / 14:00 / 15:00
1d:  T15:00:00Z
禁止独立 13:00 伪 bar
```

加法产品解决的是另一件事：把官方墙上时钟的网格错开，或把日线收到中午，让策略能在 **bar 收盘后的第一个可交易时点** 成交，而不是默认打到次日开盘的高低开。

这不是：

- Hilbert / IIR 滤波器相位
- 3 秒分笔 `session_phase`（集合竞价 / 连续竞价）
- FactorLab `shifted_session_clock@1.0` 的午休连续钟
- 小波研究跨交易日连续 60m

查询入口仍是 `GET /api/v1/history/bars`。不传新参数 = 官方 v2。传了新参数 = 按需派生加法产品，不改官方 latest，不改钉死 version。

加法产品是同一份 1 分钟 raw 的回测分桶，不是第二路实时行情。Terminal replay 必须继续点 1m raw；noon-close / offset 只给 FactorLab 回测用。

## FactorLab 可选研究菜单（不是 DataHub 默认）

DataHub 只提供墙上时钟错位能力。下面是 FactorLab 给旧择时研究的可选重做配方，**不是** `/history/bars` 的默认参数：

| 旧研究频率 | 查询 frequency | session_offset_minutes | 典型下午收盘 |
|---|---|---|---|
| 日线过渡 | 60m | 0（官方网格） | 选择 14:00 收线 |
| 日线过渡 | 30m | 30 | 选择 14:30 收线 |
| 小时过渡 | 30m | 15 | 10:15 起的半小时网格 |
| 小时过渡 | 60m | 30 | 完整收线 11:00 / 14:30 |
| 小时过渡 | 60m | 45 | 完整收线 11:15 / 14:45 |
| 15 分钟过渡 | 15m | 5 | 完整收线从 09:50 起 |
| 15 分钟过渡 | 15m | 10 | 完整收线从 09:55 起（平移 10 分钟） |

FactorLab 研究菜单不强制唯一：日线 11:30 / 14:00 / 14:30，小时只有 +15 / +30 / +45，15 分钟只有 +5 / +10。禁止把 60m+5 或 15m+15 写成研究默认，也禁止 `15m+45`。

FactorLab T+0研究面V3另行追加`1m_official`与`5m+0/+1/+2/+3/+4`，不改变
上述V2菜单。5m五相位只用于股指期货/期权等T+0研究评价，不自动成为策略
默认。1m稀疏日只能因果前值平铺并披露；严重缺口日从1m/5m属性atlas排除，
不得用未来值或把缺口静默视作横盘。

语义勘误：offset 指网格起点偏移，不是收线标签。`60m+30` 的真实
完整 bar 标签是 `11:00/14:30`，不能重命名成 14:00；日级 14:00
代理必须从官方 `60m+0` 网格选择 14:00 那根。

## 适合 / 不适合

适合：CN-A 股票 / ETF / LOF，从 1m raw 派生 5/15/30/60m，以及 1m 合成的中午收盘日线。

不适合 / 禁止原地改：

- FactorLab 钉死合同 `bars_cn_a_1d_qfq_canonical_xdxr_v9_factorlab_2009_2025_20260814`
- 交易所官方 15:00 日线事实源
- 期货夜盘、3s 分笔、NAV、宏观
- 把 15:00 日线的 `timestamp` 改写成 11:30 却仍聚合下午

## 查询参数

```text
GET /api/v1/history/bars
  frequency=1d|60m|30m|15m|5m|1m
  bar_align=session_end_label_v2|session_wall_clock
  session_offset_minutes=<int>
  close_anchor=15:00|11:30
  include_tail_partial=false|true
```

CLI：

```bash
datahubctl history bars \
  --symbol 000001 --market cn_a --frequency 60m \
  --start-time 2014-01-01T00:00:00Z --end-time 2014-12-31T15:00:00Z \
  --session-offset-minutes 5

datahubctl history bars \
  --symbol 000001 --market cn_a --frequency 1d \
  --start-time 2014-01-01T00:00:00Z --end-time 2014-12-31T15:00:00Z \
  --close-anchor 11:30
```

fail closed：

- 钉死 `dataset_version` + offset / noon-close
- `close_anchor` 用在 5m/15m/60m
- `session_offset_minutes` 用在 1d 或 1m
- 未知 `bar_align`

## 金样

算法：`session_wall_clock`。上下午分段，午休不跨段。残缺首桶和不足一根的尾桶默认丢弃。

```text
60m + offset 5
  09:35-10:35 → 10:35
  10:35-11:30 → 丢弃
  13:00 不得独立成 bar
  13:05-14:05 → 14:05
  14:05-15:00 → 丢弃

15m + offset 15
  09:30-09:44 丢弃
  09:45-10:00 → 10:00
  ...
  11:15-11:30 → 11:30
  13:00-13:14 丢弃
  13:15-13:30 → 13:30

1d + close_anchor=11:30
  只聚合 09:30-11:30
  timestamp / bar_close_ts / available_at = T11:30:00Z
  first_tradable_slot = 当日 13:00
  下午分钟不得进入这根日线
```

`first_tradable_slot` 只是消费提示。成交、滑点、账户在 FactorLab / Terminal，不在 DataHub。

## 与 FactorLab 连续钟的边界

FactorLab `shifted_session_clock@1.0` 把 `11:00-11:30 + 13:00-13:30` 合成一根 60m。那是策略级 CloudRidge 35m 载体，不是本产品。若以后要下沉，必须另开 `bar_align=session_clock_continuous` 和新合同 id，不得污染 wall-clock 默认。

## 代码 / 测试 / 工作流

- 合同：`src/datahub/storage/query/session_offset_contract.py`
- 派生：`src/datahub/storage/query/bars_deriver.py`
- 查询：`src/datahub/storage/query/bars_query.py`、`src/datahub/api/routes/history.py`、`src/datahub/cli.py`
- 测试：`tests/unit/storage/test_session_offset_contract.py`、`tests/unit/storage/test_bars_deriver.py`
- 工作流：显式 CLI / HTTP 查询。日常 `daily_data_refresh_workflow.py` **不**自动把官方 latest 换成 noon-close。

```bash
PYTHONPATH=src .venv/bin/python -m pytest \
  tests/unit/storage/test_session_offset_contract.py \
  tests/unit/storage/test_bars_deriver.py -q
```
