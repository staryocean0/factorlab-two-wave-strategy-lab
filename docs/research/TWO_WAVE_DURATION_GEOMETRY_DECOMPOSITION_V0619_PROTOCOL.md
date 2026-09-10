# Two-Wave v0.6.19 Duration-Geometry Disagreement Decomposition — Frozen Protocol

Date: 2026-09-10
Status: `frozen_before_v0619_row_level_decomposition`

## 1. Question

v0.6.18 passed its frozen qualification-policy gate after demoting only `inefficient_leg` and `jump_dominated_leg` from hard vetoes to diagnostics. The current best qualification component is therefore v0.6.18, while global morphology acceptance remains false.

v0.6.19 changes **no recognizer rule**. It asks only:

> On the exact v0.6.18 frozen strict same-event universe, what mechanisms explain the remaining qualification disagreements, and specifically are local duration-geometry disagreements mainly harmless one-native-bar slicing boundary effects or materially larger parent-scale differences?

No duration threshold may be changed in this version.

## 2. Frozen input

Use only row-level artifacts from the completed v0.6.18 workflow run `34423674192`:

- offset0 artifact `10132007935`, digest `sha256:f2dba867d5f6e60db7d308c1ce603afd8586caf30c092f30c696c041be48bdaf`
- offset1 artifact `10132046343`, digest `sha256:07dc5aafa16599a7db84834ef88391d454646ecca6af71624d252cf73de5218d`
- offset2 artifact `10132056291`, digest `sha256:ac89ebb80c0896761ce6a70d15cbfd391c8141c84c30e159dede12cb6c45068c`
- offset3 artifact `10132017437`, digest `sha256:9d8dafbba102f8e7e52433eef4c005f4804f6aeb61f33f5c7c893687b54f316d`
- offset4 artifact `10132055670`, digest `sha256:9b4422e603fc228120359925bccda937365f2154dc554df456dc1b53493538af`

The artifacts were generated from the same v0.6.18 frozen implementation and preserve all published rows plus the complete canonical filtered-identity universe.

No market replay, resampling, outcome data or alternative matcher is authorized.

## 3. Hard-control reproduction

Before interpretation, reproduce exactly:

### 3.1 Filtered mutual-unique same-event pairs

`14,784 / 12,725 / 13,412 / 16,108 = 57,029`

using the frozen v0.6.0/v0.6.1 filtered-first mutual-unique semantics.

### 3.2 Published raw strict pairs

`8,381 / 5,770 / 6,204 / 9,098 = 29,453`.

### 3.3 v0.6.18 candidate qualification matrix

Aggregate:

- both qualified = `1,462`
- both rejected = `27,315`
- main-only qualified = `386`
- other-only qualified = `290`
- disagreements = `676`
- positive overlap = `68.38166510757717%`

Any hard-control drift makes the v0.6.19 execution invalid.

## 4. Frozen hard-reason families

For each of the 676 v0.6.18 qualification-disagreement pairs, inspect only the candidate hard reasons on the rejected side.

Families:

### A. local duration geometry

- `short_leg`
- `short_cycle`
- `cycle_duration_mismatch`

### B. amplitude

- `amplitude_mismatch`

### C. confirmation clock

- `confirmation_too_late`

### D. long-span safety

- `long_cycle`
- `long_pair`
- `too_many_observed_days`
- `wall_span_too_long`

A disagreement is `*_only` when all rejected-side hard reasons belong to exactly one family. If reasons span more than one family, classify it as `mixed_multi_family` and separately record all involved families.

No reason is removed or reweighted here.

## 5. Frozen duration measurements

Use only each published raw five-anchor identity already contained in the artifact.

For raw bars `i0<i1<i2<i3<i4`:

- legs = `[i1-i0, i2-i1, i3-i2, i4-i3]`
- cycles = `[i2-i0, i4-i2]`
- minimum leg = `min(legs)`
- minimum cycle = `min(cycles)`
- cycle-duration ratio = `max(cycles)/min(cycles)`

Frozen v0.4.3 thresholds remain descriptive references only:

- `min_leg = 4`
- `min_cycle = 12`
- `max_cycle = 48`
- `max_pair = 96`
- `duration_ratio = 2.0`
- `max_confirmation_delay = 8`

No new threshold is fitted.

## 6. Frozen boundary-effect diagnostics

For each disagreement involving local duration geometry, record:

1. `max_abs_leg_duration_delta` between the two strict same-event views;
2. `max_abs_cycle_duration_delta`;
3. rejected-side and qualified-side minimum leg;
4. rejected-side and qualified-side minimum cycle;
5. rejected-side and qualified-side cycle-duration ratio;
6. orientation (`main_qualified_other_rejected` or reverse).

Predefined reason-level boundary flags:

- `short_leg_one_bar_boundary`: rejected minimum leg is exactly `3` while qualified minimum leg is at least `4`;
- `short_cycle_one_bar_boundary`: rejected minimum cycle is exactly `11` while qualified minimum cycle is at least `12`;
- `cycle_ratio_one_bar_boundary`: the rejected side exceeds ratio `2.0`, the qualified side is `<=2.0`, and each corresponding full-cycle duration differs by at most one native bar across the two views.

A local-duration disagreement is `simple_one_bar_boundary_case=true` if every local-duration hard reason present in that rejected row satisfies its corresponding predefined boundary flag. Mixed cases keep the flag as a diagnostic but do not enter the `local_duration_only` denominator.

## 7. Decisive decomposition outputs

Report, pooled and per offset:

- primary family counts/fractions;
- any-family involvement counts/fractions;
- local-duration-only count;
- local-duration-only simple-one-bar-boundary fraction;
- reason-level one-bar-boundary fractions;
- quantiles of leg/cycle duration deltas and cycle-ratio margins;
- orientation counts;
- whether long-span safety reasons are materially involved.

Do not use D1/D2/PAWCT, direction labels, returns, outcomes, PnL or human morphology labels in this decomposition.

## 8. Frozen interpretation categories

After all hard controls pass, assign exactly one category:

1. `v0619_local_duration_boundary_sensitivity_dominant`
   - local-duration family involved in at least 50% of the 676 disagreements; and
   - at least 60% of `local_duration_only` disagreements are simple one-bar boundary cases.

2. `v0619_local_duration_geometry_material_not_simple_boundary`
   - local-duration family involved in at least 50%; but
   - the simple-one-bar fraction among `local_duration_only` is below 60%.

3. `v0619_duration_not_dominant_after_v0618`
   - local-duration family involved in less than 50%.

These categories are attribution only, not recognizer promotion.

## 9. Consequences

- v0.6.18 remains the current best qualification component regardless of v0.6.19 category.
- v0.6.19 cannot modify the full-recognizer v0.4.3 baseline or global morphology acceptance.
- No duration rule is promoted from this version.
- If category 1 occurs, the next version may preregister one narrow duration-boundary repair candidate.
- If category 2 occurs, the next step must model/redefine duration geometry rather than simply add one bar to a threshold.
- If category 3 occurs, duration tuning is deprioritized and the largest remaining family becomes the next audit target.

Direction/state classification remains frozen in all cases.

`trade_authority=false`
`production_authority=false`
