# v0.6.5 Preanalysis — scale-invariant predecessor/raw identity publication

Date: 2026-09-06

Status: **WRITTEN BEFORE ANY v0.6.5 FINANCIAL REPLAY OUTPUT IS READ**

## 1. Why this experiment exists

v0.6.4 established two facts at the same time:

1. replacing ordinal0 mirror support with a real predecessor improves cross-slicing raw identity on all four harmless native-5m offsets;
2. using the predecessor from each tuple-birth member's own birth scale makes raw identity depend on scale evidence.

The second fact is a definition-level failure even though it was rare: every native-5m view contained one canonical filtered tuple whose two birth-scale evidence members produced two different ordinal0 raw anchors.

This violates the already-adopted v0.6.0 principle that scale is evidence about one financial identity, not part of the identity key.

v0.6.5 therefore does **not** invent another geometric support formula. It asks whether the v0.6.0 append-only publication principle can be lifted one layer upward, from qualified raw identity to filtered-parent → raw projection identity.

## 2. Research question

For one canonical filtered identity

`(start_phase, five filtered occurrence bars)`,

can raw financial identity be made scale-evidence invariant by publishing it exactly once from the **first causal evidence that yields a valid v0.6.4 predecessor-supported projection**, while all later same-anchor scale evidence is append-only and forbidden to rewrite the published raw anchors?

The experiment is structural only. It does not test direction, returns, third-wave behavior, P&L, OOS, or trading.

## 3. One registered candidate only

Candidate name:

`first_valid_causal_predecessor_projection_publication`

No second predecessor rule is registered.

Within each canonical filtered tuple group:

1. order tuple-birth evidence by `(birth_confirmation_bar, birth_level, event_id)`;
2. run the frozen v0.6.4 predecessor-supported projection on evidence in that causal order;
3. invalid evidence is retained as an append-only failure evidence event;
4. the first evidence whose v0.6.4 projection is valid publishes the immutable raw identity;
5. later same-anchor evidence may be audited counterfactually, but cannot replace, re-project, or alter the already published raw identity.

If no evidence ever yields a valid projection, the group has `no_valid_published_projection`.

This is not a best-member selector. No cross-view information, direction label, qualification result, return, or outcome enters publication.

## 4. Why “first valid” rather than literally first birth

A tuple birth can exist while the registered predecessor-supported raw projection is mechanically invalid (for example an actual-turn failure or explicit left censor). Publishing an invalid raw identity would be undefined.

The analogy to v0.6.0 is therefore deliberate:

- earlier evidence may exist but fail the publication gate;
- **first evidence satisfying the already frozen publication gate** publishes identity;
- later evidence only appends evidence.

The gate itself is not changed after seeing v0.6.5 output: it is exactly v0.6.4 candidate validity.

## 5. Frozen components

v0.6.5 changes none of:

- TCSS scale lattice;
- extremum ridge linking;
- tuple-birth/death certification;
- canonical filtered identity key;
- v0.6.4 predecessor definition for one evidence member;
- ordinal0 upper support;
- ordinal1..4 sequential windows;
- exact max/min and last-exact-tie rule;
- v0.5.4 qualification thresholds;
- v0.6.0 cross-view matcher (`<=5m`, mutual-unique only);
- packing;
- D1/D2/PAWCT;
- outcomes/trading.

## 6. Required semantic invariants

Before any financial replay, tests must establish:

1. **single publication** — one canonical filtered identity produces at most one raw identity event;
2. **prefix immutability** — appending later same-anchor evidence cannot rewrite the published event;
3. **invalid-before-valid semantics** — invalid early evidence remains recorded and a later first-valid evidence may publish;
4. **later-divergent evidence isolation** — a later evidence whose v0.6.4 counterfactual raw identity differs does not change the published identity;
5. **deterministic causal ordering** — equal confirmation uses birth level then event ID, never cross-view similarity;
6. **no future evidence dependence** — publication at evidence `k` is identical whether later evidence is absent or present;
7. **no hidden fallback** — if no evidence is valid, no raw identity is published.

## 7. Financial comparison universe

Cross-view pair formation must remain the exact v0.6.2 canonical filtered-tuple universe:

- same start phase;
- five filtered occurrence timestamps position-wise within `<=5m`;
- mutual-unique only;
- no best/nearest tie-break.

The publication candidate cannot affect which filtered pairs exist.

## 8. Pre-registered comparisons

Report v0.6.5 published projection against:

1. frozen current raw projection control;
2. v0.6.4 member-specific predecessor candidate;
3. all v0.6.2 mutual-unique filtered pairs;
4. v0.6.2 control raw-displaced pairs;
5. v0.6.3 1m residual pairs;
6. v0.6.1 projection-displacement target pairs;
7. v0.6.3 target residual subset.

The v0.6.4 multi-valued groups must be explicitly replayed and shown as either one immutable published identity or no publication.

## 9. Success/failure logic

No new post-hoc numeric cutoff is introduced.

A positive structural result requires all of:

- zero multi-valued **published** identities by construction and verified by prefix tests;
- all five historical v0.6.4 multi-valued groups close to one immutable identity or explicit no-publication;
- no cross-view information used in first-valid evidence selection;
- the same directional structural improvement over the frozen current control remains on all four harmless offsets;
- the v0.6.4 repair signal is not materially erased by no-publication/newly-broken effects.

Even a positive v0.6.5 result does **not** promote the recognizer. It would only justify a separate frozen downstream qualification audit of the newly well-defined raw identity.

## 10. Explicit non-goals

Do not in v0.6.5:

- alter predecessor geometry;
- choose the birth scale that matches another offset best;
- use 1m as runtime input;
- repair sequential-lower residuals;
- adjust `<=5m` matching tolerance;
- tune v0.5.4 qualification;
- reopen direction or trading.

Global morphology status remains `morphology_replication_not_yet_accepted`; operational baseline remains v0.4.3.
