# pyright: reportAny=false, reportArgumentType=false, reportAssignmentType=false
# pyright: reportAttributeAccessIssue=false, reportIndexIssue=false
# pyright: reportMissingTypeStubs=false, reportOperatorIssue=false
# pyright: reportReturnType=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false

"""Causal OLS versus paper-kernel battle for high-slope route ownership.

The module keeps three questions separate:

* can a tool emit a causal high-slope *entry* rather than merely score a
  retrospectively known burst;
* can the same tool own the complete entry/exit lifecycle; and
* does crossing the OLS and paper-kernel responsibilities add stable value.

All decisions use information available at one 15-minute close, execute at
the next open, and then pass through a true A-share T+1 same-session exit lock.
Retrospective burst events are diagnostics only and never enter a decision.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final, Literal

import numpy as np
import pandas as pd

from factor_lab.market_state.ols_explosive_channel_v1 import (
    OLSExplosiveChannelSpec,
    build_ols_explosive_channel_from_features,
)
from factor_lab.strategy.services.risk_off_v56_steep_crash_specialist import (
    SteepCrashV56Spec,
    attach_v56_independent_channel_features,
)

BARS_PER_DAY: Final[int] = 16
PAPER_UP_SPAN_DAYS: Final[int] = 2
PAPER_DOWN_SPAN_DAYS: Final[int] = 4
PAPER_TAIL_LOOKBACK_BARS: Final[int] = 33 * BARS_PER_DAY
PAPER_TAIL_MINIMUM_BARS: Final[int] = PAPER_TAIL_LOOKBACK_BARS // 2
PAPER_TAIL_QUANTILES: Final[tuple[float, ...]] = (0.85, 0.90, 0.925, 0.95)
OLS_WINDOWS: Final[tuple[int, ...]] = (12, 24)
BUY_COST_BPS: Final[float] = 1.0
SELL_COST_BPS: Final[float] = 6.0
MAXIMUM_TIMESTAMP_EXCLUSIVE: Final[pd.Timestamp] = pd.Timestamp("2022-01-01")
BURST_MOVE: Final[float] = 0.08
BURST_MAXIMUM_BARS: Final[int] = 80
BURST_MINIMUM_PATH_EFFICIENCY: Final[float] = 0.35

Side = Literal["up", "down"]


@dataclass(frozen=True, slots=True)
class CandidatePath:
    """One direction-specific candidate and its true-T+1 position."""

    candidate_id: str
    side: Side
    decision_active: pd.Series
    executable_position: pd.Series


def _validate_carrier(
    causal_ohlc: pd.DataFrame,
    *,
    maximum_timestamp_exclusive: pd.Timestamp = MAXIMUM_TIMESTAMP_EXCLUSIVE,
) -> pd.DataFrame:
    required = ("timestamp", "open", "high", "low", "close")
    missing = [column for column in required if column not in causal_ohlc]
    if missing:
        raise KeyError(f"OLS/paper battle missing OHLC columns: {missing}")
    carrier = causal_ohlc.loc[:, required].copy().reset_index(drop=True)
    index = pd.DatetimeIndex(pd.to_datetime(carrier["timestamp"], errors="raise"))
    if index.empty or index.has_duplicates or not index.is_monotonic_increasing:
        raise ValueError("OLS/paper timestamps must be non-empty, unique, and ordered")
    if index.max() >= maximum_timestamp_exclusive:
        raise RuntimeError("OLS/paper battle crossed the sealed 2022 boundary")
    for column in required[1:]:
        values = pd.to_numeric(carrier[column], errors="raise").to_numpy(float)
        if not np.isfinite(values).all() or bool((values <= 0.0).any()):
            raise ValueError(f"OLS/paper {column} must be finite and positive")
        carrier[column] = values
    invalid = (
        carrier["low"].gt(carrier["high"])
        | carrier["open"].lt(carrier["low"])
        | carrier["open"].gt(carrier["high"])
        | carrier["close"].lt(carrier["low"])
        | carrier["close"].gt(carrier["high"])
    )
    if bool(invalid.any()):
        raise ValueError("OLS/paper battle received invalid OHLC bars")
    return carrier


def _reciprocal_ohlc(carrier: pd.DataFrame) -> pd.DataFrame:
    mirrored = carrier.copy()
    mirrored["open"] = 1.0 / carrier["open"]
    mirrored["close"] = 1.0 / carrier["close"]
    mirrored["high"] = 1.0 / carrier["low"]
    mirrored["low"] = 1.0 / carrier["high"]
    return mirrored


def _prior_path_attributes(
    log_close: np.ndarray,
    *,
    window: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Return prior-only path efficiency and largest adverse-tail share."""

    size = len(log_close)
    efficiency = np.full(size, np.nan, dtype=float)
    tail_share = np.full(size, np.nan, dtype=float)
    for location in range(window, size):
        history = log_close[location - window : location]
        changes = np.diff(history)
        gross = float(np.abs(changes).sum())
        net_down = float(history[0] - history[-1])
        if gross > 0.0:
            efficiency[location] = abs(net_down) / gross
        if net_down > np.finfo(float).eps:
            tail_share[location] = float(np.maximum(-changes, 0.0).max(initial=0.0) / net_down)
    return efficiency, tail_share


