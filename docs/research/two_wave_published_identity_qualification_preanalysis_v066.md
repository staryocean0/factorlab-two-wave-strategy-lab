# v0.6.6 Preanalysis — published raw identity downstream qualification stability

Date: 2026-09-06

Status: **WRITTEN BEFORE ANY v0.6.6 QUALIFICATION OUTPUT IS READ**

## 1. Why this audit is now allowed

v0.6.5 closed the scale-evidence multivaluedness introduced by v0.6.4: one canonical filtered identity now publishes at most one immutable predecessor-supported raw identity, using first-valid causal evidence only. The four harmless offsets retained the entire v0.6.4 structural improvement.

This authorizes one downstream question only:

> once the raw financial identity is well defined, does the already frozen v0.5.4 morphology qualification survive harmless 5m slicing consistently on strict same-event pairs?

This is not a qualification repair experiment. No threshold may change.

## 2. Frozen input identity

Use v0.6.5 published raw identity exactly as emitted:

- phase;
- five published raw occurrence bars/times;
- publishing tuple-birth member;
- publishing birth level;
- publishing confirmation bar.

Later scale evidence remains append-only and cannot alter the raw identity or qualification input.

Groups with no valid v0.6.5 publication remain missing; do not fall back to the current projection or another evidence member.

## 3. Frozen qualification logic

For each published raw identity, reconstruct five alternating raw-close extrema and apply the unchanged v0.4.3 `evaluate_pair` assumptions at the v0.6.5 publication confirmation clock.

Then apply exactly the v0.5.4 qualification ablation:

- `corresponding_leg_duration_mismatch` is diagnostic-only;
- every other frozen v0.4.3 rejection reason remains a hard gate;
- all numerical thresholds remain unchanged.

Only the binary qualification result and rejection reasons are in scope. Although `evaluate_pair` mechanically computes D1 diagnostics, v0.6.6 must not interpret, compare, optimize, or promote direction labels.

## 4. Cross-view universe

The primary stability universe is the v0.6.5 **published raw strict same-event pairs**:

```text
offset1: 8,381
offset2: 5,770
offset3: 6,204
offset4: 9,098
aggregate: 29,453
```

Pair identity is already fixed upstream. Qualification cannot participate in matching.

## 5. Pair qualification statuses

For each published raw strict pair classify only:

- `both_qualified`;
- `both_rejected`;
- `main_qualified_other_rejected`;
- `main_rejected_other_qualified`.

Qualification agreement means the two sides have the same binary qualification state. Do not discard both-rejected pairs.

## 6. Disagreement diagnostics

For qualification-disagreement pairs report:

- hard rejection reasons on the rejected side;
- whether each reason is absent/present on the qualified side's frozen audit record;
- raw leg durations, cycle durations, amplitude ratio, leg efficiency, jump share, flat share, observed-day count, wall span, confirmation delay;
- which hard reasons differ across views.

No near-threshold value may be used to alter a threshold in v0.6.6.

## 7. Per-view diagnostics

For all v0.6.5 published identities report:

- published count;
- v0.5.4 qualified count / rejected count;
- hard rejection reason frequency (reasons may overlap);
- diagnostic-only `corresponding_leg_duration_mismatch` frequency;
- confirmation delay distribution.

Counts are descriptive, not a coverage target.

## 8. Required strata

Report pair qualification stability separately for:

1. all v0.6.5 published raw strict pairs;
2. pairs that were repaired from current-control raw-displaced → v0.6.5 strict;
3. v0.6.3 residual pairs repaired by v0.6.5;
4. v0.6.1 projection targets repaired by v0.6.5;
5. v0.6.3 target residual pairs repaired by v0.6.5.

This asks whether the projection repair merely creates strict identity pairs that immediately fall apart at qualification.

## 9. Causality gate

Synthetic tests must show:

- qualification uses only the published five raw anchors, path through the completed two-cycle interval, and the fixed publication confirmation clock;
- appending future bars after the publication confirmation cannot alter qualification output;
- changing a later same-anchor scale evidence member cannot alter qualification input because v0.6.5 publication is immutable.

## 10. Interpretation

No new numeric promotion threshold is introduced.

Cloud may only decide whether qualification is:

- broadly stable enough on strict same-event pairs to keep the predecessor-publication workstream alive; or
- a material independent instability requiring its own later preanalysis.

A positive v0.6.6 result still does not authorize direction work automatically because v0.6.1 identified upstream filtered-extremum/tuple-topology instability outside the strict matched universe.

Global state remains `morphology_replication_not_yet_accepted`; operational baseline remains v0.4.3.
