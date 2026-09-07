# v0.6.16 Frozen protocol — native 5m bar-support semantics audit

Date: 2026-09-07

Status: **FROZEN BEFORE ANY v0.6.16 SUPPORT-HYPOTHESIS RESULT IS READ**

This audit changes no data, identity, matcher, projection, publication, qualification, direction, outcome or trading logic.

## 1. Hard controls

Use exactly the frozen development products:

```text
1m_official rows = 350,561
5m_offset_0 rows = 70,114
5m_offset_1 rows = 67,192
5m_offset_2 rows = 67,192
5m_offset_3 rows = 67,193
5m_offset_4 rows = 67,191
```

SHA256 values must match `data/manifest.json`. No local resampling.

## 2. Authoritative-source audit

Record whether the linked GitHub environment contains the DataHub product source named by FactorLab:

`unified_datahub/docs/modules/history/session-offset-bars-whitepaper.md`

If unavailable, do not substitute an unrelated public repository.

Record the exact FactorLab statements that DataHub owns wall-clock construction and the exact `bar_align`, close-clock and construction-contract values.

## 3. Product provenance audit

For every 5m product report:

- parquet row count;
- `data_contract` min/max stats;
- `dataset_version` min/max stats;
- `source_kind` min/max stats;
- parquet physical/logical state of `source_minute_count`;
- non-null count of `source_minute_count`;
- presence/absence of explicit support-start, support-end or source-row-id columns.

The support contract is considered self-describing only if source support is explicit, not merely if a bar-end label is present.

## 4. Fixed data-falsification hypotheses

Evaluate three frozen hypotheses without selecting a winner:

### H_end_5
For each native bar label t within one session, candidate support is the five official 1m labels ending at t.

### H_start_5
Candidate support is the five official 1m labels starting at t.

### H_prev_open_5
When the previous native label and current label enclose exactly five official 1m increments, candidate support is the five official 1m rows after the previous label through current label.

For each view/hypothesis report:

- evaluable bar count;
- native close equals candidate last close count;
- all candidate 1m closes inside native [low,high] count;
- candidate close min/max inside native [low,high] count (same diagnostic expressed per bar);
- native high/low exactly equal candidate close extrema count (diagnostic only).

Do not use these metrics to promote a hypothesis into a product contract.

## 5. Session-boundary audit

Separately enumerate native adjacent-label transitions by number of official 1m index increments and by lunch/overnight/session-local category. Never force non-five transitions into H_prev_open_5.

## 6. Required outputs

Write:

`cloud_results/cloud_chat_v0616_bar_support_semantics/`

with:

```text
summary.json
authoritative_source.json
product_provenance.json
support_hypotheses.json
session_boundary.json
data_identity.json
execution_receipt.json
```

and formal report:

`docs/research/two_wave_bar_support_semantics_results_v0616.md`

## 7. Allowed adjudications

Only:

- `bar_support_contract_recovered_from_authoritative_source`;
- `artifact_support_provenance_missing_but_one_documented_contract_is_sufficient`;
- `bar_support_contract_not_recoverable_from_available_artifacts`;
- `mixed_support_semantics_require_datahub_source_access`.

No empirical best-fit support may be called authoritative.

## 8. Global firewall

If authoritative support is not recoverable, v0.6.15 structural bounds may not be repaired by local phase inference. The next authorized action is to obtain DataHub contract/source or regenerate provenance-rich bars. Global state remains `morphology_replication_not_yet_accepted`.
