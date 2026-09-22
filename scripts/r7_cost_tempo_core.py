"""R7 cost-tempo V1 research primitives; no orders or production routing."""
from __future__ import annotations

import math
from typing import Any
import numpy as np
import pandas as pd

IDENTITY = "R7_cost_tempo_reversal_research_v1"
HORIZONS = (5, 15)
COSTS = (0., 1., 2., 5.)
PRIMARY_ROUND_TRIP_BP = 4.


def path_coordinates(log_closes: np.ndarray, sigma: float) -> tuple[float, float]:
    p = np.asarray(log_closes, dtype=float)
    if p.ndim != 1 or len(p) - 1 not in HORIZONS or not np.isfinite(p).all():
        raise ValueError("expected a finite native 5/15-return path")
    if not math.isfinite(sigma) or sigma <= 0:
        raise ValueError("invalid causal sigma")
    d = p[1:] - p[0]
    e = float(d[np.argmax(np.abs(d))])
    end = float(d[-1])
    den = sigma * math.sqrt(len(p) - 1)
    rejection = 0. if e == 0 else math.copysign(1., e) * (abs(e) - math.copysign(1., e) * end) / den
    return end / den, rejection


def scheduled_room(timestamp: pd.Timestamp, horizon: int) -> bool:
    t = timestamp.tz_convert("Asia/Shanghai")
    minute = t.hour * 60 + t.minute
    if t.second or t.microsecond or horizon not in HORIZONS:
        return False
    return (570 < minute <= 690 - horizon) or (780 < minute <= 900 - horizon)


