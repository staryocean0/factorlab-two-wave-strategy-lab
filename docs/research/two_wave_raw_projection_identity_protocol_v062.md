# v0.6.2 Frozen protocol — raw-projection financial identity audit

Date: 2026-09-06

Status: **FROZEN BEFORE ANY v0.6.2 AUDIT OUTPUT IS READ**

This protocol inherits v0.6.1 and changes no recognizer, ridge, tuple-birth, qualification, direction, packing, outcome, or trading logic.

## 1. Research question

For v0.5.2 exact-ridge filtered parent tuples that are already stable enough to form same-phase mutual-unique cross-view filtered-tuple matches, determine whether the current raw projection is:

1. single-valued inside one view across duplicate scale/confirmation evidence; and
2. financially identity-stable across harmless native-5m slicing.

If it is not, diagnose the existing operator without repairing it.

## 2. Frozen upstream

- v0.5.2 exact-ridge parent identity;
- v0.5.4 full-cycle scale qualification remains downstream and unchanged;
- v0.6.0 financial identity / packing separation remains unchanged;
- v0.6.1 decomposition result is prior evidence only.

The current projection under audit remains exactly:

`sequential_raw_close_extreme_inside_filtered_phase_bounds`

implemented by frozen `project_event_to_raw`.

## 3. Data

Primary native-5m views:

- `data/development/5m_offset_0.parquet`
- `data/development/5m_offset_1.parquet`
- `data/development/5m_offset_2.parquet`
- `data/development/5m_offset_3.parquet`
- `data/development/5m_offset_4.parquet`

Audit-only canonical path:

- `data/development/1m_official.parquet`

Manifest:

- `data/manifest.json`

All are shipped development material, 2015-01-05 through 2020-12-31. No resampling and no 2021+.

## 4. Required hard controls before interpretation

The audit must reproduce v0.6.0/v0.6.1 controls before interpreting projection diagnostics:

```text
qualified: 734 / 691 / 691 / 721 / 746
canonical qualified: 712 / 673 / 678 / 700 / 728

offset1: qualified matches=180, ambiguity=1/1, unmatched=531/492
offset2: qualified matches=129, ambiguity=0/0, unmatched=583/549
offset3: qualified matches=129, ambiguity=1/0, unmatched=582/571
offset4: qualified matches=184, ambiguity=1/1, unmatched=527/543
```

The v0.6.1 `post_tuple_birth_loss` target stratum must also reproduce:

```text
offset1: 191
offset2: 195
offset3: 194
offset4: 209
aggregate: 789
```

and prior projection-displacement diagnostics must reproduce:

```text
offset1: 191
offset2: 194
offset3: 193
offset4: 209
aggregate: 787
```

Any drift stops interpretation.

## 5. Canonical filtered-tuple grouping

Within each view, exact-ridge tuple births are grouped by:

`(start_phase, five filtered occurrence bars)`

The group retains **all** tuple-birth evidence members. Birth scale and confirmation time are evidence, not part of the filtered financial identity.

For each member event, reconstruct the current raw projection and exact current projection windows. Do not select the member with the best cross-view match.

## 6. Single-view projection single-valuedness

For each canonical filtered-tuple group, report:

- member event count;
- projection-valid count / invalid count and reasons;
- number of distinct valid raw five-anchor tuples;
- number of distinct valid raw five-anchor timestamp tuples;
- changed raw anchor ordinals across members;
- member confirmation bars / birth levels;
- ordinal-4 tail extension from filtered e4 to member confirmation;
- whether projection differences are confined to ordinal 4 or also affect earlier anchors.

Frozen group status:

- `no_valid_projection`: zero valid members;
- `single_valued_projection`: valid members map to exactly one raw five-anchor identity;
- `multi_valued_projection`: valid members map to more than one raw five-anchor identity.

Invalid evidence may coexist with a single-valued valid set and is reported separately; it does not get silently dropped.

No best-member tie-break is allowed.

## 7. Cross-view filtered-tuple match universe

For offset0 vs each offset1..4, build the full canonical filtered-tuple bipartite graph using exactly:

- same start phase;
- ordered five filtered occurrence timestamps;
- every absolute timestamp delta `<= 5 minutes`;
- mutual-unique only;
- no post-hoc nearest/best tie-break.

This is the **primary v0.6.2 cross-view universe**. Do not condition only on v0.6.1 failures.

## 8. Cross-view projection status

For every mutual-unique canonical filtered-tuple pair:

1. retain the full valid raw projection set on both sides;
2. if either side has zero valid projections, status `projection_invalid_group`;
3. else if either side has more than one distinct valid raw identity, status `within_view_multi_projection`;
4. else compare the sole raw identities with the unchanged same-phase five-anchor `<=5m` relation:
   - pass -> `raw_projection_strict_match`;
   - fail -> `raw_projection_displaced`.

This ordering is frozen. No projection member may be chosen because it matches better.

## 9. Exact current projection-window audit

For every tuple-birth member, reproduce the frozen operator's windows exactly.

For filtered bars `f0..f4` and member confirmation `c`:

```text
first lower = max(0, 2*f0 - f1)
upper[0..4] = [f1-1, f2-1, f3-1, f4-1, c]
next lower = previous selected raw occurrence + 1
```

For each ordinal record:

