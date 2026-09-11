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
- qualification policy: **v0.6.18 path-gate demotion** — current best research qualification component;
- fine-path partial-identification measurement: **v0.6.17** cloud-reviewed bounds;
- parent direction (`Range / UpTrend / DownTrend`): **winner unset / not accepted**;
- strongest pooled-exact Development direction contribution: **v0.6.25**, retained as evidence but not runtime authority.

v0.6.18 formally demotes only `inefficient_leg` and `jump_dominated_leg` from hard morphology vetoes to diagnostics. On the frozen v0.6.5 strict same-event universe, aggregate positive qualification overlap improved from **40.8129% to 68.3817%**, and both-qualified pairs increased from **482 to 1,462**, with all four harmless 5m offsets improving. This is a qualification-policy pass, **not morphology acceptance and not authorization to promote D1/D2/PAWCT as the final state classifier**.

The current OHLC market-bar direction-information expansion is closed after v0.6.46: native high/low and native open/body/gap were formally adjudicated and did not authorize a new challenger.

v0.6.47 then performed a frozen post-2020 temporal replication of the existing v0.6.18 + D1/v0.6.25 chain. The 1m-to-five-offset constructor first reproduced all shipped 2015-2020 Development 5m products exactly, and also reproduced the independent external 2024/2025 native offset-0 controls exactly. The formal replication verdict was **`v0647_temporal_replication_under_original_v0625_gate_not_all_pass`**. Across `253` post-2020 both-qualified within-year pairs, D1 exact was `242/253 = 95.6522%`, versus v0.6.25 `238/253 = 94.0711%`; v0.6.25 raised decisive coverage from `47.6285%` to `68.5771%`, but failed harmless-offset and pooled exact non-regression.

v0.6.48 has now executed the next authorized stage. A cross-repository audit found no existing independent human/external Two-Wave reference-label dataset, so the project froze and generated a **prediction-blinded 240-case reference annotation packet** rather than treating model outputs as truth. The packet is balanced across 2015-2020 with 120 hidden candidate and 120 hidden control cases; each annotator sees only an anonymous 96-bar neutral chart, the semantic instructions, and a blank label sheet. Candidate/control stratum, dates/years, model pivots, v0.6.18 qualification, D1/v0.6.25 predictions, harmless offsets, future bars and downstream outcomes are withheld.

The hidden case mapping is committed only by SHA-256. `SCORING_BLOCKED.json` keeps model/reference scoring disabled until **two independent first-pass annotation sheets** are returned and hashed, the frozen inter-annotator quality gates are run, disagreement cases are independently adjudicated, and the final reference labels are frozen. A validator for this first-pass quality stage is already implemented and covered by tests.

Therefore v0.6.18 remains qualification champion, v0.6.25 remains a retained Development direction contribution, and the parent-direction winner remains unset. Current global stage is **`independent_reference_label_packet_ready_awaiting_blinded_annotations`**. `morphology_acceptance=false`, `trade_authority=false`, `production_authority=false`.

Machine-readable authority: [`experiments/two_wave_m0_authority.json`](experiments/two_wave_m0_authority.json).

The next authorized action is to obtain the two independent blinded v0.6.48 annotation sheets and run the already-frozen agreement gates. This is an external labeling dependency, not authorization to resume OHLC/clock/session/data-quality feature mining or tune v0.6.18/v0.6.25 against labels. Even a successful v0.6.48 Development-period calibration does not by itself grant global morphology acceptance; a separately frozen fresh held-out reference-label validation would still be required.

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
