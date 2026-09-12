# 趋势连续性市场状态工作流

## 它解决什么问题

当多个趋势策略都出现“2009—2017强、2018—2020弱、2021—2026恢复”时，先不要把
策略收益下降直接判成过拟合。本工具先给出一条与具体策略无关的每日市场状态线，用来判断
收益的连续性环境是否发生了共同变化。

它不能单独回答“某策略是否抓住了全部机会”。完整诊断必须分两步：

1. 本工具判断公共趋势环境；
2. 再接该策略自己的独立机会账本，比较机会供给、捕获率和单位能力。

## 权威公式

先计算已完成日线对数收益：

```text
r_t = log(close_t / close_{t-1})
```

权威事实线是：

```text
trend_continuity_w250 = corr(r_t, r_{t-1}) over trailing 250 completed trading days
```

监控展示线是：

```text
trend_continuity_w250_ma20 = trailing mean of trend_continuity_w250 over 20 trading days
```

W250约等于一个交易年，负责真正的市场记忆；MA20只把展示噪声压低，不改变权威事实。
另外发布W100、W150、W200、W250、W300、W400、W500中位数及正值尺度比例，检查
结论是不是只靠一个窗口。

## 白话解释

- 数值明显为正：昨天涨，今天继续涨；昨天跌，今天继续跌的倾向更强，趋势工具环境较好。
- 数值接近零：相邻收益方向缺少记忆，趋势策略容易反复挨打。
- 数值为负：短期反向修复更强，追趋势更不划算。

状态标签只使用零轴和七尺度一致度，不使用策略收益拟合阈值：七个尺度至少五个同意且中位数
为正才叫`continuation`；至少五个同意为负才叫`reversal`；其余为`mixed`。

## 运行

```bash
PYTHONPATH=src python scripts/run_market_state_trend_continuity_regime.py
PYTHONPATH=src python scripts/validate_market_state_trend_continuity_regime.py
```

当前产物入口：

```text
output/market-state-foundation/trend-continuity-regime/current/manifest.json
```

主要文件：

- `trend_continuity_timeseries.csv`：逐日权威线、展示线和尺度一致度；
- `annual_summary.csv`：逐年统计；
- `phase_summary.csv`：2009—2017、2018—2020、2021—2026三段统计；
- `candidate_comparison.csv`：LAG1、LAG4、路径效率、BDCI、论文核的同口径挑战；
- `window_smoothing_surface.csv`：测量窗和展示平滑窗的完整曲面；
- `trend_continuity_timeseries.png`：权威事实线和MA20展示线的完整历史图；
- `report_zh.md`：本次数据结论。

## 强制边界

- 当日收盘计算，下一交易日才可消费；
- `diagnostic_authority=true`；
- `causal_root_proven=false`；
- `opportunity_capture_proof=false`；
- `tool_routing_authority=false`；
- `dynamic_parameter_authority=false`；
- `production_authority=false`。

更详细的选择证据与被否决候选见[白皮书](../ops/market_state_trend_continuity_regime_whitepaper.md)。
