# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportCallIssue=false, reportIndexIssue=false, reportMissingTypeStubs=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Layer 2 daily basis, roll, and option-moneyness measurements."""

from __future__ import annotations

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError


def materialize_daily_derivative_measurements(
    contracts: pd.DataFrame,
    underlying_daily: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Measure daily derivative attributes without choosing an instrument."""

    required_underlying = {"symbol", "trading_day", "close"}
    if missing := sorted(required_underlying.difference(underlying_daily.columns)):
        raise ValidationError(f"underlying daily columns missing: {missing}")
    spot = (
        underlying_daily[["symbol", "trading_day", "close"]]
        .copy()
        .rename(columns={"symbol": "underlying_index_symbol", "close": "underlying_close"})
    )
    spot["trading_day"] = pd.to_datetime(spot["trading_day"], errors="raise").dt.date.astype(str)
    joined = contracts.merge(
        spot,
        on=["underlying_index_symbol", "trading_day"],
        how="left",
        validate="many_to_one",
    )
    joined["close"] = pd.to_numeric(joined["close"], errors="coerce")
    joined["underlying_close"] = pd.to_numeric(joined["underlying_close"], errors="coerce")
    futures = joined.loc[joined["instrument_type"].eq("financial_future")].copy()
    futures["basis_points"] = futures["close"] - futures["underlying_close"]
    futures["basis_rate"] = futures["basis_points"] / futures["underlying_close"]
    futures["measurement_kind"] = "daily_futures_basis"

    roll_rows: list[dict[str, object]] = []
    for (trading_day, product_id), group in futures.groupby(["trading_day", "product_id"], sort=True):
        ordered = group.sort_values(["contract_month", "symbol"])
        if ordered.empty:
            continue
        front = ordered.iloc[0]
        second = ordered.iloc[1] if len(ordered) > 1 else None
        dominant = group.sort_values(
            ["open_interest", "volume", "symbol"], ascending=[False, False, True]
        ).iloc[0]
        roll_rows.append(
            {
                "trading_day": trading_day,
                "product_id": product_id,
                "underlying_index_symbol": front["underlying_index_symbol"],
                "underlying_close": front["underlying_close"],
                "front_symbol": front["symbol"],
                "front_contract_month": front["contract_month"],
                "front_close": front["close"],
                "front_basis_rate": front["basis_rate"],
                "front_open_interest": front["open_interest"],
                "second_symbol": second["symbol"] if second is not None else None,
                "second_contract_month": second["contract_month"] if second is not None else None,
                "second_close": second["close"] if second is not None else np.nan,
                "second_basis_rate": second["basis_rate"] if second is not None else np.nan,
                "front_second_price_spread": second["close"] - front["close"] if second is not None else np.nan,
                "front_second_basis_spread": second["basis_rate"] - front["basis_rate"] if second is not None else np.nan,
                "dominant_symbol_by_open_interest": dominant["symbol"],
                "dominant_open_interest": dominant["open_interest"],
                "dominant_volume": dominant["volume"],
                "measurement_kind": "daily_futures_roll_state",
            }
        )
    roll = pd.DataFrame(roll_rows)

    options = joined.loc[joined["instrument_type"].eq("financial_option")].copy()
    options["strike_price"] = pd.to_numeric(options["strike_price"], errors="coerce")
    options["strike_to_spot_ratio"] = options["strike_price"] / options["underlying_close"]
    options["log_moneyness"] = np.log(options["strike_to_spot_ratio"])
    options["measurement_kind"] = "daily_option_surface_reference_no_iv"
    return futures.reset_index(drop=True), roll.reset_index(drop=True), options.reset_index(drop=True)


# Historical compatibility name used by the former Layer 4 execution pool.
materialize_daily_execution_tables = materialize_daily_derivative_measurements


__all__ = ["materialize_daily_derivative_measurements", "materialize_daily_execution_tables"]
