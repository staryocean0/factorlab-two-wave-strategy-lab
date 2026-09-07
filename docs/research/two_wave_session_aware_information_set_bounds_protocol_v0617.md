# v0.6.17 Frozen protocol — session-aware information-set bounds

Date: 2026-09-07

Status: **FROZEN BEFORE ANY v0.6.17 REAL-DATA BOUND OUTPUT IS READ**

Authoritative DataHub intake result:

`authoritative_archive_copy_accepted`

This protocol changes no recognition identity, matcher, projection, publication, qualification, roughness candidate, direction, outcome or trading logic.

## 1. Frozen upstream controls

Before interpretation reproduce the existing research controls without selecting new samples:

```text
published identities = 38,176 / 36,737 / 36,619 / 36,480 / 36,264
published raw strict pairs = 8,381 / 5,770 / 6,204 / 9,098 = 29,453
both-qualified = 482
qualification disagreements = 699
target repaired = 80 = 56 agreement + 24 disagreement
fine profile defined = 737,070 published legs
oracle-comparable strict pair-leg observations = 117,805
```

Operational baseline remains v0.4.3. Global state remains `morphology_replication_not_yet_accepted`.

Any upstream behavioral drift stops interpretation.

## 2. Authoritative construction identity

Freeze support construction to the accepted DataHub archive lineage:

```text
DataHub HEAD = ba780790acd8e9a558e4e01f9474b6e79265d818
session-offset implementation ancestor = 2c7b070f38f061378e89c19d183da9ccef9a6c88
whitepaper last-touch ancestor = d31b140e35132911aa6ab164deaa9afcbb02b0ff
period_minutes = 5
```

Required committed source is the archive reviewed in:

`docs/ops/datahub_bar_support_provenance_cloud_review_20260907.md`

Do not replace this with v0.6.16 `H_end_5`, adjacent-close inference, pandas/local resampling or a newly invented clock rule.

## 3. Source-data identity gate

Real replay must use the exact accepted DataHub source/support topology or a separately frozen exact row-level bridge.

Expected DataHub diagnostic source identity:

```text
symbol = 000852.SH
role = development_material_source_only
date range = 2015-01-05..2020-12-31
source kind = market_index_transaction_derived_1m
dataset version = bars_cn_index_1m_raw_canonical_market_index_baidu_3s_20000714_20260821_factorlab_unified_missing_day_repaired_v8_20260824
DataHub source rows = 349,923
2021+ rows = 0
```

The FactorLab `data/development/1m_official.parquet` row count is 350,561 and is **not automatically equivalent** to this source surface. Using it as exact source support without a frozen bridge is a protocol failure.

## 4. Native-product identity gate

Expected frozen native 5m rows:

```text
5m_offset_0 = 70,114
5m_offset_1 = 67,192
5m_offset_2 = 67,192
5m_offset_3 = 67,193
5m_offset_4 = 67,191
```

Before bounds, authoritative replay/support mapping must produce for every view:

- identical native label set;
- zero extra/missing labels;
- zero OHLC mismatches on aligned labels;
- non-empty actual support for every emitted bar;
- last support-row close equal to native close;
- every assigned source-row close inside native `[low,high]`.

The known offset0 metadata discrepancy is retained:

- frozen parquet declares `cn_a_session_wall_clock_offset_v1`;
- accepted DataHub code routes offset0 through official v2.

Do not rewrite the frozen parquet metadata. The discrepancy is allowed only because the accepted official-route diagnostic reproduces all frozen 5m offset0 labels/OHLC exactly. No generalization to other frequencies is permitted.

## 5. Support-topology record

For every adjacent native transition used by a published leg, build a topology record containing at minimum:

```text
view_id
previous_native_label
current_native_label
current_native_bar_id
support_source_timestamps        # exact ordered actual source membership
support_source_count = m
gap_source_timestamps            # actual source rows between endpoints not assigned to current bar
gap_source_count
transition_class                 # fully_enveloped_transition | contains_unenveloped_source_gap
source_dataset_version
contract_revision
```

The topology stage may use timestamps/membership/counts but must not expose source prices to the bound constructor.

Every actual source row between the two native endpoints must be accounted for exactly once by the topology audit. Lunch/overnight wall-clock elapsed time with no source row is not a gap row.

## 6. Variable-step bound function

For `fully_enveloped_transition`, let `m=support_source_count`, previous native close `c0`, current native `L,H,C`.

Reject `m<1`, `H<L`, or `C` outside `[L,H]`.

### m = 1

```text
TV_min = TV_max = |C-c0|
M_min  = M_max  = |C-c0|
```

### m >= 2

Hidden path:

```text
c0 -> z1 -> ... -> z_(m-1) -> C
z_i in [L,H]
```

Compute:

```text
TV_min = |C-c0|
TV_max = exact maximum over 2^(m-1) vertices z_i in {L,H}
M_min  = |C-c0| / m
M_max  = max(|L-c0|, |H-c0|, H-L, |L-C|, |H-C|)
```

The real-data accepted occupancy range is expected to be within 1..6, but the implementation must fail clearly if a larger `m` appears rather than silently truncating it.

## 7. Structural-gap bound

If **any** transition in a leg has `gap_source_count > 0`, no discarded row may be assigned to a neighboring native OHLC envelope.

Let exact actual fine step count between the leg native endpoints be `N`.

For positive fine total variation register only:

