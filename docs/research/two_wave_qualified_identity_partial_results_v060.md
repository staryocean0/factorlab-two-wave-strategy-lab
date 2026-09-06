# v0.6.0 Partial results — qualified financial identity vs exclusive packing

## Status

`partial_evidence_generated_route_Q_U_M_not_adjudicated`

This result uses only already-completed frozen artifacts plus local deterministic analysis. No new GitHub Actions run was started, no recognizer was re-run, no threshold or direction formula was changed, and no outcome/trading data was used.

The purpose is to preserve everything that can already be proven while refusing to invent the missing full qualified record bodies for native offsets 1..4.

## Sources

- v0.5.4 formal native-five-view run: `33998425000`
- v0.5.4 final artifact: `9978815239`, SHA256 `0ef8ac22b4b69befd39d1b5e516b3c95bd3f396976cdbc5a7f0b8352515998cf`
- v0.5.7b formal geometry run: `34010814782`, artifact `9982490147`
- v0.5.8 formal PAWCT run: `34011528190`, artifact `9982711773`
- main-view full qualified diagnostics: frozen v0.5.5/v0.5.6 outputs already archived from the same v0.5.4 qualified pool
- local v0.6.0 helper unit tests: **8/8 PASS**

Reproducible local analyzer:

`scripts/analyze_two_wave_qualified_identity_partial_v060.py`

## 1. Packing suppression is a five-view structural phenomenon

The frozen v0.5.4 formal artifact reports:

| view | qualified | legacy selected | suppressed | suppressed fraction |
|---|---:|---:|---:|---:|
| 5m_offset_0 | 734 | 404 | 330 | 44.96% |
| 5m_offset_1 | 691 | 371 | 320 | 46.31% |
| 5m_offset_2 | 691 | 382 | 309 | 44.72% |
| 5m_offset_3 | 721 | 392 | 329 | 45.63% |
| 5m_offset_4 | 746 | 392 | 354 | 47.45% |

Mean suppression fraction = **45.81%**; range = **44.72%–47.45%**.

Therefore the main-view finding that exclusive packing hides roughly half of the qualified two-wave observations is not an offset0 anomaly.

This is not a performance argument. It is a semantic-layer finding: a non-overlap packing rule is materially transforming the set of already-qualified morphology observations in every supplied native 5m view.

## 2. Frozen upstream causality remains intact

The same v0.5.4 formal artifact contains native-five-view full + 25/50/75% checks:

- five views × three prefixes = **15/15 PASS**
- `confirmed_rewrite_count = 0` throughout
- `v054_evaluated_records = true` throughout

So the qualified/evaluated upstream record stream remains the frozen causal input to v0.6.0. v0.6.0 does not reopen v0.5.2 ridge identity or v0.5.4 qualification.

The new identity helper separately proves append-only semantics in unit tests: a first qualified same-anchor member publishes an immutable identity event; later same-anchor scale evidence cannot rewrite it.

A new 15-prefix v0.6.0 record-body replay is still kept as a protocol requirement when the full four offset qualified bodies become available locally. The historical v0.5.4 boolean checks are not mislabeled as that new replay.

## 3. Main-view canonicalization is reproduced by the new implementation

The new `canonicalize_qualified_records` helper was executed directly on the formal main-view 734 qualified diagnostic records, not on a hand-written grouping summary.

Result:

- qualified records: **734**
- canonical financial identities `(phase,e0..e4)`: **712**
- duplicate same-anchor scale-evidence groups: **21**
- records in those groups: **43**
- maximum scale-evidence members in one identity: **3**
- canonical identities with any legacy-selected member: **404**
- canonical identities entirely hidden by legacy packing: **308**
- hidden fraction among canonical identities: **43.2584%**

The helper hard-fails if an exact same-anchor identity has conflicting D1 or phase-step geometry. No such conflict was triggered in the real 734-record pool.

Thus the earlier main-view result is now reproduced through the actual v0.6.0 implementation.

## 4. Selected-only strict same-event diagnostic remains strong in every offset

This section is **diagnostic only** because it still begins from legacy selected records.

For each offset0-vs-offsetN selected ownership pair, define the frozen audit-only local relation:

- same start phase;
- all five ordered raw-extremum occurrence-time deltas `<=5 minutes`.

No direction label participates in this relation.

| other view | all ownership pairs / bars | strict local pairs / bars | strict-bar share | D1 same label | D2 same label | PAWCT large-margin flip |
|---|---:|---:|---:|---:|---:|---:|
| offset1 | 295 / 45,651 | 72 / 14,781 | 32.38% | 95.35% | 91.23% | 0% |
| offset2 | 271 / 40,475 | 54 / 11,098 | 27.42% | 96.22% | 93.50% | 0% |
| offset3 | 282 / 40,743 | 55 / 11,420 | 28.03% | 95.23% | 92.24% | 0% |
| offset4 | 285 / 44,911 | 81 / 17,423 | 38.79% | 98.34% | 97.20% | 0% |

Combined:

- strict local selected pairs: **262**
- weighted bars: **54,722**
- D1 same-label: **96.4493%**
- D2 same-label: **93.8014%**
- direct D1 uptrend↔downtrend reversal: **0**
- direct D2 uptrend↔downtrend reversal: **0**
- PAWCT large-margin sign-flip bars: **0**

Again, these numbers do not accept D1, D2 or PAWCT. They only reinforce the v0.5.9 conclusion that large direction disagreement is associated with comparing different selected financial identities.

## 5. What is still missing

The formal v0.5.4 per-view artifacts deliberately serialized only:

- full counts / prefix booleans;
- legacy selected coverage.

They did **not** serialize the full 691–746 qualified record bodies for offsets 1..4.

Therefore the following frozen v0.6.0 gates cannot yet be computed without either the parquet data or an equivalent complete qualified-record export:

1. canonical qualified identity bodies in offset1..4;
2. mutual-unique strict cross-view matches over **all qualified canonical identities**;
3. ambiguity / unmatched decomposition for that pool;
4. exact count of stable strict matches hidden by packing;
5. a concrete v0.6.0 derived identity-event prefix replay on those four full streams.

The protocol route **Q / U / M is intentionally not adjudicated**.

## Research conclusion

What can now be stated with five-view evidence is:

> **Exclusive non-overlap packing is a material morphology-layer contaminant in every native 5m view, suppressing about 45% of already-qualified observations. It must remain downstream of financial morphology identity.**

What cannot yet be stated is whether the full qualified pool itself has sufficiently stable same-event identity across harmless native slicing. That is the exact unresolved v0.6.0 question.

Therefore:

- do not return to another direction formula yet;
- do not promote PAWCT;
- do not revive endpoint D2;
- do not reopen v0.5.2/v0.5.4;
- keep exclusive packing downstream;
- obtain full qualified record bodies locally, then execute the frozen v0.6.0 mutual-unique audit;
- operational baseline remains v0.4.3;
- global status remains `morphology_replication_not_yet_accepted`.
