# Two-Wave v0.7.2 — F3 Causal Event / Immutable Publication + Downstream Transplant Precheck

Status: **frozen before any v0.7.2 event/publication statistics are read**.

## 1. Starting authority

v0.7.1 completed ridge-supported semantic-parent objectization reconstruction and selected exactly one Development reconstruction candidate:

- F0 legacy exact-consecutive tuple: `3/11`;
- F1 unrestricted nonconsecutive upper bound: `10/11`, explicitly non-identifying;
- F2 one-step-survivor skeleton: `5/11`;
- F3 persistence-dominant nonconsecutive quintet: `8/11`;
- formal verdict: `v0701_persistence_dominant_objectization_candidate_supported`.

F3 remains Development evidence only. It is **not** morphology authority. v0.7.2 does not reselect or refit F3 and does not reopen the `8/11` objectization gate.

The authorized next question is:

> Can the frozen F3 ridge-ID object be represented as a causal first-known immutable event/publication, with deterministic multiplicity and rewrite accounting, so that the historical append-only publication concept can be transplanted before raw projection is reconsidered?

## 2. Frozen sources and no-label rule

Reuse the frozen main-view source and the deterministic v0.6.48 packet generator only as a **label-free checkpoint sampler**:

- source: `data/development/5m_offset_0.parquet`;
- source SHA256: `bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`;
- packet sampling commitment SHA256: `f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8`;
- checkpoint count: exactly `240` = 6 years × 2 frozen strata × 20 checkpoints;
- checkpoint chart lookback for the continuity census: `96` bars.

`FINAL_REFERENCE_LABELS.csv`, human anchors `p0..p4`, annotator notes/confidence, direction labels, returns, PnL, future outcomes, and qualification outcomes are not read by the v0.7.2 primary analysis.

The candidate/control stratum is used only to deterministically reproduce the already frozen 240 checkpoint timestamps. No result is optimized by stratum.

## 3. Frozen F3 checkpoint object census

At each of the 240 frozen checkpoint cutoffs, reproduce the v0.7.1 F3 family **exactly** on that checkpoint's 96-bar chart:

- eligible ridge nodes are chart-visible and confirmed by cutoff;
- causal survival level is the maximum eligible scale level for the ridge ID at that cutoff;
- F3 identity is the ordered tuple of five distinct ridge IDs;
- selected ridges must be an ordered alternating common-scale quintet;
- every skipped same-level ridge between adjacent selected anchors must have causal survival level strictly below the minimum survival of the selected boundary pair;
- scale realizations of the same ordered five-ridge-ID identity are one object.

The union of F3 identities seen at these 240 checkpoints is the bounded v0.7.2 publication-precheck object universe.

This census is label-free. It is not an independent morphology validation set and does not change the v0.7.1 Development support result.

## 4. Causal first-known F3 event semantics

For every checkpoint-census F3 identity `R=(r0,r1,r2,r3,r4)`, reconstruct a prefix-only event stream from the frozen ridge lineage.

### 4.1 Identity

The canonical semantic identity is the ordered five ridge IDs. Scale level and filtered occurrence coordinates are evidence/representation fields, not identity fields.

The identity is stable across every later scale realization. A cryptographic publication ID is derived from the ordered ridge-ID tuple only.

### 4.2 Prefix-causal survival

At replay cutoff `t`, the causal survival level of a ridge ID is the maximum scale level at which any representation of that ridge ID has confirmation index `<=t`.

No representation confirmed after `t` may contribute.

### 4.3 Prefix-causal F3 evidence realization

At scale level `l`, the identity has an eligible F3 realization at replay cutoff `t` when:

1. all five ridge IDs have level-`l` representations confirmed by `t`;
2. those five representations are strictly ordered by occurrence and alternate kind;
3. for each adjacent selected pair, inspect same-level ridge nodes lying strictly between their occurrences **that are themselves confirmed by `t`**;
4. every such visible skipped ridge has prefix-causal survival strictly below the minimum prefix-causal survival of the selected boundary ridge IDs.

This is the causal event form of the frozen v0.7.1 persistence-dominance relation. It introduces no chart-distance, amplitude, duration, skip-count, persistence, or human-label threshold.

### 4.4 First-known event

The F3 first-known event is the earliest ridge-confirmation cutoff `t` at which at least one eligible realization exists.

If several realizations are valid at the same earliest `t`, publishing evidence is chosen deterministically by:

1. smallest scale level;
2. lexicographically smallest five filtered occurrence indices;
3. lexicographically smallest five node IDs.

The event then freezes:

- ordered five ridge IDs;
- first-known confirmation bar/time;
- publishing level;
- publishing five filtered occurrence bars;
- publishing five node IDs;
- phase/kind sequence;
- prefix-causal survival levels of the five identity ridges at publication.

