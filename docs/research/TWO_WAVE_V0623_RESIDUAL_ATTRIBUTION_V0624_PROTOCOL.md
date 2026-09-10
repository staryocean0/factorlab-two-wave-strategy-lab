# Two-Wave v0.6.24 v0.6.23 residual direction-attribution protocol

Date: 2026-09-10
Status: `frozen_before_v0624_attribution`

## Purpose

v0.6.23 was rejected, but it materially improved the v0.6.22 rescue trade-off: pooled exact agreement reached 95.5540% versus D1 95.7592%, while decisive coverage remained 78.5568% versus D1 48.9056%, with 100% decisive agreement and zero opposite-trend conflicts. Offsets 2 and 4 improved beyond D1 while offsets 1 and 3 regressed.

v0.6.24 changes no recognizer rule. It asks one diagnostic question needed for the next direct recognizer improvement:

> Which pair-level topology creates the residual v0.6.23 exact-agreement loss, and is that harm associated with a causal single-view property already available inside the recognizer?

This is failure attribution, not a new judge and not a direction candidate.

## Frozen universe and controls

Use exactly the same v0.6.18 artifacts and 2015-01-05..2020-12-31 native 5m development data used by v0.6.23.

Before interpretation reproduce exactly:

- filtered mutual-unique same-event pairs: `57,029`;
- raw strict same-event pairs: `29,453`;
- both-v0.6.18-qualified direction pairs: `1,462`;
- D1 exact agreement: `0.957592339261286` (`1,400/1,462`);
- v0.6.23 exact agreement: `0.9555403556771546` (`1,397/1,462`);
- D1 decisive coverage: `0.4890560875512996`;
- v0.6.23 decisive coverage: `0.7855677154582763`;
- v0.6.23 decisive agreement: `1.0`;
- v0.6.23 opposite-trend conflicts: `0`.

Any control failure invalidates the analysis.

## Frozen pair transition categories

For every one of the 1,462 same-event pairs, compare whether the two views are exact under D1 and under v0.6.23:

1. `retained_exact`: D1 exact and v0.6.23 exact;
2. `introduced_harm`: D1 exact and v0.6.23 non-exact;
3. `repaired_old_nonexact`: D1 non-exact and v0.6.23 exact;
4. `persistent_nonexact`: D1 non-exact and v0.6.23 non-exact.

These four categories must be exhaustive and mutually exclusive.

## Frozen rescue topology

For each pair classify v0.6.23 rescue application by side:

- `neither_rescued`;
- `main_only_rescued`;
- `other_only_rescued`;
- `both_rescued`.

Also classify the D1 pair topology:

- `both_uncertain`;
- `main_uncertain_other_decisive`;
- `main_decisive_other_uncertain`;
- `both_decisive`.

No category is allowed to depend on future outcomes or cross-view information at runtime; this is audit-only attribution.

## Frozen single-view explanatory fields

For every D1-Uncertain side record:

1. compute the existing v0.5.5 `uncertain_subtype` from that side's own D1 geometry;
2. compute the four v0.6.23 Huber support states/scores from that side only;
3. if the side is rescued, compute a non-fitted `consensus_margin_to_frozen_boundary`:
   - UpTrend: `min(support_scores) - 0.50`;
   - DownTrend: `-0.50 - max(support_scores)`;
   - Range: `0.15 - max(abs(support_scores))`;
4. compute `support_score_span = max(scores) - min(scores)`.

These are diagnostics only. v0.6.24 must not choose a new threshold.

## Required result tables

The formal result must report:

- the four pair transition-category counts overall and by offset;
- rescue topology within each transition category;
- D1 topology within each transition category;
- rescued-label counts for `introduced_harm` versus `repaired_old_nonexact`;
- D1 uncertain-subtype counts for rescued sides in `introduced_harm`, `repaired_old_nonexact`, and `retained_exact`;
- quantiles of consensus margin and support-score span for the same groups.

## Interpretation categories

v0.6.24 may state only measured attribution. It may authorize a future v0.6.25 candidate only if a single-view observable pattern is materially concentrated in harm relative to useful rescue. Examples include a D1 uncertain subtype or low consensus-margin/high support-span regime. The actual v0.6.25 rule and any threshold must be preregistered in a new version after this analysis.

v0.6.24 itself changes no direction authority. D1 remains the historical stability baseline and no direction winner exists. v0.6.18 remains qualification champion.

`morphology_acceptance=false`
`trade_authority=false`
`production_authority=false`
