# 两浪研究继续入口：v0.6.9 path-metric resolution response 已闭合（2026-09-06）

## 当前安全状态

冻结上游仍为：

> **v0.5.2 TCSS exact-ridge parent identity + v0.5.4 full-cycle-scale qualification**

操作基线仍为 **v0.4.3**。全局状态仍为：

`morphology_replication_not_yet_accepted`

PR #1 保持 Draft，不合并 main。Direction/D1/D2/PAWCT、H1/H2、第三浪、收益/P&L、fresh OOS、paper trading、production 全部继续冻结。

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
- v0.6.9：path-metric resolution-response audit = **efficiency 与 jump 具有相反的 resolution semantics，必须先重定义 underlying path property**。

## v0.6.9 已正式闭合

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

Helper blob：`f7ee5dec71b2055c762f9be08fc22171b2a8b2c6`。Synthetic tests：**7/7 PASS**。500 个真实 published identities native-path exact-equivalence：**500/500 PASS**。

### Hard controls / theorem checks

```text
published identities = 184,276
leg observations     = 737,104
aligned nested legs  = 736,826
non-aligned legs     = 278 (0.0377%)
common close mismatch = 0
TV refinement theorem violations = 0
Efficiency non-increase violations = 0
strict pairs = 29,453
both-qualified control = 482
qualification disagreements = 699
target repaired = 80, target disagreement = 24
```

执行层曾错误把 aggregate 24 个 target-disagreement 分摊成 `9/6/4/5`；hard gate 在 interpretation 前拦截。重新读取 v0.6.7 正式 evidence 后恢复真实 `10/7/3/4 = 24`。Frozen v0.6.9 protocol 从未冻结错误逐-offset 数字，因此只修 runtime bookkeeping，research math 未变。

## v0.6.9 resolution response

5m → supplied 1m aggregate：

```text
TV1/TV5 median   = 1.4123
E1-E5 median     = -0.2063
J1-J5 median     = -0.2505
```

Frozen 0.5 threshold 仅作诊断标签时：

```text
Efficiency leg pass->fail = 214,380 / 737,104 = 29.08%
Identity inefficient pass->fail = 97,027 / 184,276 = 52.65%
Jump leg fail->pass = 258,735 / 737,104 = 35.10%
Identity jump fail->pass = 126,196 / 184,276 = 68.48%
```

Flat-share 基本稳定。

Duration vs jump response Spearman `rho = 0.8838`，说明 jump resolution response 强烈受 leg duration 调制，进一步否定简单全局 threshold 平移。

## 正式裁决

`metrics_have_opposed_resolution_semantics_requiring_property_redefinition`

解释：

1. observed TV 随 refinement 系统性增加；
2. efficiency 在相同 endpoints 下必然下降/不升；
3. jump share 在真实数据里大幅下降，但幅度强烈受 duration 调制且不存在同类 monotonic theorem；
4. 因此 `efficiency >= 0.5` 与 `jump_share <= 0.5` 是 resolution-specific measurement + threshold，而不是 resolution-invariant morphology truths；
5. 不允许用新的全局 threshold remap 解决本轮问题。

## 下一 formal research step

只允许另开 **path-property redefinition preanalysis**。

必须先回答：

1. efficiency 与 jump_share 是否是同一 underlying path irregularity 的不同 resolution 投影；
2. 是否存在基于 multi-resolution response curve 的 threshold-free / scale-normalized descriptor；
3. 若 runtime 只允许 native 5m，能否构造对 bar-origin 平移稳定、对 resolution 明确协变/可校正的 property；
4. replacement property 必须先证明 prefix causality、harmless-slicer invariance 和 synthetic counterexamples，再讨论 threshold；
5. duration-geometry 保持独立 secondary workstream，不得混入 path-property repair。

禁止：根据 v0.6.9 拟合新的 efficiency/jump thresholds；不得直接把 1m path promoted 为 production morphology input；不得修改 matcher / projection / publication；不得回 D1/D2/PAWCT；不得使用收益/outcome；不得进入第三浪或交易层。

**当前下一步只允许 path-property redefinition preanalysis；不得直接改 qualification threshold。**
