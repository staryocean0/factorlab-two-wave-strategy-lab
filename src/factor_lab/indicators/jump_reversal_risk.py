"""Jump Reversal Risk (JRR).

JRR measures whether large up/down bars are flipping without a small-bar
transition buffer.  This is the market state where ordinary low-pass filters
can lag badly: the series can jump from strong down to strong up, or back,
before a smooth filtered turn is visible.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

JRR_HIGH_RISK = "high_jump_reversal_risk"
JRR_NORMAL = "normal"
JRR_INSUFFICIENT = "insufficient"


@dataclass(frozen=True, slots=True)
class JumpReversalRiskConfig:
    """Configuration for close-to-close Jump Reversal Risk."""

    window: int = 20
    rank_window: int = 252
    strong_return_rank_threshold: float = 0.80
    high_risk_threshold: float = 0.20
    epsilon: float = 1e-12

    def __post_init__(self) -> None:
        if self.window < 2:
            raise ValueError("JRR window must be >= 2")
        if self.rank_window < 2:
            raise ValueError("JRR rank_window must be >= 2")
        if not 0.0 < self.strong_return_rank_threshold <= 1.0:
            raise ValueError(
                "JRR strong_return_rank_threshold must be in (0, 1]"
            )
        if not 0.0 <= self.high_risk_threshold <= 1.0:
            raise ValueError("JRR high_risk_threshold must be in [0, 1]")
        if self.epsilon <= 0.0 or not math.isfinite(self.epsilon):
            raise ValueError("JRR epsilon must be a finite positive value")


@dataclass(frozen=True, slots=True)
class JumpReversalRiskResult:
    """Computed JRR result for one ordered close series."""

    score: float | None
    no_buffer_reversal_rate: float | None
    volatility_rank: float | None
    vol_of_vol_rank: float | None
    latest_return_rank: float | None
    latest_abrupt_reversal: bool
    regime: str
    valid_bar_count: int
    window: int
    rank_window: int
    strong_return_rank_threshold: float
    high_risk_threshold: float

    def to_dict(self) -> dict[str, bool | float | int | str | None]:
        return {
            "score": self.score,
            "no_buffer_reversal_rate": self.no_buffer_reversal_rate,
            "volatility_rank": self.volatility_rank,
            "vol_of_vol_rank": self.vol_of_vol_rank,
            "latest_return_rank": self.latest_return_rank,
            "latest_abrupt_reversal": self.latest_abrupt_reversal,
            "regime": self.regime,
            "valid_bar_count": self.valid_bar_count,
            "window": self.window,
            "rank_window": self.rank_window,
            "strong_return_rank_threshold": self.strong_return_rank_threshold,
            "high_risk_threshold": self.high_risk_threshold,
        }


def compute_jump_reversal_risk(
    closes: Sequence[object],
    *,
    config: JumpReversalRiskConfig | None = None,
) -> JumpReversalRiskResult:
    """Compute the latest JRR value from an ordered close-price sequence."""

    cfg = config or JumpReversalRiskConfig()
    frame = rolling_jump_reversal_risk(
        pd.Series(list(closes), dtype="object"),
        config=cfg,
    )
    if frame.empty:
        return _insufficient_result(cfg, valid_bar_count=0)
    latest = frame.iloc[-1]
    valid_bar_count = int(latest["valid_bar_count"]) if pd.notna(latest["valid_bar_count"]) else 0
    if pd.isna(latest["score"]):
        return _insufficient_result(cfg, valid_bar_count=valid_bar_count)
    return JumpReversalRiskResult(
        score=float(latest["score"]),
        no_buffer_reversal_rate=float(latest["no_buffer_reversal_rate"]),
        volatility_rank=float(latest["volatility_rank"]),
        vol_of_vol_rank=float(latest["vol_of_vol_rank"]),
        latest_return_rank=float(latest["return_rank"]),
        latest_abrupt_reversal=bool(latest["abrupt_reversal"]),
        regime=str(latest["regime"]),
        valid_bar_count=valid_bar_count,
        window=cfg.window,
        rank_window=cfg.rank_window,
        strong_return_rank_threshold=cfg.strong_return_rank_threshold,
        high_risk_threshold=cfg.high_risk_threshold,
    )


def rolling_jump_reversal_risk(
    closes: pd.Series,
    *,
    config: JumpReversalRiskConfig | None = None,
) -> pd.DataFrame:
    """Return rolling JRR components aligned to ``closes.index``."""

    cfg = config or JumpReversalRiskConfig()
    close = pd.to_numeric(closes, errors="coerce")
    log_return = (close / close.shift(1)).apply(
        lambda value: math.log(value)
        if value is not None and math.isfinite(value) and value > 0.0
        else math.nan
    )
    abs_return = log_return.abs()
    return_rank = abs_return.rolling(
        cfg.rank_window,
        min_periods=cfg.rank_window,
    ).apply(_rolling_rank_last, raw=False)
    sign = log_return.where(log_return.abs() > cfg.epsilon, 0.0).apply(_sign)
    strong = return_rank >= cfg.strong_return_rank_threshold
    abrupt_reversal = (
        strong
        & strong.shift(1, fill_value=False)
        & sign.ne(0.0)
        & sign.shift(1, fill_value=0.0).ne(0.0)
        & sign.ne(sign.shift(1))
    )
    valid_count = log_return.notna().astype(float).rolling(cfg.window).sum()
    no_buffer_reversal_rate = abrupt_reversal.astype(float).rolling(
        cfg.window,
        min_periods=cfg.window,
    ).mean()
    volatility = log_return.rolling(cfg.window, min_periods=cfg.window).std()
    volatility_rank = volatility.rolling(
        cfg.rank_window,
        min_periods=cfg.rank_window,
    ).apply(_rolling_rank_last, raw=False)
    vol_of_vol = volatility.rolling(cfg.window, min_periods=cfg.window).std()
    vol_of_vol_rank = vol_of_vol.rolling(
        cfg.rank_window,
        min_periods=cfg.rank_window,
    ).apply(_rolling_rank_last, raw=False)
    risk_multiplier = (
        (0.50 + 0.50 * volatility_rank.clip(0.0, 1.0))
        * (0.50 + 0.50 * vol_of_vol_rank.clip(0.0, 1.0))
    )
    score = (no_buffer_reversal_rate * risk_multiplier).clip(0.0, 1.0)
    regime = pd.Series(JRR_INSUFFICIENT, index=close.index, dtype=object)
    sufficient = score.notna() & (valid_count >= cfg.window)
    regime.loc[sufficient & (score >= cfg.high_risk_threshold)] = JRR_HIGH_RISK
    regime.loc[sufficient & (score < cfg.high_risk_threshold)] = JRR_NORMAL
    return pd.DataFrame(
        {
            "score": score,
            "no_buffer_reversal_rate": no_buffer_reversal_rate,
            "volatility_rank": volatility_rank,
            "vol_of_vol_rank": vol_of_vol_rank,
            "return_rank": return_rank,
            "abrupt_reversal": abrupt_reversal,
            "valid_bar_count": valid_count,
            "regime": regime,
        },
        index=close.index,
    )


def _rolling_rank_last(values: pd.Series) -> float:
    clean = pd.Series(values).dropna()
    if clean.empty:
        return math.nan
    return float(clean.rank(pct=True).iloc[-1])


def _sign(value: float) -> float:
    if not math.isfinite(float(value)) or abs(float(value)) <= 0.0:
        return 0.0
    return 1.0 if float(value) > 0.0 else -1.0


def _insufficient_result(
    config: JumpReversalRiskConfig,
    *,
    valid_bar_count: int,
) -> JumpReversalRiskResult:
    return JumpReversalRiskResult(
        score=None,
        no_buffer_reversal_rate=None,
        volatility_rank=None,
        vol_of_vol_rank=None,
        latest_return_rank=None,
        latest_abrupt_reversal=False,
        regime=JRR_INSUFFICIENT,
        valid_bar_count=valid_bar_count,
        window=config.window,
        rank_window=config.rank_window,
        strong_return_rank_threshold=config.strong_return_rank_threshold,
        high_risk_threshold=config.high_risk_threshold,
    )
