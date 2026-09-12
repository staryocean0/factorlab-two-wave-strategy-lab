"""Frozen metrics for v0.6.51 left-boundary / internal-pivot decomposition."""
from __future__ import annotations

from statistics import median
from typing import Sequence

import numpy as np

SCHEMA = "two_wave_left_boundary_internal_pivot_decomposition@0.6.51"


def _summary(values: Sequence[float]) -> dict:
    vals = [float(x) for x in values]
    if not vals:
        return {"count": 0, "median": None, "q1": None, "q3": None}
    arr = np.asarray(vals, dtype=float)
    return {
        "count": len(vals),
        "median": float(np.median(arr)),
        "q1": float(np.quantile(arr, 0.25)),
        "q3": float(np.quantile(arr, 0.75)),
    }


def _sign_incidence(values: Sequence[float]) -> dict:
    vals = [float(x) for x in values]
    n = len(vals)
    if not n:
        return {"negative": 0.0, "zero": 0.0, "positive": 0.0}
    return {
        "negative": sum(x < 0 for x in vals) / n,
        "zero": sum(x == 0 for x in vals) / n,
        "positive": sum(x > 0 for x in vals) / n,
    }


def decompose_case(model: Sequence[int], human: Sequence[int]) -> dict:
    m = [int(x) for x in model]
    h = [int(x) for x in human]
    if len(m) != 5 or len(h) != 5:
        raise ValueError("five model and five human anchors required")
    if any(b <= a for a, b in zip(m, m[1:])) or any(b <= a for a, b in zip(h, h[1:])):
        raise ValueError("ordered anchors required")

    d = [float(a - b) for a, b in zip(m, h)]
    abs_d = [abs(x) for x in d]
    t = float(median(d))
    residuals = [x - t for x in d]
    raw_mae = sum(abs_d) / 5.0
    residual_mae = sum(abs(x) for x in residuals) / 5.0
    reduction = (raw_mae - residual_mae) / raw_mae if raw_mae > 0 else 0.0

    mspan = float(m[-1] - m[0])
    hspan = float(h[-1] - h[0])
    if mspan <= 0 or hspan <= 0:
        raise ValueError("positive spans required")

    model_phase = [(m[i] - m[0]) / mspan for i in (1, 2, 3)]
    human_phase = [(h[i] - h[0]) / hspan for i in (1, 2, 3)]
    phase_error = [float(a - b) for a, b in zip(model_phase, human_phase)]
    phase_abs = [abs(x) for x in phase_error]

    model_legs = [(m[i + 1] - m[i]) / mspan for i in range(4)]
    human_legs = [(h[i + 1] - h[i]) / hspan for i in range(4)]
    leg_share_mae = sum(abs(a - b) for a, b in zip(model_legs, human_legs)) / 4.0

    return {
        "signed_anchor_displacement": d,
        "absolute_anchor_error": abs_d,
        "boundary_offset_disagreement": abs(d[0] - d[4]),
        "translation_estimate": t,
        "translation_residuals": residuals,
        "raw_anchor_mae_bars": raw_mae,
        "translation_removed_anchor_mae_bars": residual_mae,
        "translation_mae_reduction_fraction": reduction,
        "internal_phase_error": phase_error,
        "internal_phase_abs_error": phase_abs,
        "internal_phase_mae": sum(phase_abs) / 3.0,
        "center_pivot_abs_phase_error": phase_abs[1],
        "leg_share_mae": leg_share_mae,
        "start_abs_gt_end_abs": abs_d[0] > abs_d[4],
        "end_abs_gt_start_abs": abs_d[4] > abs_d[0],
        "max_boundary_abs_error": max(abs_d[0], abs_d[4]),
    }


