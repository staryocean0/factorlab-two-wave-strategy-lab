# 项目级差分数据默认拉取与统一回测白皮书

> **第 1 层 · 数据时钟。** 只负责切 bar、收线时刻、信号价/成交价和闸。不算 K 线属性，不认领方向，不选合约。第 2 层测量消费本层时钟，不得反过来改本层。归属清单 asset `unified_offset_data_and_backtest`。

日期：2026-08-19
状态：Implemented for project defaults / first vertical
范围：FactorLab 拉数默认合同、成交窗口配对、CloudRidge 日线研究竖切

---

## 一屏结论

FactorLab 新研究路径默认不再拉官方 15:00 日线，也不再让用户每次记住差分参数。

```text
日线菜单：1d@11:30 下午成交，和/或官方 60m+0 选择 14:00，和/或 30m+30 选择 14:30
小时菜单：30m+15 / 60m+30 / 60m+45，没有 60m+5
15 分钟菜单：只有 15m+5 和 15m+10，没有 15m+15 研究默认
没传参数时的 fetch 回落：1d@11:30 / 60m+30 / 15m+5
信号可用 qfq 差分 K 线
成交必须用 raw / pit，禁止 qfq fill
1m 官方网格配 next_tradable_after_bar_close；统一账本保留 [-1,1] 双向信号
旧 15:00 合同只读，必须 --legacy-official-session
```

数据和回测必须配对。11:30 日线配次日开盘、15:00 日线配当天下午，都 fail closed。

这不是 Hilbert 相位，也不是把 CloudRidge 35m 午休连续钟升格为项目默认。连续钟仍是策略级工具，见 [`shifted_bar_derivation_whitepaper.md`](shifted_bar_derivation_whitepaper.md)。

墙上时钟切 bar 的真源现在是 DataHub。本文件只保留 FactorLab 研究菜单和成交配对；分工见 [`timing_layer1_datahub_clock_split_whitepaper.md`](timing_layer1_datahub_clock_split_whitepaper.md)。


## 未来 AI 必读入口（比白皮书更硬）

只把合同写进白皮书不够。后续助手做策略时，真正会先打开：

1. `factor_lab/AGENTS.md`（always-loaded）
2. `$strategy-slice-rebuild` / `.codex/skills/strategy-slice-rebuild/SKILL.md`
3. `ai-readme.md` 先读顺序第 2 条

这三处必须同时出现 noon-close / same_day_afternoon / 1m 底数。旧研究脚本硬编码 V9 15:00 或 `backtest_signal()` 仍可跑，但不得作为新路径默认。

差分 K 线不是第二路行情。DataHub 权威底数仍是 1 分钟 raw；FactorLab 只在回测时按 11:30 / 09:35 / 09:45 重新分桶。Terminal 回放继续播同一份 1 分钟 raw，策略仍是 FactorLab 产物。

## 为什么必须项目级

以前每条策略自己钉 dataset、自己写 next_bar：

- `DataHubFetchService.view` 默认空，落到 DataHub raw
- 大量脚本钉死 `bars_cn_a_1d_qfq_canonical_xdxr_v9_factorlab_2009_2025_20260814`
- CloudRidge `backtest_signal()` 是 next-bar close-to-close
- StrategySpec 默认 `execution.window=next_session`

只改一个脚本解决不了分裂。项目级只上提合同、配对校验、fetch/backtest adapter 和门禁；策略阈值、35m 选择、Risk-Off / T0 成交语义留在策略级。


## 旧择时基础设施的双尺度过渡（可选，不强制）

这些方案都不强制。每条研究选一档、两档或三档都可以。没传参数时 fetch 只回落到菜单第一档，不等于把其他档废掉。
旧市场状态 / 论文核 / 云脊基础设施上已经发表的回测数字和时间序列，继续作为旧口径只读对照，禁止原地改写成新默认。

如果要把这些旧结论迁到可交易下午时段，用下面的**可选重做菜单**另出一版或两版。这不是把旧研究强行改名，而是同一套公式换差分桶。

