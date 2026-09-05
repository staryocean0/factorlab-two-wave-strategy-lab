"""Governed Black-76 engine for premium-style CFFEX index options.

CFFEX IO/HO/MO buyers pay premium and sellers post margin.  The corresponding
same-month index-future settlement is used as the observed forward.  Black-76
therefore still needs an explicit discount curve.  Model rho is reported with
the observed forward held constant; it is not an official exchange Greek and
does not include the separate response of the index future to interest rates.

Time to expiry is actual/365.25 from the quote session close (15:00) to the
contract metadata expiry session close.  Calendar-rule expiry remains available
only as an explicit fallback for unit tests and diagnostics.
"""

from __future__ import annotations

import calendar
import math
from datetime import date

import numpy as np
import pandas as pd
from scipy.special import ndtr

OPTION_TO_FUTURE = {"IO": "IF", "HO": "IH", "MO": "IM"}
TICK_SIZE = 0.2
SIGMA_MIN = 1.0e-6
SIGMA_MAX = 5.0
PRICE_TOLERANCE = 0.5 * TICK_SIZE
ACT_365_25 = 365.25
IV_STATUS_OK = "ok"
RISK_FREE_SERIES_ID = "cn_treasury_yield_1y"
MAX_RATE_STALENESS_DAYS = 4
CURVE_TENOR_YEARS = {"3m": 0.25, "6m": 0.50, "1y": 1.0}


def third_friday(year: int, month: int) -> date:
    """Return the calendar third Friday of a month."""

    first_weekday, _ = calendar.monthrange(year, month)
    first_friday = 1 + (calendar.FRIDAY - first_weekday) % 7
    return date(year, month, first_friday + 14)


def last_trading_day(
    year: int,
    month: int,
    trading_days: set[str],
) -> tuple[date, str]:
    """Map a CFFEX contract month to its last trading day."""

    candidate = third_friday(year, month)
    iso = candidate.isoformat()
    if not trading_days:
        return candidate, "calendar_third_friday_unadjusted"
    ordered = sorted(trading_days)
    calendar_min = ordered[0]
    calendar_max = ordered[-1]
    if iso < calendar_min or iso > calendar_max:
        return candidate, "calendar_third_friday_unadjusted"
    if iso in trading_days:
        return candidate, "third_friday_is_trading_day"
    following = [item for item in ordered if item > iso]
    if not following:
        return candidate, "calendar_third_friday_unadjusted"
    return date.fromisoformat(following[0]), "next_trading_day_after_third_friday"


def years_to_expiry(trading_day: date, last_trade: date) -> float:
    """Actual/365.25 years from session close to last-trading-day close."""

    return float((last_trade - trading_day).days) / ACT_365_25


def matching_future_symbol(option_product: str, underlying_symbol: str) -> str:
    future_product = OPTION_TO_FUTURE.get(str(option_product))
    if future_product is None:
        raise ValueError(f"unsupported CFFEX option product: {option_product}")
    suffix = str(underlying_symbol)[len(str(option_product)) :]
    return f"{future_product}{suffix}"


def _norm_cdf(values: np.ndarray) -> np.ndarray:
    return ndtr(values)


def _norm_pdf(values: np.ndarray) -> np.ndarray:
    return np.exp(-0.5 * np.square(values)) / math.sqrt(2.0 * math.pi)


