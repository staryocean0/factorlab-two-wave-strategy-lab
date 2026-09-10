# Two-Wave v0.6.31 mutual-median Range rescue protocol

Date: 2026-09-10
Status: frozen before outcome replay

## Purpose

Test one direct parent-state recognizer improvement after v0.6.30 showed that intersecting the frozen v0.6.27 Range margin and the v0.6.29 `IQR overlap >= 0.50` rule still selected too many one-sided slicing rescues.

v0.6.31 does **not** tune either old threshold. Instead it replaces the v0.6.29 overlap threshold with a parameter-free symmetric occupancy condition: the median price of each complete cycle must lie inside the other cycle's interquartile range. The condition must hold on all four already-frozen v0.6.23 endpoint-support views.

## Frozen upstream controls

Qualification remains v0.6.18. Evaluation remains the same 1,462 strict same-financial-identity pairs where both views are v0.6.18-qualified.

v0.6.25 baseline controls:

- pooled exact: `1402/1462 = 95.89603283173734%`;
- pooled decisive coverage: `70.86183310533516%`;
- decisive agreement: `100%`;
- opposite UpTrend/DownTrend conflicts: `0`;
- pooled decisive Range labels: `22`;
- per-offset exact counts offset1..4: `380 / 271 / 292 / 459`.

Inherited frozen evidence:

- v0.6.23 endpoint support views: `full`, `left_eroded_1`, `right_eroded_1`, `both_eroded_1`;
- v0.6.23 support states must be unanimously `Range`;
- v0.6.27 frozen Range consensus-margin requirement: `>= 0.03` amplitude units.

No future return, PnL, H1/H2, third wave, 2021+, 2026 data, or cross-offset information may enter runtime features or threshold choice.

## Sole candidate

For one already-published v0.6.18-qualified identity:

1. Compute v0.6.25 first.
2. If v0.6.25 is decisive, preserve it exactly.
3. Only if v0.6.25 remains `Uncertain`, compute the frozen v0.6.23 endpoint-erosion consensus.
4. The consensus must be exactly `Range`.
5. Compute the already-defined v0.6.27 Range consensus margin and require `margin >= 0.03` amplitude units.
6. For each of the four frozen v0.6.23 endpoint-support anchor views, split the completed parent into cycle 1 `[a0,a2]` and cycle 2 `[a2,a4]` using all closes in each interval.
7. On each support view compute each cycle's linear-interpolation `Q25`, median (`Q50`) and `Q75`.
8. A support view passes **mutual median containment** iff:
   - cycle-1 median lies inside cycle-2 `[Q25,Q75]`, inclusive; and
   - cycle-2 median lies inside cycle-1 `[Q25,Q75]`, inclusive.
9. All four support views must pass mutual median containment.
10. Rescue to `Range` only if steps 4, 5 and 9 all pass; otherwise remain `Uncertain`.

There is no numeric containment threshold, no weight, no grid and no post-result tuning. Any non-finite or collapsed support fails closed.

Every v0.6.31 change relative to v0.6.25 must be exactly `Uncertain -> Range`; any other change invalidates the run.

## Frozen promotion gates

v0.6.31 may become the best-supported parent-direction research component only if all are true:

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

Failure leaves the parent-direction winner unset and v0.6.25 remains the strongest pooled-exact contribution. Any validated local contribution may be retained.

Independent morphology acceptance remains false. Trading and production authority remain false.
