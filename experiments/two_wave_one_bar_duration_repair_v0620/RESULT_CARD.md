# Two-Wave v0.6.20 result card

Formal verdict: **`v0620_exact_one_bar_duration_repair_rejected`**

The sole challenger demotes `short_leg` only at `min_leg == 3` and `short_cycle` only at `min_cycle == 11`. More severe duration failures, cycle-duration mismatch, amplitude, confirmation and long-span safety gates remain hard. No cross-view data enter the candidate decision.

## Frozen control reproduction

- filtered mutual-unique pairs: **57,029 / 57,029**
- published raw strict pairs: **29,453 / 29,453**
- v0.6.18 aggregate matrix: `{'both_qualified': 1462, 'both_rejected': 27315, 'main_only_qualified': 386, 'other_only_qualified': 290}`

## Candidate stability

| offset | v0.6.18 +overlap | v0.6.20 +overlap | delta pp | both-Q v0618 | both-Q v0620 |
|---|---:|---:|---:|---:|---:|
| 5m_offset_1 | 69.9301% | 69.0827% | -0.8474 | 400 | 610 |
| 5m_offset_2 | 64.2058% | 63.1501% | -1.0557 | 287 | 425 |
| 5m_offset_3 | 64.5299% | 64.5207% | -0.0092 | 302 | 451 |
| 5m_offset_4 | 72.6575% | 70.7019% | -1.9555 | 473 | 695 |

Aggregate positive overlap: **68.3817% -> 67.3564%** (-1.0253 pp).
Aggregate both-qualified: **1,462 -> 2,181**.
Unique published identities newly qualified by the exact boundary rule: **5,297** (view-summed 5,345).

## Frozen promotion gate

- exact control reproduction: **True**
- all four offsets non-worse: **False**
- aggregate positive overlap >= 71.38166511%: **False**
- aggregate both-qualified >= 1,609: **True**
- hard safety invariants: **True**

This is a qualification-policy component adjudication only. Full morphology acceptance remains false; direction/state classification, outcomes, trading and production remain frozen.
