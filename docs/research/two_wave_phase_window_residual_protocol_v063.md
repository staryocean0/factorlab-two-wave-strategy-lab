# v0.6.3 Frozen protocol — phase-window semantics residual audit

Date: 2026-09-06

Status: **FROZEN BEFORE ANY v0.6.3 RESIDUAL-DETAIL OUTPUT IS READ**

This protocol inherits v0.6.2 and changes no recognizer, projection, ridge, tuple birth, qualification, matcher, direction, packing, outcome, or trading logic.

## 1. Primary population

For offset0 vs each offset1..4, start from the v0.6.2 mutual-unique canonical filtered-tuple universe and retain only pairs that satisfy all of:

1. both groups have exactly one valid raw projection identity;
2. current 5m raw identities fail the unchanged same-phase five-anchor `<=5m` relation;
3. applying each side's **unchanged existing absolute projection windows** to the supplied `1m_official` path yields five valid canonical-path anchors on both sides;
4. those two 1m diagnostic five-anchor tuples still fail the unchanged `<=5m` relation.

Frozen expected residual counts from v0.6.2:

```text
offset1: 1,578
offset2: 1,738
offset3: 1,806
offset4: 1,718
aggregate: 6,840
```

The v0.6.1 post-tuple target residual controls are:

```text
offset1: 32
offset2: 28
offset3: 30
offset4: 32
aggregate: 122
```

Any drift stops interpretation.

## 2. Frozen canonical path

Only supplied `data/development/1m_official.parquet` may be used for canonical-path diagnostics. No resampling, interpolation, forward fill, or synthetic bars.

For each existing 5m projection window, select the expected max/min close from 1m rows inside its closed absolute-time interval, with exact ties broken by the existing `last_argextreme` rule.

## 3. Earliest displaced ordinal

For every residual pair, compare the two canonical-1m selected anchor timestamps position-wise. Let `k` be the first ordinal whose absolute delta exceeds 5 minutes.

Primary attribution is determined **only at ordinal `k`**. Later ordinals are overlays and cannot overwrite the primary category.

## 4. Boundary-exclusion evidence at ordinal k

For side A selected canonical time `tA` and side-B window `[LB, UB]`:

- `A_before_B_lower` iff `tA < LB`;
- `A_after_B_upper` iff `tA > UB`.

Define the symmetric two flags for `tB` against side-A window.

`lower_exclusion_present` is true if either selected time is earlier than the other side's lower bound.

`upper_exclusion_present` is true if either selected time is later than the other side's upper bound.

## 5. Frozen primary attribution order

At the earliest displaced ordinal `k`, use exactly this order:

0. `mixed_lower_upper_exclusion`
   - both lower and upper exclusion are present.

1. `ordinal0_extrapolated_left_bound_exclusion`
   - `k == 0`, lower exclusion present, upper exclusion absent.

2. `filtered_predecessor_upper_bound_exclusion`
   - `k < 4`, upper exclusion present, lower exclusion absent.

3. `sequential_lower_bound_exclusion`
   - `k > 0`, lower exclusion present, upper exclusion absent.

4. `confirmation_tail_upper_bound_exclusion`
   - `k == 4`, upper exclusion present, lower exclusion absent.

5. `mutual_window_overlap_extreme_competition`
   - neither lower nor upper exclusion is present; both side-selected canonical 1m anchors lie within the other side's window, but the selected times still differ by >5m.

Exactly one primary attribution must be assigned to every residual pair. No nearest/best tie-break is allowed.

## 6. Source-semantics overlays

For the earliest displaced ordinal record, also store:

- both lower/upper absolute times;
- lower-bound and upper-bound absolute deltas;
- both canonical selected 1m times and closes;
- whether each selected time lies in the other window;
- exact 1m extreme tie counts;
- filtered occurrence times for the current ordinal and next ordinal when applicable;
- prior selected raw/1m times when `k > 0`;
- ordinal4 member-confirmation times when `k == 4`.

These are descriptive and may not change the primary category.

## 7. Session-gap overlay

Use Shanghai cash-session boundaries expressed in UTC:

- 09:30 = 01:30 UTC
- 11:30 = 03:30 UTC
- 13:00 = 05:00 UTC
- 15:00 = 07:00 UTC

For the earliest displaced ordinal, report:

- `lunch_gap_straddled`: one side's corresponding lower or upper boundary lies at/before 03:30 UTC and the other side's same boundary lies at/after 05:00 UTC on the same Shanghai trading date;
- `overnight_gap_straddled`: corresponding bounds fall on different Shanghai trading dates or one side is at/after 07:00 UTC while the other is at/before 01:30 UTC of the next observed trading date;
- `session_boundary_nearby`: any relevant bound is within one nominal 5m bar of 01:30/03:30/05:00/07:00 UTC.

These are overlays only; they do not remove observations.

## 8. Sequential-propagation overlay

For `k > 0`, report whether the two current lower bounds differ because the previous ordinal's selected 5m raw occurrences differ, and whether the 1m residual displaced ordinals form a suffix from `k`.

Do not infer causality merely from suffix structure.

## 9. Cross-view window-intersection diagnostic

At every residual ordinal, compute the closed intersection:

`[max(LA, LB), min(UA, UB)]`.

If the intersection contains at least one supplied 1m row, project the expected max/min close on that intersection using the same exact tie rule.

Report:

- intersection available yes/no;
- intersection anchor time/close/tie count;
- distance from the intersection anchor to side-A and side-B canonical selected times;
- whether the intersection anchor is within `<=5m` of both selections.

**The intersection anchor is diagnostic only. It is not a candidate runtime projection in v0.6.3.**

## 10. Target-stratum reporting

Repeat all summary metrics separately for the 122 v0.6.1 post-tuple residual cases. The frozen counts 32/28/30/32 must reproduce before interpretation.

## 11. Required outputs

Write compact outputs to:

`cloud_results/cloud_chat_v063_phase_window_residual_audit/`

Required:

```text
summary.json
pair_offset_1.json
pair_offset_2.json
pair_offset_3.json
pair_offset_4.json
v061_target_residual_summary.json
data_identity.json
execution_receipt.json
```

Large per-pair details may remain runtime-local; if needed for review, save a compact deterministic sample keyed by identity IDs, never selected by outcome.

## 12. Summary metrics

At minimum report:

- residual hard-control counts;
- first canonical-1m displaced ordinal distribution;
- primary attribution counts/fractions per offset and aggregate;
- lower/upper exclusion rates by ordinal;
- 1m exact-tie involvement;
- session-gap overlay by attribution;
- sequential-propagation overlay;
- window-intersection availability and `<=5m of both` rates;
- same metrics for the v0.6.1 target residual stratum;
- `future_outcome_used=false`;
- `trade_authority=false`;
- `morphology_status=morphology_replication_not_yet_accepted`.

## 13. Interpretation rule

No new numerical promotion threshold is set after seeing results.

Cloud may only identify which existing support semantic is materially responsible across all four offsets and therefore merits a **separately frozen repair preanalysis**.

- dominance of ordinal0-left support may justify studying absolute-time left support invariants;
- dominance of predecessor-upper support may justify studying absolute-time phase-boundary invariants;
- dominance of sequential-lower support may justify studying non-recursive per-phase support;
- dominance of confirmation-tail support may justify separating filtered e4 morphology support from confirmation timing;
- mixed results require separate workstreams.

No v0.6.3 result authorizes changing `project_event_to_raw` in the same experiment.