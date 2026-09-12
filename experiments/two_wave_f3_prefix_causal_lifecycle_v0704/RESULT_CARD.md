# v0.7.4 F3 Prefix-Causal Lifecycle Reconstruction — Result Card

Formal workflow run: `34681831280`  
Protocol: `docs/research/TWO_WAVE_F3_PREFIX_CAUSAL_LIFECYCLE_V0704_PROTOCOL.md`  
Protocol freeze commit: `3c0ae26d3453d8d0c5563be6ad58e7ea8c463ee0`  
Formal result commit: `96e528680b42e42b1951b9b656a9ed790c51073d`

## Purpose

Test whether the frozen F3 persistence-dominant ridge identity can be represented as a prefix-causal, append-only lifecycle object without falsely requiring permanent skipped-ridge death at first observation.

The lifecycle keeps `observed` distinct from terminal C1 `certified` status. Historical events may not rewrite object identity, first-observation time, or prior evidence.

## Required replication

The formal run reproduced the upstream authorities exactly:

- frozen static F3 support: **`8/11`**;
- frozen v0.7.3 C1-certified support: **`7/11`**.

The final lifecycle-live object-key set matched the final frozen static F3 object-key set in every anchored case.

## Semantic continuity

Formal lifecycle support:

- static F3 support: **`8/11`**;
- lifecycle-live support: **`8/11`**;
- C1-certified support: **`7/11`**;
- live-unresolved semantic support: **`1/11`**;
- static-supported / certified-unsupported gap cases: **`1`**;
- that permanent-certificate gap is represented as **live unresolved**, not falsely certified.

Per-ordinal live semantic cell-hit cases are `11/11, 11/11, 11/11, 11/11, 10/11` for ordinals 0–4.

## Append-only / causal invariants

Hard invariant violations: **`0`**.

In particular:

- object identity never rewrote;
- first observation remained immutable under longer-prefix replay;
- no event used future RidgeDeath or future ridge survival;
- no certification preceded observation;
- no certified object later left the live static set;
- final lifecycle-live and frozen static object-key sets were identical.

## Lifecycle mechanics

Across the 11 frozen anchored windows:

- observed lifecycle objects: **`1543`**;
- C1-certified lifecycle objects: **`1478`**;
- therefore **`65`** observed objects remained unresolved at their case cutoff;
- objects with a `dormant` transition: **`0`**;
- objects with a `reobserved` transition: **`0`**;
- observation-to-certification delay: median **`0`** bars, maximum `22` bars;
- first-observation witness multiplicity: median `2`, maximum `8` realizations;
- lifecycle event count per object: median `2`, maximum `2`;
- suppressed attempted identity rewrites: `0`.

The absence of dormancy/reobservation is descriptive Development evidence for this frozen universe; it is not promoted into a fitted rule or a universal guarantee.

## Formal verdict

**`v0704_f3_prefix_causal_lifecycle_representation_supported`**

Interpretation:

- the v0.7.3 one-case failure was a failure of **permanent-at-first-observation semantics**, not a requirement to discard the causal F3 observation itself;
- F3 can be carried as an immutable prefix-causal object whose state is `observed_live_unresolved` until explicit C1 permanence evidence arrives;
- the eighth static-supported case remains causally representable without using future information;
- this is still Development evidence only and does not grant active morphology authority.

The v0.6.4 sequential raw-projection and v0.6.5 first-valid immutable-publication principles remain the next downstream layer to transplant. v0.5.4/v0.6.18 qualification and D1/v0.6.25 direction remain blocked until lifecycle-aware publication semantics are adjudicated.

## Next authorized step

Freeze a **provisional lifecycle publication transplant**:

1. attach the historical v0.6.4 sequential raw-projection principle to the first `observed` lifecycle event, not to future certification;
2. apply v0.6.5 first-valid immutable publication without rewriting the lifecycle object identity;
3. preserve lifecycle status (`observed_live_unresolved` vs `certified`) in the published record;
4. verify that later certification only appends status/evidence and never rewrites the first published raw identity;
5. quantify projection validity, later confirmations, and would-be rewrites separately for provisional and certified states;
6. keep qualification and direction calibration blocked until this publication layer is frozen and adjudicated.

Do not use future C1 certification to backdate a publication, fit a waiting period, or drop the unresolved eighth case merely because permanence arrives later.

`morphology_acceptance=false`, `trade_authority=false`, `production_authority=false`.
