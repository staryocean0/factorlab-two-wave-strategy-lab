# Two-Wave M0 Authority

Date: 2026-09-11

## Global scientific status

- Primary object: `two_wave_parent_structure_recognizer`.
- Target semantics: two complete same-scale waves -> parent `Range / UpTrend / DownTrend / Uncertain`.
- Independent morphology acceptance: **false**.
- Global status: `morphology_replication_not_yet_accepted`.
- Historical full-recognizer operational baseline: **v0.4.3** until full morphology acceptance.
- Qualification champion: **v0.6.18 path-gate demotion**.
- Parent-direction winner: **unset**.
- Strongest pooled-exact direction contribution: **v0.6.25 absolute-margin erosion-consensus rescue**.
- Trade authority: **false**.
- Production authority: **false**.

A component-level win never upgrades the whole recognizer. Rejected challengers remain evidence only; they do not become runtime authority.

## Frozen direction evaluation universe

All direction work from v0.6.21 onward uses the same strict same-financial-identity universe derived from the frozen v0.6.18 artifacts:

- filtered mutual-unique same-event pairs: `57,029`;
- published raw strict pairs: `29,453`;
- both-v0.6.18-qualified direction pairs: `1,462`;
- main view: `5m_offset_0`;
- four harmless 5-minute comparison offsets are diagnostic only and may never become runtime information.

Historical D1 on this universe has exact four-state agreement `95.7592%`, pooled decisive coverage `48.9056%`, decisive agreement `100%`, and zero opposite UpTrend/DownTrend conflicts.

## Current best direction contribution: v0.6.25

v0.6.25 remains the strongest pooled-exact contribution and the comparison base for Range-recovery research:

- exact agreement: `1402/1462 = 0.9589603283173734`;
- pooled decisive coverage: `0.7086183310533516`;
- decisive agreement: `1.0`;
- opposite-trend conflicts: `0`;
- Range decisive share: about `1.06%`.

It is **not** a direction winner because harmless-offset non-regression was not achieved and Range supply is too small.

## Direction / Range-recovery evidence chain

The following families have already been adjudicated and must not be silently retried under new names:

- endpoint D2 and confidence-gated D2: rejected;
- PAWCT absolute phase-aligned translated path: rejected;
- v0.6.10 scalar path efficiency/jump/roughness family: already measured;
- v0.6.21-v0.6.23 whole-window Huber and erosion-consensus rescue: useful information, no winner;
- v0.6.27 direct state-relative Range margin: rejected;
- v0.6.29 cycle-IQR overlap alone: rejected;
- v0.6.30/v0.6.31 stacked Range gates: rejected;
- v0.6.33 median-shift Range: rejected;
- v0.6.34 median-shift/IQR intersection: rejected;
- v0.6.35 bar-equal complete-cycle W1: rejected as a direction challenger;
- v0.6.37 phase-balanced W1: rejected as a direction challenger;
- nearby W1-ceiling tuning from v0.6.36: not authorized;
- simple v0.6.35 AND v0.6.37 weighting-consensus gate: not authorized.

### v0.6.35-v0.6.38: W1 family state

v0.6.35 produced `725` new Range rescues and exact agreement `1363/1462 = 93.2285%`; one-sided topology was `26 main-only / 24 other-only`. v0.6.36 found `43` introduced harms, `4` repairs and `3` persistent non-exact cases, so nearby `0.15` W1 tuning was forbidden.

v0.6.37 removed duration-proportional probability weighting by assigning each completed leg exactly `50%` cycle probability mass. It produced `621` new Range rescues, exact `1370/1462 = 93.7073%`, decisive agreement `100%`, and topology `61 both / 23 main-only / 21 other-only / 1357 none`. All four harmless offsets still regressed versus v0.6.25.

v0.6.38 attributed the v0.6.35 -> v0.6.37 change: `31` old non-exact pairs repaired, `24` old exact pairs harmed, net `+7`. The remaining v0.6.37 one-sided residuals were `38 introduced_harm / 6 repaired_old_nonexact`; shared bar-equal+phase-balanced rescues were `28 harm / 4 repair`, while phase-balanced-only rescues were `10 harm / 2 repair`.

### v0.6.39: order-sensitive residual shape — diagnostic complete

Formal result established that within-leg progress shape contains a local clue but cannot authorize a gate. On the 44 one-sided v0.6.37 residuals:

- `38` introduced harm;
- `6` repaired old non-exact;
- strongest descriptor was `first_leg_progress_l1` with `P(harm > repair) = 0.7478070175438597`;
- `first_leg_progress_linf` and `max_leg_progress_l1` were about `0.72149`;
- second-leg descriptors were weak, including `second_leg_progress_linf ~= 0.50658`.

