# Two-Wave M0 Authority

Date: 2026-09-11

## Global scientific status

- Primary object: `two_wave_parent_structure_recognizer`.
- Target semantics: two complete same-scale waves -> parent `Range / UpTrend / DownTrend / Uncertain`.
- Independent morphology acceptance: **false**.
- Global status: `morphology_replication_not_yet_accepted`.
- Historical full-recognizer operational baseline: **v0.4.3**.
- Trade authority: **false**.
- Production authority: **false**.

A component-level win never silently upgrades the whole recognizer. Failed challengers never erase the best existing component. Rejected versions may contribute reusable measurements or decision mechanisms.

## Current best-supported component stack

| Layer | Current best-supported component | Status |
|---|---|---|
| causal pivot / historical full recognizer | v0.4.3 temporal maturity recognizer | historical baseline; not morphology-accepted |
| parent identity | v0.5.2 exact-ridge parent identity | supported research component |
| same-scale semantics | v0.5.4 full-cycle-scale qualification | supported research component |
| raw identity publication | v0.6.5 first-valid immutable predecessor | supported research component |
| qualification policy | **v0.6.18 path-gate demotion** | **current best qualification component** |
| fine-path information measurement | v0.6.17 session-aware bounds | supported measurement capability |
| parent direction/state classification | **no winner yet** | active research layer |

## Qualification authority: v0.6.18

Formal run `34423674192`, result commit `9600eca94de9fb2cc39db4b995edec3d5e7870c3`.

It reproduced the frozen 57,029 filtered matched pairs and 29,453 published raw strict pairs. Demoting only `inefficient_leg` and `jump_dominated_leg` from hard morphology vetoes to diagnostics improved aggregate positive qualification overlap from `40.8129%` to `68.3817%` and both-qualified pairs from `482` to `1,462`, with all four offsets improving. Long-span and other safety gates remained hard.

v0.6.19 attributed 58.14% of the remaining 676 qualification disagreements to local-duration geometry. v0.6.20 proved that direct exact-3/exact-11 admission is not a valid repair, so v0.6.18 remains unchanged.

## Direction baseline and current best contribution

On the frozen 1,462 strict same-financial-identity pairs where both views are v0.6.18-qualified, historical D1 gives:

- exact four-state agreement `95.7592%`;
- pooled decisive coverage `48.9056%`;
- decisive agreement `100%`;
- opposite UpTrend/DownTrend conflicts `0`.

D1 is a stability baseline, not human morphology truth. Its main defect is over-abstention, especially on Range.

The strongest pooled-exact direction contribution remains **v0.6.25 absolute-margin erosion-consensus rescue**:

- exact `95.8960%` (`1,402/1,462`), above D1;
- decisive coverage `70.8618%`;
- decisive agreement `100%`;
- opposite-trend conflicts `0`;
- but Range share only `1.0618%` and offsets 1/2 regressed.

Therefore v0.6.25 is not a direction winner, but it remains the comparison base for subsequent Range-recovery work.

## Direction contribution lineage

### v0.6.21-v0.6.23: whole-window signal and stabilization

- v0.6.21 whole-window Huber: exact `95.0068%`, coverage `84.2339%`, decisive agreement `100%`, conflicts `0`; rejected wholesale but proved full-parent-window information is useful.
- v0.6.22 D1-primary Huber rescue: coverage `85.8413%`, exact `94.7332%`; proved D1-primary rescue is viable but raw rescue is too sensitive.
- v0.6.23 endpoint-erosion unanimity: exact `95.5540%`, coverage `78.5568%`, decisive agreement `100%`; recovered most stability but still failed all-offset non-regression.

### v0.6.24-v0.6.28: rescue-boundary attribution

- v0.6.24 showed v0.6.23 harm is entirely one-sided rescue from D1-both-uncertain pairs.
- v0.6.25 added a frozen absolute consensus margin `>=0.10`, creating the strongest pooled-exact contribution but nearly eliminating Range.
- v0.6.26 proved the common absolute margin is state-asymmetric.
- v0.6.27 used Range margin `0.03`; class diversity returned, but exact fell to `94.9384%`.
- v0.6.28 found no valid support-dispersion threshold authorization.

### v0.6.29-v0.6.32: direct Range evidence

