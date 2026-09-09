"""Auditable, shared-calendar block uncertainty for morphology references.

This supplements the frozen evaluation protocol; it never grants acceptance.
Object matches are computed once per scoring block, using the existing matcher.
Resampling weights apply to whole blocks, including their negative windows.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

from .annotations import LABELS, _evaluate_kind, _prediction_records, validate_annotation_document

SCHEMA_VERSION = "two_wave_block_uncertainty@1.0"
SEED = 20260905
RESAMPLES = 2000
MIN_BLOCKS = 5
_SHANGHAI = ZoneInfo("Asia/Shanghai")
_KINDS = ("structure", "cycle")
_METRICS = {
    "structure": ("precision", "recall", "macro_f1", "classification_coverage", "reference_clear_classification_coverage"),
    "cycle": ("precision", "recall"),
}


def _day(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("Calendar boundaries must be ISO dates or timezone-aware timestamps")
    if len(value) == 10:
        return date.fromisoformat(value).isoformat()
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Calendar timestamps must be timezone-aware")
    return parsed.astimezone(_SHANGHAI).date().isoformat()


def build_calendar_blocks(windows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Merge all overlapping calendar cores, including transitive/cross-year links.

    Each window needs a unique window_id, product_id, scale_id, start_time and
    end_time. Time boundaries may be timezone-aware timestamps or ISO dates.
    A block is never split at a year boundary or copied for another product.
    Same-day intervals merge conservatively, even when intraday cores differ.
    """
    prepared, seen = [], set()
    for window in windows:
        item = dict(window)
        for key in ("window_id", "product_id", "scale_id"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f"Every calendar window needs {key}")
        if item["window_id"] in seen:
            raise ValueError("window_id must be unique in the calendar cohort")
        seen.add(item["window_id"])
        item["start_day"] = _day(item["start_time"])
        item["end_day"] = _day(item["end_time"])
        if item["start_day"] > item["end_day"]:
            raise ValueError("Calendar window starts after it ends")
        item["years"] = list(range(int(item["start_day"][:4]), int(item["end_day"][:4]) + 1))
        prepared.append(item)
    groups: list[list[dict[str, Any]]] = []
    end = ""
    for item in sorted(prepared, key=lambda w: (w["start_day"], w["end_day"], w["window_id"])):
        if not groups or item["start_day"] > end:
            groups.append([])
            end = item["end_day"]
        groups[-1].append(item)
        end = max(end, item["end_day"])
    blocks, window_to_block = [], {}
    for members in groups:
        start, end = min(w["start_day"] for w in members), max(w["end_day"] for w in members)
        identity = f"calendar_{start}_{end}"
        participation = sorted({
            (w["product_id"], w.get("config_id", ""), w["scale_id"], year)
            for w in members for year in w["years"]
        })
        blocks.append({
            "block_id": identity,
            "start_day": start,
            "end_day": end,
            "window_ids": sorted(w["window_id"] for w in members),
            "participation": [list(p) for p in participation],
            "product_count": len({w["product_id"] for w in members}),
            "year_count": len({year for w in members for year in w["years"]}),
        })
        window_to_block.update({w["window_id"]: identity for w in members})
    return {
        "calendar_resolution": "Asia/Shanghai inclusive calendar days; no within-day independence assumed",
        "input_window_count": len(prepared),
        "block_count": len(blocks),
        "blocks": blocks,
        "window_to_block": window_to_block,
        "independence_note": "Disjoint calendar blocks are resampling units, not proof of temporal independence.",
    }


