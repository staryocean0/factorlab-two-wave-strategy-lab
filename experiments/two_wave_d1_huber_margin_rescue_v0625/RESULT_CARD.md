# Two-Wave v0.6.25 D1-primary erosion-consensus Huber margin rescue result

Formal verdict: **`v0625_D1_primary_erosion_consensus_margin_rescue_direction_rejected`**

Frozen consensus-margin threshold: **0.10 amplitude units**.
D1 decisive overrides: **0**.
v0.6.23 rescues: **3055**.
v0.6.25 margin-qualified rescues: **2367**.
v0.6.23 rescues withheld only by the new margin gate: **688**.

| metric | D1 | v0.6.23 | v0.6.25 |
|---|---:|---:|---:|
| pooled exact agreement | 95.76% | 95.55% | 95.90% |
| pooled decisive coverage | 48.91% | 78.56% | 70.86% |
| decisive agreement | 100.00% | 100.00% | 100.00% |
| opposite trend conflicts | 0 | 0 | 0 |

Per-offset exact agreement:

| offset | D1 | v0.6.23 | v0.6.25 | delta vs D1 pp |
|---|---:|---:|---:|---:|
| 5m_offset_1 | 95.50% | 93.25% | 95.00% | -0.50 |
| 5m_offset_2 | 94.77% | 96.17% | 94.43% | -0.35 |
| 5m_offset_3 | 96.36% | 95.70% | 96.69% | 0.33 |
| 5m_offset_4 | 96.19% | 97.04% | 97.04% | 0.85 |

Promotion gates:
- upstream_controls: **True**
- D1_controls_reproduced: **True**
- v0623_control_reproduced: **True**
- D1_decisive_override_zero: **True**
- all_offsets_exact_agreement_nonworse: **False**
- pooled_exact_agreement_nonworse: **True**
- pooled_decisive_coverage_material: **True**
- each_offset_side_decisive_coverage_at_least_55pct: **True**
- pooled_decisive_agreement_at_least_99_5pct: **True**
- opposite_trend_conflict_zero: **True**
- decisive_class_diversity: **False**
- nonzero_margin_rescue: **True**

Qualification remained frozen at v0.6.18. Independent morphology acceptance remains false; no trading or production authority follows.
