"""Directional Impulse Index (DII).

DII measures directional thrust, not bar color.  It is designed to identify
violent or persistent rises/falls that BCI can miss when up/down bar counts are
not extreme but net displacement is large.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

DII_DIRECTION_BASIS_CLOSE_TO_CLOSE = "close_to_close"
DII_STRONG_UP = "strong_up"
DII_STRONG_DOWN = "strong_down"
DII_BALANCED = "balanced"
DII_INSUFFICIENT = "insufficient"


@dataclass(frozen=True, slots=True)
class DirectionalImpulseConfig:
    """Configuration for Directional Impulse Index."""

    window: int = 80
    strong_up_threshold: float = 1.25
    strong_down_threshold: float = -1.25
    epsilon: float = 1e-12
    direction_basis: str = DII_DIRECTION_BASIS_CLOSE_TO_CLOSE

    def __post_init__(self) -> None:
        if self.window < 2:
            raise ValueError("DII window must be >= 2")
        if self.strong_down_threshold >= self.strong_up_threshold:
            raise ValueError("DII down threshold must be below up threshold")
        if self.epsilon <= 0.0 or not math.isfinite(self.epsilon):
            raise ValueError("DII epsilon must be a finite positive value")
        if self.direction_basis != DII_DIRECTION_BASIS_CLOSE_TO_CLOSE:
            raise ValueError(
                "DII currently supports only close_to_close direction_basis"
            )


@dataclass(frozen=True, slots=True)
class DirectionalImpulseResult:
    """Computed DII result for one ordered price series."""

    score: float | None
    net_log_return: float | None
    path_abs_return: float | None
    energy: float | None
    efficiency: float | None
    impulse: float | None
    regime: str
    valid_bar_count: int
    window: int
    strong_up_threshold: float
    strong_down_threshold: float
    direction_basis: str = DII_DIRECTION_BASIS_CLOSE_TO_CLOSE

    def to_dict(self) -> dict[str, float | int | str | None]:
        return {
            "score": self.score,
            "net_log_return": self.net_log_return,
            "path_abs_return": self.path_abs_return,
            "energy": self.energy,
            "efficiency": self.efficiency,
            "impulse": self.impulse,
            "regime": self.regime,
            "valid_bar_count": self.valid_bar_count,
            "window": self.window,
            "strong_up_threshold": self.strong_up_threshold,
            "strong_down_threshold": self.strong_down_threshold,
            "direction_basis": self.direction_basis,
        }


def compute_directional_impulse(
    closes: Sequence[object],
    *,
    config: DirectionalImpulseConfig | None = None,
) -> DirectionalImpulseResult:
    """Compute DII from the latest ``window`` close-to-close returns."""

    cfg = config or DirectionalImpulseConfig()
    selected = list(closes[-(cfg.window + 1) :])
    returns: list[float] = []
    for previous_raw, current_raw in zip(selected, selected[1:], strict=False):
        previous_close = _finite_positive_float(previous_raw)
        current_close = _finite_positive_float(current_raw)
        if previous_close is None or current_close is None:
            continue
        returns.append(math.log(current_close / previous_close))
    return _build_result(returns=returns, config=cfg)


def rolling_directional_impulse(
    closes: pd.Series,
    *,
    config: DirectionalImpulseConfig | None = None,
) -> pd.DataFrame:
    """Return rolling DII components aligned to ``closes.index``."""

    cfg = config or DirectionalImpulseConfig()
    close = pd.to_numeric(closes, errors="coerce")
    log_return = (close / close.shift(1)).apply(
        lambda value: math.log(value)
        if value is not None and math.isfinite(value) and value > 0.0
        else math.nan
    )
    valid = log_return.notna().astype(float)
    valid_count = valid.rolling(cfg.window).sum()
    net = log_return.rolling(cfg.window).sum()
    path_abs = log_return.abs().rolling(cfg.window).sum()
    energy = (log_return * log_return).rolling(cfg.window).sum().apply(math.sqrt)
    impulse = net / energy.where(energy > cfg.epsilon)
    efficiency = net / path_abs.where(path_abs > cfg.epsilon)
    score = impulse * (0.5 + 0.5 * efficiency.abs().clip(0.0, 1.0))
    regime = pd.Series(DII_INSUFFICIENT, index=close.index, dtype=object)
    sufficient = valid_count >= cfg.window
    regime.loc[sufficient & (score >= cfg.strong_up_threshold)] = DII_STRONG_UP
    regime.loc[sufficient & (score <= cfg.strong_down_threshold)] = DII_STRONG_DOWN
    regime.loc[
        sufficient
        & (score > cfg.strong_down_threshold)
        & (score < cfg.strong_up_threshold)
    ] = DII_BALANCED
    return pd.DataFrame(
        {
            "score": score,
            "net_log_return": net,
            "path_abs_return": path_abs,
            "energy": energy,
            "efficiency": efficiency,
            "impulse": impulse,
            "valid_bar_count": valid_count,
            "regime": regime,
        },
        index=close.index,
    )


def rolling_multi_window_directional_impulse(
    closes: pd.Series,
    *,
    windows: Sequence[int] = (40, 80, 120),
    strong_up_threshold: float = 1.25,
    strong_down_threshold: float = -1.25,
) -> pd.DataFrame:
    """Compute DII for multiple windows and keep the strongest absolute score."""

    frames = {}
    for window in windows:
        cfg = DirectionalImpulseConfig(
            window=window,
            strong_up_threshold=strong_up_threshold,
            strong_down_threshold=strong_down_threshold,
        )
        frames[window] = rolling_directional_impulse(closes, config=cfg)
    score_frame = pd.DataFrame(
        {window: frame["score"] for window, frame in frames.items()},
        index=pd.to_numeric(closes, errors="coerce").index,
    )
    has_score = score_frame.notna().any(axis=1)
    selected_window = pd.Series(math.nan, index=score_frame.index)
    selected_window.loc[has_score] = score_frame.loc[has_score].abs().idxmax(axis=1)
    selected_score = pd.Series(math.nan, index=score_frame.index)
    for window in windows:
        selected_score.loc[selected_window == window] = score_frame.loc[
            selected_window == window,
            window,
        ]
    regime = pd.Series(DII_INSUFFICIENT, index=score_frame.index, dtype=object)
    known = selected_score.notna()
    regime.loc[known & (selected_score >= strong_up_threshold)] = DII_STRONG_UP
    regime.loc[known & (selected_score <= strong_down_threshold)] = DII_STRONG_DOWN
    regime.loc[
        known
        & (selected_score > strong_down_threshold)
        & (selected_score < strong_up_threshold)
    ] = DII_BALANCED
    return pd.DataFrame(
        {
            "score": selected_score,
            "selected_window": selected_window,
            "regime": regime,
        },
        index=score_frame.index,
    )


def _build_result(
    *,
    returns: Sequence[float],
    config: DirectionalImpulseConfig,
) -> DirectionalImpulseResult:
    if len(returns) < config.window:
        return DirectionalImpulseResult(
            score=None,
            net_log_return=None,
            path_abs_return=None,
            energy=None,
            efficiency=None,
            impulse=None,
            regime=DII_INSUFFICIENT,
            valid_bar_count=len(returns),
            window=config.window,
            strong_up_threshold=config.strong_up_threshold,
            strong_down_threshold=config.strong_down_threshold,
            direction_basis=config.direction_basis,
        )
    net = sum(returns)
    path_abs = sum(abs(value) for value in returns)
    energy = math.sqrt(sum(value * value for value in returns))
    impulse = net / energy if energy > config.epsilon else 0.0
    efficiency = net / path_abs if path_abs > config.epsilon else 0.0
    score = impulse * (0.5 + 0.5 * min(abs(efficiency), 1.0))
    return DirectionalImpulseResult(
        score=score,
        net_log_return=net,
        path_abs_return=path_abs,
        energy=energy,
        efficiency=efficiency,
        impulse=impulse,
        regime=_classify_score(score, config=config),
        valid_bar_count=len(returns),
        window=config.window,
        strong_up_threshold=config.strong_up_threshold,
        strong_down_threshold=config.strong_down_threshold,
        direction_basis=config.direction_basis,
    )


def _classify_score(score: float, *, config: DirectionalImpulseConfig) -> str:
    if score >= config.strong_up_threshold:
        return DII_STRONG_UP
    if score <= config.strong_down_threshold:
        return DII_STRONG_DOWN
    return DII_BALANCED


def _finite_positive_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(str(value))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or parsed <= 0.0:
        return None
    return parsed