- v0.6.29 cycle-IQR overlap `>=0.50`: exact `95.4172%`, coverage `75.0684%`, Range share `6.6059%`; useful Range evidence but too permissive alone.
- v0.6.30 intersected frozen Range margin and band overlap: exact `95.0068%`, coverage `73.4952%`; intersection reduced supply but did not preferentially remove one-sided instability.
- v0.6.31 mutual-median containment: exact `94.6648%`, coverage `72.9138%`; additional Range-like evidence but still sampling-sensitive.
- v0.6.32 showed containment slack does not separate harmful from repaired one-sided rescues; no slack tuning is authorized.

### v0.6.33 two-cycle median-shift Range

Formal result commit `6dca8441c59f7fb095c54ae24cf9a555c415d757`.

Using the two complete cycles' median-close location shift with the inherited `0.15` amplitude-unit tolerance on all four frozen endpoint supports:

- new Range rescues: `1,119`;
- exact `95.8960% -> 91.8605%`;
- decisive coverage `70.8618% -> 81.9083%`;
- Range decisive share `1.0618% -> 14.41%`;
- decisive agreement fell below the 99.5% gate;
- all four offsets regressed.

Retained contribution: direct two-cycle robust location shift is a strong Range-supply signal, but median location alone is far too permissive.

### v0.6.34 two-cycle distribution intersection

Formal workflow run `34599957160`.

This intersected, on each of the same four supports, the already-frozen v0.6.33 median-shift condition (`<=0.15`) with the already-frozen v0.6.29 cycle-IQR-overlap condition (`>=0.50`). No threshold was tuned.

Results:

- new Range rescues: `1,077`;
- exact `95.8960% -> 91.9289%`;
- decisive coverage `70.8618% -> 81.4979%`;
- decisive agreement `99.21%`;
- Range decisive share `13.97%`;
- per-offset exact deltas: `-3.00 / -2.79 / -5.96 / -4.23 pp`;
- D1/v0.6.25 decisive overrides `0`;
- opposite UpTrend/DownTrend conflicts `0`.

Formal verdict: `v0634_two_cycle_distribution_intersection_direction_rejected`.

Retained contribution: median location shift and central-IQR overlap are largely redundant at their frozen thresholds. Their intersection removes only a small fraction of v0.6.33 rescues and does not repair cross-slicing instability. Do not tune `0.15` or `0.50`, and do not keep stacking nearby gates.

### v0.6.35-v0.6.36: complete-distribution W1 and threshold attribution

v0.6.35 replaced median/IQR gate stacking with one complete-cycle empirical Wasserstein-1 distance, normalized by the frozen parent amplitude, while retaining the same `0.15` ceiling and requiring all four endpoint-erosion supports. Formal result commit `1ba5073373ac9ee925311a8de4d16bff2a1432dc`.

Results:

- new Range rescues: `725`;
- exact `95.8960% -> 93.2285%` (`1,363/1,462`);
- decisive coverage `70.8618% -> 77.3769%`;
- decisive agreement `99.7352%` (`1,130/1,133`);
- Range decisive share `12.0918%`;
- pair-change topology: `93 both / 26 main-only / 24 other-only / 1,319 none`;
- decisive overrides `0`; opposite-trend conflicts `0`.

Retained contribution: full-distribution distance is materially more selective than v0.6.33/v0.6.34 but still creates too many one-sided `Uncertain -> Range` changes and does not beat v0.6.25.

v0.6.36 then preregistered a read-only residual attribution; formal result commit `4a2b2eb066326fc195128b56850130e20537907c`. Among the `50` one-sided v0.6.35 changes, `43` introduced new non-exact pairs, `4` repaired old non-exact pairs and `3` remained non-exact. Although `40/43` harmful cases lay within `0.03` of the `0.15` W1 boundary, only four repairs existed, below the preregistered minimum support of twenty. Therefore nearby W1-threshold tuning, including `0.15 -> 0.12`, is not authorized.

### v0.6.37 phase-balanced W1 — rejected, measurement contribution retained

Protocol was frozen before implementation at `390e9f502ccbeebd1067c1fc2a248b5e1ddd8bff`. Formal workflow run `34602526496`; formal result commit `434b52aca4b84c84ec5ce46f0d561e7cbdefa187`.

