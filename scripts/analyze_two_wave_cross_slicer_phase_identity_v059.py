from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Iterable

MECHANICAL_MAX_OCCURRENCE_DELTA_MINUTES = 10.0
TARGET_CATEGORY = "D2_harm"
TARGET_SHARED_D1 = "uncertain"
LOCALITY_SWEEP_MINUTES = (
    1.0,
    3.0,
    5.0,
    6.0,
    10.0,
    15.0,
    30.0,
    60.0,
    120.0,
    240.0,
    480.0,
    1200.0,
)


def weighted_quantile(values: Iterable[float], weights: Iterable[int], q: float) -> float | None:
    pairs = sorted(
        (float(v), int(w))
        for v, w in zip(values, weights)
        if math.isfinite(float(v)) and int(w) > 0
    )
    if not pairs:
        return None
    total = sum(w for _, w in pairs)
    threshold = q * total
    running = 0
    for value, weight in pairs:
        running += weight
        if running >= threshold:
            return value
    return pairs[-1][0]


def stats(rows: list[dict]) -> dict:
    bars = sum(int(r["bars"]) for r in rows)
    if not rows or bars <= 0:
        return {
            "pairs": len(rows),
            "bars": bars,
            "large_margin_flip_pairs": 0,
            "large_margin_flip_bars": 0,
            "large_margin_flip_fraction": None,
            "ordinary_flip_fraction": None,
            "phase_match_fraction": None,
            "weighted_median_abs_delta_T": None,
            "weighted_median_D_endpoint": None,
            "weighted_median_occurrence_delta_minutes": None,
            "weighted_median_birth_scale_level_abs_delta": None,
        }
    lm_rows = [r for r in rows if bool(r["large_margin_scalar_sign_flip"])]
    ordinary_rows = [r for r in rows if bool(r["ordinary_scalar_sign_flip"])]
    phase_rows = [r for r in rows if bool(r["phase_match"])]
    weights = [int(r["bars"]) for r in rows]
    return {
        "pairs": len(rows),
        "bars": bars,
        "large_margin_flip_pairs": len(lm_rows),
        "large_margin_flip_bars": sum(int(r["bars"]) for r in lm_rows),
        "large_margin_flip_fraction": sum(int(r["bars"]) for r in lm_rows) / bars,
        "ordinary_flip_fraction": sum(int(r["bars"]) for r in ordinary_rows) / bars,
        "phase_match_fraction": sum(int(r["bars"]) for r in phase_rows) / bars,
        "weighted_median_abs_delta_T": weighted_quantile(
            [r["abs_delta_T"] for r in rows], weights, 0.5
        ),
        "weighted_median_D_endpoint": weighted_quantile(
            [r["D_endpoint"] for r in rows], weights, 0.5
        ),
        "weighted_median_occurrence_delta_minutes": weighted_quantile(
            [r["max_occurrence_timestamp_abs_delta_minutes"] for r in rows], weights, 0.5
        ),
        "weighted_median_birth_scale_level_abs_delta": weighted_quantile(
            [r["birth_scale_level_abs_delta"] for r in rows], weights, 0.5
        ),
    }


