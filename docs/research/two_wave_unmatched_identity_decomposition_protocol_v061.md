# v0.6.1 Frozen protocol — unmatched identity decomposition

## Status

This protocol is frozen before reading any v0.6.1 decomposition output.

It inherits the v0.6.0 Route M conclusion and changes **no** recognizer, qualification, direction, packing, outcome, or trading logic.

## Research question

For each `5m_offset_0` canonical qualified identity that is not in a v0.6.0 mutual-unique strict same-event match against `5m_offset_1..4`, identify the earliest pre-existing upstream layer at which a harmless-offset counterpart is lost.

## Inputs

Only:

- `data/development/5m_offset_0.parquet`
- `data/development/5m_offset_1.parquet`
- `data/development/5m_offset_2.parquet`
- `data/development/5m_offset_3.parquet`
- `data/development/5m_offset_4.parquet`
- `data/manifest.json`

and frozen v0.5.2 / v0.5.4 / v0.6.0 code.

No resampling. No 2021+. No outcomes. No returns. No direction-model changes.

## Required reconstruction

For every view, reconstruct in one run:

1. v0.5.2 `RidgeRun`;
2. v0.5.4 `evaluated_records` and qualified ledger;
3. v0.6.0 canonical qualified identities;
4. v0.6.0 causal identity events, using `first_record_id` as the only upstream representative;
5. canonical all-evaluated raw identities grouped by `(phase, five_occurrence_bars)`;
6. canonical filtered tuple-birth identities grouped by `(phase, five filtered occurrence bars)`;
7. filtered extrema by TCSS scale level.

The v0.6.0 qualified checkpoints must remain:

`734 / 691 / 691 / 721 / 746`

and main canonical qualified count must remain `712`. A mismatch is `IDENTITY_INPUT_DRIFT`; stop route interpretation.

## Frozen cross-view locality

Whenever a stage compares five corresponding anchors, the rule is unchanged:

- ordered position-wise comparison;
- each absolute timestamp delta `<= 5 minutes`;
- no IoU, D1, D2, PAWCT, amplitude, return, or outcome;
- no nearest/best tie-break.

For raw qualified/evaluated identities, start phase is part of the strict edge. A phase-ignored edge may be computed only to diagnose a phase-only mismatch.

For filtered tuple/extremum diagnostics, expected anchor kinds alternate from the main causal representative's phase.

## Frozen attribution order

For every v0.6.0 main identity outside a mutual-unique strict match, test in this exact order:

0. `qualified_strict_edge_nonmutual`
1. `phase_mismatch_raw_evaluated`
2. `qualification_survival_loss`
3. `evaluated_identity_nonmutual`
4. `phase_mismatch_filtered_tuple`
5. `post_tuple_birth_loss`
6. `tuple_identity_nonmutual`
7. `tuple_topology_or_death_certification_mismatch`
8. `birth_scale_path_shift`
9. `birth_scale_path_ambiguous`
10. `filtered_extremum_survival_mismatch`

The first satisfied category is the primary attribution. Later diagnostics may be recorded but cannot overwrite it.

### Category definitions

#### `qualified_strict_edge_nonmutual`

The original v0.6.0 qualified strict edge exists, but mutual uniqueness fails because at least one endpoint has edge degree other than one.

#### `phase_mismatch_raw_evaluated`

At the all-evaluated raw-identity layer, a mutual-unique anchor counterpart exists only when phase is ignored, and the paired phases differ.

#### `qualification_survival_loss`

A same-phase mutual-unique strict raw evaluated counterpart exists in the other view, but `qualified_any=false` for that evaluated identity group.

Record all frozen rejection reasons. Do not modify them.

#### `evaluated_identity_nonmutual`

A same-phase strict raw evaluated edge exists but is not mutual-unique.

#### `phase_mismatch_filtered_tuple`

No earlier attribution applies, but a mutual-unique filtered tuple-birth anchor counterpart exists only when phase is ignored and phases differ.

#### `post_tuple_birth_loss`

A same-phase mutual-unique strict filtered tuple-birth counterpart exists, but no Stage-1 same-phase mutual-unique raw evaluated counterpart exists.

Record projection/evaluation diagnostics from the matched other-view tuple birth(s), including invalid projection/evaluate reasons and projected raw-anchor displacement when available.

#### `tuple_identity_nonmutual`

A same-phase strict filtered tuple-birth edge exists but is not mutual-unique.