def native_scale_frame(one: pd.DataFrame, official: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Features use past only. Missing future labels never remove feature rows."""
    if horizon not in HORIZONS:
        raise ValueError("undeclared horizon")
    z = one.copy()
    z["ts"] = pd.to_datetime(z["bar_end_shanghai"], utc=True)
    z = z.sort_values("ts", kind="stable").reset_index(drop=True)
    if z["ts"].duplicated().any():
        raise ValueError("duplicate native time")
    logp = np.log(z["close"].to_numpy(float))
    if not np.isfinite(logp).all():
        raise ValueError("invalid native price")
    days = z["trading_day"].astype(str)
    exact = days.eq(days.shift()) & z["ts"].diff().eq(pd.Timedelta(minutes=1))
    segment = (~exact).cumsum().to_numpy()
    idx = np.flatnonzero(exact.to_numpy())
    rms = np.sqrt(pd.Series(logp[idx] - logp[idx-1]).pow(2).rolling(240, min_periods=240).mean().shift(1)).to_numpy()
    sigma = np.full(len(z), np.nan)
    sigma[idx] = rms
    anchors = set(pd.to_datetime(official["bar_end_shanghai"], utc=True).astype("int64"))
    times = z["ts"].tolist()
    rows = []
    for i in range(horizon, len(z)):
        t = times[i]
        if t.value not in anchors or not scheduled_room(t, horizon):
            continue
        if segment[i-horizon] != segment[i] or not np.isfinite(sigma[i]) or sigma[i] <= 0:
            continue
        endpoint, rejection = path_coordinates(logp[i-horizon:i+1], float(sigma[i]))
        future_valid = i+horizon < len(z) and segment[i] == segment[i+horizon]
        target = (logp[i+horizon]-logp[i])/(sigma[i]*math.sqrt(horizon)) if future_valid else np.nan
        rows.append({"ts": t, "trading_day": str(days.iloc[i]), "native_i": i,
                     "horizon": horizon, "sigma": float(sigma[i]), "endpoint_z": endpoint,
                     "rejection_signed_z": rejection, "target_z": float(target)})
    return pd.DataFrame(rows)


def design(frame: pd.DataFrame) -> np.ndarray:
    return np.column_stack([np.ones(len(frame)), frame["endpoint_z"], frame["rejection_signed_z"]]).astype(float)


def daily_forecasts(frame: pd.DataFrame, minimum_history: int = 1000) -> tuple[pd.DataFrame, list[dict]]:
    evaluation = frame.loc[frame.trading_day.between("2019-01-01", "2020-12-31")].copy()
    evaluation["forecast_z"] = np.nan
    audit = []
    for day, g in evaluation.groupby("trading_day", sort=True):
        hist = frame.loc[(frame.trading_day < day) & frame.target_z.notna()]
        X, y = design(hist), hist.target_z.to_numpy(float)
        if len(hist) < minimum_history or np.linalg.matrix_rank(X) != 3:
            raise ValueError("insufficient full-rank prior history")
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        evaluation.loc[g.index, "forecast_z"] = design(g) @ beta
        audit.append({"day": day, "history_max_day": hist.trading_day.max(), "n": len(hist), "beta": beta.tolist()})
    return evaluation, audit


def select_horizon(sigma: float, train_median: float) -> int:
    if not all(math.isfinite(x) and x > 0 for x in (sigma, train_median)):
        raise ValueError("unavailable tempo state")
    return 15 if sigma <= train_median else 5


def point_move_bp(forecast_z: float, sigma: float, horizon: int) -> float:
    if horizon not in HORIZONS or not math.isfinite(sigma) or sigma <= 0:
        raise ValueError("invalid horizon or sigma")
    v = float(forecast_z) * float(sigma) * math.sqrt(horizon)
    if not math.isfinite(v) or abs(v) > 1:
        raise ValueError("invalid/extreme point forecast")
    return (1. if v >= 0 else -1.) * math.expm1(v) * 10000.


def episode_ledger(frames: dict[int, pd.DataFrame], one: pd.DataFrame, mode: str, cutoff: float) -> pd.DataFrame:
    if mode not in {"FAST_EPISODE", "FAST_COST", "SLOW_COST", "ADAPTIVE_COST"}:
        raise ValueError("undeclared arm")
    indexed = {h: f.set_index("ts", verify_integrity=True) for h, f in frames.items()}
    z = one.copy()
    z["ts"] = pd.to_datetime(z.bar_end_shanghai, utc=True)
    z = z.sort_values("ts", kind="stable").reset_index(drop=True)
    occupied_until = pd.Timestamp.min.tz_localize("UTC")
    rows = []
    for t, fast in indexed[5].sort_index().iterrows():
        if t < occupied_until:
            continue
        h = 15 if mode == "SLOW_COST" else 5
        if mode == "ADAPTIVE_COST":
            h = select_horizon(float(fast.sigma), cutoff)
        if t not in indexed[h].index:  # absent PAST-scale features / scheduled session room
            continue
        signal = indexed[h].loc[t]
        pred = float(signal.forecast_z)
        move_bp = point_move_bp(pred, float(signal.sigma), h)
        if mode != "FAST_EPISODE" and move_bp <= PRIMARY_ROUND_TRIP_BP:
            continue
        p = float(np.clip(pred, -1, 1))
        if p == 0:
            continue
        i = int(signal.native_i)
        future = z.iloc[i+1:i+h+1]
        expected = pd.date_range(t+pd.Timedelta(minutes=1), periods=h, freq="1min")
        if len(future) != h or list(future.ts) != list(expected) or not future.trading_day.astype(str).eq(str(signal.trading_day)).all():
            raise ValueError("missing actual execution bars: do not drop selected trades")
        entry, exit_ = float(future.iloc[0].open), float(future.iloc[-1].close)
        if not (math.isfinite(entry) and math.isfinite(exit_) and entry > 0 and exit_ > 0):
            raise ValueError("invalid execution prices")
        occupied_until = t + pd.Timedelta(minutes=h)
        rows.append({"trading_day": str(signal.trading_day), "signal_ts": str(t),
                     "entry_bar_end": str(expected[0]), "exit_ts": str(occupied_until),
                     "horizon": h, "sigma": float(signal.sigma),
                     "tempo_state": "LOW_VOL" if fast.sigma <= cutoff else "HIGH_VOL",
                     "forecast_z": pred, "point_move_bp": move_bp, "position": p,
                     "entry_open": entry, "exit_close": exit_,
                     "gross_return": p*(exit_/entry-1), "turnover": 2*abs(p),
                     "flat_fill_touch": bool(future.causal_flat_fill.fillna(False).any())})
    columns = ["trading_day","signal_ts","entry_bar_end","exit_ts","horizon","sigma","tempo_state","forecast_z","point_move_bp","position","entry_open","exit_close","gross_return","turnover","flat_fill_touch"]
    return pd.DataFrame(rows, columns=columns)


def rank_identified_option_cards(cards: list[dict[str, Any]], *, underlying: str, direction: int,
                                  now: pd.Timestamp, risk_mandate_id: str) -> list[dict[str, Any]]:
    """Read-only eligible-card ranking, NOT a complete-cost router or fill model.

    Costs are supplied by the existing measurement primitive; do not substitute
    lifetime/tenor median spreads. Per-card eligibility must come from a separately
    validated premium/lot/depth/Greeks mandate, not from cheapest-cost ranking.
    """
    if direction not in (-1, 1) or now.tzinfo is None or not risk_mandate_id:
        raise ValueError("explicit direction, timezone, mandate required")
    output = []
    for card in cards:
        try:
            delta = float(card["delta_forward"])
            stamp = pd.Timestamp(card["available_at"])
            expires = pd.Timestamp(card["expires_at"])
            bp = float(card["identified_round_trip_hurdle_bp"])
            if card["underlying"] != underlying or delta*direction <= 0 or not .05 <= abs(delta) <= 1:
                continue
            if card["exposure_side"] != "buyer" or card["structure"] != "long_single":
                continue
            if card["risk_mandate_id"] != risk_mandate_id or card["eligible_under_mandate"] is not True:
                continue
            if card["source_semantics"] != "point_in_time_quote_measurement" or card["cost_status"] != "ok_identified_only":
                continue
            if stamp.tzinfo is None or expires.tzinfo is None or not 0 <= (now-stamp).total_seconds() <= 120 or expires <= now:
                continue
            numbers = {k: float(card[k]) for k in ("bid", "ask", "forward", "contract_multiplier", "fee_open", "fee_close", "gamma", "vega", "theta")}
            if not all(math.isfinite(v) for v in numbers.values()):
                continue
            if not (0 < numbers["bid"] <= numbers["ask"] and numbers["forward"] > 0 and numbers["contract_multiplier"] > 0 and numbers["fee_open"] >= 0 and numbers["fee_close"] >= 0):
                continue
            reference_bp = 10000. * ((numbers["ask"]-numbers["bid"])*numbers["contract_multiplier"]+numbers["fee_open"]+numbers["fee_close"]) / (abs(delta)*numbers["forward"]*numbers["contract_multiplier"])
            if not math.isfinite(bp) or bp < 0 or not math.isclose(bp, reference_bp, rel_tol=1e-10, abs_tol=1e-10):
                continue
            # Ready measurements are not full transaction costs when impact is absent.
            output.append({**card, "identified_round_trip_hurdle_bp": bp, "complete_all_in_cost_ready": False, "routing_authority": False})
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(output, key=lambda x: (x["identified_round_trip_hurdle_bp"], str(x["contract_id"])))
