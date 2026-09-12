# Two-Wave v0.7.1 — Ridge-Supported Semantic Parent Objectization Reconstruction

Status: **frozen before any v0.7.1 family-support statistics are read**.

## 1. Starting point

v0.7.0 localized the first major semantic break to the bridge from the retained TCSS/ridge state space to the legacy **exact consecutive five-ridge tuple** object:

- human-positive anchored cases: `11`;
- raw-turn support L0: `11/11`;
- common-scale causal ridge support L1: `10/11`;
- exact five-ridge tuple support L2: `3/11`;
- exact-tuple to causal tuple-birth loss: `0` cases.

Therefore v0.7.1 keeps the causal TCSS extrema/ridge infrastructure unchanged and tests whether a structurally defined ridge hierarchy can reconstruct a five-anchor semantic parent object **without fitting any bar-distance tolerance to the reference labels**.

This is Development/discovery reconstruction only. It does not create morphology acceptance or active qualification/direction authority.

## 2. Frozen evidence universe

Use exactly the same 11 v0.6.48 final-reference candidate cases that are:

- `two_complete_same_scale_waves=yes`;
- equipped with complete valid final-reference `p0..p4`;
- represented in the frozen 96-bar annotation chart.

Frozen hashes:

- source main-view SHA256: `bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`;
- final reference SHA256: `321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d`;
- sampling commitment SHA256: `f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8`.

Human support cells and inferred kinds are exactly the frozen deterministic v0.7.0 definitions. No notes, confidence, future bars, PnL, D1/v0.6.25 outputs, or fitted tolerance may be used.

## 3. Causal ridge state at a cutoff

A ridge node is eligible only when:

- its occurrence lies inside the frozen 96-bar chart;
- its node confirmation is `<= cutoff`.

For each ridge ID define its **causal survival level at cutoff** as the maximum scale level at which that same ridge ID has an eligible confirmed representation by the cutoff.

No future survival information may be used.

## 4. Frozen object families

All families use five ordered, distinct ridge nodes with alternating kinds at one common scale level. The only difference is how intervening ridge nodes are treated.

For all families the semantic object identity is the ordered tuple of five **ridge IDs**, not `(ridge IDs, scale level)`. If the same ordered ridge-ID tuple satisfies a family at multiple scale levels, it counts as **one object**. Human-reference support is true when at least one eligible scale realization of that ridge-ID object places its five nodes in the frozen human cells with the required kinds. Candidate multiplicity therefore counts unique ridge-ID objects, not duplicate scale realizations.

### F0 — legacy exact-consecutive tuple baseline

Use the existing v0.5.2 exact-ridge tuple definition: the five selected nodes must be consecutive in the level's ordered ridge sequence.

This is a continuity baseline only and is not eligible to become the reconstructed champion.

Expected anchored support from v0.7.0: `3/11`. Drift from this count fails closed.

### F1 — ordered common-scale nonconsecutive upper bound

At one level, any ordered five-node subsequence with alternating kinds is allowed; intervening ridge nodes may remain between selected anchors.

This is the structural upper bound implied by v0.7.0 L1 and is **not eligible to become champion** because it does not distinguish semantic parent ridges from arbitrary intervening structure.

Expected anchored support from v0.7.0: `10/11`. Drift from this count fails closed.

### F2 — one-step-survivor skeleton

For each level `l` that has a next coarser level `l+1`:

1. start from eligible confirmed ridge nodes at level `l` inside the chart;
2. keep only ridge IDs that also have an eligible confirmed representation at level `l+1` by the same cutoff;
3. sort these survivors by occurrence / confirmation / node ID;
4. every consecutive five-node alternating window in this survivor sequence is an F2 object.

This removes ridge structure that fails to persist even one adjacent scale step, using only the existing causal ridge hierarchy. There is no numeric persistence threshold.

### F3 — persistence-dominant nonconsecutive quintet

At one level, consider an ordered alternating five-node subsequence. For every pair of adjacent selected anchors:

- inspect all same-level eligible ridge nodes skipped between them;
- every skipped ridge must have causal survival level **strictly lower** than the minimum causal survival level of the two selected boundary ridges.

If no node is skipped in a gap, the condition is vacuously satisfied.

Thus an F3 object may skip intermediate fluctuations only when the selected semantic skeleton is topologically more persistent than every skipped ridge. No bar-distance, amplitude, duration, or human-label tolerance is introduced.

## 5. Human-reference support test

A family object supports one anchored reference case only if at least one eligible scale realization of that object has five nodes falling one-per-frozen-human-support-cell in ordinal order and each node kind matches the inferred human kind.

Report for every family:

- support case count out of 11;
- support fraction;
- unique candidate-object count distribution across the 11 charts;
- unique human-compatible object count distribution;
- number of cases with exactly one compatible object;
- per-ordinal compatible-node exact-anchor incidence, descriptive only.

No case-level object/reference table may be committed.

## 6. Frozen decision rules

Development-level family support threshold remains `8/11` cases, inherited from v0.7.0.

Precedence:

1. F0 must reproduce `3/11`; otherwise fail closed for lineage drift.
2. F1 must reproduce `10/11`; otherwise fail closed for salvage-universe drift.
3. If F2 support is `>=8/11`, verdict is `v0701_one_step_survivor_objectization_candidate_supported`.
4. Else if F3 support is `>=8/11`, verdict is `v0701_persistence_dominant_objectization_candidate_supported`.
5. Else verdict is `v0701_ridge_support_salvaged_but_frozen_objectization_families_insufficient`.

If both F2 and F3 pass, F2 has frozen precedence because it is the simpler adjacent-scale construction and introduces fewer degrees of freedom.

No candidate family becomes morphology authority in v0.7.1. A supported family only becomes the input to a later causal event/publication + independent-reference presence-calibration stage.

## 7. Component salvage semantics

Whatever the result:

- source/data/clock/replay/governance stay retained;
- TCSS extrema/ridge lineage stays retained as support infrastructure;
- the legacy exact-consecutive-five-ridge tuple remains historical baseline evidence, not semantic-parent authority;
- tuple-birth timing, v0.6.4/v0.6.5 raw projection/publication, v0.5.4/v0.6.18 same-scale qualification, and D1/v0.6.25 direction are **not declared false**;
- those downstream components remain queued for transplantation tests only after a semantic objectization family is supported.

## 8. Prohibited shortcuts

v0.7.1 may not:

- fit a bar-distance tolerance to human anchors;
- fit a skip-count threshold;
- tune persistence levels from the 11 labels;
- use amplitude/duration thresholds to rescue a family;
- inspect annotator notes/confidence;
- use future outcomes or PnL;
- promote qualification, direction, trade, or production authority.

If neither F2 nor F3 passes, the next step must freeze a new structural object family before reading its reference performance.
