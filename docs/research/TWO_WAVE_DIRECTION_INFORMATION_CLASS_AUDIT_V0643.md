# Two-Wave v0.6.43 Direction Information-Class Audit

Date: 2026-09-11
Status: `complete_read_only_audit_native_high_low_envelope_class_found`

## 1. Purpose

This is a **read-only repository/evidence audit**. It creates no recognizer rule, changes no classification, fits no threshold, and uses no future outcome or P&L.

The audit asks one narrow question after closure of the v0.6.33-v0.6.42 W1 / Range-recovery residual-gating family:

> Does any genuinely distinct, causal parent-direction morphology information class remain unadjudicated, or would the next step merely rename/recombine already measured features?

The frozen direction universe remains the v0.6.18 both-qualified strict same-financial-identity universe of `1,462` pairs. Harmless 5-minute comparison offsets remain diagnostic only and may never become runtime information.

## 2. Audit rule

A class is considered **already covered** when the repository has already measured the same underlying information, even if a later formula could be written with different algebra or a different field name.

A class may be considered **distinct and still open** only if all are true:

1. it consumes information not already represented by the closed direction families;
2. the information is available causally at the parent decision time;
3. it does not require a harmless comparison offset at runtime;
4. it does not require future returns, P&L, H1/H2, third-wave outcomes, or later-period selection data;
5. the audit can identify a mechanism before any numeric threshold is fitted.

## 3. Information-class inventory

### 3.1 Close-anchor level migration / endpoint topology — covered

Covered by D1/D2 and later sign-topology work.

- D1 uses the five confirmed close pivots and amplitude-normalized same-phase/opposite-phase migrations.
- D2 endpoint/envelope translation was historically rejected.
- v0.6.41 explicitly tested cycle-drift sign topology and closed that route.

No new challenger may be created by changing signs, confidence wrappers, endpoint combinations, or nearby drift margins.

### 3.2 Absolute phase-aligned close path — covered

PAWCT v0.5.8 maps each complete close-price cycle to the frozen 65-points-per-leg phase grid and measures absolute translated-path location/dispersion.

That route was adjudicated and rejected. Replacing the distance norm or confidence wrapper without a new information source would be a renamed retry.

### 3.3 Scalar close-path roughness / efficiency / jump / hidden variation — covered

v0.6.10 already defines threshold-free native/fine close-path descriptors including total variation, displacement, maximum step, efficiency, jump share, flat share, roughness, hidden variation, concentration, maximum-step refinement and 5-minute-origin sensitivity.

These scalar close-path descriptors are not an unmeasured direction class.

### 3.4 Whole-window robust close drift — covered

v0.6.21-v0.6.25 consume all closes in the completed parent window through a robust Huber centerline and erosion-consensus support logic.

The contribution is retained, with v0.6.25 still the strongest pooled-exact direction contribution, but this information family is not new.

### 3.5 Close-price location / overlap / containment / distribution — covered and current family closed

v0.6.29-v0.6.42 already cover central location, IQR overlap, mutual-median containment, two-cycle median shift, complete-distribution W1, phase-balanced W1, W1 residual attribution, normalized progress shape, leg asymmetry, sign topology and amplitude-normalization stability.

The v0.6.33-v0.6.42 W1 / Range-recovery residual-gating family is closed. No additional W1 normalization, residual gate, shape cutoff or weak-diagnostic composite is authorized.

### 3.6 Time / duration geometry — measured; not a pristine information class

Time geometry is **not** an untouched class.

- v0.5.4 explicitly changed `corresponding_leg_duration_mismatch` from a hard scale gate to diagnostic-only under the hypothesis `full_cycle_period_defines_scale_phase_leg_allocation_is_diagnostic`.
- v0.5.4 computes the two corresponding-leg duration ratios from all four leg durations.
- v0.5.5 D1 semantic attribution records `max_corresponding_leg_duration_ratio`, `mean_cycle_duration`, `net_drift_per_mean_cycle_bar` and `center_drift_per_mean_cycle_bar` alongside the frozen D1 semantic diagnostics.
- v0.6.19 formally decomposes remaining qualification disagreements using leg durations, cycle durations, cycle-duration ratio and one-native-bar boundary diagnostics.
- v0.6.20 then tests the narrow one-bar duration repair route.