```text
J_low  = 1/N
J_high = 1
C_inf  in [0, log(N)]
C_1    in [0, log(N)]
C_2    in [0, log(N)]
```

Tag the leg:

`structural_gap_universal_bound`

The leg remains in all aggregate and stratum reports.

## 8. Fully enveloped leg bound

If every transition in the leg has `gap_source_count = 0`:

```text
N       = sum(m_j)
TV_low  = sum(TV_min_j)
TV_high = sum(TV_max_j)
M_low   = max(M_min_j)
M_high  = max(M_max_j)

J_low  = max(1/N, M_low/TV_high)       if TV_high>0
J_high = min(1, M_high/TV_low)         if TV_low>0
         1                             otherwise
```

Require `0 < J_low <= J_high <= 1` for defined positive-TV legs.

Profile transformation:

```text
C_inf_low  = log(N*J_low)
C_inf_high = log(N*J_high)
```

For `C_1/C_2`, reuse exactly the v0.6.15 probability-simplex extremizers:

- lower bound: least-concentrated distribution with one weight at least `J_low`;
- upper bound: most-concentrated distribution with all weights capped by `J_high`.

Require all profile bounds within `[0,log(N)]` up to `1e-12` arithmetic guard.

## 9. Synthetic gates before real output

Tests must pass before any real-data bound output is interpreted:

1. generalized vertex TV maximum for `m=1..6` against independent brute force;
2. random feasible variable-step covered paths always lie inside TV/M/J bounds;
3. transformed `C_inf/C_1/C_2` synthetic profiles always lie inside registered bounds;
4. inserted un-enveloped source gap forces the universal interval;
5. zero-source-row lunch/overnight elapsed periods do not create fake gap rows;
6. actual discarded source rows do create a gap class;
7. positive price scaling leaves J/profile bounds unchanged;
8. future append outside a closed leg leaves topology and bounds unchanged;
9. bound API contains no source-price/oracle/counterpart/direction/outcome field;
10. source dataset/version mismatch fails closed;
11. a support timestamp assigned to two bars or left unclassified inside the audited transition fails closed.

## 10. Oracle/data-consistency gates

Only after topology and bounds are frozen for a leg may source prices/oracle profiles be read.

For every oracle-comparable leg report and assert:

- registered `N` equals actual fine movement count;
- actual `J1` inside `[J_low,J_high]`;
- actual `C_inf/C_1/C_2` inside corresponding intervals;
- structural-gap legs are retained;
- no coverage exception is repaired by widening an individual result-conditioned interval.

Any material support/coverage failure stops tightness interpretation.

## 11. Tightness and topology outputs

Report by each view and overall:

```text
transition_class_counts
support_source_count_distribution
gap_source_count_distribution
fully_enveloped_leg_count
structural_gap_universal_bound_leg_count
J bound lower/upper/width distributions
C_inf/C_1/C_2 lower/upper/width distributions
normalized profile widths
oracle position in non-degenerate bounds
coverage fractions
```

Universal-bound legs must be included in aggregate widths. A second explicitly labelled fully-enveloped-only table is allowed for diagnosis but may not replace the all-leg result.

No width threshold is tuned.

## 12. Frozen overlays

Repeat topology/tightness outputs for the existing frozen categories only:

- native transition-count bins `1-3`, `4-5`, `6-11`, `12-23`, `24+`;
- strict same-event pair universe 29,453;
- both-qualified 482;
- qualification disagreement 699;
- target repaired 80;
- target agreement 56;
- target disagreement 24.

No overlay changes topology or bound construction.

## 13. Cross-slicer comparison

On frozen strict same-event pairs compare:

- whether each counterpart is fully enveloped or structural-gap;
- lower/upper bound differences;
- interval widths;
- interval overlap;
- oracle coverage.

Do not use counterpart information inside a single-view bound.

## 14. Required outputs

Write compact evidence to:

`cloud_results/cloud_chat_v0617_session_aware_bounds/`

Required:

```text
summary.json
support_topology_summary.json
source_identity.json
native_identity.json
synthetic_gate_receipt.json
data_consistency.json
bound_tightness.json
step_count_overlay.json
cross_slicer_bounds.json
strata_overlays.json
execution_receipt.json
```

A large row-level support topology need not be committed if it is deterministically reproducible; if kept outside GitHub, record its SHA256, row count, schema, generation command and location in `execution_receipt.json`.

## 15. Allowed adjudications

Only:

- `session_aware_bounds_valid_and_ready_for_identifiability_interpretation`;
- `session_aware_bounds_valid_but_structural_gap_nonidentifiability_is_material`;
- `session_aware_bounds_cover_oracle_but_are_too_wide_for_identification`;
- `session_aware_bounds_fail_support_topology_or_oracle_coverage`;
- `mixed_identifiability_requires_more_audit`.

No result may be converted directly into a qualification threshold or trading rule.

## 16. Global firewall

Throughout v0.6.17:

- no `H_end_5` promotion;
- no local 1m→5m product redefinition;
- no session-boundary sample deletion;
- no empirical bound shrinkage;
- no new concentration point proxy;
- no matcher/projection/publication/qualification change;
- no roughness re-optimization;
- no direction/D1/D2/PAWCT;
- no third-wave;
- no outcomes/P&L;
- no fresh OOS, paper trading or production.

Global state remains `morphology_replication_not_yet_accepted` until a later morphology acceptance gate explicitly changes it.
