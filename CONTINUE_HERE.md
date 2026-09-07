# 两浪研究继续入口：v0.6.13 step-count normalized concentration audit 已闭合（2026-09-07）

当前全局状态：`morphology_replication_not_yet_accepted`；操作基线仍为 **v0.4.3**；PR #1 保持 Draft。Direction/D1/D2/PAWCT、H1/H2、第三浪、收益/P&L、fresh OOS、paper trading、production 全部继续冻结。

## 已闭合关键链条

- v0.6.0–v0.6.5：financial identity 解耦、projection repair、first-valid append-only publication；
- v0.6.6–v0.6.9：qualification instability 主要来自 path sampling / resolution semantics；
- v0.6.10：fine concentration / origin ensemble 显著降低 jump bar-origin aliasing；fine roughness endpoint-sensitive；
- v0.6.11：固定 25-cell inward erosion roughness ensemble materially reduces endpoint sensitivity；
- v0.6.12：native true-range concentration 有局部改善，但不能可靠代理 fine concentration；
- v0.6.13：Rényi/KL-to-uniform step-count normalization **显著削弱 raw max-share 的 duration bias，但仍不能消除 native→fine cross-resolution gap**。

## v0.6.13 正式证据

结果前：

- `docs/research/two_wave_step_count_normalized_concentration_preanalysis_v0613.md`
- `docs/research/two_wave_step_count_normalized_concentration_protocol_v0613.md`

正式结果：

- `docs/research/two_wave_step_count_normalized_concentration_results_v0613.md`
- `cloud_results/cloud_chat_v0613_step_count_normalized_concentration/summary.json`
- `cross_resolution_profile.json`
- `step_count_overlay.json`
- `cross_slicer_profile.json`
- `origin_refinement.json`
- `component_associations.json`
- `strata_overlays.json`
- `data_identity.json`
- `execution_receipt.json`

Helper blob `21160853e418b1b05199b8735613b3ab2d2c5350`；test blob `a177c193576a739f2b5500b55a0f65b894da2761`；synthetic tests **9/9 PASS**。

Hard controls：

```text
publications = 38,176 / 36,737 / 36,619 / 36,480 / 36,264
published raw strict = 8,381 / 5,770 / 6,204 / 9,098 = 29,453
both-qualified = 482
qualification disagreements = 699
target repaired = 80 = 56 agreement + 24 disagreement
v0.6.10 oracle-comparable pair-leg universe = 117,805
```

## v0.6.13 result

Registered profile：

```text
C_inf = log(n * max w)
C_1   = log(n) - ShannonEntropy(w)
C_2   = log(n * sum(w^2))
```

三者对 uniform k-fold subdivision 严格不变。

Step-count bias 明显下降：

```text
abs-gap vs native step-count Spearman
raw |J5-J1|  -0.884
C_inf          0.174
C_1           -0.223
C_2           -0.036
```

但 cross-resolution gap 仍在：

```text
native/fine Spearman     abs-gap median    signed native-fine median
C_inf 0.714              0.5185            -0.5185
C_1   0.437              0.1247            -0.1013
C_2   0.514              0.2047            -0.1833
```

Fine profile 跨 slicer 较稳定：median abs diff `C_inf/C_1/C_2 = 0.0360 / 0.0176 / 0.0267`；native profile 对应为 `0.1659 / 0.0922 / 0.1293`。

三维 profile 还高度相关，尤其 `C_1↔C_2` Spearman native/fine 都约 `0.98`。Profile 的 native availability 也只有 `664,001 / 737,104` published legs，因为事前定义要求至少两个 native increments。

正式裁决：

> **`step_count_normalization_reduces_duration_bias_but_not_cross_resolution_gap`**

因此 v0.6.13 不允许 property promotion，也不允许拟合 duration correction。

## 下一 formal research step

只允许另开 results-blind **native multiscale/refinement-aware concentration representation preanalysis**。

目标不是继续拟合一个 native scalar 到 J1，而是研究：仅使用 native causal data，能否构造多个固定 sub-partitions / scale-response coordinates，把真实 refinement uncertainty 显式表示出来，并在 supplied 1m audit oracle 上验证其结构关系。

下一轮仍必须：

- 不拟合 duration correction 或 qualification threshold；
- 不事后选择最优 partition / descriptor；
- 不把 supplied 1m 设为 production input；
- roughness erosion candidate 保持冻结；
- 不改 matcher / projection / publication；
- 不使用 direction / outcome / P&L；
- 不进入第三浪、fresh OOS、paper trading 或 production。
