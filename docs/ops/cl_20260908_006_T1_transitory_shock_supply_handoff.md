# CL-20260908-006 — T1 extreme intraday shock supply/alignment audit

Date: 2026-09-08

Status: **OPEN / LOCAL EXECUTION REQUIRED / CLOUD REVIEW PENDING**

Research identity:

`T1_transitory_component_after_extreme_intraday_shock_v1`

This task is independent of R1/R2/R3/R4 and does not reopen them. It is also independent of M0 task `CL-20260908-005`; the two local tasks may be executed separately.

## Why local execution is required

The current cloud container was tested again and still cannot resolve `raw.githubusercontent.com` / GitHub DNS, so it cannot read the repository Parquet files directly. The repository collaboration protocol therefore routes this lightweight data audit to the local model before considering GitHub Actions.

GitHub Actions are **not authorized** for this task.

## Scientific boundary

This task is **supply/alignment only**.

It may identify extreme native 5m event bars and inspect only the already-completed 1m path inside each event bar.

It must **not** read or construct:

- future returns after the event close;
- reversal / continuation first-passage labels;
- Brier/log-loss/model coefficients;
- PnL;
- post-2020 statistics.

Passing supply does not authorize outcomes. A separate cloud-reviewed authorization is required.

## Required frozen identities

Before execution, verify these Git blob SHAs exactly:

```text
docs/research/reversal_mean_reversion_round2_transitory_shock_theory_intake_20260908.md
  792e768ed8d7fb1808583a49f16d42b9c7438f97

docs/governance/reversal_mean_reversion_T1_transitory_shock_supply_protocol_v1.json
  49615926077f1f2e45e08f427f745363581e2e26

scripts/audit_broad_rmr_T1_transitory_shock_supply.py
  9bc4533dacb5914ee63b5d9d82a745694031b917

tests/unit/test_broad_rmr_T1_transitory_shock_supply.py
  e6acd417a74e4164e77f195db739b5328b8e0542
```

Execution freeze:

`docs/governance/reversal_mean_reversion_T1_supply_execution_freeze_v1.json`

Do not edit the frozen theory/protocol/runner/tests before the first real supply audit. If a genuine implementation bug blocks execution, stop and report it first; do not silently repair and continue under the same frozen identity.

## Required data identities

```text
data/development/5m_offset_0.parquet
  rows = 70,114
  SHA256 = bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48

data/development/1m_official.parquet
  rows = 350,561
  SHA256 = 755217afce9dec383e48cd46d591402fa90dc50897abeb3dc7097c9a18a109d4

symbol = 000852.SH
max day = 2020-12-31
```

This T1 broad-strategy audit uses the admitted FactorLab development package above. Do not confuse it with the separate authoritative DataHub 349,923-row source required by M0 `CL-20260908-005`.

## Frozen event definition

- native view: `5m_offset_0` only;
- event return: `log(close/open)`;
- recent reference: exactly preceding 960 native 5m bars, current bar excluded;
- center: median;
- scale: `1.4826 * MAD`;
- extreme event: absolute robust z >= `5.0`;
- no threshold search;
- no alternate offset search;
- no sign-specific thresholds.

## Frozen fine-path gate

For each extreme native 5m bar:

- select existing 1m terminal rows on the same trading day with `bar_end_shanghai` in `(5m_end-5min, 5m_end]`;
- require exactly 5 rows;
- require unique ordered timestamps;
- require final 1m close to match the native 5m close at the frozen tolerance;
- no missing-row fill;
- no 1m→5m replacement resample.

Aligned events may report only the completed-event `within_bar_retrace_fraction` descriptive distribution.

## Commands

From the latest `codex/two-wave-phase1-20260905` checkout:

```bash
pytest -q tests/unit/test_broad_rmr_T1_transitory_shock_supply.py
```

If and only if tests pass:

```bash
python scripts/audit_broad_rmr_T1_transitory_shock_supply.py \
  --output docs/research/local_broad_rmr_T1_transitory_shock_supply_receipt_v1.json
```

Do not run any outcome script afterward.

## Frozen supply gate

Aligned-event minimums:

```text
BUILD 2015-2018 >= 150
2019 >= 50
2020 >= 50
```

If any fails:

`T1_current_data_event_supply_insufficient`

Do not lower the 5-sigma threshold or 960-bar window.

If all pass:

`T1_supply_passed_outcomes_still_sealed_pending_cloud_review_and_separate_authorization`

Do not open outcomes locally.

## Required local feedback

Push only the compact receipt and any execution-note needed to explain a failure. The receipt must contain or be accompanied by:

1. exact FactorLab branch + commit SHA;
2. exact commands and exit codes;
3. pytest passed/failed test count;
4. actual 5m/1m SHA256 + row counts;
5. BUILD/2019/2020 extreme-event counts;
6. BUILD/2019/2020 aligned-event counts;
7. rejection counts by reason;
8. descriptive `within_bar_retrace_fraction` summary;
9. supply gate status;
10. explicit flags:
   - `post_event_outcomes_read=false`
   - `future_return_read=false`
   - `reversal_or_continuation_label_read=false`
   - `PnL_read=false`
   - `post_2020_rows_read=false`
   - `outcome_execution_authorized=false`
11. explicit statement: `云端复核尚未发生`.

Commit local feedback with `[skip ci]`.

## Cloud next step

After the receipt is pushed, cloud will verify frozen blob/source identities and audit the supply logic. Only a cloud-reviewed PASS can permit a **separately frozen** post-event outcome runner.
