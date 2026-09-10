# Two-Wave v0.6.30 Range-evidence intersection protocol

Date: 2026-09-10
Status: frozen before outcome replay

## Purpose

Test one direct parent-state improvement that preserves the strongest pooled-exact contribution v0.6.25 and uses the intersection of two previously frozen, independently motivated Range evidence sources. No new threshold is introduced.

The candidate does not retune v0.6.25, v0.6.27, or v0.6.29. It asks whether the two earlier Range contributions become sufficiently stable when both must agree on a record.

## Frozen upstream controls

Qualification remains v0.6.18. Evaluation remains the same 1,462 strict same-financial-identity pairs where both views are v0.6.18-qualified.

v0.6.25 baseline controls:

- pooled exact: `1402/1462 = 95.89603283173734%`;
- pooled decisive coverage: `70.86183310533516%`;
- decisive agreement: `100%`;
- opposite UpTrend/DownTrend conflicts: `0`;
- pooled decisive Range labels: `22`;
- per-offset exact counts offset1..4: `380 / 271 / 292 / 459`.

Frozen inherited Range evidence:

- v0.6.27 state-relative Range margin requirement: `0.03` amplitude units (`20% * 0.15`); this value is not changed;
- v0.6.29 two-cycle IQR occupancy-band overlap requirement: `0.50`; this value is not changed.

No future return, PnL, H1/H2, third wave, 2021+, 2026 data, or cross-offset information may enter runtime features or threshold choice.

## Sole candidate

For one already-published v0.6.18-qualified identity:

1. Compute v0.6.25 first.
2. If v0.6.25 is decisive, preserve it exactly.
3. Only if v0.6.25 is `Uncertain`, compute the frozen v0.6.23 endpoint-erosion consensus.
4. The consensus must be exactly `Range`.
5. Compute the already-defined consensus margin to the frozen Range boundary; require the v0.6.27 frozen Range requirement `margin >= 0.03` amplitude units.
6. Compute the v0.6.29 two-cycle IQR occupancy-band overlap; require `overlap >= 0.50`.
7. Rescue to `Range` only if both 5 and 6 pass. Otherwise remain `Uncertain`.

There is no weight, no candidate menu, no grid and no post-result threshold movement.

Every v0.6.30 change relative to v0.6.25 must be exactly `Uncertain -> Range`; any other change invalidates the run.

## Frozen promotion gates

v0.6.30 may become the best-supported parent-direction research component only if all are true:

- all upstream controls reproduce exactly;
- D1 decisive override count = 0;
- all label changes versus v0.6.25 are exactly `Uncertain -> Range`;
- each offset1..4 exact agreement is >= the corresponding v0.6.25 exact agreement;
- pooled exact agreement improves by at least `0.20` percentage points over v0.6.25;
- pooled decisive coverage improves by at least `1.00` percentage point over v0.6.25;
- pooled decisive agreement >= `99.5%`;
- opposite UpTrend/DownTrend conflicts remain `0`;
- pooled decisive Range share >= `2%`;
- pooled decisive UpTrend share >= `15%` and DownTrend share >= `15%`.

Failure leaves parent-direction winner unset and v0.6.25 remains the strongest pooled-exact contribution. A local contribution may still be retained.

Independent morphology acceptance remains false. Trading and production authority remain false.
