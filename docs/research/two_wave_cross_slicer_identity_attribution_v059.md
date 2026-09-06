# v0.5.9 Cross-slicer identity attribution after v0.5.8 PAWCT

## Status

`post_v058_attribution_not_morphology_acceptance`

This is a read-only attribution study over already-generated v0.5.7b and v0.5.8 artifacts. It does not re-run the recognizer, change qualification, change D1/D2/PAWCT, use future outcomes, or grant trade authority.

## Why this audit was necessary

The frozen v0.5.8 POC formally failed its selected-record cross-slicer R1 gate:

- target `shared_D1=uncertain + D2_harm`: 194 record pairs / 21,802 weighted 1m bars;
- PAWCT large-margin sign-flip bars: 1,566;
- large-margin flip fraction: **7.182827%**, above the frozen `<5%` gate;
- PAWCT median cross-slicer displacement: **0.352729**, materially lower than endpoint D1 displacement **0.719017**.

The frozen verdict `PAWCT_representation_candidate_fail` remains historically correct for the object it actually tested: **labels/scalars attached to whichever exclusive selected records owned the same timeline bars**.

However, the Stage-B geometry artifact records the five raw-extremum occurrence timestamps for each paired selected record. Those timestamps show that many compared record pairs are not local variants of the same two-wave event.

## Recomputed identity-dislocation evidence

### Threshold-free fact for the large-margin failures

Across all 1,133 selected-record pairs used by v0.5.8:

- 82 pairs / 5,596 weighted bars are PAWCT large-margin sign flips;
- the **minimum** across those 82 pairs of `max(abs(delta occurrence timestamp))` over the five anchors is **1,163 minutes**;
- weighted median maximum five-anchor displacement is **1,406 minutes**;
- maximum is **5,756 minutes**.

For the frozen R1 target subset:

- 22 pairs / 1,566 weighted bars are large-margin flips;
- minimum maximum-anchor displacement is again **1,163 minutes**;
- weighted median is **1,419 minutes**;
- maximum is **4,288 minutes**.

Therefore none of the large-margin PAWCT failures is a one-bar or several-bar perturbation of the same local five-extremum pattern. Every large-margin failure compares selected tuples whose anchors are displaced by roughly a trading day or more on at least one of the five extrema.

### Full locality sweep (exploratory attribution)

A post-hoc threshold sweep was reported rather than choosing a favorable cutoff. For each locality threshold from 1 to 480 minutes, the locally aligned subset contains **zero** PAWCT large-margin sign-flip bars.

| max five-anchor delta | target aligned bar share | target aligned large-margin flip | target dislocated flip | all aligned bar share | all aligned large-margin flip | all dislocated flip |
|---:|---:|---:|---:|---:|---:|---:|
| 1m | 2.76% | 0.000% | 7.387% | 7.02% | 0.000% | 3.504% |
| 3m | 9.12% | 0.000% | 7.904% | 20.13% | 0.000% | 4.079% |
| 5m | 12.35% | 0.000% | 8.195% | 31.86% | 0.000% | 4.781% |
| 6m | 15.65% | 0.000% | 8.515% | 35.06% | 0.000% | 5.016% |
| 10m | 24.03% | 0.000% | 9.454% | 43.60% | 0.000% | 5.776% |
| 15m | 26.04% | 0.000% | 9.712% | 49.25% | 0.000% | 6.419% |
| 30m | 30.44% | 0.000% | 10.326% | 55.03% | 0.000% | 7.244% |
| 60m | 30.44% | 0.000% | 10.326% | 57.72% | 0.000% | 7.705% |
| 120m | 32.68% | 0.000% | 10.670% | 59.70% | 0.000% | 8.084% |
| 240m | 35.44% | 0.000% | 11.125% | 62.42% | 0.000% | 8.669% |
| 480m | 35.44% | 0.000% | 11.125% | 62.42% | 0.000% | 8.669% |

The previously frozen 10-minute exploratory proxy also showed:

- target locally aligned: 5,238 bars, large-margin flip **0%**, median `|delta T|=0.04493`, endpoint displacement `0.12292`;
- target dislocated: 16,564 bars, large-margin flip **9.454%**, median `|delta T|=0.56094`, endpoint displacement `1.09853`;
- all 5,596 large-margin flip bars were in the dislocated subset;
- 91.42% of large-margin flip bars had **all five anchors** displaced by >10 minutes, and all remaining flips had at least four of five displaced.

This 10-minute partition is exploratory because the data distribution had already been inspected before that audit was frozen. The threshold-free 1,163-minute minimum among all large-margin failures is therefore the stronger finding.

## Same-event selected-pair diagnostic

Using one nominal 5m bar as an audit-only locality relation (`max five-anchor timestamp delta <=5m`):

- 262 selected-record pairs / 54,722 weighted bars qualify as local same-phase pairs;
- phase agrees on **100%** of those bars;
- D1 label agreement is **96.4493%**;
- D2 label agreement is **93.8014%**;
- neither D1 nor D2 has any direct uptrend/downtrend reversal in this local subset;
- PAWCT large-margin sign flip is **0%**.

This does not accept D1, D2 or PAWCT. It only shows that the previous cross-offset adjudication mixed **event identity disagreement** with **direction disagreement**.

## Mechanism found in the current selection layer

v0.5.4 still uses `CharacteristicExclusiveLedger` from v0.5.1. Its priority is:

1. `confirmation_bar`,
2. `characteristic_scale_level`,
3. `start_bar`,
4. `end_bar`,
5. `record_id`.

A qualified tuple is selected only if `start_bar >= current_selected_end`; otherwise it is overlap-suppressed.

A local executable counterexample using the exact class source proves:

- candidate A `[20,80]`, candidate B `[30,90]`, same qualification and scale;
- `A.confirm=60, B.confirm=61` selects A and suppresses B;
- changing only `A.confirm` to 62 selects B and suppresses A;
- therefore a one-bar confirmation-order perturbation can change the published five-extremum identity.

A second semantic counterexample uses seven alternating extrema defining three consecutive complete waves. The rolling two-wave windows `(W1,W2)` and `(W2,W3)` are both valid observations under the financial requirement, but the exclusive ledger suppresses the latter solely because the windows overlap.

## Main-view packing prevalence

From the frozen v0.5.5 main-view qualified diagnostics:

- qualified records: **734**;
- selected by exclusive ledger: **404**;
- suppressed: **330 (44.96%)**;
- strict interval-overlap components: 356 total, **178 nontrivial**;
- largest overlap component: **11** qualified tuples;
- component size p90/p95/p99: **4 / 5 / 7**;
- component span median/p90/max: **48 / 96 / 166 bars**.

Thus packing competition is not a rare edge case.

## Interpretation correction

The correct interpretation is now:

> v0.5.8 failed as a test of the stability of the **exclusive selected timeline ownership output**. It did not validly falsify PAWCT as a parent-translation representation for the same financial two-wave event, because every large-margin PAWCT failure compared materially different five-extremum identities.

Accordingly:

- do **not** tune PAWCT;
- do **not** promote PAWCT;
- do **not** declare the whole-path translation family dead from v0.5.8;
- return to morphology/event identity before another direction formula;
- keep operational baseline v0.4.3 and global status `morphology_replication_not_yet_accepted`.
