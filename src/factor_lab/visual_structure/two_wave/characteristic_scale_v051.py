"""v0.5.1 characteristic-scale selector over the frozen TCSS representation.

This module is a morphology research component, not a trading strategy.  It
adds one thing to v0.5.0: a causal characteristic-scale identity based on local
maxima over scale of a scale-normalized second temporal derivative response.
The selected TCSS member is then projected back to five exact raw-close extrema
before the unchanged v0.4.3 qualification/D1 logic is called.

No outcome, IoU, case label or P&L enters scale selection.
"""
from __future__ import annotations

import bisect
import copy
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .models import stable_id
from .multiscale_v050 import (
    ScaleLevel,
    TwoWaveCandidate,
    build_scale_levels,
    confirmed_extrema,
    default_scale_sigmas,
    time_causal_scale_space,
    two_wave_candidates,
)
from .same_scale_v04 import evaluate_pair
from .same_scale_v043 import MaturityConfig

SCHEMA = "two_wave_characteristic_scale@0.5.1"
SELECTOR = "tcss_scale_normalized_second_derivative_family_local_max"
RAW_PROJECTION = "sequential_raw_close_extreme_inside_filtered_phase_bounds"
DERIVATIVE_ORDER = 2
GAMMA = 0.75


@dataclass(frozen=True)
class CandidateFeature:
    """One five-extrema TCSS candidate with a common-scale response."""

    level: int
    scale_id: str
    sigma_bars: float
    phase: str
    occurrence_indices: tuple[int, ...]
    confirmation_index: int
    corrected_center: float
    common_response: float | None
    candidate: TwoWaveCandidate
    member_id: str


@dataclass(frozen=True)
class FamilyMember:
    family_id: str
    feature: CandidateFeature


@dataclass(frozen=True)
class CharacteristicEvent:
    event_id: str
    family_id: str
    level: int
    scale_id: str
    sigma_bars: float
    feature: CandidateFeature
    finer_feature: CandidateFeature
    coarser_feature: CandidateFeature
    confirmation_index: int
    scale_selection_delay_bars: int


@dataclass
class CharacteristicRun:
    scale_levels: tuple[ScaleLevel, ...]
    features_by_level: tuple[tuple[CandidateFeature, ...], ...]
    family_members: list[FamilyMember]
    characteristic_events: list[CharacteristicEvent]
    projection_audit: list[dict]
    evaluated_records: list[dict]
    ledger: "CharacteristicExclusiveLedger"


def kernel_mean_ages(levels: Iterable[ScaleLevel]) -> tuple[float, ...]:
    """Cumulative kernel mean ages; descriptive/matching only, never left-shifted."""

    out = []
    total = 0.0
    for level in levels:
        if level.pole:
            total += level.pole / (1.0 - level.pole)
        out.append(total)
    return tuple(out)


def _signed_second_difference(series: np.ndarray, occurrence: int, kind: str) -> float | None:
    if occurrence < 2:
        return None
    d2 = float(series[occurrence] - 2.0 * series[occurrence - 1] + series[occurrence - 2])
    if kind == "high":
        return -d2
    if kind == "low":
        return d2
    raise ValueError("extremum kind must be high or low")


def common_scale_response(candidate: TwoWaveCandidate, series: np.ndarray, sigma_bars: float) -> float | None:
    """Weakest five-phase scale-normalized curvature response.

    With n=2 and gamma=3/4, tau^(n*gamma/2) = sigma^(3/2).  Requiring every
    point to have positive signed curvature implements a common-scale gate; one
    strong extremum cannot compensate for an unsupported phase.
    """

    if not math.isfinite(sigma_bars) or sigma_bars <= 0:
        raise ValueError("sigma_bars must be finite positive")
    responses = []
    factor = sigma_bars ** (DERIVATIVE_ORDER * GAMMA)
    for point in candidate.extrema:
        signed = _signed_second_difference(series, point.occurrence_index, point.kind)
        if signed is None or signed <= 0 or not math.isfinite(signed):
            return None
        responses.append(factor * signed)
    return float(min(responses))


