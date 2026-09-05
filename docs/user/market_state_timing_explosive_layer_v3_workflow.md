# 择时策略研究 Explosive V3 历史工作流

> 当前权限由`timing_strategy_identity_registry@2.0`管理。本策略已迁入
> `src/factor_lab/strategy/research/timing/explosive_v3.py`并等待完整重新资格审查。

## 历史冻结公式

`timing_explosive_layer_v3` 保持第一层的两个互斥责任桶不变：

1. `explosive_crash_rebound`：FDA门控暴跌反弹，只输出 `up`，第一优先；
2. `explosive_p48_p96_true_channel`：P48→P96反向轨真通道，在严格余集输出 `up/down`。

V3只替换暴跌反弹的入场质量测量：旧版用四根K线路径效率和拟合阈值；新版用论文
FDA机制，在注册弧线父事件开始时要求严格前序的局部二次曲线速度与加速度同时为正。
事件一旦通过，仍完整持有原弧线生命周期。

## 没有改变的边界

- 最近已完成W12/W24下跌第一腿及14根有效期不变；
- 注册弧线父工具、入场后的生命周期和第一优先级不变；
- P48→P96通道公式、尺度晋升和反向轨退出不变；
- 第二层、第三层、V62运行时和生产权不变。

W12不是从收益曲面挑出的峰。它由当前P48通道基准尺度除以论文原型固定的四分之一
导数窗得到。W8、W10、W14、W16只做邻域挑战，不参与选择；W8—W14三段均为正，
W16在外部期转负，明确给出公式有效边界。

## 三段结论

| 责任 | 2009—17年均净对数价值 | 2018—20 | 2021—26 |
|---|---:|---:|---:|
| FDA暴跌反弹up | +0.1002 | +0.1068 | +0.0128 |
| P48→P96通道up | +0.2037 | +0.0766 | +0.1496 |
| P48→P96通道down | +0.1382 | +0.1399 | +0.1285 |
| 第一层组合 | +0.4475 | +0.3275 | +0.2929 |

2021—2026只输出账户与事件数汇总，不持久化该段事件细节图。图形归因止于2020年。

## 外部期增益有限的归因

2026-08-04的授权诊断将完成后的反弹事件按生命周期仅作事后归因：

| 生命周期 | 2009—17 事件数/单笔净价值 | 2018—20 | 2021—26 |
|---|---:|---:|---:|
| 1—12根假启动 | 89 / -0.00575 | 73 / -0.00202 | 44 / -0.00372 |
| 13—24根过渡 | 16 / +0.00190 | 13 / +0.01744 | 9 / -0.00173 |
| 25根以上持续反弹 | 50 / +0.02762 | 8 / +0.03010 | 9 / +0.02768 |

真正持续反弹的单笔能力三段几乎一致；外部期单笔/开发期为 `1.002`。
变化主要在供给：外部期持续反弹年频率只有开发期的 `0.296`。因此现有
证据不支持“W12参数在09—20过拟合”是主因，而支持“可赚的长反弹机会变少”。

生命周期是完成后才知道的标签，严禁将它反向写成运行时过滤器。前跌幅、
无条件固定等待、FDA失效止损、弧线相位硬筛和探测仓都无法同时改善开发与复核期，
不写入V3公式。后续研究已找到“反弹冲量/真实暴跌供给/一棒观察/通道回落”的
四折同向候选，详见 [弱启动观察交接工作流](market_state_fda_rebound_observation_handoff_workflow.md)。
该候选尚未修改V3权威公式。

群体相关性指标完成后，另以唯一候选验证了“全市场20日/120日相关性离散度期限结构”
能否增量改善第一道门。该候选在开发OOF中没有增加假启动拒绝，反而降低净价值和夏普，
因此被否决；2021—2026聚合黑箱未打开，V3保持不变。详见
[群体相关性增量验证工作流](market_state_fda_rebound_group_corr_increment_workflow.md)。

## 复算

```bash
PYTHONPATH=src:. python scripts/research_market_state_timing_explosive_layer_v3.py
PYTHONPATH=src:. pytest -q \
  tests/unit/test_market_state_timing_explosive_layer_v3_drift.py \
  tests/unit/test_market_state_fda_recent_down_rebound_bridge.py \
  tests/unit/test_market_state_timing_explosive_layer_v3.py \
  tests/unit/test_market_state_fda_multiscale_channel_v1.py
```

代码位于 `src/factor_lab/market_state/timing_explosive_layer_v3.py`，三层合同是
`src/factor_lab/market_state/timing_strategy_routing_v4.py`，机器产物位于
`artifacts/market_state/timing_explosive_layer_v3/`。证据见
[第一层V3冻结回执](../ops/evidence/market_state_timing_explosive_layer_v3_20260804.md)。
