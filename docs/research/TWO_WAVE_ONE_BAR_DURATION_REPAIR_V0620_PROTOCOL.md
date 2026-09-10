# Two-Wave v0.6.20 exact one-bar duration-boundary repair protocol

Date: 2026-09-10

Status: **results-blind protocol freeze**

## 1. Authorized question

v0.6.19 formally attributed the largest remaining v0.6.18 qualification instability to local-duration native-bar boundary sensitivity. This version tests exactly one causal, single-view repair candidate and nothing else:

> Can exact one-native-bar misses at the existing `min_leg=4` and `min_cycle=12` boundaries be demoted from hard vetoes to diagnostics without weakening the rest of the v0.6.18 qualification policy?

This is a qualification-policy component experiment only. It is not a new direction classifier, morphology acceptance exercise, outcome study, or trading strategy.

## 2. Champion before v0.6.20

Current best qualification-policy component: **v0.6.18 path-gate demotion**.

Frozen v0.6.18 cross-view benchmark on v0.6.5 strict same-event pairs:

| offset | strict pairs | positive overlap | both qualified |
|---|---:|---:|---:|
| offset1 | 8,381 | 0.6993006993 | 400 |
| offset2 | 5,770 | 0.6420581655 | 287 |
| offset3 | 6,204 | 0.6452991453 | 302 |
| offset4 | 9,098 | 0.7265745008 | 473 |
| aggregate | 29,453 | **0.6838166511** | **1,462** |

v0.6.18 remains champion unless every promotion requirement below passes.

## 3. Frozen input and identity universe

Use only the row-level artifacts from formal v0.6.18 run `34423674192`:

- `v0618-5m_offset_0` artifact `10132007935`
- `v0618-5m_offset_1` artifact `10132046343`
- `v0618-5m_offset_2` artifact `10132056291`
- `v0618-5m_offset_3` artifact `10132017437`
- `v0618-5m_offset_4` artifact `10132055670`

The analyzer must reproduce before candidate evaluation:

- filtered mutual-unique same-event pairs: `14,784 / 12,725 / 13,412 / 16,108 = 57,029`;
- published raw strict pairs: `8,381 / 5,770 / 6,204 / 9,098 = 29,453`;
- v0.6.18 aggregate matrix: `bothQ=1,462 / bothRejected=27,315 / mainOnlyQ=386 / otherOnlyQ=290`.

No rematching, resampling, market replay, future outcome, P&L, or cross-view feature may participate in the candidate rule.

## 4. Exactly one frozen candidate

For each already-published raw identity, start from the v0.6.18 hard reasons.

Candidate `v0.6.20_exact_one_bar_duration_repair` changes only:

1. `short_leg` is demoted **only if** raw `min_leg == 3`;
2. `short_cycle` is demoted **only if** raw `min_cycle == 11`.

All other cases remain exactly as v0.6.18:

- `short_leg` remains hard if `min_leg <= 2`;
- `short_cycle` remains hard if `min_cycle <= 10`;
- `cycle_duration_mismatch` remains hard at the frozen `duration_ratio=2.0` rule;
- `amplitude_mismatch` remains hard;
- `confirmation_too_late` remains hard;
- `long_cycle`, `long_pair`, `too_many_observed_days`, `wall_span_too_long` remain hard;
- the v0.6.18 path reasons `inefficient_leg` and `jump_dominated_leg` remain diagnostics, not hard vetoes.

There is no parameter grid and no alternate candidate.

## 5. Causality constraint

The v0.6.20 rule must be computable from one identity's own already-known raw occurrence bars and v0.6.18 hard reasons only. It may not inspect another offset, future bars, outcomes, labels, or trading returns.

Cross-view information is evaluation evidence only.

## 6. Frozen promotion gate versus v0.6.18

All conditions must pass:

### A. Exact control reproduction

- filtered pairs = `57,029` exactly;
- strict pairs = `29,453` exactly;
- v0.6.18 candidate matrix exactly reproduced per offset and aggregate.

### B. Per-offset non-regression

For every offset 1-4:

`v0.6.20 positive_overlap >= v0.6.18 positive_overlap`.

### C. Material aggregate improvement

`aggregate_positive_overlap >= 0.7138166511`

which is at least **+3.0 percentage points** over v0.6.18.

### D. Material positive-state support improvement

`aggregate_both_qualified >= 1609`

which is at least 10% above the v0.6.18 count of 1,462, rounded up.

### E. Hard safety invariants

For every individual identity:

- if v0.6.18 contains any of `long_cycle`, `long_pair`, `too_many_observed_days`, `wall_span_too_long`, v0.6.20 must remain rejected;
- if `min_leg <= 2`, v0.6.20 must remain rejected whenever `short_leg` is present;
- if `min_cycle <= 10`, v0.6.20 must remain rejected whenever `short_cycle` is present;
- if `cycle_duration_mismatch` is present, v0.6.20 may not remove it.

The candidate passes only if A+B+C+D+E all pass.

## 7. Fail-closed governance

The runner may write only its result bundle. It may not edit the M0 authority registry or declare global morphology acceptance.

If the candidate fails any gate:

- v0.6.18 remains the qualification-policy champion;
- v0.6.20 is retained as contribution/negative evidence;
- no post-result widening to `min_leg<=3`, `min_cycle<=11`, duration-ratio tuning, or candidate grid is allowed inside v0.6.20.

If it passes all gates:

- it is eligible to replace v0.6.18 **only as the qualification-policy component**;
- the historical full recognizer v0.4.3 remains the full-recognizer baseline;
- global `morphology_replication_not_yet_accepted` remains unchanged;
- parent direction/state classification remains frozen.

## 8. Frozen exclusions

No changes to parent identity, v0.6.5 publication, matcher, packing, D1/D2/PAWCT, H1/H2, third-wave logic, outcomes, transaction costs, P&L, paper trading, or production authority.
