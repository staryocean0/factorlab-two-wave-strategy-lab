# Two-Wave v0.6.52 — Ordinal-0 Predecessor-Support / First-Valid-Publication Lineage Audit

Status: **frozen before any v0.6.52 aggregate lineage statistics are read**.

## 1. Scientific question

v0.6.50 and v0.6.51 left one upstream clue unresolved: in the independently anchored human-positive cases, the algorithmic start anchor `p0` is much less aligned than the end anchor, while boundary-normalized internal geometry is comparatively close.

The next question is not another human-label error threshold. It is a property of the existing algorithm itself:

> Is ordinal 0 (`p0`) generated and frozen by a structurally different causal lineage from ordinals 1–4, and does that asymmetry materially express itself through predecessor eligibility or first-valid immutable publication?

This is a **read-only lineage/provenance audit**. It cannot alter projection geometry, publication order, qualification, parent boundaries, direction rules, or runtime authority.

## 2. Frozen code path being audited

The audit must use the current frozen Development chain without modification:

1. `extremum_ridge_v052.build_ridge_run`
2. `ordinal0_predecessor_support_v064.project_birth_with_predecessor`
3. `scale_invariant_predecessor_publication_v065.publish_first_valid_candidate`
4. `published_identity_qualification_v066.qualify_published_raw_identity`
5. `path_gate_demotion_v0618.requalify_v066_control`

The existing implementation contract to verify at runtime is:

- ordinal 0 starts at `birth-level predecessor occurrence + 1`;
- ordinals 1–4 start at `previously selected raw anchor + 1`;
- ordinal 0 is the only projection window carrying `source_predecessor_bar`;
- one canonical filtered identity orders evidence by `(birth_confirmation_bar, birth_level, event_id)`;
- the first valid candidate publishes one immutable raw identity;
- later valid evidence never rewrites the published identity and is only recorded as same-identity evidence or a suppressed would-be rewrite.

If any of these contracts fail, the formal run must fail closed rather than reinterpret the lineage.

## 3. Frozen data

Primary source:

- `data/development/5m_offset_0.parquet`
- expected SHA256: `bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`
- period: frozen 2015–2020 Development main view.

The formal audit does **not** read v0.6.48 final human labels, annotator sheets, notes, confidence, D1/v0.6.25 state, future outcomes, returns, PnL, or harmless offsets.

The frozen v0.6.48 candidate sampling commitment may be reconstructed only to report an **unlabeled candidate-cutoff descriptive replication**. It may not enter the primary decision rule.

## 4. Universes

### 4.1 Background publication universe

All canonical filtered identity groups reconstructed from the frozen ridge tuple-birth chain.

Report:

- canonical group count;
- published group count;
- no-valid-publication count;
- evidence-member-count distribution;
- valid-member-count distribution;
- publication birth-level distribution.

### 4.2 Primary lineage universe

All **v0.6.18-qualified published identities** on `5m_offset_0`.

This is the primary decision universe because it is the population that current Development qualification allows downstream.

The expected candidate-qualified publication count is `2115`; any drift fails closed.

### 4.3 Frozen candidate-cutoff descriptive replication

Reconstruct the frozen v0.6.48 packet selection from the same qualified confirmation bars and select its `120` hidden candidate cutoffs without reading reference labels.

If a cutoff contains multiple qualified identities, include all such identities for descriptive lineage replication. Do not choose an identity by human-anchor fit.

This sample is descriptive only and cannot change the primary category.

## 5. Frozen diagnostics

All diagnostics below are computed for both the background publication universe and the primary v0.6.18-qualified universe when defined. The decision gates use the **primary qualified universe**.

### 5.1 Pre-publication invalid evidence

For every published identity, preserve the evidence order used by v0.6.5 and count invalid evidence members before the publishing member.

Report incidence of published groups with at least one prior invalid member, plus invalid reasons.

Define predecessor-specific invalid reasons as:

- `ordinal0_left_censored_no_predecessor`
- `predecessor_kind_not_opposite`
- `predecessor_confirmed_after_tuple_birth`
- `birth_first_node_missing_from_level`
- `birth_nodes_not_consecutive_at_level`

Report:

- fraction of published groups with a predecessor-specific invalid member before publication;
- fraction of all pre-publication invalid members attributable to predecessor-specific reasons;
- `ordinal0_left_censored_no_predecessor` separately.

### 5.2 Projection-window provenance

For every valid evidence member verify:

- window 0 lower bar = `predecessor_occurrence_bar + 1`;
- windows 1–4 lower bar = prior selected raw bar + 1;
- only window 0 has non-null `source_predecessor_bar`.

Report per ordinal, for publishing members:

- projection window width distribution;
- absolute displacement `|raw_occurrence_i - filtered_occurrence_i|` distribution.

This is descriptive; no projection-width or displacement threshold is authorized for production or qualification.

### 5.3 Later-valid evidence and immutable publication

For each published identity, consider valid evidence members after the publishing member.

For each later-valid comparison against the published raw tuple, compute:

- whether the raw tuple is identical;
- whether it is a suppressed would-be rewrite;
- changed ordinals;
- first changed ordinal;
- whether only ordinal 0 changed;
- whether predecessor occurrence changed from the publishing member;
- whether ordinal 0 changed.

