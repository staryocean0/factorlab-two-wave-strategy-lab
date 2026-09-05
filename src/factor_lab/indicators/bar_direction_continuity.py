"""Bar Direction Continuity Index (BDCI).

BDCI measures whether a price series keeps moving in the same close-to-close
bar direction or flips direction frequently.  It is a diagnostic metric for
trend/oscillation regime suitability, not a predictive factor by itself.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

BDCI_DIRECTION_BASIS_CLOSE_TO_CLOSE = "close_to_close"
BDCI_TREND_FRIENDLY = "trend_friendly"
BDCI_OSCILLATION_FRIENDLY = "oscillation_friendly"
BDCI_OBSERVE = "observe"
BDCI_INSUFFICIENT = "insufficient"

@dataclass(frozen=True, slots=True)
class BarDirectionContinuityConfig:
    """Configuration for BDCI.

    Thresholds are intentionally configurable: the first production default uses
    60/40, but future research can tune them by asset class, bar cycle, or noise
    regime without changing the formula.
    """

    window: int | None = None
    epsilon: float = 0.0
    trend_threshold: float = 60.0
    oscillation_threshold: float = 40.0
    unit_size: int = 100
    direction_basis: str = BDCI_DIRECTION_BASIS_CLOSE_TO_CLOSE

    def __post_init__(self) -> None:
        if self.window is not None and self.window < 2:
            raise ValueError("BDCI window must be >= 2 when provided")
        if self.epsilon < 0.0 or not math.isfinite(self.epsilon):
            raise ValueError("BDCI epsilon must be a finite value >= 0")
        if self.unit_size <= 0:
            raise ValueError("BDCI unit_size must be > 0")
        if not 0.0 <= self.oscillation_threshold <= 100.0:
            raise ValueError("BDCI oscillation_threshold must be in [0, 100]")
        if not 0.0 <= self.trend_threshold <= 100.0:
            raise ValueError("BDCI trend_threshold must be in [0, 100]")
        if self.oscillation_threshold > self.trend_threshold:
            raise ValueError(
                "BDCI oscillation_threshold must be <= trend_threshold"
            )
        if self.direction_basis != BDCI_DIRECTION_BASIS_CLOSE_TO_CLOSE:
            raise ValueError(
                "BDCI currently supports only close_to_close direction_basis"
            )


@dataclass(frozen=True, slots=True)
class BarDirectionContinuityResult:
    """Computed BDCI result for one ordered price series."""

    score: float | None
    regime: str
    switch_count: int
    opportunity_count: int
    switch_rate: float | None
    switches_per_unit: float | None
    valid_direction_count: int
    neutral_direction_count: int
    invalid_pair_count: int
    z_score: float | None
    trend_threshold: float
    oscillation_threshold: float
    unit_size: int
    direction_basis: str = BDCI_DIRECTION_BASIS_CLOSE_TO_CLOSE

    def to_dict(self) -> dict[str, float | int | str | None]:
        """Return a stable JSON-friendly representation."""

        return {
            "score": self.score,
            "regime": self.regime,
            "switch_count": self.switch_count,
            "opportunity_count": self.opportunity_count,
            "switch_rate": self.switch_rate,
            "switches_per_unit": self.switches_per_unit,
            "valid_direction_count": self.valid_direction_count,
            "neutral_direction_count": self.neutral_direction_count,
            "invalid_pair_count": self.invalid_pair_count,
            "z_score": self.z_score,
            "trend_threshold": self.trend_threshold,
            "oscillation_threshold": self.oscillation_threshold,
            "unit_size": self.unit_size,
            "direction_basis": self.direction_basis,
        }


def compute_bar_direction_continuity(
    closes: Sequence[object],
    *,
    config: BarDirectionContinuityConfig | None = None,
) -> BarDirectionContinuityResult:
    """Compute BDCI from an ordered close-price sequence.

    The default direction is close-to-close log return.  Candle body color
    (`close` vs `open`) is intentionally not used.
    """

    cfg = config or BarDirectionContinuityConfig()
    selected_closes = (
        list(closes[-cfg.window :]) if cfg.window is not None else list(closes)
    )
    directions: list[int] = []
    neutral_count = 0
    invalid_pair_count = 0

    for previous_raw, current_raw in zip(
        selected_closes, selected_closes[1:], strict=False
    ):
        previous_close = _finite_positive_float(previous_raw)
        current_close = _finite_positive_float(current_raw)
        if previous_close is None or current_close is None:
            invalid_pair_count += 1
            continue
        log_return = math.log(current_close / previous_close)
        if log_return > cfg.epsilon:
            directions.append(1)
        elif log_return < -cfg.epsilon:
            directions.append(-1)
        else:
            neutral_count += 1

    return _build_result(
        directions,
        neutral_direction_count=neutral_count,
        invalid_pair_count=invalid_pair_count,
        config=cfg,
    )


def compute_bar_direction_continuity_from_rows(
    rows: Sequence[Mapping[str, object]],
    *,
    config: BarDirectionContinuityConfig | None = None,
    close_field: str = "close",
    timestamp_field: str = "timestamp",
) -> BarDirectionContinuityResult:
    """Compute BDCI from PIT/OHLCV-like rows sorted by timestamp.

    Rows are sorted by `timestamp_field` so callers can pass ordinary dataset
    rows without pre-sorting.  Only `close_field` participates in the direction
    calculation; open/high/low fields do not affect BDCI.
    """

    ordered_rows = sorted(rows, key=lambda row: str(row.get(timestamp_field, "")))
    closes = [row.get(close_field) for row in ordered_rows]
    return compute_bar_direction_continuity(closes, config=config)


def classify_bdci_score(
    score: float | None, *, config: BarDirectionContinuityConfig | None = None
) -> str:
    """Classify a BDCI score with configurable 60/40 defaults."""

    cfg = config or BarDirectionContinuityConfig()
    if score is None:
        return BDCI_INSUFFICIENT
    if score >= cfg.trend_threshold:
        return BDCI_TREND_FRIENDLY
    if score <= cfg.oscillation_threshold:
        return BDCI_OSCILLATION_FRIENDLY
    return BDCI_OBSERVE


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


def _build_result(
    directions: Sequence[int],
    *,
    neutral_direction_count: int,
    invalid_pair_count: int,
    config: BarDirectionContinuityConfig,
) -> BarDirectionContinuityResult:
    valid_direction_count = len(directions)
    opportunity_count = max(0, valid_direction_count - 1)
    if opportunity_count == 0:
        return BarDirectionContinuityResult(
            score=None,
            regime=BDCI_INSUFFICIENT,
            switch_count=0,
            opportunity_count=0,
            switch_rate=None,
            switches_per_unit=None,
            valid_direction_count=valid_direction_count,
            neutral_direction_count=neutral_direction_count,
            invalid_pair_count=invalid_pair_count,
            z_score=None,
            trend_threshold=config.trend_threshold,
            oscillation_threshold=config.oscillation_threshold,
            unit_size=config.unit_size,
            direction_basis=config.direction_basis,
        )

    switch_count = sum(
        1
        for previous_direction, current_direction in zip(
            directions, directions[1:], strict=False
        )
        if current_direction != previous_direction
    )
    switch_rate = switch_count / opportunity_count
    score = 100.0 * (1.0 - switch_rate)
    z_score = (1.0 - 2.0 * switch_rate) * math.sqrt(opportunity_count)
    regime = classify_bdci_score(score, config=config)
    return BarDirectionContinuityResult(
        score=score,
        regime=regime,
        switch_count=switch_count,
        opportunity_count=opportunity_count,
        switch_rate=switch_rate,
        switches_per_unit=switch_rate * config.unit_size,
        valid_direction_count=valid_direction_count,
        neutral_direction_count=neutral_direction_count,
        invalid_pair_count=invalid_pair_count,
        z_score=z_score,
        trend_threshold=config.trend_threshold,
        oscillation_threshold=config.oscillation_threshold,
        unit_size=config.unit_size,
        direction_basis=config.direction_basis,
    )
