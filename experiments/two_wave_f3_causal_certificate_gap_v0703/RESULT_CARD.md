# v0.7.3 F3 Causal-Certificate Gap Attribution — Result Card

Formal workflow run: `34681005995`  
Protocol: `docs/research/TWO_WAVE_F3_CAUSAL_CERTIFICATE_GAP_ATTRIBUTION_V0703_PROTOCOL.md`  
Protocol freeze commit: `de795faf95a8a47c4835ccae76f37c6d1c196821`  
Formal result commit: `68c978187b531ad6ac18c564a3214035be0dafa5`

## Purpose

Explain the single v0.7.2 case that is supported by the frozen static F3 reconstruction but not by the permanent causal C0 certificate, and test one preregistered minimal certificate C1 without changing F3 objectization or the frozen `8/11` Development gate.

## Required replication

The formal run reproduced the upstream authorities exactly:

- static F3 semantic support: **`8/11`**;
- v0.7.2 C0 causal support: **`7/11`**;
- static-supported / C0-unsupported gap cases: **`1`**.

Any drift would have failed closed.

## C1 result

C1 preserved explicit RidgeDeath as mandatory evidence and changed only the boundary-survival representation: a selected boundary could prove survival with any confirmed representation at level `>= death.coarse_level`, rather than requiring the exact coarse level.

Formal result:

- C1 causal support: **`7/11`**;
- recovered cases versus C0: **`0`**;
- therefore the frozen `8/11` causal-support threshold is **not restored**.

Across the 36 C1-certified human-compatible realizations, proof delay from selected-node confirmation had median **`3.5` bars**, minimum `0`, maximum `10`.

## Gap attribution

The one gap case contains **4** human-compatible static F3 realizations. Across those four realizations:

- `missing_explicit_death_by_cutoff`: **4**;
- `proof_confirmation_after_cutoff`: **4**;
- boundary-survival-only blocker: **0**.

Thus every compatible realization in the gap case lacks an explicit skipped-ridge death at the frozen cutoff, and full-lineage read-only attribution shows that the relevant proof arrives only later. Future lineage was used only to classify the blocker; it was not used by C0 or C1 as certificate evidence.

Across all 47 human-compatible static F3 realizations in the 11 anchored cases, aggregate blocker counts are:

- `missing_explicit_death_by_cutoff`: **11**;
- `proof_confirmation_after_cutoff`: **11**.

The exact-coarse boundary requirement is therefore not the cause of the one-case semantic loss.

## Formal verdict

**`v0703_gap_requires_explicit_death_evidence_unavailable_at_cutoff`**

Interpretation:

- F3 remains a supported **static Development reconstruction** at `8/11`.
- Under the current v0.5.2 ridge-lineage semantics, a skipped ridge is not permanently dead until a later ordered coarse continuation causally seals that transition.
- The missing case is not recoverable by the preregistered C1 boundary-proof relaxation.
- The current permanent-at-publication F3 event layer therefore remains unresolved at `7/11`.
- The v0.6.4 sequential raw-projection and v0.6.5 first-valid immutable-publication principles remain positive downstream salvage evidence from v0.7.2, but remain blocked behind the event layer.
- v0.5.4/v0.6.18 qualification and D1/v0.6.25 direction remain historical components awaiting later transplantation tests; they are not rejected.

## Next authorized step

Reconstruct the **causal object/event layer** rather than weaken the permanence proof. The next protocol should test whether F3 can be represented as an append-only lifecycle object — for example `observed -> certified` or `observed -> invalidated` — so that a prefix-causal F3 observation can remain immutable without falsely claiming permanent skipped-ridge death at first observation.

That next stage must preserve the same F3 static definition and `8/11` semantic-support continuity, use no future information to create an observation event, prohibit identity rewrites, and keep qualification/direction calibration blocked until the lifecycle semantics are separately frozen and audited.

`morphology_acceptance=false`, `trade_authority=false`, `production_authority=false`.
