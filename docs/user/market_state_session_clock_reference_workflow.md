# 中证1000 时段时钟参考层入口

> **第 1 层 · 数据时钟。** 只负责切 bar、收线时刻、信号价/成交价和闸。不算 K 线属性，不认领方向，不选合约。第 2 层测量消费本层时钟，不得反过来改本层。归属清单 asset `session_clock_reference`。
> 闸可以减仓、推迟进、提前出，**不能翻向**。指数 / IM / MO 不是同一张地图。

这是日内/日间时段地图的**唯一渐进入口**。它是择时基础设施，不是独立策略。
其他策略开发时可以参考这里的时钟、闸和工具差异，做 `Vn` vs `Vn + gate`
增量，而不是另起一套日频多空系统。

本层是闸，不是造 bar。墙上时钟切 bar 见 [`第1层 DataHub 造 bar 分工`](timing_layer1_datahub_clock_split_workflow.md)。
第 2 层隐含日内反转属性消费本层时钟，入口是 [`timing_layer2_implied_intraday_reversal_workflow.md`](timing_layer2_implied_intraday_reversal_workflow.md)。本层仍不计算 K 线属性。
如果任务只是普通拉数或成交窗口配对，先读
[`统一 offset 数据与回测工作流`](unified_offset_data_and_backtest_workflow.md)。
如果任务是 15 分钟 LAT / 绿波方向本身，仍走各自正式入口。只有当方向已经存在、
需要决定隔夜、09:31–10:00、13:00–14:00 这些库存时，才沿本入口继续。

## 五位一体

| 角色 | 权威入口 |
|---|---|
| 文档 | 本文 |
| 白皮书 | [`../ops/market_state_session_clock_reference_whitepaper.md`](../ops/market_state_session_clock_reference_whitepaper.md) |
| 代码 | `src/factor_lab/market_state/session_clock_reference.py` |
| 测试 | `tests/unit/test_market_state_session_clock_reference.py` |
| 工作流 | 本文的重建与消费顺序 |

机器预注册：
[`../ops/evidence/im_lat_futures_gate_v1_preregistration_20260827.json`](../ops/evidence/im_lat_futures_gate_v1_preregistration_20260827.json)。

## Layer 0：它是什么

- 参考层，不是第 16 个择时工具，也不是可交易账户。
- 方向仍由现有择时给出。本层只回答：这段时钟让不让该方向活着。
- 闸可以减仓、推迟进、提前出，**不能翻向**。
- 指数、IM 期货、MO 期权不是同一张地图。隔夜尤其不能互抄。
- `production_authority=false`，`standalone_session_strategy=false`。

## Layer 1：先读合同

1. [时段时钟参考层白皮书](../ops/market_state_session_clock_reference_whitepaper.md)
2. [项目级 offset 数据与回测白皮书](../ops/unified_offset_data_and_backtest_whitepaper.md)
3. 若接到期权执行，再读 [CSI1000–MO 平值日内框架](csi1000_mo_atm_intraday_framework_workflow.md)

## Layer 2：重建参考包

```bash
.venv/bin/python scripts/build_market_state_session_clock_reference.py --overwrite
.venv/bin/pytest -q tests/unit/test_market_state_session_clock_reference.py
```

生成物：`artifacts/market_state/session_clock_reference_v1/`。

## Layer 3：消费顺序

```text
先读本文
  -> 白皮书的工具拆分（指数 / IM / MO）
  -> reference.json 的 clocks / priors / fusion_order
  -> 在自己的 incumbent 上做 Vn vs Vn+gate
  -> 滚动 63 日只作健康检查，不改方向公式
```

默认融合顺序：

1. 保住 incumbent 方向。
2. 指数和 IM 都不要无条件隔夜。
3. IM 上多头跳过 13:00–14:00。
4. 09:31–10:00 只作为做多增益候选，并用滚动 63 日健康检查。
5. 不要把指数隔夜空翻译成 IM 空，更不要翻译成买 Call。
6. 只在 incumbent 全账户上做增量 ablation。

## 最小统计窗

- 月：约 20 日，只作灵敏度。
- 季 / 滚动 63 日：最小决策支持粒度。
- 年：主报告粒度。
- 重叠滚动窗不是独立验证样本。日历切片不能变成运行时规则。

## 临时研究血缘

详细数字仍可在 `tmp/` 对应 probe 中复核，但**权威结论以本入口和白皮书为准**。
`tmp/` 不再是消费入口。
