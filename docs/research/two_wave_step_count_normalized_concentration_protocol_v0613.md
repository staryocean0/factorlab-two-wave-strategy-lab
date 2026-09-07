# v0.6.13 Frozen protocol — step-count / resolution-normalized concentration profile audit

Date: 2026-09-07

Status: **FROZEN BEFORE ANY v0.6.13 REAL-DATA OUTPUT IS READ**

This audit changes no qualification rule, threshold, identity, matcher, projection, publication, direction, outcome or trading logic.

## 1. Hard controls

Before interpretation reproduce exactly:

```text
published identities = 38,176 / 36,737 / 36,619 / 36,480 / 36,264
published raw strict pairs = 8,381 / 5,770 / 6,204 / 9,098
aggregate strict pairs = 29,453
v0.6.6 both-qualified = 482
v0.6.6 qualification disagreements = 699
v0.6.1 target repaired = 80 = 56 agreement + 24 disagreement
```

On the v0.6.10 oracle-comparable pair-leg universe reproduce:

```text
pair-leg observations = 117,805
native J5 abs-diff median = 0.053931031782781566
fine J1 abs-diff median = 0.0064740520975389015
origin-jump-median abs-diff median = 0.016957546216696373
```

Any drift stops interpretation.

## 2. Movement-weight profile

For one movement sequence `x_i >= 0`, let `n=len(x)`, `S=sum(x)`, `w_i=x_i/S`.

Require `n>=2` and `S>0`; otherwise all profile components are undefined. No epsilon replacement.

Registered profile:

```text
C_inf = log(n * max(w))
C_1   = log(n) + sum_{w_i>0} w_i log(w_i)
C_2   = log(n * sum(w_i^2))
```

All three components must remain reported. No weighted combination, winner selection, PCA or learned score.

## 3. Frozen movement primitives

Native path:

```text
x5 = abs(diff(native 5m close))
```

Fine audit path:

```text
x1 = abs(diff(supplied 1m close))
```

Both use the same published leg absolute interval as prior versions. No resampling, interpolation, fill, smoothing or synthetic prices.

Native true-range concentration from v0.6.12 is descriptive only and cannot be promoted in v0.6.13.

## 4. Exact invariance gates

For arbitrary positive movement vector `x` and integer `k>=1`, uniformly split each `x_i` into `k` children `x_i/k`.

Assert within `1e-12` arithmetic guard only:

```text
C_inf(split_k(x)) == C_inf(x)
C_1(split_k(x))   == C_1(x)
C_2(split_k(x))   == C_2(x)
```

Also assert positive-scale invariance `C(a*x)==C(x)` for `a>0`.

These are mathematical properties, not empirical thresholds.

## 5. Cross-resolution audit

For every side-leg with native and fine profiles defined, report separately for `C_inf/C_1/C_2`:

- native distribution;
- fine distribution;
- signed native-minus-fine distribution;
- absolute gap distribution;
- Spearman(native,fine);
- Spearman(abs gap, native step count).

Raw `|J5-J1|` vs step count remains a descriptive control only. Descriptor units must not be mixed in a scalar comparison.

## 6. Duration / step-count bins

Use only the already frozen native step-count bins:

```text
1-3, 4-5, 6-11, 12-23, 24+
```

For each component report median native→fine absolute gap and native/fine medians by bin.

No fitted correction, regression, interpolation or duration-specific normalization may be created.

## 7. Cross-slicer audit

On the frozen 29,453 strict same-event pair universe, align corresponding legs by ordinal and report absolute counterpart differences for:

- native J5 control;
- native `C_inf/C_1/C_2`;
- fine `C_inf/C_1/C_2`.

Per offset and aggregate summaries must include count/min/median/p90/p99/max/mean.

No stability cutoff is introduced.

## 8. Origin-refinement audit

Using supplied 1m only as audit material, construct the same five deterministic 5m-origin subsamples as v0.6.10. For each defined origin compute `C_inf/C_1/C_2`.

Report per component:

```text
origin_median
origin_range
fine_minus_origin_median
```

Aggregate report origin-range distribution and Spearman between origin range and absolute native-vs-fine profile gap.

This is audit-only and cannot enter runtime.

## 9. Redundancy / complementarity

Report Spearman associations among `C_inf/C_1/C_2` separately on native and fine legs, aggregate and by the frozen step-count bins.

No component may be dropped after results.

## 10. Frozen strata

Repeat key cross-resolution and cross-slicer summaries for:

```text
both-qualified = 482 pairs
qualification-disagreement = 699 pairs
target-repaired = 80 pairs
target agreement = 56
target disagreement = 24
```

Strata cannot change descriptor definition.

## 11. Synthetic gates

Tests must prove:

1. uniform positive movements give all three components zero;
2. nonuniform movements give nonnegative components with at least one positive;
3. exact uniform-subdivision invariance for multiple `k` values;
4. positive scale invariance;
5. zeros inside a positive-sum vector are handled by Shannon convention `0 log 0 = 0`;
6. zero-sum and `n<2` are explicit undefined;
7. future append outside the supplied closed leg cannot enter profile calculation;
8. primitive profile API accepts only one movement vector and contains no 1m/counterpart/direction/outcome dependency.

## 12. Required outputs

Write compact outputs to:

`cloud_results/cloud_chat_v0613_step_count_normalized_concentration/`

Required:

```text
summary.json
cross_resolution_profile.json
step_count_overlay.json
cross_slicer_profile.json
origin_refinement.json
component_associations.json
strata_overlays.json
data_identity.json
execution_receipt.json
```

## 13. Allowed adjudications

Only:

- `renyi_concentration_profile_is_structurally_resolution_coherent_for_next_poc`;
- `step_count_normalization_reduces_duration_bias_but_not_cross_resolution_gap`;
- `normalized_profile_remains_materially_resolution_dependent`;
- `mixed_normalized_concentration_evidence_requires_more_audit`.

A positive result authorizes only a later separately frozen property POC. It creates no qualification rule, threshold or production input.

## 14. Global firewall

Global state remains `morphology_replication_not_yet_accepted`; operational baseline remains v0.4.3.

No fitted duration correction, qualification threshold, matcher/projection/publication change, roughness re-optimization, direction/D1/D2/PAWCT, third-wave, outcomes/P&L, fresh OOS, paper trading or production is allowed in v0.6.13.
