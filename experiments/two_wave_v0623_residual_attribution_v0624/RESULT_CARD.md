# Two-Wave v0.6.24 v0.6.23 residual direction attribution

v0.6.24 changes no recognizer rule.

## Frozen control reproduction

- pairs: **1462**
- D1 exact: **95.7592%**
- v0.6.23 exact: **95.5540%**
- v0.6.23 decisive coverage: **78.5568%**

## Pair transition accounting

| category | count |
|---|---:|
| retained_exact | 1350 |
| introduced_harm | 50 |
| repaired_old_nonexact | 47 |
| persistent_nonexact | 15 |

## Introduced-harm topology

- main_only_rescued: **28**
- other_only_rescued: **22**

## Rescued-side uncertain subtypes

### introduced_harm
- same_phase_reversal_conflict: **31**
- coherent_but_subthreshold: **8**
- strong_net_with_opposed_phase: **5**
- large_migration_without_coherent_direction: **3**
- opposite_envelope_conflict: **2**
- single_phase_dominant: **1**

### repaired_old_nonexact
- strong_net_with_opposed_phase: **25**
- coherent_but_subthreshold: **11**
- same_phase_reversal_conflict: **9**
- large_migration_without_coherent_direction: **2**

### retained_exact
- same_phase_reversal_conflict: **587**
- strong_net_with_opposed_phase: **54**
- coherent_but_subthreshold: **53**
- opposite_envelope_conflict: **33**
- large_migration_without_coherent_direction: **27**
- single_phase_dominant: **16**

No authority changes follow from this attribution alone. D1 remains the historical direction stability baseline and v0.6.18 remains qualification champion.

`morphology_acceptance=false`  
`trade_authority=false`  
`production_authority=false`
