# v0.6.8 Frozen protocol — canonical fine-path qualification representation POC

Date: 2026-09-06

Status: **FROZEN BEFORE ANY v0.6.8 CANDIDATE QUALIFICATION OUTPUT IS READ**

This protocol changes only the representation used for the three existing path hard reasons. It changes no raw identity, projection, publication, matcher, duration/amplitude/calendar/confirmation metric, threshold, direction, packing, outcome, or trading logic.

## 1. Candidate identity

Candidate:

`supplied_1m_canonical_path_for_path_gates_v068`

For each immutable v0.6.5 published raw identity, use its four published anchor-time legs on supplied `1m_official` to recompute only:

- leg efficiency;
- leg jump share;
- leg flat share.

Exact formulas and thresholds remain frozen.

## 2. Canonical path construction

For one leg with absolute published anchor times `[a,b]`:

- select supplied 1m rows with timestamps in the closed interval `[a,b]`;
- require at least two rows;
- require timestamps strictly increasing;
- do not interpolate or fill;
- use closes exactly as supplied.

Then:

```text
changes    = abs(diff(close))
length     = sum(changes)
efficiency = abs(close[-1]-close[0]) / length if length>0 else 0
jump_share = max(changes) / length if length>0 else 1
flat_share = mean(changes==0)
```

The candidate is unavailable for the identity if any of its four legs lacks sufficient supplied 1m rows.

## 3. Candidate qualification transformer

Start from the already frozen v0.6.6 qualification audit record for the same v0.6.5 published identity.

Let:

`control_hard_reasons = v054_hard_rejection_reasons`.

Candidate hard reasons are formed by:

1. remove any of:
   - `jump_dominated_leg`
   - `inefficient_leg`
   - `flat_dominated_leg`
2. retain every non-path hard reason unchanged;
3. recompute on canonical 1m profile:
   - add `inefficient_leg` iff min leg efficiency `< 0.5`;
   - add `jump_dominated_leg` iff max leg jump share `> 0.5`;
   - add `flat_dominated_leg` iff max leg flat share `> 0.5`.

Candidate `scale_qualified = (candidate_hard_reasons is empty)`.

No threshold change. No reason ranking.

## 4. Non-path invariance assertion

For every identity, the candidate must assert that all frozen non-path values used by v0.6.6 remain untouched:

- leg durations;
- cycle durations;
- amplitude ratio;
- observed trading days;
- wall days;
- confirmation delay;
- publishing confirmation bar;
- five raw occurrence bars.

Any candidate implementation that changes these is invalid.

## 5. Hard controls before interpretation

Reproduce v0.6.5 pair universe:

```text
8,381 / 5,770 / 6,204 / 9,098
aggregate 29,453
```

Reproduce v0.6.6 control matrix:

```text
both_qualified                    482
both_rejected                  28,272
main_qualified_other_rejected     352
main_rejected_other_qualified     347
```

Reproduce pre-registered repaired strata denominators/disagreements:

```text
control repaired               3,986 / 103
v0.6.3 residual repaired       2,390 / 63
v0.6.1 target repaired            80 / 24
v0.6.3 target-residual repaired   50 / 16
```

Reproduce v0.6.7 path controls:

```text
jump_dominated_leg disagreements = 368
inefficient_leg disagreements    = 211
```

Any drift stops interpretation.

## 6. Endpoint and data-identity gate

Before candidate qualification:

- verify `1m_official` bytes/SHA/rows/date against frozen manifest;
- verify no post-2020 row and no resampling;
- report whether each published raw anchor timestamp has an exact supplied 1m row;
- fail closed for any identity with unavailable four-leg canonical path.

Do not synthesize a missing endpoint.

## 7. Pair matrix

On the frozen 29,453 strict pairs classify candidate qualification as exactly:

- `both_qualified`;
- `both_rejected`;
- `main_qualified_other_rejected`;
- `main_rejected_other_qualified`;
- `candidate_unavailable` only if either side lacks required supplied 1m support.

Report candidate agreement and disagreement excluding nothing; unavailable remains an explicit status.

## 8. Positive-state stability metrics

For candidate and control report:

```text
union_qualified = bothQ + mainOnlyQ + otherOnlyQ
positive_overlap = bothQ / union_qualified
main_survival = bothQ / (bothQ + mainOnlyQ)
other_survival = bothQ / (bothQ + otherOnlyQ)
```

If union is zero, value is null; do not invent a value.

## 9. Control→candidate transition matrix

Report all control/candidate status combinations.

Required summaries:

- control disagreement → candidate both-qualified;
- control disagreement → candidate both-rejected;
- control disagreement → candidate disagreement;
- control both-qualified → candidate both-qualified;
- control both-qualified → candidate both-rejected;
- control both-qualified → candidate disagreement;
- control both-rejected → candidate both-rejected;
- control both-rejected → candidate both-qualified;
- control both-rejected → candidate disagreement.

A candidate is not judged by agreement alone.

## 10. Per-view qualification

For each view report:

- published identities;
- canonical-path available identities;
- unavailable identities/reasons;
- candidate qualified/rejected counts;
- candidate path reason counts;
- control path reason counts;
- non-path hard reason checksum/frequency equality.

## 11. Required strata

Repeat candidate pair matrix, positive overlap and control→candidate transitions for:

```text
control repaired               3,986
v0.6.3 residual repaired       2,390
v0.6.1 target repaired            80
v0.6.3 target-residual repaired   50
```

No stratum may be redefined by candidate qualification.

## 12. Synthetic gates

Tests must cover:

1. same underlying fine path, two coarse slicings, coarse path reason differs while canonical 1m candidate is identical;
2. two fine paths with identical coarse endpoint closes but different total variation/path reasons;
3. future append after leg end leaves profile unchanged;
4. fewer than two canonical rows -> unavailable;
5. no interpolation around missing rows;
6. constant fine path -> efficiency 0 / jump share 1 / flat share 1;
7. candidate transformer removes/recomputes only three path reasons and preserves every non-path reason;
8. candidate qualification does not read direction/outcome fields.

## 13. Required compact outputs

Write to:

`cloud_results/cloud_chat_v068_canonical_path_qualification/`

Required:

```text
summary.json
per_view_candidate_qualification.json
pair_offset_1.json
pair_offset_2.json
pair_offset_3.json
pair_offset_4.json
control_candidate_transitions.json
repaired_strata_candidate.json
data_identity.json
execution_receipt.json
```

## 14. Interpretation rule

No post-hoc numeric cutoff.

The cloud adjudication must explicitly distinguish:

- disagreement reduction;
- positive qualification overlap;
- joint-rejection inflation;
- newly introduced disagreement;
- unavailable canonical support.

Allowed final statuses only:

- `canonical_fine_path_representation_structurally_improves_qualification_stability`;
- `shared_fine_path_mainly_increases_joint_rejection_without_solving_positive_stability`;
- `canonical_fine_path_representation_remains_materially_unstable`;
- `mixed_result_requires_separate_analysis`.

Even a positive status authorizes only a later deployment/data-clock eligibility audit. `1m_official` remains research/audit-only until separately approved.

Duration-geometry remains a separate secondary workstream.

Global status remains `morphology_replication_not_yet_accepted`; operational baseline remains v0.4.3. Direction/outcome/trading remain frozen.
