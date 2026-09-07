# v0.6.12 Frozen protocol — native-5m concentration deployable-proxy / aliasing-error audit

Date: 2026-09-07

Status: **FROZEN BEFORE ANY v0.6.12 REAL-DATA PROXY OUTPUT IS READ**

This audit changes no qualification rule, threshold, identity, matcher, projection, publication, roughness candidate, direction, outcome or trading logic.

## 1. Hard controls

Before interpreting any v0.6.12 output, reproduce exactly:

```text
published identities = 38,176 / 36,737 / 36,619 / 36,480 / 36,264
published raw strict pairs = 8,381 / 5,770 / 6,204 / 9,098
aggregate strict = 29,453
both-qualified = 482
qualification disagreements = 699
target repaired = 80 = 56 agreement + 24 disagreement
```

Reproduce v0.6.10 oracle references on the same comparable pair-leg universe:

```text
pair-leg observations = 117,805
native J5 abs-diff median = 0.053931031782781566
fine J1 abs-diff median   = 0.0064740520975389015
origin-jump median abs-diff median = 0.016957546216696373
```

Any drift stops interpretation.

## 2. Data

Use the same frozen development inputs:

- five native 5m OHLC views;
- supplied `1m_official` only as audit oracle;
- 2015-01-05 through 2020-12-31;
- no post-2020 rows;
- no local resampling, interpolation, fill or synthetic prices.

## 3. Registered runtime proxy

For each published raw leg `[a,b]` with native OHLC arrays, transitions are bars `j=a+1..b`.

Compute:

```text
DC_j = abs(C_j-C_{j-1})
TR_j = max(H_j-L_j, abs(H_j-C_{j-1}), abs(L_j-C_{j-1}))
R_j  = H_j-L_j

J_close = max(DC)/sum(DC) if sum(DC)>0 else None
J_TR    = max(TR)/sum(TR) if sum(TR)>0 else None
J_HL    = max(R)/sum(R)   if sum(R)>0 else None
```

Primary candidate: `J_TR`.

`J_close` is the frozen native control. `J_HL` is diagnostic only.

## 4. Runtime uncertainty descriptor

When `J_close`, `J_TR`, `J_HL` are all defined:

```text
proxy_lower = min(...)
proxy_upper = max(...)
proxy_spread = proxy_upper - proxy_lower
```

No cutoff, multiplier or fitted expansion.

## 5. Oracle construction

On the same absolute published leg interval and supplied 1m close path, compute exactly as v0.6.10:

- `fine_concentration = J1`;
- five-origin `origin_jump_median`;
- five-origin `origin_jump_range`.

If exact 1m endpoints are unavailable, oracle remains unavailable. No interpolation.

## 6. Primary proxy-error comparisons

For every side-leg where candidate and oracle are defined, report absolute errors:

```text
|J_close - J1|
|J_TR - J1|
|J_HL - J1|

|J_close - origin_jump_median|
|J_TR - origin_jump_median|
|J_HL - origin_jump_median|
```

Required summary: count/min/median/p90/p99/max/mean.

Paired sign counts must compare `J_TR` vs `J_close` on exactly the same observations for each oracle.

No fitted calibration.

## 7. Cross-slicer stability

On frozen strict same-event pairs, align legs by ordinal and report absolute counterpart differences for:

- `J_close`;
- `J_TR`;
- `J_HL`;
- oracle `J1`;
- oracle `origin_jump_median`;
- `proxy_spread`.

For `J_TR` vs `J_close`, report paired sign smaller/equal/larger per offset and aggregate.

No new stability threshold.

## 8. Native empirical bracket

When all three native concentrations and an oracle are defined, define:

```text
lower = min(J_close,J_TR,J_HL)
upper = max(J_close,J_TR,J_HL)
width = upper-lower
```

Report separately for `J1` and `origin_jump_median`:

- oracle inside bracket count/fraction;
- below / above count;
- width distribution;
- absolute distance from bracket when outside.

Observed coverage is empirical only; do not call it a mathematical bound.

## 9. Aliasing uncertainty audit

Report Spearman associations of `proxy_spread` with:

- `origin_jump_range`;
- `abs(J_close-origin_jump_median)`;
- `abs(J_TR-origin_jump_median)`;
- `abs(J_close-J1)`;
- `abs(J_TR-J1)`.

Also report the same associations by frozen duration bins.

No learned uncertainty model.

## 10. Duration bins

Use only:

`1-3`, `4-5`, `6-11`, `12-23`, `24+` native bars.

For each bin report proxy/oracle errors and proxy-spread distribution. No duration correction is produced.

## 11. Frozen strata overlays

Repeat primary error and cross-slicer summaries for:

- 482 both-qualified pairs;
- 699 qualification-disagreement pairs;
- 80 target-repaired pairs;
- 56 target agreement;
- 24 target disagreement.

No descriptor or proxy changes by stratum.

## 12. Prefix causality / deployability gates

Synthetic tests must prove:

1. exact close concentration formula;
2. exact true-range definition using only current H/L and previous close;
3. high-low concentration definition;
4. primary proxy uses no 1m or alternate-offset input;
5. future append after leg end cannot change native proxy;
6. gaps are represented through true range previous-close term;
7. zero-sum path stays explicit undefined;
8. proxy spread / empirical bracket are deterministic, unweighted functions;
9. no direction/outcome/trading dependency.

## 13. Required outputs

Write compact evidence to:

`cloud_results/cloud_chat_v0612_concentration_deployable_proxy/`

Required:

```text
summary.json
per_view_proxy.json
oracle_error.json
cross_slicer_proxy.json
empirical_bracket.json
aliasing_uncertainty.json
duration_overlay.json
strata_overlays.json
data_identity.json
execution_receipt.json
```

## 14. Allowed adjudications

Only:

- `native_true_range_concentration_is_viable_for_separate_proxy_poc`;
- `native_proxy_tracks_center_but_uncertainty_envelope_is_too_wide`;
- `native_ohlc_proxies_do_not_reliably_track_fine_concentration`;
- `mixed_proxy_evidence_requires_more_preanalysis`.

A positive result creates no qualification threshold and does not make supplied 1m a production dependency.

## 15. Global firewall

`morphology_replication_not_yet_accepted` remains unchanged; operational baseline remains v0.4.3.

No threshold fitting, matcher/projection/publication change, roughness re-optimization, direction/D1/D2/PAWCT, third-wave, outcomes/P&L, fresh OOS, paper trading or production is allowed in v0.6.12.
