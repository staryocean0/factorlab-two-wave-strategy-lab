# Two-Wave v0.6.44 Native High/Low Envelope Direction Attribution — Frozen Protocol

Date: 2026-09-11
Status: `frozen_before_v0644_implementation_and_results`

## 1. Research question

v0.6.43 identified one materially distinct causal information class that has not been formally adjudicated for parent direction:

`native_high_low_envelope_excursion_at_frozen_parent_anchors`.

v0.6.44 is a **read-only, threshold-free attribution study**. It asks:

> After freezing the existing parent identity and five close-pivot occurrence bars, does the same-bar phase-consistent high/low envelope contain non-redundant parent-migration information, and is that information at least plausibly more harmless-slicing-stable than the close-only phase migration already used by D1?

This version changes no recognizer rule and cannot promote a direction candidate.

## 2. Frozen universe and controls

Use the same strict same-financial-identity direction universe already authoritative from v0.6.18 onward:

- filtered mutual-unique same-event pairs: `57,029`;
- published raw strict pairs: `29,453`;
- both-v0.6.18-qualified pairs: `1,462`;
- main view: `5m_offset_0`;
- four harmless comparison offsets: diagnostic only.

Hard-control reproduction must confirm:

- D1 exact pairs: `1,400/1,462`;
- v0.6.25 exact pairs: `1,402/1,462`;
- v0.6.25 pooled decisive agreement: `1.0`;
- v0.6.25 opposite UpTrend/DownTrend conflicts: `0`.

Any control drift invalidates the run.

## 3. Frozen identity and information boundary

For every view, use the already-published five occurrence bars exactly as stored. Do not move, re-detect or optimize pivots using high/low.

For anchors `i0 < i1 < i2 < i3 < i4`:

- the close pivot type is already frozen as alternating `low/high/low/high/low` or `high/low/high/low/high`;
- the anchor close remains the existing close price used by D1;
- the only new observation is the native bar extreme at the same frozen anchor bar:
  - low-phase anchor -> native bar `low`;
  - high-phase anchor -> native bar `high`.

Only bars already available by the frozen parent decision time may be read.

No inference about within-bar high/low order is allowed.

## 4. Frozen per-anchor representation

For anchor `k`, let:

- `C_k` = frozen close-pivot price;
- `E_k` = same-bar phase-consistent extreme (`low` for a low anchor, `high` for a high anchor);
- `A` = the existing frozen positive parent amplitude unit for that view.

Define normalized outward excursion:

`X_k = |E_k - C_k| / A`.

Because the anchor phase is frozen, the absolute value is only a magnitude convenience; the outward direction is already determined by whether the anchor is high or low.

Record all five `X_k` values. No anchor-excursion threshold is fitted.

## 5. Frozen close-vs-envelope phase migration

Let the existing close-based three-step D1 migration vector be:

`S_close = [(C_2-C_0)/A, (C_4-C_2)/A, (C_3-C_1)/A]`.

Define the high/low-envelope migration vector on the **same five bars**:

`S_env = [(E_2-E_0)/A, (E_4-E_2)/A, (E_3-E_1)/A]`.

Define the envelope adjustment vector:

`D_env = S_env - S_close`.

These are descriptors only. D1 thresholds are **not** applied to `S_env` in v0.6.44.

## 6. Frozen within-view descriptors

For each view report exactly the following primary descriptors:

1. `mean_anchor_outward_excursion = mean(X_0..X_4)`;
2. `max_anchor_outward_excursion = max(X_0..X_4)`;
3. `envelope_adjustment_l1 = mean(abs(D_env_j))` over the three migration coordinates;
4. `envelope_adjustment_linf = max(abs(D_env_j))`;
5. `close_migration_l1 = mean(abs(S_close_j))`;
6. `envelope_migration_l1 = mean(abs(S_env_j))`.

Also persist the raw five excursions and the three close/envelope/adjustment vectors for auditability.

No additional descriptor menu may be searched after results are seen.

## 7. Frozen harmless-slicing pair descriptors

For each matched main/comparison pair, align the corresponding descriptor/vector from the two harmless views.

Primary stability quantities:

1. `close_step_view_distance_l1 = mean(abs(S_close_main - S_close_other))`;
2. `envelope_step_view_distance_l1 = mean(abs(S_env_main - S_env_other))`;
3. `envelope_stability_gain_l1 = close_step_view_distance_l1 - envelope_step_view_distance_l1`;
4. `envelope_adjustment_view_distance_l1 = mean(abs(D_env_main - D_env_other))`;
5. `mean_anchor_excursion_view_delta = abs(mean_X_main - mean_X_other)`.

Interpretation of the frozen sign convention:

- positive `envelope_stability_gain_l1` means the same-bar high/low envelope migration is more stable under harmless slicing than the close-only migration;
- negative means it is less stable.

No numerical cutoff on these quantities is allowed.

## 8. Frozen grouping

Report the pair descriptors under both existing frozen label systems:

### 8.1 D1 consistency groups

- `D1_exact`: 1,400 pairs;
- `D1_nonexact`: 62 pairs.

### 8.2 v0.6.25 consistency groups

- `v0625_exact`: 1,402 pairs;
- `v0625_nonexact`: 60 pairs.

The grouping labels are outcome-free cross-view morphology-consistency labels, not market-return labels.

Also report all results per harmless offset and pooled.

## 9. Frozen summaries and rank statistics

For every scalar descriptor and every group report:

- count;
- mean;
- median;
- q25;
- q75;
- min;
- max.

For the primary v0.6.25 grouping, report tie-aware rank probabilities:

- `P(nonexact mean_anchor_outward_excursion > exact)`;
- `P(nonexact envelope_adjustment_l1 > exact)`;
- `P(nonexact envelope_adjustment_view_distance_l1 > exact)`;
- `P(nonexact mean_anchor_excursion_view_delta > exact)`;
- `P(nonexact envelope_stability_gain_l1 > exact)`.

For `envelope_stability_gain_l1`, additionally report:

- fraction positive in v0.6.25 exact pairs;
- fraction positive in v0.6.25 nonexact pairs;
- median gain by each of the four harmless offsets.

These are descriptive attribution statistics only.

## 10. Frozen interpretation categories

After controls pass, assign exactly one category using the qualitative mechanism evidence, not a fitted cutoff:

1. `v0644_high_low_envelope_redundant_or_unstable`
   - envelope adjustments are small/redundant relative to close migration, or envelope migration is not more stable in any coherent cross-offset sense.
   - consequence: close the native-anchor high/low envelope route.

2. `v0644_high_low_envelope_nonredundant_but_not_stability_improving`
   - high/low adds material information, but harmless-slicing stability does not improve coherently.
   - consequence: retain as scientific evidence only; no challenger authorized.

3. `v0644_high_low_envelope_nonredundant_and_stability_promising`
   - the new information is material and the envelope representation shows coherent positive harmless-slicing stability gain across the frozen comparisons, especially among the existing nonexact pairs without degrading the broad exact population.
   - consequence: a **separately frozen** later challenger may be considered.

The category assignment must cite the full fixed descriptor set and per-offset evidence. It may not be based on cherry-picking one post-hoc statistic.

## 11. Hard prohibitions

v0.6.44 must not:

- move or re-detect the five frozen anchors using high/low;
- requalify any record;
- apply D1/v0.6.25 thresholds to the high/low vector;
- fit any high/low excursion threshold;
- infer within-bar high/low ordering;
- use open/high/low from bars after the frozen decision time;
- use future returns, P&L, H1/H2, third-wave outcomes or later-period selection data;
- use harmless comparison offsets as runtime information;
- combine this diagnostic post hoc with closed W1, progress-shape, leg-asymmetry, sign-topology or amplitude-normalization residual gates.

## 12. Authority consequence

Regardless of outcome:

- v0.6.18 remains qualification champion;
- v0.6.25 remains strongest pooled-exact direction contribution unless a later separately frozen challenger formally beats it;
- parent-direction winner remains unset in v0.6.44;
- morphology acceptance remains false;
- trade authority remains false;
- production authority remains false.

`recognizer_changed=false`
`qualification_changed=false`
`trade_authority=false`
`production_authority=false`
