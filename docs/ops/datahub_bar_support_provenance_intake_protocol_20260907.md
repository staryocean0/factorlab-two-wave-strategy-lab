# DataHub 5m bar-support provenance intake protocol — 2026-09-07

Status: **FROZEN OPERATIONS/PROVENANCE GATE — NOT A MORPHOLOGY VERSION**

Research branch: `codex/two-wave-phase1-20260905`

Global research state remains `morphology_replication_not_yet_accepted`; operational baseline remains **v0.4.3**. This document does not define bar construction, does not select a support hypothesis, and does not authorize direction, third-wave, outcome/P&L, fresh OOS, paper trading, or production work.

## 1. Purpose

v0.6.16 closed with:

`bar_support_contract_not_recoverable_from_available_artifacts`

The only purpose of this protocol is to decide whether newly supplied evidence is sufficiently authoritative and provenance-complete to reopen the already-defined next step: **results-blind session-aware information-set bounds preanalysis + frozen protocol**.

This intake gate is frozen before any new DataHub evidence is reviewed so that evidence acceptance is not conditioned on whether it makes a later morphology result look favorable.

## 2. Acceptable evidence classes

At least one class must pass.

### Class A — authoritative DataHub source contract

Provide the actual project DataHub repository/archive at an immutable revision containing at minimum:

- `docs/modules/history/session-offset-bars-whitepaper.md`;
- the implementation that constructs the relevant session-offset wall-clock bars, if the whitepaper delegates important semantics to code;
- preferably the matching tests/fixtures.

The evidence must be tied to an exact repository identity and commit/revision hash. A copied document is acceptable only if its source revision and file hash are reported.

### Class B — provenance-rich authoritative 5m re-export

Provide the relevant DataHub-produced 5m rows with per-bar support provenance. At minimum each row must make available:

- the view/offset identity;
- the native bar label/end timestamp used by the product;
- `source_minute_count`;
- exact `support_start`;
- exact `support_end`;
- `data_contract` and source dataset/version identity.

Strongly preferred:

- exact source-row IDs and/or source timestamps;
- DataHub commit/revision used to build the export;
- export command/config or a reproducible build receipt.

### Class C — authoritative implementation/archive copy

If the repository itself cannot be connected, an archive/copy of the authoritative DataHub contract + implementation may pass if immutable source identity, file hashes, and enough code/tests are present to determine the exact support semantics without empirical best-fit inference.

## 3. Authority gate

Reject evidence as non-authoritative if any of the following is true:

- it comes from an unrelated public project with a similar `DataHub` name;
- it is a locally reconstructed rule inferred from the current 1m/5m artifacts;
- it promotes `H_end_5`, `H_start_5`, `H_prev_open_5`, or any other empirical fit into product truth without DataHub lineage;
- it locally resamples `1m_official` to create a replacement 5m product;
- it omits source revision/identity so provenance cannot be tied back to the project DataHub authority.

## 4. Completeness gate

Before morphology work can reopen, the supplied evidence must resolve all of the following product questions without result-conditioned guessing:

1. How are the 5m support intervals defined inside each Shanghai trading session?
2. Are support endpoints inclusive/exclusive, and how are source rows assigned at the interval boundaries?
3. What is the exact relationship among bar label, availability time, support start, and support end?
4. How are morning and afternoon sessions segmented across the lunch break?
5. How are overnight transitions handled?
6. What happens to partial/session-edge bars?
7. Are offset0 and offset1–4 governed by the same support rule or by separately documented rules?
8. Which timezone/clock convention is authoritative for serialized labels and support timestamps?
9. Can every frozen native 5m row used by the research be mapped to one exact authoritative source support set, either directly from row provenance or uniquely from the documented DataHub contract?

If any answer remains ambiguous in a way that changes the possible source-information set, the blocker remains active.

## 5. Frozen identity checks for a provenance-rich re-export

When Class B evidence is supplied for the existing development sample, review must first compare identity controls rather than morphology metrics.

Expected frozen row counts are:

```text
5m_offset_0 = 70,114
5m_offset_1 = 67,192
5m_offset_2 = 67,192
5m_offset_3 = 67,193
5m_offset_4 = 67,191
```

Expected contract lineage currently declared by the frozen products includes:

```text
data_contract = cn_a_session_wall_clock_offset_v1
source_kind = market_index_transaction_derived_1m
```

A row-count, timestamp, OHLC, dataset-version, or contract mismatch is **not** to be repaired silently. It must be reported as a distinct provenance/data-identity discrepancy and adjudicated before bounds work resumes.

## 6. Session-boundary spot checks

For source-contract or re-export evidence, the cloud review must include ordinary intraday bars plus deterministic session-boundary cases covering at least:

- first complete bar of the morning session;
- last complete bar before lunch;
- first complete bar after lunch;
- last complete bar of the afternoon session;
- the overnight transition into the next trading day;
- at least one example for offset0 and each of offset1–4.

These checks are contract-verification examples only. They may not be selected because of later morphology outcomes.

## 7. Prohibited substitutions

While this gate is unresolved, continue to prohibit:

- freezing `H_end_5` as authoritative support truth;
- local 1m→5m resampling to redefine the product;
- dropping lunch/overnight/session-boundary samples to obtain deterministic bounds;
- deriving guarantee-style support from adjacent native closes alone;
- inventing another concentration/support proxy;
- reopening direction, third-wave, outcome/P&L, fresh OOS, paper trading, or production.

## 8. Intake adjudications

Only the following operational adjudications are allowed:

- `authoritative_datahub_contract_accepted`;
- `authoritative_provenance_rich_export_accepted`;
- `authoritative_archive_copy_accepted`;
- `authoritative_evidence_present_but_semantics_still_ambiguous`;
- `provenance_or_data_identity_mismatch_requires_resolution`;
- `authoritative_datahub_bar_support_evidence_still_unavailable`.

Acceptance only removes the external provenance blocker. It does **not** accept morphology.

## 9. Next step after acceptance

Only after one evidence class passes this frozen intake gate may the repository open the next formal research action:

**results-blind session-aware information-set bounds preanalysis → frozen protocol → real replay**.

The v0.6.16 empirical `H_end_5` fit remains diagnostic and is not grandfathered into the new protocol as truth.
