# pyright: reportAny=false, reportArgumentType=false
# pyright: reportAttributeAccessIssue=false, reportGeneralTypeIssues=false
# pyright: reportMissingTypeStubs=false
# pyright: reportReturnType=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Causal, completed-bar aggregation for the V2 market-state scale ladder.

This is deliberately a data-preparation gate, not a filter implementation.
Any future digital filter must receive only ``bar_complete`` rows through the
explicit reject policy below; unobserved or partially formed source bars never
become valid inputs by padding or by looking ahead.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, time
from typing import Final

import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.horizons import TIMEZONE, normalize_bar_panel
from factor_lab.market_state.time_scale_catalog import TimeScaleCatalog, build_time_scale_catalog_v2

CAUSAL_SCALE_LADDER_SCHEMA_ID: Final[str] = "market_state_causal_scale_ladder@1.0"
CAUSAL_SCALE_LADDER_VERSION: Final[str] = "market_state_causal_scale_ladder_v2"
REJECT_INCOMPLETE_SOURCE_BARS_POLICY: Final[str] = "reject_incomplete_source_bars"
_FREQUENCY_RANK: Final[Mapping[str, int]] = {"15m": 0, "60m": 1, "1d": 2}
_SESSION_TEMPLATES: Final[frozenset[str]] = frozenset({"full_day", "half_day"})


def _slots(*values: tuple[int, int]) -> tuple[tuple[int, int], ...]:
    return values


_SOURCE_CLOSE_SLOTS: Final[Mapping[tuple[str, str], tuple[tuple[int, int], ...]]] = {
    ("15m", "full_day"): _slots(
        (9, 45),
        (10, 0),
        (10, 15),
        (10, 30),
        (10, 45),
        (11, 0),
        (11, 15),
        (11, 30),
        (13, 15),
        (13, 30),
        (13, 45),
        (14, 0),
        (14, 15),
        (14, 30),
        (14, 45),
        (15, 0),
    ),
    ("15m", "half_day"): _slots((9, 45), (10, 0), (10, 15), (10, 30), (10, 45), (11, 0), (11, 15), (11, 30)),
    ("60m", "full_day"): _slots((10, 30), (11, 30), (14, 0), (15, 0)),
    ("60m", "half_day"): _slots((10, 30), (11, 30)),
}
_TARGET_CLOSE_SLOTS: Final[Mapping[tuple[str, str], tuple[tuple[int, int], ...]]] = {
    ("15m", "full_day"): _slots((10, 30), (11, 30), (14, 0), (15, 0)),
    ("15m", "half_day"): _slots((10, 30), (11, 30)),
    ("60m", "full_day"): _slots((15, 0)),
    ("60m", "half_day"): _slots((11, 30)),
}


def completed_bar_session_slots(
    frequency: str,
    session_template_id: str,
) -> tuple[tuple[int, int], ...]:
    """Return the single registered completed-bar slot template.

    Measurement layers use this lookup instead of importing the private table or
    duplicating exchange-session clocks as a second authority.
    """

    key = (frequency, session_template_id)
    try:
        return _SOURCE_CLOSE_SLOTS[key]
    except KeyError as exc:
        raise ValidationError(f"unregistered completed-bar session template: {frequency}:{session_template_id}") from exc


@dataclass(frozen=True, slots=True)
class CausalScaleEdge:
    """One permitted aggregation edge from a finer to a coarser carrier."""

    source_frequency: str
    target_frequency: str
    aggregation_rule: str = "completed_ohlc"

    def __post_init__(self) -> None:
        if self.source_frequency not in _FREQUENCY_RANK or self.target_frequency not in _FREQUENCY_RANK:
            raise ValidationError("scale ladder edge has an unsupported frequency")
        if _FREQUENCY_RANK[self.source_frequency] >= _FREQUENCY_RANK[self.target_frequency]:
            raise ValidationError("causal scale ladder permits only upward aggregation")
        if (self.source_frequency, "full_day") not in _SOURCE_CLOSE_SLOTS:
            raise ValidationError("scale ladder edge lacks a completed-bar session template")

    def to_dict(self) -> dict[str, object]:
        return {
            "source_frequency": self.source_frequency,
            "target_frequency": self.target_frequency,
            "aggregation_rule": self.aggregation_rule,
            "availability_rule": "available_only_after_all_expected_source_bars_close",
            "missing_bar_policy": REJECT_INCOMPLETE_SOURCE_BARS_POLICY,
        }


