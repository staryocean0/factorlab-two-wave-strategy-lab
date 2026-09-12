# Two-Wave v0.7.5 — F3 Provisional Lifecycle Raw-Projection / Immutable-Publication Transplant

Status: **frozen before any v0.7.5 publication statistics are read**.

## 1. Starting authority

v0.7.4 established that the frozen F3 persistence-dominant ridge identity can be represented as a prefix-causal append-only lifecycle object:

- static F3 support `8/11`;
- lifecycle-live support `8/11`;
- terminal C1-certified support `7/11`;
- one semantic-support case remains `observed_live_unresolved` rather than being falsely future-certified;
- hard lifecycle invariant violations `0`;
- `1543` observed objects, `1478` certified objects, `65` unresolved at their frozen case cutoff;
- no dormant/reobserved transitions in the frozen 11-case Development universe.

Formal v0.7.4 result commit: `96e528680b42e42b1951b9b656a9ed790c51073d`.

v0.7.2 separately provided positive historical transplant evidence for:

- the v0.6.4 sequential raw-projection principle;
- the v0.6.5 first-valid immutable-publication principle;
- published-raw semantic support `9/11`;
- per-ordinal raw cell-hit cases `11/11, 11/11, 11/11, 11/11, 10/11`;
- `1478` unique published certified F3 raw records;
- `0` prior-invalid projections under that certified-event adapter;
- `2378` later-valid same identities;
- `223` later-valid would-be rewrites suppressed.

But v0.7.2 attached publication only after permanent certification. v0.7.5 asks whether the retained raw-projection/publication principles can attach causally to the v0.7.4 lifecycle beginning at first `observed`, including the unresolved eighth semantic case, without backdating later certification or rewriting the first raw identity.

## 2. Scientific question

Can every lifecycle object be offered prefix-causal raw-projection evidence from its first `observed` event onward, publish the **first valid** raw identity immutably, and later append C1 certification status without changing that publication?

The test must distinguish:

1. object observation time;
2. raw-publication time;
3. lifecycle status at publication (`observed_live_unresolved` or `certified`);
4. later certification time, if any;
5. later projection evidence that agrees with or would rewrite the frozen published raw identity.

Publication may occur at the first observation bar or later if the first observation has no valid causal projection. The object event remains the original v0.7.4 first observation and is never backdated or rewritten.

## 3. Frozen universe and upstream replication

Use exactly the frozen v0.7.4 universe and hashes:

- source SHA256 `bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`;
- final reference SHA256 `321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d`;
- sampling commitment `f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8`;
- exactly `11` anchored reference-positive candidate cases;
- fixed `96`-bar chart windows;
- frozen v0.7.1 F3 definition;
- frozen v0.7.3 C1 certificate;
- frozen v0.7.4 lifecycle semantics and event clock.

Required upstream replication before publication adjudication:

- static F3 support exactly `8/11`;
- lifecycle-live support exactly `8/11`;
- C1-certified support exactly `7/11`;
- hard lifecycle invariant violations exactly `0`;
- observed lifecycle objects exactly `1543`;
- certified lifecycle objects exactly `1478`;
- objects with dormant transitions exactly `0`;
- objects with reobserved transitions exactly `0`.

Any drift fails closed.

Human anchors may be used only after label-free lifecycle/publication construction to test semantic continuity. No notes/confidence, returns/PnL, qualification outputs, direction outputs, fitted waiting period, fitted predecessor rule, fitted raw-window geometry, or lifecycle timeout may be used.

## 4. Frozen lifecycle object identity

The object identity is exactly the v0.7.4 stable lifecycle object derived from the ordered five ridge IDs.

Publication may add a stable publication ID and stable raw-pivot IDs, but may not create a new semantic parent identity. All later status/evidence records reference the same lifecycle object ID.

## 5. Prefix-causal projection evidence clock

Replay exactly the v0.7.4 lifecycle event bars.

At each event bar `t`:

1. construct the frozen static F3 realization store using only prefix-confirmed ridge evidence;
2. update the frozen v0.7.4 lifecycle state;
3. for every lifecycle object that is currently live, enumerate current F3 realizations deterministically;
4. derive a prefix-causal same-level predecessor for each realization;
5. emit a projection-evidence candidate only when either:
   - the realization first appears at this prefix; or
   - its prefix-causal predecessor identity changes from the last evaluated evidence for that realization.

A realization evidence identity is `(level, selected node-ID tuple)`; predecessor change is tracked separately.

Evidence ordering at one event bar is lexicographic by:

1. event bar;
2. realization level;
3. selected occurrence-bar tuple;
4. selected node-ID tuple;
5. predecessor ridge ID, with `None` sorting before strings.

