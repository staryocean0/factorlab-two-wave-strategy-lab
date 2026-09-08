# Broad reversal Stage-1 R1/R2/R3 adjudication — 2026-09-08

Program identity: `broad_reversal_mean_reversion_discovery_program_v1`

Execution receipt:

`docs/research/cloud_session_20260908_broad_rmr_stage1_R1_R2_R3_receipt_v1.json`

Execution location: GitHub Actions run `34188765085`, after direct cloud clone failed DNS and no direct local-model execution tool was available in this session.

Scientific status of the run:

- BUILD: 2015–2018 consumed development material;
- chronological check: 2019–2020, not fresh;
- post-2020 rows unread;
- parent/finer representation levels were frozen results-blind at L5/L3;
- no PnL, calibration, threshold search, morphology-acceptance claim or production authority.

## R1 — cross-scale pullback

Decision:

`R1_STAGE1_v1_evidence_insufficient_event_measurement_too_sparse`

Resolved event supply:

- BUILD: `9`;
- 2019: `5`;
- 2020: `3`.

This fails the frozen supply gate by a wide margin, so probability comparisons are not interpretable and no parent-integrity direction may be claimed.

### What failed

The event adapter required all of the following simultaneously:

1. a mature published L5 parent two-wave structure;
2. a mature published L3 two-wave structure one octave finer;
3. the finer structure to begin only after parent publication;
4. the finer direction to oppose the parent;
5. publication within the parent's causal 96-bar validity window;
6. event price strictly between recovery and structural-failure boundaries;
7. first-passage resolution before parent expiry / year-end censor.

Although L5 and L3 structure supply individually was abundant, their fully published nested intersection is too sparse.

### Scientific interpretation

This is a **measurement/event-supply failure**, not evidence against the economic mechanism that an intact parent trend may absorb a sharp lower-scale counter-move.

The user's original mechanism is a sudden lower-scale adverse move. Requiring that adverse move itself already form another complete two-wave parent structure is stronger than the scientific question requires and delays event time substantially.

R1 v1 must not be rescued by changing L5/L3, selecting another offset, weakening gates after seeing Brier, or using its tiny outcome sample. A new event-measurement identity may be defined using the same frozen parent state but a causal single counter-shock instead of a complete lower two-wave identity.

## R2 — range-boundary / failed-breakout reversion

Decision:

`R2_STAGE1_v1_evidence_insufficient_sparse_and_chronologically_unstable`

Resolved event supply:

- BUILD: `37`;
- 2019: `11`;
- 2020: `10`.

The supply gate fails. Within the tiny check sample, the combined parent+excursion model is slightly better pooled than excursion severity alone, but:

- 2019 improves;
- 2020 worsens;
- sample sizes are far below the frozen minimum.

Therefore no R2 mechanism claim is allowed.

As with R1, the sparse intersection is partly created by requiring an already-complete finer L3 two-wave identity to be the boundary-excursion carrier. A new measurement identity may use the same published L5 parent envelope and the **first causal 5m close excursion beyond that envelope**, without using the observed tiny-sample performance to choose parameters.

## R3 — structural exhaustion / transition

Decision:

`R3_STAGE1_v1_closed_predeclared_deterioration_direction_falsified`

Resolved supply is ample:

- BUILD: `744`;
- 2019: `172`;
- 2020: `144`.

Both preregistered deterioration candidates slightly improve probability metrics relative to the simple current-drift baseline:

### Translation decay

- pooled Brier: `0.2450432 -> 0.2441101`;
- 2019: `0.2357626 -> 0.2341661`;
- 2020: `0.2561284 -> 0.2559877`;
- standardized deterioration coefficient: `-0.04937`.

### Quality decay

- pooled Brier: `0.2450432 -> 0.2434792`;
- 2019: `0.2357626 -> 0.2332191`;
- 2020: `0.2561284 -> 0.2557344`;
- standardized deterioration coefficient: `-0.12734`.

The frozen hypothesis required deterioration coefficient `> 0`: more translation/quality deterioration should raise parent-failure probability. Both coefficients are negative.

Therefore the preregistered scientific direction is contradicted. The small Brier improvement cannot be post-hoc reinterpreted as success.

R3 v1 is closed. Do not flip the sign after results, rename strengthening as exhaustion, or escalate to HMM/Koopman/deep regimes as a rescue under this identity.

## Program-level lesson

The first correct-repository screen separates two kinds of failure that must not be conflated:

1. **R1/R2: evidence supply insufficient because the lower deviation was over-specified as a complete two-wave structure.**
2. **R3: evidence sufficient, but the preregistered deterioration direction is falsified.**

This supports a cleaner architectural split:

> Use complete two-wave M0 structures primarily to describe the **parent state**. Use a lighter causal event definition for the **lower-scale deviation/shock** when the economic question is about a sudden move before a new lower parent structure is fully formed.

That split is scientific, not a result-rescue threshold change: it follows directly from the original mechanism question and from the observed event-supply deficiency, not from choosing a better-performing result cell.

## Authorized next step

A new measurement identity may be frozen results-blind for R1/R2 only:

`M1_parent_structure_plus_single_shock_event_adapter_v1`

Constraints:

- parent remains the already frozen L5 mature published M0 structure on `5m_offset_0`;
- no new parent-scale or offset search;
- R1 lower deviation becomes a first causal single counter-shock defined from parent amplitude using a pre-existing M0 amplitude-ratio constant, not a tuned result threshold;
- R2 boundary deviation becomes the first causal 5m close outside the frozen parent envelope;
- BUILD/check dates and year-end censor stay unchanged;
- R1/R2 old v1 outcomes may not be used to select thresholds or gates;
- R3 v1 remains closed and is not rerun under M1.

Production authority remains `false`.
