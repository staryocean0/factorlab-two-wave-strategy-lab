# Two-Wave v0.6.35 two-cycle Wasserstein Range protocol

Date: 2026-09-11
Status: frozen before replay

## Research question

Can one direct full-distribution distance between the two completed parent cycles identify a smaller and more sampling-stable Range set than the rejected v0.6.33 median-shift and v0.6.34 median/IQR intersection routes?

## Frozen upstream

- parent identity v0.5.2;
- same-scale semantics v0.5.4;
- raw publication v0.6.5;
- qualification champion v0.6.18;
- direction comparison base v0.6.25;
- evaluation universe: the same 1,462 strict same-financial-identity pairs where both views are v0.6.18-qualified;
- the same four v0.6.23 endpoint supports: `full`, `left_eroded_1`, `right_eroded_1`, `both_eroded_1`;
- the sole distance ceiling is `0.15` parent-amplitude units, inherited unchanged from the frozen D1 morphology `phase_tolerance`.

No threshold is fitted or tuned in v0.6.35.

## Sole candidate

Preserve every decisive v0.6.25 output exactly.

Only when v0.6.25 is `Uncertain`, for each frozen support:

1. split the completed parent into cycle 1 `[anchor0, anchor2]` and cycle 2 `[anchor2, anchor4]`;
2. treat all observed closes in each complete cycle as an empirical one-dimensional price distribution;
3. compute empirical Wasserstein-1 distance between the two cycle distributions;
4. divide that distance by the frozen parent `amplitude_unit_price`;
5. require normalized W1 `<= 0.15` on all four supports.

Rescue exactly to `Range` only when all four supports pass; otherwise remain `Uncertain`.

v0.6.35 does not use Huber Range margin, cycle-IQR overlap, mutual-median containment, containment slack, cross-offset runtime information, future outcomes, or trading/PnL data.

## Hard invariants

- qualification remains v0.6.18;
- D1/v0.6.25 decisive override count equals zero;
- every changed label is exactly `Uncertain -> Range`;
- no future return, P&L, H1/H2, third wave, 2021+, or 2026 data is used for selection.

## Frozen promotion gate vs v0.6.25

All must pass:

1. all four per-offset exact four-state agreement values are non-worse than v0.6.25;
2. pooled exact agreement improves by at least `0.20 percentage points`;
3. pooled decisive coverage improves by at least `1.00 percentage point`;
4. pooled decisive agreement is at least `99.5%`;
5. opposite UpTrend/DownTrend conflicts remain zero;
6. pooled decisive shares keep UpTrend >=15%, DownTrend >=15%, Range >=2%;
7. D1/v0.6.25 decisive override count equals zero.

Failure leaves the direction winner unset and v0.6.25 unchanged as the strongest pooled-exact contribution unless a later preregistered candidate passes all gates.

Independent morphology acceptance remains false. Trading and production remain closed.
