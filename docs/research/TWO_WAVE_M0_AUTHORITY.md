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

All current direction work uses the same strict same-financial-identity universe derived from the frozen v0.6.18 artifacts:

- filtered mutual-unique same-event pairs: `57,029`;
- published raw strict pairs: `29,453`;
- both-v0.6.18-qualified direction pairs: `1,462`;
- main view: `5m_offset_0`;
- four harmless 5-minute comparison offsets are diagnostic only and may never become runtime information.

Historical D1 on this universe:

- exact four-state agreement: `1400/1462 = 95.7592%`;
- decisive coverage: `48.9056%`;
- decisive agreement: `100%`;
- opposite UpTrend/DownTrend conflicts: `0`.

## Current best direction contribution: v0.6.25

v0.6.25 remains the strongest pooled-exact contribution:

- exact agreement: `1402/1462 = 0.9589603283173734`;
- pooled decisive coverage: `0.7086183310533516`;
- decisive agreement: `1.0`;
- opposite-trend conflicts: `0`;
- Range decisive share: about `1.06%`.

It is **not** a direction winner because harmless-offset non-regression was not achieved and Range supply is too small.

## Closed direction information families

The following families are already adjudicated and must not be silently retried under new names:

- endpoint D2 and confidence-gated D2: rejected;
- PAWCT absolute phase-aligned translated close path: rejected;
- v0.6.10 scalar close-path efficiency/jump/roughness/hidden-variation family: already measured;
- v0.6.21-v0.6.25 whole-window Huber / erosion-consensus family: useful contribution, no winner;
- v0.6.27-v0.6.32 state-relative Range margin, IQR overlap and mutual-median containment routes: rejected or diagnostic-only;
- v0.6.33-v0.6.42 median-shift / W1 / phase-balanced W1 / residual-shape / sign-topology / amplitude-normalization family: closed;
- time/duration geometry: already measured through v0.5.4/v0.5.5 and v0.6.19-v0.6.20; not a fresh direction information class;
- native same-bar high/low envelope excursion at the frozen five parent anchors: adjudicated and closed by v0.6.44;
- native open/body/gap geometry at the frozen five parent anchors: adjudicated and closed by v0.6.46.

### v0.6.35-v0.6.38: W1 route

v0.6.35 produced `725` new Range rescues and exact `1363/1462`; one-sided topology was `26 main-only / 24 other-only`. v0.6.36 found `43` introduced harms, `4` repairs and `3` persistent non-exact cases, so nearby W1-ceiling tuning was forbidden.

v0.6.37 phase-balanced W1 produced `621` new Range rescues, exact `1370/1462`, decisive agreement `100%`, and topology `61 both / 23 main-only / 21 other-only / 1357 none`; all four harmless offsets still regressed versus v0.6.25.

v0.6.38 found `38 introduced_harm / 6 repaired_old_nonexact` among the remaining one-sided residuals. No simple v0.6.35 AND v0.6.37 consensus gate was authorized.

### v0.6.39-v0.6.41: shape and sign routes

v0.6.39 found a local first-leg progress-shape clue, strongest `first_leg_progress_l1` with `P(harm > repair) = 0.7478070175438597`, but only six repairs existed and no cutoff was authorized.

v0.6.40 showed leg asymmetry did not generalize: harm-vs-stable ranks were about `0.5336` for rescue-side `A_L1` and `0.5216` for harmless-slicing `|delta A_L1|`. Route closed.

v0.6.41 cycle-drift sign topology also failed to form a coherent separator. Formal workflow run `34608353257`, result commit `5c92809f7606519d03b83426671c7772b7a9a639`. Route closed.

### v0.6.42: amplitude-normalization stability; W1 / Range-recovery family closed

Formal workflow run: `34612200264`.  
Formal result commit: `ce97db4b347ef55ea648a7a9d476c364ac12a298`.

Threshold-free harm-vs-stable ranks:

- amplitude-unit SRD: `0.547886108714409`;
- cycle-amplitude-imbalance SRD: `0.5599654874892148`;
- raw-W1 SRD: `0.6570319240724762`;
- normalized-W1 SRD: `0.6949956859361519`.

