# Two-Wave v0.6.46 Native Open / Body / Gap Direction Attribution — Frozen Protocol

Date: 2026-09-11
Status: `frozen_before_v0646_empirical_attribution`

## 1. Question

v0.6.45 identified one remaining causally available market-price information class omitted by the earlier audit: native `open` at the already-frozen five parent anchor bars.

v0.6.46 asks only:

> Does frozen-anchor open/body/gap geometry contain non-redundant information associated with existing harmless-view direction inconsistency, and is an open-anchor migration representation at least plausibly more harmless-slicing-stable than close-anchor migration?

This is attribution only. It cannot classify, rescue, veto, fit a threshold, alter qualification, or promote a recognizer.

## 2. Frozen universe and hard controls

Reuse only the completed v0.6.18 artifacts from workflow run `34423674192` and the shipped immutable development bars.

Before interpretation reproduce exactly:

- filtered mutual-unique same-event pairs: `57,029`;
- published raw strict pairs: `29,453`;
- both-v0.6.18-qualified pairs: `1,462`;
- D1 exact count: `1,400`;
- v0.6.25 exact count: `1,402`;
- v0.6.25 decisive agreement reference: `1.0`;
- v0.6.25 opposite UpTrend/DownTrend conflicts: `0`.

Any drift invalidates the attribution.

## 3. Frozen information boundary

For each side of every matched pair:

- preserve the published five occurrence bars exactly;
- preserve frozen phase (`low` or `high`);
- reconstruct the frozen v0.6.18 parent only to obtain D1 and the existing amplitude unit;
- read native `open` and `close` only from the five frozen anchor bars;
- for gap descriptors only, read the immediately preceding observed native bar close (`anchor_index - 1`); if any anchor has no preceding observed row, fail closed;
- do not move pivots;
- do not infer intrabar high/low/open/close ordering;
- do not use future bars beyond information already available at the parent confirmation time;
- do not consume comparison-offset identity in any runtime candidate. Cross-offset pairing exists only for stability evaluation.

No high/low value is part of the v0.6.46 primary descriptor menu; v0.6.44 remains a separate closed route.

## 4. Frozen per-side descriptors

Let the five frozen anchor closes be `c0..c4`, opens `o0..o4`, immediately preceding observed closes `p0..p4`, and frozen amplitude unit `A > 0`.

### 4.1 Absolute body geometry

For each anchor:

`body_i = (c_i - o_i) / A`

Record:

- `mean_abs_anchor_body = mean(abs(body_i))`;
- `max_abs_anchor_body = max(abs(body_i))`.

### 4.2 Phase-oriented body geometry

For a frozen low anchor, outward direction is downward; for a frozen high anchor, outward direction is upward.

Define orientation `q_i = -1` for low anchors and `+1` for high anchors.

`oriented_body_i = q_i * (c_i - o_i) / A`

Positive values mean the anchor close finished farther in the phase-consistent outward direction than its bar open.

Record:

- `mean_oriented_anchor_body`;
- `positive_oriented_body_fraction` over the five anchors.

### 4.3 Opening-gap geometry

`gap_i = (o_i - p_i) / A`

Record:

- `mean_abs_anchor_gap = mean(abs(gap_i))`;
- `max_abs_anchor_gap = max(abs(gap_i))`.

This is observed bar-boundary price displacement only; no claim is made about economic execution or overnight tradability.

### 4.4 Open-anchor phase migration

Using the same D1 phase relationships, define:

- `open_s0 = (o2 - o0) / A`;
- `open_s1 = (o4 - o2) / A`;
- `open_s2 = (o3 - o1) / A`.

Frozen close migration is reconstructed identically from closes:

- `close_s0 = (c2 - c0) / A`;
- `close_s1 = (c4 - c2) / A`;
- `close_s2 = (c3 - c1) / A`.

Record:

- `open_migration_l1 = mean(abs(open_s0), abs(open_s1), abs(open_s2))`;
- `close_migration_l1`;
- `open_adjustment_vector = open_steps - close_steps`;
- `open_adjustment_l1 = mean(abs(open_adjustment_vector))`;
- `open_adjustment_linf = max(abs(open_adjustment_vector))`.