def build_candidate_features(
    values: Iterable[float],
    sigmas: Iterable[float] | None = None,
) -> tuple[tuple[ScaleLevel, ...], dict[str, np.ndarray], tuple[tuple[CandidateFeature, ...], ...]]:
    """Build prefix-native TCSS candidate features at all frozen scales."""

    levels = build_scale_levels(default_scale_sigmas() if sigmas is None else sigmas)
    scale_space = time_causal_scale_space(values, [level.sigma_bars for level in levels])
    ages = kernel_mean_ages(levels)
    all_features = []
    for level in levels:
        series = scale_space[level.scale_id]
        extrema = confirmed_extrema(series, level.scale_id)
        candidates = two_wave_candidates(extrema)
        rows = []
        for candidate in candidates:
            occurrences = candidate.occurrence_indices
            phase = candidate.extrema[0].kind
            response = common_scale_response(candidate, series, level.sigma_bars)
            member_id = stable_id(
                "tcss_candidate_member_v051",
                {
                    "schema": SCHEMA,
                    "scale": level.scale_id,
                    "phase": phase,
                    "occurrences": occurrences,
                    "confirmation": candidate.confirmation_index,
                },
            )
            rows.append(
                CandidateFeature(
                    level=level.level,
                    scale_id=level.scale_id,
                    sigma_bars=level.sigma_bars,
                    phase=phase,
                    occurrence_indices=occurrences,
                    confirmation_index=candidate.confirmation_index,
                    corrected_center=float(occurrences[2]) - ages[level.level],
                    common_response=response,
                    candidate=candidate,
                    member_id=member_id,
                )
            )
        all_features.append(tuple(rows))
    return levels, scale_space, tuple(all_features)


def _root_family_id(feature: CandidateFeature) -> str:
    return stable_id("tcss_characteristic_family_v051", {"root_member_id": feature.member_id})


def _match_one_phase(
    fine_members: list[FamilyMember],
    coarse_features: list[CandidateFeature],
    coarse_sigma: float,
) -> tuple[list[FamilyMember], list[FamilyMember]]:
    """Causal monotone one-to-one family matching for one start phase."""

    fine = sorted(fine_members, key=lambda m: (m.feature.corrected_center, m.feature.confirmation_index, m.feature.member_id))
    coarse = sorted(coarse_features, key=lambda f: (f.corrected_center, f.confirmation_index, f.member_id))
    if any(a.feature.corrected_center > b.feature.corrected_center for a, b in zip(fine, fine[1:])):
        raise ValueError("fine centers must be ordered")
    confirmations = [m.feature.confirmation_index for m in fine]
    if any(a > b for a, b in zip(confirmations, confirmations[1:])):
        raise ValueError("fine confirmations must be monotone within phase")
    centers = [m.feature.corrected_center for m in fine]
    gate = int(math.ceil(coarse_sigma))
    last_used = -1
    matched: list[FamilyMember] = []
    new_roots: list[FamilyMember] = []

    for feature in coarse:
        lo = last_used + 1
        hi = bisect.bisect_right(confirmations, feature.confirmation_index)
        chosen = None
        if lo < hi:
            pos = bisect.bisect_left(centers, feature.corrected_center, lo, hi)
            options = []
            for idx in (pos - 1, pos):
                if lo <= idx < hi:
                    distance = abs(centers[idx] - feature.corrected_center)
                    options.append((distance, fine[idx].feature.confirmation_index, fine[idx].feature.member_id, idx))
            if options:
                distance, _, _, idx = min(options)
                if distance <= gate:
                    chosen = idx

        if chosen is None:
            member = FamilyMember(_root_family_id(feature), feature)
            new_roots.append(member)
            matched.append(member)
        else:
            last_used = chosen
            matched.append(FamilyMember(fine[chosen].family_id, feature))
    return matched, new_roots


def link_candidate_families(
    features_by_level: tuple[tuple[CandidateFeature, ...], ...],
    levels: tuple[ScaleLevel, ...],
) -> list[FamilyMember]:
    """Link adjacent scale candidates without outcome- or case-driven matching."""

    if len(features_by_level) != len(levels):
        raise ValueError("feature levels and scale levels must align")
    all_members: list[FamilyMember] = []
    previous: list[FamilyMember] = []

    for j, features in enumerate(features_by_level):
        if j == 0:
            current = [FamilyMember(_root_family_id(feature), feature) for feature in features]
        else:
            current = []
            for phase in ("low", "high"):
                fine_phase = [m for m in previous if m.feature.phase == phase]
                coarse_phase = [f for f in features if f.phase == phase]
                phase_members, _ = _match_one_phase(fine_phase, coarse_phase, levels[j].sigma_bars)
                current.extend(phase_members)
            current.sort(key=lambda m: (m.feature.corrected_center, m.feature.phase, m.feature.member_id))
        all_members.extend(current)
        previous = current
    return all_members


