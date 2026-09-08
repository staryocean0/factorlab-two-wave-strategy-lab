# v0.6.17 session-aware information-set bounds — cloud freeze receipt

Date: 2026-09-08

Status: **CLOUD FROZEN / FORMAL REAL-DATA REPLAY NOT YET EXECUTED**

Research branch: `codex/two-wave-phase1-20260905`

Global state remains `morphology_replication_not_yet_accepted`; operational baseline remains **v0.4.3**. This receipt does not authorize direction/D1/D2/PAWCT, third-wave, outcome/P&L, fresh OOS, paper trading or production.

## 1. Provenance blocker closure

The DataHub intake gate has been independently reviewed in:

`docs/ops/datahub_bar_support_provenance_cloud_review_20260907.md`

Formal intake adjudication:

`authoritative_archive_copy_accepted`

GitHub issue #4 is closed as **completed**. This closes only the external bar-support provenance blocker; it is not morphology acceptance.

## 2. Immutable v0.6.17 research protocol

The following results-blind artifacts are now frozen for the formal replay:

```text
preanalysis:
  docs/research/two_wave_session_aware_information_set_bounds_preanalysis_v0617.md
  git blob SHA1 = 77f54c7a8e3699997450eaad941ed13b1e561b3a

protocol:
  docs/research/two_wave_session_aware_information_set_bounds_protocol_v0617.md
  git blob SHA1 = f0f6acd06c7ccacd331ed9938f77ff68c9519cfa

protocol freeze commit:
  61eba4c80215bb07375e59d3c53e8ac2b989ff28
```

These two research documents are immutable for the upcoming formal replay. If a real-data result exposes a bug or impossible precondition, the run must fail closed and report it. Do not edit the frozen protocol to make a result pass.

## 3. Accepted DataHub authority and source identity

Freeze the support authority to the accepted archive lineage:

```text
DataHub committed HEAD = ba780790acd8e9a558e4e01f9474b6e79265d818
session-offset implementation ancestor = 2c7b070f38f061378e89c19d183da9ccef9a6c88
whitepaper last-touch ancestor = d31b140e35132911aa6ab164deaa9afcbb02b0ff
symbol = 000852.SH
source_kind = market_index_transaction_derived_1m
dataset_version = bars_cn_index_1m_raw_canonical_market_index_baidu_3s_20000714_20260821_factorlab_unified_missing_day_repaired_v8_20260824
date_range = 2015-01-05..2020-12-31
DataHub source rows = 349,923
2021+ rows = 0
```

Important frozen semantics:

- offset0 uses the official `cn_a_session_end_label_no_noon_partial_v2` route;
- offset1–4 use `cn_a_session_wall_clock_offset_v1`;
- the frozen offset0 parquet metadata incorrectly/stalely declares wall-clock v1, but authoritative official-route replay reproduces all 70,114 labels and OHLC exactly; retain this as a metadata caveat and never use that frozen field to choose offset0 support;
- DataHub serialized `T09:35:00Z` is a Shanghai wall-clock-labelled construction string, not UTC 01:35 for bucket assignment;
- exact actual support is the accepted DataHub source rows assigned by the authoritative function, including missing-minute occupancy; do not synthesize absent source minutes;
- FactorLab `1m_official.parquet` (350,561 rows) is not an accepted substitute for the 349,923-row DataHub source surface unless a separately frozen exact row-level bridge is first established.

## 4. Post-freeze implementation state

After the protocol freeze, three implementation-only commits were added without changing the frozen protocol:

```text
3e49adf2a37c8b947d88ea0f46e17da8537ea074
  implement v0.6.17 session-aware bound helper

2f29faf1e09c9fe78eb6fccdf00b88a7d0904eac
  add v0.6.17 synthetic bound tests

a96422d6aff1baff4192ef1c41eef04ef3eed054
  clean v0.6.17 source identity gate
```

Relevant files:

```text
src/factor_lab/visual_structure/two_wave/session_aware_information_set_bounds_v0617.py
tests/unit/test_two_wave_session_aware_information_set_bounds_v0617.py
```

These files are candidate implementation of the frozen protocol. They may be corrected only for protocol-conformance bugs found before or during execution; any correction must preserve the frozen mathematical/data contract and be documented before interpreting affected real-data outputs.

## 5. Formal replay firewall

At the time of this receipt, no formal results document exists at:

`docs/research/two_wave_session_aware_information_set_bounds_results_v0617.md`

The next executor is authorized to implement/complete the support-topology runner and execute the frozen v0.6.17 real replay only.

The executor must not:

- reopen or alter the preanalysis/protocol;
- promote v0.6.16 `H_end_5` to truth;
- locally resample FactorLab 1m into replacement 5m bars;
- delete lunch/overnight/session-boundary or structural-gap legs;
- use source prices inside the topology/bound constructor before the oracle-validation phase;
- condition interval widths on observed oracle results;
- invent a new point proxy or threshold;
- change recognizer/matcher/projection/publication/qualification/roughness;
- open direction, third-wave, outcomes/P&L, fresh OOS, paper trading or production.

## 6. Required formal output

Follow section 14 of the frozen protocol exactly. Compact evidence belongs under:

`cloud_results/cloud_chat_v0617_session_aware_bounds/`

The formal report belongs at:

`docs/research/two_wave_session_aware_information_set_bounds_results_v0617.md`

Large row-level topology may stay local only if its SHA256, row count, schema, deterministic generation command and local location are recorded in `execution_receipt.json`.

## 7. Handoff

The formal replay is assigned under `CL-20260908-005` in `docs/ops/cloud_local_communication.md`.

Cloud review after local execution is mandatory. A local green run is not itself a morphology verdict and must not update the global state.