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

v0.6.52 completed the frozen ordinal-0 predecessor / first-valid publication lineage audit without using the human reference labels in its primary decision. The structural p0 provenance asymmetry is real, but it is not materially expressed: all `2,115` v0.6.18-qualified identities have exactly one evidence member and one valid member, with zero prior-invalid selection, zero later-valid alternatives, and zero suppressed rewrites; median raw-vs-filtered displacement is `3` bars at every ordinal. The formal verdict is **`v0652_structural_ordinal0_provenance_asymmetry_not_materially_expressed`**.

v0.7.0 localized the first large semantic loss to exact-consecutive five-ridge objectization: common-scale ridge support was `10/11`, while the legacy exact tuple supported only `3/11`. This preserves the causal ridge infrastructure but demotes the exact tuple from semantic-parent authority. Downstream v0.6.x components remain retained for transplantation retests rather than blanket rejection.

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


v0.7.1 has now reconstructed a ridge-supported semantic-parent candidate without fitting label-distance or persistence thresholds. F3 — the **persistence-dominant nonconsecutive quintet** — supports `8/11` anchored human-positive cases, versus legacy F0 `3/11`, F2 `5/11`, and the non-identifying F1 upper bound `10/11`. F3 is Development evidence only and is not morphology authority. The next authorized stage is **causal F3 event/publication + downstream transplantation precheck**: first freeze first-known/immutable F3 object semantics, then test whether historical raw projection/publication, qualification, and direction results can be transplanted sequentially. `morphology_acceptance=false`, `trade_authority=false`, `production_authority=false`.


v0.7.2 then tested whether F3 can be converted into a permanently causal immutable event while preserving the frozen Development semantics. Static F3 support reproduced `8/11`, but the explicit skipped-ridge death/survivor certificate preserved only `7/11`, so the formal verdict is **`v0702_f3_static_objectization_not_causally_publishable`**. This is a one-case event-certification gap, not a rejection of the F3 static reconstruction. The transplanted sequential raw-projection / first-valid immutable-publication principles produced `9/11` published-raw semantic support, so those historical principles remain promising but blocked behind the causal-event gate. The next authorized stage is a read-only causal-certification gap attribution. Qualification and direction components remain retained for later transplantation retests rather than blanket rejection.


v0.7.3 localized the remaining F3 event gap. The frozen static reconstruction still supports `8/11`; v0.7.2 C0 reproduces `7/11`; and the preregistered C1 boundary-survival relaxation also remains `7/11`, recovering no case. In the single gap case, all four human-compatible static F3 realizations lack explicit skipped-ridge death evidence at cutoff, and read-only full-lineage attribution shows the proof arrives only later. The formal verdict is **`v0703_gap_requires_explicit_death_evidence_unavailable_at_cutoff`**. The next stage therefore reconstructs the causal object/event layer rather than weakening the permanence certificate, with append-only lifecycle semantics (`observed -> certified/invalidated`) as the leading design. Qualification and direction calibration remain blocked.


v0.7.4 resolves the v0.7.3 causal-event deadlock by separating first observation from terminal permanence. The prefix-causal append-only lifecycle keeps frozen F3 live support at `8/11` while C1 certification remains `7/11`; the single certificate-gap case stays live unresolved instead of using future death evidence. All hard lifecycle invariants pass with zero violations. Across the 11 frozen windows, 1543 objects are observed and 1478 certify; no dormant/reobserved transitions occur. Formal verdict: **`v0704_f3_prefix_causal_lifecycle_representation_supported`**. The next stage is lifecycle-aware provisional raw projection / immutable publication; qualification and direction remain blocked.