def stratify(rows: list[dict], threshold: float) -> dict:
    aligned = [
        r
        for r in rows
        if float(r["max_occurrence_timestamp_abs_delta_minutes"]) <= threshold
    ]
    dislocated = [
        r
        for r in rows
        if float(r["max_occurrence_timestamp_abs_delta_minutes"]) > threshold
    ]
    total = stats(rows)
    a = stats(aligned)
    d = stats(dislocated)
    bars = total["bars"] or 0
    return {
        "total": total,
        "phase_consistent_proxy": a,
        "anchor_dislocated_proxy": d,
        "phase_consistent_bar_fraction": (a["bars"] / bars) if bars else None,
        "anchor_dislocated_bar_fraction": (d["bars"] / bars) if bars else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pair_details", type=Path, help="v0.5.8 PAWCT pair_details.json")
    ap.add_argument(
        "--geometry-pair-details",
        type=Path,
        required=True,
        help="v0.5.7b geometry pair_details.json",
    )
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument(
        "--max-occurrence-delta-minutes",
        type=float,
        default=MECHANICAL_MAX_OCCURRENCE_DELTA_MINUTES,
    )
    args = ap.parse_args()

    payload = json.loads(args.pair_details.read_text())
    rows = list(payload["rows"])
    geometry_payload = json.loads(args.geometry_pair_details.read_text())
    geometry_rows = list(geometry_payload["rows"])
    geometry_by_key = {
        (r["view"], r["main_record_id"], r["other_record_id"]): r
        for r in geometry_rows
    }
    if len(geometry_by_key) != len(geometry_rows):
        raise AssertionError("v0.5.7b geometry pair keys are not unique")
    if any(
        (r["view"], r["main_record_id"], r["other_record_id"]) not in geometry_by_key
        for r in rows
    ):
        raise AssertionError("v0.5.8 PAWCT pair is missing from v0.5.7b geometry evidence")

    # Enrich the PAWCT rows with the exact occurrence-time displacement evidence.
    for r in rows:
        g = geometry_by_key[(r["view"], r["main_record_id"], r["other_record_id"])]
        deltas = [float(x) for x in g["occurrence_timestamp_abs_delta_minutes"]]
        if len(deltas) != 5:
            raise AssertionError("expected five occurrence timestamp deltas")
        r["occurrence_timestamp_abs_delta_minutes"] = deltas
        r["max_occurrence_timestamp_abs_delta_minutes"] = max(deltas)

    threshold = float(args.max_occurrence_delta_minutes)
    if threshold != MECHANICAL_MAX_OCCURRENCE_DELTA_MINUTES:
        raise ValueError("v0.5.9 frozen exploratory partition remains 10 minutes")

    groups = {
        "all": rows,
        "D1_uncertain_D2_harm": [
            r
            for r in rows
            if r["category"] == TARGET_CATEGORY and r.get("shared_D1") == TARGET_SHARED_D1
        ],
        "D2_help": [r for r in rows if r["category"] == "D2_help"],
        "both_agree": [r for r in rows if r["category"] == "both_agree"],
        "both_disagree": [r for r in rows if r["category"] == "both_disagree"],
    }

    result = {
        "schema": "two_wave_cross_slicer_phase_identity_attribution@0.5.9",
        "status": "post_v058_attribution_not_morphology_acceptance",
        "source_schema": payload.get("schema"),
        "geometry_source_schema": geometry_payload.get("schema"),
        "mechanical_phase_consistency_proxy": {
            "metric": "max_occurrence_timestamp_abs_delta_minutes",
            "threshold_minutes": threshold,
            "basis": (
                "Ten minutes is retained only as the frozen exploratory partition from the first "
                "v0.5.9 audit. The threshold-free failure displacement and the full locality sweep "
                "are also reported so no favorable cutoff is selected."
            ),
        },
        "groups": {name: stratify(group_rows, threshold) for name, group_rows in groups.items()},
        "per_view_target": {},
        "future_outcome_used": False,
        "trade_authority": False,
    }

    target = groups["D1_uncertain_D2_harm"]
    for view in sorted({r["view"] for r in target}):
        result["per_view_target"][view] = stratify(
            [r for r in target if r["view"] == view], threshold
        )

    all_total = result["groups"]["all"]["total"]
    all_aligned = result["groups"]["all"]["phase_consistent_proxy"]
    all_dislocated = result["groups"]["all"]["anchor_dislocated_proxy"]
    target_aligned = result["groups"]["D1_uncertain_D2_harm"]["phase_consistent_proxy"]
    target_dislocated = result["groups"]["D1_uncertain_D2_harm"]["anchor_dislocated_proxy"]
    flip_total = int(all_total["large_margin_flip_bars"])

    pattern_bars = {}
    target_pattern_bars = {}
    target_anchor_gt10_bars = [0, 0, 0, 0, 0]
    target_bars = sum(int(r["bars"]) for r in groups["D1_uncertain_D2_harm"])
    flip_pattern_bars = {}
    for r in rows:
        deltas = list(r["occurrence_timestamp_abs_delta_minutes"])
        pattern = "".join("1" if x > threshold else "0" for x in deltas)
        pattern_bars[pattern] = pattern_bars.get(pattern, 0) + int(r["bars"])
        if r["category"] == TARGET_CATEGORY and r.get("shared_D1") == TARGET_SHARED_D1:
            target_pattern_bars[pattern] = target_pattern_bars.get(pattern, 0) + int(r["bars"])
            for i, x in enumerate(deltas):
                if x > threshold:
                    target_anchor_gt10_bars[i] += int(r["bars"])
        if bool(r["large_margin_scalar_sign_flip"]):
            flip_pattern_bars[pattern] = flip_pattern_bars.get(pattern, 0) + int(r["bars"])

    result["anchor_pattern_attribution"] = {
        "pattern_semantics": "five-character 0/1 string; 1 means that occurrence anchor differs by >10 minutes",
        "all_pattern_bars": dict(sorted(pattern_bars.items(), key=lambda kv: (-kv[1], kv[0]))),
        "target_pattern_bars": dict(
            sorted(target_pattern_bars.items(), key=lambda kv: (-kv[1], kv[0]))
        ),
        "large_margin_flip_pattern_bars": dict(
            sorted(flip_pattern_bars.items(), key=lambda kv: (-kv[1], kv[0]))
        ),
        "target_anchor_gt10_bar_fraction_by_position": [
            x / target_bars for x in target_anchor_gt10_bars
        ],
    }

    def flip_anchor_summary(group_rows: list[dict]) -> dict:
        flips = [r for r in group_rows if bool(r["large_margin_scalar_sign_flip"])]
        if not flips:
            return {"pairs": 0, "bars": 0}
        weights = [int(r["bars"]) for r in flips]
        vals = [float(r["max_occurrence_timestamp_abs_delta_minutes"]) for r in flips]
        return {
            "pairs": len(flips),
            "bars": sum(weights),
            "minimum_max_anchor_delta_minutes": min(vals),
            "weighted_q10_max_anchor_delta_minutes": weighted_quantile(vals, weights, 0.10),
            "weighted_q25_max_anchor_delta_minutes": weighted_quantile(vals, weights, 0.25),
            "weighted_median_max_anchor_delta_minutes": weighted_quantile(vals, weights, 0.50),
            "weighted_q75_max_anchor_delta_minutes": weighted_quantile(vals, weights, 0.75),
            "maximum_max_anchor_delta_minutes": max(vals),
        }

    result["threshold_free_large_margin_flip_anchor_displacement"] = {
        "all": flip_anchor_summary(groups["all"]),
        "D1_uncertain_D2_harm": flip_anchor_summary(groups["D1_uncertain_D2_harm"]),
    }
    result["locality_sweep"] = {
        str(int(t) if float(t).is_integer() else t): {
            "all": stratify(groups["all"], float(t)),
            "D1_uncertain_D2_harm": stratify(
                groups["D1_uncertain_D2_harm"], float(t)
            ),
        }
        for t in LOCALITY_SWEEP_MINUTES
    }

    result["attribution_summary"] = {
        "all_large_margin_flip_bars": flip_total,
        "all_large_margin_flip_bars_phase_consistent": int(
            all_aligned["large_margin_flip_bars"]
        ),
        "all_large_margin_flip_bars_anchor_dislocated": int(
            all_dislocated["large_margin_flip_bars"]
        ),
        "all_large_margin_flip_fraction_localized_to_dislocated": (
            all_dislocated["large_margin_flip_bars"] / flip_total if flip_total else None
        ),
        "target_phase_consistent_bar_fraction": result["groups"]["D1_uncertain_D2_harm"][
            "phase_consistent_bar_fraction"
        ],
        "target_anchor_dislocated_bar_fraction": result["groups"]["D1_uncertain_D2_harm"][
            "anchor_dislocated_bar_fraction"
        ],
        "target_large_margin_flip_fraction_phase_consistent": target_aligned[
            "large_margin_flip_fraction"
        ],
        "target_large_margin_flip_fraction_anchor_dislocated": target_dislocated[
            "large_margin_flip_fraction"
        ],
        "target_weighted_median_abs_delta_T_phase_consistent": target_aligned[
            "weighted_median_abs_delta_T"
        ],
        "target_weighted_median_abs_delta_T_anchor_dislocated": target_dislocated[
            "weighted_median_abs_delta_T"
        ],
        "target_weighted_median_D_endpoint_phase_consistent": target_aligned[
            "weighted_median_D_endpoint"
        ],
        "target_weighted_median_D_endpoint_anchor_dislocated": target_dislocated[
            "weighted_median_D_endpoint"
        ],
    }

    result["research_conclusion"] = (
        "observed_large_margin_direction_instability_is_conditioned_on_cross_slicer_anchor_dislocation; "
        "separate_financial_event_identity_from_exclusive_packing_before_another_direction_formula"
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result["attribution_summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
