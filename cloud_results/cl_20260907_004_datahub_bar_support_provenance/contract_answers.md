# CL-20260907-004 合同问题答案

权威绑定：本地 `unified_datahub` `main` HEAD `ba780790acd8e9a558e4e01f9474b6e79265d818` 的 **已提交 blob**，不是脏工作区。
实现提交：`2c7b070f38f061378e89c19d183da9ccef9a6c88`（`Keep alternative session clocks additive to canonical bars`）。
本文件只转述白皮书/代码/测试；不从 v0.6.16 `H_end_5` 反推，不发明 `support_start/support_end` 产品字段。

证据副本：`archive/`。

## 1. 5m support interval 在上午/下午 session 内如何定义？

CN-A 会话窗口（1m 端标签、闭区间）是：

- 上午 `[09:30, 11:30]` = minute-of-day `[570, 690]`
- 下午 `[13:00, 15:00]` = `[780, 900]`

来源：`session_offset_contract.py` 中 `CN_A_MORNING_WINDOW` / `CN_A_AFTERNOON_WINDOW`；`bars_deriver.py` 注释与 `_session_filter_expr()`。

5m 把每个会话里的 1m 端标签映射到一根 end-label 5m bar：

- **offset=0 / official v2**：每节第一桶是 `[session_start, session_start+5]`，标签 `session_start+5`；之后按 ceil 分桶，最后一桶 cap 在 `session_end`。
- **offset=1..4 / wall-clock**：每节网格从 `session_start+offset` 开始；该分钟之前的 1m 丢弃；完整桶标签为 `grid_start + k*5`，且标签必须 `<= session_end`。

白皮书金样是 60m+5 / 15m+15，不是 5m；5m 规则由同一函数 `assign_intraday_bucket_minute(period_minutes=5, offset_minutes=k)` 给出。测试：`test_5m_raw_aggregation_granularity`（官方 09:35/09:40）、`test_5m_offset_equal_to_period_is_allowed`。

## 2. support 起止端点的 inclusive/exclusive 规则是什么？

权威赋值规则是 **每个 1m 端标签最多进入一个 bucket**，由 `assign_intraday_bucket_minute` 决定，不是独立的半开区间字符串。

对 wall-clock offset>0：

- 第一完整桶包含 `grid_start` **和** `grid_start+period`，因此 5m 第一桶有 **6** 个 1m 端标签。
- 后续完整桶是上一根标签之后到当前标签，即 `(prev_label, current_label]`，有 **5** 个 1m 端标签。

例：5m offset1 上午第一桶 `09:31..09:36 → 09:36`；第二桶 `09:37..09:41 → 09:41`。

白皮书 60m+5 写作 `09:35-10:35 → 10:35`，代码同样把 `10:35` 留在第一桶。`construction_fields()["bar_open_ts"] = close-period` 对后续桶会落到上一根 bar 的标签上，**不等于**后续桶实际最小 1m。不要把 `bar_open_ts` 当成 exact `support_start`。

当前产品 **没有** `support_start` / `support_end` / `source_row_ids` 字段。

## 3. bar label、availability time、support_start、support_end 的精确关系是什么？

- **bar label / timestamp**：会话墙上时钟的 end-label，序列化为 `YYYY-MM-DDTHH:MM:00Z`（见问题 8）。派生 SQL 用该字符串作 `bucket_timestamp`。
- **intended support**：所有 `assign_intraday_bucket_minute(m)==label_minute` 的同日 1m 端标签。
- **actual support**：intended 集合与真实 1m 源行的交集。缺分钟仍会生成 5m bar。
- **`bar_close_ts`**：加法产品元数据，等于 label。
- **`bar_open_ts`**：`close-period` 并按节起点+offset 夹紧；只在非 official 行上附加。
- **`first_tradable_slot`**：bar 完成后的消费提示。上午未到 11:30 时等于 label；11:30 那根变成当日 `13:00`。白皮书写明成交/滑点/账户不在 DataHub。
- **湖里/冻结行的 `available_at`**：本样本是 `T15:30:00+08:00` 批次字段，**不是** `first_tradable_slot`。

冻结 5m 没有 exact support 字段。offset0 走 official 合同，deriver **不附加** construction metadata。

## 4. 午休如何切分，是否跨午休聚合？

不跨午休。上下午是两个独立窗口。`13:00` 不得成为独立 bar：official 把它并进下午第一桶；wall-clock offset>0 把 `13:00` 当作下午节起点，offset>0 时 `13:00` 本身被丢掉。

来源：白皮书“上下午分段，午休不跨段”；`assign_intraday_bucket_minute` 的 for-loop；`test_official_60m_gold_labels` / `test_wall_clock_60m_offset5_gold_labels` 断言无独立 `13:00`。

