# Two-Wave v0.6.39 order-sensitive residual-shape attribution protocol

Date: 2026-09-11
Status: frozen before diagnostic replay

## Purpose

Diagnose whether the remaining one-sided v0.6.37 `Uncertain -> Range` errors contain information in **within-leg path order/shape** that is absent from the order-free location/distribution measurements used by v0.6.29-v0.6.37.

This is diagnostic evidence only. It changes no recognizer, classification, qualification rule, threshold, promotion gate, or authority.

## Frozen residual universe

Use exactly the same 1,462 strict same-financial-identity pairs where both views are v0.6.18-qualified.

Restrict the diagnostic rows to the `44` one-sided v0.6.37 changes versus v0.6.25 identified by v0.6.38:

- `38 introduced_harm`;
- `6 repaired_old_nonexact`;
- `0 persistent_nonexact`.

For each pair, measure only the side whose v0.6.37 label changed from v0.6.25 `Uncertain` to `Range`.

## Frozen phase representation

For each changed-side record, use its published five occurrence bars and raw close path only.

For each of the four legs separately:

1. linearly interpolate the raw leg onto exactly `65` equally spaced phase points, matching the already-historical PAWCT phase-grid resolution so no new resolution parameter is introduced;
2. convert the interpolated leg to a dimensionless progress curve

   `progress(t) = (price(t) - price(start)) / (price(end) - price(start))`;

3. require a finite non-zero endpoint displacement; the curve therefore starts at `0` and ends at `1` for both rising and falling legs.

This removes the leg's absolute price level and its total endpoint displacement before any cross-cycle comparison.

The resulting object is therefore deliberately different from:

- D2 endpoint/envelope translation;
- PAWCT absolute phase-aligned price translation between complete cycles;
- v0.6.10 scalar efficiency, jump-share, total-variation and roughness descriptors;
- v0.6.33-v0.6.37 order-free location/distribution measurements.

## Frozen descriptors

Compare corresponding legs of complete cycle 1 and complete cycle 2:

- `first_leg_progress_l1`: mean absolute pointwise difference between the two first-leg progress curves;
- `second_leg_progress_l1`: mean absolute pointwise difference between the two second-leg progress curves;
- `first_leg_progress_linf`: maximum absolute pointwise difference between the two first-leg progress curves;
- `second_leg_progress_linf`: maximum absolute pointwise difference between the two second-leg progress curves;
- `mean_leg_progress_l1`: arithmetic mean of the two L1 distances;
- `max_leg_progress_l1`: maximum of the two L1 distances;
- `mean_leg_progress_linf`: arithmetic mean of the two L-infinity distances;
- `max_leg_progress_linf`: maximum of the two L-infinity distances.

No other descriptor may be added after seeing the result.

## Frozen reporting

For each descriptor, report separately for `introduced_harm` and `repaired_old_nonexact`:

- count;
- mean;
- median;
- 25th percentile;
- 75th percentile;
- minimum;
- maximum.

Also report one threshold-free rank statistic:

`harm_greater_probability = P(H > R) + 0.5 * P(H = R)`

computed over all harm/repair observation pairs. `0.5` means no rank separation; values above `0.5` mean harmful rescues tend to have larger shape distance; values below `0.5` mean the reverse.

Report the same descriptor summaries by v0.6.38 rescue origin (`shared_bar_equal_and_phase_balanced_rescue` versus `phase_balanced_only_rescue`) only as secondary context; do not fit or choose a subgroup-specific cutoff.

## Hard interpretation constraints

- No threshold search, menu, classifier, logistic model, tree, score, or composite fit.
- No classification changes and no candidate promotion from v0.6.39.
- No use of another offset as runtime information.
- No future return, P&L, H1/H2, third wave, 2021+, or 2026 selection data.
- The six repaired cases are explicitly too small to authorize a shape-distance gate in this diagnostic, irrespective of apparent rank separation.
- Any later recognizer candidate requires a separately frozen mechanism and threshold source before replay.
- v0.6.25 remains the strongest pooled-exact direction contribution unless a later frozen challenger passes the existing promotion gates.
- v0.6.18 remains qualification champion.
- independent morphology acceptance remains false; trading and production remain closed.
