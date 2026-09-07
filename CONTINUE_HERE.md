# 两浪研究继续入口：v0.6.15 identifiability bound audit 被 data-consistency gate 拦截（2026-09-07）

当前全局状态：`morphology_replication_not_yet_accepted`；操作基线仍为 **v0.4.3**；PR #1 保持 Draft。Direction/D1/D2/PAWCT、第三浪、收益/P&L、fresh OOS、paper trading、production 全部继续冻结。

## 最近闭合链条

- v0.6.13：Rényi/KL-to-uniform step-count normalization 显著削弱 raw-J duration bias，但 native→fine concentration gap 仍 materially 存在；裁决 `step_count_normalization_reduces_duration_bias_but_not_cross_resolution_gap`。
- v0.6.14：native close-only deterministic coarsening response 跨 slicer 较稳定，但几乎不追踪真实 fine-refinement uncertainty；裁决 `native_multiscale_response_is_stable_but_not_informative_of_fine_refinement`。
- v0.6.15：首次停止 point-estimate proxy，改做 native-5m OHLC 对 hidden 1m concentration 的保证型 structural bounds；但 frozen hidden-path information-set assumption 在 offset session boundaries 上发生 material data-consistency failure，因此 tightness 未被解释。

## v0.6.15 正式证据

结果前：
- `docs/research/two_wave_fine_concentration_identifiability_preanalysis_v0615.md`
- `docs/research/two_wave_fine_concentration_identifiability_protocol_v0615.md`

正式结果：
- `docs/research/two_wave_fine_concentration_identifiability_results_v0615.md`
- `cloud_results/cloud_chat_v0615_concentration_identifiability/` 下 8 个 protocol-required compact files

Helper blob `03a534f072e7cd11753e7bbf54dc6333995cb9cb`；test blob `53ce8c4d6b3612e6655410b3ffd43cba2853b3a9`；synthetic tests **8/8 PASS**。

Hard controls：publications `38,176 / 36,737 / 36,619 / 36,480 / 36,264`；strict pairs `29,453`；both-qualified `482`；qualification disagreements `699`；target repaired `80=56+24`；fine profile defined `737,070`；oracle-comparable pair-legs `117,805`。

## v0.6.15 data-consistency failure

Frozen model 假设每个相邻 native close transition 都对应恰好五个 hidden supplied-1m close increments，并且 hidden minute closes 受当前 native bar `[low,high]` 包络。

真实 offset1–4 在午休/隔夜边界会系统出现 `fine index difference = 10`：offset slicer 为维持 origin 会丢弃 session 边界 partial bars，所以相邻 native closes 之间并不总是一个完整 5m bar的信息集。

Published legs 至少包含一个违反 frozen model 的 transition：

```text
offset0    335 / 152,704 = 0.22%
offset1 50,729 / 146,948 = 34.52%
offset2 50,761 / 146,476 = 34.65%
offset3 50,691 / 145,920 = 34.74%
offset4 50,630 / 145,056 = 34.90%
```

在冻结的 117,805 oracle-comparable strict pair-leg 中，**35,905 = 30.48%** 至少一侧违反该 information-set assumption。

因此按 frozen protocol，tightness / coverage interpretation 在此停止；没有删除 session-boundary legs 后继续，也没有经验缩窄 bounds。

正式裁决：

> **`structural_bounds_fail_data_consistency_or_oracle_coverage`**

这里首先是 information-set / data-clock model failure，不是 synthetic outer-bound 数学被推翻。

## 下一 formal research step

只允许 results-blind **session-aware native information-set / structural-bounds preanalysis**。

下一版必须显式区分：

1. complete native 5m bars；
2. offset slicer 丢弃的 session-boundary partial-bar trading minutes；
3. 午休 / 隔夜 gap transition；
4. 每一段真正可用的 native OHLC envelope 与 hidden fine-step count。

不得通过删除边界 legs、改变 same-event matcher、经验 shrink bounds 或回到 point-estimate proxy 来绕过 v0.6.15 failure。只有 session-aware information-set model 先通过 data-consistency / oracle-coverage gates，才允许再次讨论 identifiability/tightness。
