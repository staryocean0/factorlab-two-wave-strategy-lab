# v0.6.49 Reference-Conditioned Qualification Failure Attribution — Result Card

Date: 2026-09-12  
Formal workflow run: `34664379475`  
Formal result commit: `d3f4c3a2b97b6d517faed5fb4bbb54d2d95f46c8`  
Protocol: `docs/research/TWO_WAVE_REFERENCE_CONDITIONED_QUALIFICATION_FAILURE_ATTRIBUTION_V0649_PROTOCOL.md`

## Frozen question

Why did the independently adjudicated v0.6.48 reference confirm only `16/120` hidden v0.6.18-qualified candidates as complete same-scale two-wave parents?

This run is attribution-only. It does not fit a classifier, tune a threshold, restore a demoted gate, change qualification, or use direction predictions/future outcomes.

## Hard controls

- source Development SHA256 verified: `bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`;
- sampling commitment reproduced: `f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8`;
- final reference SHA256 reproduced: `321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d`;
- candidate partition reproduced exactly: `104 reference-no / 16 reference-yes`;
- control cases: `120`, of which `10` are reference-yes;
- annotator notes/confidence not used;
- D1/v0.6.25 predictions not used;
- no future outcomes or P&L used;
- no threshold fitting performed;
- no case-level residual table written.

## Frozen family decision

No predeclared family reaches the protocol's `strongly_supported` rule.

| Family | Strongly supported |
|---|---:|
| publication maturity | false |
| fragment / parent scale | false |
| same-scale imbalance | false |
| path noise | false |
| identity ambiguity | false |

Primary attribution:

`diffuse_or_fundamental_semantic_object_mismatch`

## Key diagnostics

### Publication maturity — unsupported

- confirmation delay median: reference-no `4.0` bars vs reference-yes `4.0` bars;
- direction-adjusted failure rank: `0.5027043269230769`.

The candidate/reference mismatch is not explained by the final pivot simply being published too close to the chart cutoff.

### Fragment / parent scale — one local clue, family not established

The strongest individual clue in the whole audit is amplitude scale relative to the visible 96-bar window:

- `amplitude_unit_fraction` median: reference-no `0.31374702750061895` vs reference-yes `0.43471746553155977`;
- direction-adjusted failure rank: **`0.75`** — individually strong.

But corroborating scale diagnostics do not reach the frozen strong threshold:

- parent span fraction: medians `0.4473684210526316` vs `0.5473684210526316`, adjusted rank `0.6225961538461539`;
- parent anchor excursion fraction: medians `0.7411218178587164` vs `0.7538325150315854`, adjusted rank `0.5306490384615384`.

Therefore the protocol does **not** authorize a `fragment_parent_scale` mechanism claim or any amplitude cutoff.

### Same-scale imbalance — unsupported

- cycle duration ratio rank: `0.4807692307692308`;
- corresponding-leg duration max-ratio rank: `0.4909855769230769`;
- amplitude-ratio rank: `0.4128605769230769`.

Reference-negative candidates are not consistently more imbalanced by the frozen duration/amplitude ratios.

### Path noise — suggestive jump effect only, family unsupported

- max jump-share rank: `0.6274038461538461`;
- min-efficiency adjusted rank: `0.5474759615384616`;
- max-flat-share rank: `0.47896634615384615`;
- jump-dominated trigger incidence: `27.88%` reference-no vs `18.75%` reference-yes, gap `+9.13pp`;
- inefficient-leg incidence: `43.27%` reference-no vs `50.00%` reference-yes, gap `-6.73pp`.

The evidence is insufficient to restore either v0.6.18-demoted path gate.

### Identity ambiguity — unsupported

- identity-count adjusted rank: `0.5096153846153846`;
- multi-identity incidence: `1.92%` reference-no vs `0%` reference-yes.

The mismatch is not primarily caused by multiple qualified identities at the same cutoff.

### Legacy corresponding-leg mismatch — opposite of expected failure story

- incidence: `43.27%` reference-no vs `56.25%` reference-yes;
- difference `-12.98pp`.

This diagnostic cannot authorize a gate and does not explain reference rejection.

## Scientific interpretation

v0.6.48 already showed that the frozen v0.6.18 candidate set has very low independent semantic precision. v0.6.49 now shows that this failure is **not cleanly attributable to any one of the existing candidate diagnostics**: publication maturity, span occupancy, cycle/amplitude balance, legacy path noise, or identity multiplicity.

The evidence therefore points upstream of another residual qualification gate. The current exact-ridge/published-five-anchor object appears not to map reliably onto the independently annotated semantic object, `two complete visibly comparable same-scale waves belonging to one parent structure near the right edge`.

The isolated `amplitude_unit_fraction` signal is retained as evidence, not as a threshold candidate.

## Verdict

`v0649_diffuse_or_fundamental_semantic_object_mismatch`

No qualification rule changes. No direction changes. No morphology/trade/production authority changes.

## Next authorized step

Freeze a **semantic-object / parent-representation audit** that asks whether the mismatch originates in the object itself — for example, anchor correspondence to independent reference pivots where available, parent-boundary placement, and whether the frozen algorithmic five-anchor tuple represents the same visible parent object as the reference annotators.

Do not mine a new residual gate from the 104 negative candidates and do not fit an amplitude-unit cutoff to v0.6.48 labels.
