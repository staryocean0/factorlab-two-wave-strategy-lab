# Two-Wave v0.6.51 — Left-Boundary / Internal-Pivot Correspondence Decomposition

Status: **frozen before any v0.6.51 decomposition statistics are read**.

## 1. Scientific question

v0.6.50 established that the algorithmic and human parent intervals are neither clearly identical nor clearly disjoint. On the `11` frozen human-positive candidate cases with complete final-reference `p0..p4`, median outer-interval IoU was `0.7742`, median normalized five-anchor MAE was `0.1242`, median start-boundary error was `17` bars, and median end-boundary error was `4` bars.

The next question is narrower:

> Is the unresolved correspondence primarily a left-boundary definition problem, a rigid temporal translation, an internal pivot/phase decomposition mismatch, or a distributed mixture?

This is a **read-only decomposition**. It cannot create a new recognizer, remap pivots, tune boundary tolerances, change qualification, or authorize direction/trading logic.

## 2. Frozen inputs and membership

Use exactly the same frozen objects as v0.6.50:

- source `data/development/5m_offset_0.parquet`, SHA256 `bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`;
- v0.6.48 sampling commitment `f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8`;
- final independent reference labels SHA256 `321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d`;
- v0.6.18 frozen qualified-publication chain;
- canonical identity selection from v0.6.50: lexicographic `(published_raw_occurrence_bars, phase)` at multi-identity cutoffs.

The direct decomposition universe is **only** the frozen reference-positive candidate cases with complete valid final-reference `p0..p4`. It must reconstruct exactly the same `11` cases identified by v0.6.50.

Do not use annotator notes/confidence, A/B/C source-sheet alternatives, direction predictions, future bars/outcomes, PnL, harmless offsets, or reference-negative pseudo-anchors.

No case-level table pairing blinded IDs with model/human anchors may be committed.

## 3. Coordinate system

For each anchored case, map the algorithmic five anchors to the frozen 96-bar chart positions exactly as v0.6.50:

`mi_visible = mi - (cutoff - 95)` for `i=0..4`.

Human anchors are the frozen final-reference integers `pi` in `0..95`.

Define signed anchor displacement:

`di = mi_visible - pi`.

Positive means the model anchor occurs **later/rightward** than the human anchor; negative means earlier/leftward.

Define absolute anchor error `ai = |di|`.

## 4. Boundary diagnostics

Aggregate separately for `i=0` and `i=4`:

- median signed displacement;
- median absolute displacement;
- Q1/Q3 of signed and absolute displacement;
- positive / zero / negative sign incidence.

Define per-case boundary-offset disagreement:

`B = |d0 - d4|`.

Small `B` is consistent with rigid translation; large `B` means the two outer boundaries are not shifted together.

Report median/Q1/Q3 of `B`.

## 5. Translation-removed diagnostics

For each case define the rigid-translation estimate:

`t = median(d0,d1,d2,d3,d4)`.

Translation-removed residuals:

`ri = di - t`.

Report:

- raw five-anchor MAE in bars;
- translation-removed five-anchor MAE in bars;
- fractional MAE reduction `(raw_mae - residual_mae)/raw_mae` when raw MAE > 0;
- median reduction across cases.

This is diagnostic only; `t` is not a proposed runtime correction.

## 6. Boundary-normalized internal phase diagnostics

To separate internal decomposition from outer-boundary disagreement, normalize each object to its own `[0,1]` parent interval.

For model internal anchors `i=1,2,3`:

`um_i = (m_i - m_0)/(m_4 - m_0)`.

For human internal anchors:

`uh_i = (p_i - p_0)/(p_4 - p_0)`.

Define internal phase errors:

`qi = um_i - uh_i`.

Per case report internally only, and aggregate only:

- absolute phase error by ordinal `i=1,2,3`;
- `internal_phase_mae = mean(|q1|,|q2|,|q3|)`;
- center-pivot absolute phase error `|q2|`.

Also normalize the four leg durations by each object's own total span and compute:

`leg_share_mae = mean(|model_leg_share_j - human_leg_share_j|)` for `j=0..3`.

No time warping, pivot permutation, phase reversal, nearest-neighbor matching, or ordinal reassignment is allowed.

## 7. Frozen evidence bands

All thresholds below are frozen before v0.6.51 results are read.

### 7.1 Rigid translation dominant

Strong support only if all hold:

1. median boundary-offset disagreement `B <= 6` bars;
2. median internal phase MAE `<= 0.08`;
3. median translation-removal MAE reduction `>= 0.50`;
4. median of `max(|d0|,|d4|) >= 8` bars, so the result is not merely already-close correspondence.

### 7.2 Left-boundary dominant

Strong support only if all hold:

1. median `|d0| >= 10` bars;
2. median `|d4| <= 6` bars;
3. median internal phase MAE `<= 0.08`;
4. at least `8/11` cases satisfy `|d0| > |d4|`.

This does not authorize a 10-, 17-, or any other bar tolerance.

### 7.3 End-boundary dominant

Symmetric rule:

1. median `|d4| >= 10` bars;
2. median `|d0| <= 6` bars;
3. median internal phase MAE `<= 0.08`;
4. at least `8/11` cases satisfy `|d4| > |d0|`.

### 7.4 Internal pivot/phase decomposition mismatch

Strong support if either holds:

- median internal phase MAE `> 0.12`; or
- at least two of the three internal ordinals have median absolute phase error `> 0.12`.

### 7.5 Mixed boundary + internal mismatch

Strong support only if:

- internal pivot/phase mismatch from §7.4 is true; and
- median `max(|d0|,|d4|) >= 10` bars.

### 7.6 Correspondence after removing boundary representation

Strong support only if:

- median internal phase MAE `<= 0.08`; and
- median leg-share MAE `<= 0.08`.

This means internal ordinal geometry agrees after each object is normalized to its own boundaries. It does **not** authorize changing the algorithmic boundaries.

## 8. Frozen primary-category precedence

Choose exactly one:

1. `v0651_rigid_translation_dominant` if §7.1 passes;
2. else `v0651_left_boundary_definition_dominant` if §7.2 passes;
3. else `v0651_end_boundary_definition_dominant` if §7.3 passes;
4. else `v0651_mixed_boundary_and_internal_pivot_mismatch` if §7.5 passes;
5. else `v0651_internal_pivot_phase_mismatch_dominant` if §7.4 passes;
6. else `v0651_internal_geometry_corresponds_boundary_representation_unresolved` if §7.6 passes;
7. else `v0651_correspondence_decomposition_mixed_or_unresolved`.

## 9. Reporting

Commit aggregate evidence only:

- reconstructed anchored-case count;
- per-ordinal signed/absolute error summaries;
- boundary-offset disagreement distribution;
- translation-removal aggregate summaries;
- per-internal-ordinal phase-error summaries;
- internal phase MAE and leg-share MAE distributions;
- incidence counts required by frozen rules;
- every frozen-rule boolean and primary category.

Do not commit case IDs, per-case human/model anchors, per-case errors, or any candidate rule derived from them.

## 10. Governance

Whatever the result:

- `threshold_fitting_performed=false`;
- `pivot_remapping_performed=false`;
- `qualification_changed=false`;
- `direction_winner_changed=false`;
- `morphology_acceptance=false`;
- `trade_authority=false`;
- `production_authority=false`.

Any future semantic-object challenger must be separately specified and validated on evidence not used to fit it. v0.6.51 itself is attribution/decomposition only.
