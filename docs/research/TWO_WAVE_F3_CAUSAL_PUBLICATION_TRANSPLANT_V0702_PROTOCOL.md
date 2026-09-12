# Two-Wave v0.7.2 — F3 Causal Event / Publication + Downstream Transplant Precheck

Status: **frozen before any v0.7.2 F3 event/publication statistics are read**.

## 1. Starting point

v0.7.1 retained the causal TCSS/ridge infrastructure and supported one reconstructed semantic-parent object family on frozen Development reference evidence:

- `F3 = persistence-dominant nonconsecutive quintet`;
- support `8/11` anchored reference-positive cases;
- no fitted distance, skip-count, persistence, amplitude, or duration threshold;
- F3 remains a Development reconstruction candidate, not morphology authority.

Before any historical qualification or direction result can be transplanted, F3 needs a causal event/publication contract. The old v0.6.5 append-only publication concept may be salvageable, but it cannot be assumed to transfer unchanged.

## 2. Primary audit universe is label-blind

The primary audit uses the already committed v0.6.48 **240-case packet cutoff universe** only as a deterministic set of historical 96-bar cutoffs.

Frozen controls:

- source main-view SHA256: `bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`;
- sampling commitment SHA256: `f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8`;
- packet size: exactly `240` cutoffs;
- chart length: `96` bars.

The primary audit **must not read**:

- final reference labels;
- candidate/control stratum when computing or reporting metrics;
- annotator notes/confidence;
- D1/v0.6.25 outputs;
- future returns or PnL.

The legacy v0.6.18 publication chain may be replayed only to reconstruct the frozen packet cutoff commitment. Its labels/qualification do not enter the F3 event decision.

## 3. Frozen F3 object identity

F3 definition is exactly v0.7.1:

- five ordered distinct ridge IDs;
- alternating kinds;
- at one common eligible scale realization;
- any skipped same-level ridge between adjacent selected anchors must have causal survival level strictly below the minimum causal survival level of the two selected boundary ridges.

Object identity is the ordered five-ridge-ID tuple, independent of which scale level realizes it.

No F3 family parameter may change in v0.7.2.

## 4. Why a stronger causal certificate is needed

Ordinary F3 validity at cutoff uses the **currently observed** causal survival levels. A skipped ridge may simply not yet have a confirmed continuation to a coarser scale; absence of continuation is not by itself an immutable death statement.

Therefore ordinary first-observed F3 validity is not automatically an append-only publication event.

v0.7.2 introduces no new semantic filter. It audits whether existing v0.5.2 explicit ridge-death evidence can supply a monotone certificate for the already frozen F3 relation.

## 5. Death-certified F3 event

Consider one F3 realization of selected ridges `(r0..r4)` at scale level `l` at frozen cutoff `c`.

For each adjacent selected pair `(ri, r{i+1})`, inspect the same-level ridge nodes skipped between them.

### Gap with no skipped ridge

The gap is certified once both selected level-`l` nodes are confirmed.

### Gap with skipped ridges

A witness level `k > l` certifies the gap only when, by the event time:

1. both selected boundary ridge IDs have confirmed ridge-node representations at level `k`;
2. every skipped ridge has an explicit existing v0.5.2 `RidgeDeath` whose `coarse_level <= k`;
3. every such death is already causally confirmed.

Use the **lowest witness level `k`** satisfying these conditions. The gap certificate time is the maximum confirmation index of the two boundary representations at `k` and all required skipped-ridge deaths.

If no witness exists by cutoff, that realization is not death-certified by cutoff.

The realization certificate time is the maximum of:

- all five selected level-`l` node confirmations;
- its four gap certificate times.

The object certificate time is the earliest certificate time among all F3 scale realizations of the same ridge-ID tuple that are valid at the frozen cutoff.

This certificate is intended to be monotone: it relies on confirmed selected-ridge survival and explicit irreversible ridge-death evidence, not on a provisional lack of future continuation.

## 6. Required runtime verification

For every certified object, replay the exact ridge state using only confirmations `<= certificate_time` and verify that the same ridge-ID tuple is already a valid F3 object at that time.

