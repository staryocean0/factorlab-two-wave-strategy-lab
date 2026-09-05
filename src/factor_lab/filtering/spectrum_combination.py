"""Decision helpers for merging or keeping spectrum-stack bandpass layers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, Literal

BandpassCombinationDecision = Literal[
    "keep_separate_overlay",
    "merge_or_keep_one",
    "reject_incremental_layer",
    "micro_overlay_only",
]


@dataclass(frozen=True, slots=True)
class SpectrumCombinationConfig:
    """Policy thresholds for post-stack combination diagnostics."""

    high_correlation_threshold: float = 0.75
    low_conflict_threshold: float = 0.20
    min_cagr_improvement: float = 0.02
    max_mdd_worsening: float = 0.20
    micro_turnover_threshold: float = 400.0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SpectrumCombinationDecisionCard:
    """Result of deciding whether bandpass layers should be merged."""

    decision: BandpassCombinationDecision
    rationale_zh: str
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision,
            "rationale_zh": self.rationale_zh,
            "metadata": self.metadata,
        }


def decide_bandpass_combination(
    *,
    overlap_rows: Sequence[Mapping[str, Any]],
    combo_rows: Sequence[Mapping[str, Any]],
    base_combo: str = "lp_only",
    candidate_combo: str = "lp_plus_two_bp",
    config: SpectrumCombinationConfig | None = None,
) -> SpectrumCombinationDecisionCard:
    """Decide whether bandpass layers should be merged or kept separate.

    The decision is based on actual signal behavior and marginal portfolio
    evidence, not on frequency labels alone.
    """

    cfg = config or SpectrumCombinationConfig()
    bandpass_pairs = [
        row
        for row in overlap_rows
        if "bandpass" in str(row.get("a", "")) and "bandpass" in str(row.get("b", ""))
    ]
    max_corr = max(
        (abs(float(row.get("corr", 0.0))) for row in bandpass_pairs), default=0.0
    )
    min_conflict = min(
        (float(row.get("conflict_share", 1.0)) for row in bandpass_pairs), default=1.0
    )
    combos = {str(row.get("combo")): row for row in combo_rows}
    base = combos.get(base_combo)
    candidate = combos.get(candidate_combo)
    cagr_delta = None
    mdd_delta = None
    if base is not None and candidate is not None:
        cagr_delta = float(candidate.get("cagr", 0.0)) - float(base.get("cagr", 0.0))
        mdd_delta = float(candidate.get("max_drawdown", 0.0)) - float(
            base.get("max_drawdown", 0.0)
        )

    if (
        max_corr >= cfg.high_correlation_threshold
        and min_conflict <= cfg.low_conflict_threshold
    ):
        decision: BandpassCombinationDecision = "merge_or_keep_one"
        rationale = (
            "带通信号高度同步且冲突低，说明主要是同一机会的重复表达，" +
            "应合并或只保留一个。"
        )
    elif (
        cagr_delta is not None
        and cagr_delta >= cfg.min_cagr_improvement
        and (mdd_delta is None or mdd_delta >= -cfg.max_mdd_worsening)
    ):
        decision = "keep_separate_overlay"
        rationale = (
            "带通信号不高度同步，且加入组合后收益有边际改善，" +
            "暂不硬合并，保留为分权重 overlay。"
        )
    else:
        decision = "reject_incremental_layer"
        rationale = "带通层没有提供足够边际收益，或回撤恶化过大，不应进入最终组合。"

    return SpectrumCombinationDecisionCard(
        decision=decision,
        rationale_zh=rationale,
        metadata={
            "policy": cfg.to_dict(),
            "max_abs_bandpass_corr": max_corr,
            "min_bandpass_conflict_share": min_conflict,
            "base_combo": base_combo,
            "candidate_combo": candidate_combo,
            "cagr_delta": cagr_delta,
            "mdd_delta": mdd_delta,
        },
    )
