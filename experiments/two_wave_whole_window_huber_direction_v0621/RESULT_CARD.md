# Two-Wave v0.6.21 whole-window Huber direction result

Formal verdict: **`v0621_whole_window_huber_direction_rejected`**

Qualification remained frozen at v0.6.18. Direction evaluation used only 1,462 strict same-financial-identity pairs where both views were v0.6.18-qualified.

| metric | D1 | v0.6.21 |
|---|---:|---:|
| pooled exact four-state agreement | 95.76% | 95.01% |
| pooled decisive coverage | 48.91% | 84.23% |
| opposite-trend conflict | 0.00% | 0.00% |

Per-offset exact agreement:

| offset | D1 | v0.6.21 | delta pp |
|---|---:|---:|---:|
| 5m_offset_1 | 95.50% | 93.50% | -2.00 |
| 5m_offset_2 | 94.77% | 94.77% | 0.00 |
| 5m_offset_3 | 96.36% | 94.70% | -1.66 |
| 5m_offset_4 | 96.19% | 96.62% | 0.42 |

Promotion gates:
- upstream_controls: **True**
- all_offsets_exact_agreement_nonworse: **False**
- pooled_exact_agreement_plus_3pp: **False**
- opposite_trend_conflict_nonworse: **True**
- pooled_decisive_coverage_floor_and_nonregression: **True**
- each_offset_side_decisive_coverage_at_least_40pct: **True**
- decisive_class_diversity: **True**

This is direction research only. Independent morphology acceptance remains false; no trading or production authority follows.
