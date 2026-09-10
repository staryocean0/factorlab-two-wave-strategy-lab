# Two-Wave v0.6.30 Range-evidence intersection result

Formal verdict: **`v0630_range_evidence_intersection_direction_rejected`**

Frozen Range evidence: v0.6.27 margin >= 0.03 AND v0.6.29 cycle-IQR overlap >= 0.50.
D1 decisive overrides: **0**.
New Range rescues beyond v0.6.25: **211**.

| metric | v0.6.25 | v0.6.30 |
|---|---:|---:|
| pooled exact agreement | 95.90% | 95.01% |
| pooled decisive coverage | 70.86% | 73.50% |
| decisive agreement | 100.00% | 100.00% |
| Range share among decisive labels | 1.06% | 4.61% |
| opposite trend conflicts | 0 | 0 |

Per-offset exact agreement:

| offset | v0.6.25 | v0.6.30 | delta pp |
|---|---:|---:|---:|
| 5m_offset_1 | 95.00% | 95.00% | 0.00 |
| 5m_offset_2 | 94.43% | 93.73% | -0.70 |
| 5m_offset_3 | 96.69% | 95.36% | -1.32 |
| 5m_offset_4 | 97.04% | 95.56% | -1.48 |

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
