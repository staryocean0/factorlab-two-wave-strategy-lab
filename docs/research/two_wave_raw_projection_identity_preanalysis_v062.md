# v0.6.2 Preanalysis — raw-projection financial identity audit

Date: 2026-09-06

Status: **FROZEN BEFORE ANY v0.6.2 OUTPUT IS READ**

Operational baseline remains **v0.4.3**. Global morphology status remains `morphology_replication_not_yet_accepted`. This is an attribution/audit stage only. It does not authorize a replacement projection, D1/D2/PAWCT, H1/H2, third-wave, return/P&L, fresh OOS, paper trading, or production.

## 1. Inherited evidence that is allowed to motivate this audit

v0.6.1 was frozen and executed before this preanalysis. Its accepted result is therefore prior evidence, not a v0.6.2 outcome:

- 2,223 v0.6.0 unmatched main pair-observations were decomposed across offset0 vs offset1..4;
- `post_tuple_birth_loss` was the largest single primary category: 789 / 35.49%;
- 787 / 789 of those cases had valid projection/evaluation but raw projected anchors displaced beyond the already-frozen one-nominal-5m-bar same-event relation;
- phase mismatch and mutual-unique ambiguity were negligible;
- filtered-extremum / tuple-topology instability and qualification survival remain independent substantial problems and are not superseded by this audit.

The only permitted inference at the start of v0.6.2 is therefore:

> The existing **filtered tuple → raw-price extrema projection** deserves an independent identity audit. Nothing yet says which projection mechanism is wrong or what should replace it.

## 2. Existing frozen projection semantics being audited

The v0.5.2 exact-ridge run deliberately reuses the v0.5.1 raw projection. For one filtered five-extremum tuple `f0..f4`, the current operator:

1. derives raw-close phase windows from filtered bar indices;
2. uses `left = max(0, 2*f0 - f1)` for the first lower bound;
3. uses upper bounds `[f1-1, f2-1, f3-1, f4-1, member_confirmation]`;
4. scans each window sequentially for the raw close max/min matching the expected phase;
5. breaks exact equal-price ties by choosing the **last** occurrence;
6. after selecting one raw extremum, sets the next lower bound to `previous_raw_occurrence + 1`;
7. freezes the points at the existing confirmation clock and then calls the unchanged scale qualification / D1 machinery.

No outcome or return is used. The operator is causal in the ordinary prefix sense, but causal prefix stability and cross-slicing financial-identity stability are different properties and must not be conflated.

## 3. Why a separate identity layer is necessary

The filtered exact-ridge tuple already has a structural identity before raw projection. A valid raw projection should therefore be auditable as a mapping

`filtered parent identity -> raw financial anchor identity`

rather than being treated as an invisible implementation detail.

There are two logically distinct questions:

### RQ-A — single-view single-valuedness

If the same canonical filtered tuple is observed as more than one birth-scale / confirmation evidence item inside one view, does the current projection always map it to exactly one raw five-anchor identity?

If not, raw identity depends on later scale/confirmation evidence rather than only on the already-defined filtered financial parent identity.

### RQ-B — harmless-slicer equivariance

For filtered tuple identities that already form a same-phase mutual-unique cross-view match under the unchanged five-anchor `<=5m` relation, do their raw projections also form one financial identity under that same relation?

If filtered identity is stable but raw identity is not, the loss is located in projection rather than in the tuple matcher.

## 4. Candidate mechanisms to distinguish — hypotheses, not conclusions

The audit must be able to separate at least the following mechanisms without changing the projection:

1. **within-view multi-projection identity** — duplicate filtered-tuple evidence in one view yields different raw anchor tuples;
2. **confirmation-tail dependence** — especially ordinal 4, because its current upper bound is member confirmation rather than the next filtered phase boundary;
3. **phase-window boundary exclusion** — the cross-view raw counterpart lies outside the other view's corresponding absolute-time projection window;
4. **5m sampling-lattice aliasing** — the two absolute phase windows support the same canonical underlying 1m close extremum, but the two supplied 5m close lattices select different extrema;
5. **window-semantics instability** — even when evaluated against the common supplied `1m_official` close path, the two current absolute phase windows select different extrema beyond one nominal 5m bar;
6. **exact-tie / plateau dependence** — current `last_argextreme` tie rule participates in the identity change;
7. **sequential propagation** — an earlier raw selection changes a later lower bound and displaced anchors appear as a suffix of the five-point sequence;
8. **interior competition** — the projected extrema differ even though neither counterpart is excluded by the paired absolute windows and no exact tie explains it.

