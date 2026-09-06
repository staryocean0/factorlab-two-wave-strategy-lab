# v0.6.7 Frozen protocol — qualification disagreement decomposition

Date: 2026-09-06

Status: **FROZEN BEFORE ANY v0.6.7 DECOMPOSITION OUTPUT IS READ**

This protocol inherits v0.6.6 and changes no projection, publication, matcher, qualification threshold, direction, packing, outcome, or trading logic.

## 1. Hard controls

Before interpreting any decomposition, reproduce exactly:

```text
published raw strict pairs: 8381 / 5770 / 6204 / 9098
qualification disagreements: 179 / 158 / 187 / 175
aggregate disagreements: 699
both-qualified strict control: 482

control repaired disagreement: 103 / 3986
v0.6.3 residual repaired disagreement: 63 / 2390
v0.6.1 target repaired disagreement: 24 / 80
v0.6.3 target-residual repaired disagreement: 16 / 50
```

Rejected-side hard-reason controls:

```text
jump_dominated_leg       368
inefficient_leg          211
short_leg                105
confirmation_too_late     76
short_cycle               54
amplitude_mismatch        50
cycle_duration_mismatch   37
long_cycle                 4
```

Any drift stops interpretation.

## 2. Primary disagreement family

Map every rejected-side v0.5.4 hard reason into exactly one frozen family:

```text
path_metric:
  jump_dominated_leg
  inefficient_leg
  flat_dominated_leg

duration_geometry:
  short_leg
  short_cycle
  long_cycle
  long_pair
  cycle_duration_mismatch

amplitude:
  invalid_amplitude
  amplitude_mismatch

calendar:
  too_many_observed_days
  wall_span_too_long

confirmation_clock:
  confirmation_too_late
```

For each disagreement pair:

- if all hard reasons belong to one family: `<family>_only`;
- otherwise: `mixed_multi_family`.

Exactly one primary family is assigned. Family attribution uses only frozen rejection reasons; no new threshold or score is introduced.

## 3. Reason-level metrics and margins

For each disagreement pair retain both sides' frozen metrics. For every rejected-side hard reason compute signed threshold margins using the exact frozen threshold:

```text
jump_dominated_leg:       max(jump_share) - 0.5
inefficient_leg:          0.5 - min(efficiency)
flat_dominated_leg:       max(flat_share) - 0.5
short_leg:                4 - min(leg_duration)
short_cycle:              12 - min(cycle_duration)
long_cycle:               max(cycle_duration) - 48
long_pair:                pair_duration - 96
cycle_duration_mismatch:  max(cycle)/min(cycle) - 2
invalid_amplitude:        no numeric margin; validity flag only
amplitude_mismatch:       amplitude_ratio - 2
confirmation_too_late:    confirmation_delay - 8
too_many_observed_days:   observed_days - 3
wall_span_too_long:       wall_days - 7
```

Report rejected-side and qualified-side values plus signed margins. No near-threshold category is created.

## 4. Qualification orientation

Retain only:

- `main_qualified_other_rejected`;
- `main_rejected_other_qualified`.

This is not market direction. Report orientation by primary family and required strata.

## 5. Canonical 1m path audit

Use only supplied `1m_official`; no resampling/interpolation/fill.

For every published leg `[anchor_k, anchor_{k+1}]` on each side, use 1m closes inside the closed absolute-time interval and compute:

```text
length = sum(abs(diff(close)))
efficiency = abs(last-first) / length, or 0 if length==0
jump_share = max(abs(diff(close))) / length, or 1 if length==0
flat_share = mean(diff(close)==0)
```

For each path reason, derive a diagnostic reason flag with the same frozen numeric threshold:

- inefficient iff efficiency < 0.5;
- jump dominated iff jump_share > 0.5;
- flat dominated iff flat_share > 0.5.

For a pair/reason classify the side-specific 1m diagnostic relation:

- `both_pass`;
- `both_fail`;
- `rejected_side_only`;
- `qualified_side_only`;
- `unavailable`.

The 1m diagnostic can never modify qualification or become runtime input.

## 6. Anchor displacement overlay

For every strict pair, compare the five published raw-anchor timestamps position-wise and report:

- deltas in minutes;
- max delta;
- sum delta;
- nonzero-anchor count.

No tolerance changes. Summary controls:

- all 699 disagreements;
- all 482 both-qualified pairs;
- v0.6.1 target repaired agreement/disagreement split.

## 7. Confirmation clock overlay

For every pair report:

- publishing confirmation timestamps;
- absolute confirmation-time delta;
- confirmation delay bars on both sides;
- absolute delay-bar difference;
- confirmation-only flag.

## 8. Session/calendar overlay

Use UTC minute-of-day boundaries `(90, 210, 300, 420)` corresponding to Shanghai 09:30/11:30/13:00/15:00.

Report if any raw anchor or publishing confirmation is within 5 minutes of a boundary, whether any corresponding leg crosses the lunch break, and whether corresponding anchors fall on different observed trading dates.

Overlay only.

## 9. Required strata and counts

Primary outputs must report separately:

```text
all disagreements:                    699
control-repaired disagreements:       103
v0.6.3 residual-repaired disagreements: 63
v0.6.1 target-repaired disagreements: 24
v0.6.3 target-residual disagreements: 16
both-qualified strict control:        482
```

The full upstream repaired-stratum denominators remain `3986 / 2390 / 80 / 50` and must also be retained.

## 10. Synthetic gates

Tests must cover:

- each primary reason family and mixed classification;
- exact signed margin formulas;
- 1m path metric formulas including zero-length path handling;
- 1m relation labels (`both_pass`, `both_fail`, rejected-only, qualified-only);
- anchor delta computation;
- session-boundary overlay;
- no future/outcome/direction fields are required.

## 11. Outputs

Write compact outputs to:

`cloud_results/cloud_chat_v067_qualification_disagreement_decomposition/`

Required:

```text
summary.json
pair_offset_1.json
pair_offset_2.json
pair_offset_3.json
pair_offset_4.json
repaired_strata.json
one_minute_path_diagnostics.json
data_identity.json
execution_receipt.json
```

Large per-pair details may remain runtime-local or be kept as deterministic identity-keyed samples; never select samples by outcome.

## 12. Interpretation rule

No new promotion cutoff.

Cloud may only identify which frozen mechanism family materially contributes to disagreement and whether canonical-1m path diagnostics support 5m sampling-lattice sensitivity versus residual side-specific geometry.

No threshold repair, projection change, direction work, third-wave test, P&L, fresh OOS or trading is authorized by v0.6.7.

Global state remains `morphology_replication_not_yet_accepted`; operational baseline remains v0.4.3.