def build_lightweight_ols_feature_panel(
    causal_ohlc: pd.DataFrame,
    *,
    maximum_timestamp_exclusive: pd.Timestamp = MAXIMUM_TIMESTAMP_EXCLUSIVE,
) -> pd.DataFrame:
    """Reproduce the frozen W12/W24 OLS inputs without unrelated V59 columns."""

    carrier = _validate_carrier(
        causal_ohlc,
        maximum_timestamp_exclusive=maximum_timestamp_exclusive,
    )
    output = pd.DataFrame(index=carrier.index)
    geometry_spec = SteepCrashV56Spec(
        channel_windows_bars=OLS_WINDOWS,
        channel_minimum_fit_r2=0.10,
    )
    original_close = carrier["close"].to_numpy(float)
    for side in ("down", "up"):
        local = carrier if side == "down" else _reciprocal_ohlc(carrier)
        local = local.reset_index(drop=True)
        local_close = local["close"].to_numpy(float)
        geometry = attach_v56_independent_channel_features(local, geometry_spec)
        log_close = np.log(local_close)
        for window in OLS_WINDOWS:
            source = f"exit_channel_w{window}"
            slope = geometry[f"{source}_slope_log_per_bar"].to_numpy(float)
            fit_r2 = geometry[f"{source}_fit_r2"].to_numpy(float)
            upper = geometry[f"{source}_upper_rail"].to_numpy(float)
            lower = geometry[f"{source}_lower_rail"].to_numpy(float)
            efficiency, tail_share = _prior_path_attributes(
                log_close,
                window=window,
            )
            centre = np.sqrt(upper * lower)
            qualified = (
                np.isfinite(slope)
                & np.isfinite(fit_r2)
                & np.isfinite(upper)
                & np.isfinite(lower)
                & np.isfinite(efficiency)
                & np.isfinite(tail_share)
                & (slope < -0.001)
            )
            # Keep the expression split: numpy does not short-circuit and the
            # explicit conjunction mirrors V59's frozen fast-family contract.
            qualified = (
                np.asarray(qualified, dtype=bool) & (tail_share <= 0.50) & (local_close <= centre) & (fit_r2 >= 0.10) & (efficiency >= 0.30)
            )
            prior = np.zeros(len(carrier), dtype=bool)
            if len(prior) > 1:
                prior[1:] = qualified[:-1]
            candidate = qualified & ~prior
            if side == "up":
                slope = -slope
                transformed_upper = 1.0 / lower
                transformed_lower = 1.0 / upper
                upper, lower = transformed_upper, transformed_lower
            prefix = f"context_free_explosive_{side}_w{window}_"
            values: dict[str, np.ndarray] = {
                "path_efficiency": efficiency,
                "fit_r2": fit_r2,
                "slope_log_per_15m": slope,
                "upper_rail": upper,
                "lower_rail": lower,
                "qualified": qualified,
                "candidate_trigger": candidate,
            }
            for name, value in values.items():
                output[f"{prefix}{name}"] = value
    output["runtime_uses_future"] = False
    output["runtime_uses_registered_events"] = False
    # The original close is deliberately touched here so reciprocal mistakes
    # cannot silently pass an otherwise shape-only unit test.
    if not np.allclose(original_close, carrier["close"].to_numpy(float)):
        raise RuntimeError("OLS/paper carrier was mutated while mirroring")
    return output


