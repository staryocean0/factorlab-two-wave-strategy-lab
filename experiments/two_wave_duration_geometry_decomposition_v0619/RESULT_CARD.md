# Two-Wave v0.6.19 duration-geometry decomposition result

Formal attribution: **`v0619_local_duration_boundary_sensitivity_dominant`**

v0.6.19 changes no recognizer or qualification rule. It decomposes only the 676 remaining v0.6.18 cross-slicing qualification disagreements.

## Frozen control reproduction

- filtered mutual-unique same-event pairs: **57,029**
- published raw strict same-event pairs: **29,453**
- v0.6.18 disagreements: **676**

## Decisive attribution

- local-duration family involved: **393/676 = 58.14%**
- local-duration-only: **361**
- local-duration-only simple one-bar boundary: **318/361 = 88.09%**
- long-span safety involved: **21/676 = 3.11%**

| reason | involved | one-bar boundary | fraction |
|---|---:|---:|---:|
| short_leg | 252 | 250 | 99.21% |
| short_cycle | 108 | 94 | 87.04% |
| cycle_duration_mismatch | 68 | 29 | 42.65% |

Per-offset local-duration attribution:

| offset | disagreements | local involved | local-only | local-only simple boundary |
|---|---:|---:|---:|---:|
| 5m_offset_1 | 172 | 100 (58.14%) | 90 | 78 (86.67%) |
| 5m_offset_2 | 160 | 91 (56.88%) | 84 | 73 (86.90%) |
| 5m_offset_3 | 166 | 101 (60.84%) | 94 | 85 (90.43%) |
| 5m_offset_4 | 178 | 101 (56.74%) | 93 | 82 (88.17%) |

## Consequence

The frozen category authorizes a future version to preregister **one narrow duration-boundary repair candidate**. It does not itself change any duration threshold, does not change v0.6.18 qualification authority, and does not unfreeze Range/UpTrend/DownTrend direction classification.

`morphology_acceptance=false`  
`trade_authority=false`  
`production_authority=false`
