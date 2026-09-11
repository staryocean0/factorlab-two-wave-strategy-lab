# Two-Wave v0.6.40 Leg-Asymmetry and Harmless-Slicing Stability Attribution Protocol

Date: 2026-09-11
Status: frozen before implementation and replay
Mode: read-only diagnostic; no recognizer change

## Purpose

v0.6.39 found that the strongest order-sensitive separation inside the 44 v0.6.37 one-sided residuals was concentrated in the first leg rather than the second leg. The strongest frozen descriptor was `first_leg_progress_l1`, with `P(harm > repair)=0.747807`, while `second_leg_progress_linf` was essentially non-separating. Because the repair subgroup contains only six rows, v0.6.39 explicitly did not authorize a fitted threshold.

v0.6.40 tests a narrower mechanism without fitting any threshold: whether harmful Range rescues are characterized by **leg-location asymmetry** in the already-frozen v0.6.39 progress-shape distances, and whether that asymmetry itself is unstable under harmless 5-minute slicing.

The primary signed quantity is

`A_L1 = first_leg_progress_l1 - second_leg_progress_l1`.

The secondary quantity is

`A_Linf = first_leg_progress_linf - second_leg_progress_linf`.

Zero is not a fitted cutoff. It is the structural equality point where mismatch is equally concentrated across the two legs.

## Frozen universe

The replay must reproduce the same v0.6.18-qualified comparison universe used by v0.6.25-v0.6.39:

- filtered matched pairs: `57,029`;
- published raw strict pairs: `29,453`;
- both-v0.6.18-qualified pairs: `1,462`;
- main view: `5m_offset_0`;
- harmless comparison views: the same four frozen 5-minute offsets.

The v0.6.37 pair-change topology versus v0.6.25 must reproduce exactly:

- `both = 61`;
- `main_only = 23`;
- `other_only = 21`;
- `none = 1,357`.

The diagnostic universe is exactly the `105` rescue-involved pairs:

- `61` `both` pairs, where both harmless slicing views receive the v0.6.37 `Uncertain -> Range` rescue;
- `44` one-sided pairs (`main_only` or `other_only`).

The one-sided semantic decomposition must reproduce v0.6.38/v0.6.39 exactly:

- `introduced_harm = 38`;
- `repaired_old_nonexact = 6`;
- `persistent_nonexact = 0`.

## Frozen shape representation

No new path representation is introduced.

For every side measured, reuse the exact v0.6.39 machinery:

1. use the record's `published_raw_occurrence_bars`;
2. split the two complete cycles into their four observed legs;
3. interpolate each leg to exactly `65` equally spaced phase points;
4. normalize each leg to progress from `0` at its own start to `1` at its own end;
5. compare cycle-1 first leg with cycle-2 first leg and cycle-1 second leg with cycle-2 second leg;
6. compute the already-frozen L1 and L-infinity progress-shape distances.

No interpolation resolution, endpoint rule, normalization rule, or distance definition may be changed after this freeze.

## Frozen primary and secondary quantities

For each side:

- `A_L1 = first_leg_progress_l1 - second_leg_progress_l1` — **primary**;
- `A_Linf = first_leg_progress_linf - second_leg_progress_linf` — secondary.

Interpretation:

- positive `A`: more cycle-to-cycle shape mismatch is concentrated in the first leg;
- negative `A`: more mismatch is concentrated in the second leg;
- zero: equal concentration across legs.

No absolute cutoff other than this structural equality point is permitted.

## Frozen pair-level constructions

### Stable both-rescue pairs

For each of the 61 `both` pairs, compute both sides' asymmetry values and report:

- `main_A_L1`, `other_A_L1`;
- `pair_mean_A_L1 = (main_A_L1 + other_A_L1) / 2`;
- `pair_abs_delta_A_L1 = abs(main_A_L1 - other_A_L1)`;
- corresponding L-infinity quantities;
- whether the two sides have the same sign, treating exact zero as its own structural case.

The `pair_abs_delta` quantities measure harmless-slicing sensitivity of the asymmetry itself.

### One-sided rescue pairs

For each of the 44 one-sided pairs, define:

- `rescue_side`: the side changed by v0.6.37 relative to v0.6.25;
- `nonrescue_side`: the unchanged harmless slicing view;
- `rescue_A_L1`;
- `nonrescue_A_L1`;
- `rescue_minus_nonrescue_A_L1`;
- `pair_abs_delta_A_L1 = abs(rescue_A_L1 - nonrescue_A_L1)`;
- corresponding L-infinity quantities.

Keep the already-frozen semantic label (`introduced_harm` or `repaired_old_nonexact`) and rescue-origin label (`shared_bar_equal_and_phase_balanced_rescue` or `phase_balanced_only_rescue`).

## Frozen reporting

Report numeric summaries (`count`, `mean`, `median`, `q25`, `q75`, `min`, `max`) for:

1. stable both-rescue pair means and pair absolute deltas;
2. one-sided rescue-side, non-rescue-side, signed paired difference, and absolute paired difference;
3. the one-sided quantities split by semantic class;
4. the one-sided quantities split by rescue origin.

Report only threshold-free/nonparametric comparison statistics:

- `P(harm rescue_A_L1 > stable_both pair_mean_A_L1)`;
- `P(harm pair_abs_delta_A_L1 > stable_both pair_abs_delta_A_L1)`;
- the analogous two L-infinity probabilities;
- within each one-sided semantic class, the fraction of rows with `rescue_minus_nonrescue_A_L1 > 0`, `= 0`, and `< 0`;
- the corresponding L-infinity sign fractions.

The six repair rows remain descriptive only. No fitted separator, p-value optimization, resampling-based cutoff, classifier, tree, regression, score combination, or parameter search is allowed.

## Interpretation boundary

v0.6.40 is not a recognizer challenger and cannot itself change any label.

A later v0.6.41 may be preregistered only if this diagnostic provides a coherent structural reason to test a **relative** leg rule whose boundary is inherited from equality (`A=0`), rather than a cutoff estimated from these 105 pairs. Any such v0.6.41 must be separately frozen before replay on the 1,462-pair universe.

Regardless of apparent separation, v0.6.40 does **not** authorize:

- a fitted `first_leg_progress_l1` threshold;
- a fitted `A_L1` or `A_Linf` threshold;
- retuning the v0.6.37 W1 ceiling `0.15`;
- combining v0.6.35 and v0.6.37 by a new ad-hoc consensus rule;
- using harmless comparison offsets as runtime information;
- using future outcome, P&L, H1/H2, third-wave, 2021+, or 2026 selection information.

## Authority held fixed

- qualification champion: v0.6.18;
- strongest pooled-exact direction contribution: v0.6.25;
- parent-direction winner: unset;
- independent morphology acceptance: false;
- trade authority: false;
- production authority: false.
