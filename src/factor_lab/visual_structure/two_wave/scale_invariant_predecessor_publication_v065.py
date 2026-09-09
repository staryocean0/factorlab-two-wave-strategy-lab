"""v0.6.5 append-only publication for predecessor-supported raw identity.

This module does not change v0.6.4 projection geometry. It only turns ordered
member-level candidate evidence into at most one immutable raw identity event
per canonical filtered identity.
"""
from __future__ import annotations

import hashlib
import json
from typing import Sequence

SCHEMA = "two_wave_scale_invariant_predecessor_publication@0.6.5"
CANDIDATE = "first_valid_causal_predecessor_projection_publication"


def _stable_id(namespace: str, payload: object) -> str:
    raw = json.dumps([namespace, payload], sort_keys=True, separators=(",", ":"), allow_nan=False)
    return f"{namespace}_{hashlib.sha256(raw.encode()).hexdigest()[:20]}"


def evidence_order_key(row: dict) -> tuple[int, int, str]:
    return (
        int(row["birth_confirmation_bar"]),
        int(row["birth_level"]),
        str(row["event_id"]),
    )


def publish_first_valid_candidate(
    phase: str,
    five_filtered_occurrence_bars: Sequence[int],
    member_rows: Sequence[dict],
) -> dict:
    """Publish once from first valid causal evidence; later evidence never rewrites.

    ``member_rows`` are frozen v0.6.4 member-specific candidate results plus the
    causal birth ordering fields. Cross-view information is intentionally absent.
    """
    if phase not in {"low", "high"}:
        raise ValueError("phase must be low or high")
    filtered = tuple(int(x) for x in five_filtered_occurrence_bars)
    if len(filtered) != 5 or any(b <= a for a, b in zip(filtered, filtered[1:])):
        raise ValueError("five strictly increasing filtered occurrence bars required")
    if not member_rows:
        raise ValueError("at least one evidence member required")

    ordered = sorted((dict(row) for row in member_rows), key=evidence_order_key)
    publication = None
    evidence_events = []
    prior_invalid = 0
    suppressed_rewrite = 0

    for row in ordered:
        valid = bool(row.get("valid"))
        raw = row.get("raw_occurrence_bars")
        if valid:
            if raw is None:
                raise ValueError("valid member requires raw_occurrence_bars")
            raw_tuple = tuple(int(x) for x in raw)
            if len(raw_tuple) != 5 or any(b <= a for a, b in zip(raw_tuple, raw_tuple[1:])):
                raise ValueError("valid raw identity must contain five strictly increasing bars")
        else:
            raw_tuple = None

        disposition: str
        would_rewrite = False
        if publication is None:
            if not valid:
                disposition = "invalid_before_publication"
                prior_invalid += 1
            else:
                publication = {
                    "schema": SCHEMA,
                    "candidate": CANDIDATE,
                    "canonical_filtered_identity_id": _stable_id(
                        "canonical_filtered_identity_v065", [phase, list(filtered)]
                    ),
                    "publication_event_id": _stable_id(
                        "raw_projection_publication_v065",
                        [phase, list(filtered), str(row["event_id"]), list(raw_tuple)],
                    ),
                    "phase": phase,
                    "five_filtered_occurrence_bars": list(filtered),
                    "publishing_member_event_id": str(row["event_id"]),
                    "publishing_birth_level": int(row["birth_level"]),
                    "publishing_birth_confirmation_bar": int(row["birth_confirmation_bar"]),
                    "predecessor_occurrence_bar": (
                        int(row["predecessor_occurrence_bar"])
                        if row.get("predecessor_occurrence_bar") is not None
                        else None
                    ),
                    "predecessor_confirmation_bar": (
                        int(row["predecessor_confirmation_bar"])
                        if row.get("predecessor_confirmation_bar") is not None
                        else None
                    ),
                    "published_raw_occurrence_bars": list(raw_tuple),
                    "prior_invalid_evidence_count": prior_invalid,
                    "future_outcome_used": False,
                    "trade_authority": False,
                }
                disposition = "publishing_evidence"
        else:
            if not valid:
                disposition = "invalid_after_publication"
            else:
                would_rewrite = list(raw_tuple) != publication["published_raw_occurrence_bars"]
                if would_rewrite:
                    suppressed_rewrite += 1
                    disposition = "later_valid_would_rewrite_suppressed"
                else:
                    disposition = "later_valid_same_identity"

        evidence_events.append(
            {
                "schema": SCHEMA,
                "canonical_filtered_identity_id": _stable_id(
                    "canonical_filtered_identity_v065", [phase, list(filtered)]
                ),
                "event_id": str(row["event_id"]),
                "birth_level": int(row["birth_level"]),
                "birth_confirmation_bar": int(row["birth_confirmation_bar"]),
                "candidate_valid": valid,
                "candidate_reason": row.get("reason"),
                "counterfactual_raw_occurrence_bars": list(raw_tuple) if raw_tuple is not None else None,
                "disposition": disposition,
                "would_rewrite_published_identity": would_rewrite,
                "future_outcome_used": False,
                "trade_authority": False,
            }
        )

    return {
        "schema": SCHEMA,
        "candidate": CANDIDATE,
        "phase": phase,
        "five_filtered_occurrence_bars": list(filtered),
        "status": "published_single_identity" if publication is not None else "no_valid_published_projection",
        "publication_event": publication,
        "evidence_events": evidence_events,
        "evidence_member_count": len(ordered),
        "suppressed_would_be_rewrite_count": suppressed_rewrite,
        "future_outcome_used": False,
        "trade_authority": False,
    }
