# v0.6.4 Preanalysis — ordinal0 predecessor-supported raw projection

Date: 2026-09-06

Status: **written after v0.6.3 adjudication and before any v0.6.4 repair replay output is read**.

## 1. Prior evidence

v0.6.3 closed with `ordinal0_extrapolated_left_bound_exclusion` as the dominant canonical-1m residual mechanism:

- all residuals: `4659 / 6840 = 68.11%`;
- v0.6.1 post-tuple target residuals: `112 / 122 = 91.80%`;
- exact ties at the first displaced canonical-1m anchor: only `82 / 6840 = 1.20%`;
- `mutual_window_overlap_extreme_competition = 0`.

The current first raw support lower bound is synthetic:

```text
left = max(0, 2*f0 - f1)
```

where `f0/f1` are occurrence **bar indices in the current supplied 5m view**.

By contrast, after ordinal0 the current projection lower bound is not extrapolated: each later phase starts immediately after the preceding selected raw extremum.

## 2. Structural observation

At the exact-ridge tuple-birth scale, the five tuple nodes are consecutive parent ridges. Unless the tuple is genuinely left-censored at the available history edge, the birth-level ridge list also contains a real filtered extremum immediately preceding `f0`.

That predecessor is a pre-existing single-view causal object. It is not inferred from another offset, from 1m data, from D1/D2, or from outcomes.

Therefore the narrow repair hypothesis is:

> ordinal0 should begin after the real preceding filtered phase boundary at the same tuple-birth scale, rather than after an index-space mirror of `f0 -> f1`.

## 3. Only registered repair candidate

Candidate name:

`birth_scale_predecessor_filtered_phase_start`

For one exact-ridge tuple birth at level `L` with nodes `f0..f4`:

1. locate the tuple's five ridge nodes in the complete ordered `ridge_nodes_by_level[L]` list;
2. require them to occupy five consecutive positions and preserve the frozen tuple identity;
3. if a preceding ridge node exists at position `pos(f0)-1`, require its kind to be the opposite of `f0.kind` and require it to be confirmed no later than the tuple birth confirmation;
4. set ordinal0 raw-search lower bar to `predecessor.occurrence_index + 1`;
5. keep ordinal0 upper bound exactly `f1 - 1`;
6. keep ordinals1..4 exactly unchanged from frozen `project_event_to_raw`, including their recursive lower bounds and ordinal4 confirmation upper bound;
7. use the same raw close, same max/min rule and same last-exact-tie rule.

If no valid birth-scale predecessor exists, return explicit audit status `ordinal0_left_censored_no_predecessor`. **Do not fall back to the old mirror rule.**

No other candidate is permitted in v0.6.4.

## 4. Why this candidate is admissible before replay

It removes a synthetic boundary using information already present in the frozen parent representation. It does not introduce a fitted duration, tolerance, volatility measure, return label, direction label, other-view information, or 1m runtime dependency.

It is also minimal: only ordinal0 lower support changes. This matters because v0.6.3 separately found `sequential_lower_bound_exclusion = 20.51%`; changing ordinals1..4 in the same experiment would confound the two mechanisms.

## 5. Required invariants

Before financial replay, synthetic/unit tests must establish:

1. **single-view only** — candidate uses only the current view's frozen ridge birth, ridge-level predecessor and raw bars;
2. **causal predecessor** — predecessor confirmation must not exceed tuple-birth confirmation;
3. **prefix immutability** — appending bars after tuple-birth confirmation cannot rewrite the candidate raw identity;
4. **no mirror fallback** — absence of predecessor is explicit left censoring;
5. **ordinal isolation** — with the same selected ordinal0 raw extremum, ordinals1..4 are byte-for-byte/output-equivalent to frozen projection semantics;
6. **tie rule unchanged** — exact max/min ties still select the last occurrence;
7. **no future/outcome authority** — no D1/D2/PAWCT/return/outcome/trade field enters selection.

## 6. Financial replay universe

Primary universe remains the v0.6.2 mutual-unique canonical filtered-tuple pairs across offset0 vs offset1..4. Candidate identity is evaluated before qualification; it is not allowed to change tuple matching.

Report separately:

- all filtered-tuple strict pairs;
- the v0.6.2 raw-displaced stratum;
- the v0.6.3 6,840 canonical-1m residual stratum;
- the v0.6.1 787 projection-displacement target cases and the 122 target residual subset.

## 7. Frozen evaluation metrics

For each view:

- candidate projection-valid / left-censored / other-invalid counts;
- within-view canonical filtered identity -> candidate raw identity single-valuedness.

For each offset pair:

- mutual-unique filtered-tuple pair count unchanged;
- candidate raw strict match / displaced / invalid counts under the unchanged same-phase five-anchor `<=5m` evaluator;
- comparison to frozen current projection on exactly the same pair universe;
- ordinal-specific displacement counts;
- canonical-1m diagnostic using the candidate's own absolute windows, audit-only;
- no cross-view tie-break.

For the v0.6.3 residual and v0.6.1 target strata, report how many cases are repaired, unchanged, newly broken, or unavailable. `repaired` means candidate raw identity passes the unchanged strict relation where the frozen current projection failed; it does not mean morphology accepted.

## 8. Guard against result-driven scope creep

v0.6.4 may not:

- alter `f1-1`, `f2-1`, `f3-1`, `f4-1`, or ordinal4 confirmation upper support;
- alter the recursive lower bounds for ordinals1..4;
- use window intersection across views;
- use `1m_official` as production/runtime input;
- tune a predecessor distance or tolerance;
- choose between multiple predecessors;
- modify ridge linking/death certification/tuple births;
- change v0.5.4 qualification thresholds;
- modify D1/D2/PAWCT;
- inspect returns/outcomes/P&L.

## 9. Interpretation boundary

This is a repair **POC**, not a baseline promotion.

If predecessor support materially improves financial-identity stability across all four offsets without introducing multi-valued identities or substantial censoring/new breaks, cloud may next audit its downstream qualification consequences in a separately frozen experiment.

If it fails or produces mixed behavior, v0.6.4 ends without inventing a second candidate after seeing results. Sequential-lower support remains a separate future workstream.

Global status remains `morphology_replication_not_yet_accepted` and operational baseline remains v0.4.3.
