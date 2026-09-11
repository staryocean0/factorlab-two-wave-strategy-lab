# Two-Wave v0.6.42 Amplitude-Normalization Stability Attribution Protocol

Date: 2026-09-11
Status: `frozen_before_implementation_and_replay_with_pre_result_semantic_clarification`
Mode: read-only mechanism attribution; no recognizer change

## 1. Question

v0.6.35 and v0.6.37 established that complete-cycle Wasserstein evidence supplies Range candidates but remains unstable across harmless 5-minute slicing. v0.6.39-v0.6.41 did not identify a stable residual gate in order-sensitive progress shape, leg asymmetry, or cycle-drift sign topology.

One mechanism remains unadjudicated before the current W1 / Range-recovery family is closed:

> Is harmful one-sided v0.6.37 Range rescue materially caused by instability in the frozen parent amplitude normalization denominator, rather than by the raw phase-balanced Wasserstein numerator itself?

v0.6.42 changes no direction classification and fits no threshold.

## 2. Frozen universe

Use the same v0.6.18 artifacts and same strict same-event pairing as v0.6.25-v0.6.41.

Hard controls must reproduce exactly:

- filtered mutual-unique same-event pairs: `57,029`;
- published raw strict pairs: `29,453`;
- both-v0.6.18-qualified direction pairs: `1,462`;
- main view: `5m_offset_0`;
- v0.6.37 pair-change topology: `61 both / 23 main_only / 21 other_only / 1,357 none`.

Diagnostic universe is the same `105` v0.6.37 rescue-involved pairs:

- `61` stable both-rescue pairs;
- `44` one-sided pairs.

One-sided semantics must remain:

- `introduced_harm = 38`;
- `repaired_old_nonexact = 6`;
- `persistent_nonexact = 0`.

Rescue origins must remain:

- `shared_bar_equal_and_phase_balanced_rescue = 32`;
- `phase_balanced_only_rescue = 12`.

Any hard-control drift invalidates the run.

## 3. Frozen measurements per side

For each published qualified record, reconstruct the existing v0.4/D1 pair only from its already-published raw occurrence bars and the frozen development bars. Do not rerun or alter the pivot detector.

Read from the reconstructed pair:

- `detrended_amplitudes_price = [amp1, amp2]`;
- `amplitude_unit_price = (amp1 + amp2) / 2` under the frozen historical formula.

Record:

1. `amp1_price`;
2. `amp2_price`;
3. `amplitude_unit_price`;
4. `cycle_amplitude_imbalance = 2*abs(amp1-amp2)/(amp1+amp2)`.

The imbalance is descriptive and threshold-free.

## 4. Frozen phase-balanced W1 decomposition

Reuse the exact v0.6.37 phase-balanced empirical W1 implementation and its four frozen endpoint-support views. Each complete cycle gives `50%` probability mass to its first leg and `50%` to its second leg.

For every support record:

- `raw_w1_price` = phase-balanced Wasserstein distance in raw price units;
- `normalized_w1` = `raw_w1_price / amplitude_unit_price`.

Per side report:

- `max_raw_w1_price` across the four supports;
- `mean_raw_w1_price` across the four supports;
- `max_normalized_w1` across the four supports;
- `mean_normalized_w1` across the four supports;
- inherited price-space ceiling `w1_ceiling_price = 0.15 * amplitude_unit_price`;
- `price_headroom = w1_ceiling_price - max_raw_w1_price`;
- `normalized_headroom = 0.15 - max_normalized_w1`.

The value `0.15` is not tuned in v0.6.42. It is the existing frozen v0.6.35/v0.6.37 Range-W1 ceiling and is used only to explain the already-observed crossing.

## 5. Frozen harmless-view difference representation

For non-negative quantities `a,b`, define the threshold-free symmetric relative difference:

`SRD(a,b) = 0 if a=b=0 else 2*abs(a-b)/(a+b)`.

For signed orientation of one-sided changes, define:

`signed_SRD(rescue, nonrescue) = 0 if both are zero else 2*(rescue-nonrescue)/(abs(rescue)+abs(nonrescue))`.

No empirical cutoff is applied to either quantity.

For each pair report harmless-view SRD for:

- amplitude unit;
- max raw W1;
- max normalized W1;
- cycle-amplitude imbalance.

## 6. Stable both-rescue controls

For each of the `61` stable both-rescue pairs, both harmless views must be v0.6.37 Range rescues.

Report distributions of:

- pair-mean amplitude unit;
- amplitude-unit SRD;
- max-raw-W1 SRD;
- max-normalized-W1 SRD;
- pair-mean cycle-amplitude imbalance;
- imbalance SRD.

These rows are the frozen stability control population.

## 7. One-sided rescue decomposition

For each of the `44` one-sided pairs preserve the same frozen `rescue_side` / `nonrescue_side`, semantic class and rescue origin used in v0.6.40-v0.6.41.

