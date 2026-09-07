# v0.6.14 Frozen protocol — native multiscale/refinement-aware concentration audit

Date: 2026-09-07

Status: **FROZEN BEFORE ANY v0.6.14 REAL-DATA OUTPUT IS READ**

This audit changes no qualification rule, threshold, identity, matcher, projection, publication, roughness candidate, direction, outcome or trading logic.

## 1. Hard controls

Reproduce exactly before interpretation:

```text
published identities = 38,176 / 36,737 / 36,619 / 36,480 / 36,264
published raw strict pairs = 8,381 / 5,770 / 6,204 / 9,098 = 29,453
both-qualified = 482
qualification disagreements = 699
target repaired = 80 = 56 agreement + 24 disagreement
```

Retain v0.6.13 references:

```text
native profile defined = 664,001 published legs
fine profile defined = 737,070
both native+fine = 663,972
raw |J5-J1| gap vs native step-count Spearman = -0.8840933565
C_inf/C_1/C_2 gap vs step-count Spearman = 0.1736718801 / -0.2228458477 / -0.0359650963
```

Any drift stops interpretation.

## 2. Native-only subpartition construction

For one closed native path of point indices `0..m`, for every `stride s in {1,2,3,4}` and phase `r in {0,...,s-1}`:

- always include points `0` and `m`;
- include interior point `i` iff `i mod s == r`;
- sort and deduplicate;
- compute movement magnitudes between selected closes;
- compute v0.6.13 `C_inf/C_1/C_2` if at least two movements and positive total movement exist.

No 1m data or counterpart information is accepted by the registered native function.

## 3. Registered outputs

For every component and stride:

```text
phase_values_s
phase_median_s
phase_range_s
defined_phase_count_s
```

Registered response coordinates:

```text
native_value = phase_median_1
delta_s = phase_median_s - native_value  for s=2,3,4
range_s = phase_range_s                 for s=2,3,4
```

No best stride/phase or weighted scalar is permitted.

## 4. Fine-oracle diagnostics

Using supplied 1m only outside the native function, retain:

- fine `C_inf/C_1/C_2`;
- absolute native→fine profile gap;
- supplied-1m five-origin profile ranges.

Report Spearman for each component between:

```text
abs(delta_2/3/4) vs native→fine abs gap
range_2/3/4       vs native→fine abs gap
range_2/3/4       vs fine five-origin range
```

Also report each native response coordinate vs native step count.

No fitted mapping.

## 5. Cross-slicer audit

On frozen 29,453 strict pairs, align corresponding legs and report absolute counterpart differences for all registered `delta_s` and `range_s`, per offset and aggregate.

Retain native/fine v0.6.13 profile difference as references only.

## 6. Step-count bins

Use only `1-3`, `4-5`, `6-11`, `12-23`, `24+`. Report availability and median response by bin. No bin-specific correction.

## 7. Frozen strata

Repeat key oracle associations and cross-slicer response summaries for:

```text
both-qualified = 482
qualification-disagreement = 699
target repaired = 80
target agreement = 56
target disagreement = 24
```

Descriptor definition never changes.

## 8. Synthetic gates

Tests must prove:

1. exact deterministic index sets for strides 1..4 and all phases;
2. endpoints are always present once;
3. stride-1 profile equals direct v0.6.13 profile;
4. no phase-selection/ranking function exists;
5. future append outside closed input cannot change output;
6. positive price scaling preserves concentration coordinates;
7. short/zero movement partitions remain explicit undefined;
8. native API contains no 1m/counterpart/direction/outcome dependency.

## 9. Required outputs

Write compact evidence to:

`cloud_results/cloud_chat_v0614_native_multiscale_concentration/`

Required:

```text
summary.json
native_response.json
oracle_associations.json
cross_slicer_response.json
step_count_overlay.json
strata_overlays.json
data_identity.json
execution_receipt.json
```

## 10. Allowed adjudications

Only:

- `native_coarsening_response_tracks_refinement_uncertainty_for_next_poc`;
- `native_multiscale_response_is_stable_but_not_informative_of_fine_refinement`;
- `native_multiscale_response_remains_slicer_sensitive_and_uninformative`;
- `mixed_native_multiscale_evidence_requires_more_audit`.

## 11. Global firewall

`morphology_replication_not_yet_accepted` remains unchanged. Operational baseline remains v0.4.3.

No fitted mapping to J1, duration correction, qualification threshold, matcher/projection/publication change, roughness re-optimization, direction/D1/D2/PAWCT, third-wave, outcomes/P&L, fresh OOS, paper trading or production is allowed.