@dataclass(frozen=True, slots=True)
class CausalScaleLadder:
    """Frozen upward-only K-line aggregation graph and input policy."""

    catalog: TimeScaleCatalog
    edges: tuple[CausalScaleEdge, ...]
    production_authority: bool = False
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False

    def __post_init__(self) -> None:
        if self.production_authority or self.dynamic_parameter_authority or self.tool_routing_authority:
            raise ValidationError("causal scale ladder cannot grant authority")
        keys = [(item.source_frequency, item.target_frequency) for item in self.edges]
        if not keys or len(keys) != len(set(keys)):
            raise ValidationError("causal scale ladder requires unique registered edges")

    def edge(self, source_frequency: str, target_frequency: str) -> CausalScaleEdge:
        for item in self.edges:
            if (item.source_frequency, item.target_frequency) == (source_frequency, target_frequency):
                return item
        raise ValidationError(f"unregistered causal scale transition: {source_frequency}->{target_frequency}")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_id": CAUSAL_SCALE_LADDER_SCHEMA_ID,
            "ladder_version": CAUSAL_SCALE_LADDER_VERSION,
            "time_scale_catalog": self.catalog.to_dict(),
            "edges": [item.to_dict() for item in self.edges],
            "filter_sampling_policy": {
                "policy_id": REJECT_INCOMPLETE_SOURCE_BARS_POLICY,
                "requires_completed_target_bar": True,
                "permits_padding": False,
                "permits_future_source_bar": False,
            },
            "production_authority": self.production_authority,
            "dynamic_parameter_authority": self.dynamic_parameter_authority,
            "tool_routing_authority": self.tool_routing_authority,
            "field_labels_zh": {
                "source_frequency": "源K线频率",
                "target_frequency": "只向上因果聚合后的K线频率",
                "bar_complete": "目标K线是否已收齐所有预期源K线",
                "available_at": "目标K线可被使用的最早时点",
                "sampling_status": "滤波输入的规则采样/缺K线状态",
            },
        }
        payload["semantic_digest"] = canonical_digest(payload)
        return payload


def build_causal_scale_ladder_v2(
    *,
    catalog: TimeScaleCatalog | None = None,
) -> CausalScaleLadder:
    """Build the two physical K-line aggregation edges used by V2."""

    return CausalScaleLadder(
        catalog=catalog or build_time_scale_catalog_v2(),
        edges=(CausalScaleEdge("15m", "60m"), CausalScaleEdge("60m", "1d")),
    )