def characteristic_events(family_members: Iterable[FamilyMember]) -> list[CharacteristicEvent]:
    """Select local maxima over scale; the coarser neighbor sets information time."""

    grouped: dict[str, dict[int, CandidateFeature]] = defaultdict(dict)
    for member in family_members:
        level = member.feature.level
        if level in grouped[member.family_id]:
            raise ValueError("one family may have at most one member per scale")
        grouped[member.family_id][level] = member.feature

    out = []
    for family_id, by_level in grouped.items():
        for level, feature in sorted(by_level.items()):
            if level - 1 not in by_level or level + 1 not in by_level:
                continue
            finer, coarser = by_level[level - 1], by_level[level + 1]
            responses = (finer.common_response, feature.common_response, coarser.common_response)
            if any(v is None or not math.isfinite(v) or v <= 0 for v in responses):
                continue
            if not (feature.common_response > finer.common_response and feature.common_response >= coarser.common_response):
                continue
            confirmation = max(finer.confirmation_index, feature.confirmation_index, coarser.confirmation_index)
            event_id = stable_id(
                "tcss_characteristic_event_v051",
                {
                    "family_id": family_id,
                    "level": level,
                    "member": feature.member_id,
                    "finer": finer.member_id,
                    "coarser": coarser.member_id,
                    "confirmation": confirmation,
                },
            )
            out.append(
                CharacteristicEvent(
                    event_id=event_id,
                    family_id=family_id,
                    level=level,
                    scale_id=feature.scale_id,
                    sigma_bars=feature.sigma_bars,
                    feature=feature,
                    finer_feature=finer,
                    coarser_feature=coarser,
                    confirmation_index=confirmation,
                    scale_selection_delay_bars=confirmation - feature.confirmation_index,
                )
            )
    out.sort(key=lambda e: (e.confirmation_index, e.level, e.feature.occurrence_indices, e.event_id))
    return out


def _last_argextreme(values: np.ndarray, kind: str) -> tuple[int, float]:
    target = float(np.max(values)) if kind == "high" else float(np.min(values))
    positions = np.flatnonzero(values == target)
    if not len(positions):
        raise ValueError("empty extreme positions")
    return int(positions[-1]), target


