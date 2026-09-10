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
- parent direction (`Range / UpTrend / DownTrend`): **still blocked / not accepted**.

v0.6.18 formally demotes only `inefficient_leg` and `jump_dominated_leg` from hard morphology vetoes to diagnostics. On the frozen v0.6.5 strict same-event universe, aggregate positive qualification overlap improved from **40.8129% to 68.3817%**, and both-qualified pairs increased from **482 to 1,462**, with all four harmless 5m offsets improving. This is a qualification-policy pass, **not morphology acceptance**.

Machine-readable authority: [`experiments/two_wave_m0_authority.json`](experiments/two_wave_m0_authority.json).

Next authorized research is a results-blind decomposition of remaining **duration-geometry** qualification disagreements. Direction/state formula changes remain frozen until morphology identity/qualification stability is adequate.

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
