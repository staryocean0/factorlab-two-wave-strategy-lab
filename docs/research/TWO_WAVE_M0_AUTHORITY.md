# Two-Wave M0 Authority

Date: 2026-09-10

## Global scientific status

- Primary object: `two_wave_parent_structure_recognizer`
- Target semantics: two complete same-scale waves -> parent `Range / UpTrend / DownTrend / Uncertain`
- Independent morphology acceptance: **false**
- Global status: `morphology_replication_not_yet_accepted`
- Historical full-recognizer operational baseline: **v0.4.3**
- Trade authority: **false**
- Production authority: **false**

A later component may be better supported without changing the full-recognizer baseline. Never overwrite the historical/full-recognizer baseline merely because one component passes its own frozen gate.

## Current best-supported component stack

| Layer | Current best-supported component | Status | Meaning |
|---|---|---|---|
| causal pivot / original full recognizer | v0.4.3 temporal maturity recognizer | historical operational baseline | still the last full recognizer baseline; not morphology-accepted |
| parent identity | v0.5.2 exact-ridge parent identity | supported research component | causally absorbs child-scale extrema and recovers parent five-anchor identity |
| same-scale qualification semantics | v0.5.4 full-cycle-scale qualification | supported research component | corresponding half-leg duration mismatch is diagnostic, not a hard same-scale veto |
| raw financial identity publication | v0.6.5 first-valid immutable predecessor publication | supported research component | one canonical filtered identity publishes at most one append-only raw identity |
| path-related qualification policy | **v0.6.18 path-gate demotion** | **current best research qualification component** | `inefficient_leg` and `jump_dominated_leg` are diagnostics, not hard morphology vetoes; all non-path v0.5.4 gates remain hard |
| qualification disagreement attribution | v0.6.19 duration-geometry decomposition | supported diagnostic evidence | remaining v0.6.18 disagreements are dominated by local-duration one-native-bar boundary sensitivity; changes no rule |
| exact one-bar duration repair | v0.6.20 | rejected challenger / retained contribution | greatly increases positive supply but worsens cross-slicing positive overlap; do not widen the 3/11 relaxation |
| fine-path information measurement | v0.6.17 session-aware information-set bounds | cloud-reviewed measurement capability | carries partial-identification intervals when native 5m bars do not identify fine path |
| parent direction/state classification | D1 historical diagnostic only | **blocked / not accepted; active next research layer** | D1/D2/PAWCT are not current parent-state authority; new work must not retry rejected endpoint routes |

## v0.6.18 decisive evidence

Frozen run: GitHub Actions `34423674192`.
Formal result commit on research branch: `9600eca94de9fb2cc39db4b995edec3d5e7870c3`.
Result bundle: `experiments/two_wave_path_gate_demotion_v0618/`.

Frozen upstream controls reproduced exactly:

- filtered mutual-unique pairs: `14,784 / 12,725 / 13,412 / 16,108 = 57,029`;
- v0.6.5 published raw strict same-event pairs: `8,381 / 5,770 / 6,204 / 9,098 = 29,453`;
- v0.6.6 aggregate matrix: `bothQ=482 / bothRejected=28,272 / mainOnlyQ=352 / otherOnlyQ=347`.

Candidate result after demoting only the two resolution-sensitive path reasons:

- aggregate positive qualification overlap: `40.8129% -> 68.3817%`;
- aggregate both-qualified: `482 -> 1,462`;
- all four offsets improved positive overlap;
- all frozen promotion gates passed;
- long-cycle / long-pair / wall-span / observed-day safety gates were not demoted;
- future outcomes were not used.

Formal verdict: `v0618_path_gate_demotion_research_candidate_pass`.

This does **not** mean morphology acceptance. It means the v0.6.18 qualification policy is the best-supported current qualification component for subsequent M0 research.

## v0.6.19 attribution evidence

Formal workflow run: GitHub Actions `34425574563`.
Formal result commit: `e5bb5d29e614d2b81f2d23820590e458430b9b86`.
Result bundle: `experiments/two_wave_duration_geometry_decomposition_v0619/`.
Formal attribution: `v0619_local_duration_boundary_sensitivity_dominant`.

The analyzer changed no recognizer or qualification rule and reproduced all v0.6.18 controls exactly:

- filtered mutual-unique same-event pairs: `57,029 / 57,029`;
- published raw strict same-event pairs: `29,453 / 29,453`;
- v0.6.18 disagreements: `676 / 676`;
- v0.6.18 candidate matrix: `bothQ=1,462 / bothRejected=27,315 / mainOnlyQ=386 / otherOnlyQ=290`.

Pooled attribution:

