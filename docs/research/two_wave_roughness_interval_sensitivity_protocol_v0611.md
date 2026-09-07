# v0.6.11 Frozen protocol — endpoint-robust roughness interval-sensitivity audit

Date: 2026-09-07

Status: **FROZEN BEFORE ANY v0.6.11 REAL-DATA OUTPUT IS READ**

This audit changes no qualification rule, threshold, identity, matcher, projection, publication, direction, outcome or trading logic.

## 1. Hard controls

Before interpreting any v0.6.11 result, reproduce exactly:

```text
published identities = 38,176 / 36,737 / 36,619 / 36,480 / 36,264
published raw strict pairs = 8,381 / 5,770 / 6,204 / 9,098
aggregate strict pairs = 29,453
v0.6.6 both-qualified = 482
v0.6.6 qualification disagreements = 699
v0.6.1 target repaired = 80
  agreement = 56
  disagreement = 24
```

Reproduce the v0.6.10 aggregate fine-roughness reference on the same comparable pair-leg universe when available:

```text
pair-leg observations = 117,805
fine_roughness abs-diff median = 0.0831451887861357
fine_roughness abs-diff p90    = 0.39279613781110223
native_roughness abs-diff median = 0.021657587163696427
```

If the v0.6.10 comparable universe changes because of a documented availability implementation difference, stop and reconcile before interpretation.

## 2. Data

Use only the same frozen inputs as v0.6.10:

- five native 5m development views;
- supplied `data/development/1m_official.parquet`;
- date range 2015-01-05 through 2020-12-31;
- no post-2020 rows;
- no resampling, interpolation, fill or synthetic prices.

## 3. Fine roughness

For a supplied-1m close sequence `y` on one closed interval:

```text
TV = sum(abs(diff(y)))
D = abs(y[-1] - y[0])
R = log(TV / D)  if TV>0 and D>0
```

If undefined, return `None`. Do not add epsilon.

## 4. Registered erosion ensemble

For one published leg `[t0,t1]` independently:

Enumerate all 25 fixed inward shifts `(s,e)` for `s,e ∈ {0,1,2,3,4}` minutes.

Candidate interval:

```text
[t0 + s minutes, t1 - e minutes]
```

A cell is defined only if:

- both shifted timestamps exist exactly in supplied 1m rows;
- shifted start < shifted end;
- at least two supplied rows lie in the closed interval;
- TV>0 and D>0.

Registered single-view descriptor:

```text
erosion_roughness_median
erosion_roughness_range
erosion_defined_count
```

No cell is selected as best. No counterpart information enters this function.

## 5. Exact pair decomposition

For counterpart original intervals A/B, when both roughness values are defined, compute:

```text
delta_R = R_A - R_B
delta_log_TV = log(TV_A) - log(TV_B)
delta_log_D = log(D_A) - log(D_B)
identity_error = delta_R - (delta_log_TV - delta_log_D)
```

Require `abs(identity_error) <= 1e-12` as arithmetic guard only.

No dominance classifier is created.

## 6. Common-support oracle

Define:

```text
common_start = max(start_A,start_B)
common_end = min(end_A,end_B)
```

If exact supplied 1m rows are available and interval is valid, compute common-support roughness plus each side's deviation from it.

Common support uses counterpart information and is **audit-only**. It may never be used as the registered single-view candidate or later runtime without a new protocol.

## 7. Boundary-sliver diagnostics

For each side, when defined, record original vs `(4,0)`, `(0,4)`, `(4,4)` roughness and:

```text
left_removed_TV_fraction
right_removed_TV_fraction
both_removed_TV_fraction
left_displacement_change
right_displacement_change
both_displacement_change
```

Use only supplied 1m rows. No weighted combination.

## 8. Decisive cross-slicer comparison

On frozen strict same-event pairs and corresponding leg ordinal, compare only observations for which both counterpart original fine roughness and both counterpart erosion medians are defined.

For original `fine_roughness` and candidate `erosion_roughness_median`, report per offset and aggregate:

- count;
- min, median, p90, p99, max, mean absolute pair difference;
- paired sign count candidate smaller / equal / larger than original fine-roughness difference.

No new tolerance or stability cutoff.

Also report `erosion_roughness_range` pair differences and per-leg range distribution as uncertainty diagnostics.

## 9. Availability

Report:

- defined-cell count distribution 0..25;
- pair-leg count retained by the decisive comparison;
- exact reasons for undefined cells (missing shifted timestamp, interval collapse, zero TV, zero displacement).

No availability threshold may be invented after results.

## 10. Frozen strata

Repeat the decisive registered comparison for:

```text
both-qualified strict pairs = 482
qualification-disagreement pairs = 699
target-repaired = 80
target-agreement = 56
target-disagreement = 24
```

Descriptor definition never changes by stratum.

## 11. Synthetic gates

Tests must prove:

1. roughness formula;
2. pair decomposition identity;
3. exactly 25 deterministic erosion cells are attempted;
4. all shifts are inward only;
5. missing exact minute stays unavailable;
6. zero-TV / zero-displacement is explicit undefined;
7. future append after original end does not alter candidate;
8. candidate does not require counterpart data;
9. common support is a separately named audit-only helper.

## 12. Required outputs

Write compact outputs to:

`cloud_results/cloud_chat_v0611_roughness_interval_sensitivity/`

Required:

```text
summary.json
per_view_roughness.json
erosion_availability.json
pair_decomposition.json
common_support_oracle.json
boundary_slivers.json
strata_overlays.json
data_identity.json
execution_receipt.json
```

## 13. Allowed adjudications

Only:

- `endpoint_erosion_ensemble_materially_reduces_roughness_interval_sensitivity`;
- `common_support_confirms_boundary_effect_but_erosion_not_sufficient`;
- `roughness_instability_is_not_reliably_reduced_by_registered_erosion`;
- `mixed_interval_sensitivity_requires_more_audit`.

No v0.6.11 result creates a qualification rule or threshold.

## 14. Deferred workstream

Native-5m deployable proxy/error-bound research for fine concentration/origin ensemble is **out of scope** and must be a separate later version.

## 15. Global firewall

`morphology_replication_not_yet_accepted` remains unchanged. Operational baseline remains v0.4.3.

Direction/D1/D2/PAWCT, third-wave, outcomes/P&L, fresh OOS, paper trading and production remain frozen.
