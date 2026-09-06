# v0.6.8 Preanalysis — canonical fine-path qualification representation

Date: 2026-09-06

Status: **WRITTEN BEFORE ANY v0.6.8 CANDIDATE QUALIFICATION OUTPUT IS READ**

## 1. Why this experiment is allowed

v0.6.7 decomposed the 699 frozen v0.6.6 qualification disagreements without changing thresholds.

The dominant mechanism was path sampling sensitivity:

```text
path_metric_only          404 / 699
path family involved      538 / 699 = 76.97%
```

Using supplied `1m_official` only as an audit path:

```text
jump_dominated_leg: 368 / 368 -> both_pass
inefficient_leg:    211 / 211 -> both_fail
```

Thus the side-specific 5m path-reason split disappeared on the shared fine lattice in all 579 observed path-reason cases. This authorizes one representation POC only.

It does **not** authorize changing any threshold, duration rule, projection, matcher, publication rule, direction model, outcome rule, or trading logic.

## 2. Mathematical problem

The current frozen path gates use close-to-close path statistics computed on each native 5m slicing:

```text
length      = sum(abs(diff(close)))
efficiency  = abs(last-first) / length
jump_share  = max(abs(diff(close))) / length
flat_share  = mean(diff(close)==0)
```

These are not invariant to harmless phase shifts of a coarse sampling lattice because intermediate reversals and jump allocation change when the 5m bar endpoints change.

v0.6.8 asks whether path qualification should instead be represented on one **shared canonical fine lattice**, while preserving the same raw financial identity, the same absolute anchor interval, the same formulas, and the same numerical thresholds.

## 3. Single registered representation candidate

Candidate name:

`supplied_1m_canonical_path_for_path_gates_v068`

For each v0.6.5 immutable published raw identity and each of its four legs:

1. take the existing published raw anchor timestamps `[t_k, t_{k+1}]` as a closed absolute-time interval;
2. read only supplied `data/development/1m_official.parquet` rows inside that interval;
3. require at least two supplied 1m rows;
4. compute length / efficiency / jump_share / flat_share with the exact frozen formulas above;
5. use the existing v0.5.4 path thresholds unchanged:
   - `inefficient_leg` iff min efficiency `< 0.5`;
   - `jump_dominated_leg` iff max jump share `> 0.5`;
   - `flat_dominated_leg` iff max flat share `> 0.5`.

No resampling, interpolation, forward fill, synthetic row, smoothing, or fitted tolerance is allowed.

The word **canonical** means only “shared supplied 1m lattice for all five native-5m views.” It does not claim invariance to arbitrary finer sampling frequencies.

## 4. Everything else remains frozen

For candidate qualification:

- v0.6.5 published raw identity and publishing confirmation clock stay unchanged;
- v0.6.6/v0.5.4 non-path hard reasons stay exactly as already computed;
- remove only the three 5m path reasons from the control hard-reason set;
- recompute only those three path reasons on supplied 1m;
- `corresponding_leg_duration_mismatch` remains diagnostic-only as in v0.5.4;
- duration, amplitude, calendar and confirmation metrics remain the native-view frozen values;
- qualification does not participate in matching.

No D1/D2/PAWCT field may be interpreted.

## 5. Primary pair universe

Use exactly the frozen v0.6.5 published raw strict same-event pairs:

```text
offset1 8,381
offset2 5,770
offset3 6,204
offset4 9,098
aggregate 29,453
```

Pair formation is upstream of candidate qualification and cannot change.

## 6. Control qualification matrix

Before candidate interpretation reproduce v0.6.6 exactly:

```text
both_qualified                    482
both_rejected                  28,272
main_qualified_other_rejected     352
main_rejected_other_qualified     347
aggregate                       29,453
```

Frozen repaired-strata controls:

```text
control repaired               3,986; disagreement 103
v0.6.3 residual repaired       2,390; disagreement 63
v0.6.1 target repaired            80; disagreement 24
v0.6.3 target-residual repaired   50; disagreement 16
```

v0.6.7 path-reason controls:

```text
jump_dominated_leg 368
inefficient_leg    211
```

Any drift stops interpretation.

## 7. Candidate pair matrix

On the same 29,453 strict pairs report exactly:

- `both_qualified`;
- `both_rejected`;
- `main_qualified_other_rejected`;
- `main_rejected_other_qualified`.

Report:

- binary agreement;
- union-qualified pairs;
- both-qualified / union-qualified overlap;
- main-qualified survival to other;
- other-qualified survival to main.

High agreement by itself is not success because both-rejected may dominate.

## 8. Control → candidate transition accounting

For every strict pair retain its v0.6.6 control status and v0.6.8 candidate status.

Report at least:

- control disagreement -> candidate agreement, split into candidate both-qualified / both-rejected;
- control agreement -> candidate disagreement;
- control both-qualified -> candidate both-qualified / both-rejected / disagreement;
- control both-rejected -> candidate both-rejected / both-qualified / disagreement.

This prevents declaring success merely because a shared fine path rejects both sides more often.

## 9. Per-view candidate qualification

For every view report:

- published identity count;
- candidate qualified / rejected;
- candidate path reason counts;
- non-path reason counts unchanged check;
- number of identities with unavailable canonical-1m leg;
- endpoint timestamp presence on the supplied 1m path.

No coverage count is a promotion threshold.

## 10. Required repaired strata

Report candidate pair matrix and control→candidate transitions separately for:

1. all current-control repaired pairs: `3,986`;
2. v0.6.3 residual repaired: `2,390`;
3. v0.6.1 target repaired: `80`;
4. v0.6.3 target-residual repaired: `50`.

The target strata must not be diluted by the overall both-rejected population.

## 11. Synthetic / mathematical gates

Before financial replay tests must demonstrate:

1. **shared-lattice invariance**: two coarse slicings of the same supplied fine path can produce different coarse path metrics while the canonical-1m path metric for the same absolute interval is identical;
2. **5m-close non-identifiability**: two different fine paths can share the same coarse endpoint closes yet have different total variation / efficiency / jump share, showing exact fine-path qualification cannot be reconstructed from coarse closes alone;
3. future rows strictly after the leg end do not change canonical path metrics;
4. missing/insufficient 1m support fails closed; no interpolation;
5. zero-length fine path keeps frozen convention `efficiency=0`, `jump_share=1`;
6. no non-path v0.5.4 reason is changed by the candidate transformer.

## 12. Deployment firewall

Even if the mathematical POC is positive, v0.6.8 does not automatically make `1m_official` a production morphology input.

A later, separately frozen deployment/data-clock audit would be required to establish:

- whether a canonical fine path is available under the intended live information clock;
- whether the supplier path is complete enough to fail-open/closed safely;
- operational latency and source identity;
- whether research-only 1m availability differs from deployable availability.

If 1m is not deployable, a later workstream must design a 5m-compatible approximation with explicit invariance/error bounds; v0.6.8 may not invent one after seeing results.

## 13. Interpretation

No post-hoc numeric promotion cutoff.

Cloud may conclude only one of:

- `canonical_fine_path_representation_structurally_improves_qualification_stability`;
- `shared_fine_path_mainly_increases_joint_rejection_without_solving_positive_stability`;
- `canonical_fine_path_representation_remains_materially_unstable`;
- `mixed_result_requires_separate_analysis`.

A positive result authorizes only a separate data-clock/deployment eligibility audit. It does not reopen direction work and does not authorize threshold changes.

Duration-geometry remains a separate secondary workstream.

Global state remains `morphology_replication_not_yet_accepted`; operational baseline remains v0.4.3.