This ordering is fixed before results.

## 6. Frozen prefix-causal predecessor adapter

v0.7.2 selected the immediate predecessor from the full-sample scale row and only afterward checked whether it was confirmed by the event. That implementation can allow a future-unconfirmed intermediate ridge to block a predecessor that was actually known at the publication prefix.

v0.7.5 freezes the causal correction before statistics:

For a current F3 realization at level `L` and evidence bar `t`:

1. take all ridge nodes at level `L` with `confirmation_index <= t`;
2. sort by `(occurrence_index, confirmation_index, node_id)`;
3. locate the five selected ridge IDs in that prefix-confirmed row;
4. require them to be present and ordered;
5. choose as predecessor the nearest prefix-confirmed ridge immediately before selected ordinal 0 in that ordered prefix row;
6. if none exists, projection is invalid with `ordinal0_left_censored_no_predecessor`;
7. require predecessor kind to be opposite selected ordinal-0 kind.

The predecessor is not restricted to the 96-bar chart window; this preserves the historical predecessor provenance principle. It must, however, be causally confirmed by `t`.

No future-unconfirmed ridge may affect predecessor selection.

## 7. Frozen sequential raw-projection geometry

Given a valid prefix predecessor and selected F3 nodes, preserve the v0.7.2 transplant of the historical v0.6.4 sequential principle:

- let selected occurrence bars be `s0 < s1 < s2 < s3 < s4`;
- let `member_confirmation` be the selected ordinal-4 node confirmation bar;
- first lower bound = predecessor occurrence bar + 1;
- ordinal upper bounds = `s1-1, s2-1, s3-1, s4-1, member_confirmation`;
- for each ordinal, search from the previous selected raw bar + 1 through its upper bound;
- choose the **last** occurrence of the required high/low extreme in that window;
- require strictly increasing raw bars;
- require each adjacent raw price move to be an actual alternating turn in the required direction.

All projection windows and selected raw bars must be `<= evidence bar t`. No raw bar or price after `t` may be used.

The raw geometry, last-extreme tie break, actual-turn rule, and five-point count are frozen. v0.7.5 may not tune them.

## 8. Stable publication and pivot identity

For a valid projection evidence candidate, define raw identity as:

`raw_identity = (phase, raw_occurrence_bar_0..4)`.

A stable publication ID is derived from lifecycle object ID + raw identity + v0.7.5 schema. It does **not** include later certification time.

Each stable raw-pivot ID is derived from lifecycle object ID, ordinal, kind, raw occurrence bar, and raw price. It does **not** include later lifecycle status.

Thus certification/status changes cannot silently create a new raw identity.

## 9. First-valid immutable publication

For each lifecycle object:

1. object first observation remains the frozen v0.7.4 event;
2. process projection-evidence candidates in the frozen causal order;
3. invalid evidence before publication increments `prior_invalid_projection_count` and records only aggregate reason counts;
4. the first valid projection emits exactly one immutable publication;
5. publication records:
   - lifecycle object ID and object key;
   - first-observation bar;
   - publishing evidence bar;
   - publishing realization level;
   - prefix predecessor ID;
   - phase and raw identity;
   - lifecycle status at publication (`observed_live_unresolved` or `certified`);
6. later invalid evidence cannot revoke publication;
7. later valid evidence with the same raw identity is `later_valid_same_identity`;
8. later valid evidence with a different raw identity is `later_valid_would_rewrite_suppressed` and may not modify publication;
9. later C1 certification appends lifecycle status/evidence only and may not alter publication ID, raw identity, pivot IDs, predecessor provenance, first-observation bar, or publishing bar.

If an object is dormant in a future universe, no new projection evidence is evaluated while dormant; reobservation may resume evidence evaluation. In the frozen v0.7.4 11-case universe, dormancy/reobservation must replicate zero.

## 10. Publication status and certification append audit

For each published object, classify status at publication:

- `published_while_unresolved` if publication bar < certification bar or object never certifies by cutoff;
- `published_when_certified` otherwise.

For publications made while unresolved that later certify, verify a pure status append:

- raw identity unchanged;
- publication ID unchanged;
- pivot IDs unchanged;
- no republishing event.

Report counts of:

- unresolved publications that later certify;
- unresolved publications still unresolved at cutoff;
- already-certified publications;
- any status-append identity violation.

## 11. Hard causal / immutable-publication invariants

The formal run requires zero violations of all of the following:

