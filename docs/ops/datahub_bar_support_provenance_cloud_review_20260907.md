# DataHub 5m bar-support provenance — cloud independent review

Date: 2026-09-07

Research branch: `codex/two-wave-phase1-20260905`

Frozen intake gate: `docs/ops/datahub_bar_support_provenance_intake_protocol_20260907.md`

Local handoff: `CL-20260907-004`

## Adjudication

> **`authoritative_archive_copy_accepted`**

The external DataHub bar-support provenance blocker introduced by v0.6.16 is **removed**.

This is an operations/provenance adjudication only. It does **not** accept morphology, does not change the operational baseline from v0.4.3, and does not authorize direction/D1/D2/PAWCT, third-wave, outcome/P&L, fresh OOS, paper trading or production. Global state remains:

`morphology_replication_not_yet_accepted`

## 1. Cloud review scope

The cloud review independently read the archived committed DataHub whitepaper, implementation and tests copied into:

`cloud_results/cl_20260907_004_datahub_bar_support_provenance/archive/`

and reviewed:

- `SOURCE_IDENTITY.json`;
- `HASHES.sha256`;
- `contract_answers.md`;
- `run_identity_diagnostic.py`;
- `identity_diagnostic.json`;
- deterministic `session_boundary_samples.json`;
- local `test_receipt.json`.

The local pytest receipt is treated as **local execution evidence**, not as a cloud rerun. The cloud acceptance is based on immutable-source identity plus independent static contract/implementation/test review and review of the read-only identity diagnostic design/output.

## 2. Authority / immutability gate — PASS

The evidence is tied to a local project DataHub git repository:

- local repository: `/home/starryocean/桌面/量化/unified_datahub`;
- branch: `main`;
- committed HEAD: `ba780790acd8e9a558e4e01f9474b6e79265d818`;
- session-offset implementation commit: `2c7b070f38f061378e89c19d183da9ccef9a6c88`, recorded as an ancestor of HEAD;
- whitepaper last-touch commit: `d31b140e35132911aa6ab164deaa9afcbb02b0ff`, recorded as an ancestor of HEAD.

The local working tree was dirty, but the evidence binding explicitly excludes uncommitted changes and uses **HEAD committed blobs only**.

The copied archive contains the whitepaper, workflow, construction contract, deriver/query implementation and matching tests. `SOURCE_IDENTITY.json` records both SHA256 and the original DataHub git-blob SHA1 at HEAD. The blobs stored in this FactorLab evidence archive have the same content-addressed git blob identities as the recorded DataHub HEAD blobs. This is sufficient immutable lineage for frozen intake **Class C**; it is not an unrelated public DataHub substitute and is not an empirical reconstruction from FactorLab bars.

## 3. Contract semantics gate — PASS

The committed contract and implementation determine 5m support assignment without using v0.6.16 `H_end_5` or any best-fit hypothesis.

### 3.1 Session windows

CN-A support is segmented into independent Shanghai wall-clock sessions:

- morning: 09:30–11:30;
- afternoon: 13:00–15:00.

Bars do not cross lunch or overnight.

### 3.2 Offset0 versus offset1–4

They are separate documented construction paths:

- offset0: official `cn_a_session_end_label_no_noon_partial_v2` route;
- offset1–4: additive `cn_a_session_wall_clock_offset_v1` route.

`derive_bars_from_1m` dispatches official requests to the official session bucket case and non-official offsets to the wall-clock bucket case. Both operate directly on source 1m wall-clock labels; no second hidden resampler was found in the reviewed construction path.

### 3.3 Source-row assignment

For 5m wall-clock offset > 0, the first complete bucket of a session can contain six 1m end labels because the grid-start minute and the grid-start+5 minute are both assigned to the first bucket. Later complete buckets normally contain five end labels. Missing source minutes can reduce actual occupancy.

Therefore a guarantee-style information-set model may **not** hard-code `source_minute_count = 5` for every native 5m bar.

### 3.4 Labels and metadata

The authoritative bucket label is the Shanghai session wall-clock end label. DataHub serialized timestamps such as `T09:35:00Z` are wall-clock-labelled source strings in this construction path; FactorLab separately retains/normalizes UTC audit timestamps.

`bar_open_ts` construction metadata is not an exact `support_start`: for some buckets it can equal the previous bucket label while the actual first source minute is later. Frozen `available_at=15:30+08:00` is also not the per-bar source-support endpoint.

### 3.5 Partial/session-edge handling

