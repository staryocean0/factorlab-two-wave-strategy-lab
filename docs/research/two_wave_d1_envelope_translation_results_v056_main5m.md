# v0.5.6 D2 whole-envelope translation：主 5m mechanism audit

日期：2026-09-06  
状态：`main5m_mechanism_pass_multiview_pending`

冻结协议：`docs/research/two_wave_d1_envelope_translation_protocol_v056.md`  
金融/数学预分析：`docs/research/two_wave_d1_envelope_translation_preanalysis_v056.md`

## 1. 正式执行

最新有效执行：

- workflow：`two-wave-envelope-direction-v056-main5m`
- run：`34009093294`
- execution HEAD：`c12bb0918071db1eab76e6ab1ccc1d5b557a7532`
- artifact：`9981922969`
- artifact SHA256：`a93bd6f45d15feeef29a0ee271810d55c734f4d47bba53e9f84b784540ac6316`
- full regression：PASS
- main-5m mechanism audit：PASS

此前 `3938e599...` 上的失败只来自两个 synthetic 数值边界实现问题：裸浮点 `==0.05` 与 `0.10+0.05` 的 IEEE 表示略超 `0.15`。后续仅加入 `1e-12` 数值比较 epsilon，并把测试改为近似比较；另有 hard gate 证明 `0.150001` 仍为 clear translation。因此没有改变冻结研究阈值 `0.15`。

Node.js 20 deprecation 仅为 GitHub Actions warning，不是失败原因。

## 2. 上游零漂移

D2 只新增方向版本；以下全部 exact match：

- evaluated candidate identity
- v0.5.4 qualification flags
- selected record IDs
- selected occurrence intervals
- 历史 D0/D1 字段
- confirmation / available-at clock

`future_outcome_used=false`，`trade_authority=false`。

因此本实验没有通过改 parent / qualification / ledger 来获得方向结果。

## 3. 主 5m 数量（不作为 PASS 理由）

`5m_offset_0`：

- evaluated：38,049
- qualified：734
- selected：404

qualified labels：

- D1：range 4 / uncertain 371 / uptrend 187 / downtrend 172
- D2：range 22 / uncertain 185 / uptrend 280 / downtrend 247

selected labels：

- D1：range 3 / uncertain 218 / uptrend 101 / downtrend 82
- D2：range 17 / uncertain 106 / uptrend 155 / downtrend 126

不能把 uncertain 减少或类别更均衡解释为准确率提升。

## 4. D1 -> D2 qualified transition

- range -> range：4
- uncertain -> uptrend：105
- uncertain -> downtrend：80
- uncertain -> range：18
- uncertain -> uncertain：168
- uptrend -> uptrend：175
- uptrend -> uncertain：12
- downtrend -> downtrend：167
- downtrend -> uncertain：5

没有 D1 uptrend 直接翻为 downtrend，亦没有 D1 downtrend 直接翻为 uptrend；原趋势只有在另一条完整 envelope 缺少明确同向迁移时降为 uncertain。

## 5. v0.5.5 uncertain 归因如何映射到 D2

D1 uncertain 共 371：

- `same_phase_reversal_conflict` 243：D2 up 75 / down 61 / range 18 / uncertain 89
- `strong_net_with_opposed_phase` 40：D2 up 12 / down 9 / uncertain 19
- `coherent_but_subthreshold` 36：D2 up 10 / down 7 / uncertain 19
- `opposite_envelope_conflict` 18：全部仍 uncertain
- `single_phase_dominant` 17：全部仍 uncertain
- `large_migration_without_coherent_direction` 17：D2 up 8 / down 3 / uncertain 6

核心机制与 v0.5.5 归因一致：D1 最大失败类不是“阈值太严”，而是把共享 envelope 上的两个局部步 `s0/s1` 当作独立趋势投票。D2 改用完整 upper/lower envelope 总迁移后，局部 reversal 不再自动否定父级 translation。

## 6. D2 range 的金融含义

22 个 qualified D2 range 中：

- 21 个（95.45%）存在 `s0*s1<0` 的局部 same-envelope reversal；
- `max(|s0|,|s1|)` 中位数约 0.490，p90 约 1.340，最大约 2.068。

这不是 bug，而是 D2 与 D1 的核心语义区别：

> parent range 允许内部存在大幅波动，只要求两个完整 parent envelopes 在两浪窗口内没有形成明确同向迁移。

因此 D2 不等价于“低波动”或“所有局部步都小”。

## 7. D2 trend margin

527 个 qualified D2 trend 的较弱 envelope 相对 `0.15` 的超额 margin：

- min：0.00167
- p10：0.0881
- p25：0.2691
- median：0.5943
- p75：1.0233
- p90：1.5611
- max：3.9580

边界附近对象被保留审计，但没有据此重新选阈值。

## 8. 固定窗口 / safety audit

- 2018-06-20：D1 uncertain -> D2 uptrend；两条 envelope 均明确向上。
- 2019-04-15：D1 uncertain -> D2 uptrend；两条 envelope 均明确向上。
- 2020-07-15：原 D1 downtrend 保持 D2 downtrend；另一 qualified 仍 uncertain。
- case_00：仍 0 qualified，D2 不回头修改 qualification。
- case_02：唯一 qualified/selected 对象 D1 uptrend -> D2 uptrend；旧 90/3 假结构没有通过上游复活。
- case_10：当前新 parent candidate D1 uncertain -> D2 downtrend；legacy `stable_range` 名称仅是旧回归图集标签，不是独立真值，保留为后续独立 morphology acceptance 的重点争议案例。
- case_11：大区间内多个不同 parent pairs 产生不同局部状态；D2 不把整个 legacy 长窗口强行赋一个标签。
- case_14：大区间内同样含多个局部 parent states；legacy 名称不是本轮 outcome label。

因此 fixed/legacy cases 没有暴露 D2 反向修改上游结构的现象；但 case_10/11/14 继续保留为后续独立形态验收重点，不能用本轮自洽性替代独立准确率。

## 9. 主 5m 裁决

结果前协议的 main-5m 六项 PASS 条件全部满足：

1. upstream identity / qualification / selection zero drift：PASS
2. synthetic semantics：PASS
3. 原 D0 明确 downtrend 反例不回归：PASS
4. D2 变化严格由 frozen envelope rule 解释：PASS
5. 无 NaN / low-high asymmetry / clock mutation：PASS
6. safety cases 不修改上游结构：PASS

正式状态：

> **`main5m_mechanism_pass_multiview_pending`**

下一步只允许按冻结协议进入 multiview：五个 native 5m full + 25/50/75% prefix，以及 `1m_official` 三个 causal prefix。D2 方向层只有在 18/18 confirmed classification zero rewrite、selected interval 继续 exact frozen，且 native-5m overlap 上 D2 label agreement 不四项系统性低于 D1 后，才可升格为 `parent_direction_candidate`。

仍不进入收益、第三浪/H1/H2 或交易。