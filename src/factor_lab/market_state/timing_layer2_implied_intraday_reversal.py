# pyright: reportAny=false, reportArgumentType=false, reportIndexIssue=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
"""Layer 2 implied intraday-reversal K-line attribute.

V1 reports causal historical averages of Layer 1 session pieces.
V1.1 cuts extreme signed daytime returns with a MAD band.
V1.2 freezes the ordinary-day main bucket as |close-to-close| <= 1% and
amplitude <= 2%, then splits that main bucket by weekly up / ordinary /
down context. It does not emit a direction, gate, or production signal.
"""

from __future__ import annotations

from collections.abc import Mapping
from math import erf, sqrt
from typing import Final, Literal

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.session_clock_reference import AUTHORITY as LAYER1_CLOCK_AUTHORITY
from factor_lab.market_state.session_clock_reference import (
    CARRIER_INDEX,
    INDEX_WINDOW,
    MINIMUM_WINDOW,
)
from factor_lab.market_state.timing_layer2_measurement_plane import validate_measurement_output_columns

SCHEMA_ID: Final[str] = "timing_layer2_implied_intraday_reversal@1.2"
SCHEMA_ID_V1: Final[str] = "timing_layer2_implied_intraday_reversal@1.0"
SCHEMA_ID_V1_1: Final[str] = "timing_layer2_implied_intraday_reversal@1.1"
PROVIDER_ID: Final[str] = SCHEMA_ID
FAMILY: Final[str] = "implied_intraday_reversal"
LAYER1_CLOCK_ID: Final[str] = "factorlab.market_state_session_clock_reference@1.0"
PRIMARY_CARRIER: Final[str] = CARRIER_INDEX
TWIN_CARRIER: Final[str] = "000300.SH"
UNREAD_START: Final[str] = str(INDEX_WINDOW["end_exclusive"])
ROLLING_WINDOW: Final[int] = 63
MIN_SIGN_N: Final[int] = 40
MIN_TRIM_N: Final[int] = 60
BODY_Z: Final[float] = 2.0
MAD_TO_SIGMA: Final[float] = 1.4826
VIEW_ID: Final[str] = "session_piece_previous_close"
SHANGHAI_TZ: Final[str] = "Asia/Shanghai"
PRIMARY_BUCKET_GRAIN: Final[str] = "60m"
FILTER_VARIABLE: Final[str] = "daytime_body"
DAILY_RETURN_LIMIT: Final[float] = 0.01
DAILY_AMPLITUDE_LIMIT: Final[float] = 0.02
WEEKLY_RETURN_LIMIT: Final[float] = 0.025
WEEKLY_AMPLITUDE_LIMIT: Final[float] = 0.05
WEEK_PERIOD: Final[str] = "W-FRI"
PASSTHROUGH_COLUMNS: Final[tuple[str, ...]] = (
    "close_to_close",
    "day_high",
    "day_low",
    "prev_close",
    "open_0931",
    "close_1500",
    "close_from_open",
)

PieceName = Literal[
    "overnight",
    "first30",
    "morning",
    "early_afternoon",
    "late_afternoon",
    "afternoon",
]

CANONICAL_PIECES: Final[tuple[PieceName, ...]] = (
    "overnight",
    "first30",
    "morning",
    "early_afternoon",
    "late_afternoon",
    "afternoon",
)
V1_INDEX_PANEL_PIECES: Final[tuple[PieceName, ...]] = (
    "overnight",
    "first30",
    "morning",
    "afternoon",
)
PANEL_COLUMN_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "overnight": ("overnight", "overnight_gap"),
    "first30": ("first30", "open_to_first30"),
    "morning": ("morning", "morning_body"),
    "early_afternoon": ("early_afternoon", "early_afternoon_body", "h1301_1400"),
    "late_afternoon": ("late_afternoon", "late_afternoon_body", "h1401_1500"),
    "afternoon": ("afternoon", "afternoon_body"),
    "daytime_body": ("daytime_body", "close_from_open", "daytime"),
    "open_hour": ("open_hour", "h0931_1030"),
    "late_morning": ("late_morning", "h1031_1130"),
}
STAT_FIELDS: Final[tuple[str, ...]] = ("mean", "se", "n", "t", "p_pos", "std", "var", "usable")
LOOKBACKS: Final[tuple[str, ...]] = ("expanding", "roll63")
BUCKETS_60M: Final[tuple[tuple[str, str, str], ...]] = (
    ("open_hour", "09:31", "10:30"),
    ("late_morning", "10:30", "11:30"),
    ("early_afternoon", "13:01", "14:00"),
    ("late_afternoon", "14:00", "15:00"),
)
BUCKETS_30M: Final[tuple[tuple[str, str, str], ...]] = (
    ("m0931_1000", "09:31", "10:00"),
    ("m1001_1030", "10:00", "10:30"),
    ("m1031_1100", "10:30", "11:00"),
    ("m1101_1130", "11:00", "11:30"),
    ("m1301_1330", "13:01", "13:30"),
    ("m1331_1400", "13:30", "14:00"),
    ("m1401_1430", "14:00", "14:30"),
    ("m1431_1500", "14:30", "15:00"),
)
KEY_CLOCKS: Final[tuple[str, ...]] = (
    "09:31",
    "10:00",
    "10:30",
    "11:00",
    "11:30",
    "13:01",
    "13:30",
    "14:00",
    "14:30",
    "15:00",
)

