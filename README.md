# FactorLab Two-Wave Layer 3 Research Theme

## Current bucket authority: causal structure/state recognition

This repository is the current FactorLab bucket for **causally deciding whether the present parent K-line structure is range-bound, an uptrend, or a downtrend**.

The canonical primary research object remains `two_wave_parent_structure_recognizer`:

1. causally identify completed same-scale waves;
2. pair two complete waves at the same scale;
3. classify their parent structure as **Range / UpTrend / DownTrend / Uncertain**;
4. preserve event time, confirmation time, classification time and replay stability;
5. do not use trading P&L as a substitute for morphology/state-recognition acceptance.

Start with:

- [`docs/INDEX.md`](docs/INDEX.md)
- [`docs/research/TWO_WAVE_M0_AUTHORITY.md`](docs/research/TWO_WAVE_M0_AUTHORITY.md)
- [`docs/user/two_wave_strategy_handoff_prompt.md`](docs/user/two_wave_strategy_handoff_prompt.md)
- [`docs/user/cloud_execution_prompt.md`](docs/user/cloud_execution_prompt.md)

## Current M0 scientific status

The full recognizer is **not yet independently morphology-accepted**. Historical full-recognizer operational baseline remains `v0.4.3`; component-level advances do not silently replace that full baseline.

Current best-supported research components are:

- parent identity: **v0.5.2 exact-ridge identity**;
- same-scale semantics: **v0.5.4 full-cycle qualification**;
- immutable raw identity publication: **v0.6.5**;
- qualification policy: **v0.6.18 path-gate demotion** — Development-era champion, but failed independent reference calibration;
- fine-path partial-identification measurement: **v0.6.17** cloud-reviewed bounds;
- parent direction (`Range / UpTrend / DownTrend`): **winner unset / not accepted**;
- strongest pooled-exact Development direction contribution: **v0.6.25**, retained as evidence but not runtime authority.

v0.6.18 formally demotes only `inefficient_leg` and `jump_dominated_leg` from hard morphology vetoes to diagnostics. On the frozen v0.6.5 strict same-event universe, aggregate positive qualification overlap improved from **40.8129% to 68.3817%**, and both-qualified pairs increased from **482 to 1,462**, with all four harmless 5m offsets improving. This is a qualification-policy pass, **not morphology acceptance and not authorization to promote D1/D2/PAWCT as the final state classifier**.

The current OHLC market-bar direction-information expansion is closed after v0.6.46: native high/low and native open/body/gap were formally adjudicated and did not authorize a new challenger.

v0.6.47 then performed a frozen post-2020 temporal replication of the existing v0.6.18 + D1/v0.6.25 chain. The 1m-to-five-offset constructor first reproduced all shipped 2015-2020 Development 5m products exactly, and also reproduced the independent external 2024/2025 native offset-0 controls exactly. The formal replication verdict was **`v0647_temporal_replication_under_original_v0625_gate_not_all_pass`**. Across `253` post-2020 both-qualified within-year pairs, D1 exact was `242/253 = 95.6522%`, versus v0.6.25 `238/253 = 94.0711%`; v0.6.25 raised decisive coverage from `47.6285%` to `68.5771%`, but failed harmless-offset and pooled exact non-regression.

v0.6.48 completed the independently blinded reference-label calibration. The annotation layer passed its frozen agreement gates and all 16 first-pass disagreements were independently adjudicated, but the recognizer calibration failed decisively: only `16/120 = 13.33%` of hidden v0.6.18 candidate cases were independently confirmed as complete same-scale two-wave parents, and v0.6.25 parent-state exact agreement on those 16 confirmed candidates was only `5/16 = 31.25%`. The formal verdict is **`v0648_independent_reference_calibration_gates_not_all_pass`**. Therefore v0.6.18 remains only the Development-era qualification champion; independently reference-calibrated qualification authority is **none**.

v0.6.49 then executed the frozen read-only reference-conditioned failure attribution over the same 120 candidates. No predeclared existing diagnostic family — publication maturity, fragment/parent scale, duration/amplitude imbalance, path noise, or identity ambiguity — met the frozen strong-support rule. `amplitude_unit_fraction` produced an isolated adjusted rank of `0.75`, but its family-level corroboration failed, so no amplitude cutoff or qualification gate is authorized. The formal verdict is **`v0649_diffuse_or_fundamental_semantic_object_mismatch`**.

v0.6.50 completed that semantic-object / parent-representation audit. All 120 candidate algorithmic parents were fully visible in the frozen human chart, and right-edge staleness was absent. Among the 11 reference-positive cases with complete human p0-p4 anchors, the outer parent intervals overlap reasonably well (median IoU `0.7742`) but the full five-anchor alignment remains only mixed (normalized anchor MAE `0.1242`); the start boundary differs by a median `17` bars while the end boundary differs by only `4` bars. The formal verdict is **`v0650_parent_representation_correspondence_not_identified`**.

v0.6.51 completed the frozen left-boundary / internal-pivot decomposition. On the 11 human-positive anchored cases, p0/p4 median absolute errors are `17`/`4` bars and start error dominates in `9/11`; per-case translation removal reduces median five-anchor MAE from `11.8` to `3.8` bars. Yet the start/end offset disagreement median is `12` bars, so pure rigid translation is rejected. Boundary-normalized internal phase MAE is `0.08397`: below the internal-mismatch band but narrowly above the preregistered `0.08` correspondence/left-boundary band. The formal verdict is **`v0651_correspondence_decomposition_mixed_or_unresolved`**.

Current global stage is therefore **ordinal-0 predecessor-support / first-valid-publication lineage audit required**. The start side is the strongest descriptive clue, but no start-boundary tolerance, translation correction, pivot remapping, semantic-object challenger, qualification change, or direction challenger is authorized. `morphology_acceptance=false`, `trade_authority=false`, `production_authority=false`.

## Four-layer timing navigation shell

The retained infrastructure inventory is `docs/ops/timing_infrastructure_four_layer_inventory@1.0.json`.
Its navigation semantics remain: **数据时钟 → K线测量 → 状态/机会研究 → 执行标的**.
This shell is compatibility/navigation infrastructure only; it does not change the Two-Wave bucket's current scientific authority.

## Migrated supporting evidence

A separate causal K-line state-recognizer lineage (`v1`-`v13`) was mistakenly developed in `factorlab-trend-reversion-regime-lab`. Its key authority, contribution ledger and decisive result cards are preserved under:

`docs/archive/migrated_kline_state_recognizer_from_trend_reversion_20260909/`

That migrated package is **supporting/comparison evidence only**. Its historical `v10 temporal blend` champion is not automatically the Two-Wave champion because it does not implement the required two-complete-wave morphology contract. Any reuse must be integrated and revalidated against the Two-Wave acceptance semantics.

## Explicit bucket boundary

This repository does **not** own:

- concrete reversal/mean-reversion strategy payoff research such as R1/R2 — that belongs to `factorlab-trend-reversion-regime-lab`;
- STAR50/CSI1000 bottom-layer volatility/risk-state switching such as Unsafe/Recovering/HighVol — that belongs to `factorlab-star50-filter-lab`;
- Layer 4 live execution or production trading.

The package still contains imported Layer 1/2/3 infrastructure closure required by the bounded cloud theme; those dependencies are not separate active strategy mandates.

`production_authority=false`.
