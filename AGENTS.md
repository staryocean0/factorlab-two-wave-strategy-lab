# Broad Reversal / Mean-Reversion Research Control Plane

This repository is a **broad reversal / mean-reversion direction finder**, not a single-strategy optimizer.

Repository-wide mission:

> **Use causal multi-scale measurements to distinguish temporary lower-scale deviations inside an intact parent state from true parent-state changes, and compare multiple low-capacity mechanisms before taking any one mechanism deep.**

Historical two-wave work is preserved as `M0_two_wave_structure_measurement_foundation`. M0 is measurement infrastructure, not automatic trading alpha.

No production, paper-trading, Layer-4, FactorLab-current-pointer mutation, or unrestricted PnL-selection authority is granted by this repository.

## Repository-wide authority order

When deciding what the project is doing now, read in this order:

1. `CONTINUE_HERE.md`
2. `docs/governance/reversal_mean_reversion_program_charter_v1.json`
3. `docs/governance/reversal_mean_reversion_data_reuse_validation_policy_v1.md`
4. `docs/governance/reversal_mean_reversion_program_state_v1.json`
5. `docs/research/reversal_mean_reversion_program_whitepaper_v2.md`
6. this `AGENTS.md`
7. post-reset lane protocols / cloud reviews
8. historical v0.x documents only inside their own M0 / historical identity

An unfinished `next_action` in an older two-wave document does not control repository-wide direction.

## Data is reusable; blackbox qualification is scarce

The project uses three evidence roles.

### TRAIN

Current interval: `2015-01-05..2018-12-31`.

TRAIN is a reusable research asset. It may be repeatedly used for:

- model fitting;
- feature construction;
- threshold exploration when a research identity permits it;
- diagnostics;
- case inspection;
- failure analysis;
- mechanism redesign.

Using TRAIN once does not consume it.

### VALIDATION

Current interval: `2019-01-01..2020-12-31`.

VALIDATION is also reusable. It may be repeatedly used to:

- check chronological stability;
- inspect years/events/details;
- diagnose why a model failed;
- revise a model and validate again.

Once details are inspected, the data is still valid as VALIDATION; it simply is not a never-seen blackbox.

### BLACKBOX

No BLACKBOX interval is currently assigned.

BLACKBOX is reserved only for a sufficiently mature candidate. It should normally expose only predeclared aggregate confirmation outputs. If its details are opened for diagnosis, that interval is demoted to VALIDATION and a future blackbox must be assigned separately if another unseen confirmation is desired.

**Data itself is not disposable. Only never-seen blackbox qualification is consumable.**

Do not mechanically burn one calendar year per research attempt. By default prefer pooled effective sample size plus chronological stability diagnostics over arbitrary `N per natural year` gates unless the year-specific question is scientifically central.

Historical frozen gates remain historical facts and must not be retroactively rewritten.

## M0 — two-wave measurement foundation

M0 covers causal complete-wave and parent-structure measurement, including:

- online pivots and complete waves;
- same-scale pairing;
- parent drift / envelope / overlap;
- path efficiency / roughness / duration / density;
- streaming / replay / prefix invariance;
- session / offset / source-support semantics;
- morphology replication infrastructure.

Current global morphology status remains:

`morphology_replication_not_yet_accepted`

Operational baseline remains `v0.4.3`.

### v0.6.17 accepted measurement capability

`CL-20260908-005` is completed and cloud-reviewed.

Accepted verdict:

`session_aware_bounds_valid_but_structural_gap_nonidentifiability_is_material`

Accepted capability:

`interval_valued_session_aware_path_information_bounds`

This does **not** mean morphology is accepted and does **not** mean native 5m OHLC reveals the exact fine path.

Any future fine-path feature must declare one of:

1. admitted actual finer-source direct measurement;
2. fully-enveloped finite interval measurement;
3. structural-gap partial-identification interval.

Do not turn an interval midpoint or convenient proxy into observed truth. Do not drop structural-gap events merely because they hurt a strategy result.

## Historical broad-lane evidence

Historical results remain evidence for their exact identities but do not make the underlying data unusable.

- `R1_cross_scale_pullback`: historically unresolved because the old gate had insufficient resolved samples; mechanism not rejected. New research identities may continue on TRAIN/VALIDATION.
- `R2_range_boundary_reversion`: historical low-capacity M1 identity closed; independent new identities are allowed but must not rewrite the old result.
- `R3_structural_exhaustion_transition`: historical v1 preregistered direction was falsified; independent new transition identities are allowed but cannot reinterpret that failure.
- `R4_statistical_state_extremes`: historical v1 candidates failed to add stable information; other independently motivated statistical-state questions remain researchable.
- `T1_transitory_component_after_extreme_intraday_shock_v1`: historical 5-sigma/960-bar identity closed before outcome on its frozen old supply gate; future independent shock identities are allowed.

A statistical property reverting toward its own normal state is **not** by itself evidence of price mean reversion.

## Active lane — R5 multiscale serial dependence

Current active identity:

`R5_multiscale_serial_dependence_state_v1`

Independent theory motivation: short-horizon mean reversion and slower positive memory can coexist at different scales; trend and reversal are therefore scale-dependent states rather than permanent asset labels.

Frozen artifacts:

