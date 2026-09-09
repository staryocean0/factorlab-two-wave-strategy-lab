"""Independent human reference labels and predeclared morphology matching.

Labels are external observations, never an engine export recycled as truth.
Offline geometry and online-prefix references are evaluated separately. Precision
is defined only inside explicitly fully reviewed windows; sparse annotations do
not turn the rest of a price series into negative examples.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict, deque
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

SCHEMA_VERSION = "two_wave_annotations@1.0"
LABELS = ("range", "uptrend", "downtrend", "uncertain")
DEFAULT_GATES = {
    "min_independent_structures": 200,
    "min_per_directional_class": 30,
    "min_precision": 0.8,
    "min_recall": 0.8,
    "min_macro_f1": 0.75,
    "min_classification_coverage": 0.6,
}


def annotation_template(export: Mapping[str, Any]) -> dict[str, Any]:
    """An EMPTY reference document; predictions are deliberately not labels."""
    return {
        "schema_version": SCHEMA_VERSION,
        "reviewer": "",
        "reference_mode": "online",
        "config_id": export.get("config_hash", ""),
        "timeframe": export.get("config", {}).get("timeframe", ""),
        "scale_id": export.get("scale_id", ""),
        "annotations": [],
        "review_windows": [],
        "notice": "Human labels are references, not algorithmic ground truth. Fill reviewer and annotate independently.",
    }


def _reviewer(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and value.strip().lower() not in {"algorithm", "engine", "model", "automatic", "auto", "算法"}
    )


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def validate_annotation_document(document: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a reference document and return normalized independent records.

    Missing metadata may inherit from the document. This validator cannot prove
    a human worked independently; it records the attribution and rejects an
    explicitly algorithm-attributed reference rather than certifying it.
    """
    if not isinstance(document, Mapping) or document.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    result = deepcopy(dict(document))
    annotations = result.get("annotations", [])
    windows = result.get("review_windows", [])
    if not isinstance(annotations, list) or not isinstance(windows, list):
        raise ValueError("annotations and review_windows must be arrays")
    ids: set[str] = set()
    for annotation in annotations:
        for key in ("reviewer", "reference_mode", "config_id", "timeframe", "scale_id"):
            annotation.setdefault(key, result.get(key))
        if not _reviewer(annotation.get("reviewer")):
            raise ValueError("Every annotation needs an independent human reviewer attribution")
        if annotation.get("reference_mode") not in ("offline", "online"):
            raise ValueError("reference_mode must be offline or online")
        if any(
            not isinstance(annotation.get(k), str) or not annotation[k].strip()
            for k in ("config_id", "timeframe", "scale_id", "annotation_id")
        ):
            raise ValueError("annotation_id, config_id, timeframe and scale_id are required")
        if annotation["annotation_id"] in ids:
            raise ValueError("annotation_id must be unique")
        ids.add(annotation["annotation_id"])
        kind = annotation.get("kind", "structure")
        annotation["kind"] = kind
        expected = {"structure": 5, "cycle": 3}.get(kind)
        points = annotation.get("pivot_indices")
        if not expected or not isinstance(points, list) or len(points) != expected:
            raise ValueError("A structure requires five extrema; a complete cycle requires three")
        if any(not _integer(p) for p in points) or any(a >= b for a, b in zip(points, points[1:], strict=False)):
            raise ValueError("pivot_indices must be strictly increasing nonnegative bar indices")
        if annotation.get("phase") not in ("low", "high"):
            raise ValueError("phase must be low or high")
        if kind == "structure" and annotation.get("label") not in LABELS:
            raise ValueError(f"structure label must be one of {LABELS}")
        cutoff = annotation.get("visible_cutoff")
        if not _integer(cutoff) or cutoff < points[-1]:
            raise ValueError("visible_cutoff must include every annotated extremum")
        if annotation.get("algorithm_visible", False):
            # A usable review record, but not an independent reference set.
            annotation["independent_reference"] = False
        else:
            annotation["independent_reference"] = bool(annotation.get("independent_reference", True))
    for window in windows:
        if "complete_reviewed" in window:
            window.setdefault("fully_reviewed", window["complete_reviewed"])
        for key in ("reviewer", "reference_mode", "config_id", "timeframe", "scale_id"):
            window.setdefault(key, result.get(key))
        if not _reviewer(window.get("reviewer")) or window.get("reference_mode") not in ("offline", "online"):
            raise ValueError("review windows need reviewer and reference_mode")
        if any(not isinstance(window.get(k), str) or not window[k].strip() for k in ("config_id", "timeframe", "scale_id")):
            raise ValueError("review windows need config_id, timeframe and scale_id")
        if any(not _integer(window.get(k)) for k in ("start_index", "end_index", "visible_cutoff")):
            raise ValueError("review window bounds must be nonnegative bar indices")
        if not window["start_index"] <= window["end_index"] <= window["visible_cutoff"]:
            raise ValueError("review window must end no later than visible_cutoff")
    result["annotations"] = annotations
    result["review_windows"] = windows
    return result


