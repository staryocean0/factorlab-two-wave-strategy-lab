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

v0.6.25 remains the strongest pooled-exact contribution:

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

v0.6.37 removed duration-proportional probability weighting by assigning each complete cycle's first leg `50%` probability mass and second leg `50%`. It produced `621` new Range rescues, exact `1370/1462 = 93.7073%`, decisive agreement `100%`, and topology `61 both / 23 main-only / 21 other-only / 1357 none`. All four harmless offsets still regressed versus v0.6.25.

v0.6.38 attributed the v0.6.35 -> v0.6.37 change: `31` old non-exact pairs repaired, `24` old exact pairs harmed, net `+7`. Remaining v0.6.37 one-sided residuals were `38 introduced_harm / 6 repaired_old_nonexact`; shared bar-equal+phase-balanced rescues were `28 harm / 4 repair`, phase-balanced-only rescues `10 harm / 2 repair`.

### v0.6.39: order-sensitive residual shape — diagnostic complete

On the 44 one-sided v0.6.37 residuals, the strongest descriptor was `first_leg_progress_l1`, with `P(harm > repair) = 0.7478070175438597`; first-leg L-infinity and max-leg L1 were about `0.72149`, while second-leg descriptors were weak. Only six repair rows existed, so no shape-distance cutoff was authorized.

### v0.6.40: leg-asymmetry + harmless-slicing stability — route closed

Using the `61` stable both-rescue controls plus the `44` one-sided residuals, the first-vs-second-leg asymmetry did not generalize:

- harm rescue `A_L1` vs stable-both rank: about `0.5336`;
- harm harmless-slicing `|delta A_L1|` vs stable rank: about `0.5216`.

The normalized progress-shape / leg-asymmetry candidate route is closed. Do not promote `A=0`, `first_leg_L1 <= second_leg_L1`, or a fitted shape cutoff.

### v0.6.41: cycle-drift sign topology — route closed

Formal workflow run: `34608353257`.
Formal result commit: `5c92809f7606519d03b83426671c7772b7a9a639`.

The frozen universe reproduced exactly. Primary harm-minus-stable differences were small:

- rescue-side same-direction cycle drift: `+0.06125970664365832`;
- rescue-side all-three migrations same direction: `+0.02804141501294219`;
- harmless-view cycle-relation flip: `+0.016824849007765305`;
- harmless-view all-three flip: `+0.02976704055220017`.

`gate_authorized=false`. No structural sign veto is authorized.

### v0.6.42: amplitude-normalization stability — diagnostic complete; W1 / Range-recovery family closed

Formal workflow run: `34612200264`.
Formal result commit: `ce97db4b347ef55ea648a7a9d476c364ac12a298`.
Formal attribution: `v0642_amplitude_normalization_stability_attribution_complete_no_gate_authorized`.

The run reproduced the full frozen controls exactly: `57,029` filtered pairs, `29,453` raw strict pairs, `1,462` both-v0.6.18-qualified pairs, and v0.6.37 topology `61 both / 23 main-only / 21 other-only / 1,357 none`. Diagnostic universe remained `105` pairs = `61` stable both-rescue + `44` one-sided, with `38 harm / 6 repair`.

The amplitude denominator was **not** the dominant harmless-slicing instability mechanism:

- `P(harm amplitude_unit_SRD > stable) = 0.547886108714409`;
- `P(harm cycle_amplitude_imbalance_SRD > stable) = 0.5599654874892148`;
- by contrast, `P(harm max_raw_W1_SRD > stable) = 0.6570319240724762`;
- `P(harm max_normalized_W1_SRD > stable) = 0.6949956859361519`.

The median amplitude-unit SRD was only `0.041867293607276576` for harm versus `0.035764690547654264` for stable controls. Harm raw-W1 SRD was more separated: median `0.18650017680358333` versus stable `0.12271540699230692`.

The frozen 38-harm numerator/denominator swap attribution was decisive against a denominator-primary explanation:

- `raw_numerator_change_sufficient = 24/38 = 63.1579%`;
- `amplitude_denominator_change_sufficient = 4/38 = 10.5263%`;
- `either_component_alone_sufficient = 5/38 = 13.1579%`;
- `both_changes_required = 5/38 = 13.1579%`.

Thus a raw-numerator swap alone was sufficient in `29/38 = 76.3158%` when the five `either` rows are included, while a denominator swap alone was sufficient in only `9/38 = 23.6842%`. Rescue-side amplitude units were not directionally coherent (`57.8947%` higher, `42.1053%` lower), whereas rescue max raw W1 was lower than the non-rescue companion in `92.1053%` of harm rows.

Conclusion: no clear amplitude-normalization-denominator failure exists that can motivate a separately frozen alternative normalization challenger. `gate_authorized=false`. **The v0.6.33-v0.6.42 W1 / Range-recovery residual-gating family is closed.** Do not continue by inventing additional W1 normalization, residual, threshold, shape, sign, or gate combinations from these rows.

## Current research rule

- v0.6.18 remains the qualification champion.
- v0.6.25 remains the strongest pooled-exact direction contribution.
- parent-direction winner remains unset.
- no current Range-recovery challenger is authorized.
- the current W1 / Range-recovery family is closed.

The next work must begin with a **fresh, read-only direction information-class audit** over the existing repository and evidence ledger. Its job is to identify whether any genuinely unmeasured causal morphology information class remains after D2, PAWCT, scalar path descriptors, Huber/erosion evidence, location/IQR/containment, W1 weighting/normalization, normalized progress shape, leg asymmetry, and sign topology. It is not authorized to create an empirical candidate merely by recombining existing rejected features.

No v0.6.43 recognizer challenger is currently authorized. A future challenger requires a separately frozen mechanism that is demonstrably distinct from the closed families.

## Forbidden shortcuts

- retry endpoint D2 or confidence-gated D2;
- retry PAWCT absolute translated path as-is;
- relabel v0.6.10 scalar path metrics as a new signal;
- retune v0.6.25 margin, v0.6.29 overlap, v0.6.33 location shift, containment slack, or v0.6.35/v0.6.37 W1 ceiling;
- simple v0.6.35 AND v0.6.37 consensus gate;
- fit a shape-distance cutoff from v0.6.39;
- use v0.6.40 leg-asymmetry equality as a candidate gate;
- use v0.6.41 sign topology as a structural veto;
- alter parent amplitude normalization based on v0.6.42;
- mine more residual gates from the 44 one-sided v0.6.37 rows;
- combine weak residual diagnostics post hoc into a composite classifier;
- use harmless comparison offsets as runtime information;
- use future returns, P&L, H1/H2, third-wave outcomes, or later-period selection data for morphology decisions.

Independent morphology acceptance remains false. Trading and production remain closed.
