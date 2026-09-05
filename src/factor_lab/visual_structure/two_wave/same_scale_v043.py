"""v0.4.3 confirmation-kernel ablation for same-scale two-wave research.

Only pivot confirmation changes from v0.4.2: a turn is confirmed after an
opposite running extremum matures by ``min_leg`` bar intervals. Qualification,
direction and exclusive publishing are reused unchanged. No outcome data.
"""
from __future__ import annotations

import copy
import math
from dataclasses import asdict, dataclass

from .engine import Engine
from .models import Config, stable_id
from .same_scale_v04 import ExclusiveLedger, direction_versions, evaluate_pair

SCHEMA = "two_wave_same_scale@0.4.3-confirmation-ablation"


@dataclass(frozen=True)
class MaturityConfig:
    timeframe: str = "5m_offset_0"
    max_unfinished_leg: int = 48
    min_leg: int = 4
    min_cycle: int = 12
    max_cycle: int = 48
    max_pair: int = 96
    duration_ratio: float = 2.0
    amplitude_ratio: float = 2.0
    min_leg_efficiency: float = 0.5
    max_jump_share: float = 0.5
    max_flat_share: float = 0.5
    max_observed_days: int = 3
    max_wall_days: float = 7.0
    max_confirmation_delay: int = 8
    phase_tolerance: float = 0.15
    opposite_tolerance: float = 0.05
    strong_drift: float = 0.5
    confirmation_mode: str = "opposite_extremum_min_leg_maturity"

    def __post_init__(self):
        if not isinstance(self.timeframe, str) or not self.timeframe:
            raise ValueError("nonempty timeframe required")
        if self.confirmation_mode != "opposite_extremum_min_leg_maturity":
            raise ValueError("confirmation_mode is frozen for this ablation")
        integer_fields = {"max_unfinished_leg", "min_leg", "min_cycle", "max_cycle", "max_pair",
                          "max_observed_days", "max_confirmation_delay"}
        for key, value in asdict(self).items():
            if key in {"timeframe", "confirmation_mode"}:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{key} must be finite positive")
            if key in integer_fields and not isinstance(value, int):
                raise ValueError(f"{key} must be an integer")
        if self.min_cycle > self.max_cycle or self.min_cycle < 2 * self.min_leg:
            raise ValueError("inconsistent leg/cycle durations")
        if min(self.duration_ratio, self.amplitude_ratio) < 1 or self.max_pair < 2 * self.min_cycle:
            raise ValueError("invalid scale ratios/pair limit")
        if any(getattr(self, k) > 1 for k in ("min_leg_efficiency", "max_jump_share", "max_flat_share")):
            raise ValueError("path proportions must be <=1")
        if self.opposite_tolerance > self.phase_tolerance:
            raise ValueError("opposite tolerance must not exceed phase tolerance")

    @property
    def config_hash(self):
        return stable_id("same_scale_cfg_v043", {"schema": SCHEMA, **asdict(self)})


