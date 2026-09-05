# pyright: reportPrivateUsage=false
"""Persistent search-scope registration for multiple-testing evidence."""

from __future__ import annotations

from collections.abc import Mapping

from factor_lab.governance.temporal_governance_repository import (
    TemporalGovernanceRepository,
    canonical_digest,
)


def register_search_scope_run(
    repository: TemporalGovernanceRepository,
    *,
    campaign_id: str,
    run_id: str,
    candidate_count: int,
    parameter_config_count: int,
    protocol_count: int,
    attempted_evaluation_count: int,
    rejected_count: int = 0,
    failed_count: int = 0,
    dataset_ref: str,
    window_ref: str,
    search_space_hash: str,
    status: str = "registered",
    metadata: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Record the real search size for one run."""

    payload = {
        "artifact_type": "search_scope_registration",
        "campaign_id": campaign_id,
        "run_id": run_id,
        "candidate_count": int(candidate_count),
        "parameter_config_count": int(parameter_config_count),
        "protocol_count": int(protocol_count),
        "attempted_evaluation_count": int(attempted_evaluation_count),
        "rejected_count": int(rejected_count),
        "failed_count": int(failed_count),
        "dataset_ref": dataset_ref,
        "window_ref": window_ref,
        "search_space_hash": search_space_hash,
        "status": status,
        "metadata": dict(metadata or {}),
    }
    blockers = _payload_blockers(payload)
    if blockers:
        return {"status": "blocked", "blockers": blockers, "payload": payload}
    result = repository._register_validated_search_scope_run(payload)
    return {**result, "payload": payload}


def register_historical_unknown_search_scope(
    repository: TemporalGovernanceRepository,
    *,
    campaign_id: str,
    run_id: str,
    dataset_ref: str,
    window_ref: str,
) -> dict[str, object]:
    """Register historical unknown search consumption as promotion-poisoning."""

    return register_search_scope_run(
        repository,
        campaign_id=campaign_id,
        run_id=run_id,
        candidate_count=0,
        parameter_config_count=0,
        protocol_count=0,
        attempted_evaluation_count=0,
        dataset_ref=dataset_ref,
        window_ref=window_ref,
        search_space_hash="unknown",
        status="consumed_unknown",
    )


def evaluate_search_scope_campaign(
    repository: TemporalGovernanceRepository, *, campaign_id: str
) -> dict[str, object]:
    """Return aggregate search-scope evidence for a campaign."""

    runs = repository.get_search_scope_runs(campaign_id)
    blockers: list[str] = []
    if not runs:
        blockers.append("search_scope_registry_report_missing")
    if any(str(run.get("status")) == "consumed_unknown" for run in runs):
        blockers.append("historical_unknown_search_scope_blocks_promotion")
    attempted_total = sum(_int(run.get("attempted_evaluation_count")) for run in runs)
    if runs and attempted_total <= 0:
        blockers.append("attempted_evaluation_count_required")
    report = {
        "artifact_type": "search_scope_campaign_report",
        "campaign_id": campaign_id,
        "run_count": len(runs),
        "attempted_evaluation_count": attempted_total,
        "candidate_count": sum(_int(run.get("candidate_count")) for run in runs),
        "parameter_config_count": sum(
            _int(run.get("parameter_config_count")) for run in runs
        ),
        "protocol_count": sum(_int(run.get("protocol_count")) for run in runs),
        "status": "blocked" if blockers else "available",
        "risk_status": "high_risk" if blockers else "registered",
        "blockers": blockers,
        "runs": list(runs),
    }
    return {**report, "canonical_digest": canonical_digest(report)}


def _payload_blockers(payload: Mapping[str, object]) -> list[str]:
    blockers: list[str] = []
    for key in (
        "campaign_id",
        "run_id",
        "dataset_ref",
        "window_ref",
        "search_space_hash",
    ):
        if not str(payload.get(key, "")).strip():
            blockers.append(f"{key}_required")
    for key in (
        "candidate_count",
        "parameter_config_count",
        "protocol_count",
        "attempted_evaluation_count",
    ):
        if _int(payload.get(key)) < 0:
            blockers.append(f"{key}_must_be_non_negative")
    if (
        str(payload.get("status")) != "consumed_unknown"
        and _int(payload.get("attempted_evaluation_count")) <= 0
    ):
        blockers.append("attempted_evaluation_count_required")
    return blockers


def _int(value: object) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


__all__ = [
    "evaluate_search_scope_campaign",
    "register_historical_unknown_search_scope",
    "register_search_scope_run",
]