def _key(record: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(str(record.get(k, "")) for k in ("config_id", "timeframe", "scale_id", "phase", "_evaluation_cutoff"))


def _prediction_records(export: Mapping[str, Any], kind: str) -> list[dict[str, Any]]:
    pivots = {p["pivot_id"]: p for p in export.get("pivots", [])}
    result = []
    for original in export.get("structures" if kind == "structure" else "cycles", []):
        record = dict(original)
        points = record.get("pivot_indices")
        if points is None:
            points = [pivots[p]["occurrence_bar"] for p in record.get("pivot_ids", [])]
        if len(points) != (5 if kind == "structure" else 3):
            raise ValueError(f"Malformed {kind}: missing member pivots")
        record.update(
            prediction_id=record.get("structure_id" if kind == "structure" else "cycle_id"),
            pivot_indices=list(points),
            config_id=export.get("config_hash", ""),
            timeframe=export.get("config", {}).get("timeframe", ""),
            scale_id=export.get("scale_id", ""),
        )
        result.append(record)
    return result


def maximum_matching(
    predictions: list[dict[str, Any]], references: list[dict[str, Any]], tolerance_bars: int = 2, *, online: bool = False
) -> dict[str, Any]:
    """Class-blind maximum cardinality, then minimum total extremum distance.

    Every corresponding extremum must match within the predeclared tolerance.
    Successive shortest residual augmenting paths minimize total distance at
    each cardinality. Reference ID/prediction ID sorted insertion fixes ties.
    Labels do not influence the graph or tie ordering.
    """
    if not _integer(tolerance_bars):
        raise ValueError("tolerance_bars must be a nonnegative integer")
    groups: dict[tuple[str, ...], list[tuple[int, int]]] = defaultdict(list)
    for pi, prediction in enumerate(predictions):
        groups[_key(prediction)].append((prediction["pivot_indices"][0], pi))
    for entries in groups.values():
        entries.sort()
    graph: list[list[int]] = []
    for reference in references:
        entries = groups[_key(reference)]
        first = reference["pivot_indices"][0]
        lower = bisect_left(entries, (first - tolerance_bars, -1))
        upper = bisect_right(entries, (first + tolerance_bars, len(predictions)))
        candidates = []
        for _, pi in entries[lower:upper]:
            pred = predictions[pi]
            if online and pred["confirmation_bar"] > reference["visible_cutoff"]:
                continue
            distances = [abs(a - b) for a, b in zip(pred["pivot_indices"], reference["pivot_indices"], strict=False)]
            if len(pred["pivot_indices"]) == len(reference["pivot_indices"]) and max(distances) <= tolerance_bars:
                candidates.append((sum(distances), pi))
        graph.append([pi for _, pi in sorted(candidates)])
    r_order = sorted(range(len(references)), key=lambda i: (str(references[i]["annotation_id"]), i))
    p_order = sorted(range(len(predictions)), key=lambda i: (str(predictions[i].get("prediction_id", "")), i))
    r_node = {i: rank + 1 for rank, i in enumerate(r_order)}
    p_node = {i: rank + 1 + len(references) for rank, i in enumerate(p_order)}
    source, sink = 0, len(references) + len(predictions) + 1
    residual: list[list[list[int]]] = [[] for _ in range(sink + 1)]

    def edge(a: int, b: int, cost: int) -> int:
        index = len(residual[a])
        residual[a].append([b, len(residual[b]), 1, cost])
        residual[b].append([a, index, 0, -cost])
        return index

    pair_edges = []
    for ri in r_order:
        edge(source, r_node[ri], 0)
        for pi in sorted(graph[ri], key=lambda i: (str(predictions[i].get("prediction_id", "")), i)):
            cost = sum(abs(a - b) for a, b in zip(references[ri]["pivot_indices"], predictions[pi]["pivot_indices"], strict=True))
            pair_edges.append((ri, pi, edge(r_node[ri], p_node[pi], cost)))
    for pi in p_order:
        edge(p_node[pi], sink, 0)
    while True:
        distance = [float("inf")] * (sink + 1)
        distance[source] = 0
        previous: list[tuple[int, int] | None] = [None] * (sink + 1)
        queue, queued = deque([source]), {source}
        while queue:
            a = queue.popleft()
            queued.remove(a)
            for ei, (b, _, capacity, cost) in enumerate(residual[a]):
                if capacity and distance[a] + cost < distance[b]:
                    distance[b] = distance[a] + cost
                    previous[b] = (a, ei)
                    if b not in queued:
                        queued.add(b)
                        queue.append(b)
        if previous[sink] is None:
            break
        b = sink
        while b != source:
            a, ei = previous[b]
            forward = residual[a][ei]
            forward[2] -= 1
            residual[b][forward[1]][2] += 1
            b = a
    pairs = sorted((ri, pi) for ri, pi, ei in pair_edges if residual[r_node[ri]][ei][2] == 0)
    matched_r = {ri for ri, _ in pairs}
    matched_p = {pi for _, pi in pairs}
    degrees_p = Counter(pi for candidates in graph for pi in candidates)
    return {
        "pairs": [
            {
                "reference_index": ri,
                "prediction_index": pi,
                "annotation_id": references[ri]["annotation_id"],
                "prediction_id": predictions[pi].get("prediction_id"),
                "extremum_errors_bars": [
                    a - b for a, b in zip(predictions[pi]["pivot_indices"], references[ri]["pivot_indices"], strict=True)
                ],
            }
            for ri, pi in pairs
        ],
        "unmatched_reference_indices": [i for i in range(len(references)) if i not in matched_r],
        "unmatched_prediction_indices": [i for i in range(len(predictions)) if i not in matched_p],
        "split_candidate_count_diagnostic": sum(len(x) > 1 for x in graph),
        "merge_candidate_count_diagnostic": sum(n > 1 for n in degrees_p.values()),
        "total_absolute_extremum_error_bars": sum(
            sum(abs(a - b) for a, b in zip(references[ri]["pivot_indices"], predictions[pi]["pivot_indices"], strict=True))
            for ri, pi in pairs
        ),
        "diagnostic_note": "Multiple admissible matches are ambiguity diagnostics, not verified split/merge errors.",
    }


def _window_key(record: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(str(record.get(k, "")) for k in ("config_id", "timeframe", "scale_id"))


def _in_window(record: Mapping[str, Any], windows: list[dict[str, Any]], online: bool, *, prediction: bool) -> bool:
    last = record["pivot_indices"][-1]
    for window in windows:
        if _window_key(window) != _window_key(record) or not window.get("fully_reviewed", False):
            continue
        if not (window["start_index"] <= last <= window["end_index"]):
            continue
        if online and prediction and record["confirmation_bar"] > window["visible_cutoff"]:
            continue
        if online and not prediction and record["visible_cutoff"] != window["visible_cutoff"]:
            continue
        return True
    return False


def _independent_count(references: list[dict[str, Any]]) -> int:
    """Conservative nonoverlap count across phases/scales on the same timeframe.

    This is a sampling proxy, not a claim that disjoint market intervals are
    statistically independent. Time-block bootstrap remains a separate gate.
    """
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in references:
        groups[record["timeframe"]].append(record)
    count = 0
    for group in groups.values():
        last_end = -1
        for record in sorted(group, key=lambda r: (r["pivot_indices"][-1], r["pivot_indices"][0])):
            if record["pivot_indices"][0] > last_end:
                count += 1
                last_end = record["pivot_indices"][-1]
    return count


def _evaluate_kind(
    predictions: list[dict[str, Any]], references: list[dict[str, Any]], windows: list[dict[str, Any]], mode: str, kind: str, tolerance: int
) -> dict[str, Any]:
    online = mode == "online"
    windows = [w for w in windows if w.get("kind", "structure") in (kind, "all")]
    if online:
        # Different prefixes are different observations. Never let a prediction
        # visible in a later window enter an earlier window's confusion matrix.
        scoped_predictions, scoped_references = [], []
        for cutoff in sorted({w["visible_cutoff"] for w in windows}):
            at_cutoff = [w for w in windows if w["visible_cutoff"] == cutoff]
            scoped_predictions.extend(
                dict(p, _evaluation_cutoff=cutoff) for p in predictions if _in_window(p, at_cutoff, True, prediction=True)
            )
            scoped_references.extend(
                dict(r, _evaluation_cutoff=cutoff) for r in references if _in_window(r, at_cutoff, True, prediction=False)
            )
    else:
        scoped_predictions = [p for p in predictions if _in_window(p, windows, False, prediction=True)]
        scoped_references = [r for r in references if _in_window(r, windows, False, prediction=False)]
    pairing = maximum_matching(scoped_predictions, scoped_references, tolerance, online=online)
    matched = len(pairing["pairs"])
    report: dict[str, Any] = {
        "reference_count": len(references),
        "reviewed_reference_count": len(scoped_references),
        "reviewed_prediction_count": len(scoped_predictions),
        "matched_count": matched,
        "missed_count": len(scoped_references) - matched,
        "unmatched_prediction_count": len(scoped_predictions) - matched,
        "precision": matched / len(scoped_predictions) if scoped_predictions else None,
        "recall": matched / len(scoped_references) if scoped_references else None,
        "sparse_reference_matching": maximum_matching(predictions, references, tolerance, online=online),
        "pairing": pairing,
        "precision_scope": "Only explicitly fully reviewed windows; sparse references are separate.",
        "window_membership": "Final extremum occurs in scoring core; earlier extrema may use prior context.",
        "observation_scope": "Separate prefix observations; repeated physical objects do not increase the unique-object sample gate."
        if online
        else "Offline geometric objects",
    }
    if kind == "cycle":
        return report
    confusion = {truth: {pred: 0 for pred in (*LABELS, "not_detected")} for truth in LABELS}
    for pair in pairing["pairs"]:
        truth = scoped_references[pair["reference_index"]]["label"]
        predicted = scoped_predictions[pair["prediction_index"]].get("classification", "uncertain")
        if predicted not in LABELS:
            raise ValueError(f"Unknown prediction classification: {predicted}")
        confusion[truth][predicted] += 1
    for ri in pairing["unmatched_reference_indices"]:
        confusion[scoped_references[ri]["label"]]["not_detected"] += 1
    unmatched_classes = Counter(scoped_predictions[pi].get("classification", "uncertain") for pi in pairing["unmatched_prediction_indices"])
    unique_references = {}
    for reference in scoped_references:
        key = (_window_key(reference), reference["phase"], tuple(reference["pivot_indices"]))
        unique_references.setdefault(key, reference)
    counts = Counter(r["label"] for r in unique_references.values())
    f1s, matched_f1s, per_class = [], [], {}
    for label in LABELS[:3]:
        true_positive = confusion[label][label]
        actual = sum(confusion[label].values())
        predicted = sum(confusion[truth][label] for truth in LABELS) + unmatched_classes[label]
        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / actual if actual else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        has_observations = bool(scoped_predictions or scoped_references)
        per_class[label] = {
            "precision": precision if has_observations else None,
            "recall": recall if has_observations else None,
            "f1": f1 if has_observations else None,
            "matched_support": actual - confusion[label]["not_detected"],
            "reviewed_reference_observation_support": actual,
            "unique_reference_support": counts[label],
            "unmatched_prediction_false_positives": unmatched_classes[label],
        }
        f1s.append(f1)
        matched_actual = actual - confusion[label]["not_detected"]
        matched_predicted = predicted - unmatched_classes[label]
        matched_f1s.append(2 * true_positive / (matched_actual + matched_predicted) if matched_actual + matched_predicted else 0.0)
    accepted = sum(p.get("classification") in LABELS[:3] for p in scoped_predictions)
    report.update(
        confusion_matrix=confusion,
        confusion_scope="All scored reference observations, including not_detected; unmatched predictions count as class false positives.",
        unmatched_prediction_class_counts={c: unmatched_classes[c] for c in LABELS},
        classification_accuracy=sum(confusion[c][c] for c in LABELS) / matched if matched else None,
        classification_accuracy_scope="Matched-only auxiliary accuracy",
        macro_f1=sum(f1s) / 3 if scoped_predictions or scoped_references else None,
        matched_only_macro_f1=sum(matched_f1s) / 3 if matched else None,
        per_class=per_class,
        classification_coverage=accepted / len(scoped_predictions) if scoped_predictions else None,
        rejection_ratio=1 - accepted / len(scoped_predictions) if scoped_predictions else None,
        reference_class_counts=dict(counts),
        unique_reference_count=len(unique_references),
        reference_clear_classification_coverage=sum(confusion[truth][pred] for truth in LABELS for pred in LABELS[:3])
        / len(scoped_references)
        if scoped_references
        else None,
        nonoverlapping_reference_count=_independent_count(scoped_references),
        sampling_note="Nonoverlap is a conservative count proxy; time dependence is not removed.",
    )
    return report


def evaluate_annotations(
    export: Mapping[str, Any], document: Mapping[str, Any] | None = None, tolerance_bars: int = 2, gates: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Evaluate morphology without opening hypothesis or trading authority.

    This implementation does NOT estimate block-bootstrap uncertainty, so it
    cannot certify morphology acceptance even if preliminary point gates pass.
    """
    if not _integer(tolerance_bars):
        raise ValueError("tolerance_bars must be a nonnegative integer")
    protocol = dict(DEFAULT_GATES)
    if gates:
        unknown = set(gates) - set(protocol)
        if unknown:
            raise ValueError(f"Unknown acceptance gates: {sorted(unknown)}")
        protocol.update(gates)
    report: dict[str, Any] = {
        "schema_version": "two_wave_morphology_evaluation@1.0",
        "status": "morphology_replication_not_yet_accepted",
        "authority": "research_only_no_hypothesis_or_trading_promotion",
        "tolerance_bars": tolerance_bars,
        "matching": "same_config_timeframe_scale_phase_all_extrema_maximum_one_to_one_class_blind",
        "gates": protocol,
        "reference_count": 0,
        "accuracy": None,
        "precision": None,
        "recall": None,
        "macro_f1": None,
        "classification_coverage": None,
        "bootstrap_implemented": False,
        "uncertainty_gate": "not_evaluated_block_bootstrap_required",
        "reference_independence": "human_attribution_is_recorded_not_verified",
        "arbitration_tooling_implemented": False,
        "unresolved_reference_disagreements": "require_external_human_adjudication_before_acceptance",
        "historical_point_in_time_status": "historical_PIT_not_verified",
        "online_reference_scope": "bar_prefix_only; source available_at may be later than bar end",
        "modes": {},
    }
    if document is None:
        report["reason"] = "No independent human reference labels supplied. Algorithm output is not truth."
        return report
    normalized = validate_annotation_document(document)
    usable = [r for r in normalized["annotations"] if r["independent_reference"]]
    report["excluded_nonindependent_reference_count"] = len(normalized["annotations"]) - len(usable)
    report["reference_count"] = len(usable)
    if not usable:
        report["reason"] = "No independent human reference labels supplied."
        return report
    predictions = {kind: _prediction_records(export, kind) for kind in ("structure", "cycle")}
    for mode in ("offline", "online"):
        refs = [r for r in usable if r["reference_mode"] == mode]
        if not refs:
            continue
        windows = [w for w in normalized["review_windows"] if w["reference_mode"] == mode]
        mode_report = {
            kind: _evaluate_kind(predictions[kind], [r for r in refs if r["kind"] == kind], windows, mode, kind, tolerance_bars)
            for kind in ("structure", "cycle")
        }
        structure = mode_report["structure"]
        checks = {
            "unique_human_reference_sample_count": structure["unique_reference_count"] >= protocol["min_independent_structures"],
            "class_support": all(
                structure["reference_class_counts"].get(c, 0) >= protocol["min_per_directional_class"] for c in LABELS[:3]
            ),
        }
        for name, gate in (
            ("precision", "min_precision"),
            ("recall", "min_recall"),
            ("macro_f1", "min_macro_f1"),
            ("classification_coverage", "min_classification_coverage"),
        ):
            checks[name] = structure[name] is not None and structure[name] >= protocol[gate]
        mode_report["preliminary_gate_checks"] = checks
        mode_report["point_estimate_gates_passed"] = all(checks.values())
        mode_report["accepted"] = False
        if mode == "online":
            mode_report["by_visible_cutoff"] = {
                str(cutoff): {
                    kind: _evaluate_kind(
                        predictions[kind],
                        [r for r in refs if r["kind"] == kind and r["visible_cutoff"] == cutoff],
                        [w for w in windows if w["visible_cutoff"] == cutoff],
                        mode,
                        kind,
                        tolerance_bars,
                    )
                    for kind in ("structure", "cycle")
                }
                for cutoff in sorted({w["visible_cutoff"] for w in windows})
            }
        report["modes"][mode] = mode_report
    report["reason"] = "Offline/online reports are separate; sufficient independent references and uncertainty acceptance remain required."
    return report
