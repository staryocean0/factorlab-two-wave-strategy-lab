"""Layer-1 clock contract: menu, pairing, and DataHub query translation.

This is not a K-line attribute module and grants no direction or routing.
Wall-clock bars are constructed by DataHub. This module only chooses the
research menu, pairs signal/fill views and execution windows, and refuses
local 2m/3m/10m/20m or wall-clock resampling. Layer-2 measurement consumes
these clocks and must not rewrite them. Legacy official 15:00 daily remains
readable only through an explicit override.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any, Literal

LEGACY_OFFICIAL_1500_QFQ = (
    "bars_cn_a_1d_qfq_canonical_xdxr_v9_factorlab_2009_2025_20260814"
)
OFFICIAL_SESSION_CONTRACT = "cn_a_session_end_label_no_noon_partial_v2"
SESSION_OFFSET_CONTRACT = "cn_a_session_wall_clock_offset_v1"
DEFAULT_SIGNAL_VIEW = "qfq_canonical"
DEFAULT_FILL_VIEW = "raw_canonical"
DEFAULT_COMMISSION_BPS = 5.0
DEFAULT_SLIPPAGE_BPS = 2.0
BAR_CONSTRUCTION_OWNER = "datahub"
DATAHUB_HISTORY_BARS_ROUTE = "GET /api/v1/history/bars"
DATAHUB_ON_DEMAND_KLINE_ROUTE = "GET /api/v1/history/on-demand-klines"
FORBIDDEN_LOCAL_RESAMPLE_FREQUENCIES = ("2m", "3m", "10m", "20m")
CONTINUOUS_CLOCK_CONSTRUCTION = "shifted_session_clock@1.0"

ExecutionWindow = Literal[
    "same_day_afternoon",
    "next_session",
    "next_tradable_after_bar_close",
    "next_bar_close_to_close",
]

# Per-frequency research menus. None of these is a unique project default.
# Each native frequency has two or three legal offset schemes; callers pick one.
# If fetch omits offset/anchor, use the first fallback of that menu only.
# 15m+15 is a DataHub capability, not a 15-minute research default.
RESEARCH_OFFSET_SCHEMES: dict[str, tuple[dict[str, object], ...]] = {
    "1d": (
        {
            "scheme_id": "daily_noon_close_1130",
            "frequency": "1d",
            "close_anchor": "11:30",
            "session_offset_minutes": 0,
            "purpose": "日线中午收盘，当天下午成交",
        },
        {
            "scheme_id": "daily_to_official_60m_close_1400",
            "frequency": "60m",
            "close_anchor": None,
            "session_offset_minutes": 0,
            "bar_align": "session_end_label_v2",
            "close_time": "14:00",
            "purpose": "日线 14:00 代理：从官方 60 分钟网格选择 14:00 收线",
        },
        {
            "scheme_id": "daily_to_30m_close_1430",
            "frequency": "30m",
            "close_anchor": None,
            "session_offset_minutes": 30,
            "close_time": "14:30",
            "purpose": "日线的 14:30 / 30 分钟差分",
        },
    ),
    "60m": (
        {
            "scheme_id": "hourly_offset_30",
            "frequency": "60m",
            "session_offset_minutes": 30,
            "close_times": ("11:00", "14:30"),
            "purpose": "小时线 +30，完整收线为 11:00/14:30；fetch 回落也落在这一档",
        },
        {
            "scheme_id": "hourly_to_30m_offset_15",
            "frequency": "30m",
            "session_offset_minutes": 15,
            "purpose": "小时结论拆到半小时 +15",
        },
        {
            "scheme_id": "hourly_to_60m_offset_45",
            "frequency": "60m",
            "session_offset_minutes": 45,
            "purpose": "小时结论的 45 分钟相位，不是 15m+45",
        },
    ),
    "15m": (
        {
            "scheme_id": "quarter_to_15m_offset_5",
            "frequency": "15m",
            "session_offset_minutes": 5,
            "purpose": "15 分钟线用 5 分钟补偿第一档，K 线仍是 15 分钟",
        },
        {
            "scheme_id": "quarter_to_15m_offset_10",
            "frequency": "15m",
            "session_offset_minutes": 10,
            "purpose": "15 分钟线用 5 分钟补偿第二档，K 线仍是 15 分钟",
        },
    ),
}

# Named recipes for old timing-infrastructure remakes. Same menu, not a second default.
OPTIONAL_REMAKE_VARIANTS: dict[str, tuple[dict[str, object], ...]] = {
    "1d": (
        {
            "variant_id": "daily_to_60m_close_1400",
            "frequency": "60m",
            "session_offset_minutes": 30,
            "close_time": "14:00",
            "purpose": "旧日线结论的下午低波动过渡，不是 11:30 默认替代",
        },
        {
            "variant_id": "daily_to_30m_close_1430",
            "frequency": "30m",
            "session_offset_minutes": 30,
            "close_time": "14:30",
            "purpose": "旧日线结论的更细下午过渡",
        },
    ),
    "60m": (
        {
            "variant_id": "hourly_to_30m_offset_15",
            "frequency": "30m",
            "session_offset_minutes": 15,
            "close_time": "10:15",
            "purpose": "旧小时结论拆到半小时差分",
        },
        {
            "variant_id": "hourly_to_60m_offset_30",
            "frequency": "60m",
            "session_offset_minutes": 30,
            "close_time": "14:00",
            "purpose": "旧小时结论的 +30 / 14:00 这根 60 分钟，不是 60m+5",
        },
        {
            "variant_id": "hourly_to_60m_offset_45",
            "frequency": "60m",
            "session_offset_minutes": 45,
            "close_time": "10:15",
            "purpose": "旧小时结论的 45 分钟相位；落在 60m 网格，不是非法的 15m+45",
        },
    ),
    "15m": (
        {
            "variant_id": "quarter_to_15m_offset_5",
            "frequency": "15m",
            "session_offset_minutes": 5,
            "close_time": "09:50",
            "purpose": "旧 15 分钟结论用 5 分钟步进做第一档相位，K 线仍是 15 分钟",
        },
        {
            "variant_id": "quarter_to_15m_offset_10",
            "frequency": "15m",
            "session_offset_minutes": 10,
            "close_time": "09:55",
            "purpose": "旧 15 分钟结论用 5 分钟步进做第二档相位，K 线仍是 15 分钟",
        },
    ),
}

# Successor V2 is a truthful construction menu, separate from the published
# legacy remake identities above. Its close clocks are contract fields.
UNIFIED_KLINE_VARIANTS_V2: tuple[dict[str, object], ...] = (
    {"view_id": "15m_offset_5", "frequency": "15m", "session_offset_minutes": 5,
     "close_times": ("09:50", "10:05", "10:20", "10:35", "10:50", "11:05", "11:20", "13:20", "13:35", "13:50", "14:05", "14:20", "14:35", "14:50")},
    {"view_id": "15m_offset_10", "frequency": "15m", "session_offset_minutes": 10,
     "close_times": ("09:55", "10:10", "10:25", "10:40", "10:55", "11:10", "11:25", "13:25", "13:40", "13:55", "14:10", "14:25", "14:40", "14:55")},
    {"view_id": "30m_offset_15", "frequency": "30m", "session_offset_minutes": 15,
     "close_times": ("10:15", "10:45", "11:15", "13:45", "14:15", "14:45")},
    {"view_id": "60m_offset_30", "frequency": "60m", "session_offset_minutes": 30,
     "close_times": ("11:00", "14:30")},
    {"view_id": "60m_offset_45", "frequency": "60m", "session_offset_minutes": 45,
     "close_times": ("11:15", "14:45")},
    {"view_id": "daily_noon_close_1130", "frequency": "1d", "close_anchor": "11:30",
     "session_offset_minutes": 0, "close_times": ("11:30",)},
    {"view_id": "daily_proxy_close_1400", "frequency": "60m", "session_offset_minutes": 0,
     "bar_align": "session_end_label_v2", "select_close_time": "14:00", "close_times": ("14:00",)},
    {"view_id": "daily_proxy_close_1430", "frequency": "30m", "session_offset_minutes": 30,
     "select_close_time": "14:30", "close_times": ("14:30",)},
)


def _clock_range(start_minute: int, end_minute: int, step: int) -> tuple[str, ...]:
    return tuple(
        f"{minute // 60:02d}:{minute % 60:02d}"
        for minute in range(start_minute, end_minute + 1, step)
    )


ONE_MINUTE_OFFICIAL_CLOCKS = (
    *_clock_range(571, 690, 1),
    *_clock_range(781, 900, 1),
)


def _five_minute_clocks(offset_minutes: int) -> tuple[str, ...]:
    first_morning_close = 575 + offset_minutes
    first_afternoon_close = 785 + offset_minutes
    return (
        *_clock_range(first_morning_close, 690, 5),
        *_clock_range(first_afternoon_close, 900, 5),
    )


# V3 appends the T+0 evaluation surface without mutating V2 identities.
UNIFIED_KLINE_VARIANTS_V3: tuple[dict[str, object], ...] = (
    {
        "view_id": "1m_official",
        "frequency": "1m",
        "session_offset_minutes": 0,
        "bar_align": "session_end_label_v2",
        "close_times": ONE_MINUTE_OFFICIAL_CLOCKS,
    },
    *(
        {
            "view_id": f"5m_offset_{offset}",
            "frequency": "5m",
            "session_offset_minutes": offset,
            "bar_align": (
                "session_end_label_v2" if offset == 0 else "session_wall_clock"
            ),
            "close_times": _five_minute_clocks(offset),
        }
        for offset in range(5)
    ),
    *UNIFIED_KLINE_VARIANTS_V2,
)


def _alias_frequency(native_frequency: str) -> str:
    freq = str(native_frequency or "").strip()
    aliases = {"daily": "1d", "hour": "60m", "hourly": "60m", "quarter": "15m"}
    return aliases.get(freq, freq)


def optional_remake_variants(native_frequency: str) -> tuple[dict[str, object], ...]:
    """Return named remake recipes for an old-caliber native frequency."""
    return OPTIONAL_REMAKE_VARIANTS.get(_alias_frequency(native_frequency), ())


def unified_kline_variants_v2() -> tuple[dict[str, object], ...]:
    """Return the immutable successor view/clock contract."""
    return UNIFIED_KLINE_VARIANTS_V2


def unified_kline_variants_v3() -> tuple[dict[str, object], ...]:
    """Return the immutable T+0-capable successor view/clock contract."""
    return UNIFIED_KLINE_VARIANTS_V3


def research_offset_schemes(native_frequency: str) -> tuple[dict[str, object], ...]:
    """Return the legal research offset menu for a native frequency.

    These are optional, not a unique default. 15m has +5 and +10 only.
    """
    return RESEARCH_OFFSET_SCHEMES.get(_alias_frequency(native_frequency), ())


def assert_no_local_bar_resample(frequency: str) -> None:
    """Refuse FactorLab-side construction of DataHub-owned bars."""

    freq = _alias_frequency(frequency)
    if freq in FORBIDDEN_LOCAL_RESAMPLE_FREQUENCIES:
        raise ValueError(
            f"frequency={freq} must be consumed from DataHub "
            f"{DATAHUB_ON_DEMAND_KLINE_ROUTE}; FactorLab must not locally "
            "resample 2m/3m/10m/20m"
        )
    if freq in {"1d", "60m", "30m", "15m", "5m", "1m"}:
        return
    raise ValueError(
        f"frequency={freq} is not a FactorLab wall-clock research frequency"
    )


def research_scheme_to_datahub_query(
    scheme: Mapping[str, object],
) -> dict[str, object]:
    """Translate one FactorLab menu item into a DataHub /history/bars query.

    ``select_close_time`` stays on the FactorLab side: DataHub still returns
    the whole official or offset grid, and FactorLab picks 14:00 / 14:30.
    """

    frequency = str(scheme.get("frequency") or "").strip()
    assert_no_local_bar_resample(frequency)
    offset = int(scheme.get("session_offset_minutes") or 0)
    anchor = scheme.get("close_anchor")
    anchor_text = None if anchor in (None, "") else str(anchor)
    align = scheme.get("bar_align")
    if align in (None, ""):
        if anchor_text == "11:30" or offset:
            align = "session_wall_clock"
        else:
            align = "session_end_label_v2"
    construction = (
        SESSION_OFFSET_CONTRACT
        if offset or anchor_text == "11:30" or align == "session_wall_clock"
        else OFFICIAL_SESSION_CONTRACT
    )
    params: dict[str, object] = {
        "frequency": frequency,
        "bar_align": str(align),
    }
    if offset:
        params["session_offset_minutes"] = offset
    if anchor_text:
        params["close_anchor"] = anchor_text
    query: dict[str, object] = {
        "route": DATAHUB_HISTORY_BARS_ROUTE,
        "bar_construction_owner": BAR_CONSTRUCTION_OWNER,
        "construction_contract": construction,
        "params": params,
    }
    select_close = scheme.get("select_close_time") or scheme.get("close_time")
    if select_close:
        query["factorlab_select_close_time"] = select_close
    return query


@dataclass(frozen=True, slots=True)
class DataContract:
    frequency: str
    close_anchor: str | None
    session_offset_minutes: int
    bar_align: str
    construction_contract: str
    signal_view: str = DEFAULT_SIGNAL_VIEW
    fill_view: str = DEFAULT_FILL_VIEW
    legacy_official_session: bool = False
    bar_construction_owner: str = BAR_CONSTRUCTION_OWNER

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_data_contract(
    frequency: str,
    *,
    legacy_official_session: bool = False,
) -> DataContract:
    freq = str(frequency or "").strip()
    if legacy_official_session:
        return DataContract(
            frequency=freq,
            close_anchor="15:00" if freq == "1d" else None,
            session_offset_minutes=0,
            bar_align="session_end_label_v2",
            construction_contract=OFFICIAL_SESSION_CONTRACT,
            legacy_official_session=True,
        )
    if freq == "1d":
        return DataContract(
            frequency="1d",
            close_anchor="11:30",
            session_offset_minutes=0,
            bar_align="session_wall_clock",
            construction_contract=SESSION_OFFSET_CONTRACT,
        )
    if freq == "60m":
        return DataContract(
            frequency="60m",
            close_anchor=None,
            session_offset_minutes=30,
            bar_align="session_wall_clock",
            construction_contract=SESSION_OFFSET_CONTRACT,
        )
    if freq == "15m":
        return DataContract(
            frequency="15m",
            close_anchor=None,
            session_offset_minutes=5,
            bar_align="session_wall_clock",
            construction_contract=SESSION_OFFSET_CONTRACT,
        )
    return DataContract(
        frequency=freq,
        close_anchor=None,
        session_offset_minutes=0,
        bar_align="session_end_label_v2",
        construction_contract=OFFICIAL_SESSION_CONTRACT,
    )


def inferred_execution_window(contract: DataContract) -> ExecutionWindow:
    if contract.legacy_official_session or (
        contract.frequency == "1d" and contract.close_anchor == "15:00"
    ):
        return "next_session"
    if contract.frequency == "1d" and contract.close_anchor == "11:30":
        return "same_day_afternoon"
    if contract.session_offset_minutes:
        return "next_tradable_after_bar_close"
    if contract.frequency in {"1m", "5m", "15m", "30m", "60m"}:
        return "next_tradable_after_bar_close"
    return "next_session"


def validate_execution_pairing(
    contract: DataContract,
    execution_window: str,
    *,
    optimistic_research_only: bool = False,
) -> None:
    """Reject data/backtest combinations that reintroduce overnight gap or future data."""

    if execution_window == "next_bar_close_to_close" and not optimistic_research_only:
        raise ValueError(
            "next_bar_close_to_close is optimistic_research_only and cannot be a trading truth"
        )
    if (
        contract.close_anchor == "11:30"
        and execution_window == "next_session"
        and not contract.legacy_official_session
    ):
        raise ValueError(
            "noon-close daily cannot use next_session; that would trade the next open gap"
        )
    if contract.close_anchor == "15:00" and execution_window == "same_day_afternoon":
        raise ValueError(
            "official 15:00 daily cannot use same_day_afternoon; afternoon data would leak"
        )
    if (
        contract.frequency in {"1m", "5m", "15m", "30m", "60m"}
        and contract.session_offset_minutes
        and execution_window == "next_session"
    ):
        raise ValueError(
            "offset intraday bars cannot use next_session; fill after bar_close_ts"
        )
    expected = inferred_execution_window(contract)
    if execution_window != expected and execution_window != "next_bar_close_to_close":
        raise ValueError(
            f"execution_window={execution_window!r} is not paired with "
            f"frequency={contract.frequency} close_anchor={contract.close_anchor} "
            f"offset={contract.session_offset_minutes}; expected {expected!r}"
        )


def apply_fetch_defaults(
    *,
    frequency: str,
    view: str | None,
    close_anchor: str | None,
    session_offset_minutes: int | None,
    bar_align: str | None,
    legacy_official_session: bool = False,
    dataset_version: str | None = None,
) -> dict[str, Any]:
    """Fill fetch parameters so callers do not have to remember offset/anchor."""

    if dataset_version == LEGACY_OFFICIAL_1500_QFQ:
        legacy_official_session = True
    contract = default_data_contract(
        frequency, legacy_official_session=legacy_official_session
    )
    if legacy_official_session:
        return {
            "view": view or DEFAULT_SIGNAL_VIEW,
            "close_anchor": None,
            "session_offset_minutes": None,
            "bar_align": None,
            "legacy_official_session": True,
            "data_contract": contract.to_dict(),
            "execution_window": inferred_execution_window(contract),
        }
    offset = (
        contract.session_offset_minutes
        if session_offset_minutes is None
        else int(session_offset_minutes)
    )
    anchor = contract.close_anchor if close_anchor in (None, "") else close_anchor
    align = contract.bar_align if bar_align in (None, "") else bar_align
    resolved = DataContract(
        frequency=frequency,
        close_anchor=anchor,
        session_offset_minutes=offset,
        bar_align=str(align or contract.bar_align),
        construction_contract=contract.construction_contract,
        signal_view=view or DEFAULT_SIGNAL_VIEW,
        fill_view=DEFAULT_FILL_VIEW,
        legacy_official_session=False,
    )
    window = inferred_execution_window(resolved)
    validate_execution_pairing(resolved, window)
    return {
        "view": resolved.signal_view,
        "close_anchor": resolved.close_anchor,
        "session_offset_minutes": resolved.session_offset_minutes or None,
        "bar_align": resolved.bar_align,
        "legacy_official_session": False,
        "data_contract": resolved.to_dict(),
        "execution_window": window,
    }


def assert_dataset_matches_contract(
    metadata: Mapping[str, Any],
    contract: DataContract,
) -> None:
    construction = str(metadata.get("construction_contract") or "")
    if contract.legacy_official_session:
        return
    if construction and construction != contract.construction_contract:
        raise ValueError(
            "DataHub response construction_contract does not match FactorLab default "
            f"({construction!r} != {contract.construction_contract!r})"
        )
    if contract.close_anchor == "11:30":
        close_anchor = str(metadata.get("close_anchor") or "")
        if close_anchor and close_anchor != "11:30":
            raise ValueError("expected noon-close daily, got official close_anchor")
