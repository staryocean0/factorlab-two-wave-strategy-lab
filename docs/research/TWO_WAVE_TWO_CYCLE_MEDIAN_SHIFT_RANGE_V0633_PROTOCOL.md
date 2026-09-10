# Two-Wave v0.6.33 two-cycle median-shift Range protocol

Date: 2026-09-10
Status: frozen before replay

## Research question

Can a direct two-complete-cycle robust location-shift measurement recover stable Range states that v0.6.25 leaves Uncertain, without reusing the sampling-sensitive Huber Range margin or v0.6.31 containment-depth logic?

## Frozen upstream

- parent identity: v0.5.2;
- same-scale semantics: v0.5.4;
- raw publication: v0.6.5;
- qualification champion: v0.6.18;
- direction baseline contribution: v0.6.25;
- evaluation universe: the same 1,462 strict same-financial-identity pairs where both views are v0.6.18-qualified;
- cross-offset information is evaluation-only and is never a runtime feature.

## Sole candidate

Preserve v0.6.25 exactly whenever it returns `range`, `uptrend`, or `downtrend`.

Only when v0.6.25 returns `uncertain`:

1. use the same four frozen v0.6.23 endpoint supports: `full`, `left_eroded_1`, `right_eroded_1`, `both_eroded_1`;
2. on each support, split the completed parent into cycle 1 `[anchor0, anchor2]` and cycle 2 `[anchor2, anchor4]`;
3. compute each cycle's median close;
4. compute normalized location shift `abs(median_cycle2 - median_cycle1) / amplitude_unit_price`;
5. require the normalized shift to be `<= 0.15` on **all four** supports;
6. if all four pass, rescue exactly to `Range`; otherwise remain `Uncertain`.

The threshold `0.15` is inherited unchanged from the frozen D1 `phase_tolerance`; it is not selected from v0.6.33 outcomes. There is no parameter menu and no post-result threshold expansion.

v0.6.33 does **not** require Huber Range consensus, v0.6.27 Range margin, cycle-IQR overlap, mutual-median containment, or containment slack.

## Invariants

- D1/v0.6.25 decisive output override count must equal zero.
- Every changed label must be exactly `Uncertain -> Range`.
- qualification remains v0.6.18.
- no future return, P&L, H1/H2, third-wave or trading outcome is read.
- no 2021+, 2025 or 2026 data is introduced for selection.

## Frozen promotion gate vs v0.6.25

All must pass:

1. all four per-offset exact four-state agreement values are non-worse than v0.6.25;
2. pooled exact agreement improves by at least `0.20 percentage points`;
3. pooled decisive coverage improves by at least `1.00 percentage point`;
4. pooled decisive agreement is at least `99.5%`;
5. opposite UpTrend/DownTrend conflicts remain zero;
6. pooled decisive label shares keep UpTrend >=15%, DownTrend >=15%, Range >=2%;
7. D1/v0.6.25 decisive override count is zero.

Failure leaves parent-direction winner unset and v0.6.25 unchanged as the strongest pooled-exact contribution unless the observed result itself exceeds it on that descriptive metric; no automatic authority change follows a failed promotion gate.

Global morphology acceptance remains false. Trading and production authority remain false.