| 旧结论原生频率 | 可选重做 1 | 可选重做 2 | 目的 |
|---|---|---|---|
| 日线 `1d@15:00` | 官方 `60m + offset 0`，选择 **14:00** | `30m + offset 30`，选择 **14:30** | 避开隔夜缺口，仍覆盖大半个下午 |
| 小时 `60m@09:30` | `30m + offset 15` | `60m + offset 45`（45 分钟相位） | 小时结论拆到半小时 / 三格 15 分钟相位 |
| 15 分钟 `15m@09:30` | `15m + offset 5` | `15m + offset 10` | 仍是 15 分钟 K 线，用 5 分钟步进做两档相位 |

约束：

1. 不强制。每条旧研究可以只做一档、两档，或继续只读旧口径。
2. 不得把其中任何一档说成唯一项目默认。日线 11:30、14:00、14:30 都合法。
3. `15m + offset 45` 非法，因为 45 超过一个 15 分钟周期。45 分钟相位必须落在 `60m + 45`。
4. 重做结果必须另写 `variant_id` 和 `data_contract`，不得覆盖旧数字。
5. 因子库、外部因子池不在本菜单范围内。

时钟语义勘误：DataHub 的 `60m+30` 完整收线标签为 `11:00/14:30`，
`60m+45` 为 `11:15/14:45`。日级 14:00 代理只能从官方 `60m+0`
网格选择 14:00 那根，不能把 `60m+30` 重命名为 14:00。旧
`dual-scale-remakes` 的既有身份仍只读；本勘误只约束 successor V2。

机器入口：`research_offset_schemes(native_frequency)` / `optional_remake_variants(native_frequency)`。 日线竖切已落地：`output/market-state-foundation/dual-scale-remakes/` 含 14:00/14:30 价格，以及六轴、论文核、统一择时的并列包；`*/current` 仍是旧 15:00。 小时/15 分钟已按同一打样切出 `hourly_to_30m_offset_15`（价格并列）、`hourly_to_60m_offset_30`、`hourly_to_60m_offset_45`、`quarter_to_15m_offset_5/10`；对应测量包、`hourly_to_60m_offset_30/45/group2_envelope` 四工具包、以及两档 15m 论文核因子完整性包都写在 `dual-scale-remakes/`，不覆盖官方 `current/`。

## 成交窗口

| 窗口 | 含义 | 合法数据前提 |
|---|---|---|
| `same_day_afternoon` | 中午收盘后，当日 13:00 起成交 | `close_anchor=11:30` |
| `next_session` | 官方收盘后下一交易时段开盘 | 官方 15:00 / 遗留合同 |
| `next_tradable_after_bar_close` | 该 bar 收盘后第一根执行频率 bar | 日内 offset bar |
| `next_bar_close_to_close` | 仅诊断，必须标 `optimistic_research_only` | 任何 |

CloudRidge `backtest_signal()` 归入最后一档，不再当交易真值。

`1m` 与 `5m` 官方日内网格同样属于
`next_tradable_after_bar_close`。`standard_backtest_service` 的共享账本接受
`[-1, 1]` 双向目标仓位，下一棒生效；仓位增加按 buy cost、仓位减少按
sell cost 计费。它不再把负信号裁成空仓，也不得把 `1m` 误配成
`next_session`。

## 代码与测试

- `src/factor_lab/data/session_offset_defaults.py`
- `src/factor_lab/data/services/datahub_fetch_service.py`
- `src/factor_lab/data/adapters/datahub_client.py`
- `src/factor_lab/data/services/standard_backtest_service.py`
- `src/factor_lab/app/api/routers/datahub.py`
- `src/factor_lab/app/headless/cli.py`
- `tests/unit/test_session_offset_defaults.py`

DataHub 产品真源：`../../unified_datahub/docs/modules/history/session-offset-bars-whitepaper.md`。

V9 15:00 合同名字一个字节都不改。要对比旧数字，显式走 legacy，并在结果包同时写 `data_contract` 和 `execution_window`。
