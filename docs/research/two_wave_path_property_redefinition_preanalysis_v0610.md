# v0.6.10 Preanalysis — path-property redefinition after resolution-semantics failure

Date: 2026-09-07

Status: **WRITTEN BEFORE ANY v0.6.10 PROPERTY-AUDIT OUTPUT IS READ**

## 1. Why a new representation audit is required

v0.6.9 closed the previous question: native-5m efficiency and jump-share are not resolution-invariant morphology truths with transferable fixed thresholds.

Observed 5m -> supplied-1m refinement produced:

- median `TV1/TV5 = 1.4123`;
- median `E1-E5 = -0.2063`;
- median `J1-J5 = -0.2505`;
- efficiency identity pass->fail `97,027 / 184,276`;
- jump identity fail->pass `126,196 / 184,276`;
- duration vs jump response Spearman `rho = 0.8838`.

Therefore v0.6.10 must not search for a new 0.5-like threshold. It must first ask what underlying path property is actually being measured.

## 2. Algebraic decomposition that is known before data inspection

For an aligned leg with the same endpoints at native-5m and supplied-1m:

```text
D  = abs(P_end - P_start)
TV5 = native 5m total variation
TV1 = supplied 1m total variation
E5 = D / TV5
E1 = D / TV1
```

Therefore, whenever `D>0`:

```text
E1 / E5 = TV5 / TV1
log(E1/E5) = -log(TV1/TV5)
```

So efficiency resolution response is algebraically determined by hidden total-variation refinement. It is not an independent resolution phenomenon.

For jump concentration:

```text
M5 = max native absolute step
M1 = max supplied-1m absolute step
J5 = M5 / TV5
J1 = M1 / TV1
```

Therefore:

```text
log(J1/J5) = log(M1/M5) - log(TV1/TV5)
```

Jump response contains two components: maximum-step scaling and total-variation refinement.

These identities are mathematical definitions, not fitted findings.

## 3. Frozen research question

Can path morphology be represented as a threshold-free continuous property vector that separates:

1. **fine-path roughness** — how much total path variation exists relative to endpoint displacement;
2. **coarse-sampling hidden variation** — how much variation a 5m partition misses;
3. **variation concentration** — how concentrated total variation is in the largest local move;
4. **bar-origin aliasing uncertainty** — how much a 5m measurement changes solely when the 5m origin moves?

The representation must be evaluated for cross-slicer stability before any pass/fail threshold is considered.

## 4. Pre-registered descriptor components

v0.6.10 registers the following descriptive components. None is a qualification rule.

### A. Canonical fine roughness

For supplied 1m path on the published leg interval:

```text
fine_roughness = log(TV1 / D)
```

where `D>0`. This equals `-log(E1)` and makes explicit that the property is path excess variation rather than 'efficiency'.

### B. Hidden-variation refinement

For an aligned native leg:

```text
hidden_variation = log(TV1 / TV5)
```

This is zero if native 5m captures all supplied fine variation and positive when coarse sampling hides variation.

### C. Fine variation concentration

```text
fine_concentration = M1 / TV1
```

This is the supplied-1m jump share, retained only as a continuous concentration coordinate, not a hard gate.

### D. Maximum-step refinement

```text
max_step_refinement = log(M1 / M5)
```

This separates jump numerator scaling from total-variation scaling.

### E. Origin-ensemble 5m aliasing spread

Using only supplied 1m close rows inside the absolute published leg interval, construct five deterministic 5-minute-origin partitions `r = 0..4`:

- always include the published start and end timestamp;
- include every interior supplied 1m timestamp whose integer UTC epoch-minute modulo 5 equals `r`;
- sort and deduplicate timestamps;
- no interpolation, OHLC aggregation, smoothing or synthetic price is allowed.

For each origin compute `TV5_r` and `J5_r`.

Report threshold-free origin-ensemble statistics:

```text
origin_log_tv_ratio_median = median_r log(TV1 / TV5_r)
origin_log_tv_ratio_range  = max_r - min_r of log(TV1 / TV5_r)
origin_jump_median         = median_r J5_r
origin_jump_range          = max_r J5_r - min_r J5_r
```

The range components explicitly encode sampling-origin uncertainty rather than pretending a single native origin is truth.

## 5. No hidden model selection

All five components above are registered before real v0.6.10 output is read.

v0.6.10 may compare them but may not create a new weighted score, PCA combination, threshold, classifier, or outcome-optimized subset after seeing results.

If one component looks weak, it remains reported; it is not silently dropped from this experiment.

## 6. Cross-slicer stability universe

Primary universe remains the frozen v0.6.5 published raw strict same-event pairs:

```text
offset1 8,381
offset2 5,770
offset3 6,204
offset4 9,098
aggregate 29,453
```

For each matched pair and each corresponding leg report absolute descriptor differences for all registered components.

No new tolerance or match rule is introduced.

## 7. Frozen controls / strata

Retain the pre-existing labels only for descriptive overlays:

- 482 v0.6.6 both-qualified pairs;
- 699 v0.6.6 qualification-disagreement pairs;
- 80 v0.6.1 target-repaired pairs, split 56 agreement / 24 disagreement;
- all remaining strict pairs.

These labels cannot define the descriptor or choose a winner.

## 8. Redundancy / complementarity audit

Report, without fitting a model:

- exact algebraic error of `log(E1/E5) + log(TV1/TV5)` on aligned legs;
- exact algebraic error of `log(J1/J5) - [log(M1/M5)-log(TV1/TV5)]` where defined;
- Spearman associations among registered continuous components;
- the same associations by frozen duration bins `1-3, 4-5, 6-11, 12-23, 24+`.

The aim is to determine which current metrics are redundant measurements of the same quantity and which contain distinct information.

## 9. Cross-slicer invariance audit

For each descriptor component report pairwise absolute-difference distributions across the 29,453 strict pairs.

As an explicit control, also report the native-5m `E5` and `J5` pairwise absolute-difference distributions on the same pairs.

A descriptor is not called 'invariant' by a new cutoff. Cloud may only compare full distributions and consistent directional improvement across all four offsets.

## 10. Prefix causality

All descriptor inputs end at the published raw leg endpoint. Appending future supplied 1m/native data after the leg endpoint must leave every descriptor unchanged.

Origin-ensemble construction may use only rows inside the closed leg interval.

## 11. Runtime / deployability firewall

The supplied `1m_official` remains a research/audit input in v0.6.10.

Even if a descriptor is structurally stable, v0.6.10 cannot promote 1m as production input. A later experiment must separately address data availability, live clock, latency and native-5m proxy/error-bound questions.

## 12. Interpretation choices

Allowed cloud adjudications only:

- `roughness_concentration_decomposition_is_structurally_coherent_for_next_poc`;
- `origin_ensemble_reduces_origin_aliasing_but_fine_property_remains_interval_sensitive`;
- `registered_components_remain_too_slicer_sensitive_for_property_promotion`;
- `mixed_property_evidence_requires_more_preanalysis`.

No threshold fitting or qualification promotion is allowed in v0.6.10.

## 13. Global firewall

Global status remains `morphology_replication_not_yet_accepted`; operational baseline remains v0.4.3.

Direction/D1/D2/PAWCT, H1/H2, third-wave, returns/P&L, fresh OOS, paper trading and production remain frozen.
