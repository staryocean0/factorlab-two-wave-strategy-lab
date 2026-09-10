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

Rejected routes remain evidence and must not be silently retried: v0.4.4 fixed 12-48 hierarchy, endpoint D2, confidence-gated endpoint D2, PAWCT as previously adjudicated on selected ownership, shared-1m with frozen 5m thresholds, single native-OHLC concentration proxy, native close coarsening proxy.

## Next authorized research step

Do **not** change direction/state classification yet.

The next unresolved qualification family is duration geometry (`short_leg`, `short_cycle`, `cycle_duration_mismatch`, with long-span safety kept separate). Before changing any duration rule, run a results-blind decomposition on the fixed v0.6.5 strict same-event universe under the v0.6.18 path policy to determine which duration disagreements are genuine parent-scale differences versus harmless one-bar slicing boundary effects.

No duration threshold may be changed in that decomposition. Direction, H1/H2, third-wave, outcomes, PnL, paper trading and production remain frozen.
