# Two-Wave v0.7.1 — Ridge-Supported Semantic Parent Objectization Reconstruction

Status: **frozen before any v0.7.1 family-support statistics are read**.

## 1. Starting authority

v0.7.0 localized the first large semantic loss at the transition from causal TCSS/ridge support to the legacy exact-consecutive five-ridge tuple object:

- anchored human-positive cases: `11`;
- L1 common-scale ridge support: `10/11`;
- L2 exact five-ridge tuple support: `3/11`;
- L1 true / L2 false: `7`;
- L2 true / L3 false: `0`.

Therefore v0.7.1 retains the causal TCSS extremum/ridge state space as support infrastructure and reconstructs the semantic-parent objectization layer only. It does **not** change data, clock, source, replay, raw projection, qualification, direction, morphology acceptance, trade authority, or production authority.

## 2. Objective

Ask one bounded question:

> Can a separately defined, causal, ridge-supported parent-object family recover the independently frozen five-anchor human parent semantics without fitting a bar-distance tolerance to the 11 anchored cases?

This is a Development representation reconstruction / challenger-selection audit. It is not a production recognizer and cannot establish morphology acceptance.

## 3. Frozen evidence universe

Reuse exactly the v0.7.0 evidence universe and reconstruction chain:

- source: `data/development/5m_offset_0.parquet`;
- source SHA256: `bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`;
- final independent reference SHA256: `321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d`;
- sampling commitment SHA256: `f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8`;
- frozen chart lookback: `96` bars;
- expected reference-positive candidate cases: `16`;
- expected anchored reference-positive cases with complete valid `p0..p4`: exactly `11`.

The v0.7.0 deterministic human support cells and inferred alternating kinds are reused unchanged.

No annotator notes/confidence, future bars, returns, PnL, D1/v0.6.25 output, qualification outcome, raw-projection outcome, or case-specific threshold fitting may be used.

## 4. Causal ridge snapshot

For each anchored case and each TCSS scale level, define the visible ridge snapshot using only ridge nodes satisfying:

- `node.confirmation_index <= cutoff`;
- `chart_start <= node.occurrence_index <= cutoff`.

Order visible ridge nodes by `(occurrence_index, confirmation_index, node_id)`.

All v0.7.1 challenger-family membership predicates operate only on this cutoff snapshot. A node confirmed after cutoff cannot create, split, invalidate, or otherwise alter a v0.7.1 challenger object.

The legacy exact-tuple control remains the already-frozen v0.7.0/v0.5.2 exact-ridge object and is not redefined by this snapshot rule.

## 5. Frozen object-family ladder

Every challenger is a **separately named structural family**. Merely changing a tolerance or silently relaxing the v0.5.2 tuple rule is forbidden.

For challengers, a five-node object is a tuple `(r0,r1,r2,r3,r4)` drawn from one common scale-level cutoff snapshot and must satisfy all base conditions:

1. five distinct ridge IDs;
2. strictly increasing occurrence indices;
3. strictly alternating ridge kinds;
4. every member is confirmed by cutoff.

Human cells are **not** part of family construction. They are used only after construction semantics are frozen to test compatibility.

### F0 — `legacy_exact_consecutive_five_ridge_tuple`

Control only. Reuse the v0.7.0 exact-ridge tuple-support definition exactly. No authority is restored by this control.

### F1 — `same_scale_full_envelope_five_turn`

A base five-node object is admitted only when every selected turn is the deterministic same-kind envelope extremum in its adjacent semantic span in the cutoff snapshot.

For ordinal `i`, define its comparison interval from selected occurrences:

- `i=0`: `[r0,r1]`;
- `i=1`: `[r0,r2]`;
- `i=2`: `[r1,r3]`;
- `i=3`: `[r2,r4]`;
- `i=4`: `[r3,r4]`.

Among snapshot ridge nodes of the same kind whose occurrence lies in that interval, the selected node must be the deterministic phase-extreme:

