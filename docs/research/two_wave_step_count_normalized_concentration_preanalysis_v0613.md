# v0.6.13 Preanalysis — step-count / resolution-normalized concentration property

Date: 2026-09-07

Status: **WRITTEN BEFORE ANY v0.6.13 REAL-DATA OUTPUT IS READ**

## 1. Why v0.6.12 requires a property-level reformulation

v0.6.12 registered native true-range concentration as a deployable proxy for supplied-1m fine concentration. It partially improved cross-slicer stability and J1 error, but failed as a reliable proxy because concentration error is strongly step-count dependent and the fixed native bracket covered fine J1 only about 4.5%.

Therefore v0.6.13 does not fit OHLC→J1, does not fit duration correction and does not search a new threshold. It asks whether the underlying concentration property itself can be written with explicit step-count semantics.

## 2. Frozen movement-weight representation

For one path represented by nonnegative movement magnitudes `x_i`, with `n>=2` and `S=sum(x)>0`:

```text
w_i = x_i / S
```

`w` is a probability distribution over observed movement increments. Concentration is then measured relative to the uniform distribution over the same `n` observed increments.

If `n<2` or `S<=0`, all registered concentration-profile components are undefined. No epsilon replacement.

## 3. Registered three-component concentration profile

All three components are frozen before real output and must remain reported; no winner may be selected after results.

### A. Max-weight excess / Rényi-infinity divergence

```text
C_inf = log(n * max_i w_i)
```

### B. Shannon concentration / KL-to-uniform

```text
H = -sum_i w_i log(w_i)  over positive w_i
C_1 = log(n) - H
```

### C. Quadratic concentration / Rényi-2-to-uniform

```text
C_2 = log(n * sum_i w_i^2)
```

All are zero for exactly uniform movement weights and increase as observed movement becomes more concentrated.

No weighting or scalar combination of `(C_inf,C_1,C_2)` is allowed in v0.6.13.

## 4. Exact uniform-subdivision invariance known before data

Take every movement `x_i` and split it into exactly `k>=1` equal children `x_i/k`. The new path has `n'=kn` movement weights `w_i/k`, each repeated k times.

Then exactly:

```text
C_inf' = C_inf
C_1'   = C_1
C_2'   = C_2
```

This property is the reason the profile is registered. It removes concentration change caused solely by uniform replication of all increments.

It does **not** prove invariance to real market refinement, where coarse moves contain cancellation and fine increments are unequal. Real-data audit is still required.

## 5. Frozen movement primitives

To isolate semantics, v0.6.13 uses:

- native close movements: `x5 = abs(diff(native 5m close))`;
- fine oracle movements: `x1 = abs(diff(supplied 1m close))` on the same absolute published leg interval.

Native true range is retained only as a descriptive secondary overlay because v0.6.12 already rejected it as a direct fine-concentration proxy. It cannot be promoted by v0.6.13.

## 6. Frozen questions

Without fitting, answer:

1. How strongly does each native profile component rank-correlate with its fine counterpart on the same leg?
2. How does each native→fine profile gap depend on native step count / duration, compared with raw max-share `J5→J1` dependence?
3. Are native profile components more stable across frozen strict same-event slicer pairs than raw `J5`, in their own continuous geometry?
4. Are fine profile components stable across the same strict pairs despite <=5m endpoint displacement?
5. Does the three-component profile provide complementary information or collapse to one redundant coordinate?

No threshold is produced.

## 7. Cross-resolution audit

For every side-leg with both native and fine profiles defined, report separately for `C_inf/C_1/C_2`:

- native distribution;
- fine distribution;
- native-minus-fine distribution;
- absolute gap distribution;
- Spearman(native,fine);
- Spearman(abs gap, native step count).

Raw `J_close` vs `J1` remains a descriptive control for step-count dependence only. Because units differ from the new profile, v0.6.13 must not compare raw absolute-error magnitudes across different descriptor units as if they were commensurate.

## 8. Cross-slicer audit

On the frozen strict same-event pair universe, align four legs by ordinal and separately report absolute counterpart differences for:

- native `J_close` control;
- native `C_inf/C_1/C_2`;
- fine `C_inf/C_1/C_2`.

Per offset and aggregate summaries: count/min/median/p90/p99/max/mean.

No new stability cutoff.

## 9. Origin-refinement diagnostic

Using supplied 1m only as audit material, construct the same five deterministic 5m-origin subsamples as v0.6.10 and compute the three-component profile for each origin when defined.

Report per leg:

- median across five origins for each component;
- range across five origins;
- fine profile minus origin-median relation.

This is audit-only and does not become a runtime requirement.

## 10. Redundancy/complementarity

Report Spearman associations among `C_inf/C_1/C_2` separately for native and fine paths, aggregate and by frozen duration bins.

No PCA, latent factor, fitted weight or descriptor dropping.

## 11. Frozen strata

Repeat key cross-resolution and cross-slicer summaries for:

- 482 both-qualified pairs;
- 699 qualification-disagreement pairs;
- 80 target-repaired pairs;
- 56 target agreement / 24 target disagreement.

Strata cannot redefine the profile.

## 12. Synthetic gates

Tests must prove:

1. uniform movement weights give all three components zero;
2. a more concentrated distribution gives positive components;
3. exact uniform-subdivision invariance for arbitrary positive movement vector and integer k;
4. scale invariance to multiplying all movements by a positive constant;
5. zero-sum / n<2 remain explicit undefined;
6. future append outside the closed leg input cannot enter the profile;
7. no 1m/counterpart/direction/outcome dependency in the primitive profile function.

## 13. Allowed adjudications

Only:

- `renyi_concentration_profile_is_structurally_resolution_coherent_for_next_poc`;
- `step_count_normalization_reduces_duration_bias_but_not_cross_resolution_gap`;
- `normalized_profile_remains_materially_resolution_dependent`;
- `mixed_normalized_concentration_evidence_requires_more_audit`.

A positive result creates no qualification rule and no production input.

## 14. Global firewall

Global state remains `morphology_replication_not_yet_accepted`; operational baseline remains v0.4.3.

No fitted duration correction, qualification threshold, matcher/projection/publication change, roughness re-optimization, direction/D1/D2/PAWCT, third-wave, outcomes/P&L, fresh OOS, paper trading or production is allowed in v0.6.13.
