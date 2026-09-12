# Two-Wave v0.6.49 Reference-Conditioned Qualification Failure Attribution Protocol

Date: 2026-09-12
Status: **frozen before v0.6.49 attribution output is read**
Research role: read-only diagnostic attribution after v0.6.48 independent-reference calibration failure

## 1. Scientific question

v0.6.48 established that only `16/120 = 13.33%` of the hidden v0.6.18-qualified candidate cases were independently confirmed as complete same-scale two-wave parents. v0.6.49 asks a narrower question:

> Which already-observable properties of the frozen v0.6.18 candidate object differ between the 104 reference-negative candidates and the 16 reference-positive candidates, and which predeclared failure family is most consistent with that difference?

This is **not** a qualification challenger, threshold search, classifier fit, direction experiment, or acceptance test.

## 2. Frozen evidence universe

Use only the exact v0.6.48 packet and final reference set already frozen on `main`:

- sampling commitment: `f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8`;
- final reference SHA256: `321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d`;
- hidden candidate cases: exactly `120`;
- reference-positive candidates: exactly `16`;
- reference-negative candidates: exactly `104`.

Controls may be reported only as count/context. They are not used to fit or define any attribution threshold.

## 3. Frozen reconstruction

Reconstruct the v0.6.18 candidate chain exactly as in v0.6.48 scoring:

`v0.5.2 exact ridge -> v0.6.1 canonical birth universe -> v0.6.4 predecessor projection -> v0.6.5 first-valid publication -> v0.6.6 published raw qualification -> v0.6.18 path-gate demotion`.

For each hidden candidate case, map the case cutoff to all v0.6.18-qualified published identities at that cutoff.

Pre-label determinacy already showed 118/120 candidate cutoffs contain one qualified identity and 2/120 contain two identities with no D1/v0.6.25 state disagreement. For v0.6.49 qualification diagnostics, the case-level aggregation rule is frozen as:

- continuous quantities: **median across qualified identities at the cutoff**;
- binary trigger quantities: **true if any qualified identity triggers**;
- identity ambiguity: retain the integer qualified-identity count.

No identity may be selected after inspecting the reference label.

## 4. Allowed diagnostic families

No new data modality is introduced. Only causal information available at the frozen publication cutoff is allowed.

### A. publication/completion maturity

- `confirmation_delay_bars = cutoff - p4`;
- `completion_buffer_fraction = confirmation_delay_bars / 95`.

Expected failure direction for an `immature_publication` explanation: reference-negative candidates have **smaller** values (final pivot closer to the cutoff / less post-pivot confirmation).

### B. fragment / parent-scale occupancy

Using the 96-bar visible packet window ending at the case cutoff:

- `parent_span_bars = p4 - p0`;
- `parent_span_fraction = parent_span_bars / 95`;
- `parent_anchor_excursion_fraction = (max(anchor closes) - min(anchor closes)) / visible_96_close_range`;
- `amplitude_unit_fraction = frozen amplitude_unit_price / visible_96_close_range`.

Expected failure direction for a `fragment_below_parent_scale` explanation: reference-negative candidates have **smaller** occupancy/excursion fractions.

### C. within-parent same-scale imbalance

- `cycle_duration_ratio = max(cycle_durations) / min(cycle_durations)`;
- `corresponding_leg_duration_max_ratio` from the two corresponding-leg ratios;
- `amplitude_ratio` from frozen v0.6.6 measurement.

Expected failure direction for a `same_scale_imbalance` explanation: reference-negative candidates have **larger** ratios.

### D. path/noise contamination

- `min_leg_efficiency`;
- `max_leg_jump_share`;
- `max_leg_flat_share`;
- binary legacy diagnostic `inefficient_leg`;
- binary legacy diagnostic `jump_dominated_leg`.

Expected failure direction for a `path_noise` explanation: reference-negative candidates have lower efficiency and/or larger jump/flat shares, with higher legacy-path trigger incidence.

The two v0.6.18-demoted path reasons remain diagnostics only. This protocol does not restore them as gates.

### E. identity ambiguity

- `qualified_identity_count_at_cutoff`.

Expected failure direction for an `identity_ambiguity` explanation: reference-negative candidates have larger identity count / higher multi-identity incidence.

### F. legacy diagnostic-only duration mismatch

- binary `corresponding_leg_duration_mismatch` trigger from the frozen v0.4.3/v0.5.4 lineage.

This is reported separately because v0.5.4 deliberately demoted it. It cannot become a gate from this audit.

## 5. Explicitly forbidden inputs

Primary attribution must not use:

- annotator free-text `notes`;
- annotator `confidence`;
- D1 or v0.6.25 state/prediction;
- post-cutoff bars;
- returns, P&L, H1/H2, third-wave outcomes;
- harmless comparison offsets as runtime information;
- newly fitted thresholds, regression, trees, clustering, feature selection, or classifier accuracy;
- dropping years/cases after seeing results.

The final reference label is used only to partition the 120 frozen candidate cases into `reference_yes` and `reference_no`.

## 6. Frozen statistics

For every continuous diagnostic, report by reference group:

- count;
- median;
- Q1/Q3;
- `P(reference_no > reference_yes) + 0.5 * P(tie)` rank probability.

For diagnostics whose expected failure direction is lower (`confirmation_delay_bars`, `completion_buffer_fraction`, `parent_span_fraction`, `parent_anchor_excursion_fraction`, `amplitude_unit_fraction`, `min_leg_efficiency`), also report the direction-adjusted failure rank as `1 - raw_rank_probability`.

For binary diagnostics, report:

- incidence in reference-no;
- incidence in reference-yes;
- incidence difference `no - yes`.

No p-value is an authorization gate.

## 7. Frozen evidence-strength rule

A continuous diagnostic supports its predeclared failure direction strongly when its direction-adjusted rank probability is `>= 0.70`.

A binary diagnostic supports its predeclared failure direction strongly when its incidence difference is `>= 0.25`.

A failure family is `strongly_supported` only when:

- at least two non-identical diagnostics in that family meet the strong rule; or
- for identity ambiguity, the single integer rank diagnostic is strong **and** multi-identity incidence differs by at least `0.10`.

Family decision:

- exactly one strongly supported family -> that family is the primary attribution;
- more than one -> `multi_mechanism_semantic_mismatch`;
- none -> `diffuse_or_fundamental_semantic_object_mismatch`.

`corresponding_leg_duration_mismatch` is never sufficient by itself to authorize a family or a gate.

## 8. Required controls

The runner must assert before producing the result:

- source Development parquet SHA is unchanged;
- v0.6.48 sampling commitment exactly reproduces;
- final reference bytes match the frozen SHA;
- exactly 120 hidden candidate cases are present;
- reference partition is exactly 16 yes / 104 no;
- every candidate cutoff has at least one v0.6.18-qualified identity;
- no future outcome is accessed;
- no threshold fitting is performed.

## 9. Interpretation boundary

v0.6.49 may identify a failure family, but it **cannot**:

- change v0.6.18 thresholds;
- restore a demoted gate;
- install a new qualification policy;
- alter parent direction;
- set `morphology_acceptance=true`;
- open trade or production authority.

If a strong mechanism is found, the next phase must separately freeze a mechanism-level scientific question before any candidate rule is tested. If no mechanism is strong, the next phase must revisit the semantic object / parent representation rather than mining residual gates.

## 10. Authority invariants

Regardless of v0.6.49 outcome:

- independently reference-calibrated qualification authority remains `none`;
- parent-direction winner remains unset;
- `morphology_acceptance=false`;
- `trade_authority=false`;
- `production_authority=false`.
