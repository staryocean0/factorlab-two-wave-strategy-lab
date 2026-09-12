# CSI1000五分钟研究Runtime白皮书

> **第 1 层 · 数据时钟。** 只负责切 bar、收线时刻、信号价/成交价和闸。不算 K 线属性，不认领方向，不选合约。第 2 层测量消费本层时钟，不得反过来改本层。归属清单 asset `csi1000_5m_research_runtime`。

本合同把DataHub正式`5m_offset_0`冻结为CSI1000最短current研究K线。offset1--4只用于边界敏感性，不参与事后挑相位。

信号在5分钟棒完成时可用；成交坐标是之后第一根可交易1分钟raw/PIT bar的open。午休后自然跳到13:01，禁止把11:30信号填在午休中，也禁止直接用5分钟收盘成交。

Terminal仍消费1分钟raw与同一策略；本合同不是第二套实时行情。2026-09-01起，2m/3m/10m/20m已通过独立的DataHub固定快照绑定获得研究回测/运行时输入权；它们不由本5m合同转授。25m已按用户决策撤出本专题范围。

造 bar 真源是 DataHub。本白皮书只冻结 CSI1000 的 5m 信号钟和 1m fill 坐标。分工见 [`timing_layer1_datahub_clock_split_whitepaper.md`](timing_layer1_datahub_clock_split_whitepaper.md)。
