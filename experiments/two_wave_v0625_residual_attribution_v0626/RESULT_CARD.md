# Two-Wave v0.6.26 v0.6.25 residual direction attribution

Formal attribution: **`v0626_absolute_margin_geometry_is_state_asymmetric`**

v0.6.26 changes no recognizer rule, threshold, qualification policy, or authority pointer.

## Frozen control reproduction

- filtered pairs: **57029**
- raw strict pairs: **29453**
- both-v0.6.18-qualified pairs: **1462**
- D1 exact: **1400/1462**
- v0.6.23 exact: **1397/1462**
- v0.6.25 exact: **1402/1462**

## D1 -> v0.6.25 pair transitions

| category | count |
|---|---:|
| retained_exact | 1366 |
| introduced_harm | 34 |
| repaired_old_nonexact | 36 |
| persistent_nonexact | 26 |

## v0.6.23 rescue candidates kept by v0.6.25 margin gate

| state | candidates | kept | withheld | keep fraction |
|---|---:|---:|---:|---:|
| range | 365 | 27 | 338 | 7.40% |
| uptrend | 1424 | 1243 | 181 | 87.29% |
| downtrend | 1266 | 1097 | 169 | 86.65% |

Range keep fraction: **7.40%**
Trend combined keep fraction: **86.99%**
Introduced-harm one-sided rescue fraction: **100.00%**

Frozen attribution gates:
- Range keep <= 0.5 * Trend keep: **True**
- introduced harm one-sided >= 80%: **True**

This result is diagnostic only. D1 remains the historical direction stability baseline; v0.6.18 remains qualification champion; morphology acceptance remains false.
