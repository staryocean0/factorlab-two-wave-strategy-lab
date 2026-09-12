# 统一多尺度 K 线与属性基础设施白皮书

状态：V3 Implemented / T+0 research infrastructure ready；V2只读保留
入口：[`../user/market_state_unified_kline_attribute_infrastructure.md`](../user/market_state_unified_kline_attribute_infrastructure.md)

## 1. 定位与责任

本基础设施把 DataHub 市场指数 1m 事实、Cloudridge 合成 1m 路径、真实
wall-clock 多尺度 K 线和年度 K 线属性装配成统一可比数据面。它是市场状态/LAT
研究的公共基础设施，不属于某个 LAT 参数版本，也不替代旧 Cloudridge 日线属性设施。

它负责：

1. 固定十四个视图的真实频率、offset、收线时钟和构造合同。
2. 确保市场指数与 Cloudridge 使用同一分桶语义。
3. 分离 qfq 信号和 raw/pit fill，按共同权威窗口闭合时间边界。
4. 物化跨载体、跨视图、按物理日尺度可比的年度属性 atlas。
5. 用覆盖、时钟、OHLC、重复键和确定性重放证明 ready。

它不负责：

- 选择 LAT 主频段、相位弧、K、方向或路由；
- 把某个属性解释成领先因子；
- 重开已消费的策略挑战或 lockbox；
- 产生生产信号或 Terminal 实时第二路行情。

## 2. 与相邻基础设施的边界

| 基础设施 | 负责内容 | 与本设施关系 |
|---|---|---|
| `timing_layer1_datahub_clock_split_whitepaper.md` | DataHub 造墙上时钟 bar，FactorLab 只消费 | 第 1 层造 bar 真源，本设施不得另写切 bar |
| `unified_offset_data_and_backtest_whitepaper.md` | DataHub wall-clock/noon-close 合同、信号/fill 与成交窗口 | 上位数据合同，本设施不得改写 |
| `cloudridge_attribute_infrastructure_whitepaper.md` | 单一 Cloudridge 日线属性字典、逐日面板与 MA 面板 | 并列旧设施，不是本设施的历史版本 |
| `lat_kline_attribute_atlas.py` | 年度属性公式 | 本设施的属性计算内核 |
| LAT 策略适配工作流 | 参数开发、切片、挑战与策略裁决 | 本设施只提供输入材料 |

旧 `dual-scale-remakes`、旧 CFFEX/创新指数导出、旧 LAT 结果全部保持只读。
successor V2/V3 不通过改名覆盖旧产物。V3只追加1m/5m与高频频带，V2八视图
的路径和manifest哈希保持不变。

## 3. 数据产品合同

### 3.1 载体

```text
cloudridge
000016.SH  000300.SH  000905.SH
000852.SH  000688.SH  399006.SZ
```

### 3.2 视图与时钟

| view_id | 构造 | 完整收线 |
|---|---|---|
| `1m_official` | 官方1m | 09:31—11:30、13:01—15:00，正常日240根 |
| `5m_offset_0` | 5m+0 | 09:35起，正常日48根 |
| `5m_offset_1/2/3/4` | 5m墙钟错位 | 每日46根；四个1分钟相位并列，不选默认赢家 |
| `15m_offset_5` | 15m+5 | 09:50 起，午前7根、午后7根 |
| `15m_offset_10` | 15m+10 | 09:55 起，午前7根、午后7根 |
| `30m_offset_15` | 30m+15 | 10:15/10:45/11:15/13:45/14:15/14:45 |
| `60m_offset_30` | 60m+30 | 11:00/14:30 |
| `60m_offset_45` | 60m+45 | 11:15/14:45 |
| `daily_noon_close_1130` | 1d@11:30 | 11:30 |
| `daily_proxy_close_1400` | 官方60m+0后选择 | 14:00 |
| `daily_proxy_close_1430` | 30m+30后选择 | 14:30 |

`60m+30` 不是 14:00 bar。任何文档、代码或产物再次把二者混同，都必须
fail closed。

### 3.3 权威窗口

市场指数父数据可晚于 Cloudridge qfq，但跨载体 atlas 必须统一截到所有参与者
的共同可用终点。当前终点 `2026-06-24`。raw 后续行可以保留在父数据中，
不得冒充 qfq 信号或偷偷扩大比较窗口。

V3市场指数高频视图从2015-01-01开始。1m缺钟只允许使用上一已知指数点做
严格因果平铺，并逐行标记；不得从下一分钟回填。2016-01-04/07熔断尾部不
平铺。任一symbol-day原始缺失超过5分钟，或任一5m相位缺完整bar，该日从
全部1m/5m属性视图排除；manifest同时保留`raw_ready`与
`ready_with_exclusions`，禁止隐藏原始覆盖失败。

## 4. 数据流与物化