These diagnostics may overlap. v0.6.2 will not force them into one mutually-exclusive primary category unless the frozen protocol below explicitly defines such an accounting.

## 5. Control universe — do not condition only on failures

The primary cross-view universe must be **all same-phase mutual-unique canonical filtered-tuple pairs** between `5m_offset_0` and each of `5m_offset_1..4`, using the exact v0.6.1 filtered-tuple relation:

- ordered five corresponding filtered occurrence timestamps;
- every absolute timestamp delta `<= 5 minutes`;
- mutual-unique only;
- no tie-break.

This universe must then be stratified into:

- raw-projection stable controls;
- raw-projection displaced cases;
- within-view multi-valued projection groups;
- projection-invalid evidence.

The accepted v0.6.1 `post_tuple_birth_loss` subset is retained as a named target stratum and its counts must reproduce, but it is not allowed to define the whole v0.6.2 sample.

## 6. Canonical 1m diagnostic — audit-only, never recognizer input

The repository already ships `data/development/1m_official.parquet`. v0.6.2 may use it **only as an audit control** to distinguish view-specific 5m sampling-lattice effects from instability of the projection windows themselves.

For each current 5m projection window, convert its existing lower/upper bar bounds to absolute timestamps. On the shipped 1m close series, within that unchanged absolute-time interval, select the same expected max/min using the same last-exact-tie convention.

Important boundaries:

- do not resample 1m into new 5m bars;
- do not feed 1m results into v0.5.2/v0.5.4 recognition or qualification;
- do not use 1m to choose a better projection after seeing results;
- compare paired 1m diagnostic anchors with the already-frozen `<=5m` financial-identity relation, not a new fitted tolerance.

Interpretation is diagnostic only:

- 5m raw displaced + 1m diagnostic strict-match supports a **5m sampling-lattice** mechanism;
- 5m raw displaced + 1m diagnostic displaced supports a **window-semantics / phase-support** mechanism;
- neither observation by itself authorizes a replacement operator.

## 7. Causality is a separate invariant

The current operator is frozen at existing confirmation clocks. v0.6.2 must preserve and explicitly test the distinction:

- **prefix immutability:** appending future bars after the frozen confirmation clock cannot rewrite a published projection;
- **financial-identity invariance:** harmless slicing of the same market path should not map a stable filtered parent to a materially different raw financial event.

Passing the first does not imply the second.

## 8. Invariants any future replacement would eventually need

This audit does not implement a replacement. Before any later repair is allowed, a separate preanalysis must show how a proposed mapping can satisfy at least:

1. causal publication / zero future rewrite;
2. a single-valued raw identity for one canonical filtered parent, independent of later duplicate scale evidence;
3. ordered alternating raw-price anchors;
4. no cross-view information inside a single-view recognizer;
5. no outcome, return, direction label, case label, or P&L in projection selection;
6. harmless-slicer financial-identity stability measured by an ex-ante relation;
7. no restoration of exclusive packing as morphology identity authority.

## 9. Forbidden v0.6.2 actions

- do not change `project_event_to_raw`;
- do not change the `<=5m` matcher after looking at displacement distributions;
- do not tune ridge linking, sigma schedule, tuple-birth certification, qualification thresholds, packing, D1/D2/PAWCT;
- do not select the "best" scale member or the closest projection post hoc;
- do not use 1m diagnostic anchors as a new recognizer output;
- do not use returns/outcomes;
- do not enter third-wave/trading.

The next file, `two_wave_raw_projection_identity_protocol_v062.md`, freezes the executable audit schema before any v0.6.2 empirical output is read.
