# Two-Wave v0.7.0 — Semantic-Bridge Counteroffensive / Salvage Staircase

Status: **frozen before any v0.7.0 human-conditioned salvage statistics are read**.

## 1. Why the counteroffensive starts here

The historical chain contains a structural/semantic bridge that was never independently validated before v0.6.48:

1. v0.5.2 constructs exact-ridge five-node tuples and causal tuple births;
2. `_projection_adapter()` wraps each five-node birth directly as a `TwoWaveCandidate`;
3. raw projection produces five raw anchors;
4. `evaluate_pair()` interprets five alternating confirmed pivots as two complete cycles sharing the center pivot, then applies same-scale and direction logic;
5. v0.5.4 explicitly freezes parent representation / identity to v0.5.2 exact-ridge births, so the later qualification and direction lineage inherits this semantic bridge.

v0.6.48–v0.6.52 show that the current published/qualified object is not independently calibrated to the target human parent semantics, while multiple downstream local explanations have been rejected. The counteroffensive therefore begins at the **structural-support → semantic-parent bridge**, not at the data clock, not by deleting ridge infrastructure, and not by discarding downstream components before retesting them.

## 2. Objective

Determine the earliest layer at which the target human-positive parent object stops being supported by the existing causal infrastructure.

This is a **salvage audit**, not a new recognizer and not morphology acceptance.

The intended outcome is a component-retention map:

- `retain_without_semantic_change`;
- `retain_as_support_infrastructure_but_not_parent_authority`;
- `requires_reconstruction_or_revalidation`;
- `downstream_component_not_yet_retested`.

## 3. Frozen evidence universe

Primary diagnostic universe:

- the frozen v0.6.48 final reference labels;
- only reference-positive candidate cases with complete valid final-reference `p0..p4` anchors;
- expected count: exactly `11` cases;
- final reference SHA256: `321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d`;
- source main-view SHA256: `bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`;
- sampling commitment SHA256: `f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8`.

This is Development/discovery evidence only. It cannot establish morphology acceptance.

No annotator notes/confidence, future bars, returns, PnL, D1/v0.6.25 output, or case-specific threshold fitting may be used.

## 4. Frozen human-anchor support cells

For each case map final-reference chart positions `p0..p4` to source bars `h0..h4` in the frozen 96-bar chart.

Infer the alternating anchor kind from observed close prices:

- if `close[h1] > close[h0]`, kinds are `low,high,low,high,low`;
- otherwise kinds are `high,low,high,low,high`.

The five human anchors must form strict alternating price turns; otherwise the audit fails closed.

Define a deterministic support cell for each human anchor, without fitting any bar tolerance:

- endpoint half-width uses half the adjacent human-anchor spacing;
- interior boundaries are integer midpoints between adjacent human anchors;
- all cells are clipped to the frozen 96-bar chart;
- cells must be ordered and non-overlapping except for a possible shared midpoint assigned deterministically to the earlier cell.

A model/extremum/ridge anchor is considered semantically compatible with human ordinal `i` only when its occurrence bar lies inside human cell `i` and its kind matches the inferred human kind.

No nearest-neighbor distance threshold is fitted.

## 5. Salvage staircase

For every one of the 11 cases evaluate the following cumulative layers at the frozen cutoff.

### L0 — observed raw-turn support

Within each human support cell, the observed close series must contain at least one extremum of the required kind. Record the deterministic last arg-extreme and whether the human anchor itself is that arg-extreme.

This layer tests only whether the chart semantics are compatible with the raw close series.

### L1 — causal TCSS extremum / ridge support

`L1=true` only if there exists at least one scale level where each of the five human cells contains a confirmed ridge node of the required kind with node confirmation `<= cutoff`.

Because ridge nodes are the retained causal-extremum infrastructure, this tests whether the target object is representable in the existing TCSS/ridge state space at one common scale.

### L2 — exact-ridge five-tuple support at any scale

`L2=true` only if, by cutoff, there exists an exact-ridge tuple whose five nodes fall one-per-cell in ordinal order and have the inferred kinds.

The tuple need not be the legacy published tuple and need not yet be a tuple birth.

### L3 — causal exact-ridge tuple-birth support

`L3=true` only if a v0.5.2 `RidgeTupleBirth` satisfying the same one-node-per-human-cell mapping has `confirmation_index <= cutoff`.

This tests the causal child-death / first-adjacency birth rule separately from mere tuple existence.

### L4 — legacy canonical filtered identity support

At the frozen candidate cutoff, select the v0.6.18-qualified identity using the already frozen v0.6.50 canonical rule: unique identity when unique; otherwise lexicographic order of `published_raw_occurrence_bars`, then `phase`.

`L4=true` only if its five **filtered occurrence bars** fall one-per-human-cell with correct kinds.

This tests whether the actual legacy candidate identity corresponds to the human parent before raw projection.

### L5 — legacy published raw identity support

`L5=true` only if the same canonical identity's five **published raw occurrence bars** fall one-per-human-cell with correct kinds.

This isolates raw projection from the filtered ridge identity.

## 6. Retention rule

Use a prespecified support threshold of `8/11` cases for a layer to be considered **development-level salvage supported**.

The threshold is deliberately coarse and is not a production acceptance criterion.

Apply cumulative precedence:

1. if `L1 < 8/11` → `v0700_ridge_state_space_not_sufficiently_aligned_with_reference_parent`;
2. else if `L2 < 8/11` → `v0700_ridge_infrastructure_salvage_supported_exact_tuple_objectization_breaks_semantic_bridge`;
3. else if `L3 < 8/11` → `v0700_exact_tuple_support_salvaged_tuple_birth_rule_breaks_semantic_bridge`;
4. else if `L4 < 8/11` → `v0700_tuple_birth_support_salvaged_legacy_identity_selection_breaks_semantic_bridge`;
5. else if `L5 < 8/11` → `v0700_filtered_identity_salvaged_raw_projection_breaks_semantic_bridge`;
6. else → `v0700_structural_identity_and_projection_salvaged_semantic_completion_or_qualification_bridge_remains`.

L0 is a sanity control and does not determine the main category unless it fails structurally.

## 7. Additional aggregate diagnostics

Report without changing the decision rule:

- per-ordinal human-anchor exact raw arg-extreme incidence;
- per-ordinal nearest compatible common-scale ridge-node distance in bars when L1 support exists;
- number of common scale levels supporting all five human cells;
- number of exact tuples and births matching the human cells by cutoff;
- for L4/L5, per-ordinal cell-hit incidence;
- transition counts `L1→L2`, `L2→L3`, `L3→L4`, `L4→L5`.

No case-level hidden mapping table may be committed.

## 8. Salvage interpretation

Whatever the result:

- data clock / source hash / causal replay / governance remain retained infrastructure;
- ridge infrastructure is retained or demoted according to L1/L2 evidence, not deleted;
- v0.6.4/v0.6.5 raw projection/publication, v0.5.4/v0.6.18 qualification, and D1/v0.6.25 direction remain **historical components awaiting transplantation tests** unless the staircase directly localizes a failure at their layer;
- no downstream historical conclusion is declared false solely because its original upstream object assumption failed;
- every downstream component must later be re-tested on the repaired semantic object before it can be retained as active authority.

## 9. Governance

This audit cannot:

- change morphology acceptance;
- change qualification authority;
- promote a direction winner;
- fit human-anchor tolerances;
- create a production recognizer;
- tune a new object constructor to these 11 cases.

The next action after v0.7.0 is determined by the earliest unsupported staircase layer, and then proceeds forward layer-by-layer so that salvageable downstream results can be transplanted rather than discarded wholesale.
