# Two-Wave v0.6.34 two-cycle distribution intersection protocol

Date: 2026-09-10
Status: frozen before replay

## Research question

Can two already-supported but individually over-permissive direct Range measurements be intersected to identify a smaller, more sampling-stable set of Range states?

## Frozen upstream

- qualification champion v0.6.18;
- direction baseline contribution v0.6.25;
- same 1,462 strict same-financial-identity both-qualified pairs for evaluation;
- v0.6.33 direct cycle-median location shift threshold stays exactly `0.15` amplitude units;
- v0.6.29 cycle-IQR overlap threshold stays exactly `0.50`;
- the four v0.6.23 endpoint supports stay `full`, `left_eroded_1`, `right_eroded_1`, `both_eroded_1`.

No threshold is tuned in v0.6.34.

## Sole candidate

Preserve every decisive v0.6.25 output exactly.

Only when v0.6.25 is `Uncertain`, for each of the four frozen supports:

1. require `abs(median(cycle2)-median(cycle1))/amplitude_unit_price <= 0.15`;
2. require cycle-1 / cycle-2 IQR overlap coefficient `>= 0.50`;
3. require both conditions on the same support.

Rescue to `Range` only if all four supports pass both direct distribution conditions. Otherwise remain `Uncertain`.

No Huber Range consensus, Huber Range margin, mutual-median containment, containment slack or cross-offset runtime feature is used.

## Hard invariants

- qualification remains v0.6.18;
- D1/v0.6.25 decisive override count is zero;
- all changes are exactly `Uncertain -> Range`;
- no future return, P&L, H1/H2, third wave or trading outcome is read.

## Frozen promotion gate vs v0.6.25

All must pass:

- every offset exact agreement non-worse;
- pooled exact agreement improves by >=0.20 percentage points;
- pooled decisive coverage improves by >=1.00 percentage point;
- pooled decisive agreement >=99.5%;
- opposite UpTrend/DownTrend conflicts remain zero;
- decisive shares: UpTrend >=15%, DownTrend >=15%, Range >=2%;
- decisive override count zero.

If rejected, v0.6.25 remains strongest pooled-exact direction contribution unless a later formally preregistered candidate surpasses it. Global morphology acceptance remains false; trading and production remain closed.
