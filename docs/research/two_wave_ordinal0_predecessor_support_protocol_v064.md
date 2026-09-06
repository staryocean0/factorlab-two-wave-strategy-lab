# v0.6.4 Frozen protocol — predecessor-supported ordinal0 raw projection POC

Date: 2026-09-06

Status: **FROZEN BEFORE ANY v0.6.4 FINANCIAL REPLAY OUTPUT IS READ**

This protocol registers exactly one repair candidate from `two_wave_ordinal0_predecessor_support_preanalysis_v064.md`. It changes no ridge identity, tuple birth, qualification threshold, direction, packing, matcher, outcome, or trading logic.

## 1. Candidate identity

Candidate name:

`birth_scale_predecessor_filtered_phase_start`

For each frozen v0.5.2 exact-ridge tuple birth:

- use its existing birth scale level and existing five ridge nodes;
- locate those five nodes in the complete ordered birth-level ridge-node list;
- require the five nodes to occupy five consecutive positions;
- let `p` be the immediately preceding birth-level ridge node;
- if `p` exists, is opposite kind to tuple `f0`, and is confirmed no later than tuple-birth confirmation, set ordinal0 lower support to `p.occurrence_index + 1`;
- ordinal0 upper support remains `f1 - 1`;
- ordinals1..4 remain exactly the frozen sequential projection rule;
- exact max/min and last-exact-tie selection remain unchanged.

If no valid predecessor exists, candidate status is `ordinal0_left_censored_no_predecessor`. No mirror fallback is permitted.

## 2. Frozen current control

The existing operator remains the control:

`sequential_raw_close_extreme_inside_filtered_phase_bounds`

with ordinal0 lower:

`max(0, 2*f0 - f1)`.

The candidate must be evaluated side-by-side against that frozen control on the same canonical filtered-tuple identities and cross-view pair universe.

## 3. Candidate validity

After substituting only ordinal0 lower support, preserve all frozen projection validation:

- each phase window must be non-empty;
- selected raw occurrences must increase strictly;
- alternating selected prices must be actual turns under the frozen check;
- no future bar beyond the existing member/selection confirmation clocks is used.

Candidate invalid reasons are reported explicitly. A left-censored missing predecessor is not converted to another projection rule.

## 4. Single-view grouping

Canonical filtered identity remains:

`(start_phase, five filtered occurrence bars)`.

Retain all tuple-birth members. For every member compute candidate projection using that member's own birth level and predecessor.

Group status:

- `no_valid_candidate_projection`;
- `single_valued_candidate_projection`;
- `multi_valued_candidate_projection`.

No member may be selected because it matches another view better. For window diagnostics use the earliest valid member ordered by `(birth_confirmation, birth_level, event_id)`, identical in spirit to v0.6.2.

## 5. Frozen cross-view universe

Primary pair universe is unchanged from v0.6.2:

- canonical filtered-tuple groups;
- same phase;
- all five filtered occurrence timestamp deltas `<=5m`;
- mutual-unique only;
- no tie-break.

The filtered-tuple edge graph must be identical to v0.6.2. Candidate projection cannot affect pair formation.

## 6. Pair status

For each mutual-unique filtered pair, compute current-control and candidate status separately.

Candidate status order:

1. `candidate_invalid_group` if either group has no valid candidate projection;
2. `candidate_within_view_multi_projection` if either group has >1 valid candidate raw identity;
3. otherwise compare sole candidate raw identities with unchanged same-phase five-anchor `<=5m` evaluator:
   - `candidate_raw_strict_match`;
   - `candidate_raw_displaced`.

No tolerance is changed.

## 7. Required strata

Report candidate vs control on exactly:

1. all mutual-unique filtered-tuple pairs;
2. v0.6.2 control raw-displaced pairs;
3. v0.6.3 canonical-1m residual pairs (`1578/1738/1806/1718`);
4. v0.6.1 post-tuple projection-displacement targets (`191/194/193/209`);
5. v0.6.3 target residual subset (`32/28/30/32`).

For each stratum report:

- `repaired`: control displaced, candidate strict;
- `unchanged_displaced`: control displaced, candidate displaced;
- `newly_invalid_or_censored`;
- `newly_broken`: control strict, candidate displaced;
- where applicable, candidate strict retained from control strict.

These labels are structural only, not accuracy or trading outcomes.

## 8. Canonical-1m audit

Use supplied `1m_official` only as audit path. For each candidate absolute window, select canonical 1m max/min with unchanged last-exact-tie rule.

1m is never a runtime input to the candidate. No resampling or interpolation.

## 9. Hard controls

Before candidate interpretation reproduce:

```text
v0.6.2 filtered mutual-unique pairs: 14784 / 12725 / 13984 / 15536
v0.6.2 control raw displaced: 6975 / 7311 / 7445 / 7542
v0.6.3 residual: 1578 / 1738 / 1806 / 1718
v0.6.1 post-tuple displaced target: 191 / 194 / 193 / 209
v0.6.3 target residual: 32 / 28 / 30 / 32
```

If any control drifts, stop interpretation.

## 10. Synthetic gates

Tests must cover:

- a tuple with a valid opposite-kind predecessor;
- no predecessor -> explicit left censor, no fallback;
- predecessor kind mismatch -> invalid;
- predecessor confirmation after tuple-birth confirmation -> invalid;
- exact tie keeps last occurrence;
- future append after frozen confirmation does not rewrite;
- if candidate ordinal0 selected occurrence equals control ordinal0, candidate ordinals1..4 equal control output;
- one-bar harmless slicing example where mirror support excludes a shared underlying first extremum but predecessor support contains it.

## 11. Output

Write compact outputs to:

`cloud_results/cloud_chat_v064_ordinal0_predecessor_support/`

Required:

```text
summary.json
per_view_candidate_single_valuedness.json
pair_offset_1.json
pair_offset_2.json
pair_offset_3.json
pair_offset_4.json
v061_target_candidate.json
v063_residual_candidate.json
data_identity.json
execution_receipt.json
```

## 12. Interpretation rule

No post-hoc numerical threshold is introduced.

Cloud may conclude only whether this **single registered ordinal0 repair** is structurally promising enough to justify a separately frozen downstream qualification audit.

Positive evidence requires the same directional improvement across all four harmless offsets, no material within-view multi-valuedness, and no new failure mode large enough to negate the repaired population. Coverage alone is not success.

If results are mixed or poor, v0.6.4 ends. Do not invent a second left-support candidate after seeing results.

Sequential-lower support is explicitly out of scope and remains a separate future workstream.

Global status remains `morphology_replication_not_yet_accepted`; operational baseline remains v0.4.3.
