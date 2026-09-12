# Two-Wave v0.7.2 — F3 Causal Event / Publication Semantics and Downstream Transplant Precheck

Status: **frozen before any v0.7.2 event-certification, projection-preservation, or downstream-interface statistics are read**.

## 1. Starting point

v0.7.0 localized the first major semantic break to legacy exact-consecutive five-ridge objectization while retaining the causal TCSS/ridge state space. v0.7.1 then froze and tested structural reconstruction families and selected:

`F3 = persistence-dominant nonconsecutive ridge quintet`

Development discovery evidence:

- F0 legacy exact tuple: `3/11` anchored reference-positive cases;
- F1 unconstrained ordered common-scale upper bound: `10/11`;
- F2 one-step survivor: `5/11`;
- F3 persistence-dominant nonconsecutive quintet: `8/11`.

v0.7.1 did **not** define a production/event publication contract. v0.7.2 therefore asks whether F3 can be converted into an immutable causal event without losing its frozen `8/11` semantic support, and which downstream legacy interfaces can be transplanted without retuning.

Formal v0.7.1 result commit: `bc6f75a9734e90bbb158ea3377fd3710a391450e`.

## 2. Frozen evidence and controls

Primary Development/discovery universe remains exactly the same 11 v0.6.48 final-reference candidate cases with complete valid final-reference `p0..p4` anchors.

Frozen inputs:

- source SHA256: `bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`;
- final reference SHA256: `321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d`;
- sampling commitment SHA256: `f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8`;
- frozen v0.7.0 human support cells and kind inference;
- frozen v0.7.1 F3 definition and unique ridge-ID object identity.

Expected static F3 support is exactly `8/11`; drift fails closed.

No annotator notes/confidence, future bars, returns, PnL, D1/v0.6.25 reference performance, threshold search, distance fitting, persistence fitting, or case-specific object selection may be used.

## 3. F3 causal certification

The v0.7.1 cutoff definition used currently confirmed ridge survival. v0.7.2 requires a stronger permanent certificate before an F3 realization may become an event.

For an F3 realization at scale level `l`, let the five selected ridge nodes be ordered `r0..r4`. For every same-level ridge skipped between adjacent selected anchors:

1. the skipped ridge must have an explicit frozen v0.5.2 `RidgeDeath` at transition `s -> s+1`, with `s >= l`;
2. that death's `confirmation_index` must be known;
3. both selected boundary ridge IDs around that skipped ridge must have confirmed representations at level `s+1`;
4. the selected boundary representations and the skipped-ridge death must all be confirmed by the event time.

This permanently proves:

`survival(skipped) < min(survival(left selected), survival(right selected))`.

A gap with no skipped ridge requires no death certificate.

The causal confirmation of one realization is the maximum of:

- confirmations of the five selected nodes at realization level `l`;
- every required skipped-ridge death confirmation;
- every selected-boundary representation used to prove survival past a skipped ridge's death level.

A realization is publishable by a frozen cutoff only when its causal confirmation is `<= cutoff`.

No future survival level may be used in place of these explicit causal certificates.

## 4. F3 object event identity

F3 object identity remains the ordered five-ridge-ID tuple from v0.7.1. Scale level is a realization, not object identity.

For one object with multiple causally certified realizations, define its first event realization by lexicographic order of:

1. causal confirmation bar;
2. realization level;
3. selected occurrence-bar tuple;
4. selected node-ID tuple.

The object event is immutable once this first certified realization exists. Later realizations do not rewrite the event identity or confirmation.

## 5. Nonconsecutive predecessor raw-projection transplant

The historical v0.6.4 projection principle is retained, but its exact-consecutive tuple precondition cannot be retained because F3 intentionally allows skipped lower-persistence ridges.

Frozen v0.7.2 transplant adapter:

