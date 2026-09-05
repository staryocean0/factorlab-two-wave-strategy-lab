# v0.5.4 结果前协议：完整周期定义尺度、半浪时长只作形态诊断

日期：2026-09-06  
状态：`protocol_frozen_before_real_result`

## 1. 前置事实

- v0.5.2 exact-ridge parent identity：`parent_identity_pass_qualification_pending`；
- v0.5.3 birth-scale TCSS leg-efficiency：主5m机制实验否定；
- frozen qualification attribution：`corresponding_leg_duration_mismatch` 有309个 exclusive near-pass，而 `cycle_duration_mismatch` exclusive=0。

因此本轮不调 duration ratio 数值，而检验 qualification 语义边界。

## 2. 唯一假说

金融合同中的“同尺度”定义为：**两个完整 reversal cycle 的时间尺度相近**。

若两周期分别由：

- cycle 1 = leg1 + leg2
- cycle 2 = leg3 + leg4

组成，则 scale qualification 继续由冻结的完整周期 duration checks 约束，包括 `cycle_duration_ratio <= 2.0`、min/max cycle、pair duration 等。

本轮唯一变化：

> `corresponding_leg_duration_mismatch` 不再作为 same-scale qualification hard rejection；它仍完整计算、保存并作为 morphology diagnostic。

数学理由：对应半浪在完整周期中的时间占比可随趋势漂移、相位不对称、局部速度变化而改变；强迫 leg1≈leg3 且 leg2≈leg4 会把 phase allocation 当成 scale，本质上把父状态/波形形态混入尺度资格。

## 3. 明确不是阈值放松实验

冻结：

- `duration_ratio = 2.0` 数值不变；
- `min_cycle / max_cycle / min_pair / max_pair` 不变；
- `min_leg` 不变；
- amplitude 不变；
- raw path efficiency `>=0.5` 不变；
- jump share `<=0.5` 不变；
- flat、observed days、wall span、confirmation delay 不变；
- v0.5.2 TCSS / ridge / tuple identity / raw projection 不变；
- D1 和 deterministic ledger 不变。

禁止根据309个 near-pass 的分布把2.0改成2.2、2.75、3、4等。

## 4. 因果与 identity

v0.5.4 直接复用 v0.5.2 evaluated candidate identity。对每条 record：

- ridge tuple ID 不变；
- five raw occurrences 不变；
- birth scale 不变；
- confirmation bar 不变；
- 所有诊断数值不重算；
- 只从 `scale_rejection_reasons` 中移除 `corresponding_leg_duration_mismatch`；
- diagnostic 字段明确保留原 rule 是否触发及原 corresponding-leg duration ratios。

追加未来不得改写已确认 record。

## 5. Synthetic hard gates

真实数据前必须证明：

1. 两个完整周期时长相近，但 phase allocation 明显不同：只要其它冻结规则通过，不应因 corresponding-leg mismatch 被拒；
2. 一个完整周期相对另一个超过 `duration_ratio=2`：仍必须被 `cycle_duration_mismatch` 拒绝；
3. short leg / short cycle 仍拒绝；
4. jump dominated 仍拒绝；
5. inefficient leg 仍拒绝；
6. amplitude mismatch 仍拒绝；
7. 原 v0.5.2 record 不原地修改；
8. 除 corresponding-leg reason 外，每一条 frozen rejection presence 对每个 candidate 完全相同。

## 6. 第一阶段：主5m机制审计

只运行 `5m_offset_0`。

必须报告：

- candidate identity exact match；
- v0.5.2 / v0.5.4 qualified / selected，仅描述；
- newly qualified 必须与 attribution 中 corresponding-leg exclusive-only 集合严格一致；
- lost qualified 必须为0；
- newly qualified 的 birth-scale、cycle-duration-ratio、leg-ratio、ER、jump 分布；
- 2018-06-20：原qualified结构不得丢失；
- 2019-04-15 / 2020-07-15：审计 attribution 中的 duration-only near-pass 是否自然释放；
- case_00：不得声称解决；
- case_02：重点检查90/3类/假结构是否因该消融获得 qualification；
- case_11 / 14：只作冻结案例审计。

若主5m显示新增结构主要是明显微腿/jump坏对象，或 case_02 安全门退化，则直接否定，不扩五视图。

## 7. 第二阶段：五个 native 5m + 1m causal diagnostic

只有主5m机制成立才扩展：

- 五个 native 5m full + 25/50/75% prefix；
- 1m_official full + 25/50/75% prefix；
- 18次 prefix zero rewrite；
- native-5m offset coverage/label IoU；
- case_02 / 11 / 14 安全门。

## 8. 晋级条件

v0.5.4 只有同时满足才保留：

1. parent candidate identity 与 v0.5.2 完全一致；
2. 所有非 corresponding-leg rejection 完全冻结；
3. 18/18 prefix zero rewrite；
4. cycle-scale hard rules不退化；
5. jump / short / efficiency / amplitude 安全门不退化；
6. case_02 不复活明显假结构；
7. native-5m offset 稳定性不系统性恶化；
8. 结果解释来自“尺度与phase allocation解耦”的机制，而不是 qualified/selected 数量增加。

失败则恢复 v0.5.2 frozen qualification，下一轮重新归因；不得事后把对应腿 ratio 改成另一个数值。