Later evidence never rewrites this publication event.

## 5. Later evidence, multiplicity, and rewrite accounting

Later prefix cutoffs may add valid scale realizations, remove current-state eligibility, or change the deterministic current canonical realization as ridge persistence information arrives. These are state/evidence updates, not retroactive edits to the first-known event.

For each identity record aggregate-safe diagnostics:

- number of relevant causal evidence cutoffs examined;
- number of valid-evidence cutoffs after first publication;
- number of distinct valid filtered-occurrence representations seen after publication;
- whether any later valid representation differs from the published five filtered bars (`would_rewrite_filtered_coordinates`);
- whether current-state F3 eligibility ever becomes false after publication and later true again (`validity_gap_after_publication`);
- number of valid scale realizations at first publication.

For checkpoint multiplicity report:

- F3 object-count distribution across all 240 checkpoints;
- union unique F3 identity count;
- first-publication fan-out distribution: number of identities sharing the same first-known confirmation bar;
- counts/fractions with later filtered-coordinate rewrite pressure and validity gaps.

No case-ID → object table is committed.

## 6. Frozen continuity and publication gates

v0.7.2 uses **hard causal/identity invariants**, not a fitted statistical threshold.

Every checkpoint-census F3 identity must satisfy all of the following:

### Gate A — causal reconstruction

A first-known F3 event exists and is no later than every checkpoint at which that identity was observed by the frozen v0.7.1 checkpoint semantics.

### Gate B — checkpoint continuity

At every checkpoint where the identity appears in the frozen v0.7.1 F3 census, the prefix-causal event formulation in §4 has at least one valid realization at that same cutoff.

This prevents v0.7.2 from silently changing the selected F3 family while introducing event semantics.

### Gate C — stable identity

The ordered five ridge IDs retain one kind sequence and one deterministic publication ID. Any ridge-kind contradiction or identity-hash collision fails closed.

### Gate D — deterministic first publication

The frozen evidence ordering produces exactly one publishing evidence realization for every first-known event. Re-running the construction on the same frozen lineage must be definitionally deterministic; ties are resolved only by the frozen keys above.

### Decision

If any gate fails:

`v0702_f3_causal_event_publication_precheck_failed`

If all gates pass:

`v0702_f3_append_only_event_publication_structurally_transplantable`

Rewrite pressure and validity gaps are **descriptive diagnostics** and do not trigger parameter fitting. The append-only event remains historical even if later current-state eligibility changes.

## 7. Historical v0.6.x downstream contract precheck

This stage distinguishes **concept transplantability** from direct function compatibility.

### v0.6.5 append-only publication

The historical concept — deterministic evidence ordering, first valid causal evidence publishes once, later evidence cannot rewrite — is eligible for conceptual transplantation if v0.7.2 Gates A-D all pass.

The historical v0.6.5 function is **not** reused as semantic identity authority because it keys canonical identity from phase + five filtered bars, whereas F3 authority is ordered five ridge IDs. v0.7.2 therefore freezes a new F3 publication event rather than aliasing it to the legacy exact-tuple identity.

### v0.6.4 raw projection / predecessor adapter

Direct reuse is frozen as **not contract-compatible** at this stage: the historical `locate_birth_predecessor()` explicitly requires the five birth nodes to be consecutive at the birth level, while F3 is intentionally nonconsecutive.

This is an adapter gap, not a scientific rejection of raw projection. v0.7.2 does not choose a new predecessor or raw-projection window.

If v0.7.2 passes, the next authorized stage is to freeze and test an **F3-specific raw-projection/predecessor adapter** before any qualification or direction transplantation.

## 8. Prohibited shortcuts

v0.7.2 may not:

- read human anchors or use human-reference labels in the primary event/publication decision;
- refit F3 persistence semantics;
- fit bar distance, skip count, amplitude, duration, or persistence thresholds;
- promote F3 to morphology authority;
- use future ridge survival when reconstructing a prefix event;
- rewrite a first-known event from later evidence;
- silently treat nonconsecutive F3 nodes as a legacy consecutive tuple birth;
- alter v0.6.4 predecessor semantics inside this stage;
- restore v0.6.18 qualification or D1/v0.6.25 direction authority.

## 9. Governance invariants

Whatever the result:

- `human_reference_labels_used=false` for the primary analysis;
- `threshold_fitting_performed=false`;
- `F3_definition_changed=false`;
- `raw_projection_changed=false`;
- `qualification_changed=false`;
- `direction_winner_changed=false`;
- `morphology_acceptance=false`;
- `trade_authority=false`;
- `production_authority=false`.
