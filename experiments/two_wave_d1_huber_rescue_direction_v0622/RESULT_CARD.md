# Two-Wave v0.6.22 D1-primary Huber-rescue result

Formal verdict: **`v0622_D1_primary_Huber_rescue_direction_rejected`**

D1 decisive overrides: **0**.
D1-Uncertain records rescued: **3737**.

| metric | D1 | v0.6.22 |
|---|---:|---:|
| pooled exact agreement | 95.76% | 94.73% |
| pooled decisive coverage | 48.91% | 85.84% |
| decisive agreement | 100.00% | 99.92% |
| opposite trend conflicts | 0 | 0 |

Per-offset exact agreement:

| offset | D1 | v0.6.22 | delta pp |
|---|---:|---:|---:|
| 5m_offset_1 | 95.50% | 92.50% | -3.00 |
| 5m_offset_2 | 94.77% | 94.77% | 0.00 |
| 5m_offset_3 | 96.36% | 95.36% | -0.99 |
| 5m_offset_4 | 96.19% | 96.19% | 0.00 |

Promotion gates:
- upstream_controls: **True**
- D1_decisive_override_zero: **True**
- all_offsets_exact_agreement_nonworse: **False**
- pooled_exact_agreement_plus_1pp: **False**
- opposite_trend_conflict_zero: **True**
- pooled_decisive_agreement_at_least_99pct: **True**
- pooled_decisive_coverage_material: **True**
- each_offset_side_decisive_coverage_at_least_55pct: **True**
- decisive_class_diversity: **True**

Independent morphology acceptance remains false; qualification champion remains v0.6.18.