def black76_undiscounted(
    forward: np.ndarray,
    strike: np.ndarray,
    years: np.ndarray,
    sigma: np.ndarray,
    is_call: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return price, delta, gamma, vega-per-vol, theta-per-year."""

    sqrt_t = np.sqrt(np.maximum(years, 0.0))
    safe_sigma = np.clip(sigma, SIGMA_MIN, SIGMA_MAX)
    variance_term = np.maximum(safe_sigma * sqrt_t, SIGMA_MIN)
    log_moneyness = np.log(np.maximum(forward, SIGMA_MIN) / np.maximum(strike, SIGMA_MIN))
    d1 = (log_moneyness + 0.5 * np.square(safe_sigma) * years) / variance_term
    d2 = d1 - variance_term
    call = forward * _norm_cdf(d1) - strike * _norm_cdf(d2)
    put = strike * _norm_cdf(-d2) - forward * _norm_cdf(-d1)
    price = np.where(is_call, call, put)
    delta = np.where(is_call, _norm_cdf(d1), _norm_cdf(d1) - 1.0)
    density = _norm_pdf(d1)
    gamma = density / (np.maximum(forward, SIGMA_MIN) * variance_term)
    vega = forward * density * sqrt_t
    theta = -forward * density * safe_sigma / (2.0 * np.maximum(sqrt_t, SIGMA_MIN))
    return price, delta, gamma, vega, theta


def black76_discounted(
    forward: np.ndarray,
    strike: np.ndarray,
    years: np.ndarray,
    sigma: np.ndarray,
    is_call: np.ndarray,
    risk_free_rate: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return discounted price and Greeks with the observed forward held fixed.

    ``risk_free_rate`` is a continuously compounded decimal rate.  Rho is per
    unit rate change (1.00 == 100 percentage points); callers also publish a
    per-basis-point view by dividing it by 10,000.
    """

    base_price, base_delta, base_gamma, base_vega, base_theta = black76_undiscounted(forward, strike, years, sigma, is_call)
    safe_years = np.maximum(np.asarray(years, dtype=float), 0.0)
    rates = np.asarray(risk_free_rate, dtype=float)
    discount = np.exp(-rates * safe_years)
    price = discount * base_price
    delta = discount * base_delta
    gamma = discount * base_gamma
    vega = discount * base_vega
    theta = discount * base_theta + rates * price
    rho = -safe_years * price
    return price, delta, gamma, vega, theta, rho


def invert_black76_iv(
    premium: np.ndarray,
    forward: np.ndarray,
    strike: np.ndarray,
    years: np.ndarray,
    is_call: np.ndarray,
    risk_free_rate: np.ndarray | None = None,
    *,
    tick: float = TICK_SIZE,
) -> tuple[np.ndarray, np.ndarray]:
    """Invert futures-style Black-76 IV with Newton plus bisection fallback."""

    premium = np.asarray(premium, dtype=float)
    forward = np.asarray(forward, dtype=float)
    strike = np.asarray(strike, dtype=float)
    years = np.asarray(years, dtype=float)
    is_call = np.asarray(is_call, dtype=bool)
    rates = np.zeros_like(premium, dtype=float) if risk_free_rate is None else np.asarray(risk_free_rate, dtype=float)
    size = premium.shape[0]
    sigma = np.full(size, np.nan, dtype=float)
    status = np.full(size, IV_STATUS_OK, dtype=object)

    intrinsic = np.where(is_call, np.maximum(forward - strike, 0.0), np.maximum(strike - forward, 0.0))
    discount = np.exp(-rates * np.maximum(years, 0.0))
    discounted_intrinsic = discount * intrinsic
    discounted_bound = discount * np.where(is_call, forward, strike)
    finite = np.isfinite(premium) & np.isfinite(forward) & np.isfinite(strike) & np.isfinite(years) & np.isfinite(rates)
    valid = (
        finite
        & (premium > 0.0)
        & (forward > 0.0)
        & (strike > 0.0)
        & (years > 0.0)
        & (premium + 1.0e-12 < discounted_bound)
        & (premium + tick >= discounted_intrinsic)
    )
    status[~finite] = "nonpositive_inputs"
    status[finite & (premium <= 0.0)] = "nonpositive_premium"
    status[finite & (years <= 0.0)] = "expiry_day_or_shorter"
    status[finite & ((forward <= 0.0) | (strike <= 0.0))] = "nonpositive_inputs"
    status[finite & (premium + 1.0e-12 >= discounted_bound)] = "premium_exceeds_discounted_bound"
    status[finite & (premium + tick < discounted_intrinsic)] = "premium_below_discounted_intrinsic"

    if not valid.any():
        status[status == IV_STATUS_OK] = "solver_failed"
        return sigma, status

    working = valid.copy()
    guess = np.full(size, 0.20, dtype=float)
    for _ in range(40):
        if not working.any():
            break
        price, _, _, vega, _, _ = black76_discounted(
            forward[working],
            strike[working],
            years[working],
            guess[working],
            is_call[working],
            rates[working],
        )
        residual = price - premium[working]
        converged = np.abs(residual) <= PRICE_TOLERANCE
        solved_idx = np.flatnonzero(working)[converged]
        sigma[solved_idx] = guess[working][converged]
        movable = (~converged) & np.isfinite(vega) & (vega > 1.0e-12)
        updated = guess[working].copy()
        updated[movable] = np.clip(
            updated[movable] - residual[movable] / vega[movable],
            SIGMA_MIN,
            SIGMA_MAX,
        )
        guess[working] = updated
        still = np.zeros(size, dtype=bool)
        still[np.flatnonzero(working)[movable]] = True
        working = still

    remaining = valid & ~np.isfinite(sigma)
    if remaining.any():
        low = np.full(int(remaining.sum()), SIGMA_MIN, dtype=float)
        high = np.full(int(remaining.sum()), SIGMA_MAX, dtype=float)
        f_idx = np.flatnonzero(remaining)
        for _ in range(60):
            mid = 0.5 * (low + high)
            price, _, _, _, _, _ = black76_discounted(
                forward[f_idx],
                strike[f_idx],
                years[f_idx],
                mid,
                is_call[f_idx],
                rates[f_idx],
            )
            too_low = price < premium[f_idx]
            low = np.where(too_low, mid, low)
            high = np.where(too_low, high, mid)
            hit = np.abs(price - premium[f_idx]) <= PRICE_TOLERANCE
            sigma[f_idx[hit]] = mid[hit]
            keep = ~hit
            if not keep.any():
                break
            f_idx = f_idx[keep]
            low = low[keep]
            high = high[keep]
        leftover = valid & ~np.isfinite(sigma)
        if leftover.any():
            status[leftover] = "solver_failed"

    failed = valid & ~np.isfinite(sigma)
    status[failed] = "solver_failed"
    return sigma, status


def attach_risk_free_rate_asof(
    trading_days: pd.Series,
    rates: pd.DataFrame,
    *,
    series_id: str = RISK_FREE_SERIES_ID,
) -> pd.DataFrame:
    """Attach the last rate that was available before the 15:00 quote close."""

    required = {"series_id", "period", "available_at", "value", "unit"}
    missing = sorted(required.difference(rates.columns))
    if missing:
        raise ValueError(f"risk-free rate columns missing: {missing}")
    selected = rates.loc[rates["series_id"].astype(str).eq(series_id)].copy()
    selected = selected.loc[selected.get("source_quality", pd.Series("official", index=selected.index)).astype(str).eq("official")]
    selected["rate_available_at"] = pd.to_datetime(selected["available_at"], utc=True, errors="coerce")
    selected["rate_period"] = selected["period"].astype(str)
    selected["risk_free_rate"] = pd.to_numeric(selected["value"], errors="coerce")
    percent = selected["unit"].astype(str).str.lower().isin({"percent", "%", "percentage_point"})
    selected.loc[percent, "risk_free_rate"] /= 100.0
    selected = selected.dropna(subset=["rate_available_at", "risk_free_rate"]).sort_values("rate_available_at")
    quotes = pd.DataFrame({"trading_day": trading_days.astype(str)})
    quotes["quote_close"] = pd.to_datetime(quotes["trading_day"] + " 15:00:00+08:00", utc=True, errors="raise")
    quotes["_row_order"] = np.arange(len(quotes))
    merged = pd.merge_asof(
        quotes.sort_values("quote_close"),
        selected[["rate_available_at", "rate_period", "risk_free_rate"]],
        left_on="quote_close",
        right_on="rate_available_at",
        direction="backward",
        allow_exact_matches=False,
    )
    merged["rate_staleness_days"] = (merged["quote_close"] - merged["rate_available_at"]).dt.total_seconds() / 86_400.0
    stale = merged["rate_staleness_days"].gt(MAX_RATE_STALENESS_DAYS)
    merged.loc[stale, ["rate_period", "risk_free_rate"]] = [None, np.nan]
    merged["rate_status"] = np.where(merged["risk_free_rate"].notna(), "ok", "missing_or_stale_risk_free_rate")
    return merged.sort_values("_row_order").drop(columns=["_row_order", "quote_close"]).reset_index(drop=True)


def attach_risk_free_curve_asof(
    trading_days: pd.Series,
    years_to_expiry_values: pd.Series,
    rates: pd.DataFrame,
) -> pd.DataFrame:
    """Attach a PIT-visible 3M/6M/1Y curve interpolated to option tenor."""

    required = {"tenor", "period", "available_at", "value", "unit"}
    missing = sorted(required.difference(rates.columns))
    if missing:
        raise ValueError(f"discount-curve columns missing: {missing}")
    selected = rates.loc[rates["tenor"].astype(str).isin(CURVE_TENOR_YEARS)].copy()
    selected["rate_available_at"] = pd.to_datetime(selected["available_at"], utc=True, errors="coerce")
    selected["rate_period"] = selected["period"].astype(str)
    selected["rate_decimal"] = pd.to_numeric(selected["value"], errors="coerce")
    percent = selected["unit"].astype(str).str.lower().isin({"percent", "%", "percentage_point"})
    selected.loc[percent, "rate_decimal"] /= 100.0
    selected = selected.dropna(subset=["rate_available_at", "rate_decimal"])
    selected = selected.sort_values(["rate_available_at", "tenor", "rate_period"])
    selected = selected.drop_duplicates(["rate_available_at", "tenor"], keep="last")
    curve = selected.pivot(
        index=["rate_available_at", "rate_period"],
        columns="tenor",
        values="rate_decimal",
    ).reset_index()
    missing_tenors = sorted(set(CURVE_TENOR_YEARS).difference(curve.columns))
    if missing_tenors:
        raise ValueError(f"discount curve missing required tenors: {missing_tenors}")
    quotes = pd.DataFrame(
        {
            "trading_day": trading_days.astype(str),
            "years_to_expiry": pd.to_numeric(years_to_expiry_values, errors="coerce"),
        }
    )
    quotes["quote_close"] = pd.to_datetime(quotes["trading_day"] + " 15:00:00+08:00", utc=True, errors="raise")
    quotes["_row_order"] = np.arange(len(quotes))
    merged = pd.merge_asof(
        quotes.sort_values("quote_close"),
        curve.sort_values("rate_available_at"),
        left_on="quote_close",
        right_on="rate_available_at",
        direction="backward",
        allow_exact_matches=False,
    )
    tenor = merged["years_to_expiry"].to_numpy(dtype=float)
    r3 = merged["3m"].to_numpy(dtype=float)
    r6 = merged["6m"].to_numpy(dtype=float)
    r1 = merged["1y"].to_numpy(dtype=float)
    rate = np.full(len(merged), np.nan, dtype=float)
    lower = np.full(len(merged), None, dtype=object)
    upper = np.full(len(merged), None, dtype=object)
    weight = np.full(len(merged), np.nan, dtype=float)
    short = np.isfinite(tenor) & (tenor > 0.0) & (tenor <= 0.25)
    middle = np.isfinite(tenor) & (tenor > 0.25) & (tenor <= 0.50)
    long = np.isfinite(tenor) & (tenor > 0.50) & (tenor <= 1.0)
    rate[short] = r3[short]
    lower[short] = "3m"
    upper[short] = "3m"
    weight[short] = 0.0
    middle_weight = (tenor[middle] - 0.25) / 0.25
    rate[middle] = r3[middle] + middle_weight * (r6[middle] - r3[middle])
    lower[middle] = "3m"
    upper[middle] = "6m"
    weight[middle] = middle_weight
    long_weight = (tenor[long] - 0.50) / 0.50
    rate[long] = r6[long] + long_weight * (r1[long] - r6[long])
    lower[long] = "6m"
    upper[long] = "1y"
    weight[long] = long_weight
    merged["risk_free_rate"] = rate
    merged["rate_curve_lower_tenor"] = lower
    merged["rate_curve_upper_tenor"] = upper
    merged["rate_curve_interpolation_weight"] = weight
    merged["rate_staleness_days"] = (merged["quote_close"] - merged["rate_available_at"]).dt.total_seconds() / 86_400.0
    stale = merged["rate_staleness_days"].gt(MAX_RATE_STALENESS_DAYS)
    invalid_tenor = ~np.isfinite(tenor) | (tenor <= 0.0) | (tenor > 1.0)
    merged.loc[stale | invalid_tenor, "risk_free_rate"] = np.nan
    merged["rate_status"] = np.select(
        [stale, invalid_tenor, merged["risk_free_rate"].notna()],
        ["stale_risk_free_curve", "tenor_outside_3m_1y_curve", "ok_term_interpolated"],
        default="missing_risk_free_curve",
    )
    return merged.sort_values("_row_order").drop(columns=["_row_order", "quote_close", "3m", "6m", "1y"]).reset_index(drop=True)


def attach_option_iv_greeks(
    options: pd.DataFrame,
    futures: pd.DataFrame,
    *,
    trading_days: set[str] | None = None,
    contract_metadata: pd.DataFrame | None = None,
    risk_free_rates: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Attach matching-forward Black-76 IV and model Greeks onto option rows."""

    required_option = {
        "trading_day",
        "symbol",
        "product_id",
        "underlying_symbol",
        "option_type",
        "strike_price",
        "settlement",
        "close",
        "delta",
        "contract_month",
    }
    missing = sorted(required_option.difference(options.columns))
    if missing:
        raise ValueError(f"option columns missing for IV engine: {missing}")
    required_future = {"trading_day", "symbol", "settlement"}
    missing_future = sorted(required_future.difference(futures.columns))
    if missing_future:
        raise ValueError(f"future columns missing for IV engine: {missing_future}")

    result = options.copy()
    calendar_days = trading_days or set(result["trading_day"].astype(str).tolist())
    result["matching_future_symbol"] = [
        matching_future_symbol(str(product), str(underlying))
        for product, underlying in zip(result["product_id"], result["underlying_symbol"], strict=True)
    ]
    future_lookup = futures[["trading_day", "symbol", "settlement"]].copy()
    future_lookup["trading_day"] = future_lookup["trading_day"].astype(str)
    future_lookup["future_settlement"] = pd.to_numeric(future_lookup["settlement"], errors="coerce")
    future_lookup = future_lookup.drop(columns=["settlement"]).drop_duplicates(["trading_day", "symbol"], keep="last")
    result["trading_day"] = result["trading_day"].astype(str)
    result = result.merge(
        future_lookup,
        left_on=["trading_day", "matching_future_symbol"],
        right_on=["trading_day", "symbol"],
        how="left",
        suffixes=("", "_future_key"),
        validate="many_to_one",
    )
    if "symbol_future_key" in result.columns:
        result = result.drop(columns=["symbol_future_key"])

    metadata_expiry: dict[str, tuple[date, str]] = {}
    metadata_unresolved_symbols: set[str] = set()
    if contract_metadata is not None:
        required_metadata = {"contract_symbol", "expiry_date"}
        missing_metadata = sorted(required_metadata.difference(contract_metadata.columns))
        if missing_metadata:
            raise ValueError(f"contract metadata columns missing: {missing_metadata}")
        metadata_columns = ["contract_symbol", "expiry_date"]
        if "expiry_date_source" in contract_metadata.columns:
            metadata_columns.append("expiry_date_source")
        metadata = contract_metadata[metadata_columns].drop_duplicates("contract_symbol", keep="last")
        metadata_unresolved_symbols = {
            str(row.contract_symbol)
            for row in metadata.itertuples(index=False)
            if pd.isna(row.expiry_date) or not str(row.expiry_date).strip()
        }
        metadata_expiry = {
            str(row.contract_symbol): (
                date.fromisoformat(str(row.expiry_date)),
                str(getattr(row, "expiry_date_source", "factorlab_contract_identity_snapshot_expiry_date")),
            )
            for row in metadata.itertuples(index=False)
            if pd.notna(row.expiry_date) and str(row.expiry_date).strip()
        }
    last_trade_cache: dict[str, tuple[date, str]] = {}
    last_trade_dates: list[date] = []
    last_trade_rules: list[str] = []
    for symbol, month in zip(result["symbol"].astype(str), result["contract_month"].astype(str), strict=True):
        metadata_item = metadata_expiry.get(symbol)
        if metadata_item is not None:
            last_trade_dates.append(metadata_item[0])
            last_trade_rules.append(metadata_item[1])
            continue
        cached = last_trade_cache.get(month)
        if cached is None:
            year_text, month_text = month.split("-")
            cached = last_trading_day(int(year_text), int(month_text), calendar_days)
            last_trade_cache[month] = cached
        last_trade_dates.append(cached[0])
        last_trade_rules.append(cached[1])
    result["last_trading_day"] = [item.isoformat() for item in last_trade_dates]
    result["last_trading_day_rule"] = last_trade_rules
    result["years_to_expiry"] = [
        years_to_expiry(date.fromisoformat(str(day)), expiry) for day, expiry in zip(result["trading_day"], last_trade_dates, strict=True)
    ]
    if risk_free_rates is None:
        result["risk_free_rate"] = np.nan
        result["rate_period"] = None
        result["rate_available_at"] = pd.NaT
        result["rate_staleness_days"] = np.nan
        result["rate_status"] = "missing_or_stale_risk_free_rate"
    else:
        if "tenor" in risk_free_rates.columns:
            rate_attachment = attach_risk_free_curve_asof(result["trading_day"], result["years_to_expiry"], risk_free_rates)
        else:
            rate_attachment = attach_risk_free_rate_asof(result["trading_day"], risk_free_rates)
        for column in (
            "risk_free_rate",
            "rate_period",
            "rate_available_at",
            "rate_staleness_days",
            "rate_status",
        ):
            result[column] = rate_attachment[column].to_numpy()
        for column in (
            "rate_curve_lower_tenor",
            "rate_curve_upper_tenor",
            "rate_curve_interpolation_weight",
        ):
            if column in rate_attachment.columns:
                result[column] = rate_attachment[column].to_numpy()
    premium = pd.to_numeric(result["settlement"], errors="coerce")
    close = pd.to_numeric(result["close"], errors="coerce")
    result["option_premium"] = premium.where(premium.gt(0.0), close)
    result["forward"] = pd.to_numeric(result["future_settlement"], errors="coerce")
    strike = pd.to_numeric(result["strike_price"], errors="coerce")
    option_type = result["option_type"].astype(str).str.strip().str.lower()
    is_call = option_type.isin({"call", "c"}).to_numpy()
    sigma, status = invert_black76_iv(
        result["option_premium"].to_numpy(dtype=float),
        result["forward"].to_numpy(dtype=float),
        strike.to_numpy(dtype=float),
        result["years_to_expiry"].to_numpy(dtype=float),
        is_call,
        result["risk_free_rate"].to_numpy(dtype=float),
    )
    missing_forward = ~np.isfinite(result["forward"].to_numpy(dtype=float))
    missing_rate = ~np.isfinite(result["risk_free_rate"].to_numpy(dtype=float))
    expiry_rule = result["last_trading_day_rule"].astype(str)
    missing_expiry_metadata = ~(
        expiry_rule.isin(
            {
                "factorlab_contract_identity_snapshot_expiry_date",
                "cffex_contract_rule_expected_expiry",
            }
        )
        | expiry_rule.str.startswith("datahub_contract_identity:")
    ).to_numpy()
    status = np.where(missing_expiry_metadata, "missing_contract_expiry_metadata", status)
    status = np.where(missing_rate, "missing_risk_free_rate", status)
    status = np.where(missing_forward, "missing_forward", status)
    status = np.where(
        result["symbol"].astype(str).isin(metadata_unresolved_symbols).to_numpy(),
        "missing_contract_expiry_metadata",
        status,
    )
    status = np.where(
        result["years_to_expiry"].to_numpy(dtype=float) <= 0.0,
        "expiry_day_or_shorter",
        status,
    )
    expiry_day_or_shorter = result["years_to_expiry"].to_numpy(dtype=float) <= 0.0
    status = np.where(expiry_day_or_shorter, "expiry_day_or_shorter", status)
    sigma = np.where(missing_forward | missing_rate | missing_expiry_metadata, np.nan, sigma)
    result["implied_volatility"] = sigma
    result["iv_status"] = status
    price, delta, gamma, vega, theta, rho = black76_discounted(
        result["forward"].to_numpy(dtype=float),
        strike.to_numpy(dtype=float),
        result["years_to_expiry"].to_numpy(dtype=float),
        np.where(np.isfinite(sigma), sigma, 0.2),
        is_call,
        np.where(
            np.isfinite(result["risk_free_rate"].to_numpy(dtype=float)),
            result["risk_free_rate"].to_numpy(dtype=float),
            0.0,
        ),
    )
    ok = result["iv_status"].eq(IV_STATUS_OK).to_numpy()
    result["model_price"] = np.where(ok, price, np.nan)
    result["delta_model"] = np.where(ok, delta, np.nan)
    result["gamma_model"] = np.where(ok, gamma, np.nan)
    result["vega_per_vol"] = np.where(ok, vega, np.nan)
    result["vega_per_vol_point"] = np.where(ok, vega / 100.0, np.nan)
    result["theta_points_per_year"] = np.where(ok, theta, np.nan)
    result["theta_points_per_calendar_day"] = np.where(ok, theta / ACT_365_25, np.nan)
    result["rho_forward_held_constant_per_rate_unit"] = np.where(ok, rho, np.nan)
    result["rho_forward_held_constant_per_bp"] = np.where(ok, rho / 10_000.0, np.nan)
    official_delta = pd.to_numeric(result["delta"], errors="coerce").to_numpy(dtype=float)
    result["delta_official"] = official_delta
    result["delta_model_abs_error"] = np.where(ok & np.isfinite(official_delta), np.abs(delta - official_delta), np.nan)
    result["log_forward_moneyness"] = np.log(strike / result["forward"])
    result["measurement_kind"] = np.where(
        ok,
        "daily_option_surface_discounted_black76_term_curve_v1_3",
        "daily_option_surface_reference_no_iv",
    )
    return result.reset_index(drop=True)


def summarize_iv_surface(options: pd.DataFrame) -> pd.DataFrame:
    """Build daily ATM / 25-delta skew and front-second term structure."""

    ok = options.loc[options["iv_status"].eq(IV_STATUS_OK)].copy()
    if ok.empty:
        return pd.DataFrame()
    ok["abs_log_forward_moneyness"] = pd.to_numeric(ok["log_forward_moneyness"], errors="coerce").abs()
    ok["abs_delta_model"] = pd.to_numeric(ok["delta_model"], errors="coerce").abs()
    month_rows: list[dict[str, object]] = []
    for keys, group in ok.groupby(["trading_day", "product_id", "contract_month"], sort=True):
        trading_day, product_id, contract_month = keys
        atm = group.sort_values(["abs_log_forward_moneyness", "symbol"]).iloc[0]
        calls = group.loc[group["option_type"].astype(str).str.lower().isin({"call", "c"})].copy()
        puts = group.loc[group["option_type"].astype(str).str.lower().isin({"put", "p"})].copy()
        call_25_row = None
        put_25_row = None
        if not calls.empty:
            calls["_delta_gap"] = (calls["abs_delta_model"] - 0.25).abs()
            call_25_row = calls.sort_values(["_delta_gap", "symbol"]).iloc[0]
        if not puts.empty:
            puts["_delta_gap"] = (puts["abs_delta_model"] - 0.25).abs()
            put_25_row = puts.sort_values(["_delta_gap", "symbol"]).iloc[0]
        call_iv_25 = float(call_25_row["implied_volatility"]) if call_25_row is not None else math.nan
        put_iv_25 = float(put_25_row["implied_volatility"]) if put_25_row is not None else math.nan
        month_rows.append(
            {
                "trading_day": trading_day,
                "product_id": product_id,
                "contract_month": contract_month,
                "last_trading_day": atm["last_trading_day"],
                "years_to_expiry": float(atm["years_to_expiry"]),
                "forward": float(atm["forward"]),
                "atm_symbol": atm["symbol"],
                "atm_strike": float(atm["strike_price"]),
                "atm_iv": float(atm["implied_volatility"]),
                "call_iv_25d": call_iv_25,
                "put_iv_25d": put_iv_25,
                "skew_25d": put_iv_25 - call_iv_25,
                "iv_row_count": int(len(group)),
                "measurement_kind": "daily_option_iv_surface_summary_v1",
            }
        )
    monthly = pd.DataFrame(month_rows)
    term_rows: list[dict[str, object]] = []
    for (trading_day, product_id), group in monthly.groupby(["trading_day", "product_id"], sort=True):
        ordered = group.sort_values(["years_to_expiry", "contract_month"])
        front = ordered.iloc[0]
        second = ordered.iloc[1] if len(ordered) > 1 else None
        term_rows.append(
            {
                "trading_day": trading_day,
                "product_id": product_id,
                "front_contract_month": front["contract_month"],
                "front_atm_iv": front["atm_iv"],
                "front_skew_25d": front["skew_25d"],
                "second_contract_month": None if second is None else second["contract_month"],
                "second_atm_iv": math.nan if second is None else second["atm_iv"],
                "term_slope_second_minus_front": (math.nan if second is None else float(second["atm_iv"]) - float(front["atm_iv"])),
                "listed_month_count": int(len(ordered)),
                "measurement_kind": "daily_option_iv_term_structure_v1",
            }
        )
    monthly = monthly.merge(
        pd.DataFrame(term_rows),
        on=["trading_day", "product_id"],
        how="left",
        validate="many_to_one",
    )
    return monthly.reset_index(drop=True)


__all__ = [
    "ACT_365_25",
    "IV_STATUS_OK",
    "OPTION_TO_FUTURE",
    "RISK_FREE_SERIES_ID",
    "TICK_SIZE",
    "attach_option_iv_greeks",
    "attach_risk_free_curve_asof",
    "attach_risk_free_rate_asof",
    "black76_discounted",
    "black76_undiscounted",
    "invert_black76_iv",
    "last_trading_day",
    "matching_future_symbol",
    "summarize_iv_surface",
    "third_friday",
    "years_to_expiry",
]
