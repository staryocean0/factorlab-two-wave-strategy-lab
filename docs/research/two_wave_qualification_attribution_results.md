# v0.5.2 frozen qualification rejection attribution 结果

日期：2026-09-06  
状态：`diagnostic_complete_no_rule_changed`

## 1. 正式证据

- protocol：`docs/research/two_wave_qualification_attribution_protocol.md`
- commit：`c90f62614e2d25250b2904c737e36685b65ec6e2`
- GitHub Actions run：`33984103882` — success
- artifact：`9974663139`
- artifact SHA256：`2ade7d11f82f440090f55d3828a055ce4a86e5626c0970b0550d949e87e88a1e`
- package validation / full regression：全部通过

本轮只读取冻结 v0.5.2 的 rejection reasons；没有修改任何 qualification 公式、阈值、D1、ledger 或 parent identity。

主 `5m_offset_0`：38,049 evaluated / 425 qualified / 37,624 rejected / 256 selected。

## 2. 总拒绝数不能直接决定下一项实验

总出现次数：

| reason | total |
|---|---:|
| corresponding_leg_duration_mismatch | 30,513 |
| jump_dominated_leg | 29,022 |
| short_leg | 27,775 |
| short_cycle | 24,421 |
| cycle_duration_mismatch | 17,659 |
| amplitude_mismatch | 16,380 |
| inefficient_leg | 11,437 |
| confirmation_too_late | 7,619 |
| long_cycle | 6,304 |
| long_pair | 4,513 |
| too_many_observed_days | 3,652 |
| wall_span_too_long | 1,838 |

但这些规则高度共现。典型：

- `jump_dominated_leg + short_leg`：26,720，Jaccard **0.888**；
- `jump_dominated_leg + short_cycle`：23,210，Jaccard **0.768**；
- `short_cycle + short_leg`：22,990，Jaccard **0.787**；
- `long_cycle + long_pair`：Jaccard **0.716**，lift **5.97**；
- `long_cycle + too_many_observed_days`：lift **5.97**；
- `inefficient_leg + long_cycle`：lift **2.93**。

所以“total 最大”往往只是同一坏结构的多个症状，不能据此直接松规则。

## 3. 真正的 exclusive near-pass

37,624 rejected 中，只有 1,176 个只差一条规则。

| reason | exclusive-only |
|---|---:|
| inefficient_leg | **355** |
| corresponding_leg_duration_mismatch | **309** |
| jump_dominated_leg | 150 |
| confirmation_too_late | 125 |
| short_cycle | 110 |
| amplitude_mismatch | 79 |
| short_leg | 38 |
| long_cycle | 6 |
| wall_span_too_long | 4 |
| cycle_duration_mismatch | **0** |
| long_pair | **0** |
| too_many_observed_days | **0** |

这给出两个重要结论：

1. 完整周期 `cycle_duration_mismatch` 虽总出现 17,659 次，但 **exclusive=0**，当前没有证据支持把它作为首个单组件修改对象。
2. `corresponding_leg_duration_mismatch` 是一个真正独立的资格瓶颈，而不是只伴生于其它坏结构。

## 4. 为什么不继续先改 efficiency

`inefficient_leg` exclusive=355 为最高，但 v0.5.3 已经对最自然的尺度对齐修正做了严格单组件实验：保持阈值0.5，仅把 ER 从 raw close 改到 exact-ridge tuple 的 birth-scale causal TCSS。结果主5m反而把 efficiency 拒绝从11,437增至20,850，并丢失292个原qualified，且2018-06-20的24/29固定父结构被新ER单独拒绝。

因此当前证据不支持继续通过“换平滑尺度”或直接调低0.5来解决 efficiency。它保留为未来独立问题。

## 5. corresponding-leg duration exclusive near-pass 的结构

309 个只因 `corresponding_leg_duration_mismatch` 被拒的对象：

- birth scale 主要在 level 4/5：116 / 106；
- 完整两周期时长比：median **1.50**，p90 **1.917**，max **2.0**；
- 即它们全部已经满足冻结的完整周期 `duration_ratio<=2`；
- 对应半浪最大时长比：min **2.059**，p10 **2.2**，median **2.75**，p90 **4.15**，max **7.25**；
- min raw leg ER：median **0.578**，全部 >0.5；
- max jump share：median **0.401**，p90 **0.477**，全部 <0.5。

这不是“大量对象只差2.0一点点”，因此不应把实验定义为事后把2.0调成2.2/2.5/3.0。

更合理的语义问题是：**两个完整周期同尺度，是否本来就不要求对应半浪持续时间相似。**

## 6. 固定窗口支持把这个问题独立拿出来

- 2018-06-20：54 overlap，已有1个qualified；没有 exclusive duration near-pass，因此下一实验不应破坏这个已通过对象。
- 2019-04-15：58 overlap / 0 qualified；存在 **1个只因 corresponding-leg duration mismatch** 被拒的对象。
- 2020-07-15：60 overlap / 1 qualified；存在 **1个只因 corresponding-leg duration mismatch**、2个只因 efficiency 被拒的对象。
- case_11：7个 corresponding-leg exclusive near-pass。
- case_14：7个 corresponding-leg exclusive near-pass。
- case_00：没有对应腿时长的 exclusive near-pass；代表性粗父结构仍同时有 duration mismatch + efficiency + jump，因此不能把 case_00 当作本轮成功目标。
- case_02：有1个 corresponding-leg exclusive near-pass，同时有3个 jump-only near-pass；必须作为安全审计，不能因为去掉半浪时长门而复活90/3类假结构。

## 7. 下一项结果前假说

下一项单组件不调整任何阈值，而检验金融/数学边界：

> **同尺度属于完整周期（full-cycle period）的属性；对应半浪的时间分配属于波形形态/父状态，不应作为 same-scale 资格硬门。**

因此 v0.5.4 计划：

- parent identity：冻结 v0.5.2；
- `cycle_duration_ratio<=2`：冻结；
- `corresponding_leg_duration_mismatch`：只从 qualification hard gate 降为 diagnostic；
- efficiency=0.5、jump=0.5、amplitude、short/long cycle、clock、confirmation、D1、ledger：全部冻结；
- 不把 309 新 near-pass 或 selected 数量增加当成功理由；
- 先主5m机制审计，再看 fixed cases 与 offset/prefix 安全门。

如果该消融导致 case_02、短腿/jump坏结构或 offset 稳定性系统退化，则直接否定，恢复 v0.5.2 qualification。
