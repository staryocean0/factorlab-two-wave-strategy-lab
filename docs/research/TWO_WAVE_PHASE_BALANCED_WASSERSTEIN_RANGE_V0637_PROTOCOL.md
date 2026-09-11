# Two-Wave v0.6.37 phase-balanced Wasserstein Range protocol

Date: 2026-09-11
Status: frozen before replay

## Motivation

v0.6.35 showed that full empirical two-cycle Wasserstein-1 distance is a materially better Range measurement than median-shift or median/IQR gate stacking, but it still loses cross-slicing exact agreement. v0.6.36 does not authorize nearby W1-margin tuning.

The v0.6.35 empirical distribution weights every observed 5m close equally. Therefore, within one complete cycle, a longer first or second leg receives more probability mass merely because it contains more sampled bars. Historical v0.5.4 evidence already established that corresponding half-leg duration allocation is diagnostic rather than a hard parent-scale semantic constraint.

v0.6.37 changes the **measurement weighting**, not the W1 threshold.

## Frozen upstream

- parent identity v0.5.2;
- same-scale semantics v0.5.4;
- raw publication v0.6.5;
- qualification champion v0.6.18;
- direction comparison base v0.6.25;
- evaluation universe: the same 1,462 strict same-financial-identity pairs where both views are v0.6.18-qualified;
- same four v0.6.23 endpoint supports: `full`, `left_eroded_1`, `right_eroded_1`, `both_eroded_1`;
- W1 ceiling remains exactly `0.15` parent-amplitude units, inherited from the frozen morphology tolerance;
- no W1 margin, no threshold menu, no fitted cutoff.

## Sole candidate

Preserve every decisive v0.6.25 output exactly.

Only when v0.6.25 is `Uncertain`, on each frozen endpoint support:

1. split complete cycle 1 into its two observed legs and complete cycle 2 into its two observed legs;
2. build each cycle's empirical price distribution as an equal mixture of its two leg distributions:
   - first leg total probability mass = `0.5`;
   - second leg total probability mass = `0.5`;
   - observations within a leg share that leg's mass equally;
3. compute weighted one-dimensional Wasserstein-1 distance between the two phase-balanced cycle distributions;
4. divide by frozen parent `amplitude_unit_price`;
5. require normalized phase-balanced W1 `<= 0.15` on **all four** endpoint supports.

If all four pass, rescue exactly to `Range`; otherwise remain `Uncertain`.

This is not PAWCT: it does not compare phase-indexed translations or align point-by-point cycle paths. It is a distribution distance with equal leg mass designed only to remove duration-allocation weighting from v0.6.35.

## Hard invariants

- qualification remains v0.6.18;
- every decisive v0.6.25 output is preserved exactly;
- every changed label is exactly `Uncertain -> Range`;
- no cross-offset information is a runtime feature;
- no future return, P&L, H1/H2, third wave, 2021+, or 2026 data selects anything.

## Frozen promotion gate vs v0.6.25

All must pass:

1. all four per-offset exact four-state agreements are non-worse than v0.6.25;
2. pooled exact improves by at least `0.20 percentage points`;
3. pooled decisive coverage improves by at least `1.00 percentage point`;
4. pooled decisive agreement >= `99.5%`;
5. opposite UpTrend/DownTrend conflicts remain zero;
6. pooled decisive shares keep UpTrend >=15%, DownTrend >=15%, Range >=2%;
7. decisive v0.6.25 override count equals zero.

Failure leaves the direction winner unset and v0.6.25 unchanged as the strongest pooled-exact contribution.

Independent morphology acceptance remains false. Trading and production remain closed.
