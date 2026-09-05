# pyright: reportAny=false, reportArgumentType=false
# pyright: reportAttributeAccessIssue=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Frozen V2 identities for market-state research time scales.

The catalog makes the five time concepts used by V2 non-interchangeable.  In
particular, a tool's ``period_bars`` remains a formula parameter; it cannot be
silently relabelled as a factor observation window or a validation fold.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.horizons import (
    SUPPORTED_FREQUENCIES,
    NormalizedBarPanel,
    normalize_bar_panel,
)

TIME_SCALE_CATALOG_SCHEMA_ID: Final[str] = "market_state_time_scale_catalog@1.0"
TIME_SCALE_CATALOG_VERSION: Final[str] = "market_state_time_scale_catalog_v2"
FACTOR_LOOKBACK_MULTIPLICITY_FAMILY: Final[str] = "market_state_v2_factor_lookback"


@dataclass(frozen=True, slots=True)
class TimeScaleSpec:
    """One factor observation window, measured in physical trading sessions."""

    scale_id: str
    factor_lookback_sessions: int
    name_zh: str
    aliases: tuple[str, ...] = ()
    multiplicity_family_id: str = FACTOR_LOOKBACK_MULTIPLICITY_FAMILY
    multiplicity_included: bool = True

    def __post_init__(self) -> None:
        if not self.scale_id.startswith("factor_"):
            raise ValidationError("factor time scale id must start with 'factor_'")
        if self.factor_lookback_sessions < 1:
            raise ValidationError("factor lookback must contain at least one session")
        if not self.name_zh.strip() or not self.multiplicity_family_id.strip():
            raise ValidationError("time scale metadata is required")
        aliases = tuple(sorted(set(self.aliases)))
        if any(not value.strip() or value.startswith("factor_") for value in aliases):
            raise ValidationError("time scale aliases must be non-factor nonblank identities")
        object.__setattr__(self, "aliases", aliases)

    def to_dict(self) -> dict[str, object]:
        return {
            "scale_id": self.scale_id,
            "factor_lookback_sessions": self.factor_lookback_sessions,
            "time_unit": "physical_trading_session",
            "name_zh": self.name_zh,
            "aliases": list(self.aliases),
            "multiplicity_family_id": self.multiplicity_family_id,
            "multiplicity_included": self.multiplicity_included,
        }


@dataclass(frozen=True, slots=True)
class ToolResearchTimeIdentity:
    """Typed five-part clock for one future tool--factor research record.

    It deliberately carries tool horizon *parameter ids*, rather than a
    numerical observation window, so callers cannot substitute a formula
    period or a validation fold for ``factor_scale_id``.
    """

    carrier_frequency: str
    factor_scale_id: str
    tool_horizon_parameter_ids: tuple[str, ...]
    decision_horizon_bars: int
    validation_span_id: str

    def __post_init__(self) -> None:
        if self.carrier_frequency not in SUPPORTED_FREQUENCIES:
            raise ValidationError("research time identity has an unsupported carrier frequency")
        if not self.factor_scale_id.startswith("factor_"):
            raise ValidationError("factor scale must be a catalog factor identity")
        parameter_ids = tuple(sorted(set(self.tool_horizon_parameter_ids)))
        if not parameter_ids or any(not item.strip() for item in parameter_ids):
            raise ValidationError("tool horizon must name one or more formula parameters")
        if self.decision_horizon_bars < 1:
            raise ValidationError("decision horizon must be positive")
        if not self.validation_span_id.strip():
            raise ValidationError("validation span identity is required")
        object.__setattr__(self, "tool_horizon_parameter_ids", parameter_ids)

    def validate_against(self, catalog: TimeScaleCatalog) -> None:
        """Prove that the declared factor observation scale was pre-registered."""

        _ = catalog.scale(self.factor_scale_id)

    def to_dict(self) -> dict[str, object]:
        return {
            "carrier_frequency": self.carrier_frequency,
            "factor_scale_id": self.factor_scale_id,
            "tool_horizon_parameter_ids": list(self.tool_horizon_parameter_ids),
            "decision_horizon_bars": self.decision_horizon_bars,
            "validation_span_id": self.validation_span_id,
        }