AUTHORITY: Final[dict[str, bool]] = {
    "measurement": True,
    "strategy_selection": False,
    "parameter_selection": False,
    "routing": False,
    "production": False,
    "standalone_session_strategy": False,
    "direction_forecast": False,
    "current_pointer_change": False,
}


def _shanghai_close(day: pd.Timestamp) -> pd.Timestamp:
    stamp = pd.Timestamp(day)
    if stamp.tzinfo is not None:
        stamp = stamp.tz_convert(SHANGHAI_TZ).tz_localize(None)
    return stamp.normalize() + pd.Timedelta(hours=15)


def _as_trading_day(values: pd.Series) -> pd.Series:
    days = pd.to_datetime(values, errors="raise")
    if getattr(days.dt, "tz", None) is not None:
        days = days.dt.tz_convert(SHANGHAI_TZ).dt.tz_localize(None)
    return days.dt.normalize().dt.strftime("%Y-%m-%d")


def _normal_tail_prob(z: float) -> float:
    return 2.0 * (1.0 - 0.5 * (1.0 + erf(z / sqrt(2.0))))


def resolve_piece_columns(columns: pd.Index, *, required: tuple[str, ...] = ("overnight", "morning", "afternoon")) -> dict[str, str]:
    present = set(columns)
    resolved: dict[str, str] = {}
    for piece, aliases in PANEL_COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in present:
                resolved[piece] = alias
                break
    missing = [name for name in required if name not in resolved]
    if missing:
        raise ValidationError(f"implied-reversal panel missing required pieces: {missing}")
    return resolved


def describe_return_distribution(values: pd.Series) -> dict[str, object]:
    series = pd.to_numeric(values, errors="coerce").dropna()
    n = int(series.shape[0])
    if n < 8:
        raise ValidationError("return distribution needs at least 8 observations")
    mean = float(series.mean())
    median = float(series.median())
    std = float(series.std(ddof=1))
    centered = series - mean
    m2 = float((centered**2).mean())
    m3 = float((centered**3).mean())
    m4 = float((centered**4).mean())
    skew = m3 / (m2**1.5) if m2 > 0 else float("nan")
    kurtosis = m4 / (m2**2) if m2 > 0 else float("nan")
    excess = kurtosis - 3.0
    z = (series - mean) / std if std > 0 else series * 0.0
    tails: dict[str, object] = {}
    for level in (1.0, 1.5, 2.0, 2.5, 3.0):
        empirical = float(z.abs().gt(level).mean())
        theoretical = _normal_tail_prob(level)
        tails[str(level)] = {
            "empirical": empirical,
            "normal": theoretical,
            "ratio": empirical / theoretical if theoretical > 0 else float("nan"),
        }
    center_mass = float(z.abs().le(1.0).mean())
    return {
        "n": n,
        "mean": mean,
        "median": median,
        "std": std,
        "mean_bp": mean * 10000.0,
        "median_bp": median * 10000.0,
        "std_bp": std * 10000.0,
        "skew": skew,
        "kurtosis": kurtosis,
        "excess_kurtosis": excess,
        "center_mass_abs_z_le_1": center_mass,
        "normal_center_mass_abs_z_le_1": 0.682689492137,
        "tail_shape": (
            "leptokurtic_peaked_center_fat_tails"
            if excess > 0.5
            else ("platykurtic_thin_tails" if excess < -0.5 else "near_mesokurtic")
        ),
        "tails_vs_normal": tails,
        "not_a_runtime_rule": True,
    }