Report group-level incidence of at least one suppressed rewrite among groups that have at least one later-valid member.

### 5.4 Per-ordinal rewrite incidence

Among suppressed rewrite comparisons only, report:

- incidence that each ordinal `0..4` changes;
- first-changed-ordinal distribution;
- ordinal-0-only rewrite incidence.

### 5.5 Predecessor-change association

Among all later-valid comparisons, separately report ordinal-0 change incidence when:

- predecessor occurrence changed;
- predecessor occurrence stayed the same.

Also report counts for both denominators.

### 5.6 Cross-member raw-anchor spread

For groups with at least two valid evidence members, compute for each ordinal:

`max(raw_occurrence_i) - min(raw_occurrence_i)`.

Report median/Q1/Q3 per ordinal. This is a stability diagnostic only.

## 6. Frozen decision gates

### Gate A — predecessor eligibility bottleneck is material

Pass only if, in the primary v0.6.18-qualified universe:

1. at least `10%` of published identities have one or more predecessor-specific invalid evidence members before publication; **or**
2. predecessor-specific reasons account for at least `50%` of all invalid evidence members before publication, with at least `50` such invalid members.

### Gate B — immutable first-valid freeze is materially exposed

Among primary qualified identities with at least one later-valid member, pass only if at least `20%` of groups have one or more suppressed would-be rewrites.

Require at least `100` groups with later-valid evidence; otherwise this gate is `insufficient_denominator` and cannot pass.

### Gate C — rewrite instability is ordinal-0 dominant

Among primary qualified suppressed rewrite comparisons, require at least `100` comparisons and both:

1. first-changed ordinal is `0` in at least `70%` of rewrite comparisons;
2. ordinal-0 changed incidence exceeds the largest changed incidence among ordinals `1..4` by at least `0.15`.

### Gate D — predecessor changes are associated with ordinal-0 changes

Require at least `50` later-valid comparisons with changed predecessor occurrence and at least `50` with unchanged predecessor occurrence, then require both:

1. `P(p0 changes | predecessor changes) >= 0.70`;
2. that incidence exceeds `P(p0 changes | predecessor unchanged)` by at least `0.20`.

If either denominator is below `50`, Gate D is `insufficient_denominator` and cannot pass.

### Gate E — publishing-member ordinal-0 projection displacement is structurally larger

Let `M0` be median `|raw_0-filtered_0|` over primary qualified publishing members, and `M123` the maximum of medians for ordinals 1–3.

Pass only if:

- `M0 >= 2` bars; and
- `M0 >= 1.5 * M123`.

Ordinal 4 is excluded from this comparison because its upper window is confirmation-bounded rather than next-filtered-anchor bounded.

Gate E is supporting evidence only; by itself it cannot authorize a mechanism claim.

## 7. Frozen primary categories

Use this precedence exactly:

1. `v0652_ordinal0_predecessor_first_valid_freeze_mechanism_supported` if Gates A, B, C and D all pass. Gate E may pass or fail.
2. `v0652_p0_specific_first_valid_rewrite_instability_without_predecessor_change_link` if Gates B and C pass but D does not pass.
3. `v0652_first_valid_publication_rewrite_instability_not_ordinal0_specific` if Gate B passes but Gate C does not pass.
4. `v0652_predecessor_support_materially_affects_publication_eligibility_only` if Gate A passes but Gate B does not pass.
5. `v0652_structural_ordinal0_provenance_asymmetry_not_materially_expressed` if none of Gates A–D pass, while the runtime provenance contract is verified.

No other primary category is permitted.

## 8. Interpretation boundaries

Even if category 1 passes, this audit **does not** authorize:

- replacing the predecessor;
- changing the ordinal-0 projection window;
- delaying or rewriting first-valid publication;
- choosing later evidence because it better matches human labels;
- a new parent identity challenger;
- a boundary tolerance;
- a translation correction;
- qualification or direction changes.

Any intervention requires a separately frozen challenger protocol and cannot be fitted to the v0.6.48 labels.

If only Gate E passes, treat it as a descriptive projection-geometry clue, not an intervention authorization.

## 9. Reporting constraints

Commit only aggregate results. Do not write a table keyed by case ID, event ID, filtered identity ID, timestamp, human label, or raw anchor tuple.

The result must explicitly report:

- source hash and manifest verification;
- code/runtime lineage-contract verification;
- background and primary universe counts;
- prior-invalid reason counts;
- later-valid / rewrite denominators;
- per-ordinal rewrite and first-changed distributions;
- predecessor-change conditional rates;
- publishing-member per-ordinal window-width and raw-vs-filtered displacement distributions;
- cross-member per-ordinal spread distributions;
- unlabeled v0.6.48 candidate-cutoff descriptive replication;
- Gates A–E and the frozen primary category.

## 10. Governance invariants

Whatever the result:

- human reference labels used: **false**;
- future outcome used: **false**;
- threshold fitting performed: **false**;
- projection geometry changed: **false**;
- publication policy changed: **false**;
- qualification changed: **false**;
- direction winner changed: **false**;
- `morphology_acceptance=false`;
- `trade_authority=false`;
- `production_authority=false`.
