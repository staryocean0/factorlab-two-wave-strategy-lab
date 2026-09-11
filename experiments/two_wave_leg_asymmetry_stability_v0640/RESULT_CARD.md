# Two-Wave v0.6.40 leg-asymmetry and harmless-slicing stability attribution

Formal attribution: **`v0640_leg_asymmetry_and_harmless_slicing_stability_attribution_complete_no_gate_authorized`**

Diagnostic universe: **105** rescue-involved pairs = 61 stable both-rescue + 44 one-sided.

Primary quantity: `A_L1 = first_leg_progress_l1 - second_leg_progress_l1`. Zero is the structural equality point, not a fitted cutoff.

| quantity | stable both-rescue median | harm one-sided median | repair one-sided median |
|---|---:|---:|---:|
| pair/rescue A_L1 | 0.006217 | 0.009595 | -0.012005 |
| harmless-slicing abs delta A_L1 | 0.040985 | 0.043883 | 0.044867 |
| pair/rescue A_Linf | 0.015926 | 0.003776 | -0.057305 |
| harmless-slicing abs delta A_Linf | 0.064950 | 0.105735 | 0.085289 |

P(harm rescue A_L1 > stable pair-mean A_L1): **0.533650**
P(harm |delta A_L1| > stable |delta A_L1|): **0.521570**
P(harm rescue A_Linf > stable pair-mean A_Linf): **0.513805**
P(harm |delta A_Linf| > stable |delta A_Linf|): **0.575065**

One-sided rescue-minus-nonrescue A_L1 sign fractions: `{'introduced_harm': {'count': 38, 'positive': 0.6578947368421053, 'zero': 0.0, 'negative': 0.34210526315789475}, 'repaired_old_nonexact': {'count': 6, 'positive': 0.3333333333333333, 'zero': 0.0, 'negative': 0.6666666666666666}}`.

This remains diagnostic only. No fitted threshold, recognizer change, trade authority or production authority is authorized by v0.6.40 itself.