def project_event_to_raw(event: CharacteristicEvent, bars: list[dict]) -> dict:
    """Project one characteristic TCSS member to five immutable raw-close extrema."""

    filtered = event.feature.occurrence_indices
    member_confirmation = event.feature.confirmation_index
    selection_confirmation = event.confirmation_index
    if selection_confirmation >= len(bars) or member_confirmation >= len(bars):
        return {"event_id": event.event_id, "valid": False, "reason": "confirmation_outside_bars"}
    closes = np.asarray([bar["close"] for bar in bars], dtype=float)
    kinds = [point.kind for point in event.feature.candidate.extrema]
    left = max(0, 2 * filtered[0] - filtered[1])
    uppers = [filtered[1] - 1, filtered[2] - 1, filtered[3] - 1, filtered[4] - 1, member_confirmation]
    occurrences = []
    prices = []
    lo = left
    for ordinal, (kind, hi) in enumerate(zip(kinds, uppers)):
        hi = min(int(hi), member_confirmation)
        if lo > hi:
            return {
                "event_id": event.event_id,
                "valid": False,
                "reason": "raw_projection_empty_phase_window",
                "phase_ordinal": ordinal,
                "lo": lo,
                "hi": hi,
            }
        rel, price = _last_argextreme(closes[lo : hi + 1], kind)
        occurrence = lo + rel
        occurrences.append(occurrence)
        prices.append(price)
        lo = occurrence + 1

    if any(a >= b for a, b in zip(occurrences, occurrences[1:])):
        return {"event_id": event.event_id, "valid": False, "reason": "raw_projection_order_conflict"}
    for kind, a, b in zip(kinds, prices, prices[1:]):
        if kind == "low" and not b > a:
            return {"event_id": event.event_id, "valid": False, "reason": "raw_projection_not_actual_turn"}
        if kind == "high" and not b < a:
            return {"event_id": event.event_id, "valid": False, "reason": "raw_projection_not_actual_turn"}

    points = []
    confirmation_time = bars[selection_confirmation]["timestamp"]
    known = bars[selection_confirmation].get("available_at", confirmation_time)
    for ordinal, (kind, occurrence, price) in enumerate(zip(kinds, occurrences, prices)):
        point = {
            "kind": kind,
            "occurrence_bar": int(occurrence),
            "occurrence_time": bars[occurrence]["timestamp"],
            "price": float(price),
            "log_price": math.log(float(price)),
            "left_censored": False,
            "confirmation_bar": int(selection_confirmation),
            "confirmation_time": confirmation_time,
            "effective_information_time": known,
            "confirmation_delay_bars": int(selection_confirmation - occurrence),
            "bar_end_assumed": False,
            "epoch": 0,
            "confirmation_mode": "tcss_characteristic_scale_then_raw_projection_v051",
            "source_characteristic_event_id": event.event_id,
            "source_filtered_occurrence_bar": int(filtered[ordinal]),
            "source_filtered_member_confirmation_bar": int(member_confirmation),
        }
        point["pivot_id"] = stable_id(
            "tcss_raw_parent_pivot_v051",
            {
                "event": event.event_id,
                "ordinal": ordinal,
                "kind": kind,
                "occurrence": occurrence,
                "price": float(price),
                "selection_confirmation": selection_confirmation,
            },
        )
        points.append(point)

    return {
        "event_id": event.event_id,
        "valid": True,
        "reason": None,
        "raw_occurrence_indices": tuple(occurrences),
        "raw_prices": tuple(prices),
        "points": tuple(points),
        "projection_frozen_at_member_confirmation_bar": int(member_confirmation),
        "characteristic_confirmation_bar": int(selection_confirmation),
        "raw_projection_method": RAW_PROJECTION,
    }


class CharacteristicExclusiveLedger:
    """Causal multi-scale greedy packing with deterministic same-time priority."""

    def __init__(self):
        self.records: list[dict] = []
        self.selected: list[dict] = []
        self.events: list[dict] = []
        self._end = -1

    @staticmethod
    def priority(record: dict):
        return (
            record["confirmation_bar"],
            record["characteristic_scale_level"],
            record["start_bar"],
            record["end_bar"],
            record["record_id"],
        )

    def add_records(self, records: Iterable[dict]) -> None:
        for source in sorted(records, key=self.priority):
            record = copy.deepcopy(source)
            record["selected"] = False
            record["overlap_suppressed_by"] = None
            if record["scale_qualified"] and record["start_bar"] >= self._end:
                record["selected"] = True
                self._end = record["end_bar"]
                self.selected.append(copy.deepcopy(record))
                self.events.append(
                    {
                        "confirmation_bar": record["confirmation_bar"],
                        "confirmation_time": record["confirmation_time"],
                        "effective_information_time": record["known_at"],
                        "record_id": record["record_id"],
                        "label": record["classification"],
                        "historical_start_exclusive": record["start_bar"],
                        "historical_end_inclusive": record["end_bar"],
                        "characteristic_scale_id": record["characteristic_scale_id"],
                        "event_only_not_current_state": True,
                    }
                )
            elif record["scale_qualified"] and self.selected:
                record["overlap_suppressed_by"] = self.selected[-1]["record_id"]
            self.records.append(copy.deepcopy(record))


def build_characteristic_run(
    bars: list[dict],
    cfg: MaturityConfig | None = None,
    sigmas: Iterable[float] | None = None,
) -> CharacteristicRun:
    """Run v0.5.1 end-to-end through frozen qualification/D1, no outcomes."""

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

    projection_audit = []
    evaluated = []
    for event in events:
        projection = project_event_to_raw(event, bars)
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
                record = evaluate_pair(list(projection["points"]), bars, cfg, source="TCSS_v051_characteristic")
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
