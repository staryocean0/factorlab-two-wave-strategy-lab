# Two-Wave v0.6.31 mutual-median Range rescue result

Formal verdict: **`v0631_mutual_median_range_rescue_direction_rejected`**

Frozen Range evidence: v0.6.23 Range consensus + v0.6.27 margin >= 0.03 + mutual median containment on all four frozen endpoint supports.
D1 decisive overrides: **0**.
New Range rescues beyond v0.6.25: **154**.

| metric | v0.6.25 | v0.6.31 |
|---|---:|---:|
| pooled exact agreement | 95.90% | 94.66% |
| pooled decisive coverage | 70.86% | 72.91% |
| decisive agreement | 100.00% | 100.00% |
| Range share among decisive labels | 1.06% | 3.85% |
| opposite trend conflicts | 0 | 0 |

Per-offset exact agreement:

| offset | v0.6.25 | v0.6.31 | delta pp |
|---|---:|---:|---:|
| 5m_offset_1 | 95.00% | 94.50% | -0.50 |
| 5m_offset_2 | 94.43% | 93.73% | -0.70 |
| 5m_offset_3 | 96.69% | 95.03% | -1.66 |
| 5m_offset_4 | 97.04% | 95.14% | -1.90 |

Promotion gates:
- upstream_controls: **True**
- D1_decisive_override_zero: **True**
- all_changes_are_uncertain_to_range: **True**
- all_offsets_exact_nonworse_vs_v0625: **False**
- pooled_exact_plus_0_20pp_vs_v0625: **False**
- pooled_decisive_coverage_plus_1pp: **True**
- pooled_decisive_agreement_at_least_99_5pct: **True**
- opposite_trend_conflict_zero: **True**
- decisive_class_diversity: **True**

Qualification remains v0.6.18. Independent morphology acceptance, trading and production authority remain false.
