# 两浪研究继续入口：v0.6.14 native multiscale concentration audit 已闭合（2026-09-07）

当前全局状态：`morphology_replication_not_yet_accepted`；操作基线仍为 **v0.4.3**；PR #1 保持 Draft。Direction/D1/D2/PAWCT、第三浪、收益/P&L、fresh OOS、paper trading、production 全部继续冻结。

## v0.6.14

正式裁决：`native_multiscale_response_is_stable_but_not_informative_of_fine_refinement`。

结果前：
- `docs/research/two_wave_native_multiscale_concentration_preanalysis_v0614.md`
- `docs/research/two_wave_native_multiscale_concentration_protocol_v0614.md`

正式结果：
- `docs/research/two_wave_native_multiscale_concentration_results_v0614.md`
- `cloud_results/cloud_chat_v0614_native_multiscale_concentration/` 下 8 个 protocol-required compact files

Helper blob `cf3274a765e9b577841fe7fc468ca9d2aa8c7e8d`；test blob `880a77dfa13c790917536c956c5b3ae5faea33b0`；synthetic tests **8/8 PASS**。

Hard controls：publications `38,176 / 36,737 / 36,619 / 36,480 / 36,264`；published raw strict pairs `29,453`；both-qualified `482`；qualification disagreements `699`；target repaired `80=56+24`；v0.6.13 profile availability native/fine/both `664,001 / 737,070 / 663,972`。

Registered native response 对每条 leg 固定 stride `1/2/3/4`、枚举所有 phase、保留 endpoints，输出 `C_inf/C_1/C_2` 的 `delta_2/3/4` 与 `range_2/3/4`。没有 best stride/phase selection。

这套 response 的 cross-slicer median 确实普遍低于 native profile scalar；例如 C1 delta/range median约 `0.066–0.086`，低于 native C1 profile `0.0922`。

但它不追踪真实 hidden refinement：`abs(delta_s)` vs native→fine profile gap Spearman 大多为 `-0.20…-0.06`；phase-range vs supplied-1m origin-range 同样弱/负。相反 response 与 native step count Spearman 常见 `0.25…0.60`。关键 target strata 也没有出现一致正向 tracking。

因此进一步 coarsening 已经 coarse 的 close path，虽然能产生稳定 native descriptor，却不能恢复 bar 内已经丢失的 fine-refinement information。

## 下一 formal research step

只允许 results-blind **fine-concentration identifiability / structural-bounds audit under the native 5m information set**。

下一版不再注册新的 point-estimate proxy。应利用 native 5m OHLC + 已知 5m→1m minute-count semantics，构造对 hidden 1m movement concentration / normalized concentration profile 的 deterministic outer bounds，并用 supplied 1m 只检查 coverage 与 tightness。

若保证型 bounds 普遍很宽，应正式裁决 native 5m information set 下该 property 不可充分识别，并转向明确 production finer-data requirement，而不是继续拟合 proxy。

继续禁止：duration correction / qualification threshold 拟合；修改 matcher/projection/publication；roughness re-optimization；direction/outcome/P&L；第三浪、fresh OOS、paper trading、production。
