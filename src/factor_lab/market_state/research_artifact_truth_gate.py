# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnusedCallResult=false
# pyright: reportMissingTypeStubs=false
"""Read-only truth gate for market-state research artifacts.

The external family lanes are allowed to produce diagnostic evidence, but their
JSON handoff, report, source implementation, data ledger, and event artifacts
must describe the same experiment before a supervisor can replay a result.  The
functions in this module never rewrite an existing lane artifact and never grant
research, routing, dynamic-parameter, or production authority.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pyarrow.parquet as parquet

from factor_lab.core.errors import ValidationError
from factor_lab.governance.canonicalization import canonical_digest
from factor_lab.market_state.tool_formula_mechanisms import (
    build_tool_formula_mechanism_bundle,
)
from factor_lab.market_state.tool_parameter_dictionary import (
    build_fixed_parameter_dictionary,
)
from factor_lab.market_state.tool_registry import tool_benchmark_specs, tool_specs

RESEARCH_REPLAY_MANIFEST_SCHEMA_ID: Final[str] = "market_state_research_replay_manifest@1.0"
RESEARCH_REPLAY_MANIFEST_VERSION: Final[str] = "market_state_research_replay_manifest_v1"
BASELINE_ID: Final[str] = "market-state-parameter-factor-v2-baseline"
_AUTHORITY_KEYS: Final[tuple[str, ...]] = (
    "production_authority",
    "dynamic_parameter_authority",
    "tool_routing_authority",
)
_REQUIRED_LANE_ARTIFACTS: Final[tuple[str, ...]] = (
    "run_manifest.json",
    "data_usage_ledger.json",
    "candidate_mapping_registry.json",
    "fold_evidence.parquet",
    "year_evidence.csv",
    "report_zh.md",
    "supervisor_handoff.json",
)
_CORE_SOURCE_PATHS: Final[tuple[str, ...]] = (
    "src/factor_lab/market_state/tool_registry.py",
    "src/factor_lab/market_state/tool_parameter_dictionary.py",
    "src/factor_lab/market_state/tool_formula_mechanisms.py",
    "src/factor_lab/market_state/tool_benchmark_adapters.py",
    "src/factor_lab/market_state/tool_formula_residual_contracts.py",
)
_ZERO_READY_REPORT_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:裁决\s*[:：]\s*)?0\s*个(?:稳定)?映射",
    flags=re.IGNORECASE,
)
_SIMPLIFICATION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\bsimplified\b|简化(?:实现|模型|EKF)?",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class LaneTruthSpec:
    """One externally produced family lane captured by the stage-0 snapshot."""

    lane_id: str
    artifact_root: str
    expected_tool_ids: tuple[str, ...]


LANE_TRUTH_SPECS: Final[tuple[LaneTruthSpec, ...]] = (
    LaneTruthSpec(
        lane_id="01_spectral_bandpass_components_round2",
        artifact_root=("output/market-state-foundation/formula-mechanism/external-family-lanes/01_spectral_bandpass_components_round2"),
        expected_tool_ids=(
            "laplace_iir_mixed_bandpass",
            "butterworth_clean_bandpass",
            "rolling_fourier_bandpass",
            "causal_haar_wavelet_bandpass",
        ),
    ),
    LaneTruthSpec(
        lane_id="02_causal_background_centerlines",
        artifact_root=("output/market-state-foundation/formula-mechanism/external-family-lanes/02_causal_background_centerlines"),
        expected_tool_ids=(
            "laplace_iir_lowpass",
            "butterworth_lowpass_residual_envelope",
            "causal_asymmetric_arc_state_space_envelope",
        ),
    ),
    LaneTruthSpec(
        lane_id="04_volatility_breakout_channels",
        artifact_root=("output/market-state-foundation/formula-mechanism/external-family-lanes/04_volatility_breakout_channels"),
        expected_tool_ids=(
            "bollinger_volatility_channel",
            "frequency_selective_bollinger_channel",
        ),
    ),
    LaneTruthSpec(
        lane_id="05_price_structure_channels",
        artifact_root=("output/market-state-foundation/formula-mechanism/external-family-lanes/05_price_structure_channels"),
        expected_tool_ids=(
            "donchian_price_channel",
            "causal_trendline_channel",
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class ResearchReplayBaseline:
    """In-memory representation of the stage-0 output pair."""

    manifest: Mapping[str, object]
    artifact_inventory: Mapping[str, object]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _candidate_rows(payload: object) -> list[Mapping[str, object]] | None:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, Mapping)]
    mapping = _mapping(payload)
    if mapping is None:
        return None
    for key in ("candidate_mappings", "candidates", "records", "items"):
        candidate = mapping.get(key)
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, Mapping)]
    return None


def _status(value: Mapping[str, object]) -> str:
    for key in ("evidence_status", "research_status", "status"):
        candidate = value.get(key)
        if isinstance(candidate, str):
            return candidate
    return ""


def _ready_count(rows: Iterable[Mapping[str, object]]) -> int:
    return sum(_status(row) == "ready_for_supervisor_replay" for row in rows)


def _artifact_record(project_root: Path, path: Path) -> dict[str, object]:
    relative_path = path.relative_to(project_root).as_posix()
    file_digest = _sha256_file(path)
    semantic_digest = file_digest
    if path.suffix == ".json":
        try:
            payload = _mapping(_load_json(path))
        except (OSError, json.JSONDecodeError):
            payload = None
        if payload is not None:
            semantic_digest = canonical_digest(dict(payload))
    return {
        "name": path.name,
        "relative_path": relative_path,
        "size_bytes": path.stat().st_size,
        "file_sha256": file_digest,
        "semantic_digest": semantic_digest,
    }


def _parquet_evidence_shape(path: Path) -> tuple[int, int] | None:
    """Read metadata only, so a truth audit need not materialize market data."""

    try:
        evidence = parquet.ParquetFile(path)
        metadata = evidence.metadata
    except (OSError, ValueError):
        return None
    if metadata is None:
        return None
    return metadata.num_rows, len(evidence.schema.names)


def _csv_evidence_shape(path: Path) -> tuple[int, int] | None:
    """Count CSV rows while retaining the content hash as the full-data witness."""

    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = csv.reader(handle)
            header = next(rows, None)
            if header is None:
                return 0, 0
            return sum(1 for _ in rows), len(header)
    except (OSError, UnicodeDecodeError, csv.Error):
        return None


def recompute_event_evidence(path: Path) -> dict[str, object]:
    """Recompute decision and utility totals from event rows, never summary metadata."""

    try:
        if path.suffix == ".parquet":
            columns = parquet.read_table(path).to_pydict()
            row_count = len(next(iter(columns.values()), []))
            rows = [{column: values[index] for column, values in columns.items()} for index in range(row_count)]
        elif path.suffix == ".csv":
            with path.open("r", encoding="utf-8", newline="") as handle:
                rows = [dict(row) for row in csv.DictReader(handle)]
        else:
            raise ValidationError("event evidence must be CSV or Parquet")
    except (OSError, ValueError, csv.Error) as exc:
        raise ValidationError(f"event evidence is not readable: {path}") from exc
    if not rows:
        raise ValidationError("event evidence cannot be empty")
    event_ids = [str(row.get("event_id", "")).strip() for row in rows]
    if any(not event_id for event_id in event_ids) or len(event_ids) != len(set(event_ids)):
        raise ValidationError("event evidence requires unique nonblank event_id values")

    utility_keys = (
        "candidate_utility_delta",
        "net_uplift",
        "f1_net_uplift_vs_fixed",
    )
    utility_key = next(
        (key for key in utility_keys if all(key in row for row in rows)),
        None,
    )
    if utility_key is None:
        raise ValidationError("event evidence lacks a supported event utility column")

    utilities: list[float] = []
    outcomes: list[str] = []
    for row in rows:
        try:
            utility = float(row[utility_key])
        except (TypeError, ValueError) as exc:
            raise ValidationError("event utility must be numeric") from exc
        if not math.isfinite(utility):
            raise ValidationError("event utility must be finite")
        utilities.append(utility)
        error_type = str(row.get("error_type", "")).strip().lower()
        if error_type in {"correct", "corrected", "right"}:
            outcomes.append("correct")
        elif error_type in {"incorrect", "wrong", "harmed"}:
            outcomes.append("incorrect")
        elif "decision_correct" in row:
            value = row["decision_correct"]
            if isinstance(value, str):
                value = value.strip().lower() in {"1", "true", "yes"}
            outcomes.append("correct" if bool(value) else "incorrect")
        else:
            raise ValidationError("event evidence lacks a supported correct/incorrect outcome column")

    correct_count = sum(outcome == "correct" for outcome in outcomes)
    incorrect_count = sum(outcome == "incorrect" for outcome in outcomes)
    payload: dict[str, object] = {
        "event_count": len(rows),
        "decision_change_count": correct_count + incorrect_count,
        "correct_change_count": correct_count,
        "incorrect_change_count": incorrect_count,
        "net_utility_delta": sum(utilities),
        "harm_introduced": sum(max(-value, 0.0) for value in utilities),
    }
    payload["event_semantic_digest"] = canonical_digest(
        {
            "events": [
                {
                    "event_id": event_id,
                    "utility": utility,
                    "outcome": outcome,
                }
                for event_id, utility, outcome in zip(event_ids, utilities, outcomes, strict=True)
            ]
        }
    )
    return payload


def validate_event_evidence_claim(
    path: Path,
    claimed_metrics: Mapping[str, object],
) -> dict[str, object]:
    """Return recomputed metrics only when every claimed key reconciles."""

    recomputed = recompute_event_evidence(path)
    if set(claimed_metrics) != set(recomputed):
        raise ValidationError("event evidence claim must contain the complete recomputed metric set")
    for key, actual in recomputed.items():
        claimed = claimed_metrics.get(key)
        if isinstance(actual, float):
            if (
                isinstance(claimed, bool)
                or not isinstance(claimed, (int, float))
                or not math.isclose(float(claimed), actual, rel_tol=0.0, abs_tol=1e-12)
            ):
                raise ValidationError(f"event evidence claim mismatch: {key}")
        elif claimed != actual:
            raise ValidationError(f"event evidence claim mismatch: {key}")
    return recomputed


def _empty_computed_counts() -> dict[str, int]:
    return {
        "handoff_candidate_rows": 0,
        "handoff_ready_rows": 0,
        "registry_candidate_rows": 0,
        "registry_ready_rows": 0,
        "fold_evidence_rows": 0,
        "fold_evidence_columns": 0,
        "year_evidence_rows": 0,
        "year_evidence_columns": 0,
    }


def _git_snapshot(project_root: Path, relevant_paths: Iterable[str]) -> dict[str, object]:
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status_output = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError):
        return {"revision": "unavailable", "relevant_dirty_paths": []}

    relevant = set(relevant_paths)
    dirty_paths: list[str] = []
    for line in status_output:
        if len(line) < 4:
            continue
        candidate = line[3:].replace("\\", "/")
        if candidate in relevant:
            dirty_paths.append(candidate)
    return {
        "revision": revision or "unavailable",
        "relevant_dirty_paths": sorted(dirty_paths),
    }


def _lane_source_paths(
    project_root: Path,
    handoff: Mapping[str, object],
    expected_tool_ids: Sequence[str],
) -> list[Path]:
    paths: set[Path] = set()
    for tool in tool_specs():
        if tool.tool_id not in expected_tool_ids:
            continue
        for relative in tool.source_strategy_refs:
            candidate = project_root / relative
            if candidate.is_file():
                paths.add(candidate)
    for relative in _string_list(handoff.get("changed_files")):
        raw_path = Path(relative)
        if raw_path.is_absolute():
            try:
                source_relative = raw_path.relative_to(project_root).as_posix()
            except ValueError:
                continue
        else:
            source_relative = raw_path.as_posix()
        if not source_relative.endswith(".py") or not source_relative.startswith(("src/", "scripts/")):
            continue
        candidate = project_root / source_relative
        if candidate.is_file():
            paths.add(candidate)
    return sorted(paths)


def _add_check(
    checks: list[dict[str, object]],
    blockers: list[str],
    *,
    check_id: str,
    passed: bool,
    detail: str,
) -> None:
    checks.append({"check_id": check_id, "passed": passed, "detail": detail})
    if not passed:
        blockers.append(check_id)


def _audit_lane(project_root: Path, spec: LaneTruthSpec) -> tuple[dict[str, object], list[Path]]:
    lane_root = project_root / spec.artifact_root
    checks: list[dict[str, object]] = []
    blockers: list[str] = []
    artifacts: list[dict[str, object]] = []
    relevant_paths: list[Path] = []

    _add_check(
        checks,
        blockers,
        check_id="artifact_root_exists",
        passed=lane_root.is_dir(),
        detail=spec.artifact_root,
    )
    if not lane_root.is_dir():
        return (
            {
                "lane_id": spec.lane_id,
                "artifact_root": spec.artifact_root,
                "expected_tool_ids": list(spec.expected_tool_ids),
                "reported_tool_ids": [],
                "reported_status": "missing",
                "truth_status": "invalid_artifact_chain",
                "computed_counts": _empty_computed_counts(),
                "artifacts": artifacts,
                "implementation": {"source_paths": [], "simplification_signals": []},
                "checks": checks,
                "blockers": blockers,
                "authority": {key: False for key in _AUTHORITY_KEYS},
            },
            relevant_paths,
        )

    for path in sorted(item for item in lane_root.iterdir() if item.is_file()):
        artifacts.append(_artifact_record(project_root, path))
        relevant_paths.append(path)

    for artifact_name in _REQUIRED_LANE_ARTIFACTS:
        _add_check(
            checks,
            blockers,
            check_id=f"required_artifact:{artifact_name}",
            passed=(lane_root / artifact_name).is_file(),
            detail=artifact_name,
        )

    handoff_path = lane_root / "supervisor_handoff.json"
    registry_path = lane_root / "candidate_mapping_registry.json"
    report_path = lane_root / "report_zh.md"
    data_usage_path = lane_root / "data_usage_ledger.json"
    fold_evidence_path = lane_root / "fold_evidence.parquet"
    year_evidence_path = lane_root / "year_evidence.csv"
    handoff = _mapping(_load_json(handoff_path)) if handoff_path.is_file() else None
    registry = _load_json(registry_path) if registry_path.is_file() else None
    ledger = _mapping(_load_json(data_usage_path)) if data_usage_path.is_file() else None
    report = report_path.read_text(encoding="utf-8") if report_path.is_file() else ""

    fold_evidence_shape = _parquet_evidence_shape(fold_evidence_path) if fold_evidence_path.is_file() else None
    year_evidence_shape = _csv_evidence_shape(year_evidence_path) if year_evidence_path.is_file() else None
    _add_check(
        checks,
        blockers,
        check_id="fold_evidence_metadata_readable",
        passed=fold_evidence_shape is not None,
        detail=str(fold_evidence_shape),
    )
    _add_check(
        checks,
        blockers,
        check_id="year_evidence_csv_readable",
        passed=year_evidence_shape is not None,
        detail=str(year_evidence_shape),
    )

    if handoff is None:
        blockers.append("handoff_not_a_json_object")
        handoff = {}
    reported_tool_ids = sorted(_string_list(handoff.get("tool_ids")))
    reported_status = str(handoff.get("research_status", "missing"))
    _add_check(
        checks,
        blockers,
        check_id="tool_coverage_matches_lane",
        passed=set(reported_tool_ids) == set(spec.expected_tool_ids),
        detail=(f"expected={sorted(spec.expected_tool_ids)} reported={reported_tool_ids}"),
    )
    for key in _AUTHORITY_KEYS:
        _add_check(
            checks,
            blockers,
            check_id=f"authority_false:{key}",
            passed=handoff.get(key) is False,
            detail=str(handoff.get(key)),
        )
    _add_check(
        checks,
        blockers,
        check_id="post_2020_rows_used_zero",
        passed=handoff.get("post_2020_rows_used") == 0,
        detail=str(handoff.get("post_2020_rows_used")),
    )
    _add_check(
        checks,
        blockers,
        check_id="fresh_oos_false",
        passed=handoff.get("fresh_oos") is False,
        detail=str(handoff.get("fresh_oos")),
    )
    _add_check(
        checks,
        blockers,
        check_id="shared_files_modified_empty",
        passed=handoff.get("shared_files_modified") == [],
        detail=str(handoff.get("shared_files_modified")),
    )

    handoff_rows = _candidate_rows(handoff) or []
    registry_rows = _candidate_rows(registry) or []
    reported_candidate_count = handoff.get("candidate_mapping_count")
    if isinstance(reported_candidate_count, int):
        _add_check(
            checks,
            blockers,
            check_id="handoff_candidate_count_matches_rows",
            passed=reported_candidate_count == len(handoff_rows),
            detail=f"reported={reported_candidate_count} rows={len(handoff_rows)}",
        )
    registry_mapping = _mapping(registry)
    if registry_mapping is not None:
        registry_reported_count = registry_mapping.get("candidate_mapping_count")
        if registry_reported_count is None:
            registry_reported_count = registry_mapping.get("mapping_count")
        if isinstance(registry_reported_count, int):
            _add_check(
                checks,
                blockers,
                check_id="registry_declared_count_matches_rows",
                passed=registry_reported_count == len(registry_rows),
                detail=f"reported={registry_reported_count} rows={len(registry_rows)}",
            )

    handoff_ready_count = _ready_count(handoff_rows)
    declared_ready_count = handoff.get("ready_count")
    if isinstance(declared_ready_count, int):
        _add_check(
            checks,
            blockers,
            check_id="handoff_ready_count_matches_rows",
            passed=declared_ready_count == handoff_ready_count,
            detail=f"reported={declared_ready_count} rows={handoff_ready_count}",
        )
    for ready_index, ready_row in enumerate(row for row in handoff_rows if _status(row) == "ready_for_supervisor_replay"):
        evidence_ref = ready_row.get("event_evidence_ref")
        claimed_metrics = _mapping(ready_row.get("event_recomputed_metrics"))
        check_id = f"ready_event_recomputation:{ready_index}"
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            _add_check(
                checks,
                blockers,
                check_id=check_id,
                passed=False,
                detail=("repairable: add lane-relative event_evidence_ref and event_recomputed_metrics to the ready mapping"),
            )
            continue
        evidence_path = (lane_root / evidence_ref).resolve()
        try:
            _ = evidence_path.relative_to(lane_root.resolve())
        except ValueError:
            _add_check(
                checks,
                blockers,
                check_id=check_id,
                passed=False,
                detail="repairable: event evidence reference escapes the lane root",
            )
            continue
        if not evidence_path.is_file() or claimed_metrics is None:
            _add_check(
                checks,
                blockers,
                check_id=check_id,
                passed=False,
                detail="repairable: event evidence file or complete claimed metrics is missing",
            )
            continue
        try:
            recomputed = validate_event_evidence_claim(
                evidence_path,
                claimed_metrics,
            )
        except ValidationError as exc:
            _add_check(
                checks,
                blockers,
                check_id=check_id,
                passed=False,
                detail=f"repairable: {exc}",
            )
        else:
            _add_check(
                checks,
                blockers,
                check_id=check_id,
                passed=True,
                detail=json.dumps(recomputed, ensure_ascii=False, sort_keys=True),
            )
    final_verdict = _mapping(handoff.get("final_verdict"))
    final_ready_count = final_verdict.get("ready_for_supervisor_replay") if final_verdict is not None else None
    if isinstance(final_ready_count, int):
        _add_check(
            checks,
            blockers,
            check_id="final_verdict_ready_count_matches_handoff",
            passed=final_ready_count == handoff_ready_count,
            detail=f"final={final_ready_count} handoff={handoff_ready_count}",
        )
    report_claims_zero_ready = bool(_ZERO_READY_REPORT_PATTERN.search(report))
    if report_claims_zero_ready:
        _add_check(
            checks,
            blockers,
            check_id="report_zero_ready_matches_handoff",
            passed=handoff_ready_count == 0,
            detail=f"report=zero handoff={handoff_ready_count}",
        )

    ledger_post_2020 = ledger.get("post_2020_rows_used") if ledger else None
    _add_check(
        checks,
        blockers,
        check_id="data_ledger_post_2020_rows_used_zero",
        passed=ledger_post_2020 == 0,
        detail=str(ledger_post_2020),
    )

    source_paths = _lane_source_paths(project_root, handoff, spec.expected_tool_ids)
    relevant_paths.extend(source_paths)
    simplification_signals: list[str] = []
    for source_path in source_paths:
        try:
            source = source_path.read_text(encoding="utf-8")
        except OSError:
            continue
        if _SIMPLIFICATION_PATTERN.search(source):
            simplification_signals.append(source_path.relative_to(project_root).as_posix())
    if simplification_signals and reported_status == "ready_for_supervisor_replay":
        _add_check(
            checks,
            blockers,
            check_id="simplified_implementation_cannot_claim_ready",
            passed=False,
            detail=", ".join(simplification_signals),
        )

    authority = {key: handoff.get(key) is True for key in _AUTHORITY_KEYS}
    truth_status = "truth_gate_passed" if not blockers else "invalid_artifact_chain"
    return (
        {
            "lane_id": spec.lane_id,
            "artifact_root": spec.artifact_root,
            "expected_tool_ids": list(spec.expected_tool_ids),
            "reported_tool_ids": reported_tool_ids,
            "reported_status": reported_status,
            "truth_status": truth_status,
            "computed_counts": {
                "handoff_candidate_rows": len(handoff_rows),
                "handoff_ready_rows": handoff_ready_count,
                "registry_candidate_rows": len(registry_rows),
                "registry_ready_rows": _ready_count(registry_rows),
                "fold_evidence_rows": (fold_evidence_shape[0] if fold_evidence_shape is not None else 0),
                "fold_evidence_columns": (fold_evidence_shape[1] if fold_evidence_shape is not None else 0),
                "year_evidence_rows": (year_evidence_shape[0] if year_evidence_shape is not None else 0),
                "year_evidence_columns": (year_evidence_shape[1] if year_evidence_shape is not None else 0),
            },
            "artifacts": artifacts,
            "implementation": {
                "source_paths": [source_path.relative_to(project_root).as_posix() for source_path in source_paths],
                "simplification_signals": simplification_signals,
            },
            "checks": checks,
            "blockers": sorted(set(blockers)),
            "authority": authority,
        },
        relevant_paths,
    )


def _manifest_digest(payload: Mapping[str, object]) -> str:
    body = dict(payload)
    body.pop("manifest_semantic_digest", None)
    return canonical_digest(body)


def validate_research_replay_manifest(manifest: Mapping[str, object]) -> None:
    """Validate the self-contained, no-authority stage-0 manifest."""

    if manifest.get("schema_id") != RESEARCH_REPLAY_MANIFEST_SCHEMA_ID:
        raise ValidationError("research replay manifest schema id is invalid")
    if manifest.get("contract_version") != RESEARCH_REPLAY_MANIFEST_VERSION:
        raise ValidationError("research replay manifest version is invalid")
    reference_counts = _mapping(manifest.get("reference_counts"))
    if reference_counts is None:
        raise ValidationError("research replay manifest reference counts are missing")
    if reference_counts.get("tool_count") != 13 or reference_counts.get("lens_count") != 23:
        raise ValidationError("research replay manifest V1 tool/lens baseline changed")
    lanes = manifest.get("lanes")
    if not isinstance(lanes, list) or len(lanes) != len(LANE_TRUTH_SPECS):
        raise ValidationError("research replay manifest lane coverage is incomplete")
    all_expected = [tool_id for lane in lanes if isinstance(lane, Mapping) for tool_id in _string_list(lane.get("expected_tool_ids"))]
    if len(all_expected) != len(set(all_expected)):
        raise ValidationError("research replay manifest lane tools overlap")
    authority = _mapping(manifest.get("authority"))
    if authority is None or any(authority.get(key) is not False for key in _AUTHORITY_KEYS):
        raise ValidationError("research replay baseline cannot grant authority")
    has_invalid_lane = any(isinstance(lane, Mapping) and lane.get("truth_status") == "invalid_artifact_chain" for lane in lanes)
    expected_baseline_status = "baseline_truth_gate_failed" if has_invalid_lane else "baseline_truth_gate_passed"
    if manifest.get("baseline_status") != expected_baseline_status:
        raise ValidationError("research replay baseline status does not match lane truth")
    if manifest.get("manifest_semantic_digest") != _manifest_digest(manifest):
        raise ValidationError("research replay manifest digest mismatch")


def build_research_replay_baseline(project_root: Path) -> ResearchReplayBaseline:
    """Build the immutable, read-only baseline and its complete file inventory."""

    root = project_root.resolve()
    registry_payload = {"tools": [item.to_dict() for item in tool_specs()]}
    benchmarks = tuple(tool_benchmark_specs())
    benchmark_payload = {"benchmarks": [item.to_dict() for item in benchmarks]}
    parameter_payload = build_fixed_parameter_dictionary().to_dict()
    formula_payload = build_tool_formula_mechanism_bundle().to_dict()
    lanes: list[dict[str, object]] = []
    artifact_paths: list[Path] = [root / relative for relative in _CORE_SOURCE_PATHS]
    for spec in LANE_TRUTH_SPECS:
        lane, lane_paths = _audit_lane(root, spec)
        lanes.append(lane)
        artifact_paths.extend(lane_paths)

    source_artifacts = [_artifact_record(root, path) for path in sorted(set(artifact_paths)) if path.is_file()]
    relevant_paths = [str(item["relative_path"]) for item in source_artifacts]
    tool_count = len(registry_payload["tools"])
    lens_count = sum(len(item.parameters_by_frequency) for item in benchmarks)
    has_invalid_lane = any(lane["truth_status"] == "invalid_artifact_chain" for lane in lanes)
    manifest: dict[str, object] = {
        "schema_id": RESEARCH_REPLAY_MANIFEST_SCHEMA_ID,
        "contract_version": RESEARCH_REPLAY_MANIFEST_VERSION,
        "baseline_id": BASELINE_ID,
        "baseline_status": ("baseline_truth_gate_failed" if has_invalid_lane else "baseline_truth_gate_passed"),
        "reference_counts": {
            "tool_count": tool_count,
            "lens_count": lens_count,
            "lane_count": len(lanes),
            "lane_tool_count": sum(len(item.expected_tool_ids) for item in LANE_TRUTH_SPECS),
        },
        "authority": {key: False for key in _AUTHORITY_KEYS},
        "source_authority": {
            "tool_registry_semantic_digest": canonical_digest(registry_payload),
            "benchmark_semantic_digest": canonical_digest(benchmark_payload),
            "parameter_dictionary_semantic_digest": canonical_digest(parameter_payload),
            "formula_bundle_semantic_digest": canonical_digest(formula_payload),
        },
        "git_snapshot": _git_snapshot(root, relevant_paths),
        "source_artifacts": source_artifacts,
        "lanes": lanes,
        "artifact_inventory_ref": "artifact://artifact_inventory.json",
        "field_labels_zh": {
            "baseline_status": "基线真值门总体状态",
            "reference_counts": "权威13工具与23镜头数量对账",
            "source_authority": "源码、参数字典和公式权威摘要",
            "git_snapshot": "本地源码提交与相关未提交路径",
            "source_artifacts": "参与审计的源码和研究产物摘要",
            "lanes": "四条并行研究线的独立真值审计",
            "truth_status": "单研究线产物链真值状态",
            "computed_counts": "由原始JSON、Parquet元数据和CSV逐行读取独立计算的候选、ready与逐期证据规模",
            "implementation": "实际工具源码和简化实现信号",
            "checks": "逐项可重放检查结果",
            "blockers": "阻止ready或accepted的真值链问题",
        },
    }
    manifest["manifest_semantic_digest"] = _manifest_digest(manifest)
    validate_research_replay_manifest(manifest)

    git_snapshot = _mapping(manifest["git_snapshot"]) or {}
    inventory: dict[str, object] = {
        "schema_id": "market_state_artifact_inventory@1.0",
        "bundle_id": BASELINE_ID,
        "bundle_semantic_digest": manifest["manifest_semantic_digest"],
        "semantic_identity": {
            "schema_id": RESEARCH_REPLAY_MANIFEST_SCHEMA_ID,
            "reference_counts": manifest["reference_counts"],
            "source_authority": manifest["source_authority"],
        },
        "code_version": str(git_snapshot.get("revision", "unavailable")),
        "config_digest": canonical_digest(parameter_payload),
        "artifacts": source_artifacts,
        "field_labels_zh": {
            "bundle_semantic_digest": "基线真值门清单摘要",
            "semantic_identity": "基线语义身份",
            "code_version": "生成快照时的Git提交",
            "config_digest": "固定参数字典摘要",
            "artifacts": "已冻结输入产物",
        },
    }
    inventory["inventory_semantic_digest"] = canonical_digest(inventory)
    return ResearchReplayBaseline(manifest=manifest, artifact_inventory=inventory)


def write_research_replay_baseline(
    *,
    project_root: Path,
    output_dir: Path,
) -> ResearchReplayBaseline:
    """Write a new V2 snapshot without modifying any V1 lane artifact."""

    baseline = build_research_replay_baseline(project_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "market_state_research_replay_manifest.json").write_text(
        json.dumps(baseline.manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "artifact_inventory.json").write_text(
        json.dumps(baseline.artifact_inventory, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return baseline


__all__ = [
    "BASELINE_ID",
    "LANE_TRUTH_SPECS",
    "RESEARCH_REPLAY_MANIFEST_SCHEMA_ID",
    "RESEARCH_REPLAY_MANIFEST_VERSION",
    "ResearchReplayBaseline",
    "build_research_replay_baseline",
    "recompute_event_evidence",
    "validate_event_evidence_claim",
    "validate_research_replay_manifest",
    "write_research_replay_baseline",
]
