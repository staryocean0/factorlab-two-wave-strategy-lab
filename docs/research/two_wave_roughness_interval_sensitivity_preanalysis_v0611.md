# v0.6.11 Preanalysis — endpoint/interval sensitivity of fine-path roughness

Date: 2026-09-07

Status: **WRITTEN BEFORE ANY v0.6.11 REAL-DATA OUTPUT IS READ**

## 1. Why this audit is authorized

v0.6.10 found that supplied-1m concentration and the five-origin concentration ensemble materially reduce native-J5 bar-origin aliasing, but `fine_roughness = log(TV1/D)` is *less* stable across already-frozen strict same-event pairs than native `-log(E5)`.

Frozen v0.6.10 aggregate controls:

```text
published raw strict pairs = 8,381 / 5,770 / 6,204 / 9,098 = 29,453
pair-leg observations used by the property audit = 117,805
native roughness abs-diff median = 0.021658
fine roughness abs-diff median   = 0.083145
fine roughness larger than native roughness difference = 75,389 / 117,805
```

The two sides of a strict financial-event pair may still have corresponding published raw leg endpoints displaced by up to the already-frozen one-native-bar locality relation. Because both sides read the same supplied 1m path, the remaining fine-roughness discrepancy is an interval-definition problem, not a sampling-resolution problem.

This authorizes an **interval-sensitivity audit only**. It does not authorize changing financial identity, the 5-minute same-event relation, qualification thresholds, direction or outcomes.

## 2. Separate workstreams

v0.6.11 addresses only roughness endpoint sensitivity.

The separate question — how to construct a native-5m deployable proxy for the already-promising fine concentration/origin ensemble — is explicitly deferred to a later version. No combined roughness+concentration repair is allowed in v0.6.11.

## 3. Frozen base property

For one closed supplied-1m interval with closes `y`:

```text
TV = sum(abs(diff(y)))
D  = abs(y[-1] - y[0])
R  = log(TV / D), when TV>0 and D>0
```

Undefined cases remain `None`; no epsilon replacement is allowed.

## 4. Exact pairwise roughness decomposition

For counterpart leg intervals A and B, whenever both roughness values are defined:

```text
R_A - R_B = [log(TV_A)-log(TV_B)] - [log(D_A)-log(D_B)]
```

Report both terms and the exact residual. This is diagnostic only. No dominance cutoff is introduced.

The audit may also form the **common-support oracle interval**:

```text
start_common = max(start_A, start_B)
end_common   = min(end_A, end_B)
```

using supplied 1m rows only when `start_common < end_common` and required rows exist. Because common support uses counterpart information, it is an audit oracle only and can never become the registered single-view property.

## 5. Registered single-view endpoint-erosion ensemble

For each published leg independently, using only supplied 1m rows inside that leg and no counterpart information:

For every integer pair `(s,e)` with

```text
s in {0,1,2,3,4}
e in {0,1,2,3,4}
```

construct the inward interval

```text
[start_time + s minutes, end_time - e minutes]
```

only if both shifted timestamps exist exactly in supplied `1m_official`, the shifted start is strictly before shifted end, at least two rows are present, and roughness is defined.

No interpolation, nearest-row substitution, resampling or fill.

Registered outputs:

```text
erosion_roughness_median = median of all defined inward-interval roughness values
erosion_roughness_range  = max - min of all defined inward-interval roughness values
erosion_defined_count    = number of defined (s,e) combinations
```

The maximum four-minute inward shift is fixed ex ante because the financial-event locality is already one nominal 5m bar; the ensemble deliberately does not move an endpoint outside the published leg or use future data.

No best erosion pair is selected. Median/range are the only registered ensemble summaries.

## 6. Boundary-sliver diagnostics

For each leg report, when defined:

- original fine roughness;
- roughness after `(4,0)`, `(0,4)` and `(4,4)` inward erosion;
- fraction of original fine total variation removed by the first four minutes, last four minutes, and both boundary slivers;
- absolute change in net displacement under the same erosions.

These are diagnostics only and cannot create a weighted score.

## 7. Cross-slicer universe

Primary universe remains the frozen v0.6.5 published raw strict same-event pairs:

```text
offset1 8,381
offset2 5,770
offset3 6,204
offset4 9,098
aggregate 29,453
```

Corresponding legs are aligned by ordinal 0..3.

For every comparable pair-leg report absolute differences of:

- original fine roughness;
- registered `erosion_roughness_median`;
- registered `erosion_roughness_range`;
- native roughness `-log(E5)` as the existing reference only.

No new stability cutoff is introduced.

## 8. Pre-registered comparison rule

The decisive comparison for the registered candidate is only:

`erosion_roughness_median` vs original `fine_roughness` on the same pair-leg observations.

Report:

- median / p90 / p99 / mean absolute difference;
- paired sign counts: erosion difference smaller / equal / larger than original fine-roughness difference;
- all four offsets separately and aggregate.

Native roughness remains a descriptive reference; v0.6.11 does not require the new descriptor to beat native roughness in order to identify interval sensitivity, but promotion to a later POC would require clear consistent improvement over original fine roughness without pathological availability loss.

## 9. Availability / short-leg firewall

Do not drop short legs silently. Report the number of valid erosion combinations per leg and pair-leg comparability.

No minimum count is fitted after results. If a leg has zero defined erosion roughness values, it remains unavailable.

## 10. Frozen strata overlays

Repeat the registered comparison, without changing the descriptor, for:

- 482 v0.6.6 both-qualified strict pairs;
- 699 v0.6.6 qualification-disagreement pairs;
- 80 v0.6.1 target-repaired pairs;
- 56 target agreement / 24 target disagreement subsets.

Strata are descriptive only.

## 11. Prefix causality

The registered erosion ensemble uses only timestamps between the original published leg endpoints. Appending future rows after the leg endpoint must not alter any ensemble member, median or range.

The common-support oracle is not a deployable candidate and is exempt from single-view availability, but it still uses no rows outside the union of the already-published counterpart intervals.

## 12. Synthetic gates

Tests must cover:

- exact roughness formula;
- exact `ΔR = ΔlogTV - ΔlogD` decomposition;
- deterministic 25-cell erosion-grid construction;
- inward-only boundary rule;
- unavailable shifted timestamps remain unavailable rather than nearest-filled;
- constant/zero-displacement path leaves roughness undefined;
- future append outside the original leg does not change the ensemble;
- counterpart information is not required by the registered erosion ensemble;
- common-support helper is explicitly audit-only.

## 13. Interpretation choices

Allowed adjudications only:

- `endpoint_erosion_ensemble_materially_reduces_roughness_interval_sensitivity`;
- `common_support_confirms_boundary_effect_but_erosion_not_sufficient`;
- `roughness_instability_is_not_reliably_reduced_by_registered_erosion`;
- `mixed_interval_sensitivity_requires_more_audit`.

A positive result authorizes only a later separately frozen roughness-property POC. It does not create a qualification rule.

## 14. Global firewall

Global state remains `morphology_replication_not_yet_accepted`; operational baseline remains v0.4.3.

No threshold fitting, matcher/projection/publication change, direction/D1/D2/PAWCT, third-wave, outcomes/P&L, fresh OOS, paper trading or production is allowed in v0.6.11.
