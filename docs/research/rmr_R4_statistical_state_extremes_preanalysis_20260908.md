# R4 preanalysis — statistical-state extremes and parent failure risk

Date: 2026-09-08  
Identity: `R4_statistical_state_extremes_stage1_v1`

R4 is an independent broad-program mechanism class that was present in the authority whitepaper before the R1/R2/R3 results. It is **not** a rescue of those lanes.

## Scientific distinction

A market statistic can revert toward its own normal region without price reverting.

Therefore R4 does **not** ask whether a statistic's next value is closer to zero. It asks:

> **At the same mature parent-structure event, does a statistical-state variable add stable causal information about parent structural failure versus same-direction extension beyond a simple geometry baseline?**

Property self-reversion may be reported descriptively only and cannot satisfy the price-path gate.

## Common event and evidence roles

Reuse the frozen broad Stage-1 parent surface:

- primary view: `5m_offset_0`;
- parent: mature, published M0 birth level L5;
- temporal maturity: each cycle 12–48 bars, pair span <=96;
- deterministic same-confirmation dedup: lexicographically smallest canonical identity;
- BUILD: 2015-01-05..2018-12-31 consumed development;
- chronological check: 2019 and 2020, not scientifically fresh;
- post-2020 unopened.

At each eligible L5 parent publication:

- event price = publication-time 5m close;
- failure boundary = already frozen parent structural failure boundary;
- distance = absolute log distance from event price to failure boundary;
- extension boundary = same distance from event price in the parent direction;
- outcome = `failure` first versus `extension` first on 5m close;
- censor at the earliest of next strictly later mature L5 publication minus one bar, event+96 bars, or calendar-year end;
- ambiguous/unresolved = censored.

Positive class is `failure`.

## Geometry baseline

Exactly two continuous features:

1. `abs_drift` — current parent normalized translation;
2. `log_amplitude = log(parent_amplitude_scale)`.

This baseline is common to all three R4 candidates. No candidate may get its own baseline.

## Past-only statistical-state normalization

For each mature L5 parent in chronological publication order:

- use the preceding 100 mature L5 observations only;
- current observation excluded;
- center = median;
- scale = median absolute deviation (MAD);
- robust z denominator = `1.4826 * MAD`;
- if fewer than 100 references, MAD <=0, or nonfinite: state unavailable and event excluded for that candidate;
- no full-sample normalization;
- no z threshold or extreme bucket is used in the probability model.

## Candidate A — path inefficiency state

Raw property: current parent `parent_eff` already defined by M0 geometry.

Past-only z:

`efficiency_z = robust_z(parent_eff)`

Oriented state:

`R4_A_inefficiency = -efficiency_z`

Predeclared interpretation: unusually low path efficiency / high roughness should raise parent failure risk.

Candidate model:

`geometry_baseline + R4_A_inefficiency`

Required fitted state coefficient sign: `>0`.

## Candidate B — lower-scale event-density state

Use the already frozen one-octave finer representation L3 only as an **activity count**, not as the deviation event and not as a price outcome.

At each L5 parent publication, count mature, deduplicated L3 publications whose confirmation bars are strictly in:

`(parent_confirmation_bar - 96, parent_confirmation_bar)`

No direction filter. No weighting. Window 96 is inherited from the old M0 maximum two-cycle pair span and was not selected from R4 outcomes.

Normalize the count with the same preceding-100-parent robust procedure:

`R4_B_event_density = robust_z(trailing_96bar_L3_count)`

Predeclared interpretation: unusually dense lower-scale structural activity should raise transition/failure risk.

Candidate model:

`geometry_baseline + R4_B_event_density`

Required state coefficient sign: `>0`.

## Candidate C — parent amplitude-state extremity

Raw property:

`log_amplitude = log(parent_amplitude_scale)`

Past-only robust z:

`amplitude_z = robust_z(log_amplitude)`

Oriented extremity:

`R4_C_amplitude_extremity = abs(amplitude_z)`

Predeclared interpretation: an unusually compressed or expanded parent amplitude relative to its own causal historical normal state marks state instability and should raise failure risk.

Candidate model:

`geometry_baseline + R4_C_amplitude_extremity`

Required state coefficient sign: `>0`.

No high/low side split is allowed in Stage-1 v1.

## Model and gate

For baseline and every candidate:

`StandardScaler + LogisticRegression(C=1, penalty=l2, solver=lbfgs, max_iter=1000)`

Fit on BUILD only. Score the unchanged fitted models on 2019 and 2020.

Each candidate independently qualifies for a future specialist review only if:

- resolved BUILD >=150;
- resolved 2019 >=50;
- resolved 2020 >=50;
- candidate pooled 2019–2020 Brier < geometry baseline;
- candidate pooled log-loss < geometry baseline;
- candidate Brier improves in both 2019 and 2020;
- standardized fitted state coefficient >0;
- all timing/source boundaries pass.

A qualifying candidate is **not** production or fresh OOS evidence. If multiple candidates qualify, do not combine them; write an explicit cross-candidate review first.

## Descriptive property reversion

For each state variable, the receipt may report:

- correlation of current robust state with next mature-L5 state;
- share of observations where absolute state moves closer to zero next time.

These fields are descriptive only and are excluded from the progression gate.

## Forbidden

- combine R4 A/B/C in one model;
- search the 100-parent normalization window;
- change the 96-bar density window;
- use z thresholds or extreme buckets;
- split amplitude high/low after results;
- add skewness, jump counts, RSI/MACD or order-flow proxies;
- change parent L5 / 5m view / failure-extension outcome;
- open post-2020 rows;
- select by PnL;
- call property self-reversion price alpha;
- rescue failure with HMM/Koopman/deep models under this identity.

If all three candidates fail, close the current broad Stage-1 mechanism sweep instead of automatically inventing R5/R6/R7 on the same consumed window.

Production authority remains `false`.
