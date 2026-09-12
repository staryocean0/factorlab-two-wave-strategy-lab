# v0.7.5 F3 Provisional Lifecycle Publication Transplant — Result Card

Formal workflow run: `34683112169`  
Protocol: `docs/research/TWO_WAVE_F3_PROVISIONAL_LIFECYCLE_PUBLICATION_V0705_PROTOCOL.md`  
Protocol freeze commit: `9652c7c2b0ba3761f1f326fd69d2d79039bd397d`  
Formal result commit: `5a7be41457adfdc304d215c06bd3ea8720ed16e7`

## Purpose

Test whether the frozen v0.7.4 prefix-causal F3 lifecycle can inherit the historical v0.6.4 sequential raw-projection and v0.6.5 first-valid immutable-publication principles from the first `observed` event, including objects that are still `observed_live_unresolved`, without using later certification to backdate or rewrite publication.

## Required upstream replication

The formal run reproduced the frozen v0.7.4 authority exactly:

- static F3 semantic support: **`8/11`**;
- lifecycle-live semantic support: **`8/11`**;
- C1-certified semantic support: **`7/11`**;
- observed lifecycle objects: **`1543`**;
- certified lifecycle objects: **`1478`**;
- lifecycle hard-invariant violations: **`0`**;
- dormant transitions: **`0`**;
- reobserved transitions: **`0`**.

## Publication coverage and causality

All **`1543/1543`** observed lifecycle objects obtained a publication. Publication happened at the first observation bar in every case: delay from observation had median `0`, minimum `0`, and maximum `0` bars.

Coverage by final lifecycle state:

- certified objects published: **`1478/1478`**;
- final unresolved objects: `65`;
- final unresolved objects published: **`65/65`**;
- final unresolved objects left unpublished: **`0`**.

Causal / append-only hard-invariant violations: **`0`**. Deterministic replay passed for all `11` anchored cases.

The prefix predecessor rule used only same-level ridges confirmed by the publication evidence bar. No future-unconfirmed ridge was used for predecessor selection, and no later certification was used to backdate publication.

## Immutable-publication mechanics

- prior invalid projections before publication: `0`;
- invalid evidence after publication: `1`;
- later valid evidence with the same raw identity: `2558`;
- later valid evidence that would have rewritten raw identity but was suppressed: **`239`**;
- prefix-predecessor change evidence: `0`;
- publications made while object was unresolved and later became certified: `669`;
- publications made when already certified: `809`;
- publications still unresolved at case cutoff: `65`.

The `239` would-be rewrites are positive stress evidence for the append-only rule: later evidence was allowed to append evidence/status, but never altered the first publication identity.

## Semantic continuity

The frozen human labels were used only after label-free construction for final continuity scoring.

- published-raw semantic support: **`9/11`**;
- per-ordinal raw-cell hit cases: **`11/11, 11/11, 11/11, 11/11, 10/11`**;
- support published while unresolved: `8/11`;
- support published when already certified: `2/11`;
- final-certified published-raw support: `8/11`;
- final-unresolved published-raw support: `1/11`.

The single frozen permanent-certificate gap case is retained as the **same lifecycle object** and has provisional raw publication satisfying all five semantic support cells: **`1/1`**.

Therefore the v0.7.2 raw-projection/publication semantic benchmark does not degrade under the v0.7.4 lifecycle representation.

## Formal verdict

**`v0705_f3_provisional_lifecycle_publication_transplant_supported`**

Interpretation:

- v0.6.4 sequential raw projection is transplantable to the first prefix-causal F3 observation;
- v0.6.5 first-valid immutable publication remains valid under provisional lifecycle semantics;
- permanent C1 certification is not required before raw publication;
- later certification may append lifecycle status/evidence but may not rewrite the first published raw identity;
- the unresolved eighth semantic case survives publication causally rather than being dropped or backdated;
- this remains Development evidence only. No active morphology, trade, or production authority is granted.

## Next authorized step

Freeze a **lifecycle-publication qualification interface + semantic transplant precheck** for historical v0.5.4 / v0.6.18 qualification.

1. Feed the immutable v0.7.5 publication fields (`phase`, five raw occurrence bars, publishing confirmation bar, bars) into the existing published-identity qualification interface without changing numerical thresholds.
2. First audit interface validity and eliminate implementation/interface exceptions without fitting or retuning qualification rules.
3. Preserve publication identity and lifecycle status; qualification may annotate a publication but may not mutate object or raw identity.
4. Quantify v0.5.4/v0.6.18 hard reasons and qualification rates separately for publications made while unresolved versus already certified, and by final lifecycle state.
5. Only after the interface is clean may frozen human labels be used for semantic correspondence scoring.
6. Direction remains blocked until qualification transplantation is separately adjudicated.

Do not refit v0.5.4/v0.6.18 thresholds, add a certification waiting period, condition qualification on future lifecycle state, or reactivate D1/v0.6.25.

`morphology_acceptance=false`, `trade_authority=false`, `production_authority=false`.
