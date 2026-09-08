# R4 statistical-state Stage-1 adjudication — 2026-09-08

Program identity: `broad_reversal_mean_reversion_discovery_program_v1`  
Research identity: `R4_statistical_state_extremes_stage1_v1`

Execution receipt:

`docs/research/cloud_session_20260908_broad_rmr_R4_statistical_state_receipt_v1.json`

Execution: GitHub Actions run `34190340146`, job `101946928577`, conclusion `success`.

All frozen identity checks, synthetic/scientific-boundary tests, market runner, authority checks and artifact upload passed.

## Evidence boundary

- BUILD: 2015–2018 consumed development;
- chronological check: 2019–2020, not fresh;
- source max day: 2020-12-31;
- primary view: `5m_offset_0`;
- parent: mature published L5 M0 structure;
- lower activity scale: L3 only for the frozen 96-bar publication count;
- past-only normalization: preceding 100 mature L5 parents;
- common baseline: `abs_drift + log_amplitude`;
- no combined state model, threshold search, window search, post-2020 access, PnL or morphology-acceptance claim.

## R4-A — path inefficiency state

State:

`R4_A_inefficiency = - robust_z(parent_eff)`

Resolved supply is ample:

- BUILD `615`;
- 2019 `160`;
- 2020 `151`.

The fitted coefficient has the preregistered positive sign (`+0.25460`), but predictive quality is worse:

### Pooled

- geometry baseline Brier `0.2505775`;
- candidate Brier `0.2510705` — worse;
- baseline log-loss `0.6943209`;
- candidate log-loss `0.6953346` — worse.

### Annual

- 2019 Brier `0.2508153 -> 0.2515442` — worse;
- 2020 Brier `0.2503256 -> 0.2505686` — worse.

Decision:

`close_R4_A_inefficiency`

Descriptive state dynamics are weakly persistent rather than clearly reverting (`current/next corr ≈ +0.297`, absolute-state contraction share ≈ `0.504`). This descriptive field is not part of the price-path gate.

## R4-B — lower-scale event-density state

State:

`R4_B_event_density = robust_z(count of mature L3 publications in prior 96 bars)`

Resolved supply:

- BUILD `515`;
- 2019 `159`;
- 2020 `136`.

The candidate fails both predictive and direction gates:

### Pooled

- baseline Brier `0.2503372`;
- candidate Brier `0.2536279` — materially worse for this low-effect screen;
- baseline log-loss `0.6938590`;
- candidate log-loss `0.7005310` — worse.

### Annual

- 2019 Brier `0.2492665 -> 0.2509108` — worse;
- 2020 Brier `0.2515888 -> 0.2568046` — worse.

State coefficient is `-0.13013`, opposite the preregistered positive failure-risk direction.

Decision:

`close_R4_B_event_density`

The event-density state itself is persistent (`current/next corr ≈ +0.571`) and has a low absolute-state contraction share (`~0.179`). That persistence is not price alpha and cannot rescue the failed price-path gate.

## R4-C — parent amplitude extremity

State:

`R4_C_amplitude_extremity = abs(robust_z(log(parent_amplitude)))`

Resolved supply:

- BUILD `615`;
- 2019 `160`;
- 2020 `151`.

The coefficient is positive (`+0.09174`) as preregistered, but probability quality is again worse:

### Pooled

- baseline Brier `0.2505775`;
- candidate Brier `0.2522137` — worse;
- baseline log-loss `0.6943209`;
- candidate log-loss `0.6976171` — worse.

### Annual

- 2019 Brier `0.2508153 -> 0.2514976` — worse;
- 2020 Brier `0.2503256 -> 0.2529724` — worse.

Decision:

`close_R4_C_amplitude_extremity`

Its descriptive state dynamics are also persistent (`current/next corr ≈ +0.541`) with contraction share ≈ `0.496`; again, this is not evidence of price mean reversion.

## Overall R4 decision

`qualified_candidate_ids = []`

No R4 candidate qualifies for specialist review.

R4 Stage-1 v1 is closed. Do not rescue it by combining A/B/C, changing the 100-parent reference, changing the 96-bar density window, splitting high/low amplitude after results, selecting one calendar year, adding skewness/jumps/technical indicators, or escalating to a deep state model under this identity.

## Program-level finding

This correct-repository broad sweep now supports an important negative result:

> **Neither parent-state geometry nor the tested statistical-state variables provide a robust, low-capacity price mean-reversion discriminator on the consumed 2015–2020 evidence under the frozen definitions.**

More specifically:

- R1 remains unresolved because the first-passage resolved check sample is insufficient even after one results-blind measurement revision;
- R2 has sufficient evidence and is closed because parent range state worsens the severity baseline;
- R3 has sufficient evidence and is closed because the preregistered deterioration direction is contradicted;
- R4 has sufficient evidence and all three independent statistical-state candidates worsen the common geometry baseline.

This is a valid direction-finder outcome. It is not a mandate to keep inventing indicators on the same consumed window.

Production authority remains `false`.