def shared_block_weights(blocks: Sequence[Mapping[str, Any]]) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """2,000 common multinomial draws; exact product/scale/year block margins.

    Stratifying by the entire participation signature couples shared products.
    Drawing separately for each product would break this property. A cross-year
    block stays intact in one signature, carrying all of its yearly cells.
    """
    groups: dict[str, list[int]] = defaultdict(list)
    for index, block in enumerate(blocks):
        signature = json.dumps(sorted(block["participation"]), separators=(",", ":"))
        groups[signature].append(index)
    weights = np.zeros((RESAMPLES, len(blocks)), dtype=np.int64)
    strata = []
    for signature, indices in sorted(groups.items()):
        # A stable substream makes invocation order and unrelated strata irrelevant.
        digest = hashlib.sha256(f"{SEED}/{signature}".encode()).digest()
        rng = np.random.default_rng(int.from_bytes(digest[:8], "big"))
        weights[:, indices] = rng.multinomial(len(indices), np.full(len(indices), 1 / len(indices)), size=RESAMPLES)
        strata.append({
            "participation": json.loads(signature),
            "block_ids": [blocks[i]["block_id"] for i in indices],
            "block_count": len(indices),
        })
    return weights, strata


def _counts(report: Mapping[str, Any], kind: str) -> np.ndarray:
    values = [report["reviewed_prediction_count"], report["reviewed_reference_count"], report["matched_count"]]
    if kind == "structure":
        confusion = report["confusion_matrix"]
        clear = sum(confusion[truth][pred] for truth in LABELS for pred in LABELS[:3])
        clear += sum(report["unmatched_prediction_class_counts"][label] for label in LABELS[:3])
        values.extend([clear, sum(confusion[t][p] for t in LABELS for p in LABELS[:3])])
        values.extend(confusion[t][p] for t in LABELS for p in (*LABELS, "not_detected"))
        values.extend(report["unmatched_prediction_class_counts"][p] for p in LABELS)
    return np.asarray(values, dtype=np.int64)


def _metrics(counts: np.ndarray, kind: str) -> dict[str, float | None]:
    predictions, references, matched = (int(x) for x in counts[:3])
    result = {"precision": matched / predictions if predictions else None, "recall": matched / references if references else None}
    if kind == "cycle":
        return result
    confusion, unmatched = counts[5:25].reshape(4, 5), counts[25:29]
    f1s = []
    for label in range(3):
        actual, predicted = int(confusion[label].sum()), int(confusion[:, label].sum() + unmatched[label])
        f1s.append(2 * int(confusion[label, label]) / (actual + predicted) if actual + predicted else 0.0)
    result.update(
        macro_f1=sum(f1s) / 3 if predictions or references else None,
        classification_coverage=int(counts[3]) / predictions if predictions else None,
        reference_clear_classification_coverage=int(counts[4]) / references if references else None,
    )
    return result


def _raw_counts(counts: np.ndarray, kind: str) -> dict[str, Any]:
    result = dict(zip(("prediction_count", "reference_observation_count", "matched_count"), map(int, counts[:3]), strict=True))
    result["missed_count"] = result["reference_observation_count"] - result["matched_count"]
    result["unmatched_prediction_count"] = result["prediction_count"] - result["matched_count"]
    if kind == "structure":
        confusion = counts[5:25].reshape(4, 5)
        result["confusion_matrix"] = {
            truth: {pred: int(confusion[ti, pi]) for pi, pred in enumerate((*LABELS, "not_detected"))}
            for ti, truth in enumerate(LABELS)
        }
        result["unmatched_prediction_class_counts"] = dict(zip(LABELS, map(int, counts[25:29]), strict=True))
    return result


def _identity(record: Mapping[str, Any]) -> tuple[str, str, str]:
    return tuple(record.get(key, "") for key in ("config_id", "timeframe", "scale_id"))