def expanding_median_mad(values: pd.Series, *, min_periods: int = MIN_TRIM_N) -> pd.DataFrame:
    numeric = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    loc = np.full(numeric.shape[0], np.nan)
    scale = np.full(numeric.shape[0], np.nan)
    for index in range(numeric.shape[0]):
        hist = numeric[:index]
        hist = hist[np.isfinite(hist)]
        if hist.size < min_periods:
            continue
        median = float(np.median(hist))
        loc[index] = median
        mad = float(np.median(np.abs(hist - median)))
        scale[index] = MAD_TO_SIGMA * mad
    return pd.DataFrame({"location": loc, "scale": scale}, index=values.index)


def causal_body_mask(daytime_body: pd.Series, *, z: float = BODY_Z, min_periods: int = MIN_TRIM_N) -> pd.Series:
    if z <= 0:
        raise ValidationError("body z threshold must be positive")
    numeric = pd.to_numeric(daytime_body, errors="coerce")
    stats = expanding_median_mad(numeric, min_periods=min_periods)
    deviation = (numeric - stats["location"]).abs()
    mask = deviation <= (z * stats["scale"])
    return mask.where(stats["scale"].gt(0) & numeric.notna())


def _lookback_stats(values: pd.Series, *, window: int | None) -> pd.DataFrame:
    lagged = pd.to_numeric(values, errors="coerce").shift(1)
    if window is None:
        n = lagged.expanding(min_periods=1).count()
        mean = lagged.expanding(min_periods=1).mean()
        std = lagged.expanding(min_periods=2).std(ddof=1)
        positive = lagged.gt(0.0).where(lagged.notna())
        p_pos = positive.astype(float).expanding(min_periods=1).mean()
    else:
        if window < MIN_SIGN_N:
            raise ValidationError("rolling lookback cannot be shorter than the sign-support minimum")
        n = lagged.rolling(window, min_periods=1).count()
        mean = lagged.rolling(window, min_periods=1).mean()
        std = lagged.rolling(window, min_periods=2).std(ddof=1)
        positive = lagged.gt(0.0).where(lagged.notna())
        p_pos = positive.astype(float).rolling(window, min_periods=1).mean()
    se = std / np.sqrt(n)
    tstat = mean / se
    usable = (n >= MIN_SIGN_N) & np.isfinite(se) & (mean.abs() >= se)
    variance = std**2
    return pd.DataFrame(
        {
            "mean": mean.astype(float),
            "se": se.astype(float),
            "n": n.astype(float),
            "t": tstat.astype(float),
            "p_pos": p_pos.astype(float),
            "std": std.astype(float),
            "var": variance.astype(float),
            "usable": usable.astype(float),
        },
        index=values.index,
    )


def _clock_label(timestamps: pd.Series) -> pd.Series:
    return timestamps.astype(str).str.slice(11, 16)


def _value_at(day: pd.DataFrame, clock: str, column: str) -> float:
    hit = day.loc[day["clock"] == clock, column]
    if hit.empty:
        return float("nan")
    return float(pd.to_numeric(hit.iloc[0], errors="coerce"))


