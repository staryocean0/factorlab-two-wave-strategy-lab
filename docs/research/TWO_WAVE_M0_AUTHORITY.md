# Two-Wave M0 Authority

Date: 2026-09-10

## Global scientific status

- Primary object: `two_wave_parent_structure_recognizer`.
- Target semantics: two complete same-scale waves -> parent `Range / UpTrend / DownTrend / Uncertain`.
- Independent morphology acceptance: **false**.
- Global status: `morphology_replication_not_yet_accepted`.
- Historical full-recognizer operational baseline: **v0.4.3**.
- Trade authority: **false**.
- Production authority: **false**.

A later component may be better supported without changing the full-recognizer baseline. Failed challengers never erase the current best component, and a component-level win never silently upgrades the whole recognizer.

## Current best-supported component stack

| Layer | Current best-supported component | Status | Meaning |
|---|---|---|---|
| causal pivot / original full recognizer | v0.4.3 temporal maturity recognizer | historical operational baseline | last full recognizer baseline; not morphology-accepted |
| parent identity | v0.5.2 exact-ridge parent identity | supported research component | causally absorbs child-scale extrema and recovers parent five-anchor identity |
| same-scale qualification semantics | v0.5.4 full-cycle-scale qualification | supported research component | corresponding half-leg duration mismatch is diagnostic, not a hard same-scale veto |
| raw financial identity publication | v0.6.5 first-valid immutable predecessor publication | supported research component | one canonical filtered identity publishes at most one append-only raw identity |
| path-related qualification policy | **v0.6.18 path-gate demotion** | **current best research qualification component** | `inefficient_leg` and `jump_dominated_leg` are diagnostics, not hard morphology vetoes |
| duration disagreement attribution | v0.6.19 | supported diagnostic evidence | remaining qualification instability is dominated by one-native-bar local-duration boundaries |
| direct one-bar duration relaxation | v0.6.20 | rejected challenger / contribution retained | increases supply but worsens cross-slicing qualification stability |
| fine-path information measurement | v0.6.17 session-aware information-set bounds | cloud-reviewed measurement capability | carries partial-identification intervals where native 5m does not identify fine path |
| parent direction/state classification | **no current winner** | active research layer | D1 is the historical stability baseline; v0.6.21 and v0.6.22 are rejected contributors, not authority |

## Qualification authority: v0.6.18 remains champion

Formal workflow run: `34423674192`.  
Formal result commit: `9600eca94de9fb2cc39db4b995edec3d5e7870c3`.

Frozen upstream controls reproduced exactly:

- filtered mutual-unique pairs: `14,784 / 12,725 / 13,412 / 16,108 = 57,029`;
- published raw strict same-event pairs: `8,381 / 5,770 / 6,204 / 9,098 = 29,453`;
- v0.6.6 aggregate matrix: `bothQ=482 / bothRejected=28,272 / mainOnlyQ=352 / otherOnlyQ=347`.

After demoting only `inefficient_leg` and `jump_dominated_leg` from hard vetoes to diagnostics:

- aggregate positive qualification overlap: `40.8129% -> 68.3817%`;
- aggregate both-qualified: `482 -> 1,462`;
- all four offsets improved;
- long-cycle, long-pair, observed-day and wall-span safety gates stayed hard;
- no future outcome was used.

Formal verdict: `v0618_path_gate_demotion_research_candidate_pass`.

## v0.6.19 and v0.6.20: duration contribution retained without changing champion

v0.6.19 reproduced all controls and showed:

- `393 / 676 = 58.14%` of remaining qualification disagreements involved local duration;
- `318 / 361 = 88.09%` of local-duration-only disagreements were preregistered one-native-bar boundary cases.

This correctly identified a real discretization problem, but v0.6.20 proved that directly admitting exact 3-bar legs / 11-bar cycles was not a valid repair:

- positive overlap `68.3817% -> 67.3564%`;
- both-qualified `1,462 -> 2,181`;
- all four offset stability deltas were non-improving.

Therefore v0.6.18 remains the qualification-policy champion. The retained contribution is that duration measurement needs improvement; nearby hard-threshold widening is a closed route.

## Direction baseline: D1

On the frozen v0.6.18 both-qualified same-event universe of 1,462 pairs:

- pooled exact four-state agreement: `95.7592%`;
- pooled decisive coverage: `48.9056%`;
- decisive agreement when both views are decisive: `100%`;
- opposite UpTrend/DownTrend conflicts: `0`.

D1 is therefore a strong stability baseline but materially over-abstains, especially on Range. It is not human morphology truth and is not current direction authority.

## v0.6.21 whole-window Huber: rejected, contribution retained

