# v0.6.5 Frozen protocol — scale-invariant predecessor/raw identity publication

Date: 2026-09-06

Status: **FROZEN BEFORE ANY v0.6.5 FINANCIAL OUTPUT IS READ**

This protocol registers exactly one candidate from the v0.6.5 preanalysis. It changes no upstream morphology recognizer, ridge, tuple-birth, qualification, matcher, direction, packing, outcome, or trading logic.

## 1. Candidate

Candidate name:

`first_valid_causal_predecessor_projection_publication`

Canonical filtered identity remains:

`(start_phase, five filtered occurrence bars)`.

All tuple-birth evidence for that identity is ordered by:

`(birth_confirmation_bar, birth_level, event_id)`.

For each evidence member in order, compute the already frozen v0.6.4 member-specific candidate:

`birth_scale_predecessor_filtered_phase_start`.

- Invalid member projection -> append a failure evidence record only.
- First valid member projection -> publish exactly one immutable raw identity event.
- Any later same-anchor member -> append evidence only; it cannot rewrite the published raw five anchors.
- If no member is valid -> `no_valid_published_projection`.

No cross-view information is permitted in evidence ordering or publication.

## 2. Publication event schema

For a published group retain at least:

- canonical filtered identity key;
- phase and five filtered occurrence bars/times;
- `publication_event_id`;
- `publishing_member_event_id`;
- publishing birth level;
- publishing birth confirmation bar;
- predecessor occurrence / confirmation bar;
- published raw five occurrence bars/times;
- publication confirmation time;
- count of prior invalid evidence members;
- append-only later evidence count;
- `future_outcome_used=false`;
- `trade_authority=false`.

A later evidence record may include its counterfactual v0.6.4 raw identity for audit, but that value is diagnostic only and cannot mutate the publication event.

## 3. Single-view statuses

Each canonical filtered group receives exactly one status:

- `published_single_identity`;
- `no_valid_published_projection`.

There is no `multi_valued_published_identity` status allowed by the candidate semantics. Tests must nevertheless assert that publication history never contains more than one identity event per canonical key.

Report separately:

- total evidence members;
- invalid-before-publication count;
- later evidence count;
- later evidence whose counterfactual v0.6.4 raw identity differs from published identity (`suppressed_would_be_rewrite`);
- groups corresponding to the five v0.6.4 multi-valued examples.

## 4. Frozen cross-view universe

Pair universe is unchanged from v0.6.2/v0.6.4:

- canonical filtered-tuple groups;
- same phase;
- five filtered occurrence timestamps all position-wise `<=5m`;
- mutual-unique only;
- no nearest/best tie-break.

Hard-control pair counts:

```text
offset1: 14,784
offset2: 12,725
offset3: 13,412
offset4: 16,108
aggregate: 57,029
```

Any drift stops interpretation.

## 5. Frozen control counts

Before interpreting v0.6.5 reproduce:

```text
current-control raw strict:     7,638 / 5,188 / 5,593 / 8,332
current-control raw displaced:  6,975 / 7,311 / 7,534 / 7,453

v0.6.3 residual:                1,578 / 1,738 / 1,806 / 1,718
v0.6.1 projection target:         191 /   194 /   193 /   209
v0.6.3 target residual:             32 /    28 /    30 /    32

v0.6.4 candidate strict:        8,381 / 5,770 / 6,204 / 9,098
v0.6.4 per-view multi-valued groups: 1 / 1 / 1 / 1 / 1
```

Aggregate v0.6.4 controls:

```text
candidate strict = 29,453
candidate displaced = 26,857
candidate invalid = 714
candidate multi pairs = 5
control-displaced repaired = 3,986
control-strict newly broken = 1,399
v0.6.3 residual repaired = 2,390
v0.6.1 projection target repaired = 80
v0.6.3 target residual repaired = 50
```

## 6. v0.6.5 cross-view status

For every frozen filtered pair:

1. if either side has no valid published projection -> `published_projection_missing_pair`;
2. else compare the two immutable published raw identities with unchanged same-phase five-anchor `<=5m` relation:
   - `published_raw_strict_match`;
   - `published_raw_displaced`.

No other projection member can be selected for pair evaluation.

## 7. Required transition accounting

Relative to current control, report:

- repaired: control displaced -> v0.6.5 published strict;
- unchanged displaced;
- newly missing publication;
- newly broken: control strict -> v0.6.5 published displaced;
- retained strict.

Relative to v0.6.4, report:

- v0.6.4 multi-valued pair -> v0.6.5 strict/displaced/missing;
- v0.6.4 strict -> v0.6.5 strict/displaced/missing;
- v0.6.4 displaced -> v0.6.5 strict/displaced/missing;
- aggregate strict-count delta versus v0.6.4.

Repeat current-control transition accounting on:

- v0.6.3 residual stratum;
- v0.6.1 projection-displacement target stratum;
- v0.6.3 target residual subset.

## 8. Historical multi-valued closure gate

The exact five canonical filtered groups reported by v0.6.4 must be checked explicitly.

For each report:

- ordered member event IDs / birth levels / confirmation bars;
- first invalid evidence if any;
- publishing member;
- immutable published raw identity;
- later counterfactual raw identities;
- whether a would-be rewrite was suppressed.

Acceptance of the audit requires that no later member changes the publication event.

## 9. Synthetic gates

Tests must cover at least:

1. first member valid -> immediate publication;
2. first invalid, second valid -> second publishes;
3. first two invalid, no later valid -> no publication;
4. later valid same raw identity -> evidence append only;
5. later valid different raw identity -> `suppressed_would_be_rewrite`, publication unchanged;
6. equal confirmation tie resolves by birth level, then event ID;
7. prefix run through publishing evidence equals full-run publication event;
8. future evidence append cannot change publication identity;
9. cross-view similarity is absent from API and ordering.

## 10. Required outputs

Write compact outputs to:

`cloud_results/cloud_chat_v065_scale_invariant_predecessor_publication/`

Required:

```text
summary.json
per_view_publication.json
historical_multivalued_closure.json
pair_offset_1.json
pair_offset_2.json
pair_offset_3.json
pair_offset_4.json
v061_target_publication.json
v063_residual_publication.json
data_identity.json
execution_receipt.json
```

Do not upload parquet or runtime caches.

## 11. Interpretation rule

No post-hoc percentage threshold is introduced.

A positive structural adjudication requires:

- zero published-identity rewrites in synthetic and financial replay;
- all five v0.6.4 multi-valued examples close to one immutable identity or explicit no-publication;
- all four harmless offsets retain the same directional improvement over the frozen current control;
- no publication-missing or newly-broken effect large enough to erase the v0.6.4 repair signal;
- evidence selection remains strictly causal and single-view.

A positive result only authorizes a **separate frozen downstream qualification audit**. It does not replace production projection in this experiment.

A negative result ends this candidate. Do not add a second evidence-selection rule after seeing output.

Global state remains `morphology_replication_not_yet_accepted`; operational baseline remains v0.4.3.
