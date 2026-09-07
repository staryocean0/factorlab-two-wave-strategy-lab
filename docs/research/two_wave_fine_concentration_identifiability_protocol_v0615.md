# v0.6.15 Frozen protocol — fine-concentration identifiability / structural bounds under native 5m OHLC

Date: 2026-09-07

Status: **FROZEN BEFORE ANY v0.6.15 REAL-DATA BOUND OUTPUT IS READ**

This audit changes no qualification rule, threshold, identity, matcher, projection, publication, roughness candidate, direction, outcome or trading logic.

## 1. Hard controls

Before interpretation reproduce exactly:

```text
published identities = 38,176 / 36,737 / 36,619 / 36,480 / 36,264
published raw strict pairs = 8,381 / 5,770 / 6,204 / 9,098 = 29,453
both-qualified = 482
qualification disagreements = 699
target repaired = 80 = 56 agreement + 24 disagreement
```

Retain v0.6.13 fine-profile availability and v0.6.10 oracle-comparable pair-leg universe:

```text
fine profile defined = 737,070 published legs
oracle-comparable strict pair-leg observations = 117,805
```

Any behavioral drift stops interpretation.

## 2. Native information set and hidden minute count

For every adjacent native close transition inside a published leg, the current native bar contributes its `low/high/close`, with previous native close supplied by the prior row.

The registered hidden-path model fixes exactly **five 1m close-to-close increments per native 5m transition**. This is not fitted.

No supplied-1m value is accepted by the bound function.

## 3. Per-bar exact upper TV and step envelopes

For `c0 -> z1 -> z2 -> z3 -> z4 -> c5`, each `zk in [L,H]`.

Compute exact:

```text
TV_bar_max = max over 16 vertices zk in {L,H}
             |z1-c0|+|z2-z1|+|z3-z2|+|z4-z3|+|c5-z4|
TV_bar_min = |c5-c0|
M_bar_min  = |c5-c0| / 5
M_bar_max  = max(|L-c0|,|H-c0|,H-L,|L-c5|,|H-c5|)
```

Reject invalid native bars with `H<L` or close outside `[L,H]` before any interpretation.

## 4. Leg-level J outer bounds

For B native transitions:

```text
N       = 5*B
TV_low  = sum(TV_bar_min)
TV_high = sum(TV_bar_max)
M_low   = max(M_bar_min)
M_high  = max(M_bar_max)

J_low  = max(1/N, M_low/TV_high)                  if TV_high>0
J_high = min(1, M_high/TV_low)                    if TV_low>0
         1                                        otherwise
```

Require `0 < J_low <= J_high <= 1` for defined legs.

## 5. Profile outer bounds

Transform J bounds to the frozen v0.6.13 profile.

```text
C_inf_low  = log(N*J_low)
C_inf_high = log(N*J_high)
```

For `C_1/C_2` lower bounds, if `J_low<=1/N` use zero; otherwise evaluate the probability vector `[J_low,(1-J_low)/(N-1),...]`.

For upper bounds under `max(w)<=J_high`, fill as many weights equal to `J_high` as possible, then one remainder and zeros. Evaluate `C_1/C_2` on that vector.

All bounds must lie in `[0,log(N)]` up to `1e-12` arithmetic guard.

## 6. Synthetic gates

Before real output tests must prove:

- exact 16-vertex TV maximum on known examples;
- random feasible synthetic hidden paths always satisfy TV/M/J bounds;
- synthetic feasible `C_inf/C_1/C_2` always lie inside profile bounds;
- simplex lower/upper extremizers satisfy max-weight constraints;
- price-scale invariance;
- prefix locality of a closed leg;
- zero-native-TV handling remains explicit;
- bound API has no fine/oracle/counterpart/direction/outcome input.

## 7. Oracle data-consistency gates

For every oracle-comparable published leg before tightness interpretation:

1. native endpoint closes match exact supplied-1m closes;
2. each adjacent native transition contains exactly five supplied-1m close increments under the frozen trading-minute sequence;
3. every supplied-1m close assigned to a native bar lies inside native `[low,high]` within arithmetic tolerance;
4. actual supplied-1m `J1/C_inf/C_1/C_2` lie inside registered outer bounds.

Report all violation counts. Any material violation stops interpretation.

## 8. Tightness outputs

For J and each profile component report:

- bound lower/upper distribution;
- width distribution;
- oracle position in bound when width>0;
- coverage fraction.

For `C_inf/C_1/C_2` also report normalized width:

```text
normalized_width = (upper-lower) / log(N)
```

when `N>1`.

No tightness threshold is fitted.

## 9. Step-count and strict-pair overlays

Use frozen native-transition bins `1-3`, `4-5`, `6-11`, `12-23`, `24+` and report width/coverage by bin.

On frozen 29,453 strict pairs, report counterpart differences of lower/upper/width and repeat for:

- both-qualified 482;
- qualification-disagreement 699;
- target repaired 80;
- target agreement 56;
- target disagreement 24.

No stratum changes the bounds.

## 10. Required outputs

Write compact evidence to:

`cloud_results/cloud_chat_v0615_concentration_identifiability/`

Required:

```text
summary.json
data_consistency.json
bound_tightness.json
step_count_overlay.json
cross_slicer_bounds.json
strata_overlays.json
data_identity.json
execution_receipt.json
```

## 11. Allowed adjudications

Only:

- `native_ohlc_bounds_are_tight_enough_for_identifiable_concentration_property`;
- `native_ohlc_bounds_cover_oracle_but_are_too_wide_for_identification`;
- `structural_bounds_fail_data_consistency_or_oracle_coverage`;
- `mixed_identifiability_requires_more_audit`.

No result authorizes threshold fitting. A wide-bound result instead authorizes a documented finer production-data requirement.

## 12. Global firewall

`morphology_replication_not_yet_accepted` remains unchanged. Operational baseline remains v0.4.3.

No empirical bound shrinkage, fitted mapping, duration correction, qualification threshold, matcher/projection/publication change, roughness re-optimization, direction/D1/D2/PAWCT, third-wave, outcomes/P&L, fresh OOS, paper trading or production is allowed.
