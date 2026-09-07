# DataHub bar-support provenance requirement — unblock two-wave morphology research after v0.6.16

Date: 2026-09-07

Status: **REQUIRED EXTERNAL DATA CONTRACT; NOT A LOCAL RESAMPLING SPEC**

Context: v0.6.16 formally adjudicated `bar_support_contract_not_recoverable_from_available_artifacts`. FactorLab declares DataHub the wall-clock bar construction owner. The frozen 5m exports identify `cn_a_session_wall_clock_offset_v1`, but contain no per-bar source support provenance (`source_minute_count` is all-null).

This document defines the minimum authoritative evidence required before guarantee-style hidden-1m structural bounds may resume. It does **not** authorize FactorLab to recreate DataHub bars locally.

## A. Preferred source-code/product-contract delivery

Provide the exact DataHub source revision (commit SHA) and product contract implementing:

```text
GET /api/v1/history/bars
frequency=5m
bar_align=session_end_label_v2 | session_wall_clock
session_offset_minutes=0..4
construction_contract=cn_a_session_wall_clock_offset_v1
```

Required semantics in code or signed product documentation:

1. source-frequency/product used for aggregation;
2. bucket membership rule, including endpoint inclusivity;
3. timestamp label rule;
4. morning/afternoon session reset behavior;
5. treatment of leading/trailing partial buckets;
6. lunch and overnight behavior;
7. OHLC aggregation rule;
8. adjustment/view handling (raw/qfq/hfq) and whether source/derived views share exact support;
9. missing-minute / causal-flat-fill behavior;
10. bar construction version / contract version.

The preferred document is the project source named by FactorLab:

`unified_datahub/docs/modules/history/session-offset-bars-whitepaper.md`

plus the implementing code revision.

## B. Acceptable provenance-rich re-export

If DataHub source cannot be shared, re-export the frozen development products with a per-bar support manifest. For **every exported native bar**, require at least:

```text
view_id
bar_timestamp / bar_end
trading_day
frequency
bar_align
session_offset_minutes
construction_contract
bar_construction_version
source_dataset_version
source_view
source_frequency
source_minute_count
support_start
support_end
support_start_inclusive
support_end_inclusive
partial_bar_flag
session_segment_id
```

Strongly preferred:

```text
source_row_ids
source_timestamps
source_rows_sha256
```

A compact source timestamp list/hash sidecar is acceptable if it is one-to-one with `view_id + bar_timestamp`.

## C. Required audit identities

The delivery must allow FactorLab to verify without inferring phase from prices:

1. every exported bar has exactly one support record;
2. source support never silently crosses lunch/overnight unless the contract explicitly says so;
3. partial-bar policy is explicit rather than inferred from absent labels;
4. recomputed source-row close at the declared closing endpoint matches native close;
5. recomputed source-row OHLC under declared aggregation semantics matches native OHLC, subject only to a separately documented price-view transformation;
6. source row count and support hashes are deterministic under replay;
7. the frozen five view row counts and timestamps remain unchanged unless a new product version is deliberately created.

Any mismatch fails closed; do not patch support locally.

## D. Frozen research products to bind

The current development artifacts are:

```text
1m_official  rows 350,561
5m_offset_0  rows 70,114
5m_offset_1  rows 67,192
5m_offset_2  rows 67,192
5m_offset_3  rows 67,193
5m_offset_4  rows 67,191
```

SHA256 identities remain those in `data/manifest.json` and v0.6.16 `data_identity.json`.

## E. What does NOT unblock the research

The following are insufficient by themselves:

- saying “bars are end-labeled” without source membership semantics;
- choosing the empirically best fitting 1m phase;
- documenting only close clocks;
- filling `source_minute_count=5` without exact support start/end;
- deleting lunch/overnight pair-legs;
- locally resampling 1m into replacement 5m bars and treating them as the frozen DataHub product.

## F. Resume condition

Only after A or B is delivered and passes the audit identities above may a new results-blind **session-aware structural-bounds protocol** be frozen.

Until then:

`morphology_replication_not_yet_accepted`

and direction/outcome/trading remain frozen.
