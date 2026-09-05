# CSI1000 DataHub按需多周期K线绑定白皮书

> **第 1 层 · 数据时钟。** 只负责切 bar、收线时刻、信号价/成交价和闸。不算 K 线属性，不认领方向，不选合约。第 2 层测量消费本层时钟，不得反过来改本层。归属清单 asset `datahub_on_demand_kline_binding`。
> 禁止 FactorLab 本地重采样 2m/3m/10m/20m。不改 DataHub 产品身份。

状态：FactorLab独立验收通过；DataHub正式`2m/3m/10m/20m offset_0`产品可作为研究回测或运行时输入。无策略、参数、路由或生产权限。

## 1. 边界

FactorLab不再从1分钟数据自行合成这四个周期。每次读取必须调用DataHub正式接口，钉死不可变`source_snapshot`、`factorlab_on_demand_kline_intervals.v1`、`offset_0`和`completeness_policy=fail`。`latest`、不完整棒、消费者侧重采样和25分钟全部拒绝。

## 2. 独立验收

FactorLab绑定DataHub上游文档、白皮书、代码、测试、合同和验收证据共14个文件的精确SHA-256，并重新执行四个周期的固定快照查询。验收日使用`bars_cn_a_1m_raw_canonical_4ceca170a851`、`000001`和2026-08-21完整交易日；四个响应均逐棒验证周期身份、源分钟数、午休/跨日边界、`available_at`、`as_of`和完整性。

验收快照只证明接口合同；今后每个研究运行仍必须把自己的源快照写入receipt，不能漂移到latest。

## 3. 权限

关闭的是DataHub正式多周期K线产品缺口。它不自动给任何LAT/IIR/IARR或其他策略授权，也不定义信号后成交规则。策略若消费这些K线，仍须独立冻结信号可见时间和下一可交易1分钟open的运输合同。

造 bar 分工见 [`timing_layer1_datahub_clock_split_whitepaper.md`](timing_layer1_datahub_clock_split_whitepaper.md)。2/3/10/20m 只问 DataHub `on-demand-klines`。
