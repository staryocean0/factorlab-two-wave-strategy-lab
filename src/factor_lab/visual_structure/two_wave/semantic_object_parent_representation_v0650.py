"""Frozen aggregate metrics for v0.6.50 semantic-object / parent-representation audit."""
from __future__ import annotations

from collections import Counter
from statistics import median
from typing import Iterable, Sequence

SCHEMA = "two_wave_semantic_object_parent_representation@0.6.50"
LOOKBACK_BARS = 96


def rank_probability(a: Sequence[float], b: Sequence[float]) -> float:
    """P(A>B)+0.5*P(A=B), exact finite-sample rank probability."""
    if not a or not b:
        raise ValueError("two non-empty samples required")
    wins = ties = 0
    for x in a:
        for y in b:
            if x > y:
                wins += 1
            elif x == y:
                ties += 1
    return (wins + 0.5 * ties) / (len(a) * len(b))


def canonical_identity(rows: Sequence[dict]) -> dict:
    if not rows:
        raise ValueError("at least one qualified identity required")
    return sorted(
        rows,
        key=lambda r: (
            tuple(int(x) for x in r["published_raw_occurrence_bars"]),
            str(r["phase"]),
        ),
    )[0]


def visible_anchor_positions(raw: Sequence[int], cutoff: int) -> list[int]:
    anchors = [int(x) for x in raw]
    if len(anchors) != 5 or any(b <= a for a, b in zip(anchors, anchors[1:])):
        raise ValueError("five strictly increasing model anchors required")
    start = int(cutoff) - (LOOKBACK_BARS - 1)
    return [x - start for x in anchors]


def full_visibility(positions: Sequence[int]) -> bool:
    if len(positions) != 5:
        raise ValueError("five visible positions required")
    return all(0 <= int(x) < LOOKBACK_BARS for x in positions)


def parse_human_anchors(row: dict) -> list[int] | None:
    if str(row.get("two_complete_same_scale_waves", "")) != "yes":
        return None
    vals = []
    for key in ("p0", "p1", "p2", "p3", "p4"):
        text = str(row.get(key, "")).strip()
        if text == "":
            return None
        try:
            value = int(text)
        except ValueError:
            return None
        vals.append(value)
    if any(x < 0 or x >= LOOKBACK_BARS for x in vals):
        return None
    if any(b <= a for a, b in zip(vals, vals[1:])):
        return None
    return vals


def interval_iou(a0: int, a1: int, b0: int, b1: int) -> float:
    if not (a0 < a1 and b0 < b1):
        raise ValueError("strict intervals required")
    inter = max(0, min(a1, b1) - max(a0, b0))
    union = max(a1, b1) - min(a0, b0)
    return inter / union if union else 0.0


def containment_category(model: Sequence[int], human: Sequence[int]) -> str:
    m0, m4 = int(model[0]), int(model[-1])
    h0, h4 = int(human[0]), int(human[-1])
    if m0 == h0 and m4 == h4:
        return "mutual_equal_boundaries"
    if m0 >= h0 and m4 <= h4:
        return "model_inside_human"
    if h0 >= m0 and h4 <= m4:
        return "human_inside_model"
    if min(m4, h4) > max(m0, h0):
        return "partial_overlap"
    return "disjoint"


def anchor_alignment(model: Sequence[int], human: Sequence[int]) -> dict:
    if len(model) != 5 or len(human) != 5:
        raise ValueError("five model and five human anchors required")
    errors = [abs(int(m) - int(h)) for m, h in zip(model, human)]
    mspan = int(model[-1]) - int(model[0])
    hspan = int(human[-1]) - int(human[0])
    if mspan <= 0 or hspan <= 0:
        raise ValueError("positive model/human spans required")
    return {
        "anchor_mae_bars": sum(errors) / 5.0,
        "anchor_mae_fraction": (sum(errors) / 5.0) / (LOOKBACK_BARS - 1),
        "start_boundary_abs_error_bars": abs(int(model[0]) - int(human[0])),
        "end_boundary_abs_error_bars": abs(int(model[-1]) - int(human[-1])),
        "interval_iou": interval_iou(int(model[0]), int(model[-1]), int(human[0]), int(human[-1])),
        "span_ratio": max(mspan, hspan) / min(mspan, hspan),
        "containment": containment_category(model, human),
    }