#### `tuple_topology_or_death_certification_mismatch`

At the main causal member's exact `birth_scale_level`, all five expected alternating filtered extrema survive uniquely within one nominal bar in the other view, but no strict tuple-birth counterpart exists.

#### `birth_scale_path_shift`

The five expected filtered extrema do not all survive uniquely at the main birth level, but exactly one different other-view TCSS level contains all five unique one-bar counterparts.

#### `birth_scale_path_ambiguous`

More than one other-view level contains all five unique one-bar counterparts. No level is selected.

#### `filtered_extremum_survival_mismatch`

No other-view scale level contains all five unique one-bar counterparts.

## Edge-degree rule

At qualified, evaluated, and tuple stages, preserve the full bipartite strict-edge graph.

A relation is `mutual_unique` only when both endpoint degrees equal one. If a main endpoint has one edge but the other endpoint has degree >1, that main identity is still **non-mutual**, not “absent”.

No deterministic tie-break is permitted.

## Evaluated-identity grouping

All v0.5.4 evaluated records are grouped by exact `(phase, five raw occurrence bars)` before cross-view audit.

Group fields must include:

- member IDs/count;
- `qualified_any`;
- union of `scale_rejection_reasons`;
- birth-scale levels;
- attached five raw occurrence timestamps.

A group with both qualified and rejected members is `qualified_any=true`; it is not a qualification-survival loss.

## Tuple-birth grouping

Exact-ridge tuple births are grouped by exact `(phase, five filtered occurrence bars)`.

Group fields must include:

- birth event IDs/count;
- birth-scale levels;
- attached five filtered occurrence timestamps.

Projection diagnostics are joined by tuple birth event ID only. Do not infer projection status from later qualified records.

## Filtered-extremum survival

Use the main canonical identity's causal `first_record_id` to obtain:

- phase;
- `filtered_occurrence_bars`;
- `birth_scale_level`.

Expected kinds are `[phase, opposite, phase, opposite, phase]`.

At a tested other-view level, each main filtered anchor is considered uniquely surviving only when exactly one same-kind other-view extremum occurrence timestamp lies within `<=5m`.

Report per-anchor candidate counts. Any count >1 makes that level ambiguous; no nearest node may be chosen.

## Boundary overlay

Cash-session boundaries are frozen as Shanghai 09:30/11:30/13:00/15:00 = UTC minute-of-day 90/210/300/420.

A main causal identity is boundary-tagged when any raw or filtered representative anchor lies within `<=5m` of one of those boundaries.

Boundary tagging is descriptive only. It may not remove observations or change the matcher.

## Local-neighborhood overlay

Among same-phase other-view canonical qualified identities, a candidate is “local-envelope-overlap” when its closed `[e0,e4]` timestamp interval intersects the main closed `[e0,e4]` interval.

For those candidates only, report:

- count;
- minimum positional maximum five-anchor displacement;
- number of candidates tying at that minimum.

No winner is selected. These values cannot change the frozen 5-minute edge.

## Output schema

Write to:

`cloud_results/local_v061_unmatched_identity_decomposition/`

Required:

- `summary.json`
- `details_offset_1.json`
- `details_offset_2.json`
- `details_offset_3.json`
- `details_offset_4.json`
- `data_identity.json`
- `run.log`

`summary.json` must include:

- data audits and qualified/canonical checkpoints;
- v0.6.0 pair controls;
- attribution counts/fractions by offset;
- rejection-reason counts;
- projection/evaluation diagnostic counts;
- same-level and any-level anchor-survival distributions;
- session-boundary prevalence by primary attribution and strict matched control;
- local-neighborhood diagnostic distributions;
- `future_outcome_used=false`;
- `trade_authority=false`;
- `morphology_status=morphology_replication_not_yet_accepted`.

## Acceptance of this audit

The audit itself is valid only if:

1. frozen data/qualified checkpoints reproduce;
2. the v0.6.0 mutual-unique pair controls reproduce exactly;
3. every main canonical identity is accounted for as strict matched, v0.6.0 ambiguous, or exactly one primary decomposition category;
4. no category uses returns/outcomes/direction labels for matching;
5. no tolerance, qualification threshold, sigma schedule, ridge linking rule, or packing rule changes;
6. code/tests used for the decomposition are committed and identified.

No numerical result from v0.6.1 automatically promotes a repair. The cloud must review the decomposition and freeze a separate repair experiment if one is warranted.