# Two-Wave v0.6.48 pre-label scoring semantics clarification

Date: 2026-09-12
Status: **frozen before any independent v0.6.48 labels exist and before model/reference scoring begins**

This note resolves two implementation ambiguities in section 9 of the already-frozen `TWO_WAVE_INDEPENDENT_REFERENCE_LABEL_CONSTRUCTION_V0648_PROTOCOL.md`. It does **not** change sample membership, annotation semantics, label-quality gates, calibration-support thresholds, or scientific authority.

## Primary model state

For the candidate-stratum calibration gates in protocol section 9.1, the primary model parent state is the frozen **v0.6.25 absolute-margin erosion-consensus rescue** applied on top of the frozen **v0.6.18 qualification policy**.

D1 is reported on the same candidate cases as a **descriptive comparator only**. D1 does not control any v0.6.48 pass/fail gate.

No D2, PAWCT, later rejected Range-recovery challenger, post-2020 retune, or new classifier is eligible for v0.6.48 scoring.

## Concurrent qualified identities at one case cutoff

The pre-label determinacy audit (`SCORING_DETERMINACY_AUDIT.json`) was run before any independent annotations existed. Among the 120 frozen candidate cases:

- 118 cutoffs contain exactly one v0.6.18-qualified identity;
- 2 cutoffs contain exactly two v0.6.18-qualified identities;
- both multi-identity cutoffs are unanimous in D1 state;
- both multi-identity cutoffs are unanimous in v0.6.25 state;
- therefore there are zero candidate cases with a case-level v0.6.25 state ambiguity.

The case-level model state is the unique state shared by every v0.6.18-qualified identity at that cutoff. If this unanimity assertion is ever violated by replay drift, scoring fails closed; no identity may be selected after seeing reference labels.

## Frozen denominators and metrics

`reference-confirmed two-wave` means finalized `two_complete_same_scale_waves=yes`. Finalized `no` and `uncertain` cases are not silently dropped from the presence denominator.

Candidate stratum (`n=120`):

- reference-confirmed presence fraction = number of finalized `yes` candidate cases / 120;
- primary parent-state exact agreement = number of reference-confirmed candidate cases where v0.6.25 exactly equals finalized `parent_state` / number of reference-confirmed candidate cases;
- UpTrend-vs-DownTrend opposite-conflict rate = number of reference-confirmed candidate cases where `{v0.6.25, reference} = {uptrend, downtrend}` / number of reference-confirmed candidate cases;
- primary uncertain rate is reported both over all 120 candidate cases and over reference-confirmed candidate cases;
- the four-state confusion matrix uses only reference-confirmed candidate cases, with rows = finalized reference state and columns = v0.6.25 state.

The same exact-agreement, opposite-conflict, uncertain-rate and confusion diagnostics are also reported for D1, but are descriptive only.

Control stratum (`n=120`):

- human-positive control miss fraction = number of finalized `yes` control cases / 120.

No model parent-state metric is defined for control cases because they are deliberately selected as non-v0.6.18-qualified cutoffs.

Year diagnostics repeat the same formulas within each fixed 20-candidate / 20-control year slice and remain descriptive only.

## Frozen calibration gates remain unchanged

The only v0.6.48 calibration-support gates remain:

- candidate reference-confirmed presence fraction >= 0.80;
- v0.6.25 parent-state exact agreement >= 0.85 among reference-confirmed candidate cases;
- v0.6.25 UpTrend/DownTrend opposite-conflict rate <= 0.02 using the denominator defined above;
- human-positive control miss fraction <= 0.20.

These gates may be evaluated only after the two first-pass sheets are frozen, first-pass label-quality gates are evaluated, all required third-party adjudications are completed while model-blind, and the final reference CSV is frozen by SHA-256.

Even if every gate passes, `morphology_acceptance=false`, parent-direction winner remains unset, `trade_authority=false`, and `production_authority=false`. v0.6.48 can establish Development-period independent-reference calibration support only.