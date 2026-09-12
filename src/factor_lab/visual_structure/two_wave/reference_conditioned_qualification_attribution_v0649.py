"""Threshold-free helpers for v0.6.49 reference-conditioned qualification attribution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

SCHEMA = "two_wave_reference_conditioned_qualification_attribution@0.6.49"
STRONG_CONTINUOUS_RANK = 0.70
STRONG_BINARY_GAP = 0.25
IDENTITY_MULTI_GAP = 0.10


@dataclass(frozen=True)
class DiagnosticSpec:
    name: str
    family: str
    failure_direction: str  # "higher" or "lower"


CONTINUOUS_SPECS = (
    DiagnosticSpec("confirmation_delay_bars", "publication_maturity", "lower"),
    DiagnosticSpec("completion_buffer_fraction", "publication_maturity", "lower"),
    DiagnosticSpec("parent_span_bars", "fragment_parent_scale", "lower"),
    DiagnosticSpec("parent_span_fraction", "fragment_parent_scale", "lower"),
    DiagnosticSpec("parent_anchor_excursion_fraction", "fragment_parent_scale", "lower"),
    DiagnosticSpec("amplitude_unit_fraction", "fragment_parent_scale", "lower"),
    DiagnosticSpec("cycle_duration_ratio", "same_scale_imbalance", "higher"),
    DiagnosticSpec("corresponding_leg_duration_max_ratio", "same_scale_imbalance", "higher"),
    DiagnosticSpec("amplitude_ratio", "same_scale_imbalance", "higher"),
    DiagnosticSpec("min_leg_efficiency", "path_noise", "lower"),
    DiagnosticSpec("max_leg_jump_share", "path_noise", "higher"),
    DiagnosticSpec("max_leg_flat_share", "path_noise", "higher"),
    DiagnosticSpec("qualified_identity_count_at_cutoff", "identity_ambiguity", "higher"),
)

BINARY_SPECS = (
    ("inefficient_leg_triggered", "path_noise"),
    ("jump_dominated_leg_triggered", "path_noise"),
    ("corresponding_leg_duration_mismatch_triggered", "legacy_duration_mismatch"),
    ("multi_identity_at_cutoff", "identity_ambiguity"),
)


def _finite(values: Iterable[float]) -> np.ndarray:
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0 or not np.isfinite(arr).all():
        raise ValueError("nonempty finite values required")
    return arr


def rank_probability(no_values: Iterable[float], yes_values: Iterable[float]) -> float:
    """P(no > yes) + 0.5*P(tie), computed exactly over all cross-pairs."""
    a = _finite(no_values)
    b = _finite(yes_values)
    gt = 0
    ties = 0
    for x in a:
        gt += int(np.sum(x > b))
        ties += int(np.sum(x == b))
    return float((gt + 0.5 * ties) / (len(a) * len(b)))


def group_summary(values: Iterable[float]) -> dict:
    arr = _finite(values)
    q1, median, q3 = np.quantile(arr, [0.25, 0.5, 0.75], method="linear")
    return {
        "count": int(len(arr)),
        "q1": float(q1),
        "median": float(median),
        "q3": float(q3),
    }


def continuous_result(spec: DiagnosticSpec, no_values: Iterable[float], yes_values: Iterable[float]) -> dict:
    no = list(float(x) for x in no_values)
    yes = list(float(x) for x in yes_values)
    raw = rank_probability(no, yes)
    adjusted = raw if spec.failure_direction == "higher" else 1.0 - raw
    return {
        "family": spec.family,
        "failure_direction": spec.failure_direction,
        "reference_no": group_summary(no),
        "reference_yes": group_summary(yes),
        "rank_probability_no_gt_yes_plus_half_tie": raw,
        "direction_adjusted_failure_rank": adjusted,
        "strong_support": bool(adjusted >= STRONG_CONTINUOUS_RANK),
    }


def binary_result(no_values: Iterable[bool], yes_values: Iterable[bool], family: str) -> dict:
    no = list(bool(x) for x in no_values)
    yes = list(bool(x) for x in yes_values)
    if not no or not yes:
        raise ValueError("nonempty binary groups required")
    p_no = sum(no) / len(no)
    p_yes = sum(yes) / len(yes)
    gap = p_no - p_yes
    return {
        "family": family,
        "reference_no_incidence": float(p_no),
        "reference_yes_incidence": float(p_yes),
        "incidence_difference_no_minus_yes": float(gap),
        "strong_support": bool(gap >= STRONG_BINARY_GAP),
    }


def family_decision(continuous: dict[str, dict], binary: dict[str, dict]) -> dict:
    """Apply the protocol-frozen family support rule without fitting anything."""
    strong = {}

    # Publication maturity: both predeclared maturity diagnostics must support.
    strong["publication_maturity"] = all(
        continuous[x]["strong_support"]
        for x in ("confirmation_delay_bars", "completion_buffer_fraction")
    )

    # Fragment/parent scale: require two conceptually distinct scale diagnostics.
    fragment_keys = (
        "parent_span_fraction",
        "parent_anchor_excursion_fraction",
        "amplitude_unit_fraction",
    )
    strong["fragment_parent_scale"] = sum(continuous[x]["strong_support"] for x in fragment_keys) >= 2

    imbalance_keys = (
        "cycle_duration_ratio",
        "corresponding_leg_duration_max_ratio",
        "amplitude_ratio",
    )
    strong["same_scale_imbalance"] = sum(continuous[x]["strong_support"] for x in imbalance_keys) >= 2

    path_flags = [
        continuous[x]["strong_support"]
        for x in ("min_leg_efficiency", "max_leg_jump_share", "max_leg_flat_share")
    ] + [
        binary[x]["strong_support"]
        for x in ("inefficient_leg_triggered", "jump_dominated_leg_triggered")
    ]
    strong["path_noise"] = sum(path_flags) >= 2

    strong["identity_ambiguity"] = bool(
        continuous["qualified_identity_count_at_cutoff"]["strong_support"]
        and binary["multi_identity_at_cutoff"]["incidence_difference_no_minus_yes"] >= IDENTITY_MULTI_GAP
    )

    supported = [k for k, v in strong.items() if v]
    if len(supported) == 1:
        primary = supported[0]
    elif len(supported) > 1:
        primary = "multi_mechanism_semantic_mismatch"
    else:
        primary = "diffuse_or_fundamental_semantic_object_mismatch"
    return {
        "strongly_supported_families": strong,
        "supported_family_names": supported,
        "primary_attribution": primary,
        "legacy_duration_mismatch_is_authorizing": False,
    }
