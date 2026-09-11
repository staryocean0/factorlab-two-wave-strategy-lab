# Two-Wave v0.6.37 phase-balanced Wasserstein Range result

Formal verdict: **`v0637_phase_balanced_wasserstein_range_direction_rejected`**

New Range rescues: **621**. D1/v0.6.25 decisive overrides: **0**.

| metric | v0.6.25 | v0.6.37 |
|---|---:|---:|
| pooled exact agreement | 95.90% | 93.71% |
| pooled decisive coverage | 70.86% | 76.54% |
| decisive agreement | 100.00% | 100.00% |
| Range decisive share | 1.06% | 8.40% |

Per-offset exact agreement:

| offset | v0.6.25 | v0.6.37 | delta pp |
|---|---:|---:|---:|
| 5m_offset_1 | 95.00% | 93.50% | -1.50 |
| 5m_offset_2 | 94.43% | 91.99% | -2.44 |
| 5m_offset_3 | 96.69% | 92.72% | -3.97 |
| 5m_offset_4 | 97.04% | 95.56% | -1.48 |

Promotion gates:
- upstream_controls: **True**
- D1_v0625_decisive_override_zero: **True**
- all_changes_uncertain_to_range: **True**
- all_offsets_exact_nonworse_vs_v0625: **False**
- pooled_exact_plus_0_20pp: **False**
- pooled_decisive_coverage_plus_1pp: **True**
- pooled_decisive_agreement_at_least_99_5pct: **True**
- opposite_trend_conflict_zero: **True**
- decisive_class_diversity: **True**

Qualification remains v0.6.18. Independent morphology acceptance, trading and production authority remain false.
