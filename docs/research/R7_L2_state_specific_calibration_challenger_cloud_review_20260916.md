# R7 × Layer2 state-specific calibration challenger — cloud review

Date: 2026-09-16

Identity: `R7_L2_state_specific_calibration_challenger_v1`

Formal adjudication: `R7_L2_CHALLENGER_EVALUATED_NOT_PROMOTED_NO_RESCUE`

## 1. Execution identity

- execution head: `40c19410319b8c75959b1abeb439d424942d095c`
- dedicated run: `35058115791`
- job: `104672459346`
- workflow conclusion: success
- frozen synthetic tests: 5/5 passed
- artifact id: `10431138239`
- artifact digest: `sha256:721c035dd49e2d343e0be1f21ee3f595f6aac7dd5452c2b411c327e5d6c65a8f`
- OLD_BASELINE exact reproduction: passed
- state-specific strict-prior/full-rank audit: passed
- BLACKBOX/post-2020/fresh-OOS/paper/production/registry authority: all false

The scientific preanalysis/protocol/runner/tests/execution-freeze were committed before the real challenger runner executed.

## 2. Frozen challenger

The challenger changed one thing only relative to formal OLD_BASELINE:

- OLD_BASELINE: one global B1 OLS, refit once per evaluation day from all strictly prior candidate rows;
- challenger: two B1 OLS fits, one for frozen `LOW_RISK=NORMAL` and one for frozen `RISK_ACTIVE=UNSAFE|RECOVERING`, each refit once per evaluation day from strictly prior rows in the same bucket.

R7 features, Layer2 thresholds/state mapping, `clip(forecast_z,-1,+1)`, t+1-open / t+5-close execution, gap handling, no-overnight rule, turnover accounting, evaluation rows, and 0/1/2/5-bps cost panel were unchanged.

Evaluation state supply was 19,004 LOW_RISK rows and 2,424 RISK_ACTIVE rows. Every 2019–2020 evaluation row had a state; all state-specific fits were full rank and strictly prior-day.

## 3. Predictive diagnostic

State-specific expanding calibration modestly reduced prediction MSE in every preregistered diagnostic group:

| Group | OLD_BASELINE MSE | L2 challenger MSE | relative improvement |
|---|---:|---:|---:|
| VALIDATION | 1.6331093434 | 1.6321759038 | 0.0572% |
| 2019 | 1.7197174922 | 1.7195616775 | 0.0091% |
| 2020 | 1.5461447825 | 1.5444305179 | 0.1109% |

This is consistent with the earlier Layer2 diagnostic: the frozen risk state contains incremental information, but the incremental predictive gain is small.

## 4. Same-contract trading comparison

### Primary 2 bps

| Metric | OLD_BASELINE | L2 challenger | challenger change |
|---|---:|---:|---:|
| total return | -2.6713% | -1.0704% | +1.6010 pp |
| annualized return | -1.3913% | -0.5553% | improved, still negative |
| Sharpe | -0.2671 | -0.0978 | +0.1693 |
| max drawdown | -13.2702% | -13.0276% | +0.2426 pp |
| average daily turnover | 9.6918x | 9.9608x | **+2.78% worse** |
| cumulative explicit cost | 0.9440 | 0.9702 | higher |
| 2019 return | -3.5607% | -3.9546% | worse |
| 2020 return | +0.9222% | +3.0029% | better |

The challenger therefore improved pooled gross/predictive quality and the pooled 2-bps loss, but it did not solve the principal implementation problem: turnover increased rather than decreased. It also made 2019 worse and remained net-negative overall.

### Cost sensitivity

| Cost | OLD_BASELINE total return | L2 challenger total return |
|---|---:|---:|
| 0 bps | +150.1430% | +161.0066% |
| 1 bp | +56.0340% | +60.6918% |
| 2 bps | -2.6713% | -1.0704% |
| 5 bps | -76.3817% | -76.9184% |

The crossover remains between 1 and 2 bps. At the fixed primary 2-bps stress neither policy is economically supported.

## 5. Frozen promotion gates

Passed:

- OLD_BASELINE exact reproduction;
- complete/causal/full-rank state-specific fitting;
- challenger 2020 return > 0;
- challenger pooled total return > OLD_BASELINE;
- challenger Sharpe > OLD_BASELINE;
- challenger max drawdown no worse than OLD_BASELINE.

Failed:

- challenger total return > 0;
- challenger Sharpe > 0;
- challenger 2019 return > 0;
- challenger average daily turnover < OLD_BASELINE.

Because the promotion rule required all gates, the challenger is **not promoted**.

## 6. Research interpretation

Layer2 risk-state conditioning is scientifically useful as a calibration coordinate, but this particular low-capacity state-specific coefficient updater is not a solution to transaction-cost fragility. Its extra state-dependent coefficient movement slightly increases exposure and rebalancing, so the incremental gross edge is largely consumed by incremental turnover at realistic stress.

This result closes `R7_L2_state_specific_calibration_challenger_v1` under the preregistered no-rescue rule. Do not tune Layer2 thresholds, merge/split states, add risk multipliers, switch cadence, select 2020-like periods, or introduce rolling/decay/regularization under this identity.

For future strategy research, keep Layer2 as an available external state descriptor, but the next independent economic improvement must target the execution/turnover architecture under a new preregistered identity rather than rescuing this coefficient challenger.

## 7. Authority boundary

2019–2020 remains reusable validation material, not fresh OOS. This is an index-proxy research backtest, not actual IM futures execution. BLACKBOX remains unassigned. Paper trading, production, and registry mutation remain unauthorized.
