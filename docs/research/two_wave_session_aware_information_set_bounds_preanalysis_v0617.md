# v0.6.17 Preanalysis — session-aware information-set bounds from authoritative DataHub support topology

Date: 2026-09-07

Status: **WRITTEN RESULTS-BLIND AFTER DataHub INTAKE ACCEPTANCE AND BEFORE ANY v0.6.17 REAL-DATA BOUND OUTPUT IS READ**

DataHub intake adjudication:

`authoritative_archive_copy_accepted`

Global state remains `morphology_replication_not_yet_accepted`; operational baseline remains v0.4.3.

## 1. Why v0.6.17 exists

v0.6.15 asked whether fine 1m movement concentration is identifiable from native 5m OHLC without fitting another proxy. Its outer-bound mathematics passed synthetic gates, but its data model failed because it treated every adjacent native close pair as one complete five-step native bar.

That assumption is false for session-offset products. In offset1–4, source minutes can be deliberately discarded at session edges. An adjacent native-close transition can therefore include source rows that belong to no current native 5m bar. v0.6.15 incorrectly forced those rows into the current bar's `[low,high]` envelope.

v0.6.16 then stopped the work until the DataHub support contract could be recovered. `CL-20260907-004` supplied an immutable DataHub contract/implementation archive, and the cloud intake review accepted it.

v0.6.17 changes **only the information-set topology**. It does not introduce a new morphology proxy, threshold, recognizer, matcher or qualification rule.

## 2. Authoritative support object

For each native 5m bar `b`, define:

```text
S_b = ordered set of actual DataHub 1m source rows assigned to bar b
```

Assignment is determined by the accepted DataHub construction contract at period=5:

- offset0 uses the official session-end-label v2 path;
- offset1–4 use the additive wall-clock-offset v1 path;
- morning and afternoon are independent sessions;
- no lunch or overnight source rows are aggregated across a session boundary;
- wall-clock offset products can discard pre-grid and incomplete-tail source rows;
- actual occupancy can differ from nominal/intended occupancy because source minutes can be absent.

The bound function may consume **support topology only**: ordered source timestamps, membership, counts and gap flags tied to the accepted DataHub dataset identity. It may not consume fine prices, oracle concentration values, counterpart morphology, direction or outcomes.

## 3. No substitution of FactorLab `1m_official`

The accepted local DataHub source surface contains 349,923 rows for 2015-01-05..2020-12-31, while the FactorLab manifest records 350,561 rows in `data/development/1m_official.parquet`.

Therefore v0.6.17 must fail closed unless real replay uses either:

1. the exact accepted DataHub source/support topology; or
2. a separately frozen row-level bridge proving the exact correspondence between another supplied 1m surface and the accepted DataHub source rows.

A timestamp-nearby heuristic or local re-resampling is not a bridge.

## 4. Transition topology

Consider adjacent native bars inside a published leg. Let previous native close be `c0` and current native bar `b` have native OHLC `(O,L,H,C)`.

Let `S_b = (s_1,...,s_m)` be the actual source rows assigned to the current bar, with `m>=1` and last source close equal to native `C` under the data-identity gate.

Let:

```text
G_b = actual source rows after the previous native endpoint and before s_1
      that are not assigned to current bar b
```

`G_b` is about **source rows**, not wall-clock elapsed time. Lunch/overnight periods containing no source row do not themselves create `G_b`. Deliberately discarded trading source rows do.

Two transition classes are frozen:

### A. fully_enveloped_transition

```text
G_b is empty
```

All fine close observations after `c0` through `C` are source rows assigned to the current native bar. Their hidden closes are constrained by current `[L,H]`.

### B. contains_unenveloped_source_gap

```text
G_b is non-empty
```

At least one actual fine source close between native endpoints is not represented by current native OHLC. Those rows may not be forced into `[L,H]`, the previous bar envelope, or an empirically inferred envelope.

No transition or leg is deleted because it belongs to class B.

## 5. Variable-step covered-bar model

For a fully enveloped transition with `m = |S_b|`, represent the fine close path as:

```text
c0 -> z1 -> ... -> z_(m-1) -> C
```

where every hidden `z_i in [L,H]`.

This replaces the v0.6.15 hard-coded five-step assumption. In the accepted DataHub contract, `m` can be 1..6 in the frozen sample; the first complete wall-clock-offset bucket commonly has six 1m end labels.

### 5.1 Exact covered-transition TV bounds

For `m=1` there is no hidden close:

```text
TV_min = TV_max = |C-c0|
M_min  = M_max  = |C-c0|
```

For `m>=2`:

```text
TV_min = |C-c0|
```

and the exact maximum close-path total variation is obtained by enumerating the `2^(m-1)` vertices:

```text
z_i in {L,H}
```

because the objective is convex in each hidden coordinate on the box.

The lower bound on the largest step is:

```text
M_min = |C-c0| / m
```

For `m>=2`, a valid outer upper bound is:

```text
M_max = max(
  |L-c0|, |H-c0|,
  H-L,
  |L-C|, |H-C|
)
```

No fine/oracle close is used to construct these bounds.

## 6. Structural-gap rule

If a leg contains any `contains_unenveloped_source_gap` transition, v0.6.17 does **not** invent a finite OHLC envelope for the discarded rows.

