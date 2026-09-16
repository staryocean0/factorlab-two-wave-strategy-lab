# R7 complete trading-strategy baseline — cloud review

Date: 2026-09-16
Identity: `R7_trading_strategy_baseline_v1`
Dedicated GitHub Actions run: `35054743474`
Job: `104662426973`
Conclusion: `success`
Artifact: `10430560602`, digest `sha256:b672a09f98c5461f6bdf8af780ef6ce9dac0222a344057afb8eff9f491a99d41`

## Adjudication

`R7_OLD_BASELINE_EVALUATED_NOT_SUPPORTED_AT_2BPS_NO_RESCUE`

The strategy-engineering run itself is valid: frozen source identities matched, all five synthetic tests passed, parent candidate counts reproduced, the expanding fit used only strictly prior trading days, execution was delayed to the next native 1m open, execution stayed in-session, and no BLACKBOX/post-2020 data were read.

The economic acceptance gate failed at the frozen primary 2 bps one-way turnover stress.

## Formal OLD_BASELINE results

The formal OLD_BASELINE is daily causal expanding B1 with the original R7 feature identity and `clip(forecast_z,-1,+1)` continuous exposure.

| Cost | Total return | Ann. return | Sharpe | Max DD | 2019 | 2020 |
|---|---:|---:|---:|---:|---:|---:|
| 0 bps | +150.143% | +60.710% | 9.801 | -2.269% | +54.042% | +62.386% |
| 1 bp | +56.034% | +25.887% | 4.800 | -2.519% | +21.885% | +28.018% |
| 2 bps | -2.671% | -1.391% | -0.267 | -13.270% | -3.561% | +0.922% |
| 5 bps | -76.382% | -52.610% | -15.066 | -76.420% | -52.232% | -50.556% |

Primary 2 bps additional metrics:

- Sortino: -0.415
- Calmar: -0.105
- positive-day fraction: 42.916%
- positive-month fraction: 29.167%
- average daily turnover: 9.692x notional
- annualized turnover: 2442.35x notional
- cumulative explicit cost deduction: 0.94399 return units
- average absolute exposure: 0.14368
- long/short fractions: 52.10% / 47.90%
- trade intervals: 21,428 over 487 trading days

## Legacy static-B1 comparator

The fixed 2015-2018 coefficients tell the same economic story. At 0 bps total return is +156.690% and Sharpe 9.827; at 1 bp total return remains +57.617%; at 2 bps it falls to -3.220% with Sharpe -0.319; at 5 bps it falls to -77.598%.

Thus the failure is not caused by choosing expanding rather than static coefficients. The dominant strategy-engineering problem is turnover/cost sensitivity.

## Interpretation

R7 remains a supported predictive/mechanistic research finding: rejected native-1m excursion contains short-horizon reversal information conditional on endpoint displacement. This complete backtest adds a distinct result: **the naive continuous five-minute implementation does not survive the preregistered 2 bps turnover stress**.

The gross signal is economically large in the index proxy, but the implementation trades roughly 9.7x notional per day. Moving from 1 bp to 2 bps is enough to cross from strongly positive to slightly negative net economics. This makes transaction intensity, not a lack of gross predictability, the main issue for the next strategy layer.

This conclusion does not authorize a threshold search, lower-cost relabeling, favorable-year selection, horizon change, or execution-rule rescue under the same R7 identity.

## Next authorized research question

The requested next experiment is a Layer2 risk-conditioned composite challenger. It must preserve the frozen OLD_BASELINE execution/cost/evaluation contract and use a pre-existing, causally defined Layer2 risk state rather than a PnL-selected threshold. The scientific question is whether risk conditioning can improve net economics and risk enough to beat this exact baseline, especially by suppressing economically unproductive turnover/exposure without erasing the gross R7 edge.

Before challenger PnL is read, the Layer2 source identity, state definition, allowed coupling to R7, and head-to-head acceptance criteria must be frozen.

This remains an index-proxy development-material backtest, not fresh OOS, not an IM futures execution claim, and not production/paper-trading authority.
