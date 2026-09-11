# Two-Wave v0.6.39 order-sensitive residual-shape attribution

Formal attribution: **`v0639_order_sensitive_residual_shape_attribution_complete_no_gate_authorized`**

Residual universe: **44** one-sided v0.6.37 changes; semantics `{'introduced_harm': 38, 'repaired_old_nonexact': 6}`.

The representation removes each leg's absolute level and endpoint displacement, then compares corresponding 65-point within-leg progress curves.

| descriptor | harm median | repair median | P(harm > repair) |
|---|---:|---:|---:|
| first_leg_progress_l1 | 0.149877 | 0.095696 | 0.747807 |
| second_leg_progress_l1 | 0.124351 | 0.102333 | 0.585526 |
| first_leg_progress_linf | 0.342913 | 0.260998 | 0.721491 |
| second_leg_progress_linf | 0.329796 | 0.340604 | 0.506579 |
| mean_leg_progress_l1 | 0.134996 | 0.106115 | 0.717105 |
| max_leg_progress_l1 | 0.169283 | 0.131374 | 0.721491 |
| mean_leg_progress_linf | 0.347468 | 0.301991 | 0.699561 |
| max_leg_progress_linf | 0.427643 | 0.379921 | 0.660088 |

Rescue-origin counts: `{'phase_balanced_only_rescue': 12, 'shared_bar_equal_and_phase_balanced_rescue': 32}`.

No threshold or gate is authorized from this diagnostic. The repaired group has only six observations by frozen design.
v0.6.25 remains the strongest pooled-exact direction contribution; v0.6.18 remains qualification champion; morphology acceptance, trading and production remain closed.
