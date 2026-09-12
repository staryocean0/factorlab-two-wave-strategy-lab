# Two-Wave v0.7.3 — F3 Causal-Certificate Gap Attribution

Status: **frozen before any v0.7.3 gap-case blocker statistics or alternative-certificate results are read**.

## 1. Starting point

v0.7.1 selected F3 (`persistence-dominant nonconsecutive ridge quintet`) as a Development semantic-parent reconstruction candidate with `8/11` anchored reference-positive support.

v0.7.2 reproduced static F3 support at `8/11`, but its explicit skipped-ridge death + exact-coarse-boundary-survival certificate preserved only `7/11` cases. The frozen event gate therefore failed with verdict:

`v0702_f3_static_objectization_not_causally_publishable`.

v0.7.2 also found positive downstream salvage evidence (`9/11` first-valid published-raw semantic support), but causal event semantics must be resolved first.

Formal v0.7.2 result commit: `580828754920f5c9a747bee310c0657bf41443c3`.

## 2. Question

Why does exactly one static-F3-supported human-positive case lack a v0.7.2 causal certificate?

Distinguish:

1. no explicit causal death exists for at least one skipped ridge by cutoff;
2. the skipped ridge has a death, but selected boundary survival is not proven by cutoff;
3. the necessary death/survivor evidence exists only after cutoff;
4. v0.7.2 C0 is implementation-level overconstraint because it requires the selected boundary ridge to be represented at the death's **exact coarse level**, when a confirmed representation at any still-coarser level would already prove survival past the death transition;
5. mixed/other contract causes.

This is an attribution/certificate-equivalence audit. It does not change F3 objectization, the `8/11` gate, or any downstream threshold.

## 3. Frozen universe and inputs

Use exactly the v0.7.2 universe and hashes:

- source SHA256 `bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`;
- final reference SHA256 `321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d`;
- sampling commitment `f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8`;
- exactly `11` anchored reference-positive candidate cases;
- frozen v0.7.0 human support cells;
- frozen v0.7.1 F3 static definition;
- frozen v0.7.2 C0 certificate implementation.

Required replication before attribution:

- static F3 support = exactly `8/11`;
- C0 causal support = exactly `7/11`;
- therefore static-supported / C0-unsupported gap cases = exactly `1`.

Any drift fails closed.

No notes/confidence, future returns/PnL, direction outputs, qualification outputs, or fitted tolerance may be used.

## 4. C0 blocker decomposition

For every human-compatible static F3 realization in the one gap case, and descriptively across all eight static-supported cases, inspect every skipped ridge between selected adjacent anchors.

For each skipped ridge classify causal-proof blockers known at the frozen cutoff:

- `missing_explicit_death_by_cutoff`: no explicit v0.5.2 RidgeDeath has confirmation `<= cutoff`;
- `death_transition_before_realization_level`: recorded death transition is structurally incompatible with the realization level;
- `left_boundary_not_proven_past_death_by_cutoff`;
- `right_boundary_not_proven_past_death_by_cutoff`;
- `exact_coarse_boundary_representation_missing_but_coarser_confirmed_survival_exists`;
- `proof_confirmation_after_cutoff`;
- `other_contract_blocker`.

Do not emit the case ID, timestamps, human anchors, or case-level table.

## 5. Frozen minimal explicit-death certificate C1

C1 changes **only** the boundary-survival proof representation; it does not waive explicit death.

For each skipped ridge in a static F3 realization:

1. require an explicit RidgeDeath with `confirmation_index <= cutoff` and `fine_level >= realization_level`;
2. let `k = death.coarse_level`;
3. require the selected left boundary ridge ID to have at least one confirmed ridge-node representation at **some level `>= k`**, confirmation `<= cutoff`;
4. require the selected right boundary ridge ID likewise;
5. C1 proof confirmation is the max of selected realization-node confirmations, skipped-ridge death confirmations, and the earliest qualifying confirmed boundary representations used in steps 3–4.

Rationale: ridge IDs propagate only through adjacent-scale continuation. A confirmed representation at level `>=k` is a causal proof that the ridge survived through the `k-1 -> k` transition. Requiring the exact level-k representation is therefore not logically necessary if a still-coarser confirmed representation already exists.

C1 may not:

- infer a skipped-ridge death from absence;
- use a future node/death confirmed after cutoff;
- use final full-sample survival level as a substitute for confirmed cutoff evidence;
- change F3 persistence dominance or human support cells.

## 6. C1 semantic-preservation test

Re-evaluate the same 11 anchored cases using the same static F3 realizations but C1 instead of C0.

Report:

- C1 causal-support cases;
- C1 minus C0 recovered-case count;
- event-proof confirmation delay distribution;
- blocker counts in the original one-case C0 gap;
- blocker counts aggregate across human-compatible static F3 realizations.

Frozen Development salvage threshold remains `8/11`.

## 7. Frozen verdict precedence

After required C0 replication:

1. if C1 causal support `>=8/11`:
   `v0703_minimal_explicit_death_certificate_restores_f3_causal_support`;
2. else if every human-compatible static realization in the gap case has at least one `missing_explicit_death_by_cutoff` blocker:
   `v0703_gap_requires_explicit_death_evidence_unavailable_at_cutoff`;
3. else if the gap is entirely boundary-survival evidence unavailable by cutoff:
   `v0703_gap_requires_boundary_survival_evidence_unavailable_at_cutoff`;
4. else if proof exists only after cutoff under the frozen causal clock:
   `v0703_gap_is_causal_confirmation_maturity_shortfall`;
5. else:
   `v0703_causal_certificate_gap_mixed_or_unresolved`.

No gate is lowered and no static F3 support claim is changed.

## 8. Governance

If C1 restores `8/11`, the next authorized stage is a separately frozen F3 event/publication rerun using C1 as the event certificate, followed by the already specified raw/publication transplantation precheck. v0.7.2's C0 remains historical evidence, not silently overwritten.

If C1 does not restore `8/11`, the next authorized stage must reconstruct the causal object/event layer; qualification calibration remains blocked.

Whatever the outcome:

- F3 static reconstruction remains Development evidence;
- v0.6.4/v0.6.5 projection/publication principles remain retained as positive transplant evidence, not active authority;
- v0.5.4/v0.6.18 and D1/v0.6.25 remain historical components awaiting later transplantation retests, not declared false;
- `morphology_acceptance=false`, `trade_authority=false`, `production_authority=false`.