No threshold or sign rule is applied.

## 5. Frozen harmless-pair stability descriptors

For each matched main-vs-other harmless pair, calculate:

- `close_step_view_distance_l1`: mean absolute difference between the three close phase-step vectors;
- `open_step_view_distance_l1`: mean absolute difference between the three open phase-step vectors;
- `open_stability_gain_l1 = close_step_view_distance_l1 - open_step_view_distance_l1`;
- `open_adjustment_view_distance_l1`: mean absolute difference between the two open-adjustment vectors;
- `mean_abs_body_view_delta`: absolute difference in `mean_abs_anchor_body`;
- `mean_oriented_body_view_delta`: absolute difference in `mean_oriented_anchor_body`;
- `mean_abs_gap_view_delta`: absolute difference in `mean_abs_anchor_gap`.

Positive `open_stability_gain_l1` means open-anchor phase migration is more cross-offset stable than close-anchor phase migration for that matched pair.

## 6. Frozen pair-level scalar rule

When comparing exact and non-exact groups for a per-side descriptor, use the arithmetic mean of main and other side values. Do not choose max/min after seeing results.

For pair stability descriptors, use the directly defined pair value.

## 7. Frozen groupings

Report the fixed descriptor menu for:

1. all `1,462` pairs;
2. D1 exact (`1,400`) vs D1 non-exact (`62`);
3. v0.6.25 exact (`1,402`) vs v0.6.25 non-exact (`60`);
4. each harmless offset separately for v0.6.25 exact/non-exact descriptive medians.

Primary governance readout uses v0.6.25 exact vs non-exact because v0.6.25 is the strongest retained direction contribution.

## 8. Frozen threshold-free primary comparisons

Compute tie-aware `P(nonexact > exact)` for v0.6.25 groups for exactly these five quantities:

1. pair-mean `mean_abs_anchor_body`;
2. pair-mean absolute `mean_oriented_anchor_body` magnitude;
3. pair-mean `mean_abs_anchor_gap`;
4. `open_adjustment_view_distance_l1`;
5. `open_stability_gain_l1`.

Also report:

- pooled median `open_stability_gain_l1` in exact/non-exact groups;
- positive stability-gain fraction in exact/non-exact groups;
- per-offset exact/non-exact median stability gain.

No additional descriptor may be promoted to a primary result after inspection.

## 9. Frozen interpretation categories

After hard controls pass, assign exactly one category.

### A. `v0646_native_open_body_gap_redundant_or_unstable`

Use this category if either:

- all five primary rank probabilities lie within `[0.40, 0.60]`; or
- `open_stability_gain_l1` has inconsistent sign across harmless offsets such that the v0.6.25 non-exact median is positive on fewer than 3 of 4 offsets.

Consequence: close the native-open route; no challenger authorized.

### B. `v0646_native_open_information_nonredundant_but_not_stability_improving`

Use this category when at least one primary rank probability lies outside `[0.40, 0.60]`, but the v0.6.25 non-exact stability-gain median is not positive on at least 3 of 4 offsets.

Consequence: retain information contribution only; no challenger authorized.

### C. `v0646_native_open_information_coherent_candidate_mechanism`

Use this category only when both are true:

- at least two primary rank probabilities are outside `[0.35, 0.65]` in a coherent direction; and
- v0.6.25 non-exact `open_stability_gain_l1` median is positive on all 4 harmless offsets.

Even category C does not promote a recognizer. It authorizes only a separately frozen later candidate protocol based on a natural open/body/gap mechanism with no fitted cutoff from this attribution.

If category conditions overlap, choose the first applicable category in A -> B -> C order.

## 10. Outputs

Persist:

- `summary.json` with controls, fixed statistics and no post-hoc fitted rule;
- `RESULT_CARD.md`;
- compressed pair-level diagnostic rows;
- a governance adjudication record assigning the pre-frozen category after the result exists.

## 11. Authority boundaries

`recognizer_changed=false`

`qualification_changed=false`

`direction_winner_changed=false`

`gate_authorized=false`

`morphology_acceptance=false`

`trade_authority=false`

`production_authority=false`