Frozen 38-harm counterfactual attribution:

- raw numerator change sufficient: `24`;
- amplitude denominator change sufficient: `4`;
- either component alone sufficient: `5`;
- both changes required: `5`.

No denominator-primary failure was established. `gate_authorized=false`. The v0.6.33-v0.6.42 W1 / Range-recovery residual-gating family is closed.

## v0.6.43: fresh direction information-class audit

Audit record: `docs/research/TWO_WAVE_DIRECTION_INFORMATION_CLASS_AUDIT_V0643.md`.

The audit established that time/duration geometry is not a pristine class: v0.5.4/v0.5.5 already measure corresponding-leg duration mismatch/ratio, mean-cycle duration and drift-per-mean-cycle-bar, while v0.6.19-v0.6.20 formally investigate duration geometry in qualification.

The materially distinct class identified at that stage was `native_high_low_envelope_excursion_at_frozen_parent_anchors`, leading only to the read-only v0.6.44 attribution.

The later v0.6.45 audit corrected one overstatement in v0.6.43/v0.6.44 governance: native `open` had not yet been formally enumerated, so the earlier phrase “price-only expansion exhausted” was premature.

## v0.6.44: native high/low envelope attribution — complete; route closed

Frozen protocol: `docs/research/TWO_WAVE_NATIVE_HIGH_LOW_ENVELOPE_DIRECTION_ATTRIBUTION_V0644_PROTOCOL.md`.  
Formal workflow run: `34616273360`.  
Raw formal result commit: `f4128a8ef1aaf6e1f1f205af64a9fef77302d19b`.  
Result card: `experiments/two_wave_native_high_low_envelope_direction_v0644/RESULT_CARD.md`.  
Governance adjudication: `experiments/two_wave_native_high_low_envelope_direction_v0644/ADJUDICATION.json`.

All hard controls reproduced exactly: `57,029` filtered, `29,453` raw strict, `1,462` both-v0.6.18-qualified, D1 exact `1,400`, v0.6.25 exact `1,402`.

Fixed v0.6.25 nonexact-vs-exact rank probabilities were `0.5080599144079886`, `0.4980266286257727`, `0.5578340466000951`, `0.4890632429862102`, and `0.5327983832620067` across the frozen high/low descriptors.

Positive stability-gain incidence was essentially identical (`0.5556348074179743` exact vs `0.55` nonexact), and nonexact median gain changed sign across offsets.

Final frozen category: `v0644_high_low_envelope_redundant_or_unstable`.

`gate_authorized=false`; `challenger_authorized=false`. The native frozen-anchor high/low route is closed.

## v0.6.45: non-close information-class audit — governance correction and final remaining market-bar class

Audit record: `docs/research/TWO_WAVE_NON_CLOSE_INFORMATION_CLASS_AUDIT_V0645.md`.

This audit explicitly corrected the prior completeness claim and inventoried the remaining causally available fields.

- **Volume** is not an authorized current research surface: CSI1000 index volume is mostly unavailable and may not be filled or manufactured.
- **Confirmation delay / `available_at` / execution clock** are causality metadata, not `Range/Trend` semantics.
- **Session/calendar span** is already scale/qualification context and cannot be repackaged as a new direction signal.
- **1m source-support/gap topology** is measurement/data-product provenance used for uncertainty bounds, not parent market-state semantics.
- **Cross-offset identity** remains diagnostic only.
- Native **open/body/gap** geometry at the already-frozen five parent anchors was the one remaining source-distinct market-price class not yet formally adjudicated.

v0.6.45 therefore authorized exactly one read-only, threshold-free follow-up: v0.6.46. It did not authorize a classifier.

## v0.6.46: native open/body/gap attribution — complete; route closed

Frozen protocol: `docs/research/TWO_WAVE_NATIVE_OPEN_BODY_GAP_DIRECTION_ATTRIBUTION_V0646_PROTOCOL.md`.  
Formal workflow run: `34618326900`.  
Raw formal result commit: `c71e9612a8dbc09aeefef5f85f2c208cdac60b8d`.  
Result card: `experiments/two_wave_native_open_body_gap_direction_v0646/RESULT_CARD.md`.  
Governance adjudication: `experiments/two_wave_native_open_body_gap_direction_v0646/ADJUDICATION.json`.