```text
DataHub canonical index 1m (v8)
  -> DataHub governed fourteen-view V3 export
  -> six-index Parquet + replay manifest

DataHub stock 1m qfq/raw + frozen Cloudridge constituents
  -> causal Cloudridge qfq/raw 1m paths
  -> same DataHub wall-clock bucket algorithm
  -> Cloudridge fourteen-view Parquet + replay manifest

seven carriers × fourteen views
  -> annual_kline_attributes(bars_per_day scaled)
  -> annual attribute atlas + coverage manifest
```

Cloudridge 的十四视图只能从 1m 路径真实聚合。旧脚本“选取某个 5m 时钟后改
frequency 名称”不满足本合同。

## 5. 属性层合同

属性 atlas 使用 `carrier + year + view_id` 唯一键。窗口 `2d/4d/8d/16d`
按各视图 `bars_per_day` 换算，使1m、5m、15m、30m、60m和日级视图表达
相同物理日尺度。滚动效率与OLS统计必须使用O(n)有界内存算法，禁止在1m年度
数据上展开`rows × window`大矩阵。

当前属性族包括：

- 路径效率、OLS 趋势 t 值/R²；
- 收益自相关、符号持续性、方向 run length、中心线穿越密度；
- 实现波动、波动的波动、上下行方差比、jump tail share；
- 隔夜 gap share、日内区间效率；
- P10/P17/P29/P38/P43/P48/P53/P67/P95 brickwall频带RMS、快慢能量占比和谱集中度。

FFT/brickwall 属性可用于研究解释，但不得直接成为运行时规则或参数选择权。

T+0只撤销股票T+1的执行硬约束。杠杆改善资金效率，不等于手续费、点差、滑点、
冲击、换月成本或期权Greeks/波动率曲面成本为零；这些必须在后续策略分支中
按真实合约另行定价，本设施不输出杠杆回测。

## 6. 代码、测试与权威产物

| 层 | 路径 |
|---|---|
| 菜单/时钟合同 | `src/factor_lab/data/session_offset_defaults.py` |
| Cloudridge 统一分桶 | `src/factor_lab/data/unified_kline_v2.py` |
| 属性公式 | `src/factor_lab/market_state/lat_kline_attribute_atlas.py` |
| 1m 路径构建 | `scripts/build_cloudridge_full_datahub_levels.py` |
| Cloudridge 物化 | `scripts/materialize_cloudridge_unified_kline_v2.py` |
| atlas 物化 | `scripts/materialize_lat_unified_kline_attribute_atlas_v2.py` |
| T+0 Cloudridge V3物化 | `scripts/materialize_cloudridge_unified_kline_v3.py` |
| T+0 atlas V3物化 | `scripts/materialize_lat_unified_kline_attribute_atlas_v3.py` |
| 单测 | `tests/unit/test_build_cloudridge_full_datahub_levels.py`, `test_session_offset_defaults.py`, `test_unified_kline_v2.py`, `test_lat_kline_attribute_atlas.py` |

权威 manifest：

```text
DataHub:
/home/starryocean/桌面/量化/unified_datahub/.runtime/live/exports/
factorlab_unified_index_kline_v3_20260824/manifest.json

FactorLab:
artifacts/market_state/unified_kline_attribute_infrastructure_v3_20260824/
cloudridge/manifest.json
attribute_atlas/manifest.json
```

## 7. 验收、变更与升级门禁

每次重建必须同时通过：

1. 所有 view 的 observed clocks 与注册 clocks 完全一致；
2. 无重复 `symbol/timestamp` 或 `view_id/timestamp`；
3. OHLC 有限、为正并满足 `low <= open/close <= high`；
4. 权威交易日覆盖闭合，已知短交易日显式治理；
5. Cloudridge qfq/raw 时间戳一对一；
6. 第二遍重放的行数和内容 hash/checksum 一致；
7. atlas carrier-view 对齐完整且唯一键重复数为 0；
8. 旧只读产物未覆盖。
9. 1m因果平铺数量、最长缺口和全部高频排除日显式写入manifest；atlas不得重新纳入。

新增载体、视图、属性或延长共同终点时，必须同时更新：菜单合同、本文、用户
入口、测试、manifest schema 与证据包。单独增加脚本或 Parquet 不算基础设施升级。

## 8. 渐进式发现规则

AI 的发现顺序固定为：

```text
ai-readme.md（一行入口，不堆细节）
  -> docs/user/market_state_unified_kline_attribute_infrastructure.md（分层导航）
  -> 本白皮书（长期权威合同）
  -> 代码 / 测试 / manifest（机器真值）
  -> evidence/final_report.md（一次验收事实）
```

AI Readme 不直接罗列全部脚本和文件；证据报告也不能反向替代白皮书。这样入口
保持轻量，同时任何需要深入的助手都能逐层抵达机器实现。