- preanalysis: `docs/research/reversal_mean_reversion_R5_multiscale_serial_dependence_preanalysis_20260908.md`
- protocol: `docs/governance/reversal_mean_reversion_R5_multiscale_serial_dependence_protocol_v1.json`
- execution freeze: `docs/governance/reversal_mean_reversion_R5_execution_freeze_v1.json`
- runner: `scripts/run_broad_rmr_R5_multiscale_serial_dependence.py`
- tests: `tests/unit/test_broad_rmr_R5_multiscale_serial_dependence.py`
- local task: `CL-20260908-007`
- handoff: `docs/ops/cl_20260908_007_R5_multiscale_serial_dependence_handoff.md`

R5 uses TRAIN and VALIDATION only; no BLACKBOX exists for this lane.

R5-A first establishes whether short-negative / slower-positive memory states have enough supply. R5-B asks whether anti-persistence changes next-return reversal strength. R5-C asks whether a counter-trend 5m shock is more likely to recover toward the preceding slow direction when slower positive memory and short anti-persistence are stronger.

Do not escalate a failed low-capacity R5 result into HMM/rSLDS/Koopman as a rescue. Those model classes require their own incremental rationale.

## Common scientific coordinate system

Every new reversal hypothesis must declare before its result is interpreted:

1. **scale** — lower / current / parent;
2. **parent state** — trend / range / transition / unknown;
3. **deviation object** — what is abnormal;
4. **recovery/failure criterion** — what counts as reversion and what counts as state change.

A mean can be a line, band, trajectory, wave structure, distribution, relative relationship or statistical state. Do not reduce mean reversion to moving-average distance.

## Research style

- Keep broad discovery shallow before going deep.
- Prefer simple statistical baselines before HMM/rSLDS/Koopman/deep models.
- TRAIN and VALIDATION can support repeated model iteration.
- Preserve every historical receipt and failed identity; do not rewrite old conclusions when a new identity is created.
- Do not select shallow research by trading PnL.
- Do not create favorable sign/year/time-of-day subgroups after seeing results and call them new evidence.
- BLACKBOX is assigned only after a candidate is mature enough for a final aggregate-only confirmation.

## Data contract

Current shipped market data used by R5:

```text
instrument = 000852.SH
file = data/development/5m_offset_0.parquet
rows = 70,114
sha256 = bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48
range = 2015-01-05..2020-12-31
```

It is index signal data, not a tradable fill surface.

For any identity that uses DataHub exact source support, obey that identity's frozen source contract. For v0.6.17 specifically, authoritative source support was the 349,923-row DataHub source surface; FactorLab `1m_official` was not an exact substitute.

Do not silently fill missing bars, synthesize OHLC, locally resample a new product when the protocol says use a supplied native view, or invent timestamp/timezone semantics.

## Causal requirements

- Candidate pivots may move; confirmed historical events may not be rewritten by future rows.
- Save occurrence, confirmation, classification and executable times separately when relevant.
- No centered windows, bilateral smoothing, future extrema, full-sample normalization or hindsight parameters in online signals.
- Batch replay must use the same causal semantics.
- OHLC alone does not reveal within-bar high/low order.
- Algorithm-generated structure labels are not independent morphology ground truth.
- Every result must state TRAIN / VALIDATION / BLACKBOX role truthfully.

## Current execution order

1. Preserve the reusable TRAIN / VALIDATION / BLACKBOX governance.
2. Execute frozen R5 locally via `CL-20260908-007` because the current cloud session has no direct Parquet execution surface.
3. Push only the compact R5 receipt using `[skip ci]`.
4. Cloud reviews the receipt and distinguishes `local_reported` from `cloud_reviewed`.
5. If R5 has partial/full support, continue diagnosis and iteration on TRAIN/VALIDATION; do not prematurely allocate a BLACKBOX.
6. If R5 low-capacity mechanisms fail, do not deep-model rescue them.
7. New data, when available, expands TRAIN/VALIDATION coverage and can later provide a small BLACKBOX; old data remains usable.

## 云端—本地交接协议

This protocol is active only when the user explicitly activates cloud/local collaboration or asks this cloud session to continue work that requires local execution. It is active in the current collaboration.

### Execution priority

When active:

1. current cloud session direct execution;
2. local large-model execution;
3. GitHub Actions only as a last resort.

Writing code or commands is not execution. Report the actual execution location and evidence.

If the cloud lacks the required local market data or filesystem:

- write an executable task-specific handoff under `docs/ops/` and, where practical, a pointer in `docs/ops/cloud_local_communication.md`;
- give the task ID, branch/commit, frozen artifacts, exact commands, expected compact output and acceptance rules;
- keep large market data and large row-level artifacts local;
- push only compact receipts/reports unless the data contract requires otherwise.

Local feedback must state actual commit, commands, exit codes, source identity, output paths, failures/unverified items, and must label itself `local_reported` rather than `cloud_reviewed`.

Cloud review must independently compare the feedback against frozen code/protocol/source gates before changing authority state.

Do not use GitHub Actions merely to probe quota. Current R5 task does not authorize Actions.

## Frozen authority boundaries

Unless a later higher-authority document explicitly changes them:

- no FactorLab current-registry mutation;
- no Layer-4 trading execution;
- no fresh-OOS claim from TRAIN/VALIDATION;
- no paper trading;
- no production;
- no unrestricted PnL-based parameter selection.

Production authority = `false`.
