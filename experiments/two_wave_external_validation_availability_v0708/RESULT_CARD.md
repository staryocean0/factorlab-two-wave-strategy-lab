# v0.7.8 External-Validation Evidence Availability — Result Card

Date: 2026-09-12  
Category: `v0708_external_validation_evidence_gap_no_candidate_opened`

## Question

After v0.7.7 successfully transplanted the historical direction stack as a Development contribution but left v0.6.47/v0.6.48 external-validation weaknesses binding, is there already GitHub-visible evidence that can legitimately reopen direction authority?

## Audit universe

All **7** repositories currently accessible through the connected GitHub installation were inspected for:

1. genuinely new CSI1000 temporal material not already consumed by v0.6.47 or later validation; and
2. a new independent Two-Wave morphology/reference-label source not already consumed by v0.6.48.

## Result

Neither trigger is currently satisfied.

- No connected CSI1000 minute archive extends the validated temporal evidence beyond `2026-08-21` with genuinely new provenance.
- Repeated copies in neighboring repositories are the same DataHub snapshot and are explicitly not fresh evidence.
- No connected repository contains a new independent Two-Wave morphology/reference-label pack.
- Stock-selection / overnight annotations are not valid substitutes for Two-Wave morphology labels.

Therefore:

- candidate identity frozen: **false**
- external-validation protocol opened: **false**
- direction scoring opened: **false**
- threshold change opened: **false**
- direction winner: **null**
- morphology/trade/production authority: **false**

## Reopening condition

A future direction-authority experiment may be opened only after **both** are available and preregistered before scoring:

- **A — new temporal evidence:** a genuinely new CSI1000 minute sample not previously consumed by v0.6.47 or later validation, with immutable provenance/digest and no result-dependent filtering;
- **B — new independent morphology labels:** an independently produced Two-Wave reference-label set with frozen provenance, case universe, labeling protocol, and label-release timing.

## Evidence

- Audit record: `docs/research/TWO_WAVE_EXTERNAL_VALIDATION_EVIDENCE_AVAILABILITY_V0708.md`
- Machine adjudication: `experiments/two_wave_external_validation_availability_v0708/ADJUDICATION.json`
- Upstream direction adjudication: `experiments/two_wave_lifecycle_qualified_direction_v0707/ADJUDICATION.json`

No scientific score was generated in v0.7.8; this stage is an evidence-availability closure, not a model experiment.
