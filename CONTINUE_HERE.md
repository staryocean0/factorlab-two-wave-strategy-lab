# 两浪研究继续入口：v0.6.12 native concentration proxy audit 已闭合（2026-09-07）

当前全局状态：`morphology_replication_not_yet_accepted`；操作基线仍为 **v0.4.3**；PR #1 保持 Draft。Direction/D1/D2/PAWCT、H1/H2、第三浪、收益/P&L、fresh OOS、paper trading、production 全部继续冻结。

## 已闭合关键链条

- v0.6.0–v0.6.5：financial identity 解耦、projection repair、first-valid append-only publication；
- v0.6.6–v0.6.9：qualification instability 主要来自 path sampling / resolution semantics；
- v0.6.10：fine concentration / origin ensemble 显著降低 jump bar-origin aliasing；fine roughness endpoint-sensitive；
- v0.6.11：固定 25-cell inward erosion roughness ensemble materially reduces endpoint sensitivity；
- v0.6.12：native true-range concentration 有局部改善，但**不能可靠代理 fine concentration / origin uncertainty**。

## v0.6.12 正式证据

结果前：

- `docs/research/two_wave_concentration_deployable_proxy_preanalysis_v0612.md`
- `docs/research/two_wave_concentration_deployable_proxy_protocol_v0612.md`

正式结果：

- `docs/research/two_wave_concentration_deployable_proxy_results_v0612.md`
- `cloud_results/cloud_chat_v0612_concentration_deployable_proxy/summary.json`
- `per_view_proxy.json`
- `oracle_error.json`
- `cross_slicer_proxy.json`
- `empirical_bracket.json`
- `aliasing_uncertainty.json`
- `duration_overlay.json`
- `strata_overlays.json`
- `data_identity.json`
- `execution_receipt.json`

Helper blob `49903c1e14fc2ea3a5458dfdcce1dd90cfa13843`；test blob `2e2d78e3e4c424420e2e7c39381af5d920191512`；synthetic tests **9/9 PASS**。

Hard controls：

```text
publications = 38,176 / 36,737 / 36,619 / 36,480 / 36,264
published raw strict = 8,381 / 5,770 / 6,204 / 9,098 = 29,453
qualification matrix = 482 / 28,272 / 352 / 347
target repaired = 80 = 56 agreement + 24 disagreement
oracle-comparable pair-leg universe = 117,805
```

## v0.6.12 result

Primary registered runtime proxy：

```text
J_TR = max(native true range) / sum(native true range)
```

它比 close-only J5 有部分改善：

```text
cross-slicer median abs diff
J_close 0.053933
J_TR    0.039807

|proxy-J1| median
J_close 0.258232
J_TR    0.215079
```

但不能 promotion：

- fixed native bracket 对 fine J1 coverage 只有 **4.51%**；J1 几乎总在 native concentration bracket 下方；
- 对 origin-jump median，J_TR paired side-leg 更优 / 相同 / 更差 = `103,693 / 20,298 / 111,626`，没有稳定胜过 Jclose；
- `proxy_spread` vs actual `origin_jump_range` Spearman 仅 **0.075**；
- `|J_TR-J1|` median 随 native step count 强烈变化：`0.399 / 0.238 / 0.155 / 0.090 / 0.041`（1-3 / 4-5 / 6-11 / 12-23 / 24+ bars）。

正式裁决：

> **`native_ohlc_proxies_do_not_reliably_track_fine_concentration`**

含义：问题不是缺一个更聪明的 native OHLC scalar，而是 max-share concentration 本身受到 number-of-increments / resolution 强烈调制。v0.6.12 不 promoted J_TR，也不拟合 duration correction。

## 下一 formal research step

只允许结果前开启 **step-count / resolution-normalized concentration property preanalysis**。

下一版应研究 concentration weight distribution 本身，而不是继续拟合 OHLC→J1。可以事前注册一个固定、无权重选择的 concentration profile，显式包含 step count，例如 normalized max-share、normalized Shannon concentration、effective-step concentration，并分别在 native close / native true-range / supplied-1m close movement weights 上审计 resolution semantics 和 cross-slicer stability。

下一轮仍必须：

- 不拟合 duration correction 或 qualification threshold；
- 不从多个 descriptor 中事后挑 winner；
- 不把 supplied 1m 直接设为 production input；
- roughness erosion candidate 保持冻结，不混合优化；
- 不改 matcher / projection / publication；
- 不使用 direction / outcome / P&L；
- 不进入第三浪、fresh OOS、paper trading 或 production。
