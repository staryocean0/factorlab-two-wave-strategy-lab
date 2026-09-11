# Two-Wave v0.6.47 independent temporal morphology replication protocol

Date: 2026-09-11  
Status: `frozen_before_external_morphology_scoring`

## Purpose

v0.6.47 is an **independent temporal replication** of the already-frozen Two-Wave parent-recognizer research chain on post-2020 CSI1000 bars that were not used by this repository's 2015-2020 morphology Development work.

This is **not** a new direction challenger, not a parameter search, and not a claim of globally fresh OOS. In particular, the external 2026 archive itself declares `fresh_oos=false` even though it is sealed as held-out validation material in its source project.

The experiment may assess whether the frozen recognition/qualification/direction machinery retains comparable harmless-slicing stability on later calendar years. It may **not** by itself set `morphology_acceptance=true`, because no independent human/reference morphology labels are supplied.

## Frozen upstream

No recognizer or threshold changes are allowed:

- parent identity: v0.5.2 ridge lineage;
- canonical birth grouping: v0.6.1;
- immutable raw predecessor projection/publication: v0.6.4/v0.6.5;
- qualification: **v0.6.18** path-gate demotion;
- historical direction baseline: D1;
- strongest pooled-exact direction contribution: **v0.6.25** D1-primary endpoint-erosion-consensus Huber margin rescue;
- v0.6.25 margin threshold: `0.10` amplitude units;
- v0.6.23 support views, Huber state boundaries, unanimous-decisive requirement, identity/confirmation/amplitude semantics: unchanged.

No future returns, PnL, H1/H2, third-wave outcome, execution result, cross-offset runtime feature, threshold menu, classifier fitting, or post-result tuning is allowed.

## Mandatory Development resampler precondition — already passed before this protocol

External archives supply 1-minute bars, while the frozen direction evaluation uses five harmless 5-minute wall-clock offsets. Before external morphology scoring was authorized, the deterministic 1m-to-five-offset constructor had to reproduce every shipped 2015-2020 Development 5m product **row-for-row exactly** on timestamp and O/H/L/C.

Authoritative precheck:

- GitHub Actions run: `34623300582`;
- job: `103342237228`;
- package validation: pass;
- full pytest: pass;
- `5m_offset_0`: `70,114/70,114` rows, timestamp exact, O/H/L/C max absolute difference all `0.0`;
- `5m_offset_1`: `67,192/67,192`, exact;
- `5m_offset_2`: `67,192/67,192`, exact;
- `5m_offset_3`: `67,193/67,193`, exact;
- `5m_offset_4`: `67,191/67,191`, exact.

Therefore the resampling semantics below are frozen before any post-2020 morphology score is computed.

## Frozen DataHub five-offset reconstruction semantics

For each trading day, morning and afternoon sessions are independent.

- 1m bar-end sessions: `09:31..11:30` and `13:01..15:00` Asia/Shanghai.
- Offset `r in {0,1,2,3,4}` has nominal 5m endpoints at session minute index `r + 4 + 5*g`.
- For `r>0`, the first shifted point-envelope includes the left-boundary endpoint (`r-1 .. r+4`); later windows are non-overlapping five-endpoint groups.
- `causal_flat_fill=true` rows preserve the wall-clock grid but are excluded from OHLC and amount aggregation.
- On an abnormal/short session, a scheduled 5m bar is emitted at its **nominal wall-clock endpoint** whenever the scheduled window contains at least one non-flat observation, even if the exact endpoint 1m row is absent; close is the last real observation in that window.
- No synthetic price interpolation is allowed.

Implementation: `src/factor_lab/visual_structure/two_wave/validation_resample_v0647.py`.

## Frozen external temporal material

### 2024 and 2025 archive

Source repository: `staryocean0/factorlab-star50-filter-lab`  
Source commit: `ef7fedc0345c0e895b278a3f5448f85c132d5b98`

2024 CSI1000 1m:

