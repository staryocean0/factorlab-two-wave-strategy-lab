"""Output-equivalent performance wrapper for the frozen v0.5.1 experiment.

Research logic is unchanged.  The only optimization is to precompute the
prefix maximum information clock once, instead of letting frozen evaluate_pair
rescan bars[:confirmation+1] for every characteristic event.
"""
from __future__ import annotations

import numpy as np

from .characteristic_scale_v051 import (
    RAW_PROJECTION,
    SCHEMA,
    SELECTOR,
    CharacteristicExclusiveLedger,
    CharacteristicRun,
    build_candidate_features,
    characteristic_events,
    link_candidate_families,
    project_event_to_raw,
)
from .models import stable_id
from .same_scale_v04 import evaluate_pair
from .same_scale_v043 import MaturityConfig


def bars_with_prefix_information_clock(bars: list[dict]) -> list[dict]:
    """Copy bars and fill only missing effective-information clocks.

    For a row without an existing effective_information_time, the inserted
    value is exactly:

        max(v.get('available_at', v['timestamp']) for v in bars[:i+1])

    which is the fallback used by frozen evaluate_pair.  Existing non-empty
    effective_information_time values are preserved verbatim.
    """

    if not bars:
        raise ValueError("bars are required")
    prefix_available = None
    out: list[dict] = []
    for bar in bars:
        row = dict(bar)
        available = row.get("available_at", row["timestamp"])
        prefix_available = available if prefix_available is None else max(prefix_available, available)
        if not row.get("effective_information_time"):
            row["effective_information_time"] = prefix_available
        out.append(row)
    return out


def build_characteristic_run_fast(
    bars: list[dict],
    cfg: MaturityConfig | None = None,
    sigmas=None,
) -> CharacteristicRun:
    """Frozen v0.5.1 with an O(n) information-clock precomputation."""

    if not bars:
        raise ValueError("bars are required")
    cfg = cfg or MaturityConfig()
    closes = np.asarray([bar["close"] for bar in bars], dtype=float)
    if not np.isfinite(closes).all() or np.any(closes <= 0):
        raise ValueError("positive finite closes required")
    log_close = np.log(closes)
    levels, _, features_by_level = build_candidate_features(log_close, sigmas)
    members = link_candidate_families(features_by_level, levels)
    events = characteristic_events(members)

    evaluation_bars = bars_with_prefix_information_clock(bars)
    projection_audit = []
    evaluated = []
    for event in events:
        projection = project_event_to_raw(event, bars, closes)
        audit = {
            "event_id": event.event_id,
            "family_id": event.family_id,
            "characteristic_scale_level": event.level,
            "characteristic_scale_id": event.scale_id,
            "characteristic_sigma_bars": event.sigma_bars,
            "filtered_occurrence_bars": list(event.feature.occurrence_indices),
            "filtered_member_confirmation_bar": event.feature.confirmation_index,
            "characteristic_confirmation_bar": event.confirmation_index,
            "scale_selection_delay_bars": event.scale_selection_delay_bars,
            "common_response": event.feature.common_response,
            "finer_response": event.finer_feature.common_response,
            "coarser_response": event.coarser_feature.common_response,
            "projection_valid": bool(projection["valid"]),
            "projection_reason": projection.get("reason"),
        }
        if projection["valid"]:
            audit["raw_occurrence_bars"] = list(projection["raw_occurrence_indices"])
            try:
                record = evaluate_pair(
                    list(projection["points"]),
                    evaluation_bars,
                    cfg,
                    source="TCSS_v051_characteristic",
                )
            except ValueError as exc:
                audit["projection_valid"] = False
                audit["projection_reason"] = f"evaluate_pair_invalid:{exc}"
            else:
                record["schema_version"] = SCHEMA
                record["record_id"] = stable_id(
                    "tcss_characteristic_pair_v051",
                    {
                        "event_id": event.event_id,
                        "raw_occurrences": projection["raw_occurrence_indices"],
                        "cfg": cfg.config_hash,
                    },
                )
                record["source"] = "TCSS_v051_characteristic"
                record["characteristic_selector"] = SELECTOR
                record["characteristic_event_id"] = event.event_id
                record["characteristic_family_id"] = event.family_id
                record["characteristic_scale_level"] = event.level
                record["characteristic_scale_id"] = event.scale_id
                record["characteristic_sigma_bars"] = event.sigma_bars
                record["characteristic_common_response"] = event.feature.common_response
                record["characteristic_finer_response"] = event.finer_feature.common_response
                record["characteristic_coarser_response"] = event.coarser_feature.common_response
                record["filtered_occurrence_bars"] = list(event.feature.occurrence_indices)
                record["filtered_member_confirmation_bar"] = event.feature.confirmation_index
                record["scale_selection_confirmation_bar"] = event.confirmation_index
                record["scale_selection_delay_bars"] = event.scale_selection_delay_bars
                record["raw_projection_method"] = RAW_PROJECTION
                record["raw_projection_frozen_at_member_confirmation_bar"] = projection[
                    "projection_frozen_at_member_confirmation_bar"
                ]
                record["trade_authority"] = False
                record["future_outcome_used"] = False
                evaluated.append(record)
        projection_audit.append(audit)

    ledger = CharacteristicExclusiveLedger()
    ledger.add_records(evaluated)
    return CharacteristicRun(
        scale_levels=levels,
        features_by_level=features_by_level,
        family_members=members,
        characteristic_events=events,
        projection_audit=projection_audit,
        evaluated_records=evaluated,
        ledger=ledger,
    )
