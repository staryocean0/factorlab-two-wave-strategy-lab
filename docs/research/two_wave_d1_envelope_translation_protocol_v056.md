# v0.5.6 D2 whole-envelope translation：结果前冻结协议

日期：2026-09-06  
状态：`result_before_code_protocol_frozen`

金融/数学 preanalysis：`docs/research/two_wave_d1_envelope_translation_preanalysis_v056.md`

冻结上游：**v0.5.2 TCSS exact-ridge parent identity + v0.5.4 full-cycle-scale qualification**。

## 1. 唯一允许变化的组件

保留历史 D0/D1，不覆盖。

新增 `D2` direction version：

> parent state hard decision 从三个局部 phase-step votes `(s0,s1,s2)` 改为两条完整 parent envelope 的总迁移 `(E_upper,E_lower)`。

除此以外任何 candidate identity、qualification、confirmation、ledger、selected interval、available-at clock 均不得改变。

## 2. 冻结输入

对已有 v0.5.4 record：

- `s0 = (P2-P0)/A`
- `s1 = (P4-P2)/A`
- `s2 = (P3-P1)/A`
- `net = s0+s1`

`A` 继续是已有两个 detrended cycle amplitudes 的平均单位，不重新估计。

### low-start

- `E_lower = net`
- `E_upper = s2`

### high-start

- `E_upper = net`
- `E_lower = s2`

## 3. 唯一 hard threshold

完全复用旧值：

`phase_tolerance = 0.15`

禁止搜索、扫描、优化任何新数值。

旧：

- `strong_drift = 0.50`
- `opposite_tolerance = 0.05`

仅作为 legacy diagnostic 保留，不进入 D2 hard decision。

## 4. D2 冻结规则

### uptrend

`E_upper > +0.15 and E_lower > +0.15`

reason：`both_parent_envelopes_up`

### downtrend

`E_upper < -0.15 and E_lower < -0.15`

reason：`both_parent_envelopes_down`

### range

`abs(E_upper) <= 0.15 and abs(E_lower) <= 0.15`

reason：`both_parent_envelopes_low_translation`

### uncertain

其它全部：

reason：`parent_envelope_translation_mixed_or_one_sided`

不得把 uncertain 强行归为 range。

## 5. `s0/s1` 的冻结职责

继续记录但不参与 D2 hard decision：

- local same-envelope reversal；
- middle anchor excursion；
- curvature；
- phase allocation；
- corresponding-leg duration asymmetry。

D2 只回答 parent translation state；不宣称解决 channel shape。

## 6. synthetic hard gates

代码必须先通过：

1. higher highs + higher lows -> uptrend；
2. lower highs + lower lows -> downtrend；
3. both envelope endpoints stable -> range；
4. s0/s1 反号，但 net 与 s2 都明确向上 -> uptrend；
5. s0/s1 反号，但 net 与 s2 都明确向下 -> downtrend；
6. one envelope up, one down -> uncertain；
7. one envelope clear, one weak -> uncertain；
8. 原 D0 反例 `[-0.2335380601,-0.2638717691,-0.3512174141]` -> downtrend；
9. low-start/high-start 映射对称；
10. 正比例价格缩放与平移在已有 amplitude-normalized steps 下不影响 D2；
11. D0/D1 历史值不被覆盖。

## 7. 主 5m mechanism audit

固定 `5m_offset_0`，报告但不按数量判优：

- evaluated / qualified / selected identity exact match；
- v0.5.4 qualification flags exact match；
- selected record IDs / occurrence bars exact match；
- D1 -> D2 transition table；
- D2 counts；
- transition by v0.5.5 uncertain subtype；
- D2 range 的 s0/s1 reversal / middle-anchor excursion distribution；
- D2 trend 中 envelope margin distribution；
- old D0 explicit counterexample regression；
- 2018/2019/2020 + case_00/02/10/11/14 audit；
- future_outcome_used=false；trade_authority=false。

主 5m **不以** range 增加、uncertain 减少、类别均衡为 PASS。

### main-5m PASS 条件

1. upstream identity / qualification / selection zero drift；
2. synthetic semantics 全过；
3. 原 D0 明确 downtrend 反例不回归；
4. D2 变化严格可由 frozen envelope rule 解释；
5. 没有 NaN / asymmetric low-high implementation / clock mutation；
6. safety cases 不出现由 D2 反向修改上游结构的现象（理论上应为零）。

达到以上，只能进入 multiview，不代表 morphology accepted。

## 8. multiview 冻结门

若 main-5m PASS：

- `5m_offset_0..4` full + 25/50/75% prefix；
- `1m_official` 仅 causal diagnostic；
- 18 次已 confirmed D2 classification zero rewrite；
- candidate/qualification/selected interval 继续 exact frozen；
- native-5m selected interval IoU 必须与 v0.5.4 完全相同（因为 D2 不重排 ledger）；
- 新增报告 overlapping selected intervals 上 D1 vs D2 label agreement；
- D2 label agreement 不得四项系统性低于 D1；否则不能升格方向层。

不使用收益或第三浪 outcome。

## 9. 最终状态边界

即使 v0.5.6 通过 multiview，也只能得到：

`parent_identity + qualification + parent_direction_candidate`

之后仍需 independent morphology acceptance，才能讨论 H1/H2。

`trade_authority=false` 始终不变。
