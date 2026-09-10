# Two-Wave v0.6.33 two-cycle median-shift Range result

Formal verdict: **`v0633_two_cycle_median_shift_range_direction_rejected`**

New Range rescues: **1119**. D1/v0.6.25 decisive overrides: **0**.

| metric | v0.6.25 | v0.6.33 |
|---|---:|---:|
| pooled exact agreement | 95.90% | 91.86% |
| pooled decisive coverage | 70.86% | 81.91% |
| decisive agreement | 100.00% | 99.13% |
| Range decisive share | 1.06% | 14.41% |

Per-offset exact agreement:

| offset | v0.6.25 | v0.6.33 | delta pp |
|---|---:|---:|---:|
| 5m_offset_1 | 95.00% | 92.00% | -3.00 |
| 5m_offset_2 | 94.43% | 91.29% | -3.14 |
| 5m_offset_3 | 96.69% | 90.73% | -5.96 |
| 5m_offset_4 | 97.04% | 92.81% | -4.23 |

Promotion gates:
- upstream_controls: **True**
- D1_v0625_decisive_override_zero: **True**
- all_changes_uncertain_to_range: **True**
- all_offsets_exact_nonworse_vs_v0625: **False**
- pooled_exact_plus_0_20pp: **False**
- pooled_decisive_coverage_plus_1pp: **True**
- pooled_decisive_agreement_at_least_99_5pct: **False**
- opposite_trend_conflict_zero: **True**
- decisive_class_diversity: **True**

Qualification remains v0.6.18. Independent morphology acceptance, trading and production authority remain false.
