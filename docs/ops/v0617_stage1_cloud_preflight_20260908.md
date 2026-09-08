# v0.6.17 Stage 1 cloud preflight — implementation conformance before formal replay

Date: 2026-09-08

Status: **CLOUD PREFLIGHT COMPLETED / FORMAL REAL-DATA REPLAY NOT STARTED**

Research branch: `codex/two-wave-phase1-20260905`

Global state remains `morphology_replication_not_yet_accepted`; operational baseline remains **v0.4.3**. This document records implementation-conformance work only. It does not alter the frozen v0.6.17 preanalysis/protocol and does not authorize direction, third-wave, outcome/P&L, fresh OOS, paper trading or production.

## 1. Frozen protocol boundary

The immutable research artifacts remain:

```text
docs/research/two_wave_session_aware_information_set_bounds_preanalysis_v0617.md
  blob 77f54c7a8e3699997450eaad941ed13b1e561b3a

docs/research/two_wave_session_aware_information_set_bounds_protocol_v0617.md
  blob f0f6acd06c7ccacd331ed9938f77ff68c9519cfa

freeze commit 61eba4c80215bb07375e59d3c53e8ac2b989ff28
```

No formal v0.6.17 real-data output existed when this preflight began. The protocol and mathematical/data contract were not edited.

## 2. What the cloud actually executed

### 2.1 Repository checkout attempt

The cloud shell attempted to clone the public research branch directly:

```bash
git clone --depth 1 --branch codex/two-wave-phase1-20260905 \
  https://github.com/staryocean0/factorlab-two-wave-strategy-lab.git \
  /tmp/factorlab-two-wave
```

Actual result:

```text
exit = 128
fatal: unable to access ...
Could not resolve host: github.com
```

This is a cloud-shell outbound-DNS limitation, not a repository/code failure. The GitHub connector remained able to read exact branch files and write commits. Therefore this preflight does **not** claim a full-repository cloud `pytest` run.

### 2.2 Direct source review

The cloud independently inspected the current post-freeze implementation and tests through the GitHub evidence surface:

```text
src/factor_lab/visual_structure/two_wave/session_aware_information_set_bounds_v0617.py
tests/unit/test_two_wave_session_aware_information_set_bounds_v0617.py
src/factor_lab/visual_structure/two_wave/fine_concentration_identifiability_v0615.py
src/factor_lab/visual_structure/two_wave/step_count_normalized_concentration_v0613.py
```

The existing implementation correctly preserved the frozen core properties already represented in code/tests:

- variable-step vertex TV maximum for `m=1..6`;
- covered-path J/profile outer bounds;
- universal bounds for structural-gap legs;
- positive price-scale invariance;
- source-identity fail closed against the accepted 349,923-row DataHub surface;
- no fine-price/oracle/counterpart/direction/outcome inputs in the bound constructor;
- zero-positive-movement handling remains explicit.

### 2.3 Isolated mathematical stress check

Because a full checkout was unavailable, the cloud executed an isolated source-equivalent mathematical harness for the frozen covered-path formulas.

A 10,000-path random feasible stress check for a representative variable-step leg (`m=6` then `m=5`) produced:

```text
J/profile coverage failures = 0
```

The exact-partition guard added below was also exercised on deterministic examples:

```text
exact partition       -> PASS
missing source row    -> expected fail-closed
unexpected source row -> expected fail-closed
```

These checks are supplemental cloud evidence. They are **not** a substitute for the full local Stage 1 pytest/conformance run required by `CL-20260908-005`.

## 3. Conformance defect found before real-data replay

The frozen protocol section 9 requires fail-closed behavior when a source timestamp inside an audited transition is:

- double-assigned; or
- left unclassified.

The prior helper `validate_transition_topology()` checked:

- support timestamps are non-empty;
- duplicates inside support/gap;
- support/gap overlap;
- ordering.

But it did **not** receive the authoritative source-row universe between the two native endpoints. Therefore it could not detect a source row that was silently omitted from both support and gap.

This is an implementation-conformance bug. It is not a research-protocol or mathematical change.

## 4. Implementation-only fix

### 4.1 Exact source-row partition guard

Commit:

```text
5ed707215072076deb502953e534eea5de70b5cc
```

File:

```text
src/factor_lab/visual_structure/two_wave/session_aware_information_set_bounds_v0617.py
```

`validate_transition_topology()` now accepts an optional authoritative:

```text
source_timestamps_between_endpoints
```

When supplied, it requires:

```text
support_source_timestamps UNION gap_source_timestamps
    == exact authoritative source_timestamps_between_endpoints
```

with support/gap disjoint and every input ordered/unique. Missing or unexpected rows fail closed. The function still consumes timestamps/membership only; no source prices enter topology validation.

### 4.2 Conformance tests

Commit:

```text
2c3b28bef68da01a616e74b034555e996574406f
```

File:

```text
tests/unit/test_two_wave_session_aware_information_set_bounds_v0617.py
```

Added checks cover:

- exact support+gap partition succeeds;
- a missing authoritative source row fails closed;
- an unexpected/invented source row fails closed;
- the bound API signature contains only native OHLC + support/gap counts and excludes fine/oracle/counterpart/direction/outcome/P&L inputs.

The frozen preanalysis/protocol blobs were not modified.

## 5. N=1 profile convention guard

The cloud review also noted an edge case that must be handled conservatively during formal execution:

- the v0.6.17 mathematical helper can produce the degenerate probability-simplex value `C_inf=C_1=C_2=0` when a complete leg has `N=1` fine movement;
- the frozen v0.6.13 `concentration_profile()` implementation reports `fewer_than_two_movements` as **undefined** for `N<2`.

This preflight does not rewrite either frozen definition. The formal runner must therefore report the count of `N=1` legs **before oracle interpretation**. If any exist, it must not convert an undefined v0.6.13 oracle profile into an observed zero merely to obtain coverage. Such legs must be reported explicitly as a profile-comparability edge case and handled fail-closed in the formal report. If the count is zero, this edge has no effect on the formal sample.

## 6. Stage 1 status

Current cloud adjudication for Stage 1 is:

```text
implementation_preflight_pass_with_full_local_test_required
```

Meaning:

- no frozen-math defect was found in the reviewed covered-path formulas;
- one concrete topology completeness defect was found and fixed before real-data output;
- supplemental cloud mathematical/partition checks passed;
- a full-repository `pytest` run has **not** occurred in this cloud shell because direct GitHub checkout failed at DNS;
- formal Stage 1 remains incomplete until the local executor runs the exact branch tests in the repository environment and records commands/exit codes.

## 7. Why Stage 2–4 remain local

The accepted authoritative source surface is local-only:

```text
DataHub HEAD = ba780790acd8e9a558e4e01f9474b6e79265d818
symbol = 000852.SH
source_kind = market_index_transaction_derived_1m
dataset_version = bars_cn_index_1m_raw_canonical_market_index_baidu_3s_20000714_20260821_factorlab_unified_missing_day_repaired_v8_20260824
source rows = 349,923
date range = 2015-01-05..2020-12-31
2021+ rows = 0
```

The cloud does not possess those 349,923 source rows. The FactorLab `1m_official.parquet` 350,561-row surface is explicitly not an authorized substitute.

Therefore the legitimate execution path remains `CL-20260908-005` for:

```text
full Stage 1 local pytest/conformance
→ Stage 2 authoritative support topology + native identity gates
→ Stage 3 price-blind bound registry checkpoint
→ Stage 4 oracle coverage/tightness replay
→ local feedback
→ cloud independent review
```

## 8. Required local read-before-run update

The CL-005 executor must include this file in its read set before running formal replay:

`docs/ops/v0617_stage1_cloud_preflight_20260908.md`

In particular it must use the current post-fix helper/tests, not the older preflight implementation commits alone.

## 9. Firewalls remain unchanged

Still prohibited:

- editing the frozen v0.6.17 preanalysis/protocol;
- promoting `H_end_5` to authoritative support;
- substituting FactorLab `1m_official` for the pinned DataHub source;
- deleting structural-gap/session-boundary legs;
- using oracle values to tighten bounds;
- introducing a new concentration proxy/threshold;
- changing recognizer/matcher/projection/publication/qualification/roughness;
- opening direction, third-wave, P&L/outcome, fresh OOS, paper trading or production.

The next formal artifact remains:

`docs/research/two_wave_session_aware_information_set_bounds_results_v0617.md`
