# Two-Wave v0.7.4 — F3 Prefix-Causal Lifecycle Object Reconstruction

Status: **frozen before any v0.7.4 lifecycle statistics are read**.

## 1. Starting authority

v0.7.1 selected F3, the persistence-dominant nonconsecutive ridge quintet, as the Development semantic-parent reconstruction candidate with `8/11` anchored human-positive support.

v0.7.2 showed that requiring a permanently certified event at first publication preserves only `7/11` cases.

v0.7.3 then ruled out the narrow exact-coarse-boundary explanation. Its preregistered C1 certificate still preserved `7/11`; in the single static-supported / causal-unsupported case, all four human-compatible static F3 realizations lacked explicit skipped-ridge death evidence at the frozen cutoff, and that evidence arrived only later.

Formal v0.7.3 result commit: `68c978187b531ad6ac18c564a3214035be0dafa5`.

The next authorized problem is therefore not to weaken permanence. It is to test whether the same frozen F3 identity can be represented as a prefix-causal, append-only **lifecycle object** whose first observation does not falsely claim permanent skipped-ridge death.

## 2. Scientific question

Can F3 be represented causally as an immutable object/event stream with:

1. a first `observed` event when the frozen static F3 rule is first satisfied from information known at that prefix;
2. later append-only lifecycle transitions when causal evidence changes;
3. a terminal `certified` transition only when the frozen v0.7.3 C1 permanence certificate is actually available;
4. no retroactive change to object identity, first-observation time, or prior event payloads;
5. the same final-cutoff live semantic support as frozen F3 (`8/11`), without using historical-but-dormant observations as current morphology support?

This stage tests **event/lifecycle representability**, not morphology acceptance, qualification, direction, returns, or trading.

## 3. Frozen universe and inputs

Use exactly the frozen v0.7.3 universe and hashes:

- source SHA256 `bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`;
- final reference SHA256 `321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d`;
- sampling commitment `f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8`;
- exactly `11` anchored reference-positive candidate cases;
- fixed `96`-bar chart windows;
- frozen v0.7.1 F3 definition;
- frozen v0.7.3 C1 certificate definition.

Required final-cutoff replication before lifecycle adjudication:

- static F3 support = exactly `8/11`;
- C1-certified support = exactly `7/11`.

Any drift fails closed.

Human anchors may be used only after lifecycle construction to test semantic continuity. They may not determine object creation, first-observation time, transition time, realization choice, or lifecycle state.

No annotator notes/confidence, returns, PnL, qualification outputs, direction outputs, fitted bar tolerance, lifecycle timeout, persistence threshold, or skip-count threshold may be used.

## 4. Frozen object identity

An F3 object identity is exactly the ordered tuple of five frozen ridge IDs:

`object_key = (ridge_id_0, ridge_id_1, ridge_id_2, ridge_id_3, ridge_id_4)`.

The object identity is independent of scale realization. Later realizations of the same ordered ridge-ID quintet are evidence about the same object, never a new identity and never a rewrite of the original object.

A stable object ID must be deterministically derived from `object_key` and the v0.7.4 schema only.

## 5. Prefix event clock

Within each fixed 96-bar case window, lifecycle replay uses only bars at which the causal state can change:

- confirmation bars of ridge-node representations whose occurrence lies inside the fixed chart window;
- confirmation bars of RidgeDeath records relevant to ridge IDs inside the window;
- the final frozen case cutoff.

Sort unique event bars ascending and discard bars after the case cutoff.

At each event bar `t`, construct the frozen F3 static set using only ridge-node representations with confirmation `<= t` and the frozen v0.7.1 causal-survival rule. No full-sample final survival level may substitute for prefix evidence.

The fixed left chart boundary does not move during replay. Nodes are not dropped merely because time advances within the case replay.

## 6. Frozen lifecycle event semantics

For every object key, maintain an append-only event ledger.

### 6.1 `observed`

When an object key is present in the frozen static F3 set for the first time at event bar `t`, emit exactly one `observed` event.

The event records:

- stable object ID;
- object key;
- first-observation confirmation bar `t`;
- one deterministic first-observation witness realization;
- witness level and selected node IDs/occurrence bars;
- evidence ordering key.

If multiple realizations exist at first observation, choose the witness deterministically by the lexicographic key:

1. maximum selected-node confirmation bar;
2. realization level;
3. selected occurrence-bar tuple;
4. selected node-ID tuple.

This witness is historical evidence only. Later evidence may not replace it.

### 6.2 `dormant`

If an un-certified observed object was live at the previous event bar but is absent from the current frozen static F3 set, append a `dormant` transition at the current event bar.

`dormant` is not permanent invalidation. It records only that the frozen F3 snapshot rule no longer supports the object at that prefix.

### 6.3 `reobserved`

If an un-certified dormant object re-enters the frozen static F3 set, append a `reobserved` transition. The original object ID and first-observation event remain unchanged.

### 6.4 `certified`

For an observed object that is currently present in the frozen static F3 set, append a terminal `certified` transition at the first event bar where at least one current F3 realization of that same object key satisfies the frozen v0.7.3 C1 certificate using only evidence confirmed `<= t`.

