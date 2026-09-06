# v0.6.0 Results — qualified financial identity vs exclusive packing

## Verdict

**Cloud adjudication: Route M (mixed).**

The local CL-20260906-002 execution is accepted as valid evidence for the frozen v0.6.0 identity protocol, with one documented non-decisive packaging exception: `scripts/validate_theme_package.py` exited 1 because `AGENTS.md` changed after the frozen research commit to add the cloud-local handoff protocol. Independent GitHub commit comparison confirms that between frozen research commit `4643133f518299d6710f3c1cc01b6399b9482c31` and execution commit `a45a3a986df80228daa500af3c95e67c7f475ff5`, only `AGENTS.md` and `docs/ops/cloud_local_communication.md` changed. No `src`, `tests`, `scripts`, `docs/research`, `data`, or `pyproject.toml` research file drift occurred.

This is a **cloud review of the committed local replay evidence**, not an independent cloud recomputation of parquet inputs.

Global status remains:

`morphology_replication_not_yet_accepted`

Operational baseline remains `v0.4.3`. PR #1 remains Draft. Do not enter H1/H2, third-wave, returns/P&L, OOS, paper trading, or production.

## Frozen protocol identity

- Frozen upstream: v0.5.2 exact-ridge parent identity + v0.5.4 full-cycle qualification.
- New component only: morphology identity decoupled from exclusive packing.
- Canonical financial identity: `(start_phase, five raw occurrence bars)`.
- Cross-view strict edge: same phase and all five ordered occurrence timestamps differ by at most one nominal 5m bar.
- Same-event matches: mutual-unique only; ambiguity is never post-hoc tie-broken.
- D1/D2/PAWCT, interval IoU, amplitude, returns and outcomes do not participate in identity matching.

## Execution and data acceptance

Local task: `CL-20260906-002`.

- execution branch / commit: `codex/two-wave-phase1-20260905` / `a45a3a986df80228daa500af3c95e67c7f475ff5`
- frozen research commit: `4643133f518299d6710f3c1cc01b6399b9482c31`
- result commit: `2d41cba048d8c62d0aca19ac501764a03082941c`
- focused governance + v0.6.0 tests: **37 passed**, exit 0
- frozen local runner: exit 0
- no runner/matching/threshold/offset change
- no v0.6.1 change
- no local resampling
- no 2021+ rows
- fresh OOS: false
- trade authority: false

The five supplied native 5m views match the frozen manifest in SHA256, bytes, row count and date range:

| view | bars | qualified | canonical identities | legacy selected | duplicate-scale groups |
|---|---:|---:|---:|---:|---:|
| offset0 | 70,114 | 734 | 712 | 404 | 21 |
| offset1 | 67,192 | 691 | 673 | 371 | 17 |
| offset2 | 67,192 | 691 | 678 | 382 | 13 |
| offset3 | 67,193 | 721 | 700 | 392 | 21 |
| offset4 | 67,191 | 746 | 728 | 392 | 18 |

The decisive raw qualified checkpoints `734 / 691 / 691 / 721 / 746` reproduce exactly, and main canonical count reproduces `712`. Therefore there is no `IDENTITY_INPUT_DRIFT`.

## Causality / prefix gate

The v0.6.0 identity-event stream passed all frozen prefix checks:

- 5 views × 25% / 50% / 75% = **15 / 15 passed**
- confirmed rewrite count = **0** for every check
- `prefix_zero_rewrite_count = 15`

Thus later same-anchor scale evidence is append-only and does not rewrite previously published canonical financial identities in these frozen replays.

## Cross-view strict identity results

### Canonical qualified identities

