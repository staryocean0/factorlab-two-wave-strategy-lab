# R7 × Layer2 state-specific calibration trading challenger — frozen preanalysis

Date: 2026-09-16
Identity: `R7_L2_state_specific_calibration_challenger_v1`
Parent strategy comparator: `R7_trading_strategy_baseline_v1` formal `OLD_BASELINE`
Layer2 reference: `R7_layer2_5m_risk_state_reference_contract_v1`

## Purpose

Test one low-capacity Layer2-conditioned challenger against the already frozen OLD_BASELINE without changing R7 features, the Layer2 state machine, execution, cost accounting, evaluation years, or the signal-to-position map.

This is an index-proxy research backtest on reusable 2019–2020 validation material, not fresh OOS and not an IM futures execution claim.

## Frozen challenger

The only challenger change is the coefficient update rule. Keep the frozen two-bucket map:

- `LOW_RISK = NORMAL`
- `RISK_ACTIVE = UNSAFE or RECOVERING`

For every evaluation trading day D and for each bucket independently, fit B1 OLS `[intercept, endpoint_z, rejection_signed_z]` using all state-matched candidate rows in that same bucket with `trading_day < D`. The fitted bucket beta is used for every signal in that bucket on D. No outcome from D is available to the D fit.

This is daily causal expanding OLS. There is no rolling window, decay/half-life, regularization, shrinkage, threshold, multiplier, sign filter, magnitude filter, intraday filter, or favorable-period selection. If either bucket lacks a full-rank prior design, execution fails rather than changing the rule.

Forecast and position remain exactly:

`forecast_z = beta0_bucket + beta_endpoint_bucket * endpoint_z + beta_rejection_bucket * rejection_signed_z`

`target_position = clip(forecast_z, -1, +1)`

No risk bucket is automatically flattened. Layer2 enters only through the preregistered state-specific coefficient update permitted by the prior cloud review.

## Frozen OLD_BASELINE comparator

Recompute the exact formal OLD_BASELINE in the same run: one global daily causal expanding B1 fit using only rows with `trading_day < D`, then `clip(forecast_z,-1,+1)`.

The run must reproduce the archived 2 bps OLD_BASELINE metrics within numerical tolerance before challenger adjudication:

- total return `-0.026713436670182222`
- Sharpe `-0.2670672170031825`
- 2019 return `-0.03560696616960668`
- 2020 return `+0.00922189313634858`
- average daily turnover `9.691847216614384`
- max drawdown `-0.13270195650953243`

## Execution and cost contract

Identical to OLD_BASELINE:

- signal at official 5m endpoint t after native 1m close t;
- enter/rebalance at native 1m open t+1;
- window exit at native 1m close t+5;
- contiguous 5m windows carry the old position across close-to-next-open gap before rebalance;
- non-contiguous blocks and end of day flatten;
- no overnight exposure;
- turnover is absolute exposure change plus block open/close;
- one-way cost panel is 0, 1, 2, 5 bps;
- 2 bps is the fixed primary research stress;
- economic evaluation is 2019–2020 only.

The challenger and OLD_BASELINE must use identical evaluation rows and execution prices.

## Pre-outcome diagnostics

Report pooled VALIDATION, 2019, and 2020 MSE for OLD_BASELINE expanding forecasts and challenger state-specific expanding forecasts. These are diagnostics; no rule may be changed after seeing them.

Report bucket supply, state match completeness, per-day strict-history audit, first/last bucket betas, and the same trading metrics as the baseline cost panel.

## Frozen promotion rule at 2 bps

`R7_L2_CHALLENGER_PROMOTED_NEW_RESEARCH_BASELINE` only if all are true:

1. OLD_BASELINE reproduction passes;
2. state mapping is complete on all 2019–2020 evaluation rows and both bucket fits are strictly prior-day/full-rank;
3. challenger total net return > 0;
4. challenger daily Sharpe > 0;
5. challenger 2019 net return > 0;
6. challenger 2020 net return > 0;
7. challenger total net return > OLD_BASELINE total net return;
8. challenger Sharpe > OLD_BASELINE Sharpe;
9. challenger average daily turnover < OLD_BASELINE average daily turnover;
10. challenger max drawdown is no worse than OLD_BASELINE (numerically greater/equal because drawdowns are negative).

If any gate fails, adjudicate `R7_L2_CHALLENGER_EVALUATED_NOT_PROMOTED_NO_RESCUE`. No threshold, bucket map, cadence, cost, year, feature, position map, or execution rule may be changed under this identity.

## Authority boundary

PnL/Sharpe are authorized only to adjudicate this single frozen challenger against the frozen OLD_BASELINE; they are not authorized to search alternative Layer2 mappings or model hyperparameters. No BLACKBOX, post-2020 data, paper trading, production, or registry mutation is authorized.