- local-duration family involved: `393 / 676 = 58.14%`;
- local-duration-only disagreements: `361`;
- preregistered simple one-native-bar boundary cases among local-duration-only: `318 / 361 = 88.09%`;
- amplitude involved: `144 / 676 = 21.30%`;
- confirmation involved: `158 / 676 = 23.37%`;
- long-span safety involved: `21 / 676 = 3.11%`.

Interpretation: the largest remaining qualification instability is concentrated near one-native-bar local-duration boundaries. This was a valid attribution, not permission to assume a one-bar relaxation would improve the recognizer.

## v0.6.20 adjudication and retained contribution

Formal workflow run: GitHub Actions `34426276576`.
Formal result commit: `8ef80d810ea7c47e1cc0e3f2cea4eb30f472f5e1`.
Result bundle: `experiments/two_wave_one_bar_duration_repair_v0620/`.
Formal verdict: `v0620_exact_one_bar_duration_repair_rejected`.

The sole preregistered challenger demoted `short_leg` only for `min_leg==3` and `short_cycle` only for `min_cycle==11`. All more severe duration failures, `cycle_duration_mismatch`, amplitude, confirmation and long-span safety reasons remained hard.

Frozen controls reproduced exactly. Relative to v0.6.18:

- aggregate positive overlap: `68.3817% -> 67.3564%` (**-1.0253 pp**);
- aggregate both-qualified: `1,462 -> 2,181`;
- newly qualified published identities: `5,297` unique across views;
- all four offset positive-overlap values were non-improving: `-0.8474 / -1.0557 / -0.0092 / -1.9555 pp`;
- material both-qualified gate passed, but per-offset non-regression and aggregate +3 pp gates failed;
- hard safety invariants passed.

Therefore v0.6.18 remains the qualification-policy champion unchanged.

The retained scientific contribution is narrower and important: **one-native-bar duration sensitivity is real, but direct threshold-minus-one admission is not a valid repair**. It releases many events while making the same financial identity less consistently qualified across harmless 5m slicing. Future duration work must improve the duration/scale measurement itself rather than widen `3/11` or search nearby hard thresholds.

## Historical contributions retained

Do not reduce historical versions to pass/fail only.

- v0.5.2 contributed parent exact-ridge identity.
- v0.5.4 contributed full-cycle rather than corresponding-leg duration semantics.
- v0.6.0 established morphology identity must be separated from exclusive packing.
- v0.6.3 identified ordinal0 left support as a projection instability source.
- v0.6.4 showed predecessor support is useful but member-scale publication was multivalued.
- v0.6.5 retained the predecessor gain while enforcing immutable first-valid publication.
- v0.6.7 showed native-5m `inefficient_leg` / `jump_dominated_leg` disagreements are dominated by sampling-resolution effects.
- v0.6.11 showed endpoint-erosion ensembles materially reduce fine-roughness interval sensitivity.
- v0.6.17 established session-aware partial-identification bounds and proved structural fine-path nonidentifiability is material.
- v0.6.18 converts the v0.6.7-v0.6.17 measurement insight into a successful qualification-policy improvement.
- v0.6.19 shows the next-largest qualification instability is concentrated at one-native-bar local-duration boundaries rather than broad parent-scale failure.
- v0.6.20 proves that this boundary concentration cannot be repaired by simply admitting exact 3-bar legs / 11-bar cycles; supply rises but cross-slicing positive stability falls.

Rejected routes remain evidence and must not be silently retried: v0.4.4 fixed 12-48 hierarchy, endpoint D2, confidence-gated endpoint D2, PAWCT as previously adjudicated on selected ownership, shared-1m with frozen 5m thresholds, single native-OHLC concentration proxy, native close coarsening proxy, and v0.6.20 direct one-bar threshold relaxation.

## Next authorized research step

Return to the primary unresolved M0 task: **parent `Range / UpTrend / DownTrend / Uncertain` state classification** on identities qualified by the current v0.6.18 policy.

The next direction/state challenger must obey:

1. v0.6.18 qualification remains frozen and is not retuned together with direction;
2. it must be causal and single-view at runtime;
3. it must use the two complete parent cycles / whole parent window rather than simply reusing the rejected endpoint-D2 rule;
4. historical D1 is the baseline diagnostic, not a trusted label source;
5. cross-offset same-financial-identity consistency may be used for stability evaluation, never as a runtime feature;
6. no future return, P&L, label balance or trading outcome may choose thresholds;
7. because independent human morphology labels remain absent, a successful direction component may become the best-supported **research component**, but global morphology acceptance must remain false.

Before running outcomes, freeze a direct parent-state candidate and a promotion gate that prevents trivial all-`Uncertain` or all-one-class solutions. H1/H2, third-wave, trading and production remain frozen.
