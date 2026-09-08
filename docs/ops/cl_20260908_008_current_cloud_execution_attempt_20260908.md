# CL-20260908-008 — current cloud execution attempt

Date: 2026-09-08

Task: `R5_B1_stability_shape_diagnostic_v1`

Execution surface: `current_cloud_session`

Status: `BLOCKED_BEFORE_FROZEN_TEST_AND_REAL_DIAGNOSTIC_BY_BINARY_ACCESS_SURFACE`

## 1. Branch identity

Repository: `staryocean0/factorlab-two-wave-strategy-lab`

Research branch: `codex/two-wave-phase1-20260905`

The branch was compared against the previously known head:

`1b8e98f927d6e9e8f4770ce01fbf7020cb7dfefb`

GitHub compare returned `identical`, `ahead_by=0`, `behind_by=0`.

## 2. Frozen artifact identity re-check

Current branch blobs match the CL-008 execution freeze:

```text
preanalysis  6407af17c2815685677cd261deebe1606d340cd3
protocol     34ae31a18a3e470f6374d1490a0826c98cd46bc1
runner       a5f1f4dea7fb46a6d42c7d91f3404b1ec8022f28
tests        539b6bba9f76ebf00584a40b9483bd6c692c30b2
```

No protocol, runner, gate, lag, window, model or feature was changed.

## 3. Source existence vs execution access

The required source is present in the public repository:

```text
path       data/development/5m_offset_0.parquet
Git blob   30eddf3020d311fb409660a8c296f6309383745f
expected rows 70,114
expected sha256 bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48
instrument 000852.SH
max day    2020-12-31
```

The expected row count and SHA256 above are frozen source-contract values; this cloud session did **not** independently recompute them because it could not obtain the raw bytes.

Current-cloud access attempts:

1. `git clone --branch codex/two-wave-phase1-20260905 --single-branch ...` failed in the execution container with `Could not resolve host: github.com`.
2. DNS checks for `github.com`, `raw.githubusercontent.com`, and `api.github.com` all failed with temporary name-resolution errors in the execution container.
3. GitHub connector can list the Parquet and confirms its Git blob, but direct binary fetch is rejected because the fetch surface accepts UTF-8 text only.
4. `fetch_blob` on the Parquet blob failed with `UnicodeDecodeError` on binary bytes.
5. `fetch_file(..., encoding=base64)` returned the correct blob identity but an empty content field for this multi-megabyte file, so no bytes were recoverable.
6. The host download path could not be used because the raw GitHub binary URL could not be successfully pre-viewed/cached by the web fetch surface.

Therefore this is **not** evidence that the file is absent, the sample is insufficient, or the fields are insufficient. It is specifically a current-session `GitHub binary -> executable filesystem` transport failure.

## 4. CL-008 execution status

The required frozen command was **not** reported as executed:

```bash
pytest -q tests/unit/test_broad_rmr_R5_B1_stability_shape.py
```

The real-data diagnostic was also **not** executed:

```bash
python scripts/diagnose_broad_rmr_R5_B1_stability_shape.py \
  --output docs/research/local_broad_rmr_R5_B1_stability_shape_diagnostic_receipt_v1.json
```

No D1 day-breadth result was observed.

No D2 anti-persistence shape result was observed.

No CL-008 scientific adjudication is claimed from this cloud attempt.

In particular, this operational failure is **not** being relabelled as `R5_B1_diagnostic_execution_drift_or_insufficient`, because the frozen runner never reached its entry-reproduction gate on the real source.

## 5. Governance truth

```text
BLACKBOX_read = false
post_2020_rows_read = false
PnL_read = false
fresh_OOS_claim = false
scientific_outcome_seen = false
production_authority = false
```

GitHub Actions were not triggered. The CL-008 freeze/handoff explicitly forbids that execution surface for this task.

## 6. Next executable step

The existing local handoff remains authoritative:

`docs/ops/cl_20260908_008_R5_B1_stability_shape_diagnostic_handoff.md`

Run exactly the frozen test command and then the frozen diagnostic command on an execution surface that can read the tracked Parquet. Push only the compact receipt with `[skip ci]`; cloud review can then independently check entry reproduction, D1, D2 and the allowed adjudication.
