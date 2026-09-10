# Two-Wave v0.6.25 D1-primary erosion-consensus Huber margin rescue protocol

Date: 2026-09-10
Status: `frozen_before_v0625_replay`

## Development evidence consumed before this version

v0.6.24 is development evidence, not fresh OOS. It decomposed v0.6.23 into 1,350 retained-exact pairs, 50 introduced-harm pairs, 47 repaired-old-nonexact pairs, and 15 persistent-nonexact pairs. Every introduced harm began with D1=`Uncertain` on both harmless slicing views and exactly one side being rescued.

The strongest single-view separation was the already-defined v0.6.23 consensus margin to the frozen Huber state boundary:

- introduced harm: median `0.02786`, p90 `0.08200`;
- repaired old nonexact: median `0.28769`, p25 `0.12734`;
- retained exact rescued sides: median `0.42190`, p25 `0.11791`.

Therefore this new version preregisters exactly one margin threshold, `0.10` amplitude units. No threshold menu or post-result search is allowed.

## Frozen upstream

Unchanged:

- v0.5.2 parent identity;
- v0.6.5 immutable raw publication;
- v0.6.18 qualification-policy champion;
- D1 historical direction baseline;
- v0.6.21 Huber estimator and state thresholds `0.15 / 0.50`;
- v0.6.23 four support views: full, left-eroded-1, right-eroded-1, both-eroded-1;
- v0.6.23 unanimous decisive erosion-consensus requirement.

No future returns, PnL, H1/H2, third wave, 2021+, or 2026 data may enter construction or selection.

## Sole candidate

For each v0.6.18-qualified parent identity:

1. if D1 is `Range`, `UpTrend`, or `DownTrend`, output D1 exactly;
2. if D1 is `Uncertain`, compute the frozen v0.6.23 erosion-consensus Huber state;
3. if the four support views are not unanimous in one decisive state, remain `Uncertain`;
4. if they are unanimous decisive, compute the frozen v0.6.24 consensus margin:
   - UpTrend: `min(support_scores) - 0.50`;
   - DownTrend: `-0.50 - max(support_scores)`;
   - Range: `0.15 - max(abs(support_scores))`;
5. rescue D1 uncertainty only when `consensus_margin >= 0.10`.

No support-score averaging, no majority vote, no subtype gate, no support-span gate, and no second margin threshold are allowed.

## Frozen evaluation universe and controls

Use only run `34423674192` v0.6.18 artifacts and 2015-01-05..2020-12-31 native 5m development data.

Before interpretation reproduce exactly:

- filtered pairs `57,029`;
- raw strict pairs `29,453`;
- both-v0.6.18-qualified direction pairs `1,462`;
- D1 exact `1,400/1,462 = 0.957592339261286`;
- D1 decisive coverage `0.4890560875512996`;
- D1 decisive agreement `1.0`;
- D1 opposite-trend conflicts `0`;
- v0.6.23 exact `1,397/1,462 = 0.9555403556771546` when the margin gate is disabled.

## Hard implementation gates

1. D1 decisive override count must be `0`;
2. v0.6.23 erosion-consensus semantics must be reused unchanged;
3. only the new `consensus_margin >= 0.10` condition may withhold an otherwise-v0.6.23 rescue;
4. identity, qualification, confirmation and amplitude unit remain unchanged;
5. cross-offset counterpart data is evaluation-only;
6. `future_outcome_used=false`, `trade_authority=false`, `production_authority=false`.

## Frozen promotion gate against D1

v0.6.25 becomes the first current best-supported **research direction component** only if ALL hold:

1. exact four-state agreement is not lower than D1 on each of all four offsets;
2. pooled exact agreement is not lower than D1;
3. pooled decisive coverage is at least `0.65` and at least D1 + `0.15`;
4. each offset on each side has decisive coverage at least `0.55`;
5. pooled decisive agreement when both sides are decisive is at least `0.995`;
6. opposite UpTrend/DownTrend conflict count is exactly `0`;
7. pooled decisive label shares satisfy `uptrend>=0.15`, `downtrend>=0.15`, `range>=0.02`;
8. at least one D1-Uncertain record is rescued.

If all pass: `v0625_D1_primary_erosion_consensus_margin_rescue_direction_research_component_pass`.
Otherwise: `v0625_D1_primary_erosion_consensus_margin_rescue_direction_rejected`; D1 remains the historical stability baseline and no direction winner is installed.

## Forbidden rescue

After results, do not change `0.10` to another number inside v0.6.25, add a grid, use v0.6.24 pair topology at runtime, or tune by offset. Any follow-up must be a new preregistered version.

Global morphology acceptance remains false even if this research component passes. No trading or production authority follows.
