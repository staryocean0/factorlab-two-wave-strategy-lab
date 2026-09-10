# Two-Wave v0.6.18 result card

Formal verdict: **`v0618_path_gate_demotion_research_candidate_pass`**

Only `inefficient_leg` and `jump_dominated_leg` were demoted from hard vetoes to diagnostics. Parent identity, v0.6.5 publication, all non-path v0.5.4 hard reasons, D1, matcher, outcomes and trading remained frozen.

## Frozen control reproduction

Filtered mutual-unique pairs: **57,029** (expected 57,029).
Published raw strict same-event pairs: **29,453** (expected 29,453).
Control matrix: `{'both_qualified': 482, 'both_rejected': 28272, 'main_only_qualified': 352, 'other_only_qualified': 347}`.

## Candidate qualification stability

| offset | filtered pairs | raw strict | control +overlap | candidate +overlap | both-Q control | both-Q candidate |
|---|---:|---:|---:|---:|---:|---:|
| 5m_offset_1 | 14,784 | 8,381 | 42.9936% | 69.9301% | 135 | 400 |
| 5m_offset_2 | 12,725 | 5,770 | 37.0518% | 64.2058% | 93 | 287 |
| 5m_offset_3 | 13,412 | 6,204 | 33.2143% | 64.5299% | 93 | 302 |
| 5m_offset_4 | 16,108 | 9,098 | 47.9167% | 72.6575% | 161 | 473 |

Aggregate positive overlap: **40.8129% -> 68.3817%**.
Aggregate both-qualified: **482 -> 1462**.

## Gate

- all four offsets non-worse: **True**
- aggregate positive overlap >= 45.8129%: **True**
- aggregate both-qualified >= 531: **True**
- upstream/control reproduction: **True**

This result is a research qualification-policy adjudication only. It is not independent morphology acceptance and carries no trade or production authority.
