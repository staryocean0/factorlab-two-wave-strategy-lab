# v0.6.52 Ordinal-0 Predecessor / First-Valid Publication Lineage Audit — Result Card

Formal workflow run: `34669006007`  
Protocol: `docs/research/TWO_WAVE_ORDINAL0_FIRST_VALID_PUBLICATION_LINEAGE_AUDIT_V0652_PROTOCOL.md`  
Protocol freeze commit: `76981c7c348807e4fe328020e81741e45e5c47dd`  
Formal raw result commit: `0bf09d84d8a082515c8205ef1cf02dc8fd984780`

## What was audited

This stage tests whether the structural specialness of ordinal 0 in the current implementation materially expresses itself through predecessor eligibility or v0.6.5 first-valid immutable publication.

The runtime contract was verified directly across the frozen Development reconstruction:

- ordinal 0 lower bound = birth-level predecessor occurrence + 1;
- ordinals 1–4 lower bound = prior selected raw anchor + 1;
- only ordinal 0 carries the predecessor provenance marker;
- publication evidence order = birth confirmation, birth level, event ID;
- first valid candidate publishes an immutable raw tuple;
- later differing valid candidates are suppressed rather than rewriting publication.

The audit uses **no human reference labels** in its primary decision.

## Background publication universe

Reconstruction produced:

- ridge tuple births: `38,636`
- canonical filtered groups: `38,634`
- valid projection evidence members: `38,178`
- published groups: `38,176`
- no-valid-publication groups: `458`
- all published groups with >=2 valid evidence members: only `2`
- suppressed would-be rewrite comparisons across the entire published universe: only `1`

There were **zero pre-publication invalid evidence members** among published groups. Thus predecessor eligibility did not delay publication for any actually published identity in this reconstruction.

The only suppressed rewrite in the full background universe changed both ordinal 0 and ordinal 1. It is therefore not an ordinal-0-only rewrite signal, and its denominator is scientifically negligible.

## Primary v0.6.18-qualified universe

The formal primary decision universe reproduces exactly `2,115` v0.6.18-qualified published identities.

Every one of those 2,115 identities has:

- evidence-member count = `1`
- valid-member count = `1`
- prior-invalid count = `0`
- later-valid evidence count = `0`
- suppressed rewrite count = `0`

Therefore the first-valid immutable publication mechanism is effectively **not exercised as a selection/freeze competition** inside the currently qualified universe. Each qualified identity arrives with one valid evidence member and no later valid alternative.

## Ordinal-0 projection geometry

Median absolute raw-vs-filtered displacement among the 2,115 qualified publishing members:

- p0: `3` bars
- p1: `3` bars
- p2: `3` bars
- p3: `3` bars
- p4: `3` bars

So ordinal 0 is not more displaced from its filtered ridge anchor than the other ordinals.

Median projection-window widths:

- p0: `18` bars
- p1: `24` bars
- p2: `25` bars
- p3: `23` bars
- p4: `13` bars

Ordinal 0's predecessor-defined window is therefore not anomalously wide relative to internal ordinals.

## Frozen gates

- Gate A — predecessor eligibility bottleneck material: **false**
- Gate B — first-valid freeze materially exposed: **false**; denominator = `0` qualified groups with later-valid evidence
- Gate C — rewrite instability ordinal-0 dominant: **false**; denominator insufficient
- Gate D — predecessor change associated with p0 rewrite: **false**; denominator insufficient
- Gate E — publishing p0 projection displacement structurally larger: **false**

## Formal verdict

**`v0652_structural_ordinal0_provenance_asymmetry_not_materially_expressed`**

The code-level provenance asymmetry is real: p0 is uniquely anchored by a birth-level predecessor. But the frozen data show that this asymmetry does not materially express itself through publication eligibility, first-valid freezing, rewrite instability, or unusually large raw projection displacement in the v0.6.18-qualified universe.

Therefore v0.6.4 predecessor support and v0.6.5 first-valid immutable publication are **closed as a material explanation** for the start-side human/model mismatch exposed by v0.6.50–v0.6.51.

This does **not** prove that the p0 mismatch itself is unimportant. It says the mismatch must be attributed further upstream or to a different representation layer.

## Next scientific breakpoint

The next legitimate read-only attribution is the representation layer immediately upstream of raw projection:

**filtered exact-ridge anchors vs raw-projected anchors vs frozen human anchors.**

The purpose is to determine whether the start-side mismatch already exists at the filtered exact-ridge `p0` before v0.6.4 raw projection, or whether raw projection worsens/improves it.

This next audit must be frozen before reading layer-attribution statistics and must not fit a new boundary tolerance, projection rule, ridge identity, or semantic-object challenger to v0.6.48 labels.

## Authority effect

- human reference labels used in v0.6.52 primary decision: **false**
- threshold fitting: **false**
- projection geometry changed: **false**
- publication policy changed: **false**
- qualification changed: **false**
- direction winner changed: **false**
- morphology acceptance: **false**
- trade authority: **false**
- production authority: **false**