class TemporalMaturityEngine(Engine):
    """Causal time-scale pivot detector.

    v0.4.2's three strictly opposite adjacent close changes are removed. While
    following a high (low), the detector waits until a lower (higher) running
    extremum occurs at least ``min_leg`` bars after that extremum. Only then is
    the former extremum confirmed. Thus every usable consecutive pivot pair is
    separated by at least the same minimum leg duration used by qualification.
    """

    def __init__(self, config=None):
        self.shape_config = config or MaturityConfig()
        super().__init__(Config(timeframe=self.shape_config.timeframe))
        self.ledger = ExclusiveLedger()
        self.resets = []
        self._chain = []
        self._mode = None
        self._candidate_point = None
        self._counter_point = None
        self._boot_low = self._boot_high = None
        self._last_pivot_bar = None
        self._epoch = 0

    def _point(self, bar, kind):
        return {"kind": kind, "occurrence_bar": bar["bar_index"], "occurrence_time": bar["timestamp"],
                "price": bar["close"], "log_price": bar["log_close"]}

    def _confirm(self, point, bar, censored=False):
        p = {**point, "left_censored": censored, "confirmation_bar": bar["bar_index"],
             "confirmation_time": bar["timestamp"], "effective_information_time": bar["effective_information_time"],
             "confirmation_delay_bars": bar["bar_index"] - point["occurrence_bar"],
             "bar_end_assumed": self._bar_end_assumed, "epoch": self._epoch,
             "confirmation_mode": self.shape_config.confirmation_mode}
        p["pivot_id"] = stable_id("time_pivot_v043", [self.shape_config.config_hash, p])
        self.pivots.append(p)
        self._last_pivot_bar = point["occurrence_bar"]
        if censored:
            return
        self._chain.append(p)
        if len(self._chain) >= 5:
            r = evaluate_pair(self._chain[-5:], self.bars, self.shape_config)
            r["schema_version"] = SCHEMA
            r["confirmation_kernel"] = self.shape_config.confirmation_mode
            self.ledger.add(r)

    def _reset(self, bar):
        self.resets.append({"bar": bar["bar_index"], "time": bar["timestamp"],
                            "known_at": bar["effective_information_time"],
                            "reason": "unfinished_leg_exceeded_duration", "previous_pivot_bar": self._last_pivot_bar})
        self._epoch += 1
        self._chain = []
        self._mode = None
        self._last_pivot_bar = None
        self._candidate_point = self._counter_point = None
        self._boot_low = self._point(bar, "low")
        self._boot_high = self._point(bar, "high")

    def _bootstrap(self, bar):
        if bar["close"] < self._boot_low["price"]:
            self._boot_low = self._point(bar, "low")
        if bar["close"] > self._boot_high["price"]:
            self._boot_high = self._point(bar, "high")
        low, high = self._boot_low, self._boot_high
        if high["occurrence_bar"] - low["occurrence_bar"] >= self.shape_config.min_leg:
            self._confirm(low, bar, True)
            self._mode = 1
            self._candidate_point = high
            self._counter_point = None
            return True
        if low["occurrence_bar"] - high["occurrence_bar"] >= self.shape_config.min_leg:
            self._confirm(high, bar, True)
            self._mode = -1
            self._candidate_point = low
            self._counter_point = None
            return True
        return False

    def update(self, supplied):
        bar, dt, available = self._normalize(supplied)
        self._availability = max(self._availability, available) if self._availability else available
        self._last_dt = dt
        self._bar_end_assumed |= bar["bar_end_assumed"]
        bar["effective_information_time"] = self._availability.isoformat()
        if supplied.get("trading_day") is not None:
            bar["trading_day"] = str(supplied["trading_day"])
        self.bars.append(bar)
        before = len(self.ledger.records)
        if self._boot_low is None:
            self._boot_low = self._point(bar, "low")
            self._boot_high = self._point(bar, "high")
            return []
        cfg = self.shape_config
        if self._last_pivot_bar is not None and bar["bar_index"] - self._last_pivot_bar > cfg.max_unfinished_leg:
            self._reset(bar)
            return []
        if self._mode is None:
            self._bootstrap(bar)
            return copy.deepcopy(self.ledger.records[before:])

        if self._mode * (bar["close"] - self._candidate_point["price"]) > 0:
            self._candidate_point = self._point(bar, "high" if self._mode > 0 else "low")
            self._counter_point = None
            return copy.deepcopy(self.ledger.records[before:])

        if self._mode * (bar["close"] - self._candidate_point["price"]) < 0:
            kind = "low" if self._mode > 0 else "high"
            if self._counter_point is None or self._mode * (bar["close"] - self._counter_point["price"]) < 0:
                self._counter_point = self._point(bar, kind)

        if self._counter_point is not None and (
            self._counter_point["occurrence_bar"] - self._candidate_point["occurrence_bar"] >= cfg.min_leg
        ):
            old = self._candidate_point
            new = self._counter_point
            self._confirm(old, bar)
            self._mode *= -1
            self._candidate_point = new
            self._counter_point = None
        return copy.deepcopy(self.ledger.records[before:])


def compare_direction_only(steps, spans, cfg=None):
    """Convenience hook proving direction logic is literally the frozen D1 helper."""
    return direction_versions(steps, spans, cfg or MaturityConfig())