- `low`: minimum `node.value`;
- `high`: maximum `node.value`;
- exact value ties: later occurrence wins; remaining tie: lexical `node_id`.

This family permits intervening ridges only when the selected five turns remain the complete two-cycle envelope under the frozen dominance rule.

### F2 — `same_scale_core_envelope_five_turn`

A base five-node object is admitted when the three shared/core turns `r1,r2,r3` satisfy the same deterministic envelope rule in `[r0,r2]`, `[r1,r3]`, `[r2,r4]` respectively. Endpoint turns `r0,r4` are not additionally envelope-constrained.

This tests whether endpoint-envelope strictness, rather than exact adjacency, is the remaining representational bottleneck.

### F3 — `same_scale_ordered_alternating_five_ridge_subsequence`

Any base five-node object is admitted. Intervening cutoff-confirmed ridges are allowed.

This is the deliberately permissive structural upper bound for a same-scale ridge-supported five-turn semantic parent. It is a separately frozen object family, not an implicit modification of F0.

No family may use nearest-human-anchor distance, fitted gap limits, fitted skip limits, amplitude thresholds chosen from the 11 cases, reference labels during construction, or best-match-to-human optimization.

## 6. Human-semantic compatibility test

After family membership is determined independently, an object is human-compatible only if its five ridge nodes map ordinally one-per-v0.7.0 human support cell and each node kind matches the frozen inferred human kind.

For each case/family report only aggregate-safe diagnostics:

- whether at least one compatible object exists;
- number of scale levels with at least one compatible object;
- compatible-object count, aggregated across cases;
- for supported cases, the minimum number of cutoff-snapshot ridge nodes skipped between the five selected nodes, aggregated as a distribution.

No case ID → family/object mapping table may be committed.

## 7. Development salvage threshold

Reuse the already frozen v0.7.0 coarse Development threshold: a family is semantic-support-salvaged when compatible support is at least `8/11` anchored cases.

This threshold is not morphology acceptance and cannot authorize production use.

## 8. Frozen adjudication precedence

Choose exactly one primary category:

1. if F0 unexpectedly reaches `8/11`, fail closed with `v071_legacy_exact_tuple_control_drift_or_contradiction`;
2. else if F1 reaches `8/11`, `v071_full_envelope_parent_objectization_development_rescue_supported`;
3. else if F2 reaches `8/11`, `v071_core_envelope_parent_objectization_development_rescue_supported`;
4. else if F3 reaches `8/11`, `v071_ordered_subsequence_parent_objectization_development_rescue_supported`;
5. else `v071_prespecified_ridge_supported_object_families_do_not_rescue_semantic_parent`.

Precedence intentionally prefers the most structurally constrained challenger that clears the inherited support threshold. No continuous parameter is optimized.

A challenger selected here is a **Development challenger only**. It is not an accepted recognizer.

## 9. Interpretation and next step

If F1/F2/F3 is selected:

- freeze that family identity as the repaired semantic-parent challenger;
- next retest the historical tuple-birth/causal publication timing layer on the repaired object;
- only after that may raw projection/publication, same-scale qualification, and direction be transplanted and retested, in that order.

If no challenger clears `8/11`:

- retain TCSS/ridge support infrastructure per v0.7.0;
- do not restore the exact tuple;
- open another separately frozen objectization reconstruction family rather than fitting human-anchor distance tolerances.

## 10. Governance invariants

Whatever the result:

- `threshold_fitting_performed=false`;
- `human_anchor_distance_tolerance_fitted=false`;
- `qualification_changed=false`;
- `direction_winner_changed=false`;
- `morphology_acceptance=false`;
- `trade_authority=false`;
- `production_authority=false`.

Forbidden shortcuts include:

- fitting bar-distance or skip-count thresholds to the 11 anchored cases;
- choosing a five-node combination by nearest-human-anchor error;
- relabeling F3 as the old exact tuple;
- treating a Development family rescue as morphology acceptance;
- resuming qualification or direction mining before repaired-object causal timing is retested;
- declaring downstream v0.6.x components false solely because the legacy objectization failed.