All frozen hard controls reproduced exactly:

- filtered pairs: `57,029`;
- raw strict pairs: `29,453`;
- both-v0.6.18-qualified pairs: `1,462`;
- D1 exact: `1,400`;
- v0.6.25 exact: `1,402`;
- v0.6.25 decisive agreement: `1.0`;
- opposite UpTrend/DownTrend conflicts: `0`.

The five pre-frozen v0.6.25 nonexact-vs-exact rank probabilities were:

- mean absolute anchor body: `0.4789586305278174`;
- absolute mean phase-oriented anchor body: `0.4865905848787446`;
- mean absolute opening gap: `0.5508559201141227`;
- open-adjustment harmless-view distance L1: `0.5259153590109368`;
- open stability gain L1: `0.5489895387541607`.

All five lie inside the pre-frozen `[0.40, 0.60]` redundancy band.

More importantly, replacing close-anchor phase migration with open-anchor migration made harmless-slicing stability **worse**, not better. Pooled median `open_stability_gain_l1 = close_view_distance - open_view_distance` was:

- v0.6.25 exact: `-0.04552300088588504`;
- v0.6.25 nonexact: `-0.03228363345938465`.

Positive-gain incidence was only `0.26105563480741795` exact and `0.2833333333333333` nonexact. The nonexact median was negative on all four harmless offsets:

- offset 1: `-0.03753271341579051`;
- offset 2: `-0.008874694440202807`;
- offset 3: `-0.060062886026750174`;
- offset 4: `-0.04717112905394007`.

By the pre-frozen A -> B -> C interpretation order, the formal category is:

`v0646_native_open_body_gap_redundant_or_unstable`

Interpretation: native open/body/gap is causally source-distinct, but it neither separates the existing v0.6.25 inconsistency nor improves harmless-slicing stability. The native-open route is closed.

`gate_authorized=false`  
`challenger_authorized=false`  
`recognizer_changed=false`  
`qualification_changed=false`  
`direction_winner_changed=false`

## Current research rule

- v0.6.18 remains the qualification champion.
- v0.6.25 remains the strongest pooled-exact direction contribution.
- parent-direction winner remains unset.
- W1 / Range-recovery residual-gating family is closed.
- duration/time-geometry repackaging is closed.
- normalized progress-shape / leg-asymmetry route is closed.
- cycle-drift sign-topology route is closed.
- amplitude-normalization route is closed.
- native frozen-anchor high/low envelope route is closed after v0.6.44.
- native frozen-anchor open/body/gap route is closed after v0.6.46.
- after the v0.6.45 governance correction and v0.6.46 adjudication, the **current market-bar price-input parent-direction expansion is genuinely exhausted**.
- **no v0.6.47 challenger is authorized**.

The next legitimate program step is **not another direction feature** from the current OHLC/clock/session/data-quality surface. Further progress should move to independent morphology validation / replication using frozen existing components, or to a separately justified new data modality with its own evidence-level audit before any candidate protocol.

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
- repackage duration, phase allocation, duration ratio or drift-per-bar as a fresh direction class;
- infer within-bar OHLC event ordering;
- move the frozen five parent anchors using high/low or open;
- fit high/low excursion or open/body/gap cutoffs from v0.6.44/v0.6.46 diagnostics;
- replace D1 with high/low or open-anchor phase steps without separately frozen authority;
- fill or impute missing index volume for parent direction;
- use missing-volume status as a morphology signal;
- use `available_at`, confirmation delay, session count, calendar span or source-support gaps as parent-direction semantics;
- use harmless comparison offsets as runtime information;
- create a v0.6.47 challenger by recombining the closed fields above;
- use future returns, P&L, H1/H2, third-wave outcomes, or later-period selection data for morphology decisions.

Independent morphology acceptance remains false. Trading and production remain closed.