1. all v0.7.4 hard lifecycle invariants;
2. publication never precedes first observation;
3. projection evidence is evaluated only while the object is live;
4. predecessor is prefix-confirmed and selected without future-unconfirmed blockers;
5. all five selected F3 nodes are prefix-confirmed by evidence bar;
6. all raw windows and raw bars are at or before evidence bar;
7. at most one publication per lifecycle object;
8. publication object ID equals lifecycle object ID;
9. stable publication/pivot IDs are deterministic under replay;
10. later valid differing raw identities are suppressed rather than rewritten;
11. certification/status append never changes an existing publication/raw/pivot identity;
12. no publication is backdated using later C1 certification;
13. repeated full replay produces identical aggregate publication identity hashes and counts.

Any violation fails the stage regardless of semantic support.

## 12. Frozen publication-coverage continuity gates

The v0.7.2 certified-event adapter published all `1478` certified F3 objects. v0.7.5 must not lose that established capability.

Therefore:

- all `1478` lifecycle objects that are C1-certified by their frozen cutoff must have an immutable publication by cutoff;
- certified-object publication coverage must equal `1478/1478`.

Publication coverage of the additional `65` unresolved lifecycle objects is reported descriptively and is not fitted into a threshold.

## 13. Frozen semantic-preservation tests

After label-free lifecycle/publication construction, score the frozen human support cells.

Report:

- published-raw semantic support cases;
- per-ordinal published-raw cell-hit cases;
- semantic support split by status at publication;
- semantic support among final certified objects;
- semantic support among final unresolved objects.

Historical v0.7.2 raw-publication continuity requirements are frozen as **no degradation**:

- published-raw semantic support must be at least `9/11`;
- ordinal 0 hit cases at least `11/11`;
- ordinal 1 hit cases at least `11/11`;
- ordinal 2 hit cases at least `11/11`;
- ordinal 3 hit cases at least `11/11`;
- ordinal 4 hit cases at least `10/11`.

Because v0.7.4 specifically preserved one static-supported/C1-unsupported semantic case as live unresolved, v0.7.5 additionally requires:

- among that single gap case's **human-compatible final live-unresolved F3 object(s)**, at least one same-object provisional publication must itself satisfy the frozen five raw support cells.

This is a semantic-continuity requirement for the already localized gap, not a fitted parameter or permission to select a different object.

Do not emit the gap case ID, timestamps, human anchors, or case-level publication table.

## 14. Descriptive mechanics — not fitted gates

Report aggregate counts/distributions for:

- all observed lifecycle objects;
- all published lifecycle objects;
- unresolved lifecycle objects published by cutoff;
- unresolved lifecycle objects never published by cutoff;
- certified objects published by cutoff;
- publication delay from first observation;
- prior-invalid projection count and reason counts;
- later-valid same-identity count;
- later-valid would-be-rewrite-suppressed count;
- prefix-predecessor-change evidence count;
- publications while unresolved that later certify;
- publications still unresolved at cutoff;
- publication evidence count per object;
- stable aggregate publication identity SHA256.

Do not fit a waiting period, invalid-evidence tolerance, rewrite tolerance, publication coverage threshold for unresolved objects, or predecessor rule from these diagnostics.

## 15. Frozen verdict precedence

After upstream replication:

1. if any lifecycle or publication hard invariant fails:
   `v0705_provisional_publication_append_only_or_causal_invariant_failed`;
2. else if certified publication coverage is not `1478/1478`:
   `v0705_certified_publication_coverage_regressed`;
3. else if published-raw semantic support is `<9/11` or any ordinal falls below the frozen v0.7.2 baseline:
   `v0705_provisional_lifecycle_raw_projection_semantic_support_insufficient`;
4. else if the single frozen live-unresolved semantic gap lacks same-object provisional raw support:
   `v0705_live_unresolved_gap_not_transplantable_to_raw_publication`;
5. else:
   `v0705_f3_provisional_lifecycle_publication_transplant_supported`.

A supported verdict does not grant active morphology authority.

## 16. Governance and next authorized stage

If v0.7.5 is supported, the next authorized stage is a separately frozen **lifecycle-publication qualification interface and semantic transplant precheck**:

- feed immutable published raw identities, with lifecycle status preserved, into the historical v0.5.4/v0.6.18 qualification interfaces;
- first eliminate interface exceptions without retuning semantic thresholds;
- then test frozen semantic correspondence under lifecycle status strata;
- only after qualification transplantation is adjudicated may D1/v0.6.25 direction be retested.

If v0.7.5 fails, raw projection/publication must be reconstructed; qualification and direction remain blocked.

Whatever the outcome:

- F3 lifecycle remains Development evidence only;
- no future certification may backdate observation or publication;
- no raw identity rewrite is authorized;
- `morphology_acceptance=false`;
- `trade_authority=false`;
- `production_authority=false`.
