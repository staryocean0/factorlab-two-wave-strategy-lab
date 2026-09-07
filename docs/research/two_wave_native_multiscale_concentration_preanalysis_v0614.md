# v0.6.14 Preanalysis — native multiscale/refinement-aware concentration representation

Date: 2026-09-07

Status: **WRITTEN BEFORE ANY v0.6.14 REAL-DATA OUTPUT IS READ**

## 1. Why v0.6.14 is required

v0.6.13 showed that explicit step-count normalization removes much of raw max-share's mechanical duration bias, but native 5m and supplied-1m concentration profiles still differ materially. Therefore the remaining problem is not a missing scalar normalization; it is the hidden refinement structure inside native bars.

v0.6.14 does not fit native data to J1 and does not estimate a correction coefficient. It asks whether native data can expose its own **sampling/refinement sensitivity** by observing how concentration changes under deterministic further coarsening.

## 2. Frozen native-only construction

For one published native-5m close path with point indices `0..m`, keep endpoints `0` and `m` fixed.

For each stride `s in {1,2,3,4}` and each phase `r in {0,...,s-1}`:

- include endpoint indices 0 and m;
- include every interior index `i` satisfying `i mod s = r`;
- sort/deduplicate;
- compute movement magnitudes between selected closes;
- compute the frozen v0.6.13 `(C_inf,C_1,C_2)` profile when at least two movements and positive total movement exist.

This uses only the already-published native leg and no 1m/counterpart/future information.

## 3. Registered multiscale response

For each component and stride report all phase values plus:

```text
phase_median_s = median of defined phase values
phase_range_s  = max - min of defined phase values
```

Registered native response coordinates are the full fixed set:

```text
native_value = phase_median_1
coarsening_delta_2 = phase_median_2 - native_value
coarsening_delta_3 = phase_median_3 - native_value
coarsening_delta_4 = phase_median_4 - native_value
phase_range_2
phase_range_3
phase_range_4
```

No weighted combination, regression, best stride, best phase or post-hoc dropping is allowed.

## 4. Frozen questions

Without fitting, answer:

1. Are native coarsening response coordinates stable across frozen strict same-event slicer pairs?
2. Does magnitude of native coarsening response rank-track the actual native→fine profile gap observed with supplied 1m?
3. Do native phase ranges rank-track supplied-1m five-origin profile ranges?
4. Is any relationship consistent across `C_inf/C_1/C_2`, step-count bins and frozen target strata?
5. Does the response retain useful information beyond native step count alone?

## 5. Fine/origin oracle firewall

Supplied 1m is audit-only. It may provide:

- fine `C_inf/C_1/C_2` on the same absolute leg;
- native→fine absolute profile gap;
- supplied-1m five-origin phase range from v0.6.13 semantics.

None of these values may enter the native response function.

## 6. Primary descriptive associations

For each component report Spearman associations between:

- `abs(coarsening_delta_2/3/4)` and native→fine absolute gap;
- `phase_range_2/3/4` and native→fine absolute gap;
- `phase_range_2/3/4` and fine five-origin range;
- same native coordinates and native step count.

No correlation cutoff is introduced.

## 7. Cross-slicer audit

On frozen 29,453 strict same-event pairs, report absolute counterpart differences for every registered native response coordinate, per offset and aggregate.

Also retain native v0.6.13 profile and fine profile cross-slicer differences as references only.

## 8. Step-count bins and availability

Use frozen bins `1-3`, `4-5`, `6-11`, `12-23`, `24+` native movements. Report defined phase counts and response distributions. Short legs remain explicit unavailable where a stride/phase cannot produce two movements.

No availability threshold is fitted.

## 9. Frozen strata

Repeat key response/oracle associations for:

- 482 both-qualified pairs;
- 699 qualification-disagreement pairs;
- 80 target repaired pairs;
- 56 target agreement / 24 target disagreement.

No stratum may redefine the native response.

## 10. Synthetic gates

Tests must prove:

1. stride/phase index construction is deterministic and endpoint preserving;
2. stride 1 reproduces the original v0.6.13 profile;
3. phase labels merely enumerate fixed subpartitions; no best phase selection exists;
4. future append after the published endpoint cannot change the response;
5. positive price scaling leaves profile coordinates unchanged;
6. short/zero-movement subpartitions remain explicit undefined;
7. native response API has no 1m/counterpart/direction/outcome input.

## 11. Allowed adjudications

Only:

- `native_coarsening_response_tracks_refinement_uncertainty_for_next_poc`;
- `native_multiscale_response_is_stable_but_not_informative_of_fine_refinement`;
- `native_multiscale_response_remains_slicer_sensitive_and_uninformative`;
- `mixed_native_multiscale_evidence_requires_more_audit`.

No positive result creates a qualification threshold or production input.

## 12. Global firewall

Global state remains `morphology_replication_not_yet_accepted`; operational baseline remains v0.4.3.

No fitted mapping to J1, duration correction, qualification threshold, matcher/projection/publication change, roughness re-optimization, direction/D1/D2/PAWCT, third-wave, outcomes/P&L, fresh OOS, paper trading or production is allowed.
