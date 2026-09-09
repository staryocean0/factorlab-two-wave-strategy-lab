"""Isolated v0.2 research candidates; the frozen v0.1 sources remain unchanged.

The two variants correct a measurement definition, not a fitted threshold.
Diagnostic attributes are NOT all rejection reasons in this schema.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from .engine import Engine
from .geometry import fit_geometry
from .models import Config, stable_id

CANDIDATE_SCHEMA = "two_wave_research_candidate@0.2.0"
VARIANTS = ("detrended_width", "drift_tolerant")


@dataclass(frozen=True)
class CandidateConfig(Config):
    geometry_variant: str = "detrended_width"

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.geometry_variant not in VARIANTS:
            raise ValueError(f"geometry_variant must be one of {VARIANTS}")

    @property
    def config_hash(self) -> str:
        return stable_id("cfg", {"schema_version": CANDIDATE_SCHEMA, **asdict(self)})


def fit_geometry_v02(pivots: list[dict], bars: list[dict], config: CandidateConfig) -> dict:
    """Refit at confirmation using only closes through the fifth extremum.

    A: replace raw pivot range ratio by all-close, common-drift-removed range
       ratio. Keep the v0.1 local speed agreement gate.
    B: same measurement correction, but local speed disagreement is an
       attribute. All other v0.1 fit/direction/width guards are retained.
    No outcome, return, post-confirmation bar, or human label is consulted.
    """
    if not isinstance(config, CandidateConfig):
        raise TypeError("v0.2 requires an explicitly versioned CandidateConfig")
    result = fit_geometry(pivots, bars, config)
    original = list(result["attributes"])
    result.update({
        "geometry_schema": CANDIDATE_SCHEMA,
        "geometry_variant": config.geometry_variant,
        "baseline_classification": result["classification"],
        "baseline_attributes": original,
        "rejection_reasons": list(original),
        "cycle_detrended_widths_log": None,
        "cycle_detrended_width_ratio": None,
        "diagnostic_attributes_are_not_rejection_reasons": True,
    })
    if not result["valid"]:
        return result
    start = pivots[0]["occurrence_bar"]
    middle = pivots[2]["occurrence_bar"]
    end = pivots[4]["occurrence_bar"]
    # The shared endpoint belongs to both complete cycles. Fit and raw reversal
    # definitions are unchanged; this is not detection of detrended oscillations.
    y = np.asarray([row["log_close"] for row in bars[start:end + 1]], dtype=float)
    z = y - result["b"] * np.arange(len(y), dtype=float)
    widths = [float(np.ptp(z[:middle - start + 1])), float(np.ptp(z[middle - start:]))]
    ratio = max(widths) / min(widths) if min(widths) > config.min_width else None
    blockers = [name for name in original if name != "cycle_amplitude_change"]
    attributes = list(original)
    if ratio is None or ratio > config.max_width_ratio:
        blockers.append("detrended_cycle_width_change")
        attributes.append("detrended_cycle_width_change")
    if config.geometry_variant == "drift_tolerant":
        blockers = [name for name in blockers if name != "uneven_phase_drift"]
    drift = result["D"]
    label = "uncertain"
    if not blockers:
        label = "range" if abs(drift) <= config.drift_threshold else ("uptrend" if drift > 0 else "downtrend")
    result.update({
        "classification": label,
        "attributes": attributes,
        "rejection_reasons": blockers,
        "cycle_detrended_widths_log": widths,
        "cycle_detrended_width_ratio": ratio,
        "cycle_width_basis": "all_completed_cycle_closes_minus_common_fitted_drift",
    })
    return result


class CandidateEngine(Engine):
    """Reuse frozen pivots and lifecycle; explicitly substitute geometry only.

    No process-global monkeypatch; independent instances can run side by side.
    The structure method mirrors v0.1 so its original bytes need not change.
    """

    def __init__(self, config: CandidateConfig | None = None):
        selected = config or CandidateConfig()
        if not isinstance(selected, CandidateConfig):
            raise TypeError("CandidateEngine requires CandidateConfig")
        super().__init__(selected)

    def _metadata(self) -> dict:
        return {**super()._metadata(), "schema_version": CANDIDATE_SCHEMA,
                "geometry_variant": self.config.geometry_variant}

    def _create_structure(self, points: list[dict], bar: dict) -> None:
        geometry = fit_geometry_v02(points, self.bars, self.config)
        cycle_ids = [self._cycles_by_ends[(points[i]["pivot_id"], points[i + 2]["pivot_id"])]["cycle_id"] for i in (0, 2)]
        structure = {
            **self._metadata(),
            **self._known(),
            "phase": points[0]["kind"],
            "pivot_ids": [p["pivot_id"] for p in points],
            "cycle_ids": cycle_ids,
            "start_bar": points[0]["occurrence_bar"],
            "end_bar": points[-1]["occurrence_bar"],
            "start_time": points[0]["occurrence_time"],
            "end_time": points[-1]["occurrence_time"],
            "occurrence_bar": points[-1]["occurrence_bar"],
            "occurrence_time": points[-1]["occurrence_time"],
            "confirmation_bar": bar["bar_index"],
            "confirmation_time": bar["timestamp"],
            "classification_time": bar["timestamp"],
            "classification_available_time": self._availability.isoformat(),
            "effective_information_time": self._availability.isoformat(),
            "confirmation_delay_bars": bar["bar_index"] - points[-1]["occurrence_bar"],
            "version": 1,
            "effective_from_bar": bar["bar_index"],
            "effective_from_time": bar["timestamp"],
            "initial_cycle_count": 2,
            "geometry": geometry,
            "classification": geometry["classification"],
            "attributes": list(geometry["attributes"]),
            "rejection_reasons": list(geometry["rejection_reasons"]),
            "authority_status": "research_only_morphology_not_accepted",
            "parent_definition": "local_envelope_of_two_same_scale_cycles",
        }
        structure["structure_id"] = stable_id("structure", [self.config.config_hash, structure["pivot_ids"]])
        self.structures.append(structure)
        key = structure["structure_id"]
        self._states[key] = {
            "cycle_count": 2,
            "geometry_alive": geometry["valid"],
            "first_breakout_event_id": None,
            "first_breakout_bar": None,
            "last_cycle_id": cycle_ids[-1],
            "last_cycle_confirmation_bar": bar["bar_index"],
            "end_reason": None if geometry["valid"] else "invalid_geometry",
            "confirmation_bar": bar["bar_index"],
        }
        self._event(
            "structure_confirmed",
            bar,
            structure_id=key,
            classification=structure["classification"],
            cycle_count=2,
            occurrence_bar=structure["end_bar"],
            occurrence_time=structure["end_time"],
        )
        if geometry["valid"]:
            self._active[key] = structure
            self._check_breakout(structure, bar, at_confirmation=True)

