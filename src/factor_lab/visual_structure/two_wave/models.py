"""Frozen, explicit assumptions for the research-only two-wave recognizer."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass

SCHEMA_VERSION = "two_wave_research@0.1.0"


def stable_id(prefix: str, value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return f"{prefix}_{hashlib.sha256(encoded.encode()).hexdigest()[:20]}"


@dataclass(frozen=True)
class Config:
    """Fixed ex ante parameters; these defaults are assumptions, not fitted optima."""

    instrument: str = "000852.SH"
    timeframe: str = "5m_offset_0"
    reversal_log: float = 0.01
    drift_threshold: float = 0.5
    max_fit_error: float = 0.2
    direction_tolerance: float = 0.15
    max_slope_disagreement: float = 0.75
    max_width_ratio: float = 1.6
    min_width: float = 1e-8

    def __post_init__(self) -> None:
        if not self.instrument or not self.timeframe:
            raise ValueError("instrument and timeframe must be nonempty")
        for name in (
            "reversal_log",
            "drift_threshold",
            "max_fit_error",
            "direction_tolerance",
            "max_slope_disagreement",
            "max_width_ratio",
            "min_width",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if self.max_width_ratio <= 1:
            raise ValueError("max_width_ratio must exceed one")

    @property
    def config_hash(self) -> str:
        return stable_id("cfg", {"schema_version": SCHEMA_VERSION, **asdict(self)})

    @property
    def scale_id(self) -> str:
        # Classification thresholds do not change the wave-scale identity.
        return stable_id(
            "scale",
            {
                "instrument": self.instrument,
                "timeframe": self.timeframe,
                "operator": "raw_log_close_directional_change_first_plateau",
                "reversal_log": self.reversal_log,
            },
        )

    def to_dict(self) -> dict:
        return asdict(self)
