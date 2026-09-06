# v0.6.7 Preanalysis — qualification disagreement decomposition

Date: 2026-09-06

Status: **WRITTEN BEFORE ANY v0.6.7 DECOMPOSITION OUTPUT IS READ**

## 1. Why this audit is allowed

v0.6.6 froze identity upstream and then applied unchanged v0.5.4 qualification on v0.6.5 immutable published raw identities. The decisive strict-pair matrix closed at 29,453 pairs with 699 binary qualification disagreements, while the pre-registered v0.6.1 repaired target strata showed 30%–32% disagreement.

This authorizes decomposition only. It does **not** authorize changing any qualification threshold.

## 2. Frozen population

Primary population: the 699 v0.6.6 published-raw strict same-event pairs with exactly one side qualified.

Frozen pair counts:

```text
offset1 179
offset2 158
offset3 187
offset4 175
aggregate 699
```

Frozen repaired-strata controls:

```text
current-control repaired disagreement: 103 / 3,986
v0.6.3 residual repaired disagreement: 63 / 2,390
v0.6.1 target repaired disagreement: 24 / 80
v0.6.3 target-residual repaired disagreement: 16 / 50
```

Frozen rejected-side hard-reason controls from v0.6.6:

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

## 3. No threshold fitting

All v0.5.4 hard reasons and thresholds remain unchanged. This audit may report signed metric margins relative to the frozen threshold, but it may not define a new near-threshold cutoff or change a threshold.

## 4. Primary reason-family decomposition

For each disagreement pair, the rejected side has at least one v0.5.4 hard reason while the qualified side has none. Map rejected-side reasons into frozen families:

- `path_metric`: `jump_dominated_leg`, `inefficient_leg`, `flat_dominated_leg`;
- `duration_geometry`: `short_leg`, `short_cycle`, `long_cycle`, `long_pair`, `cycle_duration_mismatch`;
- `amplitude`: `invalid_amplitude`, `amplitude_mismatch`;
- `calendar`: `too_many_observed_days`, `wall_span_too_long`;
- `confirmation_clock`: `confirmation_too_late`.

Primary family status is:

- `<family>_only` if every rejected-side hard reason belongs to exactly one family;
- `mixed_multi_family` if rejected-side hard reasons span more than one family.

No reason is dropped and no frequency threshold is used.

## 5. Orientation

Retain direction of disagreement only as qualification orientation, not market direction:

- `main_qualified_other_rejected`;
- `main_rejected_other_qualified`.

Report orientation by family and separately inside the two v0.6.1 target repaired strata.

## 6. Signed threshold margins

For every hard reason on the rejected side, calculate the exact frozen metric on both sides and its signed margin to the frozen threshold.

Examples:

- jump: `max_jump_share - 0.5`;
- inefficient: `0.5 - min_efficiency`;
- short leg: `4 - min_leg_bars`;
- short cycle: `12 - min_cycle_bars`;
- long cycle: `max_cycle_bars - 48`;
- long pair: `pair_duration_bars - 96`;
- cycle-duration mismatch: `cycle_duration_ratio - 2`;
- amplitude mismatch: `amplitude_ratio - 2`;
- confirmation late: `confirmation_delay_bars - 8`;
- flat dominated: `max_flat_share - 0.5`;
- too many observed days: `observed_days - 3`;
- wall span: `wall_days - 7`.

Report distributions only. Do not bin into a new pass/fail notion.

## 7. Canonical 1m path diagnostic for path reasons

Use only supplied `data/development/1m_official.parquet`; no resampling or interpolation.

For each side and each of its four published raw-anchor legs:

1. take the side's existing absolute anchor timestamps as a closed interval;
2. use supplied 1m close rows inside that interval;
3. compute path efficiency, maximum one-minute jump share, and exact flat share with the same formulas as v0.4.3;
4. apply the **same frozen path thresholds only as an audit label**, never as a runtime replacement qualification.

For every 5m path-reason disagreement, report whether the corresponding 1m diagnostic reason is:

- `both_pass`;
- `both_fail`;
- `rejected_side_only`;
- `qualified_side_only`;
- `unavailable`.

Interpretation:

- `both_pass` or `both_fail` means the 5m binary path-reason difference collapses on the canonical fine path and supports sampling-lattice sensitivity;
- `rejected_side_only` means side-specific anchor/window geometry still produces a path difference on 1m;
- `qualified_side_only` is a reversal diagnostic, not a candidate rule.

No 1m diagnostic is allowed to change v0.6.6 qualification.

## 8. Anchor displacement overlay

For each strict pair report the five published raw-anchor timestamp deltas, maximum delta, sum delta and count of nonzero positional deltas.

Compare distributions for:

- 699 disagreement pairs;
- 482 both-qualified strict-pair control;
- v0.6.1 target repaired disagreement vs agreement.

This is descriptive only and cannot widen the 5m matcher.

## 9. Confirmation-clock overlay

Report:

- each side's publishing confirmation timestamp;
- absolute confirmation timestamp delta;
- each side's `confirmation_delay_bars`;
- delay difference;
- whether `confirmation_too_late` is the only hard reason.

No confirmation rule changes in v0.6.7.

## 10. Session-boundary overlay

Tag whether any published anchor or publishing confirmation is within one nominal 5m bar of Shanghai cash-session boundaries (01:30/03:30/05:00/07:00 UTC), and whether corresponding legs cross lunch or trading-day boundaries.

Overlay only; never a matcher or exclusion rule.

## 11. Required strata

Report all metrics separately for:

1. all 699 disagreements;
2. current-control repaired disagreements (103);
3. v0.6.3 residual repaired disagreements (63);
4. v0.6.1 target repaired disagreements (24);
5. v0.6.3 target-residual repaired disagreements (16);
6. 482 both-qualified strict-pair control.

## 12. Interpretation

No post-hoc numeric cutoff.

Cloud may conclude only which already-existing mechanism families materially explain qualification disagreement, and whether the v0.6.1 target enrichment is primarily:

- path-sampling sensitivity;
- residual anchor/window geometry;
- confirmation-clock sensitivity;
- discrete duration/amplitude geometry;
- or mixed.

Any repair must be a later separately frozen experiment.

Global status remains `morphology_replication_not_yet_accepted`; operational baseline remains v0.4.3. Direction/D1/D2/PAWCT, H1/H2, third-wave, outcomes and trading stay frozen.