- path: `data/cross_index_risk_gate_v1/1m/000852.SH/2024.parquet`
- SHA256: `52e1d078fefbb1232b07a8b64682f41654ee171d850c5fe5c928350aba9d6b25`
- rows: `58,080`
- days: `242`
- interval: `2024-01-02..2024-12-31`

2024 native 5m offset-0 control:

- path: `data/cross_index_risk_gate_v1/5m/000852.SH/2024.parquet`
- SHA256: `f9c536d99daa6aaf02d00efd7010316b528e54b5866dc8cf44d002d87f9c3667`
- rows: `11,616`

2025 CSI1000 1m:

- path: `data/cross_index_risk_gate_v1/1m/000852.SH/2025.parquet`
- SHA256: `aebbf7c7bedb78863455192d6efed7536f785c6558fcecd14b475e276e95e1e6`
- rows: `58,320`
- days: `243`
- interval: `2025-01-02..2025-12-31`

2025 native 5m offset-0 control:

- path: `data/cross_index_risk_gate_v1/5m/000852.SH/2025.parquet`
- SHA256: `5fbecf49d76cd2560e7db5af280b60c012a440a6e69ba6b8306acbbbd4e49333`
- rows: `11,664`

These files were development material in the STAR50 project, but they were not part of this Two-Wave repository's frozen 2015-2020 morphology Development information set. They are therefore used here only as **post-2020 temporal replication material**, not described as globally fresh OOS.

### 2026 sealed validation archive

Source repository: `staryocean0/factorlab-star50-filter-lab`  
Source branch: `research/post-shock-recovery-2026-validation`  
Frozen source commit: `4b93dd072e39af19201202e976afd6c63bf10112`

CSI1000 1m:

- path: `data/cross_index_risk_gate_2026_v1/1m/000852.SH/2026.parquet`
- SHA256: `60b2054d2055bef8010a9948a0589bc1c4b0bb18dd6f373a9366f97e689fdf87`
- rows: `36,960`
- days: `154`
- interval: `2026-01-05..2026-08-21`
- source role: `held_out_validation_material`
- source manifest: `fresh_oos=false`, `post_snapshot_rows=0`.

The archive preserves `causal_flat_fill`, `source_minute_count`, and `high_frequency_analysis_eligible`.

## Frozen external timestamp interpretation

The external archive manifests explicitly state that source strings ending in `Z` encode **Shanghai wall-clock labels**, not true UTC instants.

For external source timestamps:

1. take the first 19 characters of the serialized timestamp;
2. parse them as naive wall clock;
3. localize to `Asia/Shanghai`;
4. convert that instant to UTC for internal ordering/comparison.

The same normalization is applied to 2024/2025 native 5m offset-0 controls.

No alternative timezone interpretation may be tried after viewing morphology metrics.

## Mandatory external pre-score control

Before any parent recognition or direction metric is interpreted:

- generated 2024 `5m_offset_0` must exactly equal its native external 5m file on row count, timestamp, O/H/L/C;
- generated 2025 `5m_offset_0` must exactly equal its native external 5m file on row count, timestamp, O/H/L/C.

Any failure stops the experiment **before morphology scoring**. A failure may only motivate an implementation repair to timestamp/clock reconstruction, using Development/native-bar controls; it may not motivate morphology threshold changes.

## Year isolation

Run three independent slices:

- `2024`;
- `2025`;
- `2026-01-05..2026-08-21`.

Each year's five views are recognized independently. A parent identity may not cross a year boundary. Aggregate metrics may pool the already-formed within-year comparison pairs, but may never construct a cross-year parent or counterpart edge.

## Frozen recognition and qualification replay

For every year and every offset view, reuse the frozen v0.6.18 generation chain exactly:

1. `build_ridge_run`;
2. `canonicalize_tuple_births`;
3. `project_birth_with_predecessor`;
4. group by `(phase, filtered occurrence tuple)`;
5. `publish_first_valid_candidate`;
6. `qualify_published_raw_identity`;
7. `requalify_v066_control`.

Development-specific expected counts are removed; scientific definitions are not changed.

Record, per year/view:

- bars;
- tuple births;
- canonical filtered groups;
- published identities;
- no-valid-publication count;
- v0.6.6 control-qualified count;
- v0.6.18-qualified count;
- newly qualified count;
- hard-reason counts.

Long-span safety gates remain binding. `future_outcome_used=false`.

## Frozen harmless-offset pairing

Within each year:

- main view: `5m_offset_0`;
- other views: offsets 1..4;
- build mutual-unique filtered identity edges with `build_edge_graph(... nominal_bar_minutes=5.0, require_phase=True)`;
- require raw strict financial identity via `strict_anchor_edge`;
- direction evaluation universe is only pairs where both sides are v0.6.18-qualified.

Cross-offset counterpart information remains evaluation-only and is never an input to one side's runtime classification.

## Frozen direction replay

For each both-qualified record:

- reconstruct the frozen parent using `evaluate_pair` on the five published raw occurrences;
- D1 is read from `direction_versions['D1']`;
- v0.6.25 classification is computed with the frozen D1-primary erosion-consensus margin rescue (`consensus_margin >= 0.10`);
- D1 decisive states may never be overridden.

No new state, tie-break, Range gate, offset-dependent rule, or year-specific threshold is allowed.

## Frozen reported metrics

Report separately for 2024, 2025, 2026 and for the pooled set of within-year pairs:

- filtered mutual-unique pairs;
- raw strict pairs;
- v0.6.18 qualification matrix;
- both-qualified pair count;
- D1 and v0.6.25 exact four-state agreement;
- main/other/pooled decisive coverage;
- decisive agreement;
- opposite UpTrend/DownTrend conflict count;
- pooled label counts and decisive label shares;
- v0.6.25 rescue count;
- D1 decisive override count.

Per-offset metrics are also reported within every year and overall.

## Frozen original v0.6.25 replication gates

The original v0.6.25 gates are reapplied **without relaxation**. For a slice to pass all gates, ALL must hold:

1. v0.6.25 exact agreement is not lower than D1 on every one of offsets 1..4;
2. pooled v0.6.25 exact agreement is not lower than pooled D1;
3. v0.6.25 pooled decisive coverage is at least `0.65` and at least D1 + `0.15`;
4. for every offset, both main-side and other-side v0.6.25 decisive coverage are at least `0.55`;
5. pooled v0.6.25 decisive agreement is at least `0.995`;
6. v0.6.25 opposite UpTrend/DownTrend conflict count is exactly `0`;
7. pooled v0.6.25 decisive label shares satisfy `UpTrend >= 0.15`, `DownTrend >= 0.15`, `Range >= 0.02`;
8. at least one D1-Uncertain record is rescued by v0.6.25.

Compute these gates independently for 2024, 2025, 2026, and the pooled set.

## Frozen experiment verdict

Formal verdict is:

`v0647_temporal_replication_under_original_v0625_gate_all_pass`

only if **all eight original gates pass for each of 2024, 2025, 2026 and for the pooled set**.

Otherwise:

`v0647_temporal_replication_under_original_v0625_gate_not_all_pass`

The purpose is replication evidence, not retroactive candidate promotion. Therefore, under either verdict:

- v0.6.18 remains qualification champion;
- parent-direction winner remains unset;
- v0.6.25 remains a research contribution, not installed runtime authority;
- `morphology_acceptance=false`;
- `trade_authority=false`;
- `production_authority=false`.

A strong temporal replication may strengthen the evidence base, but independent reference morphology labels are still required before full morphology acceptance can be considered.

## Forbidden after result

Do not:

- change the five-offset clock reconstruction after seeing morphology scores unless an external native-bar equivalence assertion itself fails;
- change v0.6.18 qualification;
- tune the v0.6.25 `0.10` margin;
- drop a weak year or weak offset;
- pool years before recognizing identities;
- relax the original v0.6.25 gates;
- fit a new rule to post-2020 residuals inside v0.6.47;
- declare v0.6.25 a direction winner from this experiment;
- declare global morphology acceptance without independent reference labels.
