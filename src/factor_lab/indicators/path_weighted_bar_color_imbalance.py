"""Path-weighted Bar Color Imbalance (PWBCI).

PWBCI keeps BCI's up/down bar-count interpretation, then scales the imbalance
by the recent absolute path percentile. It is useful when plain BCI flags many
same-color bars but those bars have too little movement intensity to matter.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

PWBCI_DIRECTION_BASIS_CLOSE_TO_CLOSE = "close_to_close"
PWBCI_TREND_UP = "trend_up"
PWBCI_TREND_DOWN = "trend_down"
PWBCI_BALANCED = "balanced"
PWBCI_INSUFFICIENT = "insufficient"


@dataclass(frozen=True, slots=True)
class PathWeightedBarColorImbalanceConfig:
    """Configuration for Path-weighted Bar Color Imbalance."""

    window: int = 20
    path_rank_window: int = 252
    lower_threshold: float = -0.55
    upper_threshold: float = 0.55
    epsilon: float = 0.0
    direction_basis: str = PWBCI_DIRECTION_BASIS_CLOSE_TO_CLOSE

    def __post_init__(self) -> None:
        if self.window < 2:
            raise ValueError("PWBCI window must be >= 2")
        if self.path_rank_window < 2:
            raise ValueError("PWBCI path_rank_window must be >= 2")
        if self.lower_threshold >= self.upper_threshold:
            raise ValueError("PWBCI lower_threshold must be below upper_threshold")
        if not -1.0 <= self.lower_threshold <= 1.0:
            raise ValueError("PWBCI lower_threshold must be in [-1, 1]")
        if not -1.0 <= self.upper_threshold <= 1.0:
            raise ValueError("PWBCI upper_threshold must be in [-1, 1]")
        if self.epsilon < 0.0 or not math.isfinite(self.epsilon):
            raise ValueError("PWBCI epsilon must be a finite value >= 0")
        if self.direction_basis != PWBCI_DIRECTION_BASIS_CLOSE_TO_CLOSE:
            raise ValueError(
                "PWBCI currently supports only close_to_close direction_basis"
            )


@dataclass(frozen=True, slots=True)
class PathWeightedBarColorImbalanceResult:
    """Computed PWBCI result for one ordered price series."""

    score: float | None
    imbalance: float | None
    path_abs_return: float | None
    path_rank: float | None
    up_share: float | None
    down_share: float | None
    regime: str
    valid_bar_count: int
    window: int
    path_rank_window: int
    lower_threshold: float
    upper_threshold: float
    direction_basis: str = PWBCI_DIRECTION_BASIS_CLOSE_TO_CLOSE

    def to_dict(self) -> dict[str, float | int | str | None]:
        return {
            "score": self.score,
            "imbalance": self.imbalance,
            "path_abs_return": self.path_abs_return,
            "path_rank": self.path_rank,
            "up_share": self.up_share,
            "down_share": self.down_share,
            "regime": self.regime,
            "valid_bar_count": self.valid_bar_count,
            "window": self.window,
            "path_rank_window": self.path_rank_window,
            "lower_threshold": self.lower_threshold,
            "upper_threshold": self.upper_threshold,
            "direction_basis": self.direction_basis,
        }


def compute_path_weighted_bar_color_imbalance(
    closes: Sequence[object],
    *,
    config: PathWeightedBarColorImbalanceConfig | None = None,
) -> PathWeightedBarColorImbalanceResult:
    """Compute the latest PWBCI value from an ordered close-price sequence."""

    cfg = config or PathWeightedBarColorImbalanceConfig()
    frame = rolling_path_weighted_bar_color_imbalance(
        pd.Series(list(closes), dtype="object"),
        config=cfg,
    )
    if frame.empty:
        return _insufficient_result(cfg, valid_bar_count=0)
    latest = frame.iloc[-1]
    valid_bar_count = int(latest["valid_bar_count"]) if pd.notna(latest["valid_bar_count"]) else 0
    if pd.isna(latest["score"]):
        return _insufficient_result(cfg, valid_bar_count=valid_bar_count)
    return PathWeightedBarColorImbalanceResult(
        score=float(latest["score"]),
        imbalance=float(latest["imbalance"]),
        path_abs_return=float(latest["path_abs_return"]),
        path_rank=float(latest["path_rank"]),
        up_share=float(latest["up_share"]),
        down_share=float(latest["down_share"]),
        regime=str(latest["regime"]),
        valid_bar_count=valid_bar_count,
        window=cfg.window,
        path_rank_window=cfg.path_rank_window,
        lower_threshold=cfg.lower_threshold,
        upper_threshold=cfg.upper_threshold,
    )


def rolling_path_weighted_bar_color_imbalance(
    closes: pd.Series,
    *,
    config: PathWeightedBarColorImbalanceConfig | None = None,
) -> pd.DataFrame:
    """Return rolling PWBCI components aligned to ``closes.index``."""

    cfg = config or PathWeightedBarColorImbalanceConfig()
    close = pd.to_numeric(closes, errors="coerce")
    log_return = (close / close.shift(1)).apply(
        lambda value: math.log(value)
        if value is not None and math.isfinite(value) and value > 0.0
        else math.nan
    )
    valid_count = log_return.notna().astype(float).rolling(cfg.window).sum()
    up = (log_return > cfg.epsilon).astype(float)
    down = (log_return < -cfg.epsilon).astype(float)
    up_share = up.rolling(cfg.window).sum() / valid_count
    down_share = down.rolling(cfg.window).sum() / valid_count
    imbalance = up_share - down_share
    path_abs = log_return.abs().rolling(cfg.window).sum()
    path_rank = path_abs.rolling(
        cfg.path_rank_window,
        min_periods=cfg.path_rank_window,
    ).apply(_rolling_rank_last, raw=False)
    score = imbalance * path_rank
    regime = pd.Series(PWBCI_INSUFFICIENT, index=close.index, dtype=object)
    sufficient = score.notna() & (valid_count >= cfg.window)
    regime.loc[sufficient & (score >= cfg.upper_threshold)] = PWBCI_TREND_UP
    regime.loc[sufficient & (score <= cfg.lower_threshold)] = PWBCI_TREND_DOWN
    regime.loc[
        sufficient
        & (score > cfg.lower_threshold)
        & (score < cfg.upper_threshold)
    ] = PWBCI_BALANCED
    return pd.DataFrame(
        {
            "score": score,
            "imbalance": imbalance,
            "path_abs_return": path_abs,
            "path_rank": path_rank,
            "up_share": up_share,
            "down_share": down_share,
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


def _insufficient_result(
    config: PathWeightedBarColorImbalanceConfig,
    *,
    valid_bar_count: int,
) -> PathWeightedBarColorImbalanceResult:
    return PathWeightedBarColorImbalanceResult(
        score=None,
        imbalance=None,
        path_abs_return=None,
        path_rank=None,
        up_share=None,
        down_share=None,
        regime=PWBCI_INSUFFICIENT,
        valid_bar_count=valid_bar_count,
        window=config.window,
        path_rank_window=config.path_rank_window,
        lower_threshold=config.lower_threshold,
        upper_threshold=config.upper_threshold,
    )
