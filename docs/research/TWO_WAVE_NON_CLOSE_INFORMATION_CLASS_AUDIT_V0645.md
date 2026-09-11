# Two-Wave v0.6.45 Non-Close Information-Class Audit

Date: 2026-09-11
Status: `complete_read_only_audit_native_open_body_gap_class_found`

## 1. Purpose

This is a read-only repository/evidence audit following v0.6.44. It changes no recognizer rule, fits no threshold, requalifies no record, and uses no future outcome or P&L.

The audit asks:

> After close-based direction families and frozen-anchor high/low envelope information have been adjudicated, does any remaining causally available input represent genuinely new parent morphology information rather than qualification, clock, data-quality or execution metadata?

The frozen direction universe remains the v0.6.18 both-qualified strict same-financial-identity universe of 1,462 harmless-view pairs. Comparison offsets remain diagnostic only.

## 2. Audit correction

The v0.6.43/v0.6.44 closure language overstated the completeness of the price-only audit. The shipped native bars contain `open`, but v0.6.43 enumerated close-path families plus high/low envelope excursion and v0.6.44 reads only `close/high/low` at frozen anchors. Native `open` was not formally parent-direction adjudicated.

This audit corrects that governance gap before any new empirical candidate is allowed.

## 3. Remaining information surfaces

### 3.1 Volume — not a valid current research class

The CSI1000 index development package states that `volume` is optional and mostly unavailable. Missing volume may not be filled or manufactured. A sparse/availability-conditioned volume study would change the effective universe and confound morphology with data availability.

Verdict: `not_authorized_current_information_surface`.

### 3.2 Confirmation delay / available_at / execution clock — causal metadata, not parent morphology

Confirmation delay is already part of qualification and causality controls. `available_at` establishes when a bar may be consumed; the repository explicitly does not assert bar-end real-time availability or trade-fill authority.

These fields may constrain when a morphology decision becomes valid, but they do not define whether the completed parent is Range, UpTrend, DownTrend or Uncertain.

Verdict: `clock_metadata_not_direction_semantics`.

### 3.3 Session / calendar span — already scale/qualification information

Observed sessions, wall-clock span, cycle duration and related timing geometry already enter the scale/qualification lineage and were formally audited in v0.6.19-v0.6.20. Reusing session count, time-of-day, trading-day count or calendar-span gates as a direction classifier would mix sampling context with parent-state semantics absent a separately demonstrated mechanism.

Verdict: `already_qualification_context_not_fresh_direction_class`.

### 3.4 Source-support / gap topology — measurement provenance, not market state

v0.6.17 uses authoritative 1m support/gap topology to bound hidden path concentration under session-aware qualification analysis. The topology records which source rows were enveloped/discarded by a native bar construction; it is data-product/sampling provenance.

A direction label must not become Range/Trend because a particular DataHub support partition contains more source gaps. This information may support uncertainty/validity auditing, not parent morphology classification.

Verdict: `measurement_provenance_not_direction_semantics`.

### 3.5 Harmless comparison-offset identity — diagnostic only

Cross-offset agreement is an evaluation surface and is explicitly forbidden as runtime information.

Verdict: `diagnostic_only`.

### 3.6 Native open/body/gap geometry at frozen parent anchors — distinct and still open

Native `open` is causally available once each completed bar is available and is not derivable from the frozen close pivot alone. It also is not the high/low envelope source tested by v0.6.44.

A narrowly defined fresh information class remains:

`native_open_body_gap_geometry_at_frozen_parent_anchors`

Allowed read-only measurements include, on the already-frozen five parent anchor bars:

- open-to-close body displacement normalized by the frozen parent amplitude unit;
- phase-oriented body displacement relative to the frozen low/high anchor kind;
- opening gap relative to the immediately preceding observed close, normalized by the same amplitude unit;
- the three open-anchor phase migrations corresponding to the same D1 phase relationships;
- close-vs-open migration adjustment;
- harmless-view stability of the open-anchor representation versus the close-anchor representation.

The anchor bars, phase, qualification and parent identity remain frozen. Open may not be used to re-detect or move pivots.

## 4. Why this is distinct

It is not D1/D2 because those consume close-pivot levels.

It is not PAWCT or v0.6.10 because those consume close paths.

It is not v0.6.44 because v0.6.44 consumes same-bar high/low envelope extremes but never native open.

It is not timing/session metadata because the value is an observed market price on the already-frozen native bar.

## 5. Audit verdict

`v0645_non_close_information_class_audit_complete`

- fresh causal direction information class found: **yes**;
- class: `native_open_body_gap_geometry_at_frozen_parent_anchors`;
- volume authorized: **no**;
- clock/availability authorized as direction semantics: **no**;
- session/calendar authorized as fresh direction semantics: **no**;
- source-support/gap topology authorized as direction semantics: **no**;
- recognizer changed: **false**;
- qualification changed: **false**;
- direction winner changed: **false**;
- morphology acceptance: **false**;
- trade authority: **false**;
- production authority: **false**.

## 6. Authorized next step

Authorize exactly one follow-up: **v0.6.46 native open/body/gap direction attribution**, read-only and threshold-free.

v0.6.46 may reproduce the frozen 1,462-pair direction universe and measure the fixed descriptor menu above. It may compare v0.6.25 exact vs non-exact groups and harmless-view stability, but it may not classify, rescue, veto, fit a cutoff, alter qualification, or use comparison offsets as runtime features.

Only a coherent, non-redundant and harmless-slicing-stable mechanism may authorize a later separately frozen challenger.

## 7. Forbidden shortcuts

- do not fill or impute index volume;
- do not use missing-volume status as a morphology label;
- do not classify parent state from `available_at`, confirmation delay, session count or source-support gaps;
- do not infer intrabar event ordering from OHLC;
- do not move the frozen five parent anchors using open;
- do not fit an open/body/gap cutoff from v0.6.46 groups;
- do not combine v0.6.46 diagnostics post hoc with closed W1/high-low/shape/sign routes;
- do not use harmless offsets as runtime information;
- do not use future returns, P&L, H1/H2 or third-wave outcomes for morphology selection.
