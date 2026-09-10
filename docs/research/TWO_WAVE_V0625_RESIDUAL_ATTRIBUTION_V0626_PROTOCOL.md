# Two-Wave v0.6.26 v0.6.25 residual direction attribution protocol

Date: 2026-09-10
Status: `frozen_before_v0626_attribution`

## Purpose

v0.6.26 is diagnostic only. It changes no parent identity, qualification, direction rule, Huber estimator, erosion support, state threshold, or v0.6.25 margin threshold.

It asks why v0.6.25 improved pooled exact agreement above D1 while still failing the all-offset non-regression gate and the Range diversity floor.

## Frozen inputs

Use only:

- v0.6.18 frozen identity/qualification artifacts from workflow run `34423674192`;
- native 5m development views `5m_offset_0..4`, 2015-01-05..2020-12-31;
- frozen D1 baseline;
- frozen v0.6.23 endpoint-erosion consensus rescue;
- frozen v0.6.25 margin gate `consensus_margin >= 0.10`.

No future return, PnL, H1/H2, third wave, 2021+, or 2026 data may enter.

## Required control reproduction

Before interpretation reproduce exactly:

- filtered mutual-unique pairs: `57,029`;
- raw strict same-event pairs: `29,453`;
- both-v0.6.18-qualified direction pairs: `1,462`;
- D1 exact: `1,400/1,462`;
- v0.6.23 exact: `1,397/1,462`;
- v0.6.25 exact: `1,402/1,462`;
- D1 pooled decisive coverage: `0.4890560875512996`;
- v0.6.25 pooled decisive coverage: `0.7086183310533516`;
- v0.6.25 decisive agreement: `1.0`;
- v0.6.25 opposite Up/Down conflicts: `0`.

Any mismatch invalidates the diagnostic.

## Frozen decomposition

For each offset pair, classify the D1 -> v0.6.25 change into exactly one of:

- `retained_exact`: D1 exact and v0.6.25 exact;
- `introduced_harm`: D1 exact and v0.6.25 nonexact;
- `repaired_old_nonexact`: D1 nonexact and v0.6.25 exact;
- `persistent_nonexact`: D1 nonexact and v0.6.25 nonexact.

For nonexact/repaired pairs record:

- offset;
- D1 pair topology;
- v0.6.25 rescue topology: main-only / other-only / both / neither;
- rescue state: Range / UpTrend / DownTrend;
- single-view v0.6.23 consensus margin on each rescued or margin-withheld side.

## Margin-geometry attribution

Across all v0.6.18-qualified single-view records where D1 is `Uncertain` and v0.6.23 would rescue decisively, report separately by consensus state:

- total v0.6.23 rescue candidates;
- number kept by v0.6.25 (`margin >= 0.10`);
- number withheld;
- keep fraction;
- margin quantiles for all / kept / withheld.

For Range only, also report `margin / 0.15`, because `0.15` is the maximum possible Range margin to the frozen Range boundary. This is a diagnostic geometry ratio, not a runtime feature or candidate rule.

Do not invent a corresponding bounded denominator for Trend: trend margin above `0.50` is not upper-bounded by the frozen state geometry.

## Frozen attribution verdict

Before any v0.6.26 result is read, define:

- `range_keep_fraction` = kept Range rescues / all v0.6.23 Range rescue candidates;
- `trend_keep_fraction` = kept UpTrend+DownTrend rescues / all v0.6.23 UpTrend+DownTrend rescue candidates;
- `introduced_harm_one_sided_fraction` = introduced-harm pairs whose v0.6.25 rescue topology is main-only or other-only / all introduced-harm pairs.

Return `v0626_absolute_margin_geometry_is_state_asymmetric` only if BOTH hold:

1. `range_keep_fraction <= 0.5 * trend_keep_fraction`;
2. `introduced_harm_one_sided_fraction >= 0.80`.

Otherwise return `v0626_residual_harm_not_explained_by_margin_geometry`.

These thresholds are attribution gates only. They do not authorize a runtime threshold and may not be tuned after results.

No direction winner, threshold change, or authority promotion follows from v0.6.26 alone.

If the first conclusion holds, the next version may preregister one state-geometry-aware single-view confidence rule. It may not tune by offset and may not reuse cross-offset pair topology at runtime.

Global morphology acceptance remains false. Trade and production authority remain false.