The changed rescue side must satisfy `max_normalized_w1 <= 0.15` because v0.6.37 changed only v0.6.25 `Uncertain -> Range` rows that pass all four frozen W1 supports.

Pre-result semantic clarification: the companion side has different meaning by semantic class.

- For the `38 introduced_harm` rows, v0.6.25 was exact before the one-sided rescue. Therefore the companion side was also v0.6.25 `Uncertain`; because it did not change under v0.6.37, it must fail the all-support W1 condition and has `max_normalized_w1 > 0.15`. These are the valid W1 crossing-attribution rows.
- For the `6 repaired_old_nonexact` rows, the unchanged companion may already be a v0.6.25 decisive `Range` row. Its unchanged state does not imply W1 failure because v0.6.37 never needs W1 to override a v0.6.25 decisive label. Repairs therefore remain descriptive only and are not forced into the counterfactual crossing categories.

Record on all 44 rows:

- rescue and companion amplitude units;
- rescue and companion max raw W1;
- rescue and companion max normalized W1;
- signed amplitude-unit SRD;
- signed max-raw-W1 SRD;
- signed max-normalized-W1 SRD;
- absolute SRDs for the same quantities;
- cycle-amplitude-imbalance quantities.

## 8. Frozen counterfactual crossing attribution on the 38 harm rows

Compute exactly two component-swap counterfactuals for each `introduced_harm` row. No new parameter is introduced.

### Raw-numerator change only

Use the rescue side's raw numerator with the companion non-rescue denominator:

`raw_only_normalized = rescue_max_raw_w1 / nonrescue_amplitude_unit`.

`raw_only_pass = raw_only_normalized <= 0.15`.

### Amplitude-denominator change only

Use the companion non-rescue side's raw numerator with the rescue denominator:

`denominator_only_normalized = nonrescue_max_raw_w1 / rescue_amplitude_unit`.

`denominator_only_pass = denominator_only_normalized <= 0.15`.

Assign exactly one categorical explanation:

1. `either_component_alone_sufficient` if both counterfactuals pass;
2. `raw_numerator_change_sufficient` if only `raw_only_pass`;
3. `amplitude_denominator_change_sufficient` if only `denominator_only_pass`;
4. `both_changes_required` if neither single-component swap passes while the actual rescue side passes.

This is attribution of the existing frozen crossing, not a new classifier.

The six repair rows receive no counterfactual category; they are reported descriptively only.

## 9. Frozen reporting

Report numeric summaries (count, mean, median, q25, q75, min, max) for the stable-both population and for one-sided rows pooled, by semantic class, and by rescue origin.

Primary threshold-free rank comparisons:

1. `P(harm amplitude_unit_SRD > stable amplitude_unit_SRD)`;
2. `P(harm max_raw_w1_SRD > stable max_raw_w1_SRD)`;
3. `P(harm max_normalized_w1_SRD > stable max_normalized_w1_SRD)`;
4. `P(harm imbalance_SRD > stable imbalance_SRD)`.

Use the same tie-aware probability definition as v0.6.39/v0.6.40: `P(H>S) + 0.5*P(H=S)`.

Also report for the `38` harmful one-sided rows:

- counterfactual attribution category counts/fractions;
- sign fractions of signed amplitude-unit SRD;
- sign fractions of signed raw-W1 SRD;
- sign fractions of signed normalized-W1 SRD.

The six repairs are descriptive only and cannot authorize a denominator rule.

## 10. Prohibited analysis

v0.6.42 must not:

- search or fit a new W1 ceiling;
- tune `0.15`;
- fit any amplitude-ratio or SRD cutoff;
- train logistic, tree, boosting, clustering, or composite models;
- combine v0.6.39-v0.6.41 weak diagnostics into a post-hoc score;
- modify v0.6.25 or v0.6.37 classifications;
- use comparison offsets as runtime features;
- use future outcomes, returns, P&L, H1/H2, third-wave behavior, or later-period selection data.

## 11. Decision consequence

v0.6.42 itself has `gate_authorized=false` and cannot promote a recognizer change.

After the frozen report:

- if harmful one-sided rows do **not** show a clear amplitude-denominator instability distinct from stable both-rescue controls, and counterfactual crossing attribution is not predominantly denominator-driven, close the current W1 / Range-recovery family rather than extending it with more residual gates;
- if a clear denominator mechanism is present, the only authorized continuation is a separately preregistered future challenger that defines an alternative parent-scale normalization before any replay. No formula may be selected post hoc from v0.6.42.

## 12. Authority held fixed

- qualification champion: v0.6.18;
- strongest pooled-exact direction contribution: v0.6.25;
- parent-direction winner: unset;
- independent morphology acceptance: false;
- trade authority: false;
- production authority: false.