def build_ols_native_panel(
    causal_ohlc: pd.DataFrame,
    *,
    maximum_timestamp_exclusive: pd.Timestamp = MAXIMUM_TIMESTAMP_EXCLUSIVE,
) -> pd.DataFrame:
    carrier = _validate_carrier(
        causal_ohlc,
        maximum_timestamp_exclusive=maximum_timestamp_exclusive,
    )
    features = build_lightweight_ols_feature_panel(
        carrier,
        maximum_timestamp_exclusive=maximum_timestamp_exclusive,
    )
    output = build_ols_explosive_channel_from_features(
        carrier,
        features,
        OLSExplosiveChannelSpec("two_opposite_closes"),
    )
    output.attrs["lightweight_feature_panel"] = features
    return output


def _lagged_ewma_volatility(returns: pd.Series, span_bars: int) -> pd.Series:
    return np.sqrt(returns.pow(2).ewm(span=span_bars, adjust=False).mean()).shift(1)


def build_paper_direction_scores(
    close_price: pd.Series,
    *,
    maximum_timestamp_exclusive: pd.Timestamp = MAXIMUM_TIMESTAMP_EXCLUSIVE,
) -> pd.DataFrame:
    """Build the exact V16 directional winners through the allowed boundary."""

    if not isinstance(close_price.index, pd.DatetimeIndex):
        raise TypeError("paper close_price must use a DatetimeIndex")
    if close_price.index.empty or close_price.index.has_duplicates or not close_price.index.is_monotonic_increasing:
        raise ValueError("paper score index must be non-empty, unique, and ordered")
    if close_price.index.max() >= maximum_timestamp_exclusive:
        raise RuntimeError("paper scores crossed the sealed 2022 boundary")
    close = pd.to_numeric(close_price, errors="raise").astype(float)
    if close.le(0.0).any():
        raise ValueError("paper closes must be positive")
    returns = close.pct_change(fill_method=None)
    up_bars = PAPER_UP_SPAN_DAYS * BARS_PER_DAY
    down_bars = PAPER_DOWN_SPAN_DAYS * BARS_PER_DAY
    up_score = (
        math.sqrt(up_bars)
        * returns.ewm(
            span=up_bars,
            adjust=False,
        ).mean()
    )
    down_volatility = _lagged_ewma_volatility(returns, down_bars)
    down_score = (
        math.sqrt(down_bars)
        * (returns / down_volatility)
        .ewm(
            span=down_bars,
            adjust=False,
        )
        .mean()
    )
    return pd.DataFrame(
        {
            "paper_up_raw_s2_score": up_score,
            "paper_down_matched_s4_score": down_score,
            "runtime_uses_future": False,
        },
        index=close.index,
    )


def paper_tail_threshold(score: pd.Series, quantile: float) -> pd.Series:
    if not 0.5 < quantile < 1.0:
        raise ValueError("paper tail quantile must lie in (0.5, 1.0)")
    return (
        score.abs()
        .rolling(
            PAPER_TAIL_LOOKBACK_BARS,
            min_periods=PAPER_TAIL_MINIMUM_BARS,
        )
        .quantile(quantile)
        .shift(1)
    )


def _boolean_lifecycle(trigger: pd.Series, exit_condition: pd.Series) -> pd.Series:
    if not trigger.index.equals(exit_condition.index):
        raise ValueError("trigger and exit condition indexes must match")
    active = False
    values = np.zeros(len(trigger), dtype=bool)
    for location, (starts, exits) in enumerate(
        zip(
            trigger.to_numpy(bool),
            exit_condition.to_numpy(bool),
            strict=True,
        )
    ):
        if active and exits:
            active = False
        if not active and starts:
            active = True
        values[location] = active
    return pd.Series(values, index=trigger.index, dtype=bool)


def build_paper_tail_decision(
    score: pd.Series,
    *,
    side: Side,
    quantile: float,
) -> pd.Series:
    sign = 1.0 if side == "up" else -1.0
    directional = pd.to_numeric(score, errors="raise") * sign
    threshold = paper_tail_threshold(score, quantile)
    above = directional.gt(threshold)
    trigger = above & ~above.shift(1, fill_value=False)
    return _boolean_lifecycle(trigger, directional.le(0.0)).rename(f"paper_{side}_tail_q{int(round(quantile * 1000)):03d}_decision")


