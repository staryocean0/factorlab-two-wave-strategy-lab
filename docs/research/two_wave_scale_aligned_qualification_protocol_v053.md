# v0.5.3 结果前协议：birth-scale 因果 TCSS 腿效率单组件实验

日期：2026-09-06  
状态：`protocol_frozen_before_real_result`

## 1. 前置结论

v0.5.2 exact-ridge parent identity 已满足事前晋级门，正式判为：

`parent_identity_pass_qualification_pending`

因此重新激活资格层研究。操作研究基线仍是 v0.4.3；v0.5.2 仅作为 parent candidate identity 的冻结上游，不开放交易、收益或生产权限。

## 2. 唯一研究问题

冻结 v0.5.2 的：

- TCSS 表示；
- extremum ridge IDs；
- ridge death；
- exact-five-ridge tuple birth；
- raw projection；
- raw reversal 金融语义；
- duration / amplitude / jump / flat / observed-day / wall-span / confirmation-delay checks；
- D1；
- deterministic exclusive ledger。

**唯一改变：** `inefficient_leg` 的路径效率测量尺度。

旧定义：逐根 raw close：

`ER_raw = |x_b-x_a| / Σ|x_t-x_{t-1}|`

v0.5.3 定义：使用该 tuple 已事前确定的 `birth_scale_id` 对应的、未左移的因果 TCSS log-price 序列：

`ER_birth_scale = |L_sigma(b)-L_sigma(a)| / Σ|L_sigma(t)-L_sigma(t-1)|`

其中 `[a,b]` 仍由五个 raw parent extrema 的 occurrence bars 定义。TCSS 只测量该 raw 父腿内部的同尺度路径质量，不得创造 raw reversal。

## 3. 数值阈值冻结

`min_leg_efficiency = 0.5` **保持不变**。

本轮禁止：

- 0.5 -> 0.3/0.4 等阈值放松；
- 同时修改 `duration_ratio=2.0`；
- 修改 `max_jump_share=0.5`；
- 修改 amplitude / duration / D1；
- 以 case、offset IoU、候选数量、覆盖、收益反选公式或参数。

## 4. 因果语义

TCSS 序列必须是 time-causal scale space 的原始在线输出，不做 group-delay 左移，不用未来样本修正历史值。

已确认 record 追加未来后：

- v0.5.2 ridge tuple identity 不得改变；
- birth scale 不得改变；
- 五个 raw occurrences 不得改变；
- 四腿 scale-aligned ER 不得改变；
- qualification / selected 状态不得改写。

## 5. Synthetic hard gates

真实数据前至少满足：

1. 父波 + 高频子摆：若 birth-scale TCSS 已吸收子摆，scale-aligned ER 可高于 raw ER；
2. 单次 jump：即使 scale-aligned ER 很高，仍必须被 frozen raw `jump_dominated_leg` 拒绝；
3. duration / amplitude 拒绝不得因本实验消失；
4. 严格单调 raw price 不得凭平滑产生两浪；
5. prefix extension 不得改变已确认 ER；
6. 输入 v0.5.2 record 不得被原地修改。

## 6. 第一阶段真实数据：主 5m 机制审计

先只运行 `5m_offset_0`，不看收益。

必须报告：

- v0.5.2 与 v0.5.3 evaluated candidate identity 是否一一一致；
- `inefficient_leg` 拒绝数 before / after；
- only-inefficiency rejection 被释放的数量；
- v0.5.3 qualified / selected 数量，仅作描述，不作为成功理由；
- raw ER 与 birth-scale ER 的 min-leg quantiles；
- rejection reason 频率 before / after；
- 2018-06-20 固定窗口的机制审计；
- case_00 仅作已冻结 fixed audit，不用于调公式。

主 5m 若显示该单组件几乎没有机制影响，或主要通过平滑掩盖 jump/其它坏结构，则立即否定，不扩到六视图。

## 7. 第二阶段真实数据：六视图因果与稳健性

只有主 5m 机制成立才扩展：

- `5m_offset_0..4`；
- `1m_official` 仅诊断；
- 六视图 × 25%/50%/75% = 18 次 prefix replay；
- 五个 native 5m offset 的发布边界 IoU；
- case_02 / 11 / 14 安全审计。

## 8. 晋级判据

v0.5.3 只有在以下条件同时成立时才保留：

1. parent identity 与 v0.5.2 完全一致；
2. 18 次 prefix replay 零 confirmed rewrite；
3. 0.5 数值阈值未变；
4. 2018 类型“父级已成立、raw 内部含子摆”的拒绝得到机制一致改善；
5. jump / flat / 90-3 / 跨周巨型结构安全门不退化；
6. 五个 native 5m offset 边界稳定性不系统性恶化；
7. 不以 candidate/selected 数量增加或收益作为晋级理由。

若 scale-aligned ER 成立，则下一轮才单独研究 duration similarity；若失败，保留 v0.5.2 parent identity，回到 qualification 归因，不修改 representation。
