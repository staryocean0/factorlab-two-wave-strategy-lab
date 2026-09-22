# R7 cost-tempo reversal research V1

Date: 2026-09-22
Identity: `R7_cost_tempo_reversal_research_v1`
Parent evidence checkpoint: `07b1f7c15a1d802110cccd921b7f8ea9a1811ec9`
Status at registration: new outcomes not read; OLD_BASELINE and closed Layer2 challenger outcomes already known.

## Research question

Can a slow-in-low-volatility / fast-in-high-volatility execution architecture earn more net return per unit turnover than the frozen R7 OLD_BASELINE? Separately, can a read-only options cost measurement adapter rank eligible same-underlying contracts by Delta-equivalent spread plus fees?

Longer holding and higher volatility are hypotheses, not guarantees of positive conditional expected return. Higher realized volatility does not guarantee narrower option spreads. A statistically supported index signal is not executable option alpha.

## Separation of responsibilities

- Layer2 risk state remains read-only. NORMAL is not an absolute low-volatility label. No changes to its states, thresholds, or probability model.
- This NEW Layer3 research family declares two path/target scales: 5 and 15 native minutes, observed at the existing official 5m endpoints. It creates no locally resampled K-line data product.
- Layer4 research projection determines economic action and later eligible option cost ranking. Option spreads are not new Layer3 factors.
- Existing R7 and Layer2 challenger identities, code, data, and rejected results remain immutable.

## Stage A: bounded index-proxy architecture experiment

Data: exactly the two frozen 2015-2020 development Parquets used by R7. TRAIN through 2018 initializes; 2019-2020 is reusable diagnostic evaluation, not fresh OOS. No post-2020 rows or new market downloads.

For H in {5,15}, generalize the R7 path formula to H native 1m returns. Use the earliest largest absolute excursion from the initial log close; endpoint and rejected excursion are divided by previous-240-exact-return RMS times sqrt(H). Target is the next-H-minute log close change on the same normalization. This is a NEW scale family, not proof that a 5m effect survives 15m.

Fit a global intercept/endpoint/rejection OLS separately at each H once per evaluation day from strictly earlier-day labels. No bucket beta refits, rolling windows, decay, regularization, signal direction filters, or hyperparameter sweep. Minimum history is 1000 rows and full rank at each H; otherwise fail closed.

Absolute-volatility tempo uses only the causal 1m RMS sigma. Split at the median of TRAIN sigma on eligible H=5 feature rows, with eligibility based on past continuity and scheduled session end, not future prices. Freeze the split before evaluation. sigma <= split means SLOW; sigma > split means FAST. This is a Layer3 consumer tempo variable, not a relabeling or modification of Layer2 risk states.

One position episode at a time. A selected horizon and position are locked until its scheduled endpoint; intermediate signals do not resize, flip, or extend it. Re-entry may occur at that endpoint for the next native open. Each episode pays both opening and closing turnover. No overnight/lunch carry. Missing required execution bars cause a data-integrity failure, not hindsight removal. End-of-session eligibility is determined from the published session clock.

Position remains clip(forecast_z,-1,+1). Proxy entry is next native minute open; exit is native minute t+H close. This is the OLD_BASELINE price convention for comparison, NOT proof of a positive one-minute latency: a bar-end label is not an open execution timestamp. No actual option fill claim is allowed.

Proxy economic admission screen, when enabled: sign(forecast) * expm1(forecast_z*sigma*sqrt(H))*10000 > 4 bp. Four bp is the predeclared round trip of the 2bp-per-side index stress, not an imported option average cost. This point-forecast screen is not a calibrated lower confidence bound. It is applied after the signal and is unchanged across cost panels.

Frozen arms:
1. OLD_BASELINE: exact archived continuous global expanding R7 comparator.
2. FAST_EPISODE: H=5, no economic screen.
3. FAST_COST: H=5, economic screen.
4. SLOW_COST: H=15, economic screen.
5. ADAPTIVE_COST: H=15 in low sigma and H=5 in high sigma, economic screen. This is the sole nominated challenger; no post-hoc winner substitution.

