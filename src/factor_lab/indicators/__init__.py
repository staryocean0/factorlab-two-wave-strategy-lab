"""Market/regime indicator utilities.

Indicators in this package are diagnostic metrics.  They are not automatically
FactorSpec, CandidateFactor, or trading-signal assets unless a caller explicitly
wraps and validates them through the normal governance flow.
"""

from __future__ import annotations

from factor_lab.indicators.bar_direction_continuity import (
    BDCI_DIRECTION_BASIS_CLOSE_TO_CLOSE,
    BDCI_INSUFFICIENT,
    BDCI_OBSERVE,
    BDCI_OSCILLATION_FRIENDLY,
    BDCI_TREND_FRIENDLY,
    BarDirectionContinuityConfig,
    BarDirectionContinuityResult,
    classify_bdci_score,
    compute_bar_direction_continuity,
    compute_bar_direction_continuity_from_rows,
)

__all__ = [
    "BDCI_DIRECTION_BASIS_CLOSE_TO_CLOSE",
    "BDCI_INSUFFICIENT",
    "BDCI_OBSERVE",
    "BDCI_OSCILLATION_FRIENDLY",
    "BDCI_TREND_FRIENDLY",
    "BarDirectionContinuityConfig",
    "BarDirectionContinuityResult",
    "classify_bdci_score",
    "compute_bar_direction_continuity",
    "compute_bar_direction_continuity_from_rows",
]
