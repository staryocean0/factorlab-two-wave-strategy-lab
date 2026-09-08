# M1 R1/R2 adjudication — 2026-09-08

Program identity: `broad_reversal_mean_reversion_discovery_program_v1`  
Measurement identity: `M1_parent_structure_plus_single_shock_event_adapter_v1`

Execution receipt:

`docs/research/cloud_session_20260908_broad_rmr_M1_R1_R2_outcome_receipt_v1.json`

Frozen execution: GitHub Actions run `34189627407`, custom workflow `broad-rmr-M1-R1-R2-outcomes`, conclusion `success`.

All custom steps passed: frozen blob identity checks, synthetic outcome-boundary tests, frozen runner, evidence/authority checks and aggregate receipt upload. The concurrently triggered old `bounded-theme-validation` workflow failed because it still encodes the historical narrow package scope; that is an infrastructure/scope mismatch and is not evidence about M1 economics.

## Evidence boundary

- BUILD: 2015–2018 consumed development;
- chronological check: 2019 and 2020, not fresh;
- max source day read: 2020-12-31;
- no post-2020 rows;
- parent fixed at mature published L5 on `5m_offset_0`;
- R1 shock fraction fixed at `0.5` from pre-existing v0.4.3 amplitude-ratio semantics;
- R2 uses the first strict close outside the frozen parent envelope with no extra threshold;
- no scale/offset/threshold search;
- no R3 reopen;
- no PnL or production authority.

## R1 — intact parent + single counter-shock

Decision:

`R1_M1_evidence_insufficient_resolved_check_supply_below_frozen_gate`

Trigger supply passed M1-S0, but first-passage resolution supply did not:

- BUILD resolved: `168` — passes minimum `150`;
- 2019 resolved: `40` — fails minimum `50`;
- 2020 resolved: `39` — fails minimum `50`.

Therefore the exact protocol requires an evidence-insufficient conclusion. The lane may **not** be rejected as a mechanism based on this run, and the probability metrics may not be used to tune or lower the event definition.

For completeness, the underpowered descriptive metrics are not favorable:

- pooled severity-only Brier `0.2343235`;
- pooled parent+severity Brier `0.2447903`;
- pooled severity-only log-loss `0.6623678`;
- pooled parent+severity log-loss `0.6841713`;
- integrity projection `-0.12734`.

2019 is approximately flat-to-worse for parent+severity (`0.2318811 -> 0.2327422`), while 2020 is materially worse (`0.2368286 -> 0.2571473`).

These numbers are descriptive only because the frozen resolved-supply gate failed. They must not be used to define a new shock fraction, lower the 50-event annual minimum, select one year, or flip the integrity direction.

### R1 next-action rule

This broad identity has already received one results-blind measurement revision after the complete-finer-two-wave event proved too sparse. Do **not** continue M2/M3 event engineering on the same 2015–2020 evidence by default. R1 remains an unresolved mechanism hypothesis rather than a progression candidate.

A future R1 revisit requires either:

- materially more data with roles frozen before outcomes; or
- an independently theory-driven event definition approved by a new program review before execution.

## R2 — parent envelope + first close excursion

Decision:

`R2_M1_closed_parent_range_state_adds_no_incremental_reentry_information`

Resolved supply is ample:

- BUILD: `657`;
- 2019: `161`;
- 2020: `151`.

The sign projection is in the preregistered range-like direction (`+0.11569`), but predictive quality is worse than simple excursion severity at every primary comparison:

### Pooled 2019–2020

- severity-only Brier: `0.2485738`;
- parent+excursion Brier: `0.2512218` — worse;
- severity-only log-loss: `0.6902362`;
- parent+excursion log-loss: `0.6956335` — worse.

Parent state alone is also worse:

- Brier `0.2517657`;
- log-loss `0.6967904`.

### 2019

- severity-only Brier `0.2478570`;
- parent+excursion Brier `0.2504643` — worse.

### 2020

- severity-only Brier `0.2493380`;
- parent+excursion Brier `0.2520294` — worse.

Thus the frozen pooled Brier, pooled log-loss and both-year improvement gates all fail with adequate supply. R2 M1 is closed.

Do not rescue it by adding a minimum breakout distance, break speed, local volatility filter, alternate range algorithm, one-direction split, another offset or PnL selection under this identity.

## R3 remains closed

R3 Stage-1 v1 was already closed because ample evidence contradicted the preregistered deterioration direction. M1 did not reopen R3 and this adjudication does not change that status.

## Broad-program conclusion after R1/R2/R3

No first-round price-path mechanism is eligible for specialist promotion:

- R1: unresolved / evidence insufficient after one measurement revision;
- R2: closed with adequate evidence;
- R3: closed with adequate evidence.

This is an informative outcome, not a reason to keep patching the same ideas.

The next broad research budget should move to one **independent statistical-state mechanism class** that was part of the broad charter before these results, not another R1/R2/R3 repair.

The first statistical-state screen must preserve the key distinction:

> **A statistic reverting toward its own normal state is not evidence of price mean reversion.**

A candidate should progress only if the state variable adds stable causal information about a separately frozen price recovery/extension or parent-transition outcome beyond a simple geometry baseline.

Production authority remains `false`.