Because there were only six repair rows, no shape-distance cutoff was authorized.

### v0.6.40: leg-asymmetry + harmless-slicing stability — route closed

v0.6.40 expanded the diagnostic population to `61` stable both-rescue controls plus the `44` one-sided residuals and tested the structural first-vs-second-leg asymmetry without fitting a cutoff.

Primary threshold-free rank results were weak:

- harm rescue `A_L1` vs stable-both pair mean: about `0.5336`;
- harm harmless-slicing `|delta A_L1|` vs stable-both: about `0.5216`;
- L-infinity analogues were likewise weak.

Conclusion: the apparent first-leg signal from v0.6.39 does not generalize into a stable equality/sign gate. The normalized progress-shape / leg-asymmetry candidate route is closed. Do not promote `first_leg_L1 <= second_leg_L1`, `A=0`, or a fitted shape threshold from these diagnostics.

### v0.6.41: cycle-drift sign topology — diagnostic complete, route closed

Formal workflow run: `34608353257`.
Formal result commit: `5c92809f7606519d03b83426671c7772b7a9a639`.

The run reproduced the frozen universe exactly and reconstructed the historical D1 phase steps from the already-published five raw occurrence bars using the frozen D1 formula; no pivot detector or direction threshold was changed.

Diagnostic universe remained `105` rescue-involved pairs = `61` stable both-rescue + `44` one-sided, with `38 harm / 6 repair`.

Frozen primary differences, harm minus stable controls:

- rescue-side same-direction cycle drift: `+0.06125970664365832`;
- rescue-side all-three migrations same direction: `+0.02804141501294219`;
- harmless-view cycle-relation flip: `+0.016824849007765305`;
- harmless-view all-three flip: `+0.02976704055220017`.

These effects are small and not a coherent separating mechanism. `gate_authorized=false`. The cycle-drift sign-topology route is closed; no structural sign veto is authorized.

## Current research rule

The parent-direction winner remains **unset**. v0.6.25 remains the strongest pooled-exact contribution. v0.6.18 remains the qualification champion.

The repeated v0.6.33-v0.6.41 evidence says the current Range-recovery problem is not solved by stacking more location, overlap, W1-ceiling, progress-shape, leg-asymmetry, or sign-topology gates. Before closing the complete W1/Range-recovery family, one final unadjudicated mechanism is authorized: determine whether harmless-slicing instability is materially caused by the **amplitude normalization denominator** rather than by the raw phase-balanced W1 numerator itself.

## Next authorized step: v0.6.42 amplitude-normalization stability attribution

Preregister and execute one **read-only v0.6.42 amplitude-normalization stability attribution** on the same v0.6.37 rescue-involved universe.

It must decompose, without fitting new thresholds:

- each side's frozen parent `amplitude_unit_price` and two detrended cycle amplitudes;
- phase-balanced W1 in raw price units across the existing four endpoint supports;
- the corresponding normalized W1 = raw W1 / amplitude unit;
- harmless-view changes in raw numerator versus amplitude denominator;
- for one-sided v0.6.37 rescues, counterfactual denominator/numerator swaps using only the already-frozen `0.15` W1 ceiling to classify whether the crossing can be explained by raw-W1 change, denominator change, either alone, or both together.

The `61` stable both-rescue pairs are the stability control group. The `38` introduced harms are the primary one-sided group. The six repairs remain descriptive only.

v0.6.42 is diagnostic only: no classifier, learned cutoff, new W1 ceiling, recognizer change, or subgroup-derived gate is allowed. Cross-offset quantities are diagnostic and may not enter runtime features.

If v0.6.42 does not reveal a clear denominator-instability mechanism distinct from the stable-both controls, the current W1 / Range-recovery family must be closed rather than extended with additional residual gates. If a strong denominator mechanism is found, any alternative parent-scale normalization must be a separately frozen future challenger before replay.

## Forbidden shortcuts

- retry endpoint D2 or confidence-gated D2;
- retry PAWCT absolute translated path as-is;
- relabel v0.6.10 scalar path metrics as a new signal;
- retune v0.6.25 margin, v0.6.29 overlap, v0.6.33 location shift, containment slack, or v0.6.35/v0.6.37 W1 ceiling;
- simple v0.6.35 AND v0.6.37 consensus gate;
- fit a shape-distance cutoff from v0.6.39;
- use v0.6.40 `A=0` / first-leg-vs-second-leg equality as a candidate gate;
- use v0.6.41 sign topology as a structural veto;
- combine weak residual diagnostics post hoc into a composite classifier;
- use harmless comparison offsets as runtime information;
- use future returns, P&L, H1/H2, third-wave outcomes, or later-period selection data for morphology decisions.

Independent morphology acceptance remains false. Trading and production remain closed.
