# v0.6.6 Frozen protocol — published raw identity qualification stability

Date: 2026-09-06

Status: **FROZEN BEFORE ANY v0.6.6 QUALIFICATION OUTPUT IS READ**

This is a downstream audit of v0.6.5 published raw identities using unchanged v0.5.4 qualification. It changes no projection, predecessor, publication ordering, matcher, threshold, direction, packing, outcome, or trading logic.

## 1. Frozen publication controls

Before qualification interpretation reproduce v0.6.5:

```text
published raw strict pairs: 8,381 / 5,770 / 6,204 / 9,098
aggregate published raw strict = 29,453

current-control raw strict = 26,751
v0.6.5 strict delta vs control = +2,702

v0.6.3 repaired residual = 2,390
v0.6.1 repaired projection target = 80
v0.6.3 repaired target residual = 50
```

Five historical v0.6.4 multi-valued groups must remain single immutable v0.6.5 publications. Any publication drift stops interpretation.

## 2. Published identity → qualification input

For every v0.6.5 published identity:

1. use its five raw occurrence bars in order;
2. expected kinds alternate from published phase;
3. point price is the supplied view's raw close at that occurrence;
4. every point uses the v0.6.5 publishing birth confirmation as the qualification confirmation clock;
5. no later scale evidence or future bar may alter the points or confirmation clock.

## 3. Frozen qualification function

Apply the frozen v0.4.3 `evaluate_pair` qualification inputs and metrics.

Then implement v0.5.4 exactly:

```text
hard_reasons = v043_scale_rejection_reasons - {corresponding_leg_duration_mismatch}
scale_qualified = (hard_reasons is empty)
```

`corresponding_leg_duration_mismatch` remains reported as diagnostic-only.

No other rejection reason or numerical threshold changes.

## 4. Direction firewall

`evaluate_pair` mechanically emits direction diagnostics. v0.6.6 must ignore them except where required internally by legacy record construction.

Forbidden outputs/interpretation:

- D1 agreement;
- trend/range counts as research evidence;
- any direction-conditioned qualification result;
- returns/outcomes/P&L.

## 5. Per-view published qualification output

For each view report:

- published identities;
- qualified / rejected;
- qualification fraction;
- hard rejection reason counts;
- diagnostic-only corresponding-leg mismatch count;
- confirmation-delay distribution.

No count is a success target.

## 6. Primary pair universe

Use only the already frozen v0.6.5 published raw strict pairs. Do not form pairs using qualification.

Expected counts:

```text
offset1: 8,381
offset2: 5,770
offset3: 6,204
offset4: 9,098
aggregate: 29,453
```

For each pair classify exactly one:

- `both_qualified`;
- `both_rejected`;
- `main_qualified_other_rejected`;
- `main_rejected_other_qualified`.

## 7. Qualification disagreement diagnostics

For every disagreement pair retain:

- rejected-side hard reasons;
- qualified-side original v0.4.3 reasons including diagnostic-only corresponding-leg mismatch;
- symmetric reason-set difference;
- leg durations;
- cycle durations;
- amplitude ratio;
- per-leg efficiencies;
- per-leg jump shares;
- per-leg flat shares;
- observed trading days;
- wall days;
- confirmation delay.

Summaries may aggregate reason frequencies and metric distributions. No threshold fitting.

## 8. Pre-registered repaired strata

Using upstream pair transition labels fixed before qualification, separately report:

1. all current-control displaced → v0.6.5 strict repaired pairs: `3,986`;
2. v0.6.3 residual repaired pairs: `2,390`;
3. v0.6.1 projection targets repaired: `80`;
4. v0.6.3 target residual repaired: `50`.

Any count drift stops stratum interpretation.

## 9. Causality tests

Synthetic tests must cover:

- five alternating raw anchors produce deterministic frozen qualification metrics;
- append future bars after qualification confirmation -> identical qualification output;
- later divergent v0.6.4 evidence cannot change v0.6.5 published anchors, therefore cannot change v0.6.6 qualification input;
- corresponding-leg mismatch alone does not reject after v0.5.4 demotion;
- every other frozen reason remains hard.

## 10. Required compact outputs

Write to:

`cloud_results/cloud_chat_v066_published_identity_qualification/`

Required:

```text
summary.json
per_view_qualification.json
pair_offset_1.json
pair_offset_2.json
pair_offset_3.json
pair_offset_4.json
repaired_strata_qualification.json
data_identity.json
execution_receipt.json
```

Large disagreement detail rows may stay runtime-local or be stored as deterministic compact samples without outcome selection.

## 11. Interpretation rule

No post-hoc numerical cutoff.

Cloud may conclude only:

- `qualification_broadly_stable_on_strict_identity_pairs`, or
- `qualification_is_material_independent_instability`, or
- `mixed_qualification_stability_requires_decomposition`.

Even the first conclusion does not accept morphology globally and does not automatically reopen D1/D2/PAWCT because unmatched upstream filtered identity remains unresolved.

Global state remains `morphology_replication_not_yet_accepted`; operational baseline remains v0.4.3.