def build_session_piece_panel_from_minutes(minutes: pd.DataFrame, *, symbol_column: str = "symbol") -> pd.DataFrame:
    """Build Layer 1 session-piece and 60-minute bucket simple returns from 1-minute bars."""

    required = {"timestamp", "trading_day", "open", "close"}
    missing = sorted(required.difference(minutes.columns))
    if missing:
        raise ValidationError(f"session-piece minutes missing columns: {missing}")
    frame = minutes.copy()
    if symbol_column not in frame.columns:
        frame[symbol_column] = PRIMARY_CARRIER
    frame["trading_day"] = _as_trading_day(frame["trading_day"])
    if (frame["trading_day"] >= UNREAD_START).any():
        raise ValidationError("session-piece minutes leaked unread rows")
    frame["clock"] = _clock_label(frame["timestamp"])
    for column in ("open", "close"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.sort_values([symbol_column, "trading_day", "clock"], kind="mergesort")
    rows: list[dict[str, object]] = []
    for (symbol, trading_day), day in frame.groupby([symbol_column, "trading_day"], sort=True):
        day = day.sort_values("clock", kind="mergesort")
        open_0931 = _value_at(day, "09:31", "open")
        close_1000 = _value_at(day, "10:00", "close")
        close_1030 = _value_at(day, "10:30", "close")
        close_1100 = _value_at(day, "11:00", "close")
        close_1130 = _value_at(day, "11:30", "close")
        open_1301 = _value_at(day, "13:01", "open")
        close_1330 = _value_at(day, "13:30", "close")
        close_1400 = _value_at(day, "14:00", "close")
        close_1430 = _value_at(day, "14:30", "close")
        close_1500 = _value_at(day, "15:00", "close")
        rec: dict[str, object] = {
            "symbol": str(symbol),
            "trading_day": str(trading_day),
            "open_0931": open_0931,
            "close_1000": close_1000,
            "close_1030": close_1030,
            "close_1130": close_1130,
            "open_1301": open_1301,
            "close_1400": close_1400,
            "close_1500": close_1500,
            "first30": close_1000 / open_0931 - 1.0 if open_0931 > 0 else float("nan"),
            "open_hour": close_1030 / open_0931 - 1.0 if open_0931 > 0 else float("nan"),
            "late_morning": close_1130 / close_1030 - 1.0 if close_1030 > 0 else float("nan"),
            "morning": close_1130 / open_0931 - 1.0 if open_0931 > 0 else float("nan"),
            "early_afternoon": close_1400 / open_1301 - 1.0 if open_1301 > 0 else float("nan"),
            "late_afternoon": close_1500 / close_1400 - 1.0 if close_1400 > 0 else float("nan"),
            "afternoon": close_1500 / open_1301 - 1.0 if open_1301 > 0 else float("nan"),
            "daytime_body": close_1500 / open_0931 - 1.0 if open_0931 > 0 else float("nan"),
            "m0931_1000": close_1000 / open_0931 - 1.0 if open_0931 > 0 else float("nan"),
            "m1001_1030": close_1030 / close_1000 - 1.0 if close_1000 > 0 else float("nan"),
            "m1031_1100": close_1100 / close_1030 - 1.0 if close_1030 > 0 else float("nan"),
            "m1101_1130": close_1130 / close_1100 - 1.0 if close_1100 > 0 else float("nan"),
            "m1301_1330": close_1330 / open_1301 - 1.0 if open_1301 > 0 else float("nan"),
            "m1331_1400": close_1400 / close_1330 - 1.0 if close_1330 > 0 else float("nan"),
            "m1401_1430": close_1430 / close_1400 - 1.0 if close_1400 > 0 else float("nan"),
            "m1431_1500": close_1500 / close_1430 - 1.0 if close_1430 > 0 else float("nan"),
        }
        rows.append(rec)
    panel = pd.DataFrame(rows)
    if panel.empty:
        raise ValidationError("session-piece minutes produced no daily rows")
    pieces: list[pd.DataFrame] = []
    for _, block in panel.groupby("symbol", sort=True):
        block = block.sort_values("trading_day", kind="mergesort").copy()
        block["overnight"] = block["open_0931"] / block["close_1500"].shift(1) - 1.0
        pieces.append(block)
    out = pd.concat(pieces, ignore_index=True)
    if (out["trading_day"] >= UNREAD_START).any():
        raise ValidationError("session-piece panel leaked unread rows")
    return out


def coerce_session_piece_panel(
    frame: pd.DataFrame,
    *,
    symbol: str | None = None,
    required: tuple[str, ...] = ("overnight", "morning", "afternoon"),
) -> pd.DataFrame:
    if "trading_day" not in frame.columns:
        raise ValidationError("session-piece panel requires trading_day")
    panel = frame.copy()
    if "symbol" not in panel.columns:
        panel["symbol"] = symbol or PRIMARY_CARRIER
    if symbol is not None:
        panel = panel.loc[panel["symbol"].astype(str) == symbol].copy()
        if panel.empty:
            raise ValidationError(f"session-piece panel has no rows for {symbol}")
    panel["trading_day"] = _as_trading_day(panel["trading_day"])
    if (panel["trading_day"] >= UNREAD_START).any():
        raise ValidationError("session-piece panel leaked unread rows")
    resolved = resolve_piece_columns(panel.columns, required=required)
    renamed = {column: piece for piece, column in resolved.items() if column != piece}
    if renamed:
        panel = panel.rename(columns=renamed)
    extra = [name for name in PASSTHROUGH_COLUMNS if name in panel.columns and name not in resolved]
    keep = ["symbol", "trading_day", *resolved.keys(), *extra]
    panel = panel.loc[:, keep].sort_values(["symbol", "trading_day"], kind="mergesort").reset_index(drop=True)
    if panel.duplicated(["symbol", "trading_day"]).any():
        raise ValidationError("session-piece panel has duplicate symbol/trading_day rows")
    return panel


def _lookback_columns(series: pd.Series, prefix: str) -> dict[str, object]:
    expanding = _lookback_stats(series, window=None)
    rolling = _lookback_stats(series, window=ROLLING_WINDOW)
    columns: dict[str, object] = {}
    for field in STAT_FIELDS:
        columns[f"{prefix}_expanding_{field}"] = expanding[field].to_numpy()
        columns[f"{prefix}_roll63_{field}"] = rolling[field].to_numpy()
    return columns


def build_implied_intraday_reversal_card(
    panel: pd.DataFrame,
    *,
    carrier_id: str = PRIMARY_CARRIER,
    view_id: str = VIEW_ID,
) -> pd.DataFrame:
    """Causal expanding/63-day means, plus the V1.1 middle-body de-drifted view."""

    if LAYER1_CLOCK_AUTHORITY["production"] or LAYER1_CLOCK_AUTHORITY["standalone_session_strategy"]:
        raise ValidationError("Layer 1 session clock cannot grant production authority")
    required = ("overnight", "morning", "afternoon")
    pieces_panel = coerce_session_piece_panel(panel, symbol=carrier_id, required=required)
    extra = ("open_hour", "late_morning", *[name for name, _start, _end in BUCKETS_30M])
    piece_names = tuple(name for name in (*CANONICAL_PIECES, *extra) if name in pieces_panel.columns)
    blocks: list[pd.DataFrame] = []
    for _, block in pieces_panel.groupby("symbol", sort=True):
        block = block.sort_values("trading_day", kind="mergesort").reset_index(drop=True)
        asof = pd.to_datetime(block["trading_day"])
        prev_day = asof.shift(1)
        available = [pd.NaT if pd.isna(day) else _shanghai_close(pd.Timestamp(day)) for day in prev_day]
        columns: dict[str, object] = {
            "carrier_id": carrier_id,
            "view_id": view_id,
            "symbol": block["symbol"].astype(str).to_numpy(),
            "trading_day": block["trading_day"].astype(str).to_numpy(),
            "observation_time": pd.DatetimeIndex(available).tz_localize(SHANGHAI_TZ),
            "available_at": pd.DatetimeIndex(available).tz_localize(SHANGHAI_TZ),
            "provider_id": PROVIDER_ID,
            "layer1_clock_id": LAYER1_CLOCK_ID,
        }
        body = None
        daily_main = None
        if "daytime_body" in block.columns:
            daytime = pd.to_numeric(block["daytime_body"], errors="coerce")
            body = causal_body_mask(daytime)
            columns["daytime_body"] = daytime.to_numpy()
            columns["body_member"] = body.eq(True).astype(float).to_numpy()
        if {"close_to_close", "day_high", "day_low", "prev_close"}.issubset(block.columns):
            amp = daily_amplitude(block["day_high"], block["day_low"], block["prev_close"])
            daily_main = daily_main_mask(block["close_to_close"], amp)
            columns["close_to_close"] = pd.to_numeric(block["close_to_close"], errors="coerce").to_numpy()
            columns["amplitude"] = amp.to_numpy()
            columns["daily_main_member"] = daily_main.astype(float).to_numpy()
        for piece in piece_names:
            series = pd.to_numeric(block[piece], errors="coerce")
            columns.update(_lookback_columns(series, piece))
            columns[piece] = series.to_numpy()
            if body is not None:
                columns.update(_lookback_columns(series.where(body), f"{piece}_body"))
            if daily_main is not None:
                columns.update(_lookback_columns(series.where(daily_main), f"{piece}_main"))
        if "morning" in piece_names and "afternoon" in piece_names:
            columns["intraday_reversal_expanding_mean"] = (
                columns["morning_expanding_mean"] - columns["afternoon_expanding_mean"]
            )
            columns["intraday_reversal_roll63_mean"] = (
                columns["morning_roll63_mean"] - columns["afternoon_roll63_mean"]
            )
            if body is not None:
                columns["intraday_reversal_body_expanding_mean"] = (
                    columns["morning_body_expanding_mean"] - columns["afternoon_body_expanding_mean"]
                )
        blocks.append(pd.DataFrame(columns))
    card = pd.concat(blocks, ignore_index=True)
    validate_measurement_output_columns(card.columns)
    card.attrs["timing_layer_contract"] = {
        "schema_id": SCHEMA_ID,
        "parent_schema_id": SCHEMA_ID_V1_1,
        "family": FAMILY,
        "layer1_clock_id": LAYER1_CLOCK_ID,
        "pieces": list(piece_names),
        "lookbacks": list(LOOKBACKS),
        "rolling_window": ROLLING_WINDOW,
        "min_sign_n": MIN_SIGN_N,
        "filter_variable": FILTER_VARIABLE,
        "body_z": BODY_Z,
        "primary_bucket_grain": PRIMARY_BUCKET_GRAIN,
        "blend_forbidden": True,
        "amplitude_is_not_a_veto": False,
        "daily_return_limit": DAILY_RETURN_LIMIT,
        "daily_amplitude_limit": DAILY_AMPLITUDE_LIMIT,
        "weekly_return_limit": WEEKLY_RETURN_LIMIT,
        "weekly_amplitude_limit": WEEKLY_AMPLITUDE_LIMIT,
        "context_conditioning": True,
        "runtime_feature_future_reads": 0,
        "direction_forecast": False,
        "read_only": True,
        "strategy_mutation": False,
        "current_pointer_change": False,
        "authority": dict(AUTHORITY),
        "minimum_window": dict(MINIMUM_WINDOW),
    }
    closed_keys = ("strategy_selection", "routing", "production", "standalone_session_strategy", "direction_forecast")
    if any(bool(AUTHORITY[key]) for key in closed_keys):
        raise ValidationError("implied-reversal cards cannot grant strategy authority")
    return card


def _piece_summary(values: pd.Series) -> dict[str, object]:
    series = pd.to_numeric(values, errors="coerce").dropna()
    n = int(series.shape[0])
    if n == 0:
        return {"n": 0}
    mean = float(series.mean())
    std = float(series.std(ddof=1)) if n > 1 else float("nan")
    se = std / np.sqrt(n) if n > 1 else float("nan")
    payload: dict[str, object] = {
        "n": n,
        "mean": mean,
        "mean_bp": mean * 10000.0,
        "se": se,
        "se_bp": se * 10000.0 if np.isfinite(se) else float("nan"),
        "std": std,
        "std_bp": std * 10000.0 if np.isfinite(std) else float("nan"),
        "var": std**2 if np.isfinite(std) else float("nan"),
        "p_pos": float((series > 0.0).mean()),
        "usable": bool(n >= MIN_SIGN_N and np.isfinite(se) and abs(mean) >= se),
    }
    if n >= 8:
        dist = describe_return_distribution(series)
        payload["skew"] = dist["skew"]
        payload["excess_kurtosis"] = dist["excess_kurtosis"]
    return payload


def summarize_unconditional_means(panel: pd.DataFrame, *, carrier_id: str = PRIMARY_CARRIER) -> dict[str, object]:
    """In-sample prototype. Not a causal card and not a runtime rule."""

    pieces_panel = coerce_session_piece_panel(panel, symbol=carrier_id, required=("overnight", "morning", "afternoon"))
    payload: dict[str, object] = {
        "carrier_id": carrier_id,
        "identity": "unconditional_and_middle_body_historical_average",
        "not_a_runtime_rule": True,
        "filter_variable": FILTER_VARIABLE,
        "body_z": BODY_Z,
        "pieces_all": {},
        "pieces_body": {},
    }
    names = [name for name in (*CANONICAL_PIECES, "open_hour", "late_morning", "daytime_body") if name in pieces_panel.columns]
    all_payload = {piece: _piece_summary(pieces_panel[piece]) for piece in names}
    payload["pieces_all"] = all_payload
    if "daytime_body" in pieces_panel.columns:
        daytime = pd.to_numeric(pieces_panel["daytime_body"], errors="coerce")
        payload["daytime_distribution_all"] = describe_return_distribution(daytime)
        loc = float(daytime.median())
        scale = MAD_TO_SIGMA * float((daytime - loc).abs().median())
        in_sample_body = (daytime - loc).abs() <= BODY_Z * scale
        payload["in_sample_body_share"] = float(in_sample_body.mean())
        payload["in_sample_body_n"] = int(in_sample_body.sum())
        payload["pieces_body"] = {piece: _piece_summary(pieces_panel.loc[in_sample_body, piece]) for piece in names}
        payload["daytime_distribution_body"] = describe_return_distribution(daytime[in_sample_body])
        payload["in_sample_trim"] = {
            "location_bp": loc * 10000.0,
            "robust_sigma_bp": scale * 10000.0,
            "z": BODY_Z,
            "amplitude_is_not_a_veto": True,
        }
    return payload


def yearly_unconditional_table(panel: pd.DataFrame, *, carrier_id: str = PRIMARY_CARRIER, body: bool = False) -> pd.DataFrame:
    pieces_panel = coerce_session_piece_panel(panel, symbol=carrier_id, required=("overnight", "morning", "afternoon"))
    if body:
        if "daytime_body" not in pieces_panel.columns:
            raise ValidationError("body yearly table requires daytime_body")
        daytime = pd.to_numeric(pieces_panel["daytime_body"], errors="coerce")
        loc = float(daytime.median())
        scale = MAD_TO_SIGMA * float((daytime - loc).abs().median())
        pieces_panel = pieces_panel.loc[(daytime - loc).abs() <= BODY_Z * scale].copy()
    pieces_panel["year"] = pieces_panel["trading_day"].str.slice(0, 4)
    rows: list[dict[str, object]] = []
    piece_names = [name for name in (*CANONICAL_PIECES, "open_hour", "late_morning") if name in pieces_panel.columns]
    for year, part in pieces_panel.groupby("year", sort=True):
        rec: dict[str, object] = {"year": str(year), "n": int(len(part))}
        for piece in piece_names:
            values = pd.to_numeric(part[piece], errors="coerce").dropna()
            rec[f"{piece}_n"] = int(values.shape[0])
            rec[f"{piece}_mean_bp"] = float(values.mean() * 10000.0) if not values.empty else float("nan")
            rec[f"{piece}_std_bp"] = float(values.std(ddof=1) * 10000.0) if len(values) > 1 else float("nan")
        rows.append(rec)
    return pd.DataFrame(rows)



def daily_amplitude(high: pd.Series, low: pd.Series, prev_close: pd.Series) -> pd.Series:
    """High-low range over previous close. Overnight gaps sit inside this amplitude."""

    span = pd.to_numeric(high, errors="coerce") - pd.to_numeric(low, errors="coerce")
    base = pd.to_numeric(prev_close, errors="coerce")
    amp = span / base
    return amp.where(base > 0)


def daily_main_mask(close_to_close: pd.Series, amplitude: pd.Series) -> pd.Series:
    """Ordinary-day main bucket: |net return| <= 1% and amplitude <= 2%."""

    ret = pd.to_numeric(close_to_close, errors="coerce")
    amp = pd.to_numeric(amplitude, errors="coerce")
    return ret.abs().le(DAILY_RETURN_LIMIT) & amp.le(DAILY_AMPLITUDE_LIMIT) & ret.notna() & amp.notna()


def build_weekly_context(panel: pd.DataFrame) -> pd.DataFrame:
    """Week-ending-Friday bars. Labels are materials, not calendar runtime rules."""

    required = {"trading_day", "close_1500", "day_high", "day_low", "prev_close"}
    missing = sorted(required.difference(panel.columns))
    if missing:
        raise ValidationError(f"weekly context missing columns: {missing}")
    frame = panel.copy()
    frame["trading_day"] = _as_trading_day(frame["trading_day"])
    if (frame["trading_day"] >= UNREAD_START).any():
        raise ValidationError("weekly context leaked unread rows")
    frame["td"] = pd.to_datetime(frame["trading_day"])
    frame["week"] = frame["td"].dt.to_period(WEEK_PERIOD)
    rows: list[dict[str, object]] = []
    for week, part in frame.groupby("week", sort=True):
        part = part.sort_values("td")
        if len(part) < 3:
            continue
        first = part.iloc[0]
        last = part.iloc[-1]
        prev = float(pd.to_numeric(first["prev_close"], errors="coerce"))
        if not np.isfinite(prev) or prev <= 0:
            continue
        ret = float(pd.to_numeric(last["close_1500"], errors="coerce")) / prev - 1.0
        week_high = float(pd.to_numeric(part["day_high"], errors="coerce").max())
        week_low = float(pd.to_numeric(part["day_low"], errors="coerce").min())
        amp = (week_high - week_low) / prev
        if abs(ret) > WEEKLY_RETURN_LIMIT:
            label = "up" if ret > 0 else "down"
        elif amp <= WEEKLY_AMPLITUDE_LIMIT:
            label = "ordinary"
        else:
            label = "wide"
        rows.append(
            {
                "week": str(week),
                "weekly_return": ret,
                "weekly_amplitude": amp,
                "weekly_label": label,
                "week_start": str(first["trading_day"]),
                "week_end": str(last["trading_day"]),
                "week_n": int(len(part)),
            }
        )
    if not rows:
        raise ValidationError("weekly context produced no weeks")
    return pd.DataFrame(rows)


def attach_weekly_labels(panel: pd.DataFrame, weekly: pd.DataFrame) -> pd.DataFrame:
    frame = panel.copy()
    frame["trading_day"] = _as_trading_day(frame["trading_day"])
    frame["week"] = pd.to_datetime(frame["trading_day"]).dt.to_period(WEEK_PERIOD).astype(str)
    return frame.merge(weekly, on="week", how="left")


def four_bucket_masks(panel: pd.DataFrame) -> dict[str, pd.Series]:
    """Main daily bucket plus weekly-up/ordinary/down splits of that main bucket."""

    if "close_to_close" not in panel.columns or "day_high" not in panel.columns:
        raise ValidationError("four-bucket masks require close_to_close and daily high/low")
    amp = daily_amplitude(panel["day_high"], panel["day_low"], panel["prev_close"])
    main = daily_main_mask(panel["close_to_close"], amp)
    labeled = attach_weekly_labels(panel, build_weekly_context(panel))
    weekly_label = labeled["weekly_label"]
    weekly_label.index = panel.index
    return {
        "daily_main": main,
        "main_weekly_up": main & weekly_label.eq("up"),
        "main_weekly_ordinary": main & weekly_label.eq("ordinary"),
        "main_weekly_down": main & weekly_label.eq("down"),
        "main_weekly_wide_remainder": main & weekly_label.eq("wide"),
    }


def summarize_four_buckets(panel: pd.DataFrame, *, carrier_id: str = PRIMARY_CARRIER) -> dict[str, object]:
    pieces_panel = coerce_session_piece_panel(panel, symbol=carrier_id, required=("overnight", "morning", "afternoon"))
    masks = four_bucket_masks(pieces_panel)
    names = [name for name in (*CANONICAL_PIECES, "open_hour", "late_morning", "daytime_body") if name in pieces_panel.columns]
    buckets: dict[str, object] = {}
    official = ("daily_main", "main_weekly_up", "main_weekly_ordinary", "main_weekly_down")
    for bucket_id in official + ("main_weekly_wide_remainder",):
        mask = masks[bucket_id]
        buckets[bucket_id] = {
            "n": int(mask.sum()),
            "share": float(mask.mean()) if len(mask) else 0.0,
            "official": bucket_id in official,
            "pieces": {piece: _piece_summary(pieces_panel.loc[mask, piece]) for piece in names},
        }
    return {
        "carrier_id": carrier_id,
        "identity": "daily_main_and_weekly_context_four_buckets",
        "not_a_runtime_rule": True,
        "daily_return_limit": DAILY_RETURN_LIMIT,
        "daily_amplitude_limit": DAILY_AMPLITUDE_LIMIT,
        "weekly_return_limit": WEEKLY_RETURN_LIMIT,
        "weekly_amplitude_limit": WEEKLY_AMPLITUDE_LIMIT,
        "amplitude_is_twice_return": True,
        "buckets": buckets,
    }

def card_contract_payload(card: pd.DataFrame) -> Mapping[str, object]:
    contract = card.attrs.get("timing_layer_contract")
    if not isinstance(contract, dict):
        raise ValidationError("implied-reversal card lost its layer contract")
    return contract


__all__ = [
    "AUTHORITY",
    "BODY_Z",
    "BUCKETS_30M",
    "BUCKETS_60M",
    "CANONICAL_PIECES",
    "FAMILY",
    "FILTER_VARIABLE",
    "KEY_CLOCKS",
    "LAYER1_CLOCK_ID",
    "PRIMARY_BUCKET_GRAIN",
    "PRIMARY_CARRIER",
    "PROVIDER_ID",
    "ROLLING_WINDOW",
    "SCHEMA_ID",
    "SCHEMA_ID_V1",
    "SCHEMA_ID_V1_1",
    "DAILY_AMPLITUDE_LIMIT",
    "DAILY_RETURN_LIMIT",
    "WEEKLY_AMPLITUDE_LIMIT",
    "WEEKLY_RETURN_LIMIT",
    "TWIN_CARRIER",
    "UNREAD_START",
    "V1_INDEX_PANEL_PIECES",
    "build_implied_intraday_reversal_card",
    "build_session_piece_panel_from_minutes",
    "card_contract_payload",
    "causal_body_mask",
    "coerce_session_piece_panel",
    "describe_return_distribution",
    "expanding_median_mad",
    "resolve_piece_columns",
    "summarize_unconditional_means",
    "summarize_four_buckets",
    "daily_amplitude",
    "daily_main_mask",
    "build_weekly_context",
    "four_bucket_masks",
    "yearly_unconditional_table",
]