def build_paper_tail_active_decision(
    score: pd.Series,
    *,
    side: Side,
    quantile: float,
) -> pd.Series:
    """Hold only while the directional score remains in its lagged tail.

    This is a deliberately narrow, post-preregistration diagnostic.  Unlike
    ``build_paper_tail_decision``, it does not turn a tail observation into a
    longer zero-cross trend lifecycle.
    """

    sign = 1.0 if side == "up" else -1.0
    directional = pd.to_numeric(score, errors="raise") * sign
    threshold = paper_tail_threshold(score, quantile)
    return directional.gt(threshold).rename(f"paper_{side}_tail_active_q{int(round(quantile * 1000)):03d}_decision")


def enforce_true_t_plus_one(decision_active: pd.Series, *, side: Side) -> pd.Series:
    """Shift a close decision once, then block same-session liquidation."""

    if not isinstance(decision_active.index, pd.DatetimeIndex):
        raise TypeError("T+1 decision requires a DatetimeIndex")
    desired = decision_active.astype(bool).shift(1, fill_value=False)
    held = False
    entry_date: object | None = None
    sign = 1.0 if side == "up" else -1.0
    values = np.zeros(len(desired), dtype=float)
    for location, (timestamp, wanted) in enumerate(desired.items()):
        trade_date = timestamp.date()
        if not held and bool(wanted):
            held = True
            entry_date = trade_date
        elif held and not bool(wanted) and entry_date != trade_date:
            held = False
            entry_date = None
        values[location] = sign if held else 0.0
    return pd.Series(values, index=desired.index, dtype=float)


def _side_score(scores: pd.DataFrame, side: Side) -> pd.Series:
    return scores["paper_up_raw_s2_score" if side == "up" else "paper_down_matched_s4_score"]


def build_ols_paper_cross_decision(
    ols_panel: pd.DataFrame,
    scores: pd.DataFrame,
    *,
    side: Side,
    exit_owner: str,
) -> pd.Series:
    """Use an OLS qualification edge, optionally handing exit to paper."""

    sign = 1 if side == "up" else -1
    score = _side_score(scores, side) * float(sign)
    paper_agrees = score.gt(0.0)
    ols_active = ols_panel["decision_position_for_next_bar"].eq(sign)
    trigger = ols_panel["entry_trigger_direction"].eq(sign) & paper_agrees
    if exit_owner == "ols":
        exits = ~ols_active
    elif exit_owner == "paper":
        exits = ~paper_agrees
    elif exit_owner == "earliest":
        exits = (~ols_active) | (~paper_agrees)
    elif exit_owner == "latest":
        exits = (~ols_active) & (~paper_agrees)
    else:
        raise ValueError(f"unsupported crossed exit owner: {exit_owner}")
    return _boolean_lifecycle(trigger, exits).rename(f"ols_entry_paper_confirm_{exit_owner}_exit_{side}")


def build_paper_trigger_ols_midline_decision(
    causal_ohlc: pd.DataFrame,
    ols_features: pd.DataFrame,
    paper_trigger: pd.Series,
    *,
    side: Side,
    maximum_timestamp_exclusive: pd.Timestamp = MAXIMUM_TIMESTAMP_EXCLUSIVE,
) -> pd.Series:
    """Let a paper tail trigger freeze the best available OLS centreline."""

    carrier = _validate_carrier(
        causal_ohlc,
        maximum_timestamp_exclusive=maximum_timestamp_exclusive,
    )
    if len(carrier) != len(ols_features) or len(carrier) != len(paper_trigger):
        raise ValueError("paper-trigger/OLS-exit inputs must have equal length")
    close = carrier["close"].to_numpy(float)
    active = False
    anchor = -1
    slope = math.nan
    upper = math.nan
    lower = math.nan
    decisions = np.zeros(len(carrier), dtype=bool)
    for location in range(len(carrier)):
        if active:
            elapsed = location - anchor
            boundary = math.sqrt(upper * lower) * math.exp(slope * elapsed)
            broken = close[location] < boundary if side == "up" else close[location] > boundary
            if broken:
                active = False
        if not active and bool(paper_trigger.iloc[location]):
            choices: list[tuple[float, int, float, float, float]] = []
            for window in OLS_WINDOWS:
                prefix = f"context_free_explosive_{side}_w{window}_"
                local_slope = float(ols_features[f"{prefix}slope_log_per_15m"].iloc[location])
                local_upper = float(ols_features[f"{prefix}upper_rail"].iloc[location])
                local_lower = float(ols_features[f"{prefix}lower_rail"].iloc[location])
                efficiency = float(ols_features[f"{prefix}path_efficiency"].iloc[location])
                fit_r2 = float(ols_features[f"{prefix}fit_r2"].iloc[location])
                directional = local_slope > 0.0 if side == "up" else local_slope < 0.0
                finite = all(
                    math.isfinite(value)
                    for value in (
                        local_slope,
                        local_upper,
                        local_lower,
                        efficiency,
                        fit_r2,
                    )
                )
                if not finite or not directional:
                    continue
                quality = abs(local_slope) * float(window - 1) * max(efficiency, 0.0) * max(fit_r2, 0.0)
                choices.append((quality, window, local_slope, local_upper, local_lower))
            if choices:
                _, _, slope, upper, lower = max(choices, key=lambda item: item[0])
                anchor = location
                active = True
        decisions[location] = active
    return pd.Series(decisions, index=paper_trigger.index, dtype=bool).rename(f"paper_trigger_ols_midline_exit_{side}")


