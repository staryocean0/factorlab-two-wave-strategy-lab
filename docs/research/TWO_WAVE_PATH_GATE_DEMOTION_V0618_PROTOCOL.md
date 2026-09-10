# v0.6.18 path-gate demotion protocol

Date: 2026-09-10
Status: `frozen_before_v0618_financial_replay`

## Question

Prior frozen evidence established that native-5m `inefficient_leg` and `jump_dominated_leg` are sampling-resolution measurements rather than slicing-invariant morphology truths:

- v0.6.7: on strict same-event pairs, all 368 `jump_dominated_leg` disagreements become both-pass on the authoritative fine path, while all 211 `inefficient_leg` disagreements become both-fail;
- v0.6.9: refinement makes efficiency and jump-share migrate in opposite directions, so no simple common threshold remap is supported;
- v0.6.17: 28.3% of published legs contain structural source gaps and therefore do not admit a unique fine-path point truth from native 5m OHLC alone.

This experiment asks one narrow question:

> Under the already-frozen parent/event identity, should native-5m `inefficient_leg` and `jump_dominated_leg` stop acting as hard same-scale qualification vetoes and remain diagnostics only?

This is a direct qualification-policy change inside the same M0 recognizer research stack. It does not create a second recognizer, a learned judge, or a new outcome evaluator.

## Frozen upstream

Unchanged:

- v0.5.2 TCSS exact-ridge parent identity;
- v0.6.4 predecessor-supported ordinal0 raw projection geometry;
- v0.6.5 first-valid append-only raw identity publication;
- v0.5.4 full-cycle-scale qualification semantics, including `corresponding_leg_duration_mismatch` already diagnostic-only;
- v0.6.0 strict cross-view identity matcher: same phase, five ordered occurrence timestamps each within one nominal 5m bar, mutual-unique only;
- all raw anchors, publication clocks and canonical filtered identities;
- D1 and all direction fields (diagnostic only here);
- no exclusive packing in the identity/qualification comparison;
- no return, PnL, future outcome, H1/H2, or trading input.

## Only allowed change

Demote exactly these two v0.5.4 hard rejection reasons to diagnostics:

- `inefficient_leg`
- `jump_dominated_leg`

The candidate hard-reason set is therefore:

`v0618_hard = v054_hard - {inefficient_leg, jump_dominated_leg}`

No numerical threshold is changed. The old raw efficiency and jump-share values and trigger flags must remain in output diagnostics.

All other v0.5.4 hard reasons remain byte-for-byte semantic controls, including:

- `short_leg`
- `short_cycle`
- `long_cycle`
- `long_pair`
- `cycle_duration_mismatch`
- `invalid_amplitude`
- `amplitude_mismatch`
- `flat_dominated_leg`
- `too_many_observed_days`
- `wall_span_too_long`
- `confirmation_too_late`

## Frozen data and comparison universe

Use only the existing 2015-01-05..2020-12-31 development material:

- `5m_offset_0` ... `5m_offset_4`

No 2021+ rows. No resampling. No 2026 data.

The cross-view comparison universe must reproduce the v0.6.5/v0.6.6 published-identity strict pairs exactly:

- offset0 vs 1: 8,381
- offset0 vs 2: 5,770
- offset0 vs 3: 6,204
- offset0 vs 4: 9,098
- aggregate: 29,453

The frozen v0.6.6 control qualification matrices are:

- offset1: bothQ=135, bothReject=8067, mainOnlyQ=89, otherOnlyQ=90
- offset2: bothQ=93, bothReject=5519, mainOnlyQ=90, otherOnlyQ=68
- offset3: bothQ=93, bothReject=5924, mainOnlyQ=89, otherOnlyQ=98
- offset4: bothQ=161, bothReject=8762, mainOnlyQ=84, otherOnlyQ=91
- aggregate: bothQ=482, bothReject=28272, mainOnlyQ=352, otherOnlyQ=347

Control aggregate positive qualification overlap is:

`482 / (482 + 352 + 347) = 40.8129%`.

## Hard implementation gates

Before interpretation, all must pass:

1. published canonical identities and strict pair counts reproduce exactly;
2. candidate raw anchors / phase / publication confirmation are identical to control;
3. for every side of every strict pair, every non-demoted hard rejection reason is unchanged;
4. no control-qualified side may become candidate-rejected;
5. `future_outcome_used=false` and `trade_authority=false` everywhere;
6. synthetic/unit tests prove that only the two registered path reasons can change qualification.

Any failure invalidates the run; it is not a research rejection.

## Frozen promotion gate

For each offset define positive overlap:

`both_qualified / (both_qualified + main_only_qualified + other_only_qualified)`.

The v0.6.18 candidate is promoted only if ALL conditions hold:

1. positive overlap is **not lower than control on each of all four offsets**;
2. aggregate positive overlap is at least **45.8129%** (control + 5.0 percentage points);
3. aggregate `both_qualified >= 531` (at least 10% above the frozen 482 control count, rounded up);
4. the old case_02 90/3 pathology remains rejected by unchanged non-path gates if that exact audit identity is present;
5. no candidate can bypass unchanged `long_cycle`, `long_pair`, `too_many_observed_days`, or `wall_span_too_long` gates merely because the two path reasons were demoted.

If all pass: `v0618_path_gate_demotion_research_candidate_pass`.
Otherwise: `v0618_path_gate_demotion_rejected` and v0.5.4 hard path gates remain the active research qualification policy.

Passing this gate is **not morphology acceptance**. Independent human-label acceptance remains separately blocked and no trading/production authority follows.

## Forbidden rescue

After seeing v0.6.18 results, do not:

- demote a third reason;
- change any duration/amplitude/clock threshold;
- alter the 5m strict matcher tolerance;
- select subsets by direction, outcome, or visual attractiveness;
- use authoritative 1m prices as runtime qualification input;
- change v0.6.5 publication to maximize cross-view agreement.