def frozen_decision(rows: Sequence[dict]) -> dict:
    if not rows:
        raise ValueError("non-empty decomposition rows required")

    start_abs = [float(r["absolute_anchor_error"][0]) for r in rows]
    end_abs = [float(r["absolute_anchor_error"][4]) for r in rows]
    boundary_disagreement = [float(r["boundary_offset_disagreement"]) for r in rows]
    phase_mae = [float(r["internal_phase_mae"]) for r in rows]
    leg_mae = [float(r["leg_share_mae"]) for r in rows]
    reduction = [float(r["translation_mae_reduction_fraction"]) for r in rows]
    max_boundary = [float(r["max_boundary_abs_error"]) for r in rows]
    ordinal_phase_abs = [
        [float(r["internal_phase_abs_error"][i]) for r in rows] for i in range(3)
    ]

    rigid_translation = (
        median(boundary_disagreement) <= 6.0
        and median(phase_mae) <= 0.08
        and median(reduction) >= 0.50
        and median(max_boundary) >= 8.0
    )
    left_boundary = (
        median(start_abs) >= 10.0
        and median(end_abs) <= 6.0
        and median(phase_mae) <= 0.08
        and sum(bool(r["start_abs_gt_end_abs"]) for r in rows) >= 8
    )
    end_boundary = (
        median(end_abs) >= 10.0
        and median(start_abs) <= 6.0
        and median(phase_mae) <= 0.08
        and sum(bool(r["end_abs_gt_start_abs"]) for r in rows) >= 8
    )
    internal_phase = (
        median(phase_mae) > 0.12
        or sum(median(vals) > 0.12 for vals in ordinal_phase_abs) >= 2
    )
    mixed = internal_phase and median(max_boundary) >= 10.0
    internal_geometry = median(phase_mae) <= 0.08 and median(leg_mae) <= 0.08

    if rigid_translation:
        category = "v0651_rigid_translation_dominant"
    elif left_boundary:
        category = "v0651_left_boundary_definition_dominant"
    elif end_boundary:
        category = "v0651_end_boundary_definition_dominant"
    elif mixed:
        category = "v0651_mixed_boundary_and_internal_pivot_mismatch"
    elif internal_phase:
        category = "v0651_internal_pivot_phase_mismatch_dominant"
    elif internal_geometry:
        category = "v0651_internal_geometry_corresponds_boundary_representation_unresolved"
    else:
        category = "v0651_correspondence_decomposition_mixed_or_unresolved"

    return {
        "rigid_translation_dominant": rigid_translation,
        "left_boundary_dominant": left_boundary,
        "end_boundary_dominant": end_boundary,
        "internal_pivot_phase_mismatch": internal_phase,
        "mixed_boundary_and_internal_mismatch": mixed,
        "internal_geometry_corresponds_after_boundary_normalization": internal_geometry,
        "primary_category": category,
    }


def summarize_decomposition(rows: Sequence[dict]) -> dict:
    if not rows:
        raise ValueError("non-empty decomposition rows required")
    per_anchor = {}
    for i in range(5):
        signed = [float(r["signed_anchor_displacement"][i]) for r in rows]
        absolute = [float(r["absolute_anchor_error"][i]) for r in rows]
        per_anchor[f"p{i}"] = {
            "signed_displacement": _summary(signed),
            "absolute_error": _summary(absolute),
            "sign_incidence": _sign_incidence(signed),
        }

    phase = {}
    for j, ordinal in enumerate((1, 2, 3)):
        signed = [float(r["internal_phase_error"][j]) for r in rows]
        absolute = [float(r["internal_phase_abs_error"][j]) for r in rows]
        phase[f"p{ordinal}"] = {
            "signed_phase_error": _summary(signed),
            "absolute_phase_error": _summary(absolute),
            "sign_incidence": _sign_incidence(signed),
        }

    aggregate = {
        "anchored_cases": len(rows),
        "per_anchor": per_anchor,
        "boundary_offset_disagreement_bars": _summary(
            [float(r["boundary_offset_disagreement"]) for r in rows]
        ),
        "translation": {
            "raw_anchor_mae_bars": _summary([float(r["raw_anchor_mae_bars"]) for r in rows]),
            "translation_removed_anchor_mae_bars": _summary(
                [float(r["translation_removed_anchor_mae_bars"]) for r in rows]
            ),
            "mae_reduction_fraction": _summary(
                [float(r["translation_mae_reduction_fraction"]) for r in rows]
            ),
        },
        "internal_phase": {
            "per_ordinal": phase,
            "internal_phase_mae": _summary([float(r["internal_phase_mae"]) for r in rows]),
            "center_pivot_abs_phase_error": _summary(
                [float(r["center_pivot_abs_phase_error"]) for r in rows]
            ),
            "leg_share_mae": _summary([float(r["leg_share_mae"]) for r in rows]),
        },
        "boundary_asymmetry_incidence": {
            "start_abs_gt_end_abs_count": sum(bool(r["start_abs_gt_end_abs"]) for r in rows),
            "end_abs_gt_start_abs_count": sum(bool(r["end_abs_gt_start_abs"]) for r in rows),
            "equal_abs_count": sum(
                float(r["absolute_anchor_error"][0]) == float(r["absolute_anchor_error"][4])
                for r in rows
            ),
        },
        "max_boundary_abs_error_bars": _summary(
            [float(r["max_boundary_abs_error"]) for r in rows]
        ),
    }
    aggregate["frozen_decision"] = frozen_decision(rows)
    aggregate["primary_category"] = aggregate["frozen_decision"]["primary_category"]
    return aggregate
