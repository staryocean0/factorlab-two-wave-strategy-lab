"""Pure diagnostic helpers for v0.6.26 residual direction attribution.

No recognizer rule is changed here.
"""
from __future__ import annotations

from typing import Iterable

RANGE_MAX_MARGIN = 0.15


def transition_category(d1_main: str, d1_other: str, cand_main: str, cand_other: str) -> str:
    d1_exact = str(d1_main) == str(d1_other)
    cand_exact = str(cand_main) == str(cand_other)
    if d1_exact and cand_exact:
        return "retained_exact"
    if d1_exact and not cand_exact:
        return "introduced_harm"
    if not d1_exact and cand_exact:
        return "repaired_old_nonexact"
    return "persistent_nonexact"


def rescue_topology(main_rescued: bool, other_rescued: bool) -> str:
    if main_rescued and other_rescued:
        return "both_rescued"
    if main_rescued:
        return "main_only_rescued"
    if other_rescued:
        return "other_only_rescued"
    return "neither_rescued"


def d1_topology(main_label: str, other_label: str) -> str:
    mu = str(main_label) == "uncertain"
    ou = str(other_label) == "uncertain"
    if mu and ou:
        return "both_uncertain"
    if mu:
        return "main_uncertain_other_decisive"
    if ou:
        return "main_decisive_other_uncertain"
    return "both_decisive"


def range_relative_margin(margin: float) -> float:
    value = float(margin)
    if value < 0:
        raise ValueError("margin must be nonnegative")
    return value / RANGE_MAX_MARGIN


def attribution_verdict(
    range_keep_fraction: float,
    trend_keep_fraction: float,
    introduced_harm_topologies: Iterable[str],
) -> dict:
    topologies = [str(x) for x in introduced_harm_topologies]
    one_sided = sum(x in {"main_only_rescued", "other_only_rescued"} for x in topologies)
    one_sided_fraction = one_sided / len(topologies) if topologies else 0.0
    range_suppressed = float(range_keep_fraction) <= 0.5 * float(trend_keep_fraction)
    harm_one_sided = one_sided_fraction >= 0.80
    verdict = (
        "v0626_absolute_margin_geometry_is_state_asymmetric"
        if range_suppressed and harm_one_sided
        else "v0626_residual_harm_not_explained_by_margin_geometry"
    )
    return {
        "verdict": verdict,
        "range_keep_fraction": float(range_keep_fraction),
        "trend_keep_fraction": float(trend_keep_fraction),
        "introduced_harm_one_sided_fraction": one_sided_fraction,
        "range_suppression_gate": range_suppressed,
        "introduced_harm_one_sided_gate": harm_one_sided,
    }
