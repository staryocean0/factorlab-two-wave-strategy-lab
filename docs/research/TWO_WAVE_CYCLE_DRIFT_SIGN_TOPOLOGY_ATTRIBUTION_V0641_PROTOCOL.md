# Two-Wave v0.6.41 Cycle-Drift Sign-Topology Attribution Protocol

Date: 2026-09-11
Status: frozen before implementation and replay
Mode: read-only diagnostic; no recognizer change

## Why this exists

v0.6.39 found a local order-sensitive clue in first-leg progress shape, but v0.6.40 showed that first-vs-second-leg shape asymmetry does not separate harmful one-sided v0.6.37 Range rescues from stable both-rescue controls: the primary rank statistics were near 0.5. Therefore the v0.6.39/v0.6.40 normalized-shape route is closed for candidate promotion.

The next unadjudicated information class is not another path distance. It is the **sign topology of the already-frozen two-cycle pivot migrations** that D1 defines as `phase_steps_in_amplitude_units`.

For five alternating pivots `x0..x4`, D1 defines:

- `s0 = (x2 - x0) / amplitude_unit`: net drift of complete cycle 1 on the starting envelope;
- `s1 = (x4 - x2) / amplitude_unit`: net drift of complete cycle 2 on the same starting envelope;
- `s2 = (x3 - x1) / amplitude_unit`: migration of the opposite envelope.

D1 uses magnitude thresholds when classifying these steps. v0.6.41 does **not** alter those thresholds and does **not** retry D2. It asks only whether Range-rescue instability is associated with the threshold-free sign topology of these already-published migrations.

## Frozen universe

Use the same frozen v0.6.18-qualified comparison universe as v0.6.25-v0.6.40:

- filtered matched pairs: `57,029`;
- raw strict pairs: `29,453`;
- both-v0.6.18-qualified pairs: `1,462`;
- main view: `5m_offset_0`;
- same four harmless 5-minute comparison offsets.

Reproduce v0.6.37 pair topology exactly:

- `both = 61`;
- `main_only = 23`;
- `other_only = 21`;
- `none = 1,357`.

Diagnostic universe: the same `105` v0.6.37 rescue-involved pairs:

- `61` stable both-rescue pairs;
- `44` one-sided pairs.

The one-sided semantic decomposition must remain:

- `introduced_harm = 38`;
- `repaired_old_nonexact = 6`;
- `persistent_nonexact = 0`.

## Frozen sign representation

For each side, use the frozen D1 `phase_steps_in_amplitude_units = [s0, s1, s2]`. Do not redetect pivots and do not add smoothing.

### Implementation clarification after the first pre-result replay failure

Formal run `34607412997` failed before producing any result because the frozen v0.6.18 replay artifacts do not serialize the derived `phase_steps_in_amplitude_units` field. They do serialize the five already-published raw pivot occurrence bars.

Therefore the replay reconstructs the omitted derived field **exactly from those published pivot bars and their observed closes using the original frozen D1 formula**:

- `legs = diff(pivot_bars)`;
- `cycles = [bar2-bar0, bar4-bar2]`;
- cycle amplitudes are the absolute middle-pivot deviations from the line joining each cycle's endpoints, exactly as in `same_scale_v04.evaluate_pair`;
- `amplitude_unit = mean(two cycle amplitudes)`;
- `s0 = (x2-x0)/amplitude_unit`;
- `s1 = (x4-x2)/amplitude_unit`;
- `s2 = (x3-x1)/amplitude_unit`.

This is an implementation repair only. No pivot is redetected, no new observation is introduced, and no descriptor, threshold, comparison, or decision rule below changes.

Use strict mathematical sign around zero only:

- positive if `s > 0`;
- negative if `s < 0`;
- zero only if exactly zero to numerical precision (`abs(s) <= 1e-12`).

No `0.15`, `0.10`, `0.05`, or other empirical/tuned magnitude boundary is part of v0.6.41.

Per side report these predeclared categorical descriptors:

1. `cycle_drift_relation`
   - `same_direction` if `s0` and `s1` have the same non-zero sign;
   - `opposite_direction` if they have opposite signs;
   - `contains_zero` otherwise.
2. `all_three_same_direction`
   - true only if `s0`, `s1`, and `s2` all have the same non-zero sign.
3. `opposite_envelope_agrees_when_cycles_coherent`
   - true if cycle drifts are `same_direction` and `s2` has that same sign;
   - false if cycle drifts are `same_direction` and `s2` has the opposite non-zero sign;
   - null otherwise.

These are topology descriptors, not a classifier.

## Frozen pair-level reporting

### Stable both-rescue pairs

For each of the 61 pairs report:

- main and comparison-side topology descriptors;
- whether `cycle_drift_relation` agrees across the two harmless views;
- whether `all_three_same_direction` agrees across the two views.

Aggregate:

- prevalence of each `cycle_drift_relation` category across all stable rescue sides;
- prevalence of `all_three_same_direction` across stable rescue sides;
- cross-view agreement fractions for both topology descriptors.

### One-sided pairs

For each of the 44 pairs define the same frozen `rescue_side` and `nonrescue_side` as v0.6.40.

Report by semantic class (`introduced_harm`, `repaired_old_nonexact`) and rescue origin:

- rescue-side category prevalence;
- non-rescue-side category prevalence;
- fraction where `cycle_drift_relation` changes across harmless slicing;
- fraction where `all_three_same_direction` changes across harmless slicing;
- fraction where rescue side is `same_direction` while non-rescue side is not;
- fraction where rescue side is `all_three_same_direction=true` while non-rescue side is false.

## Frozen primary comparisons

Primary diagnostic comparisons are categorical and threshold-free:

1. `harm_rescue_same_direction_rate - stable_rescue_side_same_direction_rate`;
2. `harm_rescue_all_three_same_direction_rate - stable_rescue_side_all_three_same_direction_rate`;
3. `harm_cycle_relation_flip_rate - stable_cycle_relation_flip_rate`;
4. `harm_all_three_flip_rate - stable_all_three_flip_rate`.

Repairs are descriptive only because there are only six rows.

No threshold search, logistic/tree model, p-value optimization, composite score, or subgroup-derived classifier is allowed.

## Distinction from previously rejected routes

v0.6.41 is not a retry of D2:

- D2 classifies whole-envelope translation using the frozen `0.15` magnitude tolerance;
- v0.6.41 does not classify and uses only sign relations around structural zero.

It is not PAWCT:

- no phase-grid price translation is computed.

It is not v0.6.39/v0.6.40:

- no within-leg normalized progress curve or shape distance is used.

It is not a retune of D1:

- D1 remains unchanged; its magnitude thresholds remain frozen.

## Decision boundary

v0.6.41 itself cannot authorize any classification change.

A later candidate may be considered only if the sign-topology evidence is coherent across stable-both controls and one-sided harm, with a mechanism expressible using structural sign/equality logic and no learned numeric cutoff. Any candidate must be separately preregistered and replayed over all 1,462 pairs.

If the primary comparisons are weak or contradictory, close the cycle-drift sign-topology route rather than combining it with another post-hoc gate.

## Authority held fixed

- qualification champion: v0.6.18;
- strongest pooled-exact direction contribution: v0.6.25;
- parent-direction winner: unset;
- independent morphology acceptance: false;
- trade authority: false;
- production authority: false;
- no future outcome/P&L;
- no harmless comparison offset as runtime information.