- expected kind;
- filtered occurrence bar/time;
- lower / upper bar and absolute time;
- selected raw occurrence bar/time/close;
- exact max/min tie count in that window;
- selected distance from lower and upper bounds in bars and minutes;
- selected-vs-filtered time displacement;
- for ordinal 4, tail extension `confirmation - filtered e4` in bars/minutes.

The audit function must be output-equivalent to frozen `project_event_to_raw`; synthetic/unit tests must compare selected indices and validity/reasons.

## 10. Diagnostics for `raw_projection_displaced`

For single-valued paired groups whose raw identities are displaced, report:

### 10.1 Anchor displacement

- five raw positional time deltas;
- first ordinal with delta `>5m`;
- count of displaced ordinals;
- whether displaced ordinals form a suffix from the first displaced ordinal.

No new tolerance is fitted.

### 10.2 Window displacement

Per ordinal:

- lower-bound absolute-time delta between views;
- upper-bound absolute-time delta between views;
- whether main selected raw time lies inside the other view's current absolute-time window;
- whether other selected raw time lies inside the main view's current absolute-time window.

This is descriptive only.

### 10.3 Tie / plateau overlay

Per ordinal:

- exact raw extreme tie count in each 5m projection window;
- flag whether either side has tie count >1.

No epsilon-near-tie threshold is introduced in v0.6.2.

### 10.4 Sequential-propagation overlay

Report lower-bound divergence and whether later displaced anchors form a suffix. This is an overlay, not proof of causal mechanism and not a primary category.

## 11. 1m canonical-path diagnostic

Use `1m_official` only after the current 5m windows are fixed.

For each side and each ordinal:

1. take that side's existing 5m projection window as an absolute closed timestamp interval;
2. select the expected max/min close from **supplied** `1m_official` rows whose timestamps fall inside that interval;
3. break exact ties by the same `last_argextreme` rule;
4. do not create/resample any 5m bar.

Compare the two resulting five-anchor 1m diagnostic timestamp tuples with the same `<=5m` relation.

Frozen diagnostic labels for a 5m raw-displaced pair:

- `one_minute_strict_match`: all five 1m diagnostic anchors are within `<=5m`;
- `one_minute_displaced`: at least one is beyond `5m`;
- `one_minute_unavailable`: at least one current absolute window contains no shipped 1m row.

Interpretation is limited:

- `5m displaced + 1m strict` supports a 5m sampling-lattice aliasing explanation;
- `5m displaced + 1m displaced` supports instability of current absolute phase-window semantics;
- neither result defines a replacement projection.

## 12. v0.6.1 target-stratum reproduction

Recompute the v0.6.1 `post_tuple_birth_loss` subset using the frozen v0.6.1 logic, not by loading its result labels as truth.

For that subset report all sections above separately, including:

- single-valuedness of the matched filtered tuple groups;
- first displaced ordinal distribution;
- ordinal-specific displacement rates;
- tie involvement;
- window cross-membership;
- 1m diagnostic labels;
- ordinal-4 confirmation-tail diagnostics.

The aggregate target and 787 displacement controls must reproduce before interpretation.

## 13. Causality / prefix tests

Synthetic tests must demonstrate both:

1. frozen current projection output is unchanged by appending arbitrary future bars after its frozen confirmation clock;
2. a one-bar perturbation of a frozen phase-window bound may change identity without using future data, proving why prefix causality alone is not cross-slicer invariance.

These tests diagnose properties of the current operator; they do not change it.

## 14. Required outputs

Write to:

`cloud_results/cloud_chat_v062_raw_projection_identity_audit/`

Required small outputs:

```text
summary.json
per_view_single_valuedness.json
pair_offset_1.json
pair_offset_2.json
pair_offset_3.json
pair_offset_4.json
v061_target_diagnostics.json
data_identity.json
execution_receipt.json
```

Large per-event rows may remain in the current execution runtime unless a compact reviewable artifact is needed. Do not upload duplicate parquet.

## 15. Summary metrics

`summary.json` must include at least:

- data identity / hard-control reproduction;
- per-view canonical filtered-tuple group counts;
- per-view no-valid / single-valued / multi-valued projection group counts;
- changed-ordinal distribution within multi-valued groups;
- cross-view mutual-unique filtered-tuple pair counts;
- projection-invalid / within-view-multi / raw-strict / raw-displaced pair counts;
- raw displacement by ordinal and first-displaced ordinal;
- suffix-propagation overlay;
- exact-tie involvement;
- window cross-membership diagnostics;
- 1m strict/displaced/unavailable diagnostic counts;
- v0.6.1 target-stratum controls and corresponding projection diagnostics;
- ordinal-4 tail-extension diagnostics;
- `future_outcome_used=false`;
- `trade_authority=false`;
- `morphology_status=morphology_replication_not_yet_accepted`.

## 16. Interpretation rule — no post-hoc numerical cutoff

This protocol intentionally sets no new percentage threshold.

Cloud adjudication may conclude only which mechanisms are materially represented across all four harmless offsets and therefore deserve a later **separately frozen repair preanalysis**.

In particular:

- if within-view multi-valued projection is present, a later repair must first make raw identity a well-defined function of canonical filtered identity;
- if 5m displacement often collapses on the canonical 1m diagnostic, a later repair may investigate view-specific sampling-lattice dependence;
- if the 1m diagnostic remains displaced, a later repair must investigate phase-window semantics before proposing a raw target;
- if mechanisms are mixed, they remain separate workstreams.

No v0.6.2 result authorizes changing `project_event_to_raw` in the same experiment.