Therefore `duration`, `phase leg allocation`, `duration ratio`, `drift-per-bar`, or a simple algebraic recombination of them cannot be presented as a fresh direction information class. This audit does **not** authorize a duration-direction challenger.

A later time-based study would require a separately demonstrated mechanism not reducible to the already measured duration geometry. No such mechanism is established here.

### 3.7 Native high/low envelope excursion at frozen parent anchors — distinct and not yet direction-adjudicated

This is the one material open class identified by the audit.

The shipped development bars contain causal bar-level `open/high/low/close` and preserve `available_at`. However:

- the historical two-wave pivots are close-price pivots;
- D1 direction uses close-pivot phase migrations;
- PAWCT uses closes;
- v0.6.10 path-property descriptors use close paths;
- v0.6.21 Huber direction uses closes;
- the W1/Range-recovery family uses completed close paths/distributions;
- v0.6.39-v0.6.42 remain close-path-derived diagnostics.

High/low information has appeared in v0.6.17 session-aware **qualification-bound** research, where native OHLC envelopes bound possible hidden total variation/concentration. That use does not constitute parent-direction adjudication: v0.6.17 explicitly excludes direction and outcomes from its API.

Thus the following information is causally available but not yet formally adjudicated for parent direction:

> how far the native bar's phase-consistent high/low envelope extends beyond the frozen close pivot at each of the five already-confirmed parent anchors, and whether replacing only the anchor price observation with the same-bar phase extreme produces a more or less harmless-slicing-stable migration geometry.

This is not D2: the new information source is same-bar high/low excursion that is absent from the close-pivot endpoint representation.

This is not PAWCT or v0.6.10: it does not remeasure the close path with another phase grid or scalar roughness statistic.

This is not v0.6.17 replay: v0.6.17 uses OHLC to bound hidden path concentration for qualification, not to measure parent phase migration.

## 4. Causality and information boundary for the open class

A valid follow-up may use high/low only **after the native bar is closed and available**. It may not infer whether the high occurred before the low inside the bar.

The parent identity, five occurrence bars, qualification decision and confirmation time remain frozen. High/low may be read only on bars already inside the completed parent information set.

No cross-offset information may be consumed by a runtime candidate. Cross-offset comparisons are stability diagnostics only.

## 5. Audit verdict

`v0643_direction_information_class_audit_complete`

- fresh causal direction information class found: **yes**;
- class: `native_high_low_envelope_excursion_at_frozen_parent_anchors`;
- time/duration class considered fresh: **no**;
- recognizer changed: **false**;
- qualification changed: **false**;
- direction winner changed: **false**;
- morphology acceptance: **false**;
- trade authority: **false**;
- production authority: **false**.

## 6. Authorized next step

Authorize exactly one next study: **v0.6.44 native high/low envelope direction attribution**, read-only and threshold-free.

v0.6.44 must be frozen before implementation/results and must answer whether the new high/low information is materially non-redundant and whether its phase-migration representation is at least plausibly more harmless-slicing-stable than the existing close-only representation.

v0.6.44 is **not** authorized to classify, rescue, veto, tune a threshold, or promote a recognizer.

Only if v0.6.44 shows a coherent, stable mechanism may a later separately frozen challenger be considered.

## 7. Newly explicit forbidden shortcuts

- do not repackage duration, phase allocation, duration ratio or drift-per-bar as a fresh direction information class;
- do not infer within-bar high/low ordering from OHLC;
- do not move the frozen five parent anchors to favorable high/low locations;
- do not use high/low to retroactively alter parent identity or v0.6.18 qualification in this line;
- do not fit an OHLC excursion cutoff from v0.6.44 diagnostic groups;
- do not combine OHLC diagnostics post hoc with closed W1/shape/sign residual gates;
- do not use future outcomes or P&L for morphology selection.