The only measurement change was within-cycle probability weighting: each complete cycle's first leg carries exactly `50%` probability mass and its second leg carries exactly `50%`, irrespective of bar count. The `0.15` W1 ceiling, four endpoint supports, v0.6.25 preservation rule and promotion gates were unchanged.

Results:

- new Range rescues: `621`;
- exact `95.8960% -> 93.7073%` (`1,370/1,462`);
- decisive coverage `70.8618% -> 76.5390%`;
- decisive agreement `100%`;
- Range decisive share `8.4004%`;
- topology: `61 both / 23 main-only / 21 other-only / 1,357 none`;
- all four offset exact-agreement rates regressed versus v0.6.25;
- decisive overrides `0`; opposite-trend conflicts `0`.

Formal verdict: `v0637_phase_balanced_wasserstein_range_direction_rejected`.

Retained contribution: removing duration-proportional sampling weight repairs part of v0.6.35's instability and restores decisive agreement to 100%, but the Range rescue remains systematically too broad.

### v0.6.38 phase-balance residual attribution — diagnostic complete

Protocol was frozen before replay. Formal workflow run `34603190318`; formal result commit `3e2dc902cb29985bbb9b31e2b6232b3ba3041b76`.

Relative to v0.6.35, phase balancing produced:

- `31` previously non-exact pairs repaired;
- `24` previously exact pairs harmed;
- net exact improvement `+7` pairs;
- `1,339` pairs exact under both and `68` non-exact under both.

The remaining v0.6.37 one-sided changes versus v0.6.25 numbered `44`: `38` introduced harm and only `6` repaired old non-exact pairs. Of these, rescues shared by bar-equal v0.6.35 and phase-balanced v0.6.37 were `28 harm / 4 repair`; phase-balanced-only rescues were `10 harm / 2 repair`.

Formal interpretation: neither nearby W1 threshold tuning nor a simple `v0.6.35 AND v0.6.37` weighting-consensus/intersection rule is authorized. Both aggregate-distribution W1 variants supply useful Range evidence but remain one-sided-instability generators.

## Current direction research rule

The parent-direction winner remains **unset**. v0.6.25 remains the strongest pooled-exact contribution. v0.6.18 remains the qualification champion.

Rejected routes must not be silently retried: endpoint D2, confidence-gated endpoint D2, PAWCT as previously adjudicated, wholesale Huber replacement, unconditional Huber rescue, ungated erosion-consensus rescue, post-hoc retuning of v0.6.25 margin, v0.6.27 direct state-relative admission, fitted support-dispersion or containment-slack thresholds, v0.6.29 overlap used alone, v0.6.30/v0.6.31 gate stacking, v0.6.33 median shift alone, v0.6.34 median-shift/IQR intersection, nearby v0.6.35 W1-ceiling tuning, v0.6.37 phase-balanced W1 used directly, or a simple bar-equal/phase-balanced W1 consensus gate.

The historical PAWCT representation must also not be recreated under another name: it phase-aligns each leg to a fixed grid and measures the second complete cycle's absolute translated price path relative to the first. Scalar path-efficiency/jump/roughness descriptors from the v0.6.10-v0.6.18 qualification research likewise already exist and must not be presented as a novel direction signal.

## Next authorized step

Preregister one **read-only v0.6.39 order-sensitive residual-shape attribution**, not a recognizer challenger.

Its purpose is to test an unmeasured information class on the already-identified v0.6.37 one-sided residuals: after removing each leg's own endpoint level and total endpoint displacement, compare the **within-leg phase progress shape** of corresponding legs across the two complete cycles. This is deliberately distinct from:

- endpoint D2, which uses envelope endpoint translation;
- PAWCT, which measures absolute phase-aligned price translation between cycles;
- v0.6.10 scalar efficiency/jump/roughness descriptors;
- v0.6.33-v0.6.37 order-free location/distribution measurements.

The diagnostic must be threshold-free and may report only predeclared shape-distance descriptors and their distributions for `introduced_harm` versus `repaired_old_nonexact` residual classes. It must not modify classification, infer a gate, select a cutoff, use other offsets as runtime information, or use future returns/P&L/H1/H2/third-wave/2021+/2026 selection data. Any later recognizer candidate must be separately frozen before replay.

Independent morphology acceptance remains false. Trading and production remain closed.