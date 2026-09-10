# Two-Wave v0.6.27 state-relative margin rescue result

Formal verdict: **`v0627_D1_primary_state_relative_margin_rescue_direction_rejected`**

Frozen relative margin fraction: **20%**.
Trend absolute margin remains 0.10; Range equivalent state-relative margin is 0.03.
D1 decisive overrides: **0**.

| metric | D1 | v0.6.25 | v0.6.27 |
|---|---:|---:|---:|
| pooled exact agreement | 95.76% | 95.90% | 94.94% |
| pooled decisive coverage | 48.91% | 70.86% | 73.53% |
| decisive agreement | 100.00% | 100.00% | 100.00% |
| opposite trend conflicts | 0 | 0 | 0 |

Per-offset exact agreement:

| offset | D1 | v0.6.25 | v0.6.27 | delta vs D1 pp |
|---|---:|---:|---:|---:|
| 5m_offset_1 | 95.50% | 95.00% | 94.75% | -0.75 |
| 5m_offset_2 | 94.77% | 94.43% | 93.73% | -1.05 |
| 5m_offset_3 | 96.36% | 96.69% | 95.36% | -0.99 |
| 5m_offset_4 | 96.19% | 97.04% | 95.56% | -0.63 |

Promotion gates:
- upstream_controls: **True**
- D1_controls_reproduced: **True**
- v0625_control_reproduced: **True**
- D1_decisive_override_zero: **True**
- all_offsets_exact_agreement_nonworse: **False**
- pooled_exact_agreement_nonworse: **False**
- pooled_decisive_coverage_material: **True**
- each_offset_side_decisive_coverage_at_least_55pct: **True**
- pooled_decisive_agreement_at_least_99_5pct: **True**
- opposite_trend_conflict_zero: **True**
- decisive_class_diversity: **True**
- nonzero_rescue: **True**

Qualification remains frozen at v0.6.18. Independent morphology acceptance remains false; no trading or production authority follows.
