# Two-Wave v0.6.21 Whole-Window Huber Direction — Frozen Protocol

Date: 2026-09-10
Status: `frozen_before_v0621_direction_replay`

## Question

Can the already-confirmed two-complete-wave parent window be classified more stably as `Range / UpTrend / DownTrend / Uncertain` by a robust whole-window centerline, without changing parent identity or the current v0.6.18 qualification policy?

This version changes only the parent direction/state component. It does not change pivot confirmation, exact-ridge parent identity, raw publication, qualification, overlap ownership, or any trading layer.

## Frozen upstream

Unchanged:

- v0.5.2 exact-ridge parent identity;
- v0.6.5 immutable first-valid raw publication;
- v0.6.18 qualification-policy champion;
- v0.6.0/v0.6.1 strict same-financial-identity audit matcher;
- development data `5m_offset_0 ... 5m_offset_4`, 2015-01-05 through 2020-12-31 only;
- no future returns, PnL, third-wave outcome, H1/H2 or human labels.

Only records qualified by v0.6.18 are eligible for direction evaluation.

## Baseline diagnostic

Historical D1 remains the comparison baseline only. D1 is not a truth label and cannot provide training targets.

For each v0.6.18-qualified published raw identity, reconstruct the frozen five-pivot pair geometry with the same observed closes and read `direction_versions['D1']`.

## Single preregistered challenger

`v0621_whole_window_huber_centerline`

For the complete raw parent window from first to fifth published occurrence anchor inclusive:

1. use every observed close in that completed parent window;
2. normalize bar position to `x in [-0.5, +0.5]`;
3. fit a deterministic Huber robust linear centerline by IRLS;
4. Huber tuning constant is fixed at `1.345` (standard robust-regression constant), with exactly 8 IRLS iterations;
5. residual scale is `1.4826 * median(|residual - median(residual)|)` with an epsilon floor;
6. total fitted centerline drift across the parent window equals fitted slope because normalized x spans one unit;
7. normalize total fitted drift by the same frozen two-cycle `amplitude_unit_price` used by `evaluate_pair`.

No candidate menu and no fitted parameter.

### Frozen state mapping

Reuse the pre-existing M0 semantic magnitudes; do not tune them:

- normalized score `>= +0.50` -> `uptrend`;
- normalized score `<= -0.50` -> `downtrend`;
- `abs(score) <= 0.15` -> `range`;
- otherwise -> `uncertain`.

This is not endpoint D2 and not PAWCT: it fits one robust low-frequency centerline to all closes in the entire completed parent span and does not compare two endpoint translations or phase-align cycle paths.

## Frozen evaluation universe

Use the exact v0.6.18 row-level artifacts from workflow run `34423674192` and reproduce:

- filtered mutual-unique pairs: `57,029`;
- published raw strict pairs: `29,453`;
- v0.6.18 candidate matrix: `bothQ=1,462 / bothRejected=27,315 / mainOnlyQ=386 / otherOnlyQ=290`.

Direction cross-view evaluation is restricted to the `1,462` strict same-financial-identity pairs where **both sides are v0.6.18-qualified**.

No cross-view information is available to either D1 or the v0.6.21 challenger at runtime; cross-view pairing is evaluation only.

## Metrics

For D1 and challenger, pooled and per offset report:

- exact four-state agreement on both-qualified same-event pairs;
- decisive agreement conditional on neither side being `uncertain`;
- opposite-trend conflict (`uptrend` vs `downtrend`);
- decisive coverage on each view (`label != uncertain`);
- label counts/shares on each view and pooled sides.

## Frozen promotion gate

The challenger becomes the best-supported **direction research component** only if all conditions hold:

1. exact four-state agreement is not lower than D1 on each of all four offsets;
2. pooled exact agreement improves over D1 by at least `+3.0 percentage points`;
3. pooled opposite-trend conflict is not higher than D1;
4. pooled decisive coverage is at least `50%` and is not more than `2 percentage points` below D1;
5. on every offset-side view, decisive coverage is at least `40%`;
6. among pooled decisive challenger labels, both `uptrend` and `downtrend` each account for at least `15%`, and `range` accounts for at least `2%`;
7. all upstream identity, qualification and no-future-outcome controls reproduce exactly.

These anti-degeneracy gates prevent all-`Uncertain` and all-one-class solutions. They do not constitute morphology truth.

If all pass: `v0621_whole_window_huber_direction_research_component_pass`.
Otherwise: `v0621_whole_window_huber_direction_rejected` and no direction component is promoted.

## Scientific boundary

Even a pass does **not** establish independent morphology acceptance because there are still no independent human morphology labels. It may only become the current best-supported direction/state **research component**.

Qualification champion remains v0.6.18 regardless of this result.

`future_outcome_used=false`
`trade_authority=false`
`production_authority=false`
