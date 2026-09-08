# R2 preanalysis — Range-boundary / failed-breakout reversion

Date: 2026-09-08  
Identity: `R2_range_boundary_reversion_stage1_v1`

## Question

A parent structure is low-drift / range-like and price moves outside its causal envelope.

Ask:

> **Can we separate temporary overshoot / failed breakout from a genuine transition into a new directional state?**

## Coordinate definition

- parent scale: one predeclared M0 structure scale;
- parent state: continuous range-likeness, not a post-hoc binary range label;
- deviation: first causal excursion beyond the frozen parent boundary/envelope;
- recovery: re-entry into the prior parent envelope before directional extension;
- failure of mean-reversion hypothesis: extension far enough to qualify as a new parent-direction move under the predeclared structural rule;
- ambiguous same-bar order or unresolved path: censored.

Exact field mapping and scale are bound by metadata/schema inspection before outcomes.

## First-pass comparison budget

At most three objects:

1. `excursion_severity_only`;
2. `parent_range_state_only`;
3. `parent_plus_excursion_state`.

The combined object may use only a tiny causal set:

- excursion size normalized by parent width;
- parent absolute drift / overlap / efficiency;
- breakout speed or local path efficiency if already causally available from the frozen M0/path cache.

No alternate range algorithm search in Stage-1 v1.

## Hypotheses

H1. For equal excursion size, stronger range-likeness increases re-entry-before-extension probability.

H2. A genuine transition should differ from a failed breakout in at least one pre-event parent-state or immediate causal breakout descriptor beyond raw excursion magnitude.

H3. The effect direction should be consistent across the 2019 and 2020 chronological check rather than exist only in the pooled sample.

## Evidence roles

- BUILD: 2015–2018 consumed development material;
- chronological check: 2019–2020, not fresh;
- post-2020 unopened for this broad screen.

## Progression condition

Progress only if parent/range information adds stable incremental information beyond excursion severity and sample supply is sufficient across the frozen common scale/view cells.

If only the combined model improves but the parent-range component has no interpretable incremental role, label the mechanism `mixed_hold_not_isolated` rather than claim range mean reversion is proven.

## Forbidden rescue

Do not after results:

- redefine the range until the result passes;
- move envelope thresholds;
- add many volatility filters;
- select only favorable directions/offsets/years;
- change extension or re-entry boundaries;
- choose by PnL.

Failure/ambiguity closes or holds R2 Stage-1 v1.
