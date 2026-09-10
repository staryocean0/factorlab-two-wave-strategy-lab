# Two-Wave v0.6.22 D1-Primary Huber-Rescue Direction — Frozen Protocol

Date: 2026-09-10
Status: `frozen_before_v0622_replay`

## Research question

v0.6.21 whole-window Huber was rejected as a wholesale D1 replacement, but it retained a strong contribution: pooled decisive coverage increased from `48.9056%` to `84.2339%`, while pairs where both harmless 5m views were decisive agreed `100%` and produced zero UpTrend-vs-DownTrend conflicts.

Can this contribution be integrated directly into the same parent-state recognizer by keeping D1 as the primary decision and using the frozen v0.6.21 Huber result **only when D1 abstains**?

## Frozen upstream

Unchanged:

- v0.5.2 parent identity;
- v0.6.5 immutable raw publication;
- v0.6.18 qualification-policy champion;
- v0.6.0/v0.6.1 same-financial-identity matcher for evaluation only;
- D1 definition and thresholds;
- v0.6.21 Huber definition: all closes in complete parent span, `c=1.345`, 8 IRLS iterations, normalized by frozen amplitude unit, state thresholds `0.15 / 0.50`;
- 2015-2020 development material only;
- no future outcomes, returns, PnL, H1/H2, third wave or human labels.

## Single preregistered candidate

`v0622_D1_primary_Huber_rescue`

For one v0.6.18-qualified parent identity in one view:

1. compute frozen D1;
2. if D1 is `range`, `uptrend`, or `downtrend`, output D1 exactly;
3. only if D1 is `uncertain`, compute/use the frozen v0.6.21 Huber label;
4. if Huber is `range`, `uptrend`, or `downtrend`, output Huber;
5. otherwise remain `uncertain`.

In compact form:

`output = D1 if D1 != uncertain else Huber`

There is no weight, no probability blend, no threshold tuning, no candidate menu, and no cross-view information at runtime.

A hard invariant in tests and runner must prove that every D1-decisive record is unchanged by v0.6.22.

## Evaluation universe

Use exactly the same frozen v0.6.18 evaluation universe as v0.6.21:

- filtered mutual-unique same-event pairs: `57,029`;
- raw strict same-event pairs: `29,453`;
- both-v0.6.18-qualified direction pairs: `1,462`.

Historical D1 is the baseline diagnostic, not label truth.

## Metrics

Report D1 and v0.6.22, pooled and per offset:

- exact four-state cross-slicing agreement;
- decisive agreement when both sides are non-Uncertain;
- opposite UpTrend-vs-DownTrend conflicts;
- decisive coverage on each side and pooled;
- label counts and decisive class shares;
- number/fraction of D1-Uncertain records rescued by each Huber state;
- number of D1-decisive records overridden (must be zero).

## Frozen promotion gate

v0.6.22 becomes the current best-supported **parent-direction research component** only if ALL hold:

1. upstream controls reproduce exactly;
2. D1-decisive override count is exactly zero;
3. exact four-state agreement is non-worse than D1 on each of all four offsets;
4. pooled exact agreement improves over D1 by at least `+1.0 percentage point`;
5. opposite UpTrend-vs-DownTrend conflict count remains exactly zero;
6. pooled decisive agreement is at least `99%`;
7. pooled decisive coverage is at least `65%` and improves over D1 by at least `+15 percentage points`;
8. every offset-side decisive coverage is at least `55%`;
9. among pooled decisive candidate labels, UpTrend and DownTrend each account for at least `15%`, and Range accounts for at least `2%`.

The exact-agreement and coverage gates must both pass; coverage cannot compensate for instability and stability cannot be achieved by abstaining.

Pass verdict: `v0622_D1_primary_Huber_rescue_direction_research_component_pass`.
Otherwise: `v0622_D1_primary_Huber_rescue_direction_rejected`.

## Consequences

- v0.6.18 remains qualification-policy champion regardless of v0.6.22.
- If v0.6.22 passes, only the **direction research component** is promoted; the historical full-recognizer v0.4.3 record remains preserved.
- Independent morphology acceptance remains false until an independent morphology-label acceptance protocol is actually satisfied.
- If v0.6.22 fails, retain the v0.6.21 whole-window contribution and analyze the exact rescue failure mechanism; do not tune Huber thresholds post hoc in the same version.

`morphology_acceptance=false`
`future_outcome_used=false`
`trade_authority=false`
`production_authority=false`
