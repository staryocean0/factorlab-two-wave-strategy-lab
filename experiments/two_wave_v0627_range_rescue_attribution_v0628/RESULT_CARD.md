# Two-Wave v0.6.28 v0.6.27 Range-rescue attribution result

Formal attribution: **`v0628_range_rescue_topology_does_not_authorize_support_dispersion_gate`**

This diagnostic changed no recognizer rule.

Frozen exact-count controls:
- D1: **1400 / 1462**
- v0.6.25: **1402 / 1462**
- v0.6.27: **1388 / 1462**

Pair transitions v0.6.25 -> v0.6.27:
- retained exact: **1383**
- introduced harm: **19**
- repaired v0.6.25 nonexact: **5**
- persistent nonexact: **55**

New-Range topology:
- no_new_range: **1411**
- both_sides_new_range: **27**
- one_side_new_range_other_already_decisive: **5**
- other_only_new_range: **11**
- main_only_new_range: **8**

Range support-dispersion groups:

| group | n sides | median | p25 | p90 |
|---|---:|---:|---:|---:|
| introduced_harm | 19 | 0.8468 | 0.7303 | 1.1811 |
| successful_exact_or_repaired | 59 | 0.6981 | 0.4412 | 1.0029 |

Frozen attribution gates:
- upstream_controls: **True**
- all_label_changes_uncertain_to_range: **True**
- introduced_harm_one_sided_fraction_at_least_80pct: **True**
- support_dispersion_separation: **True**
- minimum_group_sizes: **False**

Next-step authorization: **no_support_dispersion_gate_from_v0628**

Qualification remains v0.6.18; direction winner remains unset; morphology acceptance remains false.