@dataclass(frozen=True, slots=True)
class SessionCoverageAudit:
    """Coverage of completed bars against a caller-supplied exchange calendar.

    The catalog deliberately does not infer whether an absent date is a market
    holiday or a data outage.  The caller supplies the authoritative calendar
    scope and open-session set; the audit then exposes both closed calendar
    dates and missing observations separately.
    """

    exchange_calendar_id: str
    calendar_days: tuple[str, ...]
    expected_open_session_days: tuple[str, ...]
    observed_open_session_days: tuple[str, ...]
    exchange_closed_calendar_days: tuple[str, ...]
    missing_open_session_days: tuple[str, ...]
    unexpected_observed_session_days: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "exchange_calendar_id": self.exchange_calendar_id,
            "calendar_days": list(self.calendar_days),
            "expected_open_session_days": list(self.expected_open_session_days),
            "observed_open_session_days": list(self.observed_open_session_days),
            "exchange_closed_calendar_days": list(self.exchange_closed_calendar_days),
            "missing_open_session_days": list(self.missing_open_session_days),
            "unexpected_observed_session_days": list(self.unexpected_observed_session_days),
        }


@dataclass(frozen=True, slots=True)
class TimeScaleCatalog:
    """Read-only V2 factor-scale catalog and its V1 legacy aliases."""

    scales: tuple[TimeScaleSpec, ...]
    production_authority: bool = False
    dynamic_parameter_authority: bool = False
    tool_routing_authority: bool = False

    def __post_init__(self) -> None:
        if self.production_authority or self.dynamic_parameter_authority or self.tool_routing_authority:
            raise ValidationError("time scale catalog cannot grant research or production authority")
        if not self.scales:
            raise ValidationError("time scale catalog cannot be empty")
        scale_ids = [item.scale_id for item in self.scales]
        aliases = [alias for item in self.scales for alias in item.aliases]
        if len(scale_ids) != len(set(scale_ids)) or len(aliases) != len(set(aliases)):
            raise ValidationError("time scale catalog contains duplicate identities")
        if set(scale_ids) & set(aliases):
            raise ValidationError("factor scale ids and aliases must not overlap")
        families = {item.multiplicity_family_id for item in self.scales}
        if families != {FACTOR_LOOKBACK_MULTIPLICITY_FAMILY}:
            raise ValidationError("all default factor scale attempts share one multiplicity family")
        if not all(item.multiplicity_included for item in self.scales):
            raise ValidationError("all catalog factor scales must enter multiplicity accounting")

    def scale(self, scale_or_alias_id: str) -> TimeScaleSpec:
        for item in self.scales:
            if scale_or_alias_id == item.scale_id or scale_or_alias_id in item.aliases:
                return item
        raise ValidationError(f"unregistered factor time scale: {scale_or_alias_id}")

    def factor_lookback_sessions(self, scale_or_alias_id: str) -> int:
        return self.scale(scale_or_alias_id).factor_lookback_sessions

    def factor_scale_id_for_legacy(self, legacy_measurement_scale_id: str) -> str:
        return self.scale(legacy_measurement_scale_id).scale_id

    def legacy_measurement_scale_ids(self) -> tuple[str, ...]:
        return tuple(sorted(alias for item in self.scales for alias in item.aliases))

    def normalize_factor_panel(self, panel: pd.DataFrame, *, frequency: str) -> NormalizedBarPanel:
        """Use the canonical physical-session normalizer for a factor input panel."""

        return normalize_bar_panel(panel, frequency=frequency)

    def full_horizon_mask(
        self,
        panel: pd.DataFrame,
        *,
        frequency: str,
        scale_or_alias_id: str,
    ) -> np.ndarray:
        normalized = self.normalize_factor_panel(panel, frequency=frequency)
        return normalized.full_horizon_mask(self.factor_lookback_sessions(scale_or_alias_id))

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_id": TIME_SCALE_CATALOG_SCHEMA_ID,
            "catalog_version": TIME_SCALE_CATALOG_VERSION,
            "physical_session_indexer": "factor_lab.market_state.horizons.TradingSessionIndexer",
            "calendar_binding_requirement": "caller_supplied_exchange_open_session_calendar",
            "scales": [item.to_dict() for item in self.scales],
            "production_authority": self.production_authority,
            "dynamic_parameter_authority": self.dynamic_parameter_authority,
            "tool_routing_authority": self.tool_routing_authority,
            "field_labels_zh": {
                "factor_lookback_sessions": "因子观察窗（物理交易会话数）",
                "carrier_frequency": "原始或因果聚合K线频率",
                "tool_horizon_parameter_ids": "工具公式周期参数，不是因子观察窗",
                "decision_horizon_bars": "决策更新间隔K线数",
                "validation_span_id": "外层验证切片身份，不是因子观察窗",
                "multiplicity_family_id": "同一因子观察窗尝试族",
            },
        }
        payload["semantic_digest"] = canonical_digest(payload)
        return payload