def build_candidate_paths(
    causal_ohlc: pd.DataFrame,
    *,
    tail_quantiles: Sequence[float] = PAPER_TAIL_QUANTILES,
    maximum_timestamp_exclusive: pd.Timestamp = MAXIMUM_TIMESTAMP_EXCLUSIVE,
) -> tuple[dict[str, CandidatePath], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build fixed native and crossed candidates for both directions."""

    carrier = _validate_carrier(
        causal_ohlc,
        maximum_timestamp_exclusive=maximum_timestamp_exclusive,
    )
    index = pd.DatetimeIndex(carrier["timestamp"])
    indexed_close = pd.Series(carrier["close"].to_numpy(float), index=index)
    scores = build_paper_direction_scores(
        indexed_close,
        maximum_timestamp_exclusive=maximum_timestamp_exclusive,
    )
    features = build_lightweight_ols_feature_panel(
        carrier,
        maximum_timestamp_exclusive=maximum_timestamp_exclusive,
    )
    ols_panel = build_ols_explosive_channel_from_features(
        carrier,
        features,
        OLSExplosiveChannelSpec("two_opposite_closes"),
    )
    ols_panel.index = index
    features.index = index
    paths: dict[str, CandidatePath] = {}
    for side in ("up", "down"):
        sign = 1 if side == "up" else -1
        ols_decision = ols_panel["decision_position_for_next_bar"].eq(sign)
        native_id = f"ols_native_{side}"
        paths[native_id] = CandidatePath(
            candidate_id=native_id,
            side=side,
            decision_active=ols_decision,
            executable_position=enforce_true_t_plus_one(ols_decision, side=side),
        )
        score = _side_score(scores, side)
        sign_decision = score.mul(float(sign)).gt(0.0)
        sign_id = f"paper_sign_control_{side}"
        paths[sign_id] = CandidatePath(
            candidate_id=sign_id,
            side=side,
            decision_active=sign_decision,
            executable_position=enforce_true_t_plus_one(sign_decision, side=side),
        )
        for quantile in tail_quantiles:
            paper_decision = build_paper_tail_decision(
                score,
                side=side,
                quantile=float(quantile),
            )
            suffix = f"q{int(round(float(quantile) * 1000)):03d}"
            paper_id = f"paper_native_{side}_{suffix}"
            paths[paper_id] = CandidatePath(
                candidate_id=paper_id,
                side=side,
                decision_active=paper_decision,
                executable_position=enforce_true_t_plus_one(
                    paper_decision,
                    side=side,
                ),
            )
            tail_active_decision = build_paper_tail_active_decision(
                score,
                side=side,
                quantile=float(quantile),
            )
            tail_active_id = f"paper_tail_active_{side}_{suffix}"
            paths[tail_active_id] = CandidatePath(
                candidate_id=tail_active_id,
                side=side,
                decision_active=tail_active_decision,
                executable_position=enforce_true_t_plus_one(
                    tail_active_decision,
                    side=side,
                ),
            )
            union_decision = ols_decision | tail_active_decision
            union_id = f"ols_or_paper_tail_active_{side}_{suffix}"
            paths[union_id] = CandidatePath(
                candidate_id=union_id,
                side=side,
                decision_active=union_decision,
                executable_position=enforce_true_t_plus_one(
                    union_decision,
                    side=side,
                ),
            )
            residual_decision = tail_active_decision & ~ols_decision
            residual_id = f"paper_tail_residual_outside_ols_{side}_{suffix}"
            paths[residual_id] = CandidatePath(
                candidate_id=residual_id,
                side=side,
                decision_active=residual_decision,
                executable_position=enforce_true_t_plus_one(
                    residual_decision,
                    side=side,
                ),
            )
            threshold = paper_tail_threshold(score, float(quantile))
            directional = score * float(sign)
            above = directional.gt(threshold)
            paper_trigger = above & ~above.shift(1, fill_value=False)
            ols_exit_decision = build_paper_trigger_ols_midline_decision(
                carrier,
                features,
                paper_trigger,
                side=side,
                maximum_timestamp_exclusive=maximum_timestamp_exclusive,
            )
            crossed_id = f"paper_trigger_ols_exit_{side}_{suffix}"
            paths[crossed_id] = CandidatePath(
                candidate_id=crossed_id,
                side=side,
                decision_active=ols_exit_decision,
                executable_position=enforce_true_t_plus_one(
                    ols_exit_decision,
                    side=side,
                ),
            )
        for owner in ("ols", "paper", "earliest", "latest"):
            crossed = build_ols_paper_cross_decision(
                ols_panel,
                scores,
                side=side,
                exit_owner=owner,
            )
            crossed_id = f"ols_trigger_{owner}_exit_{side}"
            paths[crossed_id] = CandidatePath(
                candidate_id=crossed_id,
                side=side,
                decision_active=crossed,
                executable_position=enforce_true_t_plus_one(crossed, side=side),
            )
    return paths, ols_panel, scores, features


def signed_position_ledger(
    open_price: pd.Series,
    position: pd.Series,
) -> pd.DataFrame:
    if not open_price.index.equals(position.index):
        raise ValueError("open price and position indexes must match")
    forward = np.log(open_price.shift(-1) / open_price)
    change = position.diff().fillna(position)
    cost = change.clip(lower=0.0) * (BUY_COST_BPS / 10_000.0) + (-change.clip(upper=0.0)) * (SELL_COST_BPS / 10_000.0)
    gross = position * forward
    return pd.DataFrame(
        {
            "position": position,
            "forward_open_log_return": forward,
            "gross_log_return": gross,
            "cost_log_return": cost,
            "net_log_return": gross - cost,
            "turnover_units": change.abs(),
        },
        index=open_price.index,
    )


def episode_ledger(
    open_price: pd.Series,
    position: pd.Series,
    *,
    candidate_id: str,
    side: Side,
) -> pd.DataFrame:
    sign = 1.0 if side == "up" else -1.0
    active = position.eq(sign).to_numpy(bool)
    rows: list[dict[str, object]] = []
    start = -1
    episode = 0
    for location, current in enumerate(np.r_[active, False]):
        if current and start < 0:
            start = location
            continue
        if current or start < 0:
            continue
        end = location - 1
        terminal = min(end + 1, len(open_price) - 1)
        path = sign * np.log(open_price.iloc[start : terminal + 1].to_numpy(float) / float(open_price.iloc[start]))
        episode += 1
        gross = float(path[-1]) if len(path) else 0.0
        rows.append(
            {
                "episode_id": f"{candidate_id}:{episode:04d}",
                "candidate_id": candidate_id,
                "side": side,
                "start": open_price.index[start],
                "end": open_price.index[end],
                "start_location": start,
                "end_location": end,
                "bar_count": end - start + 1,
                "session_count": int(pd.DatetimeIndex(open_price.index[start : end + 1]).normalize().nunique()),
                "gross_log_return": gross,
                "net_log_return": gross - (BUY_COST_BPS + SELL_COST_BPS) / 10_000.0,
                "maximum_favorable_log_return": float(max(path.max(initial=0.0), 0.0)),
                "maximum_adverse_log_return": float(max((-path).max(initial=0.0), 0.0)),
            }
        )
        start = -1
    return pd.DataFrame(rows)


def evaluate_candidate(
    open_price: pd.Series,
    path: CandidatePath,
    *,
    period_id: str,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
) -> tuple[dict[str, object], pd.DataFrame]:
    mask = open_price.index.to_series().between(pd.Timestamp(start), pd.Timestamp(end))
    index = open_price.index[mask]
    if len(index) < 2:
        raise ValueError(f"candidate period is too short: {period_id}")
    local_open = open_price.reindex(index)
    local_position = path.executable_position.reindex(index).fillna(0.0).copy()
    local_position.iloc[-1] = 0.0
    ledger = signed_position_ledger(local_open, local_position)
    net = ledger["net_log_return"].fillna(0.0)
    daily = net.groupby(net.index.normalize()).sum()
    daily_std = float(daily.std(ddof=0))
    elapsed_years = max(
        (index[-1] - index[0]).total_seconds() / (365.2425 * 86400.0),
        1.0 / 365.2425,
    )
    nav = np.exp(net.cumsum())
    episodes = episode_ledger(
        local_open,
        local_position,
        candidate_id=path.candidate_id,
        side=path.side,
    )
    if len(episodes):
        winners = episodes.loc[episodes["net_log_return"].gt(0.0)]
        losers = episodes.loc[episodes["net_log_return"].lt(0.0)]
    else:
        winners = episodes
        losers = episodes
    average_win = float(winners["net_log_return"].mean()) if len(winners) else 0.0
    average_loss = float(-losers["net_log_return"].mean()) if len(losers) else 0.0
    total = float(net.sum())
    return (
        {
            "candidate_id": path.candidate_id,
            "side": path.side,
            "period_id": period_id,
            "start": str(index[0]),
            "end": str(index[-1]),
            "elapsed_years": elapsed_years,
            "net_log_return": total,
            "net_log_return_per_year": total / elapsed_years,
            "compound_return": float(math.exp(total) - 1.0),
            "daily_sharpe": (float(math.sqrt(252.0) * daily.mean() / daily_std) if daily_std > 0.0 else 0.0),
            "maximum_drawdown": float((nav / nav.cummax() - 1.0).min()),
            "exposure_share": float(local_position.abs().mean()),
            "turnover_units": float(ledger["turnover_units"].sum()),
            "episode_count": int(len(episodes)),
            "mean_bars_per_episode": float(episodes["bar_count"].mean()) if len(episodes) else 0.0,
            "mean_sessions_per_episode": float(episodes["session_count"].mean()) if len(episodes) else 0.0,
            "positive_episode_rate": float(episodes["net_log_return"].gt(0.0).mean()) if len(episodes) else 0.0,
            "average_win_log_return": average_win,
            "average_loss_log_return": average_loss,
            "payoff_ratio": average_win / average_loss if average_loss > 0.0 else 0.0,
        },
        episodes,
    )


def entry_outcome_summary(
    open_price: pd.Series,
    position: pd.Series,
    *,
    side: Side,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    horizon_bars: int = BURST_MAXIMUM_BARS,
) -> dict[str, float | int]:
    sign = 1.0 if side == "up" else -1.0
    starts = position.eq(sign) & position.shift(1, fill_value=0.0).eq(0.0)
    locations = np.flatnonzero(starts.to_numpy(bool))
    period_start = pd.Timestamp(start)
    period_end = pd.Timestamp(end)
    time_index = pd.DatetimeIndex(open_price.index)
    period_end_location = min(int(time_index.get_indexer([period_end], method="pad")[0]), len(open_price) - 1)
    favorable: list[float] = []
    for location in locations:
        timestamp = open_price.index[location]
        if timestamp < period_start or timestamp > period_end:
            continue
        right = min(location + horizon_bars, period_end_location)
        path = sign * np.log(open_price.iloc[location : right + 1].to_numpy(float) / float(open_price.iloc[location]))
        favorable.append(float(max(path.max(initial=0.0), 0.0)))
    values = np.asarray(favorable, dtype=float)
    count = len(values)
    return {
        "entry_count": count,
        "mean_forward_80bar_mfe": float(values.mean()) if count else 0.0,
        "median_forward_80bar_mfe": float(np.median(values)) if count else 0.0,
        "strong_8pct_count": int((values >= math.log1p(0.08)).sum()),
        "strong_8pct_rate": float((values >= math.log1p(0.08)).mean()) if count else 0.0,
        "weak_4_to_8pct_count": int(((values >= math.log1p(0.04)) & (values < math.log1p(0.08))).sum()),
        "false_below_4pct_count": int((values < math.log1p(0.04)).sum()),
        "false_below_4pct_rate": float((values < math.log1p(0.04)).mean()) if count else 0.0,
    }


def build_bounded_burst_event_clock(
    open_price: pd.Series,
    *,
    period_id: str,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
) -> pd.DataFrame:
    """Build an ex-post opportunity clock; callers must never route on it."""

    scope = pd.to_numeric(open_price, errors="raise").loc[start:end]
    rows: list[dict[str, object]] = []
    values = scope.to_numpy(float)
    log_values = np.log(values)
    absolute_steps = np.abs(np.diff(log_values))
    cumulative_path = np.concatenate(([0.0], np.cumsum(absolute_steps)))
    for side in ("up", "down"):
        cursor = 0
        event_number = 0
        while cursor < len(scope) - 1:
            found: tuple[int, int, float, float] | None = None
            for right in range(cursor + 1, len(scope)):
                window_left = max(cursor, right - BURST_MAXIMUM_BARS)
                window = values[window_left:right]
                if not len(window):
                    continue
                relative_anchor = int(np.argmin(window)) if side == "up" else int(np.argmax(window))
                left = window_left + relative_anchor
                move = float(log_values[right] - log_values[left])
                directional_move = move if side == "up" else -move
                if directional_move < math.log1p(BURST_MOVE):
                    continue
                path = float(cumulative_path[right] - cumulative_path[left])
                efficiency = abs(move) / path if path > 0.0 else 0.0
                if efficiency < BURST_MINIMUM_PATH_EFFICIENCY:
                    continue
                found = (left, right, move, efficiency)
                break
            if found is None:
                break
            left, right, move, efficiency = found
            event_number += 1
            rows.append(
                {
                    "event_id": f"{period_id}:{side}:{event_number:04d}",
                    "period_id": period_id,
                    "side": side,
                    "start": scope.index[left],
                    "confirmation": scope.index[right],
                    "bar_count": right - left,
                    "market_log_move": move,
                    "path_efficiency": efficiency,
                    "runtime_input_allowed": False,
                }
            )
            cursor = right + 1
    return pd.DataFrame(rows).sort_values(["start", "side"]).reset_index(drop=True)


def event_capture_summary(
    open_price: pd.Series,
    position: pd.Series,
    event_clock: pd.DataFrame,
    *,
    side: Side,
) -> dict[str, float | int]:
    local_events = event_clock.loc[event_clock["side"].eq(side)]
    sign = 1.0 if side == "up" else -1.0
    captures: list[float] = []
    weighted: list[float] = []
    for event in local_events.itertuples(index=False):
        index = open_price.loc[pd.Timestamp(event.start) : pd.Timestamp(event.confirmation)].index
        intervals = index[:-1]
        if not len(intervals):
            continue
        forward = np.log(open_price.shift(-1) / open_price).loc[intervals]
        desired = position.loc[intervals].eq(sign).astype(float)
        captures.append(float(desired.mean()))
        weights = forward.abs()
        denominator = float(weights.sum())
        weighted.append(float((desired * weights).sum()) / denominator if denominator > 0.0 else 0.0)
    return {
        "opportunity_count": int(len(local_events)),
        "mean_event_bar_capture": float(np.mean(captures)) if captures else 0.0,
        "mean_abs_return_weighted_capture": float(np.mean(weighted)) if weighted else 0.0,
        "event_any_capture_rate": float(np.mean(np.asarray(captures) > 0.0)) if captures else 0.0,
    }


__all__ = [
    "BARS_PER_DAY",
    "BURST_MAXIMUM_BARS",
    "CandidatePath",
    "PAPER_TAIL_QUANTILES",
    "build_bounded_burst_event_clock",
    "build_candidate_paths",
    "build_lightweight_ols_feature_panel",
    "build_ols_native_panel",
    "build_ols_paper_cross_decision",
    "build_paper_direction_scores",
    "build_paper_tail_active_decision",
    "build_paper_tail_decision",
    "build_paper_trigger_ols_midline_decision",
    "enforce_true_t_plus_one",
    "entry_outcome_summary",
    "episode_ledger",
    "evaluate_candidate",
    "event_capture_summary",
    "paper_tail_threshold",
    "signed_position_ledger",
]
