# Round-2 theory intake — transitory component after an extreme intraday shock

Date: 2026-09-08  
Research identity: `T1_transitory_component_after_extreme_intraday_shock_v1`

Status: **THEORY INTAKE FROZEN / SUPPLY-ONLY CHECK ALLOWED / POST-EVENT OUTCOMES NOT YET AUTHORIZED**

## 1. Why this is an independent mechanism

Broad Stage-1 Round 1 closed without a promoted R1/R2/R3/R4 mechanism. This intake is not a rescue of those identities.

The literature gives a distinct mechanism family:

- extreme short-horizon price moves can be followed by reversal consistent with temporary price pressure / liquidity provision;
- short-term reversal returns have been interpreted as returns to liquidity provision;
- but price jumps can also represent information shocks and exhibit short-term continuation / underreaction;
- microstructure effects can make apparent reversal evidence fragile if the event definition is contaminated by transaction-price effects.

Therefore the scientifically relevant question is **not** “do large moves reverse?” It is:

> At the end of an already-observed extreme intraday move, does evidence that part of the shock has already retraced inside the event bar identify a larger transitory component and predict subsequent same-session reversal rather than equal-distance continuation?

This is a price-path symptom test. With the current data it must **not** be called direct liquidity identification, information-shock classification, or executable alpha.

## 2. Literature anchors fixed before any new outcome execution

1. Zawadowski, A. G., Andor, G., & Kertész, J. (2006), “Short-term market reaction after extreme price changes of liquid stocks,” *Quantitative Finance* 6(4), 283–295. DOI: `10.1080/14697680600699894`.
   - Reports significant reversal after large intraday price changes and discusses liquidity provision / spread effects.

2. Nagel, S. (2012), “Evaporating Liquidity,” *Review of Financial Studies* 25(7), 2005–2039. DOI: `10.1093/rfs/hhs066`.
   - Interprets short-term reversal returns as a proxy for liquidity provision and shows their expected returns rise in market turmoil.

3. Jiang, G. J., & Zhu, K. X. (2017), “Information Shocks and Short-Term Market Underreaction,” *Journal of Financial Economics* 124(1), 43–64. DOI: `10.1016/j.jfineco.2016.06.006`.
   - Shows that jumps used as information-shock proxies can predict continuation rather than reversal.

4. Park, J. (2009), “A Market Microstructure Explanation for Predictable Variations in Stock Returns following Large Price Changes,” *Journal of Financial and Quantitative Analysis*.
   - Shows that part of apparent reversal evidence can be driven by microstructure/sample-selection effects.

These references are used only to define an independent mechanism and failure risks. They do not authorize changing the empirical definition after seeing this repository’s results.

## 3. Current data feasibility

Available development material is CSI1000 (`000852.SH`) 2015-01-05..2020-12-31 only.

Relevant frozen package products:

- `data/development/5m_offset_0.parquet` — 70,114 rows, SHA256 `bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`;
- `data/development/1m_official.parquet` — 350,561 rows, SHA256 `755217afce9dec383e48cd46d591402fa90dc50897abeb3dc7097c9a18a109d4`.

`volume` is optional and mostly unavailable. It must not be filled. There is no order-book, bid/ask, trade-direction, or news field in the admitted package.

Consequently:

- direct liquidity-shock identification is unavailable;
- direct information-shock identification is unavailable;
- only a price-only, causally completed event-path symptom is admissible.

## 4. Evidence roles remain unchanged

No new data are opened by this intake:

- BUILD: 2015-01-05..2018-12-31, consumed development;
- CHECK_2019: 2019-01-01..2019-12-31, not fresh;
- CHECK_2020: 2020-01-01..2020-12-31, not fresh;
- post-2020: unopened / unavailable in this package.

This intake cannot claim fresh OOS.

## 5. Event definition frozen before supply check

Primary event surface: existing native `5m_offset_0` bars. No new 5m resampling is allowed.

For each completed 5m bar:

`r5 = log(close_5m / open_5m)`

Recent scale is computed causally from the immediately preceding 960 native 5m bars (20 nominal 48-bar sessions), excluding the current bar:

- center = median of prior `r5`;
- scale = `1.4826 * MAD(prior r5)`;
- require all 960 previous native bars and finite positive scale;
- no expanding/full-sample normalization;
- no volatility model or parameter search.

Extreme event threshold:

`abs(r5 - prior_median) / prior_robust_scale >= 5.0`

The `5.0` threshold is fixed as a literature-anchored extreme-move convention before this repository’s event supply is inspected. If supply is inadequate, the identity is currently untestable; the threshold is not relaxed.

Event sign:

`shock_sign = sign(r5)`

Zero-return bars are not events.

## 6. Fine-path alignment gate

The event must be explainable by the already-existing `1m_official` terminal replay; this is path inspection, not creation of a replacement 5m product.

For an event bar to be usable:

