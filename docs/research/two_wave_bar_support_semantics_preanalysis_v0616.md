# v0.6.16 Preanalysis — native 5m bar-support semantics / contract recovery audit

Date: 2026-09-07

Status: **WRITTEN BEFORE ANY v0.6.16 SUPPORT-HYPOTHESIS FIT OUTPUT IS READ**

## 1. Why v0.6.16 precedes any session-aware bound repair

v0.6.15 failed its frozen data-consistency gate because the assumed mapping

`adjacent native closes -> exactly five supplied-1m increments constrained by current native bar OHLC`

is materially false on the offset products, especially at lunch/overnight boundaries. A smaller set of exact-five transitions also has supplied-1m closes outside the assumed current-bar `[low,high]` support.

The next step therefore cannot invent a session-aware bound formula before the native product's actual source-minute support is known.

## 2. Source-of-truth hierarchy frozen before inspection

Support semantics may be established only by, in order:

1. DataHub implementation or DataHub product whitepaper explicitly defining source rows / bucket support;
2. immutable product metadata or per-row provenance in the exported parquet;
3. FactorLab contract code/whitepaper that explicitly delegates a precise support rule.

Observed agreement with supplied 1m prices is **not** sufficient to promote a support hypothesis into a contract.

## 3. Already-known contract facts

FactorLab `session_offset_defaults.py` states:

- wall-clock bars are constructed by DataHub;
- official 1m clocks are 09:31–11:30 and 13:01–15:00;
- 5m offsets have close clocks built separately in each morning/afternoon session;
- offset0 uses `session_end_label_v2`; offsets1–4 use `session_wall_clock`;
- construction contract is `cn_a_session_wall_clock_offset_v1` for offset bars.

The FactorLab whitepaper explicitly names the DataHub session-offset-bars whitepaper as product truth, but that separate DataHub repository is not available through the linked GitHub installation in this session.

## 4. Artifact self-description audit

For each frozen `5m_offset_0..4.parquet`, report:

- `data_contract`, `dataset_version`, `source_kind`, view/frequency;
- whether `source_minute_count` is populated per row;
- whether any explicit support-start/support-end/source-row IDs exist;
- whether timestamp fields describe only bar end/availability or source support.

No inferred phase is allowed in this section.

## 5. Fixed falsification hypotheses

Only as diagnostics, test all fixed endpoint-label hypotheses below against supplied 1m. None may become contract by best fit.

For a native bar labeled at minute `t`, using same-session official trading-minute order:

- H_end_5: five 1m rows ending at t;
- H_start_5: five 1m rows starting at t;
- H_prev_open_5: five rows immediately after the previous native label when exactly five exist.

For each hypothesis report exact-close agreement plus OHLC envelope consistency (native high/low must contain candidate 1m closes; optionally native high/low equality to candidate extrema is diagnostic only).

Session-boundary transitions are reported separately and never forced into a five-row hypothesis.

## 6. Adjudication

Allowed conclusions only:

- `bar_support_contract_recovered_from_authoritative_source`;
- `artifact_support_provenance_missing_but_one_documented_contract_is_sufficient`;
- `bar_support_contract_not_recoverable_from_available_artifacts`;
- `mixed_support_semantics_require_datahub_source_access`.

A data-fit hypothesis alone cannot yield either of the first two conclusions.

## 7. Consequence for later bounds

If support is not authoritatively recoverable, deterministic OHLC-to-hidden-1m bounds are not auditable on these frozen products. The next engineering requirement must be either:

- obtain DataHub source/product contract; or
- regenerate/export bars with per-row `source_minute_count` plus exact support/source-row provenance.

Do not alter matcher, identity, qualification or data by local resampling.

## 8. Global firewall

`morphology_replication_not_yet_accepted` and operational baseline v0.4.3 remain unchanged. No direction/outcome/trading work is authorized.