For that complete leg, use only universal concentration bounds based on the exact actual fine step count `N` between its native endpoints:

```text
J_low  = 1/N
J_high = 1
```

for positive total variation.

The normalized concentration-profile bounds become the full simplex range:

```text
C_inf in [0, log(N)]
C_1   in [0, log(N)]
C_2   in [0, log(N)]
```

This is deliberately conservative. It keeps session-boundary legs in the research universe and records that native OHLC does not constrain the discarded source rows enough for a sharper guarantee.

Zero-total-variation cases remain explicitly undefined under the existing fine-concentration convention; they are not assigned an artificial concentration value.

## 7. Fully enveloped leg bounds

For a leg whose every transition is fully enveloped, let transition `j` contain `m_j` fine increments.

```text
N       = sum_j m_j
TV_low  = sum_j TV_min_j
TV_high = sum_j TV_max_j
M_low   = max_j M_min_j
M_high  = max_j M_max_j
```

Then:

```text
J_low  = max(1/N, M_low/TV_high)       if TV_high>0
J_high = min(1, M_high/TV_low)         if TV_low>0
         1                             otherwise
```

Transform to the frozen v0.6.13 concentration profile exactly as in v0.6.15:

```text
C_inf_low  = log(N*J_low)
C_inf_high = log(N*J_high)
```

`C_1/C_2` lower and upper bounds use the same probability-simplex extremizers already frozen in v0.6.15. No empirical shrinkage is allowed.

## 8. Support-topology and data-identity gates

Before any tightness interpretation, real replay must prove:

1. source dataset version, source kind, symbol and date role match the accepted DataHub lineage;
2. no 2021+ row is loaded;
3. every emitted frozen 5m label maps to exactly one non-empty `S_b`;
4. the authoritative support replay reproduces the frozen 5m label set for each offset with no extra/missing label;
5. aggregating each `S_b` reproduces the frozen native OHLC for every matching label;
6. the last source close in `S_b` equals native close;
7. all source closes in `S_b` lie within the native `[L,H]` envelope;
8. every source row between published-leg endpoints is classified exactly once as either assigned to some relevant `S_b`, an explicit unassigned `G_b`, or outside the leg interval under the authoritative source sequence;
9. support topology is derived without fine price values entering the bound API.

Any material failure stops interpretation.

## 9. Oracle-coverage gate

Only after bounds are constructed from native OHLC + support topology may supplied fine prices be used for validation.

For every oracle-comparable leg, verify:

- actual fine step count equals registered `N`;
- actual fine `J1` lies inside `[J_low,J_high]`;
- actual `C_inf/C_1/C_2` lie inside their registered bounds;
- class-B structural-gap legs are retained and covered by the universal interval, not dropped.

A coverage failure is a model/data bug, not permission to tune a bound.

## 10. Required descriptive outputs

Report, by view and overall:

- fraction/count of fully enveloped transitions;
- fraction/count of transitions with un-enveloped source gaps;
- fraction/count of fully enveloped legs;
- fraction/count of structural-gap legs receiving universal bounds;
- distribution of actual `m_j` and leg `N`;
- J and profile bound widths;
- normalized width `(upper-lower)/log(N)` for profile components when `N>1`;
- oracle position within non-degenerate bounds;
- coverage rate.

Do not hide universal-bound legs from aggregate width statistics.

## 11. Frozen overlays

Repeat descriptive outputs on the pre-existing frozen universes without changing membership:

- native transition-count bins `1-3`, `4-5`, `6-11`, `12-23`, `24+`;
- 29,453 strict same-event pairs;
- both-qualified 482;
- qualification-disagreement 699;
- target repaired 80;
- target agreement 56;
- target disagreement 24.

No stratum changes a bound or support classification.

## 12. Synthetic gates

Before real-data interpretation tests must prove:

1. generalized `2^(m-1)` vertex TV maximum matches brute force for `m=1..6`;
2. random feasible covered paths satisfy J/profile bounds for variable `m`;
3. any leg with an inserted un-enveloped gap receives the universal interval, never a current-bar envelope;
4. lunch/overnight with zero source rows does not create a fake gap;
5. discarded source rows do create `contains_unenveloped_source_gap`;
6. positive price scaling leaves all concentration bounds invariant;
7. future append outside a closed leg cannot rewrite support classification or bounds;
8. bound API rejects fine prices/oracle/counterpart/direction/outcome fields;
9. a mismatched source dataset identity fails closed.

## 13. Results interpretation

Allowed adjudications only:

- `session_aware_bounds_valid_and_ready_for_identifiability_interpretation`;
- `session_aware_bounds_valid_but_structural_gap_nonidentifiability_is_material`;
- `session_aware_bounds_cover_oracle_but_are_too_wide_for_identification`;
- `session_aware_bounds_fail_support_topology_or_oracle_coverage`;
- `mixed_identifiability_requires_more_audit`.

No result authorizes a fitted bound shrinkage or qualification threshold. A material structural-gap result means the slicer has genuinely discarded information; it is not permission to delete those legs.

## 14. Global firewall

No matcher/projection/publication/qualification change, roughness re-optimization, direction/D1/D2/PAWCT, third-wave, outcomes/P&L, fresh OOS, paper trading or production is authorized.

The only next step is to freeze the corresponding protocol and execute the support-identity-gated replay.
