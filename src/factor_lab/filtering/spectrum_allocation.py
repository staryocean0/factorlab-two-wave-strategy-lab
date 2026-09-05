"""Construct one-lowpass plus non-overlapping-bandpass spectrum plans.

The frequency discovery stage is intentionally expansive: it finds positive DII
points and consolidates them into tradable bands.  A production-facing timing
plan needs one more compression step.  Filters are capital-allocation objects,
not independent trivia: a low-pass trend layer retains all slower structure
above its cutoff, while band-pass layers should cover faster slices with as
little overlap as practical.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, Literal

SpectrumLayerRole = Literal[
    "lowpass_anchor", "bandpass_layer", "conflicting_alternative"
]


@dataclass(frozen=True, slots=True)
class SpectrumAllocationConfig:
    """Policy for compressing candidate bands into a spectrum stack."""

    min_lowpass_anchor_cagr: float = 0.20
    min_lowpass_anchor_mdd: float = -0.30
    min_bandpass_layer_cagr: float = 0.10
    max_bandpass_layer_mdd: float = -0.45
    lowpass_overlap_guard_ratio: float = 0.95
    bandpass_merge_overlap_ratio: float = 0.20
    max_bandpass_layers: int = 4
    require_bandpass_tool_match: bool = True

    def __post_init__(self) -> None:
        if self.lowpass_overlap_guard_ratio <= 0.0:
            raise ValueError("lowpass_overlap_guard_ratio must be > 0")
        if not 0.0 <= self.bandpass_merge_overlap_ratio < 1.0:
            raise ValueError("bandpass_merge_overlap_ratio must be in [0, 1)")
        if self.max_bandpass_layers <= 0:
            raise ValueError("max_bandpass_layers must be > 0")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SpectrumAllocationLayer:
    """One layer in the final one-lowpass + many-bandpass stack."""

    role: SpectrumLayerRole
    cluster_id: str
    carrier: str
    filter_mode: str
    period_lo_days: float
    period_hi_days: float
    selected_oos_cagr: float
    selected_oos_mdd: float
    selected_oos_turnover: float
    best_fixed_filter: str
    included_candidates: str
    rationale_zh: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SpectrumAllocationPlan:
    """Final spectrum allocation artifact for one index."""

    status: str
    lowpass_anchor: SpectrumAllocationLayer | None
    bandpass_layers: list[SpectrumAllocationLayer]
    conflicting_alternatives: list[SpectrumAllocationLayer]
    rejected: list[SpectrumAllocationLayer]
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "lowpass_anchor": (
                self.lowpass_anchor.to_dict() if self.lowpass_anchor else None
            ),
            "bandpass_layers": [item.to_dict() for item in self.bandpass_layers],
            "conflicting_alternatives": [
                item.to_dict() for item in self.conflicting_alternatives
            ],
            "rejected": [item.to_dict() for item in self.rejected],
            "metadata": self.metadata,
        }


def build_spectrum_allocation_plan(
    rows: Sequence[Mapping[str, Any]],
    *,
    config: SpectrumAllocationConfig | None = None,
) -> SpectrumAllocationPlan:
    """Build the final one-lowpass plus non-overlapping-bandpass plan.

    Input rows are expected to be post-WF merged-band summaries with at least
    ``filter_mode``, ``T_days_lo``, ``T_days_hi``, ``selected_oos_cagr`` and
    ``selected_oos_mdd``.  The function is deliberately independent from a
    specific dataframe dependency so CLI reports and workflow artifacts can use
    the same policy.
    """

    cfg = config or SpectrumAllocationConfig()
    completed = [
        row for row in rows if str(row.get("status", "completed")) == "completed"
    ]
    candidates = [
        _layer_from_row(row, role="conflicting_alternative") for row in completed
    ]
    lowpass_anchor = _select_lowpass_anchor(candidates, cfg)
    if lowpass_anchor is None:
        return SpectrumAllocationPlan(
            status="empty_no_lowpass_anchor",
            lowpass_anchor=None,
            bandpass_layers=[],
            conflicting_alternatives=[],
            rejected=candidates,
            metadata={
                "policy": cfg.to_dict(),
                "spectrum_contract_zh": (
                    "最终择时方案尝试输出一个低通趋势层加多个不重叠带通层；"
                    "本次没有通过政策的低通锚。"
                ),
            },
        )

    bandpass_pool = [item for item in candidates if item.filter_mode == "bandpass"]
    selected_bandpass: list[SpectrumAllocationLayer] = []
    conflicts: list[SpectrumAllocationLayer] = []
    rejected: list[SpectrumAllocationLayer] = []
    lowpass_cutoff = lowpass_anchor.period_lo_days * cfg.lowpass_overlap_guard_ratio
    for item in sorted(bandpass_pool, key=_quality_sort_key, reverse=True):
        if cfg.require_bandpass_tool_match and not _looks_like_bandpass_tool(item):
            rejected.append(
                _replace_role(
                    item,
                    "conflicting_alternative",
                    "发现阶段是 bandpass，但最终赢家不是带通/component 工具；" +
                    "不放入带通频谱层。",
                )
            )
            continue
        if item.period_hi_days >= lowpass_cutoff:
            conflicts.append(
                _replace_role(
                    item,
                    "conflicting_alternative",
                    (
                        "与低通锚的慢频保留区重叠；作为同一频谱区域的替代表达，"
                        "不放入同一资金栈。"
                    ),
                )
            )
            continue
        if (
            item.selected_oos_cagr < cfg.min_bandpass_layer_cagr
            or item.selected_oos_mdd < cfg.max_bandpass_layer_mdd
        ):
            rejected.append(
                _replace_role(
                    item, "conflicting_alternative", "收益/回撤未达到带通层最低准入。"
                )
            )
            continue
        if any(
            _band_overlap_share(item, selected) > cfg.bandpass_merge_overlap_ratio
            for selected in selected_bandpass
        ):
            conflicts.append(
                _replace_role(
                    item,
                    "conflicting_alternative",
                    "与已入选带通层重叠，保留为替代候选。",
                )
            )
            continue
        selected_bandpass.append(
            _replace_role(
                item,
                "bandpass_layer",
                "位于低通锚更快的一侧，且与已选带通层基本不重叠。",
            )
        )
        if len(selected_bandpass) >= cfg.max_bandpass_layers:
            break

    selected_ids = {item.cluster_id for item in selected_bandpass}
    conflict_ids = {item.cluster_id for item in conflicts}
    rejected_ids = {item.cluster_id for item in rejected}
    for item in candidates:
        if (
            item.cluster_id in selected_ids
            or item.cluster_id in conflict_ids
            or item.cluster_id in rejected_ids
        ):
            continue
        if item.cluster_id == lowpass_anchor.cluster_id:
            continue
        if item.filter_mode == "lowpass":
            conflicts.append(
                _replace_role(
                    item,
                    "conflicting_alternative",
                    "低通层只保留一个；其他低通作为替代锚，不并行使用。",
                )
            )

    return SpectrumAllocationPlan(
        status="completed",
        lowpass_anchor=lowpass_anchor,
        bandpass_layers=selected_bandpass,
        conflicting_alternatives=conflicts,
        rejected=rejected,
        metadata={
            "policy": cfg.to_dict(),
            "lowpass_cutoff_days_for_bandpass_guard": lowpass_cutoff,
            "spectrum_contract_zh": (
                "最终输出不是一堆互相竞争的单点/频段，而是一个低通趋势锚"
                "加多个更快、尽量不重叠的带通层。低通保留其 cutoff 以上的"
                "慢频趋势，带通只补低通锚之外的更快频段。"
            ),
        },
    )


def _select_lowpass_anchor(
    candidates: Sequence[SpectrumAllocationLayer],
    cfg: SpectrumAllocationConfig,
) -> SpectrumAllocationLayer | None:
    eligible = [
        item
        for item in candidates
        if item.filter_mode == "lowpass"
        and item.selected_oos_cagr >= cfg.min_lowpass_anchor_cagr
        and item.selected_oos_mdd >= cfg.min_lowpass_anchor_mdd
    ]
    if not eligible:
        eligible = [item for item in candidates if item.filter_mode == "lowpass"]
    if not eligible:
        return None
    # For the anchor, prefer the slowest robust low-pass rather than the most
    # aggressive high-return low-pass.  This prevents a short low-pass from
    # swallowing the whole spectrum and making band-pass layers meaningless.
    selected = max(
        eligible, key=lambda item: (item.period_hi_days, _quality_sort_key(item))
    )
    return _replace_role(
        selected, "lowpass_anchor", "最低频趋势锚：低通层保留该 cutoff 以上的慢频趋势。"
    )


def _quality_sort_key(item: SpectrumAllocationLayer) -> tuple[float, float, float]:
    risk_adjusted = item.selected_oos_cagr / (abs(item.selected_oos_mdd) + 0.05)
    return (risk_adjusted, item.selected_oos_cagr, -item.selected_oos_turnover)


def _band_overlap_share(
    a: SpectrumAllocationLayer, b: SpectrumAllocationLayer
) -> float:
    lo = max(a.period_lo_days, b.period_lo_days)
    hi = min(a.period_hi_days, b.period_hi_days)
    if hi <= lo:
        return 0.0
    denom = max(
        min(a.period_hi_days - a.period_lo_days, b.period_hi_days - b.period_lo_days),
        1e-12,
    )
    return (hi - lo) / denom


def _looks_like_bandpass_tool(item: SpectrumAllocationLayer) -> bool:
    name = item.best_fixed_filter.lower()
    return "_bp" in name or "bandpass" in name


def _layer_from_row(
    row: Mapping[str, Any], *, role: SpectrumLayerRole
) -> SpectrumAllocationLayer:
    return SpectrumAllocationLayer(
        role=role,
        cluster_id=str(row.get("cluster_id", "")),
        carrier=str(row.get("carrier", "")),
        filter_mode=str(row.get("filter_mode", "")),
        period_lo_days=float(row.get("T_days_lo", row.get("period_lo_days", math.nan))),
        period_hi_days=float(row.get("T_days_hi", row.get("period_hi_days", math.nan))),
        selected_oos_cagr=float(row.get("selected_oos_cagr", math.nan)),
        selected_oos_mdd=float(row.get("selected_oos_mdd", math.nan)),
        selected_oos_turnover=float(row.get("selected_oos_turnover", math.nan)),
        best_fixed_filter=str(row.get("best_fixed_filter", "")),
        included_candidates=str(row.get("included_candidates", "")),
        rationale_zh="",
    )


def _replace_role(
    item: SpectrumAllocationLayer,
    role: SpectrumLayerRole,
    rationale_zh: str,
) -> SpectrumAllocationLayer:
    return SpectrumAllocationLayer(
        role=role,
        cluster_id=item.cluster_id,
        carrier=item.carrier,
        filter_mode=item.filter_mode,
        period_lo_days=item.period_lo_days,
        period_hi_days=item.period_hi_days,
        selected_oos_cagr=item.selected_oos_cagr,
        selected_oos_mdd=item.selected_oos_mdd,
        selected_oos_turnover=item.selected_oos_turnover,
        best_fixed_filter=item.best_fixed_filter,
        included_candidates=item.included_candidates,
        rationale_zh=rationale_zh,
    )
