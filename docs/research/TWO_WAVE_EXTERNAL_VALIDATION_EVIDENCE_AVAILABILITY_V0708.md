# Two-Wave v0.7.8 external-validation evidence availability audit

Date: 2026-09-12  
Status: `complete_read_only_audit_external_evidence_gap_no_candidate_opened`

## Purpose

v0.7.7 established that the historical v0.6.25 D1-primary erosion-consensus rescue is technically transplantable onto the v0.7.5/v0.7.6 lifecycle-publication stack and materially active on the 115 qualified publications, but it remains **Development-only and externally blocked**. The binding constraints are unchanged:

- v0.6.47 temporal replication: D1 exact `242/253` versus v0.6.25 exact `238/253`;
- v0.6.48 independent reference calibration: both D1 and v0.6.25 exact `5/16`, with only `16/120` candidate cases having reference-confirmed presence.

The v0.7.7 adjudication therefore permits reopening direction authority only after a **new preregistered external-validation protocol** backed by **genuinely external evidence** that directly addresses both weaknesses without tuning on held-out outcomes.

This v0.7.8 step is a read-only availability audit. It does not score D1 or v0.6.25, does not change any threshold, and does not open a direction challenger.

## Connected GitHub universe audited

The authenticated GitHub installation currently exposes seven repositories owned by `staryocean0`:

1. `factorlab-two-wave-strategy-lab`
2. `factorlab-star50-filter-lab`
3. `factorlab-overnight-open-lab`
4. `factorlab-overnight-gap-fill-repeat-2026`
5. `factorlab-trend-reversion-regime-lab`
6. `factorlab-multifactor-stock-lab`
7. `factorlab-multifactor-research-private`

No other connected repository is available through the current GitHub installation.

## Evidence inventory

### 1. `factorlab-two-wave-strategy-lab`

This is the consumer research repository. Its existing post-Development external evidence is already part of the v0.6.47/v0.6.48 lineage and therefore cannot be relabeled as new evidence for v0.7.8.

Current v0.7.7 governance remains:

- direction winner: `null`;
- morphology acceptance: `false`;
- trade authority: `false`;
- production authority: `false`;
- any reopening requires new external evidence.

### 2. `factorlab-star50-filter-lab`

This repository supplied the temporal material already consumed by v0.6.47.

The frozen v0.6.47 protocol used:

- 2024 CSI1000 1m;
- 2025 CSI1000 1m;
- sealed 2026 CSI1000 1m from `2026-01-05..2026-08-21`.

The current 2026 archive manifest still reports:

- `actual_last_day = 2026-08-21`;
- `post_snapshot_rows = 0`;
- `fresh_oos = false`;
- source role `held_out_validation_material`.

Therefore this repository contains no post-2026-08-21 CSI1000 minute extension that is presently available as a new v0.7.8 temporal sample.

### 3. `factorlab-overnight-open-lab`

The visible 2026 CSI1000 repeat pack ends at `2026-08-21` and explicitly states:

- `post_2026-08-21_included = false`;
- `fresh_oos = false`;
- `scientific_role = repeat_only_not_fresh`.

Its CSI1000 1m input is sourced from the same DataHub export used by the STAR50 2026 archive (`source_sha256 = aeacff04b268c166faac333ec7ab9d840abcd347d82cb3bcee0218d058fc7423`). It is therefore not an independent temporal evidence source.

The associated `annotated_panel_2025Q4_to_20260821.parquet` contains overnight-gap fields (`open_0931`, `prev_close`, `close_1500`, `overnight_gap`) for the overnight project. It is not an independent Two-Wave morphology/reference-label set and cannot resolve v0.6.48.

### 4. `factorlab-overnight-gap-fill-repeat-2026`

This temporary repository is retired. Its README states that the complete repeat-only pack was consolidated into `factorlab-overnight-open-lab`; the parquet files were byte-identical Git blobs there. Scientific role remains `repeat_only_not_fresh`.

It is a duplicate surface, not a new evidence source.

### 5. `factorlab-trend-reversion-regime-lab`

The CSI1000 1m directory currently contains annual files `2015.parquet` through `2025.parquet` only. There is no `2026.parquet` in the current tree.

Hence it provides no new post-2026-08-21 temporal sample. No independent Two-Wave morphology/reference-label package is exposed by this repository.

### 6. `factorlab-multifactor-stock-lab`

The repository data README explicitly states:

- A-share daily/factor research surfaces through 2025;
- `2026 rows are absent`;
- `fresh_oos = false`.

The one listed 2026-dated market reference is a broad-market daily CSV, not CSI1000 minute morphology material. This repository cannot resolve either v0.6.47 or v0.6.48.

### 7. `factorlab-multifactor-research-private`

The repository README states `No full one-minute dataset`. Its current package catalog reports:

- `observation_end = 2022-12-31`;
- `full_minute_data = false`;
- `fresh_oos = false`.

The packages are REAKA stock-selection / portfolio replay and validation assets, not Two-Wave morphology reference labels. This repository cannot supply the required v0.7.8 evidence.

## Adjudication

No connected GitHub repository currently supplies a qualifying new evidence package that can legitimately reopen v0.6.25 direction authority.

Primary category:

`v0708_external_validation_evidence_gap_no_candidate_opened`

Frozen state:

- `candidate_identity_frozen = false`;
- `external_validation_protocol_opened = false`;
- `direction_scoring_opened = false`;
- `threshold_change_opened = false`;
- `result_opened = false`;
- `direction_winner = null`;
- `morphology_acceptance = false`;
- `trade_authority = false`;
- `production_authority = false`.

## Exact reopening triggers

A future v0.7.9-or-later external-validation protocol may be opened only after the GitHub-visible evidence inventory contains material satisfying **both blocker classes**. The two blocker classes may be satisfied by one combined sealed package or by two separately sealed packages.

### Trigger A — new temporal replication material

There must be a genuinely new CSI1000 minute-bar sample that was not consumed by v0.6.47, for example a sealed post-`2026-08-21` continuation. It must have:

- explicit first/last trading day;
- immutable source commit/ref;
- content SHA256 or equivalent immutable digest;
- source/data-role declaration;
- no direction-result-dependent filtering;
- no use to retune v0.6.25 thresholds before formal scoring.

A duplicate copy, alternate repository path, or repackaging of the existing `2026-01-05..2026-08-21` DataHub source is not new evidence.

### Trigger B — new independent morphology/reference evidence

There must be an independent Two-Wave morphology/reference-label set not already consumed by v0.6.48. It must provide enough information to evaluate parent presence and parent direction without deriving labels from D1/v0.6.25 outputs or from future trading/PnL outcomes.

At minimum its provenance, labeling protocol, frozen case universe, and label-release timing must be sealed before model scoring.

A price-only archive cannot by itself resolve v0.6.48.

## Forbidden shortcuts

Do not:

- reuse the v0.6.47 2024/2025/2026 samples and call them new external evidence;
- treat a duplicate GitHub copy of the same DataHub export as independent evidence;
- use the overnight-gap annotated panel as a Two-Wave morphology label source;
- open another in-sample direction rescue/tuning branch while the evidence gap remains;
- retune v0.6.25 margin, Huber boundaries, qualification thresholds, or lifecycle semantics in response to this audit;
- install v0.6.25 as direction winner from v0.7.7 Development support;
- grant morphology, trade, or production authority.

Until Trigger A and Trigger B are satisfied, the correct next state is **blocked on external evidence availability, with no direction candidate opened**.
