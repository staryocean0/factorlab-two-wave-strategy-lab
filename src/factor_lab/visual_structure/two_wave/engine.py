"""Causal, append-only research engine.  It emits no position or execution signal."""

from __future__ import annotations

import copy
import math
from collections.abc import Iterable
from datetime import UTC, datetime

from .geometry import fit_geometry
from .models import SCHEMA_VERSION, Config, stable_id


def _time(value: object, name: str) -> datetime:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an ISO datetime") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return dt.astimezone(UTC)


class Engine:
    """One fixed-scale stream; confirmed lists are never rewritten by update().

    The first observed extremum is explicitly left censored and excluded from
    cycles.  Each subsequent alternating triple forms one full cycle, and each
    consecutive quintuple forms a two-cycle structure, preserving both phases.
    """

    def __init__(self, config: Config | None = None):
        self._config = config or Config()
        self.bars: list[dict] = []
        self.pivots: list[dict] = []
        self.cycles: list[dict] = []
        self.structures: list[dict] = []
        self.events: list[dict] = []
        self._usable: list[dict] = []
        self._cycles_by_ends: dict[tuple[str, str], dict] = {}
        self._states: dict[str, dict] = {}
        self._active: dict[str, dict] = {}
        self._direction: str | None = None
        self._candidate: dict | None = None
        self._initial_low: dict | None = None
        self._initial_high: dict | None = None
        self._last_dt: datetime | None = None
        self._availability: datetime | None = None
        self._bar_end_assumed = False

    @property
    def config(self) -> Config:
        return self._config

    def _metadata(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "instrument": self.config.instrument,
            "timeframe": self.config.timeframe,
            "scale_id": self.config.scale_id,
            "config_hash": self.config.config_hash,
        }

    def _known(self) -> dict:
        return {
            "information_available_time": self._availability.isoformat() if self._availability else None,
            "bar_end_assumed": self._bar_end_assumed,
        }

    @staticmethod
    def _extreme(bar: dict, kind: str) -> dict:
        return {
            "kind": kind,
            "occurrence_bar": bar["bar_index"],
            "occurrence_time": bar["timestamp"],
            "price": bar["close"],
            "log_price": bar["log_close"],
        }

    def _event(self, kind: str, bar: dict, **fields: object) -> dict:
        event = {
            **self._metadata(),
            **self._known(),
            "type": kind,
            "occurrence_bar": bar["bar_index"],
            "occurrence_time": bar["timestamp"],
            "confirmation_bar": bar["bar_index"],
            "confirmation_time": bar["timestamp"],
            "effective_information_time": self._availability.isoformat(),
            **fields,
        }
        event["event_id"] = stable_id("event", [self.config.config_hash, len(self.events), event])
        self.events.append(event)
        return event

    def _normalize(self, supplied: dict) -> tuple[dict, datetime, datetime]:
        dt = _time(supplied["timestamp"], "timestamp")
        if self._last_dt is not None and dt <= self._last_dt:
            raise ValueError("bar timestamps must be strictly increasing; duplicate or unordered row")
        prices = {}
        for field in ("open", "high", "low", "close"):
            raw = supplied[field]
            if isinstance(raw, bool):
                raise ValueError(f"{field} must be a positive finite price")
            try:
                value = float(raw)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"{field} must be a positive finite price") from exc
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{field} must be a positive finite price")
            prices[field] = value
        if prices["low"] > min(prices.values()) or prices["high"] < max(prices.values()):
            raise ValueError("OHLC range is inconsistent")
        availability = _time(supplied["available_at"], "available_at") if supplied.get("available_at") is not None else dt
        if availability < dt:
            raise ValueError("available_at cannot precede bar-end timestamp")
        bar = {
            "bar_index": len(self.bars),
            "timestamp": dt.isoformat(),
            **prices,
            "log_close": math.log(prices["close"]),
            "available_at": availability.isoformat(),
            "bar_end_assumed": supplied.get("available_at") is None,
        }
        if "volume" in supplied and supplied["volume"] is not None:
            volume = float(supplied["volume"])
            if not math.isfinite(volume) or volume < 0:
                raise ValueError("volume must be finite and nonnegative when provided")
            bar["volume"] = volume
        return bar, dt, availability

    def update(self, supplied: dict) -> list[dict]:
        """Consume one bar and return copies of its newly confirmed events."""
        bar, dt, availability = self._normalize(supplied)
        event_offset = len(self.events)
        self.bars.append(bar)
        self._last_dt = dt
        self._availability = max(self._availability, availability) if self._availability else availability
        self._bar_end_assumed = self._bar_end_assumed or bar["bar_end_assumed"]

        # Previously effective frozen channels see the new close first.
        for structure in list(self._active.values()):
            self._check_breakout(structure, bar, at_confirmation=False)

        x, threshold = bar["log_close"], self.config.reversal_log
        if self._initial_low is None:
            self._initial_low = self._extreme(bar, "low")
            self._initial_high = self._extreme(bar, "high")
            return []
        if self._direction is None:
            if x < self._initial_low["log_price"]:
                self._initial_low = self._extreme(bar, "low")
            if x > self._initial_high["log_price"]:
                self._initial_high = self._extreme(bar, "high")
            if x - self._initial_low["log_price"] >= threshold:
                self._confirm_pivot(self._initial_low, bar, left_censored=True)
                self._direction = "up"
                self._candidate = self._extreme(bar, "high")
            elif self._initial_high["log_price"] - x >= threshold:
                self._confirm_pivot(self._initial_high, bar, left_censored=True)
                self._direction = "down"
                self._candidate = self._extreme(bar, "low")
        elif self._direction == "up":
            if x > self._candidate["log_price"]:
                self._candidate = self._extreme(bar, "high")
            elif self._candidate["log_price"] - x >= threshold:
                self._confirm_pivot(self._candidate, bar)
                self._direction = "down"
                self._candidate = self._extreme(bar, "low")
        else:
            if x < self._candidate["log_price"]:
                self._candidate = self._extreme(bar, "low")
            elif x - self._candidate["log_price"] >= threshold:
                self._confirm_pivot(self._candidate, bar)
                self._direction = "up"
                self._candidate = self._extreme(bar, "high")
        return copy.deepcopy(self.events[event_offset:])

    def _confirm_pivot(self, candidate: dict, bar: dict, left_censored: bool = False) -> None:
        pivot = {
            **self._metadata(),
            **candidate,
            **self._known(),
            "left_censored": left_censored,
            "confirmation_bar": bar["bar_index"],
            "confirmation_time": bar["timestamp"],
            "confirmation_delay_bars": bar["bar_index"] - candidate["occurrence_bar"],
        }
        pivot["pivot_id"] = stable_id("pivot", [self.config.config_hash, candidate, bar["timestamp"]])
        self.pivots.append(pivot)
        self._event(
            "pivot_confirmed",
            bar,
            pivot_id=pivot["pivot_id"],
            left_censored=left_censored,
            occurrence_bar=pivot["occurrence_bar"],
            occurrence_time=pivot["occurrence_time"],
        )
        if left_censored:
            return
        self._usable.append(pivot)
        if len(self._usable) >= 3:
            points = self._usable[-3:]
            logs = [p["log_price"] for p in points]
            prices = [p["price"] for p in points]
            cycle = {
                **self._metadata(),
                **self._known(),
                "phase": points[0]["kind"],
                "pivot_ids": [p["pivot_id"] for p in points],
                "start_bar": points[0]["occurrence_bar"],
                "end_bar": points[-1]["occurrence_bar"],
                "start_time": points[0]["occurrence_time"],
                "end_time": points[-1]["occurrence_time"],
                "occurrence_bar": points[-1]["occurrence_bar"],
                "occurrence_time": points[-1]["occurrence_time"],
                "confirmation_bar": bar["bar_index"],
                "confirmation_time": bar["timestamp"],
                "amplitude_log": max(logs) - min(logs),
                "amplitude_price": max(prices) - min(prices),
                "duration_bars": points[-1]["occurrence_bar"] - points[0]["occurrence_bar"],
                "confirmation_delay_bars": bar["bar_index"] - points[-1]["occurrence_bar"],
            }
            cycle["cycle_id"] = stable_id("cycle", cycle["pivot_ids"])
            self.cycles.append(cycle)
            self._cycles_by_ends[(points[0]["pivot_id"], points[-1]["pivot_id"])] = cycle
            self._event(
                "cycle_confirmed",
                bar,
                cycle_id=cycle["cycle_id"],
                phase=cycle["phase"],
                occurrence_bar=cycle["end_bar"],
                occurrence_time=cycle["end_time"],
            )
            for structure in list(self._active.values()):
                if structure["phase"] == cycle["phase"] and cycle["end_bar"] > structure["end_bar"]:
                    state = self._states[structure["structure_id"]]
                    state["cycle_count"] += 1
                    state["last_cycle_id"] = cycle["cycle_id"]
                    state["last_cycle_confirmation_bar"] = bar["bar_index"]
                    self._event(
                        "structure_cycle_confirmed",
                        bar,
                        structure_id=structure["structure_id"],
                        cycle_id=cycle["cycle_id"],
                        cycle_count=state["cycle_count"],
                        occurrence_bar=cycle["end_bar"],
                        occurrence_time=cycle["end_time"],
                    )
        if len(self._usable) >= 5:
            self._create_structure(self._usable[-5:], bar)

    def _create_structure(self, points: list[dict], bar: dict) -> None:
        geometry = fit_geometry(points, self.bars, self.config)
        cycle_ids = [self._cycles_by_ends[(points[i]["pivot_id"], points[i + 2]["pivot_id"])]["cycle_id"] for i in (0, 2)]
        structure = {
            **self._metadata(),
            **self._known(),
            "phase": points[0]["kind"],
            "pivot_ids": [p["pivot_id"] for p in points],
            "cycle_ids": cycle_ids,
            "start_bar": points[0]["occurrence_bar"],
            "end_bar": points[-1]["occurrence_bar"],
            "start_time": points[0]["occurrence_time"],
            "end_time": points[-1]["occurrence_time"],
            "occurrence_bar": points[-1]["occurrence_bar"],
            "occurrence_time": points[-1]["occurrence_time"],
            "confirmation_bar": bar["bar_index"],
            "confirmation_time": bar["timestamp"],
            "classification_time": bar["timestamp"],
            "classification_available_time": self._availability.isoformat(),
            "effective_information_time": self._availability.isoformat(),
            "confirmation_delay_bars": bar["bar_index"] - points[-1]["occurrence_bar"],
            "version": 1,
            "effective_from_bar": bar["bar_index"],
            "effective_from_time": bar["timestamp"],
            "initial_cycle_count": 2,
            "geometry": geometry,
            "classification": geometry["classification"],
            "attributes": list(geometry["attributes"]),
            "authority_status": "research_only_morphology_not_accepted",
            "parent_definition": "local_envelope_of_two_same_scale_cycles",
        }
        structure["structure_id"] = stable_id("structure", [self.config.config_hash, structure["pivot_ids"]])
        self.structures.append(structure)
        key = structure["structure_id"]
        self._states[key] = {
            "cycle_count": 2,
            "geometry_alive": geometry["valid"],
            "first_breakout_event_id": None,
            "first_breakout_bar": None,
            "last_cycle_id": cycle_ids[-1],
            "last_cycle_confirmation_bar": bar["bar_index"],
            "end_reason": None if geometry["valid"] else "invalid_geometry",
            "confirmation_bar": bar["bar_index"],
        }
        self._event(
            "structure_confirmed",
            bar,
            structure_id=key,
            classification=structure["classification"],
            cycle_count=2,
            occurrence_bar=structure["end_bar"],
            occurrence_time=structure["end_time"],
        )
        if geometry["valid"]:
            self._active[key] = structure
            self._check_breakout(structure, bar, at_confirmation=True)

    def _check_breakout(self, structure: dict, bar: dict, at_confirmation: bool) -> None:
        geometry = structure["geometry"]
        elapsed = bar["bar_index"] - geometry["origin_bar"]
        lower = geometry["lower_offset"] + geometry["b"] * elapsed
        upper = geometry["upper_offset"] + geometry["b"] * elapsed
        x = bar["log_close"]
        direction = "up" if x > upper + 1e-12 else ("down" if x < lower - 1e-12 else None)
        if direction is None:
            return
        state = self._states[structure["structure_id"]]
        trend = {"uptrend": "up", "downtrend": "down"}.get(structure["classification"])
        relation = "undirected" if trend is None else ("same_direction" if trend == direction else "opposite_direction")
        previous = self.bars[-2]["log_close"] if len(self.bars) > 1 else x
        boundary_overtook_price = (direction == "down" and geometry["b"] > 0 and x >= previous) or (
            direction == "up" and geometry["b"] < 0 and x <= previous
        )
        event = self._event(
            "structure_breakout",
            bar,
            structure_id=structure["structure_id"],
            direction=direction,
            directional_relation=relation,
            cycle_count=state["cycle_count"],
            confirmation_already_outside=at_confirmation,
            lower_log=lower,
            upper_log=upper,
            close_log=x,
            trigger=f"close_{'above_upper' if direction == 'up' else 'below_lower'}",
            boundary_overtook_price=boundary_overtook_price,
            event_scope="first_geometry_breakout_only",
            has_position_or_exit_authority=False,
        )
        state.update(
            {
                "geometry_alive": False,
                "first_breakout_event_id": event["event_id"],
                "first_breakout_bar": bar["bar_index"],
                "end_reason": "first_geometry_breakout",
            }
        )
        self._active.pop(structure["structure_id"], None)

    def snapshot(self) -> dict:
        """A current-state copy; observation-end censoring never emits a fake end."""
        state_copies = copy.deepcopy(self._states)
        current = len(self.bars) - 1
        for state in state_copies.values():
            last = state["first_breakout_bar"] if state["first_breakout_bar"] is not None else current
            state["age_bars_since_confirmation"] = max(0, last - state["confirmation_bar"])
            state["right_censored_at_observation_end"] = state["geometry_alive"]
        return {
            "bar_index": current,
            "timestamp": self.bars[-1]["timestamp"] if self.bars else None,
            **self._known(),
            "direction": self._direction,
            "candidate_pivot": copy.deepcopy(self._candidate),
            "initial_low": copy.deepcopy(self._initial_low) if self._direction is None else None,
            "initial_high": copy.deepcopy(self._initial_high) if self._direction is None else None,
            "warmup_status": (
                "two_cycles_available"
                if self.structures
                else "insufficient_confirmed_reversals"
                if self._direction
                else "no_threshold_move_yet"
            ),
            "structure_states": state_copies,
        }

    def export(self) -> dict:
        return {
            **self._metadata(),
            "config": self.config.to_dict(),
            "bars": copy.deepcopy(self.bars),
            "pivots": copy.deepcopy(self.pivots),
            "cycles": copy.deepcopy(self.cycles),
            "structures": copy.deepcopy(self.structures),
            "events": copy.deepcopy(self.events),
            "state": self.snapshot(),
            "authority_status": "research_only_morphology_not_accepted",
        }


def run_bars(bars: Iterable[dict], config: Config | None = None) -> Engine:
    """Batch replay is exactly the same update loop used for live prefixes."""
    engine = Engine(config)
    for bar in bars:
        engine.update(bar)
    return engine
