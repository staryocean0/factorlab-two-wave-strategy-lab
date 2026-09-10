# Two-Wave v0.6.28 v0.6.27 Range-rescue attribution protocol

Date: 2026-09-10
Status: frozen before diagnostic outcome replay

## Purpose

Explain why v0.6.27 restored Range class diversity yet reduced cross-slicing exact agreement. This is a read-only diagnostic. It changes no recognizer, qualification rule, margin threshold, state boundary, identity, or publication rule.

## Frozen upstream controls

- qualification: v0.6.18 unchanged;
- evaluation universe: 1,462 strict same-financial-identity pairs with both views v0.6.18-qualified;
- D1 exact count: 1,400;
- v0.6.25 exact count: 1,402;
- v0.6.27 exact count: 1,388;
- v0.6.25 trend absolute margin: 0.10;
- v0.6.27 Range absolute equivalent of the frozen 20% relative margin: 0.03;
- D1 decisive outputs are never overridden.

No future return, PnL, H1/H2, third wave, 2021+, 2026 data, or cross-offset information may be used as a runtime feature.

## Frozen diagnostic decomposition

For every one of the 1,462 matched pairs, reconstruct D1, v0.6.25 and v0.6.27 independently in each single view and record:

1. pair transition from v0.6.25 exactness to v0.6.27 exactness:
   - retained_exact;
   - introduced_harm;
   - repaired_v0625_nonexact;
   - persistent_nonexact.
2. whether v0.6.27 differs from v0.6.25 on zero, one or both sides;
3. because the trend rule is frozen identically in v0.6.25 and v0.6.27, verify every changed side is exactly `v0.6.25=Uncertain -> v0.6.27=Range`; otherwise fail closed;
4. for every newly admitted Range side, record the already-defined v0.6.23 single-view diagnostics:
   - `consensus_margin_to_frozen_boundary`;
   - `consensus_score_span` across the four endpoint-erosion supports;
   - `consensus_score_span / 0.15` as a dimensionless Range-support dispersion;
   - min/max support score and the four support scores.
5. split newly admitted Range sides/pairs by topology:
   - both_sides_new_range;
   - main_only_new_range;
   - other_only_new_range;
   - one_side_new_range_other_already_decisive;
   - one_side_new_range_other_uncertain.
6. compare the frozen score-span distributions for:
   - introduced_harm caused by a new Range side;
   - repaired_v0625_nonexact caused by a new Range side;
   - retained/exact pairs containing new Range admissions.

## Frozen attribution gates

This diagnostic may authorize a later **single-view Range support-dispersion gate** only if all of the following hold:

- all frozen upstream controls reproduce exactly;
- every v0.6.25 -> v0.6.27 label change is `Uncertain -> Range`;
- at least 80% of v0.6.27 introduced-harm pairs involve a one-sided new Range admission;
- the median dimensionless Range support dispersion among harmful new-Range sides is at least 1.5x the median among successful exact/repaired new-Range sides, OR its p25 exceeds the successful-group median;
- there are at least 20 harmful new-Range sides and at least 20 successful exact/repaired new-Range sides, so the comparison is not a tiny-sample artifact.

If these conditions fail, the next version may not invent a score-span threshold from this diagnostic. It must retain v0.6.25 as the strongest pooled-exact contribution and seek another causal source of Range evidence.

This diagnostic cannot install a direction winner. Global morphology acceptance remains false; trading and production remain closed.