1. use the event realization's common scale level;
2. locate selected ridge `r0` in the full ordered ridge sequence at that level;
3. use the immediately preceding same-level ridge as the real predecessor;
4. predecessor kind must be opposite to `r0` and predecessor confirmation must be `<= event confirmation`;
5. ordinal-0 raw-search lower bound = `predecessor occurrence + 1`;
6. ordinal `1..4` lower bounds are the previous selected raw anchor + 1, exactly preserving the sequential v0.6.4 principle;
7. raw-search upper bounds are selected filtered occurrences `r1-1, r2-1, r3-1, r4-1`, followed by the last selected node's own confirmation for ordinal 4;
8. within each window use the frozen last raw-close arg-extreme of the required kind;
9. the five projected raw anchors must be strictly ordered alternating actual price turns.

No bar-distance tolerance, amplitude rule, duration rule, human anchor, or future value enters projection.

This adapter is a **transplant precheck**, not active authority.

## 6. First-valid immutable raw publication per F3 object

For every F3 ridge-ID object, causally certified realizations are processed in the frozen event order from §4.

- invalid raw projections before publication remain recorded as prior invalid evidence;
- the first valid raw projection becomes the immutable published raw identity for that F3 object;
- later valid identical raw tuples are confirming evidence;
- later valid different raw tuples are `suppressed_would_be_rewrite` and never modify the publication.

This preserves the v0.6.5 first-valid / immutable principle while changing the grouping key from the legacy filtered exact tuple to the reconstructed F3 ridge-ID object.

## 7. Frozen semantic-preservation tests

For the 11 anchored reference-positive cases report:

- static F3 support count (must reproduce `8/11`);
- causally certified F3 support count;
- cases with at least one first-valid published F3 raw identity whose five raw anchors fall one-per-frozen human support cell with correct kinds;
- event-certification delay distribution;
- number of certified F3 objects, published F3 objects, prior-invalid projections, later-valid confirmations and suppressed rewrites;
- per-ordinal published-raw cell-hit incidence.

The inherited Development salvage threshold remains `8/11`.

No new threshold may be introduced.

## 8. Downstream transplantation interface precheck

For every valid published F3 raw identity, without reference scoring:

1. run the existing `evaluate_pair()` contract unchanged;
2. run v0.6.6 published-identity qualification and v0.6.18 path-gate demotion unchanged;
3. run D1 extraction unchanged;
4. run the frozen v0.6.25 absolute-margin erosion-consensus rescue unchanged.

Report only:

- interface exception count (must be zero to call an interface transplantable);
- v0.6.18 qualification counts/rate, descriptive only;
- D1 and v0.6.25 state counts, descriptive only;
- D1 decisive override count under v0.6.25 (must remain zero as an invariant).

**No human-reference exact agreement, calibration, threshold retuning, or direction gate is evaluated in v0.7.2.** A downstream component can be called structurally transplantable while still lacking semantic authority.

## 9. Frozen decision precedence

1. If static F3 support != `8/11`: fail closed for v0.7.1 lineage drift.
2. Else if causally certified F3 support < `8/11`:
   `v0702_f3_static_objectization_not_causally_publishable`.
3. Else if first-valid published F3 raw semantic support < `8/11`:
   `v0702_f3_event_salvaged_raw_projection_requires_reconstruction`.
4. Else if any downstream interface exception occurs or v0.6.25 overrides a D1-decisive state:
   `v0702_f3_event_projection_salvaged_downstream_interface_incompatible`.
5. Else:
   `v0702_f3_event_projection_publication_transplant_supported_downstream_semantic_retest_next`.

Passing v0.7.2 means only that causal F3 event semantics and the listed downstream interfaces are technically transplantable. It does not restore v0.6.18 or v0.6.25 authority.

## 10. Governance / retained成果

Whatever the result:

- source/data/clock/replay/governance remain retained;
- TCSS extrema/ridge lineage remains retained;
- F3 remains only a Development reconstruction candidate unless v0.7.2 fails earlier;
- v0.5.2 exact-consecutive tuple remains historical baseline, not active parent authority;
- v0.6.4 predecessor projection principle and v0.6.5 immutability principle are preserved if the transplant precheck passes, even though their object adapters/keys change;
- v0.5.4/v0.6.18 qualification and D1/v0.6.25 direction remain historical成果 awaiting semantic retest, not declared false.

No morphology acceptance, trade authority, or production authority may be granted by this stage.