def _default_scales() -> tuple[TimeScaleSpec, ...]:
    aliases = {20: ("fast_20d",), 60: ("medium_60d",), 120: ("slow_120d",)}
    return tuple(
        TimeScaleSpec(
            scale_id=f"factor_{sessions}d",
            factor_lookback_sessions=sessions,
            name_zh=f"{sessions}个物理交易日因子观察窗",
            aliases=aliases.get(sessions, ()),
        )
        for sessions in (1, 3, 5, 10, 15, 20, 30, 40, 60, 120)
    )


def build_time_scale_catalog_v2() -> TimeScaleCatalog:
    """Build the frozen, zero-authority default factor-scale universe."""

    return TimeScaleCatalog(scales=_default_scales())


def audit_physical_session_coverage(
    panel: pd.DataFrame,
    *,
    frequency: str,
    exchange_calendar_id: str,
    calendar_days: Iterable[object],
    expected_open_session_days: Iterable[object],
) -> SessionCoverageAudit:
    """Audit holiday/closure dates separately from missing completed-bar data."""

    if not exchange_calendar_id.strip():
        raise ValidationError("exchange calendar identity is required for session coverage")
    calendar = _session_day_ids(calendar_days, field="calendar days")
    expected = _session_day_ids(expected_open_session_days, field="expected open sessions")
    if not calendar or not expected:
        raise ValidationError("calendar days and expected open sessions cannot be empty")
    if not set(expected).issubset(calendar):
        raise ValidationError("expected open sessions must belong to the supplied calendar span")
    normalized = normalize_bar_panel(panel, frequency=frequency)
    observed = tuple(sorted({pd.Timestamp(value).strftime("%Y-%m-%d") for value in normalized.frame["trading_day"]}))
    calendar_set = set(calendar)
    expected_set = set(expected)
    observed_set = set(observed)
    return SessionCoverageAudit(
        exchange_calendar_id=exchange_calendar_id,
        calendar_days=calendar,
        expected_open_session_days=expected,
        observed_open_session_days=observed,
        exchange_closed_calendar_days=tuple(sorted(calendar_set - expected_set)),
        missing_open_session_days=tuple(sorted(expected_set - observed_set)),
        unexpected_observed_session_days=tuple(sorted(observed_set - expected_set)),
    )


def validate_research_time_identities(
    catalog: TimeScaleCatalog,
    identities: Iterable[ToolResearchTimeIdentity],
) -> tuple[ToolResearchTimeIdentity, ...]:
    """Validate pre-registered identities without creating an experiment."""

    result = tuple(identities)
    for identity in result:
        identity.validate_against(catalog)
    return result


def _session_day_ids(values: Iterable[object], *, field: str) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        parsed = pd.Timestamp(value)
        if pd.isna(parsed):
            raise ValidationError(f"{field} contains an invalid date")
        result.append(parsed.normalize().strftime("%Y-%m-%d"))
    if len(result) != len(set(result)):
        raise ValidationError(f"{field} contains duplicate dates")
    return tuple(sorted(result))


__all__ = [
    "FACTOR_LOOKBACK_MULTIPLICITY_FAMILY",
    "SessionCoverageAudit",
    "TIME_SCALE_CATALOG_SCHEMA_ID",
    "TIME_SCALE_CATALOG_VERSION",
    "TimeScaleCatalog",
    "TimeScaleSpec",
    "ToolResearchTimeIdentity",
    "audit_physical_session_coverage",
    "build_time_scale_catalog_v2",
    "validate_research_time_identities",
]
