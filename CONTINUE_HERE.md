# 两浪研究继续入口：v0.6.11 endpoint-robust roughness audit 已闭合（2026-09-07）

当前全局状态：`morphology_replication_not_yet_accepted`；操作基线仍为 **v0.4.3**；PR #1 保持 Draft。Direction/D1/D2/PAWCT、H1/H2、第三浪、收益/P&L、fresh OOS、paper trading、production 全部继续冻结。

## 已闭合关键链条

- v0.6.0：financial identity / exclusive packing 解耦；
- v0.6.1–v0.6.5：raw identity attribution、projection repair、first-valid append-only publication；
- v0.6.6–v0.6.7：qualification mixed stability，path sampling sensitivity 主导；
- v0.6.8–v0.6.9：shared 1m + 原 threshold 不成立；efficiency/jump 是 resolution-specific measurements；
- v0.6.10：fine concentration / origin ensemble 显著降低 jump bar-origin aliasing，但 fine roughness 仍 endpoint-sensitive；
- v0.6.11：固定 25-cell inward erosion roughness ensemble **materially reduces endpoint/interval sensitivity**。

## v0.6.11 正式证据

结果前：

- `docs/research/two_wave_roughness_interval_sensitivity_preanalysis_v0611.md`
- `docs/research/two_wave_roughness_interval_sensitivity_protocol_v0611.md`

正式结果：

- `docs/research/two_wave_roughness_interval_sensitivity_results_v0611.md`
- `cloud_results/cloud_chat_v0611_roughness_interval_sensitivity/summary.json`
- `per_view_roughness.json`
- `erosion_availability.json`
- `pair_decomposition.json`
- `common_support_oracle.json`
- `boundary_slivers.json`
- `strata_overlays.json`
- `data_identity.json`
- `execution_receipt.json`

Helper blob `bc3275c6c94ec8b5d5cc7c4979c278c4f74169b9`；test blob `10b99bb63b3d378ce6c3a7513e89865bba154dc9`；synthetic tests **9/9 PASS**。

Hard controls：

```text
tuple births = 38,636 / 37,176 / 37,062 / 36,937 / 36,689
publications = 38,176 / 36,737 / 36,619 / 36,480 / 36,264
filtered mutual-unique pairs = 14,784 / 12,725 / 13,412 / 16,108
published raw strict = 8,381 / 5,770 / 6,204 / 9,098 = 29,453
qualification matrix = 482 / 28,272 / 352 / 347
target repaired = 80; target disagreement = 24
```

## v0.6.11 decisive result

同一 v0.6.10 comparable universe：**117,805 strict pair-leg observations**。

```text
original fine roughness abs-diff
median 0.083145
p90    0.392796

erosion-ensemble median roughness abs-diff
median 0.028086
p90    0.177399
```

Paired signs：

```text
candidate smaller 83,901
candidate equal      162
candidate larger  33,742
```

即 **71.22%** pair-leg 改善；四个 harmless offsets 全部同方向。

Availability 没有造成 decisive-selection artifact：全五视图 737,104 published legs 中 641,645 条拥有 25/25 defined erosion cells，仅 19 条 0/25；decisive pair-leg universe仍完整保留 117,805。

Common-support oracle 对 117,805/117,805 pair-leg 可用，side-to-common roughness absolute change median `0.026477`。Erosion-grid range 与原 roughness disagreement Spearman `0.557`，支持 endpoint sensitivity 机制。

正式裁决：

> **`endpoint_erosion_ensemble_materially_reduces_roughness_interval_sensitivity`**

它仍只是 continuous-property structural result，不创建 qualification threshold，也不改变 financial identity。

## 下一 formal research step

按照 workstream 隔离规则，roughness endpoint-sensitivity 已完成一轮正向结构验证。下一步转到**独立的 concentration deployable-proxy workstream**：

> supplied-1m 上已表现稳定的 `fine_concentration / origin_jump_median / origin_jump_range`，能否仅用当前 native 5m causal information 构造一个可部署 proxy，并给出对未知 5m bar-origin aliasing 的 deterministic/empirical error envelope。

下一版必须先写 results-blind preanalysis + frozen protocol，再看 proxy 结果。

必须保持：

- 不拟合 qualification threshold；
- 不把 supplied 1m 直接设为 production input；
- 不改 matcher / projection / publication；
- roughness erosion candidate 在该 workstream 内保持冻结，不混合优化；
- 不使用 direction / outcome / P&L；
- 不进入第三浪、fresh OOS、paper trading 或 production。