def summarize_alignment(rows: Sequence[dict]) -> dict:
    if not rows:
        return {
            "usable_human_anchor_cases": 0,
            "anchor_correspondence_status": "insufficient_frozen_human_anchor_coverage",
            "containment_counts": {},
        }
    ious = [float(x["interval_iou"]) for x in rows]
    maes = [float(x["anchor_mae_fraction"]) for x in rows]
    ratios = [float(x["span_ratio"]) for x in rows]
    counts = Counter(str(x["containment"]) for x in rows)
    n = len(rows)
    identified = n >= 8
    if not identified:
        status = "insufficient_frozen_human_anchor_coverage"
    elif median(ious) >= 0.70 and median(maes) <= 0.08:
        status = "strong_correspondence"
    elif median(ious) < 0.50 or median(maes) > 0.15:
        status = "strong_boundary_mismatch"
    else:
        status = "mixed_or_indeterminate"
    return {
        "usable_human_anchor_cases": n,
        "anchor_correspondence_identified": identified,
        "anchor_correspondence_status": status,
        "median_interval_iou": median(ious),
        "median_anchor_mae_fraction": median(maes),
        "median_span_ratio": median(ratios),
        "median_start_boundary_abs_error_bars": median(float(x["start_boundary_abs_error_bars"]) for x in rows),
        "median_end_boundary_abs_error_bars": median(float(x["end_boundary_abs_error_bars"]) for x in rows),
        "containment_counts": dict(counts),
        "containment_incidence": {k: v / n for k, v in counts.items()},
    }


def frozen_decision(
    *,
    no_not_visible_incidence: float,
    yes_not_visible_incidence: float,
    right_edge_gap_rank_no_gt_yes: float,
    span_fraction_rank_no_lt_yes: float,
    alignment: dict,
) -> dict:
    visibility_failure = (
        no_not_visible_incidence >= 0.25
        and no_not_visible_incidence - yes_not_visible_incidence >= 0.20
    )
    stale = right_edge_gap_rank_no_gt_yes >= 0.70
    smaller_parent = span_fraction_rank_no_lt_yes >= 0.70

    identified = bool(alignment.get("anchor_correspondence_identified", False))
    status = str(alignment.get("anchor_correspondence_status", "insufficient_frozen_human_anchor_coverage"))
    span_ratio = alignment.get("median_span_ratio")
    incidence = alignment.get("containment_incidence", {}) or {}
    model_fragment = bool(
        identified
        and incidence.get("model_inside_human", 0.0) >= 0.60
        and span_ratio is not None
        and float(span_ratio) >= 1.25
    )
    model_overwide = bool(
        identified
        and incidence.get("human_inside_model", 0.0) >= 0.60
        and span_ratio is not None
        and float(span_ratio) >= 1.25
    )

    if visibility_failure:
        category = "v0650_packet_window_visibility_failure"
    elif stale:
        category = "v0650_algorithmic_object_stale_at_reference_cutoff"
    elif smaller_parent and ((not identified) or model_fragment):
        category = "v0650_algorithmic_parent_fragment_sizing_supported"
    elif status == "strong_boundary_mismatch":
        category = "v0650_direct_parent_boundary_mismatch"
    elif status == "strong_correspondence" and not smaller_parent:
        category = "v0650_algorithmic_and_human_parent_correspondence_supported_but_presence_semantics_still_fail"
    else:
        category = "v0650_parent_representation_correspondence_not_identified"

    return {
        "packet_window_visibility_failure": visibility_failure,
        "right_edge_staleness_supported": stale,
        "smaller_parent_size_supported": smaller_parent,
        "model_fragment_of_human_parent": model_fragment,
        "model_overwide_relative_to_human_parent": model_overwide,
        "primary_category": category,
    }