- exactly the native 1m observations belonging to that existing 5m interval must be identified by timestamp/session semantics;
- expected full-support event bar = five 1m terminal observations;
- the last admitted 1m close must equal the native 5m close within deterministic numerical tolerance;
- 1m timestamps must be unique and ordered;
- no missing 1m bar may be synthesized or forward/back-filled;
- no local 1m→5m OHLC product may be constructed and substituted for the native 5m row;
- any alignment mismatch fails the event closed.

A supply receipt must report aligned and rejected event counts/reasons before post-event outcomes may be read.

## 7. Single frozen mechanism variable

This identity gets **one** mechanism variable, not a basket of indicators.

At the end of the extreme 5m bar, using only its already-observed 1m path:

- let `p0 = log(open_5m)`;
- let `s = shock_sign`;
- for each admitted 1m terminal close `p_j`, define directed displacement `d_j = s * (p_j - p0)`;
- `peak_displacement = max_j d_j`;
- `terminal_displacement = s * (log(close_5m) - p0) = abs(r5)`;
- require `peak_displacement > 0` and `terminal_displacement > 0`;
- define

`within_bar_retrace_fraction = max(0, peak_displacement - terminal_displacement) / peak_displacement`.

It is bounded to `[0,1]` by construction.

Interpretation fixed in advance:

- larger value = a larger fraction of the event’s maximum directed excursion has already unwound before the 5m bar closes;
- frozen hypothesis direction: **larger `within_bar_retrace_fraction` should increase the probability of subsequent same-session reversal relative to equal-distance continuation**.

This variable is a price-path symptom only. Do not label it “liquidity” or “information” ex post.

## 8. Future outcome definition — frozen now, execution still forbidden

If and only if a separate supply/alignment gate later passes, the eventual binary first-passage outcome is already frozen here to prevent redesign after supply inspection.

Starting strictly after the event 5m close and ending at the same trading session close:

- reversal boundary = event 5m open price (full retracement of the completed shock);
- continuation boundary = in log space, one additional event displacement in the shock direction:
  `log(close_event) + shock_sign * abs(r5)`;
- positive label = reversal boundary hit first;
- negative label = continuation boundary hit first;
- if neither is hit before same-session close, the event is unresolved/censored;
- no overnight continuation;
- no use of future intrabar ordering inside a 5m bar unless a separately frozen 1m first-passage implementation is specified before outcome execution.

No 50% retracement parameter, no optimized horizon, and no after-the-fact session-time exclusion are allowed.

## 9. Future low-capacity comparison — frozen but not authorized

If supply passes, baseline and candidate must use exactly the same resolved rows.

Baseline event-time features only:

- signed shock direction (`+1/-1`);
- absolute robust shock severity;
- causal normalized native 5m session position / bars remaining to same-session close.

Candidate adds only:

- `within_bar_retrace_fraction`.

Frozen model form:

`StandardScaler + LogisticRegression(C=1, penalty=l2, solver=lbfgs, max_iter=1000)`

Fit on BUILD only. Apply the exact frozen model to 2019 and 2020 separately. No threshold selection or calibration.

## 10. Supply gate before any post-event outcome read

Only supply/alignment counts are authorized next.

Minimum aligned extreme-event supply required before outcome execution may be separately authorized:

- BUILD >= 150;
- 2019 >= 50;
- 2020 >= 50.

The supply check may read only current/past event data required to identify the extreme event and its completed 1m within-bar path. It must not read any post-event bar after the event close.

If any minimum fails, status becomes:

`T1_current_data_event_supply_insufficient`

and this exact threshold/path identity closes for the current 2015–2020 evidence. Do not lower `5.0`, reduce 960, add asymmetric sign thresholds, or search alternate views.

## 11. Eventual progression gate — frozen now

Even if supply later passes, T1 progresses only if all are true:

- resolved BUILD >= 150;
- resolved 2019 >= 50;
- resolved 2020 >= 50;
- candidate pooled Brier strictly below baseline;
- candidate pooled log-loss strictly below baseline;
- candidate Brier strictly improves in both 2019 and 2020;
- standardized coefficient on `within_bar_retrace_fraction` is strictly positive;
- all alignment/evidence/source gates pass.

A pass means only:

`candidate_for_dedicated_specialist_review`

It does not mean tradable strategy, fresh OOS, or production alpha.

## 12. Explicit forbidden moves

- no threshold search around 5 robust sigma;
- no changing 960-bar normalization after supply/results;
- no positive/negative shock split for selection;
- no first-30-minute / lunch / late-day favorable filtering after results;
- no RSI/MACD/Hurst/roughness/event-density add-ons;
- no combination with R1/R2/R3/R4 states;
- no volume fill, spread proxy, order-book proxy, or news proxy invented from OHLC;
- no claim that `within_bar_retrace_fraction` directly measures liquidity;
- no post-2020 access;
- no PnL selection;
- no paper trading / production;
- no rescue under the same identity if supply or frozen progression gates fail.

## 13. Next authorized action

Create and execute a **supply/alignment-only** audit for T1. Post-event price outcomes remain sealed until that receipt is cloud-reviewed and a separate outcome authorization is written.
