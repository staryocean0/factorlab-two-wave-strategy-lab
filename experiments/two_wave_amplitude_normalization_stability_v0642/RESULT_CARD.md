# Two-Wave v0.6.42 amplitude-normalization stability attribution

Formal attribution: **`v0642_amplitude_normalization_stability_attribution_complete_no_gate_authorized`**

Diagnostic universe: **105** = 61 stable both-rescue + 44 one-sided; harm counterfactual rows = 38.

| quantity | stable median | harm median | rank P(harm > stable) |
|---|---:|---:|---:|
| amplitude-unit SRD | 0.035765 | 0.041867 | 0.547886 |
| max raw-W1 SRD | 0.122715 | 0.186500 | 0.657032 |
| max normalized-W1 SRD | 0.099678 | 0.186531 | 0.694996 |
| cycle-amplitude-imbalance SRD | 0.276829 | 0.339595 | 0.559965 |

Harm counterfactual attribution counts: `{'amplitude_denominator_change_sufficient': 4, 'both_changes_required': 5, 'either_component_alone_sufficient': 5, 'raw_numerator_change_sufficient': 24}`.
Harm signed amplitude-unit change fractions: `{'count': 38, 'positive': 0.5789473684210527, 'zero': 0.0, 'negative': 0.42105263157894735}`.
Harm signed raw-W1 change fractions: `{'count': 38, 'positive': 0.07894736842105263, 'zero': 0.0, 'negative': 0.9210526315789473}`.
Harm signed normalized-W1 change fractions: `{'count': 38, 'positive': 0.0, 'zero': 0.0, 'negative': 1.0}`.

v0.6.42 is diagnostic only. It does not change the recognizer, tune the inherited 0.15 ceiling, or authorize a gate.
