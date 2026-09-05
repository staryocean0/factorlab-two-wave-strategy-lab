# 中证1000 时段时钟参考层白皮书

> **第 1 层 · 数据时钟。** 只负责切 bar、收线时刻、信号价/成交价和闸。不算 K 线属性，不认领方向，不选合约。第 2 层测量消费本层时钟，不得反过来改本层。归属清单 asset `session_clock_reference`。
> 闸可以减仓、推迟进、提前出，**不能翻向**。指数 / IM / MO 分地图，隔夜尤其不能互抄。

状态：Implemented as research infrastructure / reference overlay  
权限：`strategy_authority=false`，`production_authority=false`，
`standalone_session_strategy=false`

## 1. 身份

本设施冻结 2026-08 临时日内/日间研究中仍然有用的部分：时段地图、工具差异、
库存闸和最小统计窗。它供其他择时策略参考，不自己产生方向，不授权生产。本层不上切 bar；墙上时钟真源见 [`timing_layer1_datahub_clock_split_whitepaper.md`](timing_layer1_datahub_clock_split_whitepaper.md)。
第 2 层时段形状测量见 [`timing_layer2_implied_intraday_reversal_whitepaper.md`](timing_layer2_implied_intraday_reversal_whitepaper.md)。

载体拆分必须保留：

| 工具 | 窗口 | 角色 |
|---|---|---|
| 中证1000 指数 `000852.SH` | 2014-10-17 至 2024，2025 未读 | 路径地图 |
| 中证1000 股指期货 IM | 2022-07-22 至 2024，2025 未读 | 可空的执行层 |
| 中证1000 股指期权 MO | 2022-07-22 至 2024，2025 未读 | 权利金路径，IV 已在价格内 |

指数 1 分钟时间戳按中国交易时段标签解释，即使存储带 `Z` 后缀。

## 2. 指数地图

无条件形状（不是每年都同样强）：

1. 隔夜平均为负，约 60% 低开。收盘买、开盘卖是成本，不是收益。
2. 上涨主要在上午，尤其 09:31–10:00。
3. 2021 年后，13:00–14:00 是最清楚的负小时。14:00–14:30 略负，14:30–15:00 略正。
   不能说“最后一小时纯负”。
4. 2023 年不是周期消失，而是早盘增益变薄。隔夜仍负，下午仍略负。

因此指数上的无条件最优**不是**“昨收买、今早卖”。那会把负隔夜焊进账户。
更干净的无条件指数底座是：默认不隔夜，优先拥有上午。

高开/低开也不是对称反向：高开偏延续，低开偏修复。无条件“高开空、低开多”
作为独立策略不成立。

## 3. IM 期货差异

IM 收益 ≈ 指数收益 + Δ基差。相关约 1。

- **日内**，尤其 13:00–14:00：基差几乎不动。空这段就是空指数这段。
- **隔夜**：指数低开，IM 常因贴水隔夜回补而翻正。指数空隔夜不能搬到 IM。
- 09:31–10:00 IM 仍为正，但比指数弱，弱在上午贴水变深。
- 2023 年 IM 早盘多失效；13:00–14:00 空三年都还在，只是强弱不同。

接到冻结 CSI1000 LAT `lat_1m_p32_centre_exit_atm_v2` 上时：

- 该 LAT 规格 14:55 已强制平仓，隔夜闸是空操作。
- 唯一有材料的闸是：方向为多时跳过 13:00–14:00。
- 1 分钟换手在 1.5bp 成本下会打穿账户。闸不是成本修复器。

## 4. MO 期权差异

隐含波动率已经在权利金里，不是漏算项。平值/实值 last-trade 诊断表明：

- 早盘买 ATM Call 平均拿不到指数那截正漂移；theta/IV 下降把涨幅吃掉。
- 13:00–14:00 买 Put 弱正，卖 Call 统计上更强，但卖方风险未定价，且无 L1。
- 实值比平值更像期货，少受 IV 折腾。
- 极度虚值不在范围内。无连续盘口，不得宣称可执行净收益。

## 5. 融合合同

```text
live_position = incumbent_direction × inventory_gate(clock, instrument)
```

闸输出 0 或 1，禁止翻向。推荐先接：

1. 隔夜：指数与 IM 默认都不无条件持有。
2. IM 多头跳过 13:00–14:00。
3. 09:31–10:00 仅作做多增益候选，滚动 63 日 `|均值| < SE` 则停用增益。

成功只看 incumbent 全账户增量，不看时段子账户是否单独好看。

## 6. 最小统计窗

月约 20 日，只作灵敏度。季约 60 日 / 滚动 63 日是最小决策支持粒度。
年是主报告粒度。重叠窗不是独立验证。禁止把 2024Q4 写成以后每年四季度规则。

Bead：`fl-0xkd2`。

## 7. 权威与重建

```bash
.venv/bin/python scripts/build_market_state_session_clock_reference.py --overwrite
.venv/bin/pytest -q tests/unit/test_market_state_session_clock_reference.py
```

科学状态：`frozen_research_reference_waiting_for_incumbent_ablation`。