All arms use the same evaluation calendar, initial capital convention, exposure cap, and 0/1/2/5bp one-way scenario panel. Inactive days remain zero returns. The new episode arms share identical accounting. Compare FAST_EPISODE vs FAST_COST for admission effect; FAST_COST vs SLOW_COST vs ADAPTIVE_COST for tempo value. OLD_BASELINE comparison additionally includes the explicitly different episode architecture.

Mandatory outputs: source hashes, counts, old-result reproduction, strict-history audit, trade ledger, daily and monthly returns, total/CAGR/annual volatility/Sharpe/Sortino/Calmar/max drawdown, daily turnover, time-weighted exposure, positive-day/month fractions, annual results, gross-return-per-unit-turnover, break-even cost, selected horizon and sigma-state counts, and flat-fill diagnostics. Max drawdown is an episode-mark proxy until minute-account reconstruction; it must not be called tick/minute max drawdown.

Primary 2bp engineering support requires ADAPTIVE_COST total return >0, Sharpe >0, both 2019 and 2020 >0, total and Sharpe above OLD_BASELINE, drawdown no worse than OLD_BASELINE, and turnover below OLD_BASELINE. Incremental tempo support additionally requires total return at 2bp greater than BOTH FAST_COST and SLOW_COST. Numerical pass alone is not statistical significance, production readiness, or final option-strategy acceptance. Five-bp results are mandatory stress information, not grounds to change the primary fee.

## Stage B: read-only option measurement adapter

The existing `csi1000_option_lifecycle_cost_map@1.0` measurement is the reference:
`N_delta = abs(delta_forward) * same_month_IM_forward * contract_multiplier`
`identified_round_trip_bp = 10000 * ((ask-bid)*multiplier + fee_open + fee_close) / N_delta`.

Its historical 14 CNY/side is a versioned project fee assumption, not a verified current broker fee. Current actual fee inputs must be explicit. Compare spread plus fees, not fee/premium alone.

The workflow `docs/user/csi1000_option_lifecycle_cost_map_v1_workflow.md` explicitly revokes feeding a sample-average hurdle into strategy/backtest routing. The successor is the option instrument identity profile. Reuse the measurement primitive/cards only; do not revive its revoked average-cost authority or mutate the upstream tool.

Eligible candidates must have the same underlying and requested directional exposure, known positive multiplier/forward, abs(delta)>=0.05, finite valid bid/ask and Greeks, PIT timestamps, unexpired contracts, explicit fees, and a risk/capital/liquidity mandate. Cheapness does not override Gamma/Vega/Theta, premium budget, integer lots, quote freshness, or minimum-depth requirements. No naked option selling is introduced. A held contract is not switched just because another becomes marginally cheaper.

Stage-B initial output is a ranked MEASUREMENT card list only, with complete_all_in_cost_ready=false when impact is unidentified. It must not emit orders, authorize live routing, or masquerade as an actual option backtest. Full-account option acceptance requires real entry Ask / exit Bid (spread is then NOT separately deducted), explicit fees, integer lots, capital/PnL and Greeks attribution; Theta is not charged twice.

MO started on 2022-07-22. The 2015-2020 proxy cannot be historical MO trading. A separately admitted, bounded real-MO replay cohort and consumer grant must be frozen before option outcomes are read. Existing later-period infrastructure summaries do not grant that access.

## Stopping and interpretation

If the frozen tempo fails, preserve the measured result; do not choose new horizon pairs, sigma quantiles, fee assumptions, or profitable subperiods under V1. Any follow-up is a new predeclared experiment. Unknown option execution capacity or missing future option quotes are not evidence of profitability.

Production, real orders, paper trading, registry mutation, post-2020 R7 outcome access and fresh-OOS claims remain false.
