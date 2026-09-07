# v0.6.15 Preanalysis — fine-concentration identifiability under native 5m OHLC

Date: 2026-09-07

Status: **WRITTEN BEFORE ANY v0.6.15 REAL-DATA BOUND OUTPUT IS READ**

## 1. Why this is the next question

v0.6.12 rejected native OHLC point-estimate proxies for fine concentration. v0.6.13 removed much of the mechanical step-count effect but retained a material native→fine measurement gap. v0.6.14 showed that deterministic further coarsening of native closes is stable but does not reveal the hidden fine refinement.

Therefore v0.6.15 stops inventing point estimates. It asks an information-theoretic question:

> Given only the already-available native 5m OHLC path and the known five-minute sampling semantics, what fine 1m movement-concentration values are structurally possible?

If guaranteed native-information bounds are very wide, the correct conclusion is non-identifiability / finer production-data requirement, not another fitted proxy.

## 2. Frozen hidden-path model

For one native transition from previous native close `c0` to current native close `c5`, the current 5m bar supplies `L,H,C=c5`.

The hidden supplied-1m close path is represented as five close-to-close increments:

```text
c0 -> z1 -> z2 -> z3 -> z4 -> c5
```

where each hidden minute close `zk` must lie in `[L,H]`.

This is an **outer information-set model**: native OHLC tells us that minute closes cannot lie outside the bar trading range, but does not assert that minute closes attained H or L, and does not invent intrabar ordering.

No oracle 1m value enters bound construction.

## 3. Per-bar exact total-variation upper bound

For fixed `c0,L,H,c5`, the maximum hidden close-path total variation over `z1..z4 in [L,H]` is:

```text
TV_bar_max = max |z1-c0| + |z2-z1| + |z3-z2| + |z4-z3| + |c5-z4|
```

Because this objective is convex in each hidden coordinate over a box, a maximum occurs at a vertex. v0.6.15 therefore computes the exact maximum by enumerating the fixed 16 assignments `zk in {L,H}`.

The minimum possible bar variation is the triangle-inequality lower bound:

```text
TV_bar_min = |c5-c0|
```

## 4. Per-bar maximum-step bounds

For five hidden increments:

```text
M_bar_min = |c5-c0| / 5
```

by the pigeonhole/triangle inequality.

The exact maximum possible single hidden close step is:

```text
M_bar_max = max(
  |L-c0|, |H-c0|,
  H-L,
  |L-c5|, |H-c5|
)
```

which is equivalent to the native bar's close-path true-range envelope.

## 5. Leg-level guaranteed outer bounds

For a published leg with `B` native close transitions:

```text
N = 5 * B                       # hidden 1m movement count
TV_low  = sum(TV_bar_min)
TV_high = sum(TV_bar_max)
M_low   = max(M_bar_min)
M_high  = max(M_bar_max)
```

Fine max-share concentration `J = M/TV` must satisfy the guaranteed outer interval:

```text
J_low  = max(1/N, M_low / TV_high)
J_high = min(1,   M_high / TV_low)   if TV_low>0
         1                            otherwise
```

No empirical shrinkage, fitted multiplier or quantile calibration is allowed.

## 6. Guaranteed bounds for the v0.6.13 normalized profile

Because `C_inf = log(N*J)`, its outer bounds are:

```text
C_inf_low  = log(N * J_low)
C_inf_high = log(N * J_high)
```

For `C_1` and `C_2`, use only probability-simplex consequences of `max(w) in [J_low,J_high]`.

### Lower concentration bound from `max(w) >= p`

If `p=J_low <= 1/N`, lower bound is zero. Otherwise the least concentrated distribution with a weight at least p is:

```text
[p, (1-p)/(N-1), ..., (1-p)/(N-1)]
```

Use this distribution to compute registered `C_1_low` and `C_2_low`.

### Upper concentration bound from `max(w) <= u`

Let `u=J_high`, `k=floor(1/u)`, `r=1-k*u` (with arithmetic handling of exact division). The most concentrated probability vector under cap u is:

```text
[u repeated k times, r if r>0, zeros otherwise]
```

Use this distribution to compute registered `C_1_high` and `C_2_high`.

These are outer mathematical bounds; they are not claimed to be jointly sharp with every OHLC path constraint.

## 7. Data-consistency gates before interpretation

On oracle-comparable intervals only, before interpreting tightness assert:

1. every native endpoint timestamp used by the fine audit has an exact supplied-1m close and equal close value;
2. between adjacent native closes there are exactly five supplied 1m close-to-close increments under the frozen data clock;
3. every supplied 1m close inside a native bar lies within that native bar's `[low,high]`;
4. actual fine `J1/C_inf/C_1/C_2` lie inside the registered outer bounds within `1e-12` arithmetic guard.

Any material violation stops interpretation and triggers data-clock/bound debugging.

## 8. Tightness audit

For each component report:

- bound lower / upper distributions;
- absolute bound width;
- normalized width `width / log(N)` for `C_inf/C_1/C_2` when `N>1`;
- fine oracle location `(oracle-low)/(high-low)` when width>0;
- empirical coverage (expected to be 100% if assumptions/implementation are correct).

For J report raw width `J_high-J_low` and oracle location.

No width cutoff is introduced.

## 9. Step-count and strata overlays

Report bound tightness by frozen native step-count bins `1-3`, `4-5`, `6-11`, `12-23`, `24+`, and on frozen pair strata:

- both-qualified 482;
- qualification-disagreement 699;
- target repaired 80;
- target agreement 56;
- target disagreement 24.

No stratum changes the bound.

## 10. Cross-slicer bound consistency

On the frozen 29,453 strict same-event pair universe, compare counterpart lower bounds, upper bounds and widths for corresponding legs. This is descriptive only; a wide but stable bound is still uninformative.

## 11. Synthetic gates

Tests must prove:

1. 16-vertex enumeration matches brute-force vertex maximum for bar TV;
2. every generated feasible hidden path lies inside J bounds;
3. C_inf/C_1/C_2 oracle profiles generated from feasible synthetic paths lie inside transformed bounds;
4. probability-simplex lower/upper constructions have the stated max-weight constraints;
5. positive price scaling leaves J/profile bounds unchanged;
6. future append outside the closed leg cannot change bounds;
7. native bound API contains no fine/oracle/counterpart/direction/outcome input.

## 12. Interpretation choices

Allowed adjudications only:

- `native_ohlc_bounds_are_tight_enough_for_identifiable_concentration_property`;
- `native_ohlc_bounds_cover_oracle_but_are_too_wide_for_identification`;
- `structural_bounds_fail_data_consistency_or_oracle_coverage`;
- `mixed_identifiability_requires_more_audit`.

A positive result still creates no qualification threshold. A wide-bound result authorizes documenting a finer production-data requirement rather than continuing point-estimate proxy fitting.

## 13. Global firewall

Global state remains `morphology_replication_not_yet_accepted`; operational baseline remains v0.4.3.

No fitted bound shrinkage, duration correction, qualification threshold, matcher/projection/publication change, roughness re-optimization, direction/D1/D2/PAWCT, third-wave, outcomes/P&L, fresh OOS, paper trading or production is allowed.
