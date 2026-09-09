"""Auditable reconciliation of two independent human annotation documents.

This module cannot establish that a named person actually reviewed a chart.
It checks recorded provenance, retains every disagreement, and never promotes
agreement or algorithmic/synthetic labels into adjudicated truth automatically.
The frozen morphology matching tolerance remains two bars per extremum.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime
from typing import Any

from .annotations import SCHEMA_VERSION, maximum_matching, validate_annotation_document

RECONCILIATION_SCHEMA = "two_wave_annotation_reconciliation@1.0"
DECISION_SCHEMA = "two_wave_annotation_adjudication@1.0"
_IDENTITY = ("instrument", "config_id", "timeframe", "scale_id", "kind", "reference_mode")
_AUTOMATIC_REVIEWERS = {"algorithm", "engine", "model", "automatic", "auto", "synthetic", "算法"}


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _human(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in _AUTOMATIC_REVIEWERS


def _timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() is not None
    except ValueError:
        return False


def reviewer_template() -> dict[str, Any]:
    """An empty form, with independence and completeness deliberately unsigned."""
    return {
        "schema_version": SCHEMA_VERSION,
        "reviewer": "",
        "instrument": "000852.SH",
        "reference_mode": "offline",
        "config_id": "",
        "timeframe": "",
        "scale_id": "",
        "provenance": {
            "source_type": "",
            "reference_version": "",
            "completed_at": "",
            "blinded_to_algorithm": None,
            "independent_of_other_reviewer": None,
            "future_exposed": None,
            "online_clock": None,
        },
        "annotations": [],
        "review_windows": [],
        "notice": "EMPTY FORM. No human work, negative window, independence or adjudication is asserted.",
    }


def prepare_review_document(exported: Mapping[str, Any]) -> dict[str, Any]:
    """Add unsigned provenance fields to a replay export without certifying it."""
    if exported.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Replay export schema_version must be {SCHEMA_VERSION}")
    result = reviewer_template()
    result.update(deepcopy(dict(exported)))
    result["source_export_sha256"] = _hash(exported)
    for record in result.get("annotations", []):
        record.setdefault("reason", "")
        record.setdefault("confidence", None)
    result["notice"] = "Prepared from replay export. A real reviewer must complete unsigned provenance, reasons and confidence."
    return result


def _issues(record: Mapping[str, Any], *, window: bool = False) -> list[str]:
    provenance = record.get("provenance", {})
    if not isinstance(provenance, Mapping):
        return ["missing_or_invalid_provenance"]
    issues = []
    if provenance.get("source_type") != "independent_human":
        issues.append("source_type_not_independent_human")
    if not isinstance(provenance.get("reference_version"), str) or not provenance["reference_version"].strip():
        issues.append("missing_reference_version")
    if not _timestamp(provenance.get("completed_at")):
        issues.append("missing_timezone_aware_completion_time")
    if provenance.get("blinded_to_algorithm") is not True or record.get("algorithm_visible", False):
        issues.append("algorithm_blinding_not_attested")
    if provenance.get("independent_of_other_reviewer") is not True:
        issues.append("independent_double_review_not_attested")
    if record.get("independent_reference", True) is not True:
        issues.append("explicitly_nonindependent")
    if not isinstance(record.get("instrument"), str) or not record["instrument"].strip():
        issues.append("missing_instrument_identity")
    if record["reference_mode"] == "online":
        if provenance.get("future_exposed") is not False:
            issues.append("online_future_blinding_not_attested")
        if provenance.get("online_clock") not in ("bar_end", "information_available_time"):
            issues.append("online_information_clock_not_declared")
    if not window:
        if record.get("duplicate_geometry_annotation_ids"):
            issues.append("duplicate_geometry_within_same_reference_view")
        if not isinstance(record.get("reason"), str) or not record["reason"].strip():
            issues.append("missing_annotation_reason")
        confidence = record.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            issues.append("confidence_must_be_between_zero_and_one")
        if record.get("ambiguous") is True:
            issues.append("reviewer_marked_ambiguous")
    else:
        if record.get("fully_reviewed") is not True:
            issues.append("window_not_complete_reviewed")
        if any(k in record and not isinstance(record[k], bool) for k in ("fully_reviewed", "complete_reviewed")):
            issues.append("window_completeness_flags_must_be_boolean")
        if "complete_reviewed" in record and record["complete_reviewed"] != record.get("fully_reviewed"):
            issues.append("conflicting_window_completeness_flags")
    return issues


def _normalize(document: Mapping[str, Any]) -> dict[str, Any]:
    for record in document.get("annotations", []):
        if any(k in record and not isinstance(record[k], bool) for k in ("algorithm_visible", "independent_reference", "ambiguous")):
            raise ValueError("Annotation independence, visibility and ambiguity flags must be boolean")
    normalized = validate_annotation_document(document)
    if not _human(normalized.get("reviewer")):
        raise ValueError("Each document requires one named independent human reviewer")
    for kind in ("annotations", "review_windows"):
        for record in normalized[kind]:
            if record["reviewer"] != normalized["reviewer"]:
                raise ValueError("Each source document must contain only its declared reviewer's records")
            record.setdefault("instrument", normalized.get("instrument"))
            record.setdefault("kind", "structure")
            if record["kind"] not in ("structure", "cycle", "all") or kind == "annotations" and record["kind"] == "all":
                raise ValueError("Review kind must be structure or cycle; windows may also use all")
            record["provenance"] = deepcopy(record.get("provenance", normalized.get("provenance", {})))
    geometries = defaultdict(list)
    for record in normalized["annotations"]:
        geometries[(_identity(record), record["phase"], tuple(record["pivot_indices"]))].append(record)
    for duplicates in geometries.values():
        if len(duplicates) > 1:
            ids = sorted(record["annotation_id"] for record in duplicates)
            for record in duplicates:
                record["duplicate_geometry_annotation_ids"] = ids
    return normalized


def _identity(record: Mapping[str, Any]) -> tuple[Any, ...]:
    identity = tuple(record.get(k) for k in _IDENTITY)
    if record["reference_mode"] == "online":
        provenance = record.get("provenance", {})
        clock = provenance.get("online_clock") if isinstance(provenance, Mapping) else None
        identity += (record["visible_cutoff"], clock)
    return identity


def _case(a: dict[str, Any] | None, b: dict[str, Any] | None) -> dict[str, Any]:
    reasons = []
    if a is None or b is None:
        reasons.append("missing_reviewer_a_object" if a is None else "missing_reviewer_b_object")
    else:
        if a.get("label") != b.get("label"):
            reasons.append("classification_disagreement")
        if a["pivot_indices"] != b["pivot_indices"]:
            reasons.append("geometry_variation_within_frozen_tolerance")
    provenance_issues = {side: _issues(record) for side, record in (("a", a), ("b", b)) if record is not None}
    return {
        "case_id": "case_" + _hash({"a": a, "b": b})[:24],
        "reviewer_a_record": a,
        "reviewer_b_record": b,
        "comparison": reasons or ["double_review_agreement"],
        "provenance_issues": provenance_issues,
        "status": "awaiting_explicit_human_adjudication",
    }


def decision_template(reconciliation: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": DECISION_SCHEMA,
        "source_document_sha256": deepcopy(reconciliation["source_document_sha256"]),
        "decisions": [
            {"case_id": case["case_id"], "action": None, "adjudicator": "", "decided_at": "", "reason": ""}
            for case in reconciliation["cases"]
        ],
        "notice": "Unsigned rows remain pending. Actions: accept_a, accept_b, reject_both, ambiguous.",
    }


def _apply_decisions(cases: list[dict], document: Mapping[str, Any] | None, sources: dict) -> list[dict]:
    references = []
    if document is None:
        return references
    if document.get("schema_version") != DECISION_SCHEMA or document.get("source_document_sha256") != sources:
        raise ValueError("Decisions must use the current schema and exact source_document_sha256")
    decisions = document.get("decisions")
    if not isinstance(decisions, list):
        raise ValueError("decisions must be an array")
    by_id = {case["case_id"]: case for case in cases}
    seen = set()
    for decision in decisions:
        case_id = decision.get("case_id")
        if case_id not in by_id or case_id in seen:
            raise ValueError("Unknown or duplicate adjudication case_id")
        seen.add(case_id)
        action = decision.get("action")
        if action is None:
            continue
        if action not in ("accept_a", "accept_b", "reject_both", "ambiguous"):
            raise ValueError("Invalid adjudication action")
        if not _human(decision.get("adjudicator")) or not _timestamp(decision.get("decided_at")):
            raise ValueError("Signed decisions require a human adjudicator and timezone-aware decided_at")
        if not isinstance(decision.get("reason"), str) or not decision["reason"].strip():
            raise ValueError("Signed decisions require an explicit reason")
        case = by_id[case_id]
        decided_at = datetime.fromisoformat(decision["decided_at"].replace("Z", "+00:00"))
        for source_record in (case["reviewer_a_record"], case["reviewer_b_record"]):
            provenance = source_record.get("provenance", {}) if source_record else {}
            completed_at = provenance.get("completed_at") if isinstance(provenance, Mapping) else None
            if _timestamp(completed_at) and decided_at < datetime.fromisoformat(completed_at.replace("Z", "+00:00")):
                raise ValueError("decided_at cannot precede a source review completion time")
        case["adjudication"] = deepcopy(decision)
        if action in ("ambiguous", "reject_both"):
            case["status"] = "ambiguous" if action == "ambiguous" else "rejected_by_human_adjudication"
            continue
        side = action[-1]
        record = case[f"reviewer_{side}_record"]
        if record is None or case["provenance_issues"][side]:
            raise ValueError("Cannot accept missing, ambiguous or nonindependent source record; repair the source as a new version")
        record = deepcopy(record)
        record["source_annotation_id"] = record["annotation_id"]
        record["annotation_id"] = case_id
        record["adjudication"] = {**deepcopy(decision), "source_document_sha256": deepcopy(sources)}
        record["independent_reference"] = True
        case["status"] = "accepted_by_human_adjudication"
        references.append(record)
    accepted_geometries = set()
    for record in references:
        geometry = (_identity(record), record["phase"], tuple(record["pivot_indices"]))
        if geometry in accepted_geometries:
            raise ValueError("Adjudication selected duplicate reference geometry; revise decisions explicitly")
        accepted_geometries.add(geometry)
    return references


def _reconciled_windows(a: dict, b: dict, cases: list[dict]) -> tuple[list[dict], list[dict]]:
    def key(window):
        return _identity(window) + (window["start_index"], window["end_index"])

    def in_core(record, window):
        scope = {**window, "kind": record["kind"]} if window["kind"] == "all" else window
        return _identity(record) == _identity(scope) and window["start_index"] <= record["pivot_indices"][-1] <= window["end_index"]

    groups = {side: defaultdict(list) for side in ("a", "b")}
    for side, doc in (("a", a), ("b", b)):
        for window in doc["review_windows"]:
            groups[side][key(window)].append(window)
    audit, usable = [], []
    for identity in sorted(set(groups["a"]) | set(groups["b"]), key=str):
        left, right = groups["a"].get(identity, []), groups["b"].get(identity, [])
        reasons = []
        if len(left) != 1 or len(right) != 1:
            reasons.append("missing_or_duplicate_double_review_window")
        for side, windows in (("a", left), ("b", right)):
            for window in windows:
                reasons.extend(f"{side}:{issue}" for issue in _issues(window, window=True))
        window = (left or right)[0]
        unresolved, ineligible = [], []
        for case in cases:
            for side, record in (("a", case["reviewer_a_record"]), ("b", case["reviewer_b_record"])):
                if record and in_core(record, window):
                    if set(case["provenance_issues"][side]) - {
                        "reviewer_marked_ambiguous", "duplicate_geometry_within_same_reference_view"
                    }:
                        ineligible.append(case["case_id"])
                    if case["status"] not in ("accepted_by_human_adjudication", "rejected_by_human_adjudication"):
                        unresolved.append(case["case_id"])
        if unresolved:
            reasons.append("unresolved_objects_in_core_window")
        if ineligible:
            reasons.append("ineligible_source_records_in_core_window")
        entry = {"reviewer_a_windows": left, "reviewer_b_windows": right, "exclusion_reasons": reasons,
                 "unresolved_case_ids": sorted(set(unresolved)), "ineligible_source_case_ids": sorted(set(ineligible)),
                 "usable_for_primary_scoring": not reasons}
        audit.append(entry)
        if not reasons:
            chosen = deepcopy(window)
            chosen["reviewer"] = a["reviewer"]
            chosen["double_reviewers"] = [a["reviewer"], b["reviewer"]]
            chosen["complete_reviewed"] = chosen["fully_reviewed"] = True
            chosen["window_reconciliation"] = "exact_double_review_scope_with_all_cases_explicitly_resolved"
            usable.append(chosen)
    return usable, audit


def reconcile_annotations(
    reviewer_a: Mapping[str, Any], reviewer_b: Mapping[str, Any], decisions: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Retain every source object and require explicit decisions for references.

    Matching is class blind and scoped by instrument, product/config, scale,
    phase, object kind and reference mode; online references additionally share
    cutoff and declared information clock. No market outcomes are consulted.
    """
    a, b = _normalize(reviewer_a), _normalize(reviewer_b)
    if a["reviewer"].strip().casefold() == b["reviewer"].strip().casefold():
        raise ValueError("Double review requires two different reviewer identities")
    sources = {"reviewer_a": _hash(reviewer_a), "reviewer_b": _hash(reviewer_b)}
    groups = {side: defaultdict(list) for side in ("a", "b")}
    for side, doc in (("a", a), ("b", b)):
        for record in doc["annotations"]:
            groups[side][_identity(record)].append(record)
    cases = []
    for identity in sorted(set(groups["a"]) | set(groups["b"]), key=str):
        left = sorted(groups["a"].get(identity, []), key=lambda r: r["annotation_id"])
        right = sorted(groups["b"].get(identity, []), key=lambda r: r["annotation_id"])
        predictions = [{**record, "prediction_id": record["annotation_id"]} for record in right]
        matches = maximum_matching(predictions, left, tolerance_bars=2)
        for pair in matches["pairs"]:
            cases.append(_case(left[pair["reference_index"]], right[pair["prediction_index"]]))
        cases.extend(_case(left[i], None) for i in matches["unmatched_reference_indices"])
        cases.extend(_case(None, right[i]) for i in matches["unmatched_prediction_indices"])
    cases.sort(key=lambda case: case["case_id"])
    references = _apply_decisions(cases, decisions, sources)
    windows, window_audit = _reconciled_windows(a, b, cases)
    statuses = Counter(case["status"] for case in cases)
    unresolved = sum(case["status"] in ("awaiting_explicit_human_adjudication", "ambiguous") for case in cases)
    reference_document = {
        "schema_version": SCHEMA_VERSION,
        "annotations": references,
        "review_windows": windows,
        "source_document_sha256": sources,
        "historical_point_in_time_status": "historical_PIT_not_verified",
        "notice": "Only explicit human decisions are references. Original observations and unresolved cases remain in reconciliation.",
    }
    validate_annotation_document(reference_document)
    return {
        "schema_version": RECONCILIATION_SCHEMA,
        "status": "morphology_replication_not_yet_accepted",
        "source_document_sha256": sources,
        "source_reviewers": {"reviewer_a": a["reviewer"], "reviewer_b": b["reviewer"]},
        "matching_tolerance_bars": 2,
        "cases": cases,
        "review_window_audit": window_audit,
        "adjudicated_reference": reference_document,
        "counts": {
            "reviewer_a_annotations": len(a["annotations"]),
            "reviewer_b_annotations": len(b["annotations"]),
            "cases": len(cases),
            "status_counts": dict(sorted(statuses.items())),
            "unresolved_cases": unresolved,
            "unresolved_fraction": unresolved / len(cases) if cases else None,
            "records_with_provenance_issues": sum(bool(issues) for case in cases for issues in case["provenance_issues"].values()),
            "adjudicated_reference_count": len(references),
            "primary_scoring_window_count": len(windows),
            "excluded_or_incomplete_review_window_groups": sum(not item["usable_for_primary_scoring"] for item in window_audit),
        },
        "limitations": [
            "Metadata validation cannot prove actual human identity, blinding or independent work.",
            "Missing or ambiguous cases are retained; affected full windows are withheld from primary scoring.",
            "Ambiguity inclusion/exclusion sensitivity must still be reported with a completed reference set.",
            "Corrected geometry requires a new human source version and new signed decisions; old versions must be retained.",
            "Matching and adjudication do not grant morphology acceptance, H1/H2, trading or registration authority.",
        ],
    }
