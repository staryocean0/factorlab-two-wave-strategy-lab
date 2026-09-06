# v0.6.9 Preanalysis — path-metric sampling-resolution response

Date: 2026-09-06

Status: **WRITTEN BEFORE ANY v0.6.9 RESOLUTION-RESPONSE OUTPUT IS READ**

## 1. Why this audit is needed

v0.6.7 proved that the dominant qualification disagreement mechanism is path sampling sensitivity.

v0.6.8 then tested a single shared 1m representation while keeping the original 5m path thresholds. Binary disagreement fell, but positive qualification collapsed because canonical-1m efficiency rejected many more identities.

Therefore the next question is not “which threshold should replace 0.5?” and not “should we simply use 1m?”

The next question is:

> how do the frozen path metrics themselves transform under sampling refinement on the **same physical leg**, and is there any stable resolution semantics that could support a later representation design?

No threshold or qualification rule may change in v0.6.9.

## 2. Frozen population

Primary population: every v0.6.5 immutable published raw identity in each native-5m view for which the corresponding supplied `1m_official` path is available.

Use the same four published raw-anchor legs and the same absolute leg endpoints.

v0.6.8 controls:

```text
published identities:
offset0 38,176
offset1 36,737
offset2 36,619
offset3 36,480
offset4 36,264

canonical 1m unavailable = 0 in every view
```

No new identity selection is allowed.

## 3. Nested-partition meaning

For one view and one leg, the native 5m close timestamps lying between the published anchors form the coarse observed path. The supplied 1m timestamps over the same absolute interval form the fine observed path.

Where every coarse timestamp has an exact supplied 1m row with the same close, the coarse partition is a subset of the fine partition.

For such aligned legs, exact finite-variation mathematics implies:

```text
TV_1m >= TV_5m
```

and, with the same endpoint displacement,

```text
Efficiency_1m <= Efficiency_5m
```

apart from zero-length conventions / floating representation.

v0.6.9 must explicitly verify alignment and these inequalities rather than assume them.

No analogous monotonicity is pre-asserted for jump_share or flat_share.

## 4. Metrics per leg

For each of the four legs report native-5m and canonical-1m:

- total variation;
- net displacement;
- efficiency;
- jump share;
- flat share;
- number of observed path rows.

Derived resolution-response diagnostics:

- `tv_refinement_ratio = TV_1m / TV_5m` when TV_5m > 0;
- `efficiency_ratio = E_1m / E_5m` when E_5m > 0;
- `efficiency_delta = E_1m - E_5m`;
- `jump_share_delta = J_1m - J_5m`;
- `flat_share_delta = F_1m - F_5m`.

No derived diagnostic becomes a qualification threshold.

## 5. Frozen threshold crossing diagnostics

The existing 0.5 thresholds may be used only to describe crossing direction.

Per leg report for efficiency:

- pass at 5m / pass at 1m;
- pass at 5m / fail at 1m;
- fail at 5m / pass at 1m;
- fail at both.

Likewise for jump share (`pass` means `<=0.5`) and flat share (`pass` means `<=0.5`).

These counts are not candidate qualification results.

## 6. Identity-level path-reason transitions

For each published identity, using four legs only, compare the three path reason flags under 5m and 1m and report transitions for:

- `inefficient_leg`;
- `jump_dominated_leg`;
- `flat_dominated_leg`.

This reproduces and generalizes v0.6.7/v0.6.8 without applying non-path qualification.

## 7. Duration-response overlay

Sampling response may depend on leg duration.

Report resolution-response diagnostics by the **existing native leg duration in bars**, but do not invent fitted bins. Required output:

- exact-duration counts for each integer duration with adequate observations;
- overall correlation/association between native leg duration and TV refinement ratio / efficiency delta / jump delta;
- no regression model is promoted.

If compact reporting requires grouping, only these pre-registered descriptive bins may be used:

```text
1-3 bars
4-5 bars
6-11 bars
12-23 bars
24+ bars
```

These bins reflect existing qualification scale boundaries and are not tuned to v0.6.9 results.

## 8. Required strict-pair overlays

Use the frozen v0.6.5 29,453 strict pair universe only as an overlay.

Compare resolution-response distributions for:

- v0.6.6 both-qualified pairs (482);
- v0.6.6 qualification disagreements (699);
- v0.6.1 target repaired pairs (80), split by v0.6.6 agreement/disagreement.

No pair is reclassified by v0.6.9.

## 9. Non-identifiability synthetic proof

Synthetic tests must retain the following mathematical fact:

Two different fine paths can have exactly the same coarse endpoint closes while having different fine total variation, efficiency and jump concentration.

Therefore exact fine-path properties are not identifiable from coarse close samples alone without additional assumptions or information.

This rules out any later claim that a 5m-only formula can exactly recover canonical fine-path variation in all cases.

## 10. Interpretation

No post-hoc threshold mapping.

Cloud may conclude only whether:

- path metrics have a predictable resolution scaling that could support later normalization;
- resolution response is too heterogeneous for a simple scalar threshold remapping;
- some metrics are structurally redundant/opposed under refinement;
- or additional representation research is required.

No candidate replacement metric is promoted in v0.6.9.

A later repair preanalysis may be authorized only after this resolution-response audit is closed.

Duration-geometry remains a separate secondary workstream.

Global state remains `morphology_replication_not_yet_accepted`; operational baseline remains v0.4.3; direction/outcome/trading remain frozen.
