# Two-Wave v0.6.23 D1-primary endpoint-erosion-consensus Huber rescue protocol

Date: 2026-09-10
Status: `frozen_before_v0623_replay`

## Question

v0.6.21 proved that a robust whole-parent-window Huber centerline contains strong direction/state information but cannot replace D1 wholesale. v0.6.22 then preserved every D1 decisive output and used Huber only to rescue D1 `Uncertain`; coverage rose sharply, but cross-slicing exact agreement still regressed on offsets 1 and 3.

Historical v0.6.11 independently showed that fixed endpoint-erosion ensembles materially reduce slicing-sensitive measurement differences. v0.6.23 asks one direct recognizer question:

> Can D1 keep full authority on its decisive outputs while Huber rescues only those D1-Uncertain records whose state is internally stable to fixed one-native-bar endpoint support erosion within the same runtime view?

This is one parent-state recognizer candidate, not a judge, meta-judge, post-outcome selector, or cross-view runtime filter.

## Frozen upstream

Unchanged:

- v0.5.2 exact-ridge parent identity;
- v0.6.5 immutable raw identity publication;
- v0.6.18 qualification policy, including path-gate demotion;
- v0.6.0 cross-view same-financial-identity matcher for evaluation only;
- D1 historical direction diagnostic;
- v0.6.21 Huber estimator constants and state thresholds:
  - `HUBER_C=1.345`;
  - `IRLS_ITERATIONS=8`;
  - `Range` iff `|score| <= 0.15`;
  - `UpTrend` iff `score >= 0.50`;
  - `DownTrend` iff `score <= -0.50`;
  - otherwise `Uncertain`.

No 2021+ data, no 2026 data, no returns, PnL, future outcome, H1/H2, or trading signal may enter candidate construction or selection.

## Sole candidate

For one already-completed v0.6.18-qualified parent identity with raw anchors `a0<a1<a2<a3<a4`, compute the frozen v0.6.21 Huber state on exactly four support windows from the **same single 5m runtime view**:

1. `full`: `[a0, a4]`;
2. `left_eroded_1`: `[a0+1, a4]`;
3. `right_eroded_1`: `[a0, a4-1]`;
4. `both_eroded_1`: `[a0+1, a4-1]`.

The v0.6.18 hard `min_leg>=4` condition guarantees the fixed one-bar support erosion does not cross the adjacent parent extrema.

Use the same amplitude unit as the frozen full parent record. Do not re-estimate amplitude, anchors, identity, qualification, confirmation time, or D1.

Define `erosion_consensus_state`:

- if all four Huber states are the same decisive state in `{range, uptrend, downtrend}`, that state is available as rescue;
- otherwise rescue state is `uncertain`.

Final v0.6.23 decision:

- if D1 is decisive, output D1 exactly;
- if D1 is `uncertain` and `erosion_consensus_state` is decisive, output the consensus state;
- otherwise output `uncertain`.

No score averaging, majority vote, confidence margin, fitted threshold, erosion-width menu, or parameter grid is allowed.

## Frozen evaluation universe

Use only the exact v0.6.18 development artifacts from workflow run `34423674192` and 2015-01-05..2020-12-31 native 5m development material.

The evaluator must reproduce exactly before interpretation:

- filtered mutual-unique same-event pairs: `57,029`;
- published raw strict same-event pairs: `29,453`;
- both-v0.6.18-qualified direction pairs: `1,462`;
- D1 pooled exact agreement: `0.957592339261286`;
- D1 pooled decisive coverage: `0.4890560875512996`;
- D1 decisive agreement: `1.0`;
- D1 opposite-trend conflicts: `0`.

Cross-offset information is evaluation-only and must never be used to create one side's state.

## Hard implementation gates

All must pass:

1. upstream pair counts and D1 controls reproduce exactly;
2. D1 decisive override count is exactly `0`;
3. full-support Huber state exactly matches frozen v0.6.21 for the same input semantics;
4. erosion support changes only the first and/or last included raw bar by exactly one native bar;
5. no identity, qualification, confirmation, amplitude unit or D1 field is modified;
6. `future_outcome_used=false`, `trade_authority=false`, `production_authority=false`.

A failure here invalidates the run; it is not a scientific rejection.

## Frozen promotion gate against D1

v0.6.23 becomes the current best-supported **research direction component** only if ALL hold:

1. exact four-state agreement is **not lower than D1 on each of all four offsets**;
2. pooled exact four-state agreement is **not lower than D1**;
3. pooled decisive coverage is at least `0.65` and at least `D1 + 0.15`;
4. each offset, on each side separately, has decisive coverage at least `0.55`;
5. decisive agreement when both sides are decisive is at least `0.995`;
6. opposite `UpTrend` vs `DownTrend` conflict count is exactly `0`;
7. pooled decisive label shares satisfy `uptrend>=0.15`, `downtrend>=0.15`, `range>=0.02`;
8. at least one D1-Uncertain record is rescued by endpoint-erosion consensus.

This is a Pareto-style gate: coverage improvement cannot buy lower slicing stability, and stability cannot win through trivial abstention.

If all pass: `v0623_D1_primary_erosion_consensus_Huber_rescue_direction_research_component_pass`.
Otherwise: `v0623_D1_primary_erosion_consensus_Huber_rescue_direction_rejected` and no direction winner is installed.

## Forbidden rescue

After results, do not:

- change erosion width from one bar;
- drop one of the four support views;
- use majority vote instead of unanimity;
- tune `0.15` or `0.50`;
- add a Huber score margin;
- select only certain labels or offsets;
- use cross-view counterpart state at runtime;
- alter v0.6.18 qualification together with direction.

A failed v0.6.23 may still retain a measured contribution, but it does not erase D1 or any earlier current-best component.

Independent human morphology acceptance remains separate and false. No trading or production authority follows.
