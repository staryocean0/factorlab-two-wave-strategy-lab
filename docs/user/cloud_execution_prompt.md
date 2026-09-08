# Cloud execution prompt

请先完整阅读：

1. `CONTINUE_HERE.md`
2. `docs/governance/reversal_mean_reversion_program_charter_v1.json`
3. `docs/governance/reversal_mean_reversion_program_state_v1.json`
4. `docs/research/reversal_mean_reversion_program_whitepaper_v1.md`
5. `AGENTS.md`
6. `docs/INDEX.md`

然后按**广义反转 / 均值回归方向发现器**接管本仓。

## 当前仓库级任务

不要把仓库重新解释成“只继续优化两浪识别器”。

现有两浪 v0.x 研究现在属于：

`M0_two_wave_structure_measurement_foundation`

它提供因果的 scale / parent state / wave / path measurement 语言。当前 v0.6.17 authoritative-source formal replay 仍是 M0 自己的合法待办，但不阻止不依赖 morphology acceptance 的 broad results-blind preanalysis。

当前三条主研究线：

- `R1_cross_scale_pullback`：父趋势完整时，低一级反向冲击是否只是回撤；
- `R2_range_boundary_reversion`：父级震荡时，越界是暂时 overshoot 还是新趋势；
- `R3_structural_exhaustion_transition`：父级方向尚在但结构恶化时，反转/转换风险是否上升。

## 第一阶段工作方式

本仓是方向发现器，不是单策略优化器。

请：

- 先冻结公共 scale / parent-state / deviation / recovery 口径；
- 对 R1/R2/R3 各写一个 bounded、results-blind 的浅层 preanalysis；
- 每条路线使用相近的小候选预算；
- 优先复用现有因果两浪 measurements 和已提供 DataHub data surface；
- 先看 phenomenon / causal observability / chronological stability；
- 比较三条路线后再决定谁值得 dedicated deep identity。

不要：

- 因为 M0 还有 v0.6.17 待办就停掉其他独立研究；
- 自动继续设计 v0.6.18/v0.6.19；
- 用 PnL 选择 recognizer、threshold 或 parent-state formula；
- 失败后不断加过滤器救策略；
- 把算法生成标签当 morphology ground truth；
- 把已消费的 2015-2020 或其他旧证据称 fresh；
- 进入 Layer 4 / paper trading / production。

## M0 v0.6.17 并行任务

若当前任务明确要求继续 M0，则严格按原冻结链执行：

`full local Stage 1 pytest/conformance -> authoritative DataHub support topology -> price-blind bound registry checkpoint -> oracle coverage/tightness formal replay -> local feedback -> cloud review`

继续使用 accepted DataHub 349,923-row source surface，不得用 FactorLab 350,561-row `1m_official` 替代 exact support。

M0 的 green run 本身不构成仓库级反转策略成功，也不构成 morphology acceptance，除非其自己的 frozen acceptance gate 明确通过并完成复核。

## 交付要求

每次交付写清：

- 当前执行的是 M0 还是哪条 R lane；
- 修改了什么；
- 实际在哪执行；
- 用了哪些数据、证据角色是什么；
- 样本量；
- pass / fail / unresolved；
- 哪些结论仍被冻结；
- 下一步是否仍属于 broad shallow discovery，还是应该 handoff 给 dedicated identity。

Production authority = `false`。