def aggregate_causal_bars(
    bars: pd.DataFrame,
    *,
    source_frequency: str,
    target_frequency: str,
    ladder: CausalScaleLadder | None = None,
) -> pd.DataFrame:
    """Aggregate OHLC only after every expected source bar has completed.

    An observed partial group remains in the returned audit frame with
    ``bar_complete=false`` and ``available_at=NaT``.  It is never silently
    converted into a target observation.
    """

    active_ladder = ladder or build_causal_scale_ladder_v2()
    _ = active_ladder.edge(source_frequency, target_frequency)
    normalized = normalize_bar_panel(bars, frequency=source_frequency).frame
    frame = normalized.copy()
    if "session_template_id" not in frame:
        frame["session_template_id"] = "full_day"
    frame["session_template_id"] = frame["session_template_id"].astype(str)
    if not frame["session_template_id"].isin(_SESSION_TEMPLATES).all():
        raise ValidationError("session_template_id must be full_day or half_day")

    rows: list[dict[str, object]] = []
    for (trading_day, template), session in frame.groupby(["trading_day", "session_template_id"], sort=True):
        source_slots = _SOURCE_CLOSE_SLOTS[(source_frequency, template)]
        target_slots = _TARGET_CLOSE_SLOTS[(source_frequency, template)]
        actual_slots = [_clock(value) for value in session["timestamp"]]
        if any(value not in source_slots for value in actual_slots):
            raise ValidationError("source bar timestamp does not match its registered session template")
        bucket_by_source_slot = {
            source_slot: target_slots[index // (len(source_slots) // len(target_slots))] for index, source_slot in enumerate(source_slots)
        }
        working = session.copy()
        working["_target_slot"] = [_slot_key(bucket_by_source_slot[value]) for value in actual_slots]
        for target_key, group in working.groupby("_target_slot", sort=True):
            target_slot = tuple(int(part) for part in target_key.split(":"))
            target_index = target_slots.index(target_slot)
            width = len(source_slots) // len(target_slots)
            expected_slots = source_slots[target_index * width : (target_index + 1) * width]
            observed_slots = {_clock(value) for value in group["timestamp"]}
            complete = observed_slots == set(expected_slots)
            target_timestamp = _target_timestamp(pd.Timestamp(trading_day), target_slot)
            rows.append(
                {
                    "trading_day": pd.Timestamp(trading_day).normalize(),
                    "timestamp": target_timestamp,
                    "open": float(group["open"].iloc[0]),
                    "high": float(group["high"].max()),
                    "low": float(group["low"].min()),
                    "close": float(group["close"].iloc[-1]),
                    "session_template_id": template,
                    "source_frequency": source_frequency,
                    "target_frequency": target_frequency,
                    "source_bar_count": int(len(group)),
                    "expected_source_bar_count": int(len(expected_slots)),
                    "bar_complete": complete,
                    "available_at": target_timestamp if complete else pd.NaT,
                    "sampling_status": "complete" if complete else "incomplete_source_bars",
                }
            )
    if not rows:
        raise ValidationError("causal aggregation has no source groups")
    return pd.DataFrame(rows).sort_values("timestamp", kind="mergesort").reset_index(drop=True)


def validate_causal_filter_input(
    bars: pd.DataFrame,
    *,
    missing_bar_policy: str = REJECT_INCOMPLETE_SOURCE_BARS_POLICY,
) -> pd.DataFrame:
    """Fail closed before a digital filter consumes causal aggregate bars."""

    if missing_bar_policy != REJECT_INCOMPLETE_SOURCE_BARS_POLICY:
        raise ValidationError("digital filter missing-bar policy is not registered")
    required = {"timestamp", "available_at", "bar_complete", "sampling_status"}
    missing = sorted(required - set(bars.columns))
    if missing:
        raise ValidationError(f"causal filter input missing fields: {missing}")
    if bars.empty or not bars["bar_complete"].eq(True).all() or not bars["sampling_status"].eq("complete").all():
        raise ValidationError("digital filter rejects incomplete causal source-bar groups")
    if bars["available_at"].isna().any():
        raise ValidationError("completed causal bar must have an availability timestamp")
    if not pd.to_datetime(bars["available_at"], errors="coerce").equals(pd.to_datetime(bars["timestamp"], errors="coerce")):
        raise ValidationError("causal bar may be available only at its completed target timestamp")
    return bars.copy()


def _clock(value: object) -> tuple[int, int]:
    timestamp = pd.Timestamp(value)
    return timestamp.hour, timestamp.minute


def _slot_key(slot: tuple[int, int]) -> str:
    return f"{slot[0]:02d}:{slot[1]:02d}"


def _target_timestamp(trading_day: pd.Timestamp, slot: tuple[int, int]) -> pd.Timestamp:
    naive = datetime.combine(trading_day.date(), time(slot[0], slot[1]))
    return pd.Timestamp(naive).tz_localize(TIMEZONE)


__all__ = [
    "CAUSAL_SCALE_LADDER_SCHEMA_ID",
    "CAUSAL_SCALE_LADDER_VERSION",
    "CausalScaleEdge",
    "CausalScaleLadder",
    "REJECT_INCOMPLETE_SOURCE_BARS_POLICY",
    "aggregate_causal_bars",
    "build_causal_scale_ladder_v2",
    "completed_bar_session_slots",
    "validate_causal_filter_input",
]
