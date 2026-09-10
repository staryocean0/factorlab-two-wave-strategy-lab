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
| fine-path information measurement | v0.6.17 session-aware information-set bounds | cloud-reviewed measurement capability | carries partial-identification intervals when native 5m bars do not identify fine path |
| parent direction/state classification | D1 historical diagnostic only | **blocked / not accepted** | do not promote D1/D2/PAWCT to current parent-state authority |

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

Formal workflow run: GitHub Actions `34438737396`.
Formal result commit: `2c755eab8d28822ea7f7927c4c8b43162af1824e`.
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

Reason-level one-bar boundary attribution:

- `short_leg`: `250 / 252 = 99.21%`;
- `short_cycle`: `94 / 108 = 87.04%`;
- `cycle_duration_mismatch`: `29 / 68 = 42.65%`.

All four harmless offsets independently showed the same pattern: simple-one-bar fraction among local-duration-only was `86.67% / 86.90% / 90.43% / 88.17%`.

Interpretation: after the successful v0.6.18 path-gate demotion, the largest remaining instability is a narrow native-bar discretization boundary around the frozen `min_leg=4` and `min_cycle=12` requirements. The evidence does **not** support demoting `cycle_duration_mismatch` in the same step. This authorizes exactly one preregistered single-view causal boundary-repair challenger.

v0.6.18 remains the current best qualification component until such a challenger passes its own frozen promotion gate.

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

Rejected routes remain evidence and must not be silently retried: v0.4.4 fixed 12-48 hierarchy, endpoint D2, confidence-gated endpoint D2, PAWCT as previously adjudicated on selected ownership, shared-1m with frozen 5m thresholds, single native-OHLC concentration proxy, native close coarsening proxy.

## Next authorized research step

Do **not** change direction/state classification yet.

The only newly authorized challenger is a narrow, causal, single-view duration-boundary repair built on the v0.6.18 qualification policy:

- `short_leg` may be demoted only for the exact boundary `min_leg == 3`; `min_leg <= 2` remains hard rejection;
- `short_cycle` may be demoted only for the exact boundary `min_cycle == 11`; `min_cycle <= 10` remains hard rejection;
- `cycle_duration_mismatch` remains hard in this first boundary-repair challenger;
- amplitude, confirmation, long-cycle, long-pair, observed-day and wall-span gates remain unchanged;
- no cross-view counterpart may be used by the recognizer at runtime;
- no parameter grid or broad duration-threshold loosening is authorized.

Before results, freeze a promotion gate against v0.6.18 on the same `57,029 -> 29,453` identity universe. v0.6.18 remains champion if the challenger does not pass.

Direction, H1/H2, third-wave, outcomes, PnL, paper trading and production remain frozen.
