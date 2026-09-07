# 两浪研究继续入口：v0.6.13 step-count normalized concentration audit 已闭合（2026-09-07）

当前全局状态：`morphology_replication_not_yet_accepted`；操作基线仍为 **v0.4.3**；PR #1 保持 Draft。Direction/D1/D2/PAWCT、H1/H2、第三浪、收益/P&L、fresh OOS、paper trading、production 全部继续冻结。

## v0.6.13

正式结果：`step_count_normalization_reduces_duration_bias_but_not_cross_resolution_gap`。

关键 hard controls：publications `38,176 / 36,737 / 36,619 / 36,480 / 36,264`；published raw strict `8,381 / 5,770 / 6,204 / 9,098 = 29,453`；both-qualified `482`；qualification disagreements `699`；target repaired `80 = 56+24`；v0.6.10 oracle-comparable pair-leg universe `117,805`。

Registered profile：`C_inf = log(n*max w)`、`C_1 = log(n)-H(w)`、`C_2 = log(n*sum(w^2))`。三者对 uniform k-fold subdivision 严格不变。

Raw `|J5-J1|` gap vs native step-count Spearman `-0.884`；normalized `C_inf/C_1/C_2` 为 `0.174 / -0.223 / -0.036`，说明纯 step-count bias 大幅下降。

但 native/fine profile 仍存在系统 cross-resolution gap：Spearman `0.714 / 0.437 / 0.514`；signed native-fine median `-0.5185 / -0.1013 / -0.1833`。Fine profile 跨 slicer median abs diff `0.0360 / 0.0176 / 0.0267`，native profile 为 `0.1659 / 0.0922 / 0.1293`。C1/C2 Spearman native/fine 都约 `0.98`，且 native profile availability 仅 `664,001 / 737,104` published legs。

证据入口：
- `docs/research/two_wave_step_count_normalized_concentration_preanalysis_v0613.md`
- `docs/research/two_wave_step_count_normalized_concentration_protocol_v0613.md`
- `docs/research/two_wave_step_count_normalized_concentration_results_v0613.md`
- `cloud_results/cloud_chat_v0613_step_count_normalized_concentration/`

## 下一 formal research step

只允许 results-blind **native multiscale/refinement-aware concentration representation preanalysis**：仅用 native causal data 构造多个固定 sub-partitions / scale-response coordinates，把真实 refinement uncertainty 显式表示出来，再用 supplied 1m 作为 audit oracle 验证结构关系。

不得拟合 duration correction / qualification threshold；不得事后挑最优 partition / descriptor；不得把 supplied 1m 设为 production input；roughness erosion candidate 保持冻结；不得修改 matcher/projection/publication，不得使用 direction/outcome/P&L，不得进入第三浪、fresh OOS、paper trading 或 production。