| pair | matches | main match | other match | ambiguous main/other | unmatched main/other | hidden by legacy packing | hidden fraction | D1 same label* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| offset0 vs 1 | 180 | 25.28% | 26.75% | 1 / 1 | 531 / 492 | 109 | 60.56% | 96.67% |
| offset0 vs 2 | 129 | 18.12% | 19.03% | 0 / 0 | 583 / 549 | 75 | 58.14% | 96.90% |
| offset0 vs 3 | 129 | 18.12% | 18.43% | 1 / 0 | 582 / 571 | 74 | 57.36% | 96.12% |
| offset0 vs 4 | 184 | 25.84% | 25.27% | 1 / 1 | 527 / 543 | 104 | 56.52% | 95.11% |

\* D1 is diagnostic only after strict identity matching. It is not an identity gate and is not promotion evidence.

### Legacy selected-only identities

| pair | matches | main match | other match | ambiguous main/other | unmatched main/other |
|---|---:|---:|---:|---:|---:|
| offset0 vs 1 | 72 | 17.82% | 19.41% | 0 / 0 | 332 / 299 |
| offset0 vs 2 | 54 | 13.37% | 14.14% | 0 / 0 | 350 / 328 |
| offset0 vs 3 | 55 | 13.61% | 14.03% | 0 / 0 | 349 / 337 |
| offset0 vs 4 | 81 | 20.05% | 20.66% | 0 / 0 | 323 / 311 |

## Interpretation

Two facts coexist.

First, **exclusive packing is a material identity pollutant**. Moving from selected-only to all canonical qualified identities raises strict same-event match counts from `72/54/55/81` to `180/129/129/184`. Among the strict qualified matches that do exist, **56.52%–60.56% are hidden by legacy packing** because one or both sides were overlap-suppressed. Therefore exclusive non-overlap packing must remain downstream and must not regain authority to define whether a financial two-wave morphology event exists.

Second, **removing packing is not sufficient**. The canonical qualified universe still has only about **18.1%–25.8% main-side strict mutual-unique coverage** across the four harmless 5m offsets. Equivalently, main-side unmatched counts remain `531/583/582/527` out of 712, roughly **74%–82% unmatched**. Ambiguity is essentially absent, so the failure mode is not an evaluator tie-breaking problem; it is that most qualified canonical identities simply do not have a strict same-event counterpart under harmless slicing changes.

That combination is exactly the frozen semantic definition of **Route M**:

> packing hides substantial stable identities, but qualified identity remains materially unstable.

Route Q is rejected because the canonical qualified pool does not show a clear high-coverage local-match structure across all four offsets. Route U alone is also incomplete because packing demonstrably destroys a large share of the stable matches that do exist.

## Consequences

1. **Architecture decision is retained:** morphology identity and exclusive packing stay separated permanently at this layer.
2. **Direction adjudication remains blocked.** Do not return to D1/D2/PAWCT yet, despite high D1 agreement on the matched subset.
3. Continue **upstream identity research** on ridge/qualification representation under harmless slicing changes.
4. Do not tune the v0.5.4 qualification threshold or v0.5.2 ridge rules against these observed outcomes without a separately frozen experiment.
5. Do not invent a post-hoc numeric acceptance cutoff from this replay.
6. The next experiment should diagnose why strict identity edges are absent for the unmatched majority before proposing a new recognizer component. At minimum separate: phase mismatch, anchor-count/topology mismatch, ordered-anchor displacement beyond one bar, scale-evidence/qualification survival differences, and genuinely different parent families. Freeze that decomposition before using it to change the recognizer.

## Evidence paths

- frozen protocol: `docs/research/two_wave_qualified_identity_audit_protocol_v060.md`
- local feedback: `docs/ops/cloud_local_communication.md`, CL-20260906-002
- committed summary: `cloud_results/local_v060_qualified_identity_audit/summary.json`
- data identity: `cloud_results/local_v060_qualified_identity_audit/data_identity.json`
- per-view canonical identities / causal events / evidence events: `cloud_results/local_v060_qualified_identity_audit/5m_offset_*/`
- local result commit: `2d41cba048d8c62d0aca19ac501764a03082941c`

## Final state

**v0.6.0 cloud adjudication = Route M.**

`morphology_replication_not_yet_accepted`

`trade_authority=false`
