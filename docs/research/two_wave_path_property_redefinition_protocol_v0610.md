# v0.6.10 Frozen protocol — threshold-free path-property redefinition audit

Date: 2026-09-07

Status: **FROZEN BEFORE ANY v0.6.10 PROPERTY-AUDIT OUTPUT IS READ**

This protocol changes no qualification rule, threshold, identity, matcher, projection, publication, direction, outcome or trading logic.

## 1. Hard controls

Reproduce v0.6.9 upstream controls before interpretation:

```text
published identities = 38,176 / 36,737 / 36,619 / 36,480 / 36,264
aggregate = 184,276
strict same-event pairs = 8,381 / 5,770 / 6,204 / 9,098
aggregate strict = 29,453
both-qualified = 482
qualification disagreement = 699
v0.6.1 target repaired = 80, including 24 disagreement
```

Any drift stops interpretation.

## 2. Input paths

For each v0.6.5 published raw leg:

- native path: supplied native-view close rows from published start anchor through published end anchor inclusive;
- fine path: supplied `1m_official` close rows in the same closed absolute-time interval;
- no interpolation, OHLC resampling, smoothing, filling or synthetic prices.

Legs with insufficient fine rows remain unavailable and are reported.

## 3. Base quantities

For each path sequence `y`:

```text
TV = sum(abs(diff(y)))
D  = abs(y[-1]-y[0])
M  = max(abs(diff(y)))
E  = D/TV if TV>0 else 0
J  = M/TV if TV>0 else 1
F  = mean(diff(y)==0)
```

All quantities are descriptive; no pass/fail is produced.

## 4. Registered property components

For each leg compute exactly:

```text
fine_roughness = log(TV1 / D)                  if D>0 and TV1>0
hidden_variation = log(TV1 / TV5)             if TV1>0 and TV5>0
fine_concentration = J1
max_step_refinement = log(M1 / M5)             if M1>0 and M5>0
```

No epsilon replacement is allowed for undefined logarithms. Undefined cases remain explicit.

## 5. Origin-ensemble construction

For each supplied 1m fine leg and each origin `r in {0,1,2,3,4}`:

1. include the exact published start and end 1m rows when available;
2. include every interior supplied 1m row whose integer UTC epoch-minute modulo 5 equals `r`;
3. sort by timestamp and deduplicate;
4. require at least two rows;
5. compute the same TV/J formulas on the resulting deterministic subsample.

No aggregation is performed. The five origin paths are sampling partitions of the supplied 1m close path.

Report:

```text
origin_log_tv_ratio_median
origin_log_tv_ratio_range
origin_jump_median
origin_jump_range
```

where each `log_tv_ratio_r = log(TV1/TV5_r)` for defined positive TV values.

If fewer than five origins are defined, report availability count and do not impute.

## 6. Algebraic identity checks

On aligned, positive-denominator legs assert within arithmetic tolerance `1e-12` only:

```text
log(E1/E5) + log(TV1/TV5) == 0
log(J1/J5) - (log(M1/M5) - log(TV1/TV5)) == 0
```

`1e-12` is only a floating implementation guard and cannot enter research classification.

Report violation counts and max absolute errors. Any material violation stops interpretation.

## 7. Native-vs-registered cross-slicer audit

On frozen strict same-event pairs, align corresponding four legs by ordinal.

For each pair/leg report absolute differences for:

- native `E5`;
- native `J5`;
- fine_roughness;
- hidden_variation;
- fine_concentration;
- max_step_refinement;
- origin_log_tv_ratio_median;
- origin_log_tv_ratio_range;
- origin_jump_median;
- origin_jump_range.

Summaries per offset and aggregate must include count, min, median, p90, p99, max and mean.

No new stability threshold is introduced.

## 8. Directional comparison rule

For each registered descriptor compare its pairwise absolute-difference distribution with the relevant native control only by pre-registered paired summaries:

- median absolute difference;
- p90 absolute difference;
- paired sign count of descriptor difference being smaller/equal/larger than native control difference, where a natural control exists.

Natural controls:

- fine_roughness vs `-log(E5)` difference;
- fine_concentration vs native `J5` difference;
- origin_jump_median vs native `J5` difference.

Hidden-variation / refinement / spread components have no native scalar control and remain descriptive.

No weighted score is allowed.

## 9. Redundancy/complementarity audit

Report Spearman associations among registered components over leg observations and separately by duration bins:

`1-3`, `4-5`, `6-11`, `12-23`, `24+` native bars.

Also report:

- fine_roughness vs hidden_variation;
- fine_concentration vs max_step_refinement;
- hidden_variation vs max_step_refinement;
- origin spread vs native-origin absolute metric differences.

No PCA, clustering, fitted latent factor or learned weight in v0.6.10.

## 10. Frozen strata overlays

Repeat descriptor pair-difference summaries for:

- 482 v0.6.6 both-qualified strict pairs;
- 699 v0.6.6 qualification-disagreement pairs;
- 80 v0.6.1 target-repaired pairs;
- the 56 target agreement and 24 target disagreement subsets.

No stratum may change the descriptor definition.

## 11. Prefix causality synthetic gates

Tests must cover:

- algebraic efficiency identity;
- algebraic jump decomposition identity;
- origin-ensemble construction for all five origins;
- origin shift changes individual 5m metrics while ensemble summary is permutation invariant;
- fine-path future append after leg end leaves all descriptors unchanged;
- constant path / zero-TV undefined handling;
- no direction/outcome dependency.

## 12. Required outputs

Write compact outputs to:

`cloud_results/cloud_chat_v0610_path_property_redefinition/`

Required:

```text
summary.json
per_view_property_response.json
cross_slicer_descriptor_differences.json
origin_ensemble.json
component_associations.json
strata_overlays.json
data_identity.json
execution_receipt.json
```

## 13. Interpretation rule

Allowed adjudications only:

- `roughness_concentration_decomposition_is_structurally_coherent_for_next_poc`;
- `origin_ensemble_reduces_origin_aliasing_but_fine_property_remains_interval_sensitive`;
- `registered_components_remain_too_slicer_sensitive_for_property_promotion`;
- `mixed_property_evidence_requires_more_preanalysis`.

A positive result only authorizes a later separately frozen qualification POC. It does not create a qualification rule in v0.6.10.

## 14. Global firewall

`morphology_replication_not_yet_accepted` remains unchanged. Operational baseline remains v0.4.3.

Direction/D1/D2/PAWCT, third-wave, outcomes/P&L, fresh OOS, paper trading and production remain frozen.