- official offset0 retains the official session-end capped bucket;
- wall-clock offset > 0 drops pre-grid minutes and, by default, incomplete tail buckets whose label would exceed the session end;
- no lunch/overnight aggregation is permitted;
- no standalone 13:00 bar is created by the reviewed rules.

These semantics resolve the nine frozen intake questions without result-conditioned guessing.

## 4. Test evidence — PASS as corroboration

The archived tests cover the official/additive split, session clocks, offset fail-closed behavior, lunch segmentation, tail handling and raw 5m aggregation behavior.

Local execution receipt:

```text
PYTHONPATH=src .venv/bin/python -m pytest \
  tests/unit/storage/test_session_offset_contract.py \
  tests/unit/storage/test_bars_deriver.py -q --tb=short

exit 0
33 passed in 0.81s
```

This receipt is not re-labelled as cloud execution. It corroborates the committed-source review.

## 5. Frozen-product identity diagnostic — PASS for lineage binding

The read-only diagnostic uses the committed DataHub `assign_intraday_bucket_minute` implementation against:

- symbol `000852.SH`;
- 2015-01-05 through 2020-12-31 only;
- dataset version `bars_cn_index_1m_raw_canonical_market_index_baidu_3s_20000714_20260821_factorlab_unified_missing_day_repaired_v8_20260824`;
- source kind `market_index_transaction_derived_1m`;
- 349,923 DataHub source rows;
- no 2021+ rows.

For all five frozen native 5m views, authoritative-contract replay produced:

```text
offset0: 70,114 labels; only_frozen=0; only_derived=0; OHLC mismatch=0
offset1: 67,192 labels; only_frozen=0; only_derived=0; OHLC mismatch=0
offset2: 67,192 labels; only_frozen=0; only_derived=0; OHLC mismatch=0
offset3: 67,193 labels; only_frozen=0; only_derived=0; OHLC mismatch=0
offset4: 67,191 labels; only_frozen=0; only_derived=0; OHLC mismatch=0
```

This is not used to invent the contract; the contract was already fixed by the archived DataHub source. It is used only to bind that authoritative construction to the frozen FactorLab products.

Deterministic boundary samples cover the first morning bar, last pre-lunch bar, first post-lunch bar, last afternoon bar and overnight transition for offset0–4.

## 6. Two retained caveats

### 6.1 offset0 contract-id metadata mismatch

The frozen offset0 parquet declares `data_contract = cn_a_session_wall_clock_offset_v1`, while the committed DataHub request normalization routes offset0 through the official v2 contract.

This discrepancy is **not silently repaired**. For the frozen 5m offset0 product, however, the diagnostic using the actual official route reproduces every frozen label and OHLC row exactly. The discrepancy therefore does not leave the 5m support assignment ambiguous for this research sample; it is retained as a lineage-metadata caveat.

This conclusion is strictly scoped to the frozen 5m offset0 product and must not be generalized to 15m/30m/60m products.

### 6.2 DataHub source rows are not the same surface as FactorLab `1m_official`

The authoritative DataHub diagnostic source has 349,923 rows for the frozen date range, while the FactorLab manifest records 350,561 rows for `data/development/1m_official.parquet`.

Therefore future bounds code must **not** silently substitute FactorLab `1m_official` as the exact DataHub actual-support source. The next protocol must fail closed unless it either:

1. consumes the exact DataHub source/support mapping used by the accepted contract lineage; or
2. establishes a separate results-blind row-level bridge proving which FactorLab 1m rows correspond to the exact DataHub support set.

This is an execution/data-identity requirement for the next replay, not a reason to reject the recovered authoritative construction contract itself.

## 7. Frozen intake decision

Class C satisfies the frozen gate:

- authoritative lineage: PASS;
- immutable source identity/hashes: PASS;
- contract sufficient to determine source assignment semantics: PASS;
- implementation path consistent with the contract: PASS;
- matching tests present and local receipt passed: PASS;
- deterministic session-boundary evidence present: PASS;
- frozen-product labels/OHLC bound to the authoritative implementation: PASS;
- prohibited best-fit/local-resample substitutions: not used.

Formal adjudication:

> **`authoritative_archive_copy_accepted`**

Issue #4 may be closed as the external provenance acquisition blocker. Closure does not constitute morphology acceptance.

## 8. Authorized next formal research action

Open, results-blind:

**v0.6.17 session-aware information-set bounds preanalysis → frozen protocol → real replay**.

The new model must build information sets from authoritative per-bar session support semantics, not from adjacent native-close spacing, and must retain a fail-closed source-identity gate before real-data interpretation.