Choose the certification witness deterministically by:

1. C1 event-proof confirmation bar;
2. realization level;
3. selected occurrence-bar tuple;
4. selected node-ID tuple.

After certification the object remains terminally certified. No later event may rewrite or revoke certification.

v0.7.4 does **not** invent a permanent `invalidated` event. A logically permanent invalidation rule would require a separately frozen proof and is outside this protocol.

## 7. Derived lifecycle state

At any event bar an object is exactly one of:

- `observed_live_unresolved` — observed, not certified, and present in current static F3 set;
- `observed_dormant_unresolved` — observed, not certified, and absent from current static F3 set;
- `certified` — C1-certified terminal state.

The current morphology-support view at a case cutoff consists only of objects that are either:

- currently `observed_live_unresolved`; or
- `certified` **and still present in the current frozen static F3 set**.

Historical dormant observations never count as current semantic support.

This final-cutoff live view must equal the frozen static F3 snapshot set by object key. Any set difference fails closed.

## 8. Hard append-only / causal invariants

The formal run must verify all of the following with zero violations:

1. one stable object ID per object key;
2. at most one `observed` event per object key;
3. event bars are nondecreasing within each object ledger;
4. no event precedes its required ridge-node/death evidence;
5. no future ridge lineage or future survival is used to create `observed`, `dormant`, `reobserved`, or `certified` events;
6. first-observation bar and witness are unchanged when replay is extended to later event bars;
7. certification bar is never earlier than first observation;
8. every certification witness satisfies frozen C1 at its transition prefix;
9. certified object identity is identical to observed object identity;
10. no certified object later receives `dormant` or `reobserved` transitions;
11. final lifecycle live object-key set equals final frozen static F3 object-key set in every anchored case;
12. final static F3 support reproduces exactly `8/11` and final C1-certified support exactly `7/11`.

If any hard invariant fails, lifecycle reconstruction fails regardless of semantic support.

## 9. Frozen semantic-continuity tests

After lifecycle construction, score the same frozen human support cells.

Report:

- final static F3 support cases;
- final lifecycle-live support cases;
- final certified support cases;
- final live-unresolved support cases;
- whether the previously localized one-case permanent-certificate gap is represented as live-unresolved rather than falsely certified;
- per-ordinal live semantic cell-hit cases.

Frozen continuity requirements:

- final lifecycle-live support = exactly `8/11`;
- final lifecycle-live object-key sets equal final static F3 sets case by case;
- final certified support = exactly `7/11`.

The lifecycle layer does not claim to improve the `8/11` static reconstruction. It only asks whether the eighth supported case can exist causally as unresolved rather than being discarded for lack of future permanence evidence.

## 10. Descriptive mechanics — not fitted gates

Report aggregate, non-case-identifying distributions/counts for:

- observed object count;
- certified object count;
- live-unresolved object count at cutoff;
- dormant unresolved object count at cutoff;
- objects with at least one dormant transition;
- objects with at least one reobserved transition;
- observation-to-certification delay bars;
- number of lifecycle transitions per object;
- suppressed attempted identity rewrites, which must be zero by construction/invariant;
- first-observation witness multiplicity at the observation bar.

These quantities are descriptive only. Do not derive a lifecycle timeout, churn threshold, or fitted acceptance rule from them.

Do not write case IDs, timestamps, human anchors, or case-level lifecycle tables into the formal result artifact.

## 11. Frozen verdict precedence

After required replication and invariant checks:

1. if any hard invariant fails:
   `v0704_f3_lifecycle_append_only_or_causal_invariant_failed`;
2. else if final lifecycle-live support or object-key equality fails to reproduce frozen static F3:
   `v0704_f3_lifecycle_does_not_preserve_static_semantics`;
3. else if final certified support differs from frozen C1 `7/11`:
   `v0704_f3_lifecycle_certification_lineage_drift`;
4. else:
   `v0704_f3_prefix_causal_lifecycle_representation_supported`.

A supported verdict means only that the F3 reconstruction can be represented as a causal append-only lifecycle object without pretending the unresolved eighth case was already permanent.

It does **not** grant active morphology authority.

## 12. Governance and next step

If v0.7.4 is supported, the next authorized stage is a separately frozen transplant test for **provisional lifecycle publication**:

- test whether v0.6.4 sequential raw projection and v0.6.5 first-valid immutable publication can attach to the `observed` event without identity rewrites;
- preserve lifecycle status in the published record;
- quantify what happens when an observed object becomes dormant before certification;
- do not activate qualification or direction until provisional publication semantics are adjudicated.

If v0.7.4 fails, the causal object/event layer must be reconstructed again; qualification and direction remain blocked.

Whatever the outcome:

- F3 static reconstruction remains Development evidence only;
- v0.6.4/v0.6.5 remain retained as positive transplant evidence, not active authority;
- v0.5.4/v0.6.18 and D1/v0.6.25 remain historical components awaiting later transplantation retests, not declared false;
- `morphology_acceptance=false`;
- `trade_authority=false`;
- `production_authority=false`.
