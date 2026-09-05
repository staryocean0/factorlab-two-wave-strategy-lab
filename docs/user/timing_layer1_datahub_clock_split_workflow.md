# 第 1 层数据时钟：DataHub 造 bar / FactorLab 消费工作流

> **第 1 层 · 数据时钟。** 切 bar 问 DataHub；FactorLab 只选菜单、配对成交窗、上闸。
> 白皮书：[`../ops/timing_layer1_datahub_clock_split_whitepaper.md`](../ops/timing_layer1_datahub_clock_split_whitepaper.md)
> 机器合同：[`../ops/timing_layer1_datahub_clock_split@1.0.json`](../ops/timing_layer1_datahub_clock_split@1.0.json)

这是车道 1 造 bar 职责的当前入口。身份横幅不是本轮；本轮把墙上时钟切 bar 从 FactorLab 剥离到 DataHub。

## 五位一体

| 角色 | FactorLab | DataHub |
|---|---|---|
| 文档 | 本文 | [`../../unified_datahub/docs/modules/history/session-offset-bars-workflow.md`](../../unified_datahub/docs/modules/history/session-offset-bars-workflow.md) |
| 白皮书 | [`../ops/timing_layer1_datahub_clock_split_whitepaper.md`](../ops/timing_layer1_datahub_clock_split_whitepaper.md) | [`session-offset-bars-whitepaper.md`](../../unified_datahub/docs/modules/history/session-offset-bars-whitepaper.md) |
| 代码 | `src/factor_lab/data/session_offset_defaults.py` | `src/datahub/storage/query/session_offset_contract.py` + `bars_deriver.py` |
| 测试 | `tests/unit/test_timing_layer1_datahub_clock_split.py` | `tests/unit/storage/test_session_offset_contract.py` |
| 工作流 | 本文 | DataHub 加法查询工作流 |

## 新研究怎么拉数

1. 不要本地切 1 分钟，也不要走 `derive-shifted-bars` 做墙上时钟。
2. 用 `apply_fetch_defaults` / `factor-lab datahub-fetch-bars`。它只翻译菜单，bar 由 DataHub 造。
3. 日线菜单：`1d@11:30` 下午成交，和/或官方 `60m+0` 选 14:00，和/或 `30m+30` 选 14:30。
4. 小时菜单：`30m+15` / `60m+30` / `60m+45`。没有 `60m+5`。
5. 15 分钟菜单只有 `15m+5` / `15m+10`。没有 `15m+15` 研究默认。
6. 没传参数时 fetch 回落到该菜单第一档：`1d@11:30` / `60m+30` / `15m+5`。`60m+30` 完整收线是 11:00/14:30，不是 14:00。
7. 2/3/10/20m 走 DataHub `on-demand-klines`，禁止 FactorLab 重采样。
8. 信号可 qfq；成交必须 raw/pit。

## 什么时候还能碰 FactorLab 造 bar

只有云脊午休连续钟：`shifted_session_clock@1.0`。工作流见 [`shifted_bar_derivation_workflow.md`](shifted_bar_derivation_workflow.md)。它会把 `11:00-11:30 + 13:00-13:30` 合成一根 60m。这不是 DataHub 墙上时钟，也不是研究默认。

旧 `dual-scale-remakes/` 只读。后继下午/相位重做必须重新问 DataHub，不得从旧云脊包再切。

## 禁止

- 11:30 日线配 `next_session`
- 15:00 日线配 `same_day_afternoon`
- qfq 当成交价
- 把 DataHub 金样 `60m+5` / `15m+15` 写成 FactorLab 默认
- 把 `derive-shifted-bars` 标成 DataHub 原生能力或 `/datahub/*`
- 开新的 offset 搜索

## 验收

```bash
uv run pytest -q \
  tests/unit/test_timing_layer1_datahub_clock_split.py \
  tests/unit/test_session_offset_defaults.py \
  tests/unit/test_shifted_bar_service.py \
  tests/unit/test_timing_layer1_clock_identity.py
```

DataHub 侧在 `unified_datahub` 根目录：

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q \
  tests/unit/storage/test_session_offset_contract.py \
  tests/unit/storage/test_factorlab_timing_layer1_clock_split.py
```
