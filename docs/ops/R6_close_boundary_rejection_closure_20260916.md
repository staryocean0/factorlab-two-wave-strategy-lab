# R6 close-boundary rejection closure

日期：2026-09-16

状态：`CLOSED / DIRECTION ASYMMETRY / NO RESCUE`

Identity：`R6_close_boundary_rejection_v1`

Frozen execution run `35041067183` passed all execution-integrity checks and 4/4 tests. Supply was ample, but the frozen direction gate failed because VALIDATION lower-breakout mean effect was `+0.0579478` instead of `<0`.

正式 closure：

`R6_closed_direction_asymmetry_no_rescue`

保留的历史事实：pooled TRAIN/VALIDATION、2019、2020 和 upper-breakout 都呈预期 reversal direction；但这不足以覆盖 lower-breakout 的反向结果。

明确禁止：

- outcome 后改成 upper-only identity 并把它称为 R6 continuation；
- 调 12-bar boundary、1-bar rejection 或 3-bar horizon；
- 按年份、时段、方向筛 favorable subset；
- 加 R5-B1 anti-persistence 或 M0 structural features rescue；
- BLACKBOX / PnL / Sharpe / complex regime model。

下一研究预算转向新的 broad identity family，优先 `market_common_vs_idiosyncratic_shock_reversion`。在科学协议冻结之前，只允许做数据 availability / identity / timestamp overlap inventory，不读取未来 outcome 以调科学定义。
