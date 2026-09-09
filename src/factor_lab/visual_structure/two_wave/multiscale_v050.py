"""v0.5 pre-study primitives for causal multiscale two-wave representation.

This is research POC code, not an accepted recognizer.  It implements only the
first production-candidate representation from the frozen v0.5 protocol:
a one-dimensional time-causal scale-space built as cascaded first-order
recursive filters.  It deliberately does not call qualification, D1, trading,
or outcome logic.

The scale parameter is the standard deviation (in bars) of the *smoothing
kernel*, not a wave-duration threshold.  Increasing scale is therefore a
representation operation, not the v0.4.4 rule "close when a cycle first reaches
N bars".
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np

SCHEMA = "two_wave_multiscale_poc@0.5.0-prestudy"
REPRESENTATION = "time_causal_recursive_scale_space"
RAW_WAVE_SEMANTICS = "raw_reversal"


@dataclass(frozen=True)
class ScaleLevel:
    """One cumulative causal scale-space level."""

    level: int
    sigma_bars: float
    added_variance: float
    pole: float

    @property
    def scale_id(self) -> str:
        return f"tcss_sigma_{self.sigma_bars:.12g}"


@dataclass(frozen=True)
class ConfirmedExtremum:
    """A causal extremum: occurrence is known only at confirmation_index."""

    scale_id: str
    kind: str
    occurrence_index: int
    confirmation_index: int
    value: float


@dataclass(frozen=True)
class TwoWaveCandidate:
    """Five alternating extrema forming two adjacent complete cycles."""

    scale_id: str
    extrema: tuple[ConfirmedExtremum, ...]

    @property
    def occurrence_indices(self) -> tuple[int, ...]:
        return tuple(p.occurrence_index for p in self.extrema)

    @property
    def confirmation_index(self) -> int:
        return self.extrema[-1].confirmation_index

    @property
    def cycle_durations(self) -> tuple[int, int]:
        p = self.occurrence_indices
        return p[2] - p[0], p[4] - p[2]


def default_scale_sigmas() -> tuple[float, ...]:
    """Pre-fixed geometric scale lattice, independent of real-data outcomes.

    The ladder spans kernel standard deviations from 0.5 to about 45 bars in
    half-octave increments.  These are smoothing scales, not parent-cycle
    closure limits and are intentionally not derived from the old 12--48
    qualification band.
    """

    root2 = math.sqrt(2.0)
    return tuple(0.5 * root2**i for i in range(14))


def _pole_for_discrete_geometric_variance(variance: float) -> float:
    """Return the stable pole whose normalized geometric kernel has variance v.

    For y[n] = (1-a)x[n] + a y[n-1], the impulse response is
    (1-a) a**k, k>=0, with discrete variance a/(1-a)**2.  Solving
    v = a/(1-a)**2 for the root in [0,1) gives the expression below.
    """

    if not math.isfinite(variance) or variance < 0:
        raise ValueError("variance must be finite and nonnegative")
    if variance == 0:
        return 0.0
    return ((2.0 * variance + 1.0) - math.sqrt(4.0 * variance + 1.0)) / (2.0 * variance)


def build_scale_levels(sigmas: Iterable[float] | None = None) -> tuple[ScaleLevel, ...]:
    values = tuple(default_scale_sigmas() if sigmas is None else sigmas)
    if not values:
        raise ValueError("at least one scale is required")
    if any(not math.isfinite(s) or s <= 0 for s in values):
        raise ValueError("scale sigmas must be finite positive")
    if any(b <= a for a, b in zip(values, values[1:])):
        raise ValueError("scale sigmas must be strictly increasing")

    levels = []
    previous_variance = 0.0
    for i, sigma in enumerate(values):
        target_variance = float(sigma) ** 2
        added_variance = target_variance - previous_variance
        pole = _pole_for_discrete_geometric_variance(added_variance)
        levels.append(ScaleLevel(i, float(sigma), added_variance, pole))
        previous_variance = target_variance
    return tuple(levels)


def _causal_first_order(values: np.ndarray, pole: float) -> np.ndarray:
    if not 0 <= pole < 1:
        raise ValueError("pole must lie in [0, 1)")
    if values.ndim != 1 or values.size == 0:
        raise ValueError("values must be a nonempty one-dimensional series")
    out = np.empty_like(values, dtype=float)
    # Constant pre-history equal to the first observation avoids fabricating an
    # artificial jump at the left boundary and uses no future information.
    out[0] = float(values[0])
    gain = 1.0 - pole
    for i in range(1, len(values)):
        out[i] = gain * float(values[i]) + pole * out[i - 1]
    return out


def time_causal_scale_space(
    values: Iterable[float],
    sigmas: Iterable[float] | None = None,
) -> dict[str, np.ndarray]:
    """Return all cumulative causal scale levels for one price series.

    Each successive level adds another causal first-order integrator.  Because
    the filter state at index n depends only on indices <=n, running this on a
    prefix produces exactly the same values on that prefix as running it on a
    longer series.
    """

    raw = np.asarray(tuple(values), dtype=float)
    if raw.ndim != 1 or raw.size == 0 or not np.isfinite(raw).all():
        raise ValueError("values must be a finite nonempty one-dimensional series")

    current = raw.copy()
    outputs: dict[str, np.ndarray] = {}
    for level in build_scale_levels(sigmas):
        current = _causal_first_order(current, level.pole)
        outputs[level.scale_id] = current.copy()
    return outputs


def confirmed_extrema(
    values: Iterable[float],
    scale_id: str,
    *,
    atol: float = 1e-12,
) -> list[ConfirmedExtremum]:
    """Detect extrema with one-sided confirmation and deterministic plateaus.

    A nonzero first-difference sign reversal at index i confirms the previous
    run's extremum.  For a flat plateau, occurrence is the *last* plateau sample
    immediately before the first opposite move.  That occurrence is never
    reported before the opposite move is observed.
    """

    x = np.asarray(tuple(values), dtype=float)
    if x.ndim != 1 or x.size == 0 or not np.isfinite(x).all():
        raise ValueError("values must be a finite nonempty one-dimensional series")
    if not scale_id:
        raise ValueError("scale_id is required")
    if not math.isfinite(atol) or atol < 0:
        raise ValueError("atol must be finite and nonnegative")

    result: list[ConfirmedExtremum] = []
    last_direction = 0
    for i in range(1, len(x)):
        delta = float(x[i] - x[i - 1])
        direction = 1 if delta > atol else (-1 if delta < -atol else 0)
        if direction == 0:
            continue
        if last_direction and direction != last_direction:
            occurrence = i - 1
            kind = "high" if last_direction > 0 else "low"
            result.append(
                ConfirmedExtremum(
                    scale_id=scale_id,
                    kind=kind,
                    occurrence_index=occurrence,
                    confirmation_index=i,
                    value=float(x[occurrence]),
                )
            )
        last_direction = direction
    return result


def two_wave_candidates(extrema: Iterable[ConfirmedExtremum]) -> list[TwoWaveCandidate]:
    """Build overlapping five-extrema candidates at one immutable scale."""

    points = tuple(extrema)
    if not points:
        return []
    scale_ids = {p.scale_id for p in points}
    if len(scale_ids) != 1:
        raise ValueError("all extrema must come from one scale")
    out = []
    for i in range(len(points) - 4):
        window = points[i : i + 5]
        if any(a.kind == b.kind for a, b in zip(window, window[1:])):
            raise ValueError("extrema must alternate phase")
        if any(a.occurrence_index >= b.occurrence_index for a, b in zip(window, window[1:])):
            raise ValueError("extrema must be occurrence ordered")
        out.append(TwoWaveCandidate(window[0].scale_id, window))
    return out


def scale_space_two_wave_candidates(
    values: Iterable[float],
    sigmas: Iterable[float] | None = None,
) -> dict[str, list[TwoWaveCandidate]]:
    """Convenience research export; does not select a winning scale."""

    output = {}
    for scale_id, series in time_causal_scale_space(values, sigmas).items():
        output[scale_id] = two_wave_candidates(confirmed_extrema(series, scale_id))
    return output
