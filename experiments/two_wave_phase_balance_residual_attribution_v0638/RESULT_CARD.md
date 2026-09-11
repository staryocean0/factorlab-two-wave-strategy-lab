# Two-Wave v0.6.38 phase-balance residual attribution

Formal attribution: **`v0638_phase_balance_residual_attribution_complete`**

v0.6.35 -> v0.6.37 exact-status transitions:

| class | count |
|---|---:|
| both_exact | 1339 |
| phase_balance_repaired_v0635_nonexact | 31 |
| both_nonexact | 68 |
| phase_balance_harmed_v0635_exact | 24 |

Remaining v0.6.37 one-sided changes vs v0.6.25: **44**.
Semantic classes: `{'introduced_harm': 38, 'repaired_old_nonexact': 6}`.

Semantic class by rescue origin:

| semantic class | shared v0635+v0637 | phase-balanced only |
|---|---:|---:|
| introduced_harm | 28 | 10 |
| repaired_old_nonexact | 4 | 2 |
| persistent_nonexact | 0 | 0 |

This diagnostic changes no recognizer and does not authorize threshold tuning or automatic weighting-consensus promotion.
v0.6.25 remains the strongest pooled-exact direction contribution; v0.6.18 remains the qualification champion; morphology acceptance, trading and production remain closed.