def _check_explicit_provenance(document: Mapping[str, Any]) -> None:
    """A human-looking name cannot override explicit evidence of nonindependence."""
    for window in document["review_windows"]:
        for key in ("fully_reviewed", "complete_reviewed"):
            if key in window and not isinstance(window[key], bool):
                raise ValueError("Complete review declarations must be booleans, never strings or numeric flags")
        if "fully_reviewed" in window and "complete_reviewed" in window and window["fully_reviewed"] != window["complete_reviewed"]:
            raise ValueError("Conflicting complete review declarations")
    for record in (document, *document["annotations"], *document["review_windows"]):
        provenance = record.get("provenance", {})
        if not isinstance(provenance, Mapping):
            raise ValueError("Invalid reference provenance; repair and retain a new reference version")
        source = provenance.get("source_type")
        if source not in (None, "", "independent_human"):
            raise ValueError("Explicit nonindependent reference source_type cannot be scored")
        if record.get("algorithm_visible", False) or record.get("independent_reference", True) is False:
            raise ValueError("Explicit nonindependent or algorithm-visible reference cannot be scored")
        if provenance.get("blinded_to_algorithm") is False or provenance.get("independent_of_other_reviewer") is False:
            raise ValueError("Explicit nonindependent or unblinded reference provenance cannot be scored")
        if record.get("reference_mode", document.get("reference_mode")) == "online":
            inherited = document.get("provenance", {})
            clock = provenance.get("online_clock", inherited.get("online_clock"))
            if clock not in (None, "", "bar_end"):
                raise ValueError("Unsupported online_clock: this evaluator supports bar_end ideal-prefix references only")
            if provenance.get("future_exposed", inherited.get("future_exposed")) is True:
                raise ValueError("Explicit future_exposed online reference cannot be scored")


