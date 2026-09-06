# 两浪研究继续入口：v0.6.9 path-metric resolution response 已闭合（2026-09-06）

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
- v0.6.9：path-metric resolution-response audit = efficiency 与 jump 具有相反的 resolution semantics，需要先重定义 underlying path property。

## v0.6.9 正式证据

结果前：
- `docs/research/two_wave_path_metric_resolution_response_preanalysis_v069.md`
- `docs/research/two_wave_path_metric_resolution_response_protocol_v069.md`

正式结果：
- `docs/research/two_wave_path_metric_resolution_response_results_v069.md`
- `cloud_results/cloud_chat_v069_path_metric_resolution_response/summary.json`
- `cloud_results/cloud_chat_v069_path_metric_resolution_response/per_view_response.json`
- `cloud_results/cloud_chat_v069_path_metric_resolution_response/threshold_crossings.json`
- `cloud_results/cloud_chat_v069_path_metric_resolution_response/identity_reason_transitions.json`
- `cloud_results/cloud_chat_v069_path_metric_resolution_response/duration_overlay.json`
- `cloud_results/cloud_chat_v069_path_metric_resolution_response/strict_pair_overlays.json`
- `cloud_results/cloud_chat_v069_path_metric_resolution_response/data_identity.json`
- `cloud_results/cloud_chat_v069_path_metric_resolution_response/execution_receipt.json`

Helper blob `f7ee5dec71b2055c762f9be08fc22171b2a8b2c6`；synthetic tests 7/7 PASS；500 个真实 published identities native-path exact-equivalence 500/500 PASS。

Hard controls：184,276 published identities；737,104 legs；736,826 aligned nested legs；278 non-aligned；close mismatch 0；TV theorem violation 0；efficiency theorem violation 0；29,453 strict pairs；482 both-qualified；699 qualification disagreements；80 target repaired / 24 disagreement。

5m→1m aggregate：TV1/TV5 median 1.4123；E1-E5 median -0.2063；J1-J5 median -0.2505。

Frozen 0.5 仅作诊断标签：efficiency leg pass→fail 214,380/737,104=29.08%；identity inefficient pass→fail 97,027/184,276=52.65%；jump leg fail→pass 258,735/737,104=35.10%；identity jump fail→pass 126,196/184,276=68.48%；flat-share 基本稳定。Duration vs jump response Spearman rho=0.8838。

正式裁决：`metrics_have_opposed_resolution_semantics_requiring_property_redefinition`。

执行层曾把 aggregate 24 个 target disagreements 错误分摊成 9/6/4/5；hard gate 在 interpretation 前拦截。读取 v0.6.7 正式 evidence 后恢复真实 10/7/3/4=24。Frozen protocol 未冻结错误逐-offset 数字，research math 未变。

## 下一 formal research step

只允许另开 **path-property redefinition preanalysis**：研究 efficiency/jump 是否为同一 underlying path irregularity 的不同 resolution 投影，是否存在 multi-resolution / scale-normalized / threshold-free descriptor，以及 native-5m runtime 如何获得明确协变或误差界的 property。任何 replacement 必须先证明 prefix causality、harmless-slicer invariance 与 synthetic counterexamples，再讨论 threshold。

Duration-geometry 保持独立 secondary workstream。不得拟合新 path thresholds、不得把 1m 直接 promoted 为 production input、不得修改 matcher/projection/publication、不得回 direction/outcome/trading。