## 5. overnight 如何处理？

本产品没有隔夜会话。09:30–11:30 与 13:00–15:00 之外的 1m 返回 `None`。1d 按 `trading_day` 分组，禁止 1440 分钟跨夜桶。15:00 到次日 09:30 不聚合。

指数 `cn_index` 使用同一 CN-A 窗口作为 fallback（`bars_deriver.py` `_session_filter_expr` 注释）。

## 6. session-edge partial bars 如何处理/丢弃/标记？

- **official offset0**：第一节不完整前缀并进第一桶；最后一桶 cap 在 `session_end`，默认保留。`include_tail_partial` 默认 false 对 official 路径不是丢尾条件。
- **wall-clock offset>0**：`minute < grid_start` 丢弃；标签将超过 `session_end` 的尾桶默认丢弃。只有 `include_tail_partial=true` 才把尾桶标成 `session_end`。冻结研究产品未声明该开关，应按默认 false。
- 没有单独的 partial-bar 标记列。被丢弃的 1m 不会出现在任何 5m label 里。

测试：`test_60m_offset_5_uses_0935_grid_and_drops_short_tails`、`test_include_tail_partial_keeps_incomplete_last_bucket`。

## 7. offset0 与 offset1–4 是否完全同一 support rule？

**不是同一条路径。**

| 视图 | `normalize_session_offset_request(frequency=5m, session_offset_minutes=k)` | 分桶函数 | deriver 是否附加 construction fields |
|---|---|---|---|
| offset0 | `uses_official_contract=True`，`construction_contract=cn_a_session_end_label_no_noon_partial_v2` | `_session_bucket_case` / offset=0 official 分支 | 否 |
| offset1–4 | `uses_official_contract=False`，`construction_contract=cn_a_session_wall_clock_offset_v1` | `_wall_clock_bucket_case(offset=k)` | 是 |

对 **5m**，official offset0 与 wall-clock offset0 的标签网格恰好重合（09:35..11:30 / 13:05..15:00）。这不能推广到 60m。冻结五视图的 `data_contract` 却全部写成 `cn_a_session_wall_clock_offset_v1`，与 offset0 的代码合同 id 不一致；只报告，不改冻结文件。

## 8. serialized timestamp 与 source support 的 timezone/clock convention？

DataHub 1m/派生 timestamp 是 **上海 A 股会话墙上时钟**，写成 `YYYY-MM-DDTHH:MM:00Z`。`_minute_of_day_expr()` 直接 `substr(timestamp, 12, 2)` / `substr(..., 15, 2)`，把 `T09:35` 当 09:35，而不是 UTC 01:35。

两浪冻结包已经拆开：

- `timestamp_source_serialized`：上述墙上时钟 `...T09:35:00Z`
- `bar_end_shanghai`：`Asia/Shanghai` 09:35
- `timestamp`：真正 UTC 01:35

权威 support 应对齐 **serialized 墙上时钟 / `bar_end_shanghai`**，不要用 UTC `timestamp` 去做 minute-of-day。

## 9. 能否对当前冻结 5m 行唯一确定 exact source support set？

分两层：

1. **Intended support（合同窗口）**：能。给定 `(trading_day, label, offset, include_tail_partial=false)`，`assign_intraday_bucket_minute` 唯一确定 intended 1m 端标签集合。
2. **Actual source set（真实聚合行）**：冻结 5m **不能单独**确定。`source_minute_count` 全 null，没有 `support_start/support_end/source_row_ids`。缺 1m 仍会产出 5m。

本地用同一 `dataset_version` 的 DataHub 1m 湖（2015-01-05..2020-12-31，`000852.SH`，349923 行，未读 2021+）按官方函数回放：

- 五个视图的 label 集合与冻结 5m **完全一致**（only_frozen=0, only_derived=0）
- 对齐 label 的 OHLC mismatch = 0
- 行数与冻结控制完全一致：70114 / 67192 / 67192 / 67193 / 67191

因此：在该 1m 源仍存在时，exact actual support 可以从 **合同函数 + 同源 1m** 恢复；冻结 5m 文件本身仍缺 provenance 列。这不是 Class B 新产品，也没有改 `data/development/`。

例（2015-01-05 offset0 第一根）：intended 6 分钟 `09:30..09:35`，实际 5 分钟，缺 `09:30`。指数 1m 当天从 `09:31` 起。

## Route B 未作为新产品交付

白皮书 fail-closed：钉死 `dataset_version` + offset。当前 deriver 输出列也没有 `source_minute_count` / exact support。本地没有通过公开 API 重导，也没有用 `1m_official` 重采样制造 replacement 5m。