def _prepare_runs(runs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    prepared, identities = [], set()
    for run in runs:
        product = run.get("product_id")
        if not isinstance(product, str) or not product.strip():
            raise ValueError("Each run needs the full DataHub product_id, including actual frequency/offset identity")
        export, bars = run["export"], run["bars"]
        identity = (export.get("config_hash", ""), export.get("config", {}).get("timeframe", ""), export.get("scale_id", ""))
        run_key = (product, *identity)
        if run_key in identities:
            raise ValueError("Duplicate product/config/timeframe/scale run; combine its references before evaluation")
        identities.add(run_key)
        days = [_day(bar["timestamp"]) for bar in bars]
        if any(a > b for a, b in zip(days, days[1:], strict=False)):
            raise ValueError("Bar calendar days must be ordered")
        if any(bar.get("trading_day", day) != day for bar, day in zip(bars, days, strict=True)):
            raise ValueError("trading_day must agree with Shanghai calendar date")
        document = run.get("annotations")
        normalized = validate_annotation_document(document) if document is not None else {"annotations": [], "review_windows": []}
        _check_explicit_provenance(normalized)
        references = [r for r in normalized["annotations"] if r["independent_reference"] and _identity(r) == identity]
        # Repeated online cutoffs are distinct observations, but same-prefix duplicate
        # drawings must be reconciled before matching rather than inflating support.
        seen = set()
        for reference in references:
            key = (reference["reference_mode"], reference["kind"], reference["phase"], tuple(reference["pivot_indices"]))
            if reference["reference_mode"] == "online":
                key += (reference["visible_cutoff"],)
            if key in seen:
                raise ValueError("Duplicate reference geometry requires deduplication or human adjudication")
            seen.add(key)
        windows = [dict(w) for w in normalized["review_windows"] if _identity(w) == identity]
        run_id = hashlib.sha256(json.dumps(run_key).encode()).hexdigest()[:16]
        for index, window in enumerate(windows):
            if window["visible_cutoff"] >= len(bars):
                raise ValueError("Review window cutoff exceeds supplied bar history")
            window.update(
                window_id=f"{run_id}:{window['reference_mode']}:{index}",
                source_window_id=window.get("window_id"),
                product_id=product,
                start_time=days[window["start_index"]],
                end_time=days[window["end_index"]],
            )
        prepared.append({
            "run_id": run_id, "product_id": product, "identity": identity, "days": days,
            "references": references, "windows": windows,
            "predictions": {kind: _prediction_records(export, kind) for kind in _KINDS},
        })
    return sorted(prepared, key=lambda run: (run["product_id"], run["identity"]))


def _annual_windows(run: Mapping[str, Any], windows: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = defaultdict(list)
    days = run["days"]
    for window in windows:
        start, last = window["start_index"], window["end_index"]
        while start <= last:
            year, end = int(days[start][:4]), start
            while end + 1 <= last and int(days[end + 1][:4]) == year:
                end += 1
            result[year].append(dict(window, start_index=start, end_index=end))
            start = end + 1
    return result


def _summary(
    cells: np.ndarray, point: np.ndarray, kind: str, blocks: list[dict[str, Any]], weights: np.ndarray,
    sampling_strata: list[dict[str, Any]], relevant: set[str], min_blocks: int, common_reasons: list[str],
) -> dict[str, Any]:
    reasons = list(common_reasons)
    if int(point[1]) == 0:
        reasons.append("no_scored_independent_reference_objects")
    if len(relevant) < min_blocks:
        reasons.append("fewer_than_minimum_calendar_blocks")
    sparse = [s for s in sampling_strata if set(s["block_ids"]) & relevant and s["block_count"] < min_blocks]
    if sparse:
        reasons.append("sparse_joint_product_scale_year_participation_stratum")
    estimates = _metrics(point, kind)
    interval = {metric: None for metric in _METRICS[kind]}
    valid_counts = {metric: 0 for metric in _METRICS[kind]}
    metric_reasons: dict[str, str] = {}
    if not reasons:
        samples = [_metrics(row, kind) for row in weights @ cells]
        for metric in interval:
            values = [sample[metric] for sample in samples if sample[metric] is not None]
            valid_counts[metric] = len(values)
            if estimates[metric] is None or len(values) != RESAMPLES:
                metric_reasons[metric] = "undefined_point_or_resampled_denominator; undefined_draws_are_not_dropped"
            else:
                interval[metric] = [float(v) for v in np.quantile(values, [0.025, 0.975], method="linear")]
    return {
        "counts": _raw_counts(point, kind),
        "point_estimates": estimates,
        "confidence_intervals_95": interval,
        "calendar_block_count": len(relevant),
        "calendar_block_ids": sorted(relevant),
        "ci_status": "withheld" if reasons else ("computed" if not metric_reasons else "partially_undefined"),
        "ci_withheld_reasons": sorted(set(reasons)),
        "metric_withheld_reasons": metric_reasons,
        "valid_resamples": valid_counts,
        "sparse_sampling_strata": sparse,
        "accepted": False,
    }


def evaluate_block_bootstrap(runs: Sequence[Mapping[str, Any]], *, min_blocks: int = MIN_BLOCKS) -> dict[str, Any]:
    """Evaluate separate offline/online block CIs for supplied independent labels.

    Each run is {product_id, export, bars, annotations}. ``annotations`` is the
    ordinary annotations@1.0 document, preferably the adjudicated reference.
    The full bar list is used only to map core indices to dates, never as labels.
    No labels/incomplete review/sparse blocks produce null CIs with raw counts.
    """
    if not isinstance(min_blocks, int) or isinstance(min_blocks, bool) or min_blocks < 2:
        raise ValueError("min_blocks must be an integer at least 2")
    prepared = _prepare_runs(runs)
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "morphology_replication_not_yet_accepted",
        "authority": "research_only_no_hypothesis_or_trading_promotion",
        "bootstrap_implemented": True,
        "bootstrap_resamples": RESAMPLES,
        "seed": SEED,
        "seed_derivation": "sha256(seed/participation_signature) first 8 bytes big-endian; numpy default_rng",
        "numpy_version": np.__version__,
        "minimum_blocks_per_joint_stratum": min_blocks,
        "minimum_blocks_policy": "Supplementary conservative implementation assumption; not a numeric requirement frozen in protocol v0.1",
        "matching_tolerance_bars": 2,
        "reference_independence": "human_attribution_is_recorded_not_verified",
        "historical_point_in_time_status": "historical_PIT_not_verified",
        "sampling_unit": "merged_calendar_review_core_block",
        "pooling": "Object-count pooled descriptive metrics; products do not receive equal weight",
        "modes": {},
    }
    for mode in ("offline", "online"):
        declared = [w for run in prepared for w in run["windows"] if w["reference_mode"] == mode]
        reviewed = [w for w in declared if w.get("fully_reviewed", False)]
        plan = build_calendar_blocks(reviewed)
        blocks, lookup = plan["blocks"], plan["window_to_block"]
        weights, strata = shared_block_weights(blocks)
        block_index = {block["block_id"]: i for i, block in enumerate(blocks)}
        cells: dict[tuple[str, int, str], np.ndarray] = {}
        relevant: dict[tuple[str, int, str], set[str]] = defaultdict(set)
        global_counts = {kind: np.zeros(29 if kind == "structure" else 3, dtype=np.int64) for kind in _KINDS}
        mismatch = []
        for run in prepared:
            windows = [w for w in run["windows"] if w["reference_mode"] == mode and w.get("fully_reviewed", False)]
            refs = [r for r in run["references"] if r["reference_mode"] == mode]
            run_total = {kind: np.zeros_like(global_counts[kind]) for kind in _KINDS}
            for kind in _KINDS:
                kind_refs = [r for r in refs if r["kind"] == kind]
                primary = _counts(_evaluate_kind(run["predictions"][kind], kind_refs, windows, mode, kind, 2), kind)
                global_counts[kind] += primary
                for year, annual in _annual_windows(run, windows).items():
                    key = (run["run_id"], year, kind)
                    cells[key] = np.zeros((len(blocks), len(primary)), dtype=np.int64)
                    for identity in sorted({lookup[w["window_id"]] for w in annual}):
                        subset = [w for w in annual if lookup[w["window_id"]] == identity and w.get("kind", "structure") in (kind, "all")]
                        if not subset:
                            continue
                        relevant[key].add(identity)
                        count = _counts(_evaluate_kind(run["predictions"][kind], kind_refs, subset, mode, kind, 2), kind)
                        cells[key][block_index[identity]] = count
                        run_total[kind] += count
                if not np.array_equal(primary, run_total[kind]):
                    mismatch.append({
                        "run_id": run["run_id"], "kind": kind,
                        "global": primary.tolist(), "block_annual_sum": run_total[kind].tolist(),
                    })
        common_reasons = []
        if not reviewed:
            common_reasons.append("no_complete_reviewed_windows")
        if mismatch:
            common_reasons.append("global_matching_not_additive_across_block_or_annual_boundaries")
        pooled, by_product_year = {}, []
        for kind in _KINDS:
            matrix = np.zeros((len(blocks), len(global_counts[kind])), dtype=np.int64)
            relevant_all: set[str] = set()
            for key in cells:
                if key[2] == kind:
                    matrix += cells[key]
                    relevant_all.update(relevant[key])
            pooled[kind] = _summary(matrix, global_counts[kind], kind, blocks, weights, strata, relevant_all, min_blocks, common_reasons)
        for run in prepared:
            years = sorted({key[1] for key in cells if key[0] == run["run_id"]})
            for year in years:
                row = {"product_id": run["product_id"], "config_id": run["identity"][0], "timeframe": run["identity"][1],
                       "scale_id": run["identity"][2], "year": year, "kinds": {}}
                for kind in _KINDS:
                    key = (run["run_id"], year, kind)
                    row["kinds"][kind] = _summary(
                        cells[key], cells[key].sum(axis=0), kind, blocks, weights, strata, relevant[key], min_blocks, common_reasons,
                    )
                by_product_year.append(row)
        report["modes"][mode] = {
            "declared_window_plan": build_calendar_blocks(declared),
            "complete_reviewed_window_plan": plan,
            "sampling_strata": strata,
            "resample_weights_sha256": hashlib.sha256(weights.astype("<i8").tobytes()).hexdigest(),
            "global_matching_equals_block_annual_count_sum": not mismatch,
            "matching_additivity_failures": mismatch,
            "pooled": pooled,
            "by_product_year": by_product_year,
        }
    return report
