# R7 trading-strategy baseline — frozen preanalysis

Date: 2026-09-16
Identity: `R7_trading_strategy_baseline_v1`
Parent mechanism: `R7_native_1m_rejected_excursion_v1`
Research role: complete strategy-engineering baseline before any Layer2 risk-conditioned composite comparison.

## 1. Purpose

This stage converts the already-supported R7 mechanism into a complete causal research trading strategy and measures its historical economic behavior. It is no longer only a prediction/MSE experiment.

The result will become the immutable `OLD_BASELINE` comparator for the next Layer2 risk-control study. The Layer2 study must use the same data, feature identity, signal-to-position map, execution convention, cost panel, and evaluation period; only the preregistered risk-conditioning component may differ.

## 2. Governance boundary

The underlying data are `000852.SH` market-index development material, not a directly tradable IM futures execution feed. The data contract reports `instrument_type=market_index`, `signal_price_view=identity_index_point`, `fill_price_view=raw_pit`, `data_contract=cn_a_session_wall_clock_offset_v1`, `package_data_role=development_material`.

Therefore this run is an **index-proxy research backtest**, not a claim of directly executable IM futures PnL, slippage, capacity, or production readiness.

2015-01-05..2018-12-31 remains reusable TRAIN/history. 2019-01-01..2020-12-31 remains reusable VALIDATION/economic evaluation. Neither is fresh OOS. No BLACKBOX or post-2020 data may be read.

PnL is authorized in this frozen strategy-engineering stage only. PnL/Sharpe may adjudicate this frozen strategy implementation, but may not be used to alter or rescue the R7 feature identity, path length, forward horizon, sigma window, position map, execution lag, evaluation years, or transaction-cost panel.

## 3. Frozen signal identity

No feature search is allowed. R7 remains:

- official 5m endpoint anchor;
- exact same-session native 1m continuity;
- past path = 5 native 1m returns;
- forward mechanism horizon = 5 native 1m returns;
- causal sigma = previous 240 exact 1m returns RMS, shift 1;
- features = intercept + `endpoint_z` + `rejection_signed_z` only;
- no M0 structure cache, R5-B1, volume, high/low/order-book feature, regime model, or threshold search.

## 4. Two fixed coefficient policies

### 4.1 Legacy comparator

Fit B1 once on all 2015-2018 TRAIN candidates. Hold those coefficients fixed throughout 2019-2020. This preserves the historical comparator but is not the formal OLD_BASELINE because specialist Stage1 already documented calibration drift.

### 4.2 Formal OLD_BASELINE

Daily causal expanding OLS on the same B1 design. For every evaluation trading day D, fit once using only candidate rows whose `trading_day < D`. The resulting beta is frozen for every signal on D. Outcomes from D are not available to the D fit.

No rolling-window search, decay/half-life search, regularization, threshold, sign filter, time-of-day filter, year filter, magnitude filter, or validation-period local refit is allowed.

## 5. Frozen signal-to-position rule

For either coefficient policy:

`forecast_z = beta0 + beta_endpoint * endpoint_z + beta_rejection * rejection_signed_z`

`target_position = clip(forecast_z, -1.0, +1.0)`

Position is a continuous index-proxy exposure in notional units. No forecast threshold is used.

## 6. Frozen execution rule

At official endpoint t, R7 features use information through the close of native minute t. The strategy must not transact at that same close.

Primary proxy execution is:

- enter/rebalance at the **open of native minute t+1**;
- the five-bar forecast window runs through the **close of native minute t+5**;
- within-window return is `target_position * (close[t+5] / open[t+1] - 1)`;
- for two contiguous R7 windows on the same trading day whose signal endpoints differ by exactly 5 minutes, the prior position remains live from the prior window exit close to the next execution open, so gap carry is `old_position * (new_entry_open / old_exit_close - 1)` before the rebalance;
- the interval gross return is `(1 + gap_carry_return) * (1 + window_return) - 1`;
- all five future bars must be exact same-session native minutes already admitted by the R7 candidate construction;
- no overnight exposure;
- a discontinuity between adjacent R7 signal windows (including lunch/session gaps) forces flattening at the prior interval end, zero exposure through the gap, and a fresh opening at the next admitted interval.

This is deliberately delayed relative to the signal and is not changed after viewing PnL.

## 7. Frozen turnover and cost panel

Turnover is absolute change in target exposure. At the first admitted interval of a continuous block, opening turnover is `abs(position)`. Between contiguous 5-minute signal windows it is `abs(new_position - old_position)`. At a gap or end of trading day, the old position is flattened and pays `abs(old_position)` closing turnover; the next block starts from zero.

Net interval return at cost c is gross interval return less `turnover * c / 10000`.

Because no governed real IM execution-cost contract is present in this repository, this study freezes a transparent one-way turnover stress panel:

- 0 bps;
- 1 bp;
- **2 bps primary research stress**;
- 5 bps robustness stress.

These values are scenario stresses, not claims about actual IM commissions/slippage.

## 8. Evaluation period and metrics

Economic evaluation is fixed to 2019-2020 only. 2015-2018 initializes the models and is not counted in strategy PnL.

For both the legacy comparator and formal OLD_BASELINE, report at every cost level:

- total compounded return;
- annualized return from 252 trading days;
- annualized daily volatility;
- daily Sharpe, risk-free rate 0;
- daily Sortino;
- max drawdown;
- Calmar;
- positive-day fraction;
- positive-month fraction;
- average daily turnover and annualized turnover;
- cumulative explicit cost deduction;
- average absolute exposure;
- long / short / exactly-flat signal fractions;
- 2019 total return;
- 2020 total return.

Implementation diagnostics must also report candidate/trade counts, source-contract identity, and whether execution rows touch source rows marked `causal_flat_fill`. That diagnostic is descriptive only and cannot be used to remove unfavorable rows after PnL is known.

## 9. Pre-outcome acceptance rule

The formal OLD_BASELINE is `economically_supported_at_2bps_research_stress` only if all are true at the fixed 2 bps scenario:

1. 2019-2020 net compounded total return > 0;
2. net daily Sharpe > 0;
3. 2019 net compounded return > 0;
4. 2020 net compounded return > 0;
5. all causality, execution-lag, source-identity, and no-overnight tests pass.

Max drawdown and Calmar are mandatory reported metrics but are not assigned an arbitrary pass threshold after the fact. The 5 bps panel is robustness information, not a hidden replacement gate.

If any primary gate fails, the strategy is recorded as evaluated but unsupported. No threshold, feature, horizon, cost, favorable year, or favorable intraday subset may be changed to rescue it under the same identity.

## 10. Next-stage comparison contract

Only after this baseline is frozen and executed may Layer2 risk conditioning be tested. The next strategy must compare head-to-head against this exact OLD_BASELINE under identical 2019-2020 rows, execution lag, position cap, turnover accounting, cost panel, and metrics. Risk conditioning must earn improvement; baseline rules may not be weakened or changed for the challenger.

No BLACKBOX, paper trading, production authority, or registry mutation is granted by this run.