Any certificate that fails this causal replay check fails the audit closed.

No future information may be used to move the reported certificate time earlier.

## 7. Aggregate metrics

Across the pooled 240 cutoff charts report only aggregate statistics:

- number of cutoffs containing at least one ordinary F3 object;
- ordinary F3 unique-object count distribution per cutoff;
- total ordinary final-cutoff F3 objects;
- number/fraction of those objects death-certified by the same cutoff;
- number/fraction of F3-positive cutoffs containing at least one certified object;
- certified-object count distribution per F3-positive cutoff;
- certificate delay distribution in bars from the selected base-realization confirmation to immutable certificate time;
- fraction of certified objects requiring at least one skipped-ridge death witness;
- fraction certifiable immediately with no skipped ridge;
- certificate replay failure count (must be zero).

Do not commit case-level object IDs, case IDs, hidden strata, or object/reference joins.

## 8. Frozen Development decision rules

### Gate A — causal certificate coverage

Both must hold:

1. at least `80%` of ordinary final-cutoff F3 objects are death-certified by the same cutoff;
2. among cutoffs containing at least one ordinary F3 object, at least `80%` contain at least one death-certified F3 object.

This `80%` is a coarse Development salvage threshold, not morphology acceptance.

### Gate B — direct single-parent publication identifiability

Evaluated only if Gate A passes.

Direct single-parent publication is considered structurally identified only when, among F3-positive cutoffs:

- median certified-object count `<= 1`; and
- 75th percentile certified-object count `<= 2`.

No ranking rule is fitted if multiplicity exceeds this band.

### Verdict precedence

1. If Gate A fails: `v0702_f3_death_certificate_coverage_insufficient_event_semantics_not_frozen`.
2. Else if Gate B fails: `v0702_f3_immutable_event_certificate_supported_append_only_concept_salvaged_object_selection_unresolved`.
3. Else: `v0702_f3_immutable_event_and_single_parent_publication_precheck_supported`.

## 9. Downstream transplant precheck — code-contract only

This section does not score human labels.

### v0.6.5 append-only publication

The **concept** `publish once from an immutable causal certificate; later evidence cannot rewrite that same object identity` is eligible for salvage if Gate A passes.

Do not claim the old v0.6.5 grouping key or exact function can be reused unchanged; F3 identity is a ridge-ID tuple, not a legacy exact filtered tuple.

### v0.6.4 predecessor raw projection

The old implementation is **not directly transplantable unchanged** because `locate_birth_predecessor()` explicitly requires the five birth nodes to be consecutive at one level. F3 is nonconsecutive by construction.

This does not prove the sequential raw-projection idea wrong. It means a generalized F3 projection contract must be separately frozen before qualification retesting.

### v0.6.6 / v0.6.18 qualification

The qualification interface consumes five ordered raw anchors, phase, confirmation, and bars. It is therefore structurally eligible for a later transplantation test once an F3 raw projection is frozen, but its thresholds/semantics are not validated in v0.7.2.

### D1 / v0.6.25 direction

Direction remains downstream and untouched. Historical conclusions are retained; no active direction authority is restored in v0.7.2.

## 10. Prohibited shortcuts

v0.7.2 may not:

- read reference labels to choose event timing or selection;
- fit a persistence, distance, skip-count, multiplicity, or delay threshold;
- choose one F3 object using human-anchor proximity;
- transplant v0.6.4 raw projection by silently forcing nonconsecutive nodes into its consecutive-birth contract;
- retune v0.6.18 or D1/v0.6.25;
- change morphology acceptance, trade authority, or production authority.

## 11. Next step

- If Gate A fails: reconstruct causal event semantics before any downstream transplantation.
- If Gate A passes but Gate B fails: preserve the append-only publication concept and freeze a purely structural F3 object-selection / uniqueness protocol next.
- If A and B pass: freeze generalized F3 raw projection next, then retest v0.5.4/v0.6.18 qualification, then D1/v0.6.25 direction in that order.
