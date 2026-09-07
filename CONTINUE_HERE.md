# 两浪研究继续入口：v0.6.10 threshold-free path-property audit 已闭合（2026-09-07）

当前全局状态：`morphology_replication_not_yet_accepted`；操作基线仍为 v0.4.3；PR #1 保持 Draft。Direction/D1/D2/PAWCT、H1/H2、第三浪、收益/P&L、fresh OOS、paper trading、production 全部继续冻结。

## 已闭合关键链条

- v0.6.0：financial identity / exclusive packing 解耦 = Route M；
- v0.6.1：unmatched decomposition；
- v0.6.2：raw projection identity audit；
- v0.6.3：ordinal0 left-support residual 定位；
- v0.6.4：birth-scale predecessor POC，机制有效但 identity 多值，不 promoted；
- v0.6.5：first-valid causal append-only publication，消除 rewrite 并保留 strict-match gain；
- v0.6.6：published strict identity 上 frozen v0.5.4 qualification = mixed stability；
- v0.6.7：qualification disagreement decomposition = path sampling sensitivity dominant；
- v0.6.8：shared 1m path + 原 thresholds 主要制造 joint rejection，不 promoted；
- v0.6.9：efficiency / jump 的 resolution semantics 相反，禁止简单 threshold remap；
- v0.6.10：threshold-free roughness / hidden variation / concentration / origin-ensemble property audit = **origin ensemble 明显削弱 jump 的 bar-origin aliasing，但 fine roughness 仍对 published leg endpoint 轻微错位敏感**。

## v0.6.10 正式证据

结果前：
- `docs/research/two_wave_path_property_redefinition_preanalysis_v0610.md`
- `docs/research/two_wave_path_property_redefinition_protocol_v0610.md`

正式结果：
- `docs/research/two_wave_path_property_redefinition_results_v0610.md`
- `cloud_results/cloud_chat_v0610_path_property_redefinition/summary.json`
- `cloud_results/cloud_chat_v0610_path_property_redefinition/per_view_property_response.json`
- `cloud_results/cloud_chat_v0610_path_property_redefinition/cross_slicer_descriptor_differences.json`
- `cloud_results/cloud_chat_v0610_path_property_redefinition/origin_ensemble.json`
- `cloud_results/cloud_chat_v0610_path_property_redefinition/component_associations.json`
- `cloud_results/cloud_chat_v0610_path_property_redefinition/strata_overlays.json`
- `cloud_results/cloud_chat_v0610_path_property_redefinition/data_identity.json`
- `cloud_results/cloud_chat_v0610_path_property_redefinition/execution_receipt.json`

Helper blob `a1c3bcf5e3c51d30729bb333c0ea31a38cf0d834`；test blob `ca4d8bf0f2f281a68bd11fa2e815596a5a6af8d2`；synthetic tests 9/9 PASS。

Hard controls：tuple births `38,636 / 37,176 / 37,062 / 36,937 / 36,689`；published identities `38,176 / 36,737 / 36,619 / 36,480 / 36,264`；filtered mutual-unique pairs `14,784 / 12,725 / 13,412 / 16,108`；published raw strict pairs `8,381 / 5,770 / 6,204 / 9,098 = 29,453`；v0.6.6 matrix `482 / 28,272 / 352 / 347`；target repaired `80`，其中 disagreement `24`。

737,104 published legs 中 descriptor 可用 737,070，仅 34 unavailable。Efficiency / jump algebraic identity 最大误差均 <9e-16。Numba origin-ensemble execution accelerator 与 frozen Python helper 在 100 条随机真实腿上 100/100 exact-equivalence PASS。

## v0.6.10 关键结论

在 117,805 个 strict pair-leg observations 上：

- native `J5` abs-diff median `0.053931`, p90 `0.220604`；
- `fine_concentration=J1` median `0.006474`, p90 `0.059680`，86.46% pair-leg 比 native J5 更稳定；
- `origin_jump_median` median `0.016958`, p90 `0.094801`，78.15% pair-leg 比 native J5 更稳定；
- `origin_jump_range` 与 native-origin 对 ensemble median 的绝对误差 Spearman `0.582`；TV-origin range 对应关系 `0.617`。

但是：

- native roughness `-log(E5)` abs-diff median `0.021658`, p90 `0.181079`；
- `fine_roughness=log(TV1/D)` median `0.083145`, p90 `0.392796`；63.99% pair-leg 上 fine roughness 更不稳定。

所以正式裁决：

`origin_ensemble_reduces_origin_aliasing_but_fine_property_remains_interval_sensitive`

含义：concentration/origin-ensemble 是有结构价值的 continuous property，但 roughness 仍被 <=5m published endpoint displacement materially 影响，整个 path property 还不能 promotion，也不能开新 threshold。

## Compact-evidence caveat

v0.6.10 正式裁决后 runtime 曾重置；aggregate exact distributions / paired-sign counts / hard controls 均已保留。少量未在 reset 前落盘的 per-offset/stratum quantiles 没有事后猜测重建，compact files 中已明确标记。这不改变 formal adjudication，但后续如需要逐 offset quantile 作为新 hard control，应单独 replay 后再冻结。

## 下一 formal research step

**先只开 interval-sensitivity workstream，不与 deployable concentration proxy 混在同一实验。**

下一版优先研究：为什么 fine roughness 对 <=5m endpoint displacement 敏感，以及是否存在不改变 financial identity、保持 prefix causality 的 endpoint-robust / inward-erosion ensemble roughness representation。

已经较稳定的 fine concentration / origin-ensemble concentration 的 native-5m deployable proxy 留作后续独立版本；避免一轮同时修改两个 property family。

下一轮仍不得：
- 拟合任何 qualification threshold；
- 改 matcher / projection / publication；
- 使用 direction / outcome / P&L；
- 进入第三浪、fresh OOS、paper trading 或 production。
