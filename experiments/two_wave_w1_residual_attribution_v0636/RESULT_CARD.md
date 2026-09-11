# Two-Wave v0.6.36 W1 residual attribution

Formal attribution: **`v0636_w1_margin_route_not_authorized`**

One-sided changes: **50**.
Semantic classes: `{'introduced_harm': 43, 'repaired_old_nonexact': 4, 'persistent_nonexact': 3}`.

Changed-side W1 slack (`0.15 - max_support_W1`):

| group | n | median | q25 | q75 | fraction <=0.03 |
|---|---:|---:|---:|---:|---:|
| introduced_harm | 43 | 0.013296 | 0.004584 | 0.019356 | 0.930233 |
| repaired_old_nonexact | 4 | 0.056255 | 0.035013 | 0.078900 | 0.250000 |
| persistent_nonexact | 3 | 0.014361 | 0.011590 | 0.014361 | 1.000000 |

W1-margin challenger authorized: **False**

Authorization gates:
- introduced_harm_n_at_least_20: **True**
- repaired_n_at_least_20: **False**
- harm_median_at_least_0_03_smaller: **True**
- harm_near_boundary_fraction_at_least_70pct: **True**
- repair_near_boundary_fraction_at_most_40pct: **True**

This diagnostic changes no recognizer. v0.6.25 remains the strongest pooled-exact direction contribution and v0.6.18 remains the qualification champion unless a later preregistered challenger passes all gates.
