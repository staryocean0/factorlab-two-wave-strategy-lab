# Two-Wave v0.6.48 independent reference-label calibration result

Formal workflow run: `34663178194`  
Final reference SHA256: `321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d`  
Formal scoring result: `REFERENCE_SCORING_RESULT.json`

## Verdict

**`v0648_independent_reference_calibration_gates_not_all_pass`**

v0.6.48 first established a blinded independent reference set before any model/reference scoring. The annotation-quality layer passed, but the frozen recognizer/calibration gates did not.

## Reference-label quality

- cases: `240`;
- first-pass presence exact agreement: `0.9333333333333333`;
- first-pass presence Cohen kappa: `0.7010742643624475`;
- both-first-pass-yes cases: `22`;
- parent-state exact agreement within both-yes cases: `1.0`;
- parent-state Cohen kappa: `1.0`;
- first-pass disagreements: `16`;
- third-adjudicated disagreements: `16`;
- unresolved disagreements: `0`;
- all pre-frozen label-quality gates passed: `true`.

The final reference set contains exactly `240` cases and is frozen at SHA256 `321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d`.

## Pre-frozen calibration gates

| gate | observed | threshold | pass |
|---|---:|---:|---|
| candidate reference-confirmed presence | `16/120 = 0.13333333333333333` | `>= 0.80` | **false** |
| v0.6.25 parent-state exact among reference-confirmed candidates | `5/16 = 0.3125` | `>= 0.85` | **false** |
| v0.6.25 UpTrend/DownTrend opposite-conflict rate | `0/16 = 0.0` | `<= 0.02` | **true** |
| human-positive control miss fraction | `10/120 = 0.08333333333333333` | `<= 0.20` | **true** |

`all_calibration_support_gates_pass=false`.

## Descriptive comparator

D1 was frozen as descriptive-only, not a gated challenger. Among the same `16` reference-confirmed candidate cases:

- D1 parent-state exact agreement: `5/16 = 0.3125`;
- D1 opposite-trend conflict rate: `0.0`;
- D1 uncertain rate among reference-confirmed candidates: `9/16 = 0.5625`.

v0.6.25 reduces uncertainty relative to D1 on this subset (`7/16 = 0.4375` uncertain) but does not improve exact agreement beyond `0.3125`.

## Interpretation

The dominant failure is upstream of direction refinement. Only `13.33%` of the frozen v0.6.18 candidate cases are confirmed by the independent reference as containing two complete same-scale waves, versus a pre-frozen required `80%`.

Therefore v0.6.48 does **not** support the current v0.6.18 qualification semantics as independently reference-calibrated morphology recognition. The low direction exact agreement is secondary because it is evaluated on only the `16` reference-confirmed candidate cases.

The control miss gate passes (`8.33%`), so the most immediate evidenced weakness is candidate precision / semantic qualification, not an obvious broad missed-positive problem in the frozen control stratum.

No threshold retuning, sample removal, hidden-stratum redefinition, future outcome use, or post-result gate change was performed.

## Authority

- Development-era qualification champion remains historically `v0.6.18`, but it is **not independently reference-calibrated**;
- independently reference-calibrated qualification authority: **none**;
- parent-direction winner: **unset**;
- v0.6.25 remains a retained Development contribution, not a winner;
- `morphology_acceptance=false`;
- `trade_authority=false`;
- `production_authority=false`.

The current recognizer must not be promoted from this evidence. Any next research stage must begin with a separately frozen, read-only reference-conditioned failure attribution or a materially revised semantic object; it may not fit v0.6.18 thresholds directly to these 240 reference labels.