Formal result commit: `4fe8e4d837bcb5d9accb372c0bc754be137ff0a1`.  
Primary workflow run: `34439356292`.  
Equivalent cached replay: `34439563376`.

Result versus D1:

- exact agreement: `95.7592% -> 95.0068%`;
- decisive coverage: `48.9056% -> 84.2339%`;
- decisive agreement: `100%`;
- opposite trend conflicts: `0`;
- Range labels across both sides: `9 -> 254`.

Formal verdict: `v0621_whole_window_huber_direction_rejected` because per-offset exact agreement was not non-worse and the frozen material exact-agreement gate failed.

Retained contribution: whole-parent-window robust centerline information sharply reduces D1 over-abstention, and its decisive labels are internally very stable. It should be integrated conservatively, not used as a wholesale D1 replacement.

## v0.6.22 D1-primary Huber rescue: rejected, contribution retained

Formal workflow run: `34440036520`.  
Formal result commit: `89126f20a17be5e8b64c296cff4a5795efb371c4`.  
Formal verdict: `v0622_D1_primary_Huber_rescue_direction_rejected`.

The sole frozen rule preserved every D1 decisive output and used v0.6.21 Huber only when D1 was `Uncertain`.

Results:

- D1 decisive overrides: `0`;
- D1-Uncertain records rescued: `3,737`;
- pooled exact agreement: `95.7592% -> 94.7332%`;
- pooled decisive coverage: `48.9056% -> 85.8413%`;
- decisive agreement: `99.9178%`;
- opposite UpTrend/DownTrend conflicts: `0`;
- offset exact-agreement deltas: `-3.00 / 0.00 / -0.99 / 0.00 pp`.

The candidate failed the all-offset exact-agreement non-regression gate and the preregistered pooled exact-agreement improvement gate.

Retained contribution: **the Huber signal is useful as a D1 rescue source, but unconditional rescue is too sensitive at the rescue/abstention boundary**. The next direct repair should preserve D1, preserve the frozen Huber thresholds, and require the Huber state to be stable under small single-view support perturbations before rescuing D1 uncertainty.

## Historical contributions retained

Do not reduce historical versions to pass/fail only.

- v0.5.2 contributed exact-ridge parent identity.
- v0.5.4 contributed full-cycle rather than corresponding-leg duration semantics.
- v0.6.0 separated financial identity from exclusive packing.
- v0.6.3 identified ordinal0 left support as a projection instability source.
- v0.6.4 showed predecessor support helps but member-scale publication was multivalued.
- v0.6.5 retained predecessor support while enforcing immutable first-valid publication.
- v0.6.7 showed native-5m path veto disagreements are dominated by sampling-resolution effects.
- **v0.6.11 showed endpoint-erosion ensembles materially reduce slicing-sensitive measurement differences.**
- v0.6.17 established session-aware partial-identification bounds.
- v0.6.18 converted path-measurement insight into the current qualification-policy champion.
- v0.6.19 identified local-duration boundary concentration.
- v0.6.20 proved direct one-bar threshold relaxation is not the repair.
- v0.6.21 established strong whole-window direction information but failed wholesale replacement.
- v0.6.22 proved D1-primary Huber rescue can raise coverage to 85.84% with zero D1 decisive overrides and zero opposite-trend conflicts, but needs a stronger internal stability condition.

Rejected routes remain evidence and must not be silently retried: v0.4.4 fixed 12-48 hierarchy, endpoint D2, confidence-gated endpoint D2, PAWCT as previously adjudicated, shared-1m with frozen 5m thresholds, single native-OHLC concentration proxy, native close coarsening proxy, v0.6.20 direct one-bar threshold relaxation, v0.6.21 wholesale Huber replacement, and v0.6.22 unconditional Huber rescue.

## Next authorized research step

The only newly authorized direction challenger is **v0.6.23 D1-primary endpoint-erosion-consensus Huber rescue**:

1. v0.6.18 qualification stays frozen;
2. D1 decisive outputs can never be overridden;
3. the v0.6.21 Huber estimator and `0.15 / 0.50` state thresholds stay frozen;
4. when D1 is `Uncertain`, Huber may rescue only if the full parent window and fixed one-native-bar endpoint-eroded support views all give the same decisive state;
5. all support views are computed from the same runtime 5m view only; cross-offset data is evaluation-only;
6. no parameter grid, margin tuning, future return, PnL or outcome selection is allowed;
7. promotion requires D1 exact-agreement non-regression on every offset plus a material decisive-coverage gain; a coverage gain bought by lower stability does not win.

Independent human morphology labels remain absent. Even a successful direction challenger can become only the best-supported **research direction component**; global morphology acceptance remains false. H1/H2, third-wave, trading and production remain frozen.
