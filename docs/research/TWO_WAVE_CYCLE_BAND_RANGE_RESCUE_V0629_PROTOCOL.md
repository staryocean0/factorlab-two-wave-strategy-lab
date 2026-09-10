# Two-Wave v0.6.29 cycle-band Range rescue protocol

Date: 2026-09-10
Status: frozen before outcome replay

## Purpose

Test one direct parent-state recognizer improvement after v0.6.28 closed the small-sample support-dispersion route. The candidate keeps v0.6.25 exactly as the base recognizer and adds one independent, causal Range evidence source from the two complete parent cycles: robust central price-band overlap.

This is not endpoint D2 and not PAWCT. It does not compare cycle endpoints or phase-aligned pointwise translation. It asks whether the two completed cycles repeatedly occupy the same robust central price region.

## Frozen upstream controls

- qualification policy: v0.6.18 unchanged;
- evaluation universe: 1,462 strict same-financial-identity pairs where both views are v0.6.18-qualified;
- D1 exact: 1,400 / 1,462;
- v0.6.25 exact: 1,402 / 1,462;
- v0.6.25 pooled decisive coverage: 0.7086183310533516;
- v0.6.25 decisive agreement: 1.0;
- v0.6.25 opposite UpTrend/DownTrend conflicts: 0;
- v0.6.25 pooled decisive Range labels: 22, corresponding to 1.0618% of decisive labels;
- v0.6.25 exact counts by offset1..4: 380 / 271 / 292 / 459.

No future return, PnL, H1/H2, third wave, 2021+, 2026 data, or cross-offset information may enter runtime features or choose thresholds.

## Frozen candidate

For each already-published, v0.6.18-qualified identity, compute v0.6.25 first.

1. If D1 is decisive, preserve D1 exactly. No override is permitted.
2. If v0.6.25 is already decisive, preserve v0.6.25 exactly.
3. Only if v0.6.25 remains `Uncertain` and the frozen v0.6.23 endpoint-erosion consensus state is `Range`, compute one additional single-view Range evidence measure.
4. Let the five occurrence bars be `a0<a1<a2<a3<a4`. Define cycle 1 as all closes on `[a0,a2]` and cycle 2 as all closes on `[a2,a4]`.
5. For each cycle, define its robust central occupancy band as `[Q25(close), Q75(close)]` using NumPy's fixed linear quantile definition.
6. Define central-band overlap coefficient

   `overlap = intersection_width / min(IQR_width_1, IQR_width_2)`.

   If either IQR width is non-positive within machine epsilon, overlap is 0 (fail closed).
7. Frozen Range admission rule: `overlap >= 0.50`.
8. If the rule passes, output `Range`; otherwise remain `Uncertain`.

The threshold 0.50 is a geometric definition (at least half of the narrower robust central occupancy band is shared), not a fitted value from v0.6.28's 19 harmful sides. There is no threshold menu and no post-result tuning.

Therefore every v0.6.29 label change relative to v0.6.25 must be exactly `Uncertain -> Range`; otherwise fail closed.

## Frozen evaluation

Cross-offset matching is evaluation-only. Runtime remains single-view and causal.

Report v0.6.25 and v0.6.29 on the same 1,462 pairs:

- four-state exact agreement;
- decisive coverage;
- decisive agreement when both views are decisive;
- opposite UpTrend/DownTrend conflict count;
- pooled decisive class shares;
- per-offset exact agreement;
- count/topology of newly admitted Range sides.

## Frozen promotion gates

v0.6.29 may become the best-supported parent-direction research component only if all are true:

- all frozen upstream controls reproduce exactly;
- D1 decisive override count = 0;
- every v0.6.25 -> v0.6.29 label change is `Uncertain -> Range`;
- each of offsets 1..4 has v0.6.29 exact agreement >= v0.6.25 exact agreement;
- pooled exact agreement improves by at least 0.20 percentage points over v0.6.25;
- pooled decisive coverage is at least 1.00 percentage point above v0.6.25;
- pooled decisive agreement >= 99.5%;
- opposite UpTrend/DownTrend conflicts remain 0;
- pooled decisive Range share >= 2%;
- pooled decisive UpTrend share >= 15% and DownTrend share >= 15%.

Failure leaves the parent-direction winner unset. Any validated local contribution remains recorded but cannot replace v0.6.25 as the strongest pooled-exact contribution.

Independent morphology acceptance remains false. Trading and production authority remain false.
