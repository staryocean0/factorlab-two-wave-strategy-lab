# Two-Wave v0.6.48 pre-label execution status

Date: 2026-09-12
Status: **pre-label implementation complete; external blinded annotations still required**

## What is complete

The v0.6.48 Development-period independent-reference evidence surface is fully prepared up to the point that genuinely independent human/external labels are required.

- Frozen construction protocol: `TWO_WAVE_INDEPENDENT_REFERENCE_LABEL_CONSTRUCTION_V0648_PROTOCOL.md`.
- Formal blinded packet run: `34628102738`.
- Frozen 240-case sampling commitment: `f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8`.
- Blinded packet SHA256: `4c08c8d3f32c6e222acb3c4236fa8f39428ff25349deae16d6f49dca2901566e`.
- First-pass A/B label validator and frozen agreement gates: implemented and tested.
- Pre-label case-level scoring determinacy audit: complete before any independent labels were present.
- Third-party disagreement-only adjudication packet builder: implemented before labels.
- Final reference-label freezer with SHA256 commitments: implemented before labels.
- Primary v0.6.25 calibration scoring metrics and D1 descriptive comparator: implemented before labels.
- Post-reference scoring runner: implemented before labels and fails closed unless the frozen first-pass quality gate authorizes scoring.

## Pre-label scoring determinacy audit

Formal audit workflow run: `34630392872`.  
Formal aggregate audit result commit: `bdf57c1c50e9675b1459c81060e47b7a12892a69`.  
Audit file: `experiments/two_wave_independent_reference_label_v0648/SCORING_DETERMINACY_AUDIT.json`.

The frozen 120 candidate cases have:

- `118` cutoffs with exactly one v0.6.18-qualified parent identity;
- `2` cutoffs with exactly two v0.6.18-qualified parent identities;
- `0` multi-identity D1 state disagreements;
- `0` multi-identity v0.6.25 state disagreements.

Therefore case-level v0.6.25 state is deterministic without choosing an identity after reference labels are observed. If future replay ever violates this unanimity assertion, scoring fails closed.

Pre-label v0.6.25 case-state counts are recorded only as model-side determinacy controls, not compared to reference labels: `41 downtrend / 39 uptrend / 40 uncertain`. D1 descriptive counts are `33 downtrend / 29 uptrend / 58 uncertain`.

## Frozen post-label sequence

No redesign is permitted after the independent labels arrive. The sequence is already fixed:

1. receive two complete first-pass CSVs from different independent annotators;
2. freeze the exact SHA256 of both CSVs before comparison;
3. run the frozen first-pass exact-agreement/Cohen-kappa quality gates;
4. if there are disagreements, generate a packet containing only those case IDs, their original blinded charts and the two frozen first-pass labels;
5. a distinct third adjudicator must attest independence from A/B and model blinding; every disagreement must be resolved;
6. freeze `FINAL_REFERENCE_LABELS.csv` and its SHA256;
7. only if the first-pass quality gates passed may hidden candidate/control mapping and frozen model state be unblinded for aggregate scoring;
8. evaluate the already-frozen calibration gates with v0.6.25 as the primary model and D1 as descriptive only.

The exact scoring denominators and primary/comparator roles are frozen in `TWO_WAVE_V0648_PRELABEL_SCORING_SEMANTICS_CLARIFICATION.md`.

## What is not complete

No independent A/B annotations have been supplied yet. Consequently:

- `independent_labels_present=false`;
- `final_reference_labels_frozen=false`;
- `model_reference_scoring_started=false`;
- no v0.6.48 calibration verdict exists yet;
- `morphology_acceptance=false`;
- parent-direction winner remains unset;
- `trade_authority=false`;
- `production_authority=false`.

It is scientifically invalid to substitute model outputs, migrated recognizer outputs, repository adjudication records, the user, or this assistant for the two genuinely independent blinded annotators.