# v0.6.1 Preanalysis — unmatched identity decomposition

## Why this experiment exists

v0.6.0 was cloud-adjudicated **Route M**. Removing legacy exclusive packing materially improves strict same-event recovery, but it does not solve identity stability: for `5m_offset_0` versus offsets 1..4, roughly 74%–82% of canonical qualified main identities remain outside a mutual-unique strict same-event match.

The next question is therefore not whether to widen the five-anchor tolerance and not whether to change D1/D2/PAWCT. The question is:

> **At which already-existing upstream layer does a v0.6.0 unmatched qualified financial identity first cease to have a harmless-offset counterpart?**

This is a decomposition/audit experiment only. It must not change the recognizer, qualification thresholds, direction formulas, packing, or trading authority.

## Frozen upstream

- v0.5.2 TCSS exact-ridge parent identity;
- v0.5.4 full-cycle qualification;
- v0.6.0 financial identity semantics and strict cross-view relation;
- v0.6.0 formal cloud verdict: **Route M**;
- supplied `5m_offset_0..4` development views only, through 2020-12-31;
- no resampling, no 2021+, no outcome/P&L fields.

Operational baseline remains **v0.4.3**. Global status remains `morphology_replication_not_yet_accepted`.

## Population

For each pair `5m_offset_0` versus `5m_offset_k`, k=1..4:

1. reconstruct frozen v0.5.4 evaluated records and v0.6.0 canonical qualified identities;
2. reproduce the v0.6.0 strict identity graph: same phase, ordered five raw occurrence timestamps, every positional absolute delta `<= 5 minutes`;
3. keep the v0.6.0 mutual-unique matches as controls;
4. decompose main identities that are **not** in a mutual-unique strict match.

A main identity with a strict edge that fails only because the other endpoint is not unique is not to be silently called “absent”; it receives an explicit non-mutual/ambiguity attribution.

## Frozen causal representative

A canonical financial identity may contain multiple birth-scale members. Upstream tracing uses the member that causally published the v0.6.0 identity: `first_record_id` from `causal_identity_events`.

This rule is fixed before decomposition. No representative is selected by whichever one produces the best cross-view match.

## Stage-by-stage attribution

The decomposition is hierarchical. Once an identity is recovered at an earlier stage, later stages may be reported as diagnostics but may not replace that attribution.

### Stage 0 — qualified strict edge exists but is non-mutual

Use the original v0.6.0 qualified canonical identities and original 5-minute same-phase relation.

If a main identity has one or more strict qualified edges but none is mutual-unique because of endpoint degree, report:

`qualified_strict_edge_nonmutual`

No tie-break is allowed.

### Stage 1 — raw evaluated identity, before qualification survival

Canonicalize **all** v0.5.4 `evaluated_records`, not only qualified records, by:

`(phase, five raw occurrence bars)`

Scale duplicates are evidence for the same evaluated raw identity. Preserve:

- member record IDs;
- whether any member is qualified;
- union of frozen rejection reasons;
- birth-scale levels.

Run the same ordered-five-anchor `<=5m` relation at this layer.

Attribution:

- opposite-phase unique raw-anchor counterpart: `phase_mismatch_raw_evaluated`;
- same-phase strict counterpart exists but only as rejected evaluated identity: `qualification_survival_loss`;
- a strict evaluated edge exists but is not mutual-unique: `evaluated_identity_nonmutual`.

For `qualification_survival_loss`, report frozen `scale_rejection_reasons`; do not change thresholds in this experiment.

### Stage 2 — filtered exact-ridge tuple birth

Canonicalize exact-ridge tuple births by:

`(start phase, five filtered occurrence bars)`

and compare ordered filtered occurrence timestamps with the same `<=5m` positional rule.

Attribution:

- opposite-phase unique tuple counterpart: `phase_mismatch_filtered_tuple`;
- same-phase strict tuple counterpart exists, but no Stage-1 raw evaluated counterpart: `post_tuple_birth_loss`.

For `post_tuple_birth_loss`, report diagnostic subflags only:

- `projection_invalid`;
- `evaluate_pair_invalid`;
- `raw_projection_displacement` when projection is valid but the projected raw identity does not retain the strict five-anchor relation;
- main/other tuple birth-scale levels.

These subflags do not change the Stage-2 attribution.

### Stage 3 — same birth-level filtered-extremum survival

If no strict tuple-birth counterpart exists, take the causal main member's five filtered occurrence anchors and its frozen `birth_scale_level`.

At the **same level** in the other view, for each of the five anchors require:

- expected alternating extremum kind implied by the main start phase;
- occurrence timestamp within `<=5m`;
- exactly one eligible other-view extremum.

If all five anchors survive uniquely at the same scale level but no strict tuple birth exists, attribute:

`tuple_topology_or_death_certification_mismatch`

This says the local extrema survived but the exact-ridge tuple/birth certification path did not.

If any anchor has more than one eligible node, report ambiguity; do not pick nearest.

### Stage 4 — birth-scale path shift

If Stage 3 fails, apply the same five-anchor survival test independently at every supplied TCSS scale level in the other view.

- exactly one other level with all five unique anchors: `birth_scale_path_shift`;
- more than one qualifying level: `birth_scale_path_ambiguous`;
- no level with all five unique anchors: proceed to Stage 5.

No closest level is selected post hoc.

### Stage 5 — filtered-extremum survival mismatch

If the same filtered five-anchor morphology cannot be recovered uniquely at any level, attribute:

`filtered_extremum_survival_mismatch`

Report the number of uniquely surviving anchors at the main birth level and the maximum number recovered on any other level (0..5), without converting that diagnostic into a fitted threshold.

## Session/slicing-boundary overlay

Session proximity is a **tag, not a root-cause classifier and not a matcher**.

Using timezone-aware UTC bar-end timestamps, tag an identity when any causal representative raw or filtered anchor is within one nominal 5-minute bar of a CSI1000 cash-session boundary corresponding to Shanghai 09:30, 11:30, 13:00, or 15:00 (UTC 01:30, 03:30, 05:00, 07:00).

Report boundary-tag prevalence by attribution category and among v0.6.0 strict matched controls. Do not remove boundary records or create a calendar-based recognizer rule.

## Local-neighborhood diagnostic

For unmatched main identities, report—without using it for matching—the number of same-phase qualified other-view identities whose `[e0,e4]` time envelopes overlap the main `[e0,e4]` envelope.

If at least one exists, report only:

- the minimum attainable positional `max_delta_minutes` among those local candidates;
- how many candidates tie for that minimum.

Do not choose a winner, do not widen the v0.6.0 matcher, and do not create a new tolerance from these values.

## Required outputs

Per offset pair, report:

- v0.6.0 mutual-unique matches / ambiguity / unmatched controls;
- count and fraction of each Stage 0–5 attribution among main non-mutual/unmatched identities;
- qualification rejection-reason counts for Stage 1;
- projection/evaluation diagnostic counts for Stage 2;
- same-level and any-level anchor-survival distributions;
- birth-level shift diagnostics;
- session-boundary-tag prevalence by category and matched control;
- local-neighborhood candidate-count and minimum-displacement distributions;
- full per-identity decomposition rows for audit.

Also re-report frozen data identity, raw qualified checkpoints and `trade_authority=false`.

## Interpretation boundary

This experiment is **attribution, not repair**. It does not have a post-hoc numeric promotion threshold and cannot itself authorize a code-path change.

After the decomposition, the next research target must be the earliest layer that the evidence shows is materially responsible. Any proposed repair at that layer requires a new preanalysis/frozen protocol before implementation or parameter changes.

In particular:

- do not widen the 5-minute relation from this run;
- do not change v0.5.4 qualification thresholds from rejection counts;
- do not relink ridges from the decomposition output;
- do not return to D1/D2/PAWCT unless identity adequacy is separately established;
- do not use returns/outcomes/P&L.

PR remains Draft and main is not merged.