"""Shared brick-wall (FFT) band-volatility measurement engine.

This module is the reusable *measurement* implementation behind the frozen
S0.56 seven-band surface (v1), the nested half-octave surface (v2),
the nested quarter-octave surface (v3 uniform),
the fast-fine/slow-coarse hybrid (current v3), and the epicenter-only v4.
It never emits a trading signal.  FFT updates are full recomputes with
historical restatement; there is no causal incremental path.
"""

from __future__ import annotations

from typing import Final, Mapping

import numpy as np
import pandas as pd

PAD: Final[int] = 8192
YEARS: Final[tuple[int, ...]] = tuple(range(2009, 2026))

V1_EDGES: Final[tuple[float, ...]] = (7.4, 22.8, 56.6, 113.1, 226.3, 453.0)
V1_BAND_NAMES: Final[tuple[str, ...]] = (
    "ultra_fast",
    "P13",
    "P40",
    "P80",
    "P160",
    "P320",
    "ultra_slow",
)

V2_PARENT_CHILDREN: Final[Mapping[str, tuple[str, str]]] = {
    "P13": ("P10", "P17"),
    "P40": ("P29", "P45"),
    "P80": ("P67", "P95"),
    "P160": ("P134", "P190"),
    "P320": ("P269", "P381"),
}


def half_octave_edges(parent_edges: tuple[float, ...]) -> tuple[float, ...]:
    """Insert the geometric midpoint of every adjacent parent edge."""

    inserted: list[float] = []
    previous: float | None = None
    for edge in parent_edges:
        if previous is not None:
            inserted.append(float(np.sqrt(previous * edge)))
        inserted.append(float(edge))
        previous = float(edge)
    return tuple(inserted)


V2_EDGES: Final[tuple[float, ...]] = half_octave_edges(V1_EDGES)
V2_BAND_NAMES: Final[tuple[str, ...]] = (
    "ultra_fast",
    "P10",
    "P17",
    "P29",
    "P45",
    "P67",
    "P95",
    "P134",
    "P190",
    "P269",
    "P381",
    "ultra_slow",
)

# V3 inserts one more geometric midpoint into every v2 interval.
# The child whose geometric centre would be named P40 is called P40q so it
# cannot collide with the frozen v1 parent band P40 (22.8-56.6 bars).
V3_EDGES: Final[tuple[float, ...]] = half_octave_edges(V2_EDGES)
V3_BAND_NAMES: Final[tuple[str, ...]] = (
    "ultra_fast",
    "P9",
    "P11",
    "P15",
    "P20",
    "P26",
    "P32",
    "P40q",
    "P51",
    "P62",
    "P73",
    "P87",
    "P104",
    "P123",
    "P147",
    "P174",
    "P208",
    "P247",
    "P294",
    "P349",
    "P415",
    "ultra_slow",
)
V2_TO_V3_CHILDREN: Final[Mapping[str, tuple[str, str]]] = {
    "P10": ("P9", "P11"),
    "P17": ("P15", "P20"),
    "P29": ("P26", "P32"),
    "P45": ("P40q", "P51"),
    "P67": ("P62", "P73"),
    "P95": ("P87", "P104"),
    "P134": ("P123", "P147"),
    "P190": ("P174", "P208"),
    "P269": ("P247", "P294"),
    "P381": ("P349", "P415"),
}

# Sealed uniform 22-band V3 keeps the names above.  The user-requested
# revision is a *new* current V3 hybrid: quarter-octave only faster than
# P80, V2 width from P67 upward.
V3_UNIFORM_EDGES: Final[tuple[float, ...]] = V3_EDGES
V3_UNIFORM_BAND_NAMES: Final[tuple[str, ...]] = V3_BAND_NAMES


def geometric_midpoint(lo: float, hi: float) -> float:
    return float(np.sqrt(float(lo) * float(hi)))


def refine_parent_edges(
    parent_edges: tuple[float, ...],
    parent_band_names: tuple[str, ...],
    split_parents: tuple[str, ...],
) -> tuple[float, ...]:
    """Insert geometric midpoints only inside the named parent bands."""

    named = parent_band_names[1:-1]
    extras: list[float] = []
    for index, name in enumerate(named):
        if name in split_parents:
            extras.append(geometric_midpoint(parent_edges[index], parent_edges[index + 1]))
    return tuple(sorted(parent_edges + tuple(extras)))


def log_split_points(lo: float, hi: float, pieces: int) -> tuple[float, ...]:
    """Return interior geometric cut points that split [lo, hi] into ``pieces`` bands."""

    if pieces < 2:
        raise ValueError("pieces must be at least 2")
    left = float(np.log(lo))
    right = float(np.log(hi))
    return tuple(float(np.exp(left + (right - left) * k / pieces)) for k in range(1, pieces))


def refine_parent_edges_into(
    parent_edges: tuple[float, ...],
    parent_band_names: tuple[str, ...],
    split_parents: tuple[str, ...],
    *,
    pieces: int,
) -> tuple[float, ...]:
    named = parent_band_names[1:-1]
    extras: list[float] = []
    for index, name in enumerate(named):
        if name in split_parents:
            extras.extend(log_split_points(parent_edges[index], parent_edges[index + 1], pieces))
    return tuple(sorted(set(parent_edges + tuple(extras))))


V3_HYBRID_SPLIT_PARENTS: Final[tuple[str, ...]] = ("P10", "P17", "P29", "P45")
V3_HYBRID_EDGES: Final[tuple[float, ...]] = refine_parent_edges(
    V2_EDGES, V2_BAND_NAMES, V3_HYBRID_SPLIT_PARENTS
)
V3_HYBRID_BAND_NAMES: Final[tuple[str, ...]] = (
    "ultra_fast",
    "P9",
    "P11",
    "P15",
    "P20",
    "P26",
    "P32",
    "P40q",
    "P51",
    "P67",
    "P95",
    "P134",
    "P190",
    "P269",
    "P381",
    "ultra_slow",
)
V2_TO_V3_HYBRID_CHILDREN: Final[Mapping[str, tuple[str, str]]] = {
    "P10": ("P9", "P11"),
    "P17": ("P15", "P20"),
    "P29": ("P26", "P32"),
    "P45": ("P40q", "P51"),
}

# V5: two-criterion unequal width.
# Fast of 2.2d (P38): keep V2 width (cannot follow / averaging washes).
# Slow of P67: keep a V2 band only if it historically layers vs its neighbor.
# Tradable middle: only P45 stays at 1/8, because that is the holding-period frame.
V5_FAST_CUTOFF_DAYS: Final[float] = 2.2
V5_SPLIT_PARENTS: Final[tuple[str, ...]] = ("P45",)
V5_EDGES: Final[tuple[float, ...]] = refine_parent_edges_into(
    V2_EDGES, V2_BAND_NAMES, V5_SPLIT_PARENTS, pieces=4
)
V5_BAND_NAMES: Final[tuple[str, ...]] = (
    "ultra_fast",
    "P10",
    "P17",
    "P29",
    "P38",
    "P43",
    "P48",
    "P53",
    "P67",
    "P95",
    "P134",
    "P190",
    "P269",
    "P381",
    "ultra_slow",
)
V2_TO_V5_CHILDREN: Final[Mapping[str, tuple[str, str, str, str]]] = {
    "P45": ("P38", "P43", "P48", "P53"),
}
V5_SLOW_PARENTS: Final[tuple[str, ...]] = ("P67", "P95", "P134", "P190", "P269", "P381")
V5_LAYERING_UNIQUE_MIN: Final[float] = 0.20

# V6 / current V4.3: keep the V5 tradable frame, then split the old ultra_slow
# tail into two wide trend-bonus bands out to half a year (~57 trading days).
# One extra band from 28d to 180d would be a 6.4x dump; two √2 steps match the
# existing slow geometry and stay wide. Beyond ~57d remains ultra_slow.
V6_SLOW_EXTENSION_EDGES: Final[tuple[float, ...]] = (
    453.0 * (2.0 ** 0.5),  # 640.64 bars ≈ 40.0 days
    453.0 * 2.0,           # 906.00 bars ≈ 56.6 days
)
V6_EDGES: Final[tuple[float, ...]] = V5_EDGES + V6_SLOW_EXTENSION_EDGES
V6_BAND_NAMES: Final[tuple[str, ...]] = (
    "ultra_fast",
    "P10",
    "P17",
    "P29",
    "P38",
    "P43",
    "P48",
    "P53",
    "P67",
    "P95",
    "P134",
    "P190",
    "P269",
    "P381",
    "P539",
    "P762",
    "ultra_slow",
)
V6_NEW_SLOW_BANDS: Final[tuple[str, ...]] = ("P539", "P762")
V6_SLOW_PARENTS: Final[tuple[str, ...]] = V5_SLOW_PARENTS + V6_NEW_SLOW_BANDS

# Current V4 is now the V6 slow-extended ruler. Frozen V5 (15 bands) stays as
# the predecessor scientific name. Older 13-band / 24-band V4 identities remain
# physically deleted.
CURRENT_V4_EDGES: Final[tuple[float, ...]] = V6_EDGES
CURRENT_V4_BAND_NAMES: Final[tuple[str, ...]] = V6_BAND_NAMES
CURRENT_V4_SPLIT_PARENTS: Final[tuple[str, ...]] = V5_SPLIT_PARENTS
V2_TO_CURRENT_V4_CHILDREN: Final[Mapping[str, tuple[str, str, str, str]]] = V2_TO_V5_CHILDREN

def band_edges_with_ends(interior: tuple[float, ...]) -> tuple[float, ...]:
    return (0.0, *interior, float("inf"))


def brickwall_components(
    values: np.ndarray,
    *,
    interior_edges: tuple[float, ...],
    band_names: tuple[str, ...],
    pad: int = PAD,
) -> dict[str, np.ndarray]:
    """Zero-phase ideal rectangular rFFT partition.  One bin, one band."""

    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size < pad + 2:
        raise ValueError("brickwall input must be a 1-d series longer than the pad")
    if len(band_names) != len(interior_edges) + 1:
        raise ValueError("band_names must have one more entry than interior edges")
    padded = np.concatenate([array[pad:0:-1], array, array[-2 : -pad - 2 : -1]])
    spectrum = np.fft.rfft(padded)
    freqs = np.fft.rfftfreq(len(padded), d=1.0)
    periods = np.where(freqs > 0.0, 1.0 / np.where(freqs > 0.0, freqs, 1.0), np.inf)
    edges = band_edges_with_ends(interior_edges)
    components: dict[str, np.ndarray] = {}
    for name, lo, hi in zip(band_names, edges[:-1], edges[1:], strict=True):
        mask = (periods >= lo) & (periods < hi) if np.isfinite(hi) else (periods >= lo)
        reconstructed = np.fft.irfft(spectrum * mask, n=len(padded))
        components[name] = reconstructed[pad : pad + len(array)].copy()
    return components


def padded_components(
    values: np.ndarray,
    *,
    interior_edges: tuple[float, ...],
    band_names: tuple[str, ...],
    pad: int = PAD,
) -> dict[str, np.ndarray]:
    """Same partition as ``brickwall_components`` but kept on the padded domain."""

    array = np.asarray(values, dtype=float)
    padded = np.concatenate([array[pad:0:-1], array, array[-2 : -pad - 2 : -1]])
    spectrum = np.fft.rfft(padded)
    freqs = np.fft.rfftfreq(len(padded), d=1.0)
    periods = np.where(freqs > 0.0, 1.0 / np.where(freqs > 0.0, freqs, 1.0), np.inf)
    edges = band_edges_with_ends(interior_edges)
    components: dict[str, np.ndarray] = {}
    for name, lo, hi in zip(band_names, edges[:-1], edges[1:], strict=True):
        mask = (periods >= lo) & (periods < hi) if np.isfinite(hi) else (periods >= lo)
        components[name] = np.fft.irfft(spectrum * mask, n=len(padded))
    return components


def identity_max_abs(
    values: np.ndarray, components: Mapping[str, np.ndarray], names: tuple[str, ...]
) -> float:
    total = np.sum(np.stack([components[name] for name in names]), axis=0)
    return float(np.max(np.abs(total - np.asarray(values, dtype=float))))


def orthogonality_max_abs_corr(padded_comps: Mapping[str, np.ndarray], names: tuple[str, ...]) -> float:
    worst = 0.0
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            denom = float(np.linalg.norm(padded_comps[left]) * np.linalg.norm(padded_comps[right]))
            corr = abs(float(np.dot(padded_comps[left], padded_comps[right]))) / denom if denom else 0.0
            worst = max(worst, corr)
    return worst


MATCHED_HORIZON_CYCLES: Final[int] = 3
BARS_PER_TRADING_DAY: Final[float] = 16.0
# ultra_slow has no finite slow edge; do not adjudicate yearly compression on it.
UNBOUNDED_BANDS: Final[frozenset[str]] = frozenset({"ultra_slow"})


def band_period_bounds_bars(
    band_names: tuple[str, ...],
    interior_edges: tuple[float, ...],
) -> dict[str, tuple[float, float]]:
    """Return (fast_edge_bars, slow_edge_bars) for each named band."""

    if len(band_names) != len(interior_edges) + 1:
        raise ValueError("band_names must have one more entry than interior edges")
    edges = (0.0, *interior_edges, float("inf"))
    return {name: (float(edges[i]), float(edges[i + 1])) for i, name in enumerate(band_names)}


def matched_lookback_bars(slow_edge_bars: float, *, cycles: int = MATCHED_HORIZON_CYCLES) -> int | None:
    """Lookback in bars: cycles times the band's slow-edge period.

    A finite slow edge is required.  Unbounded tails return None so callers
    cannot pretend an annual RMS is a phase-stable amplitude.
    """

    if not 0.0 < slow_edge_bars < float("inf"):
        return None
    if cycles < 1:
        raise ValueError("cycles must be at least 1")
    return int(round(cycles * slow_edge_bars))


def rolling_matched_rms(series: np.ndarray, lookback_bars: int) -> np.ndarray:
    """Causal trailing RMS over a matched lookback.  Prefix is NaN until full."""

    if lookback_bars < 2:
        raise ValueError("lookback_bars must be at least 2")
    frame = pd.Series(np.asarray(series, dtype=float))
    return (
        frame.pow(2)
        .rolling(lookback_bars, min_periods=lookback_bars)
        .mean()
        .pow(0.5)
        .to_numpy(dtype=float)
    )


def yearly_matched_rms(
    series: np.ndarray,
    index: pd.DatetimeIndex,
    *,
    lookback_bars: int,
) -> dict[str, float]:
    """Yearly amplitude = mean of the matched-horizon trailing RMS inside the year.

    This keeps a year label for display, but the number itself is not a
    calendar-box RMS.  Slow bands therefore cannot report a one-year energy
    that covers less than three of their own cycles.
    """

    trailing = rolling_matched_rms(series, lookback_bars)
    frame = pd.Series(trailing, index=index)
    out: dict[str, float] = {}
    for year in YEARS:
        segment = frame[(index >= pd.Timestamp(f"{year}-01-01")) & (index < pd.Timestamp(f"{year + 1}-01-01"))]
        values = segment.to_numpy(dtype=float)
        finite = values[np.isfinite(values)]
        out[str(year)] = float(np.mean(finite)) if len(finite) else float("nan")
    return out


def yearly_rms(series: np.ndarray, index: pd.DatetimeIndex) -> dict[str, float]:
    """Legacy calendar-year RMS.  Too short for slow bands; keep for replay only."""

    frame = pd.Series(series, index=index)
    out: dict[str, float] = {}
    for year in YEARS:
        segment = frame[(index >= pd.Timestamp(f"{year}-01-01")) & (index < pd.Timestamp(f"{year + 1}-01-01"))]
        out[str(year)] = (
            float(np.sqrt(np.mean(np.square(segment.to_numpy(dtype=float))))) if len(segment) else float("nan")
        )
    return out


def monthly_rms(components: Mapping[str, np.ndarray], index: pd.DatetimeIndex) -> pd.DataFrame:
    rows: dict[str, dict[str, float]] = {}
    series = {name: pd.Series(values, index=index) for name, values in components.items()}
    month_starts = pd.date_range("2009-01-01", "2025-12-01", freq="MS")
    for start in month_starts:
        end = start + pd.offsets.MonthBegin(1)
        row: dict[str, float] = {}
        for name, item in series.items():
            segment = item[(item.index >= start) & (item.index < end)]
            row[name] = (
                float(np.sqrt(np.mean(np.square(segment.to_numpy(dtype=float))))) if len(segment) else float("nan")
            )
        rows[str(start.date())] = row
    frame = pd.DataFrame.from_dict(rows, orient="index")
    frame.index.name = "month"
    return frame


def era_mean(yearly: Mapping[str, Mapping[str, float]], years: tuple[int, ...]) -> dict[str, float]:
    return {
        name: float(np.mean([yearly[name][str(year)] for year in years]))
        for name in yearly
    }


def compression_ratio(
    yearly: Mapping[str, Mapping[str, float]],
    *,
    baseline_years: tuple[int, ...],
    compare_years: tuple[int, ...],
) -> dict[str, float]:
    base = era_mean(yearly, baseline_years)
    compare = era_mean(yearly, compare_years)
    return {name: float(compare[name] / base[name]) if base[name] else float("nan") for name in yearly}


BASELINE_YEARS_EX_2015: Final[tuple[int, ...]] = tuple(year for year in range(2009, 2018) if year != 2015)
ERA_2018_2020: Final[tuple[int, ...]] = tuple(range(2018, 2021))
ERA_2021_2025: Final[tuple[int, ...]] = tuple(range(2021, 2026))


__all__ = [
    "BASELINE_YEARS_EX_2015",
    "ERA_2018_2020",
    "ERA_2021_2025",
    "PAD",
    "V1_BAND_NAMES",
    "V1_EDGES",
    "V2_BAND_NAMES",
    "V2_EDGES",
    "V2_PARENT_CHILDREN",
    "V2_TO_V3_CHILDREN",
    "V2_TO_V3_HYBRID_CHILDREN",
    "V3_BAND_NAMES",
    "V3_EDGES",
    "V3_HYBRID_BAND_NAMES",
    "V3_HYBRID_EDGES",
    "V3_HYBRID_SPLIT_PARENTS",
    "V3_UNIFORM_BAND_NAMES",
    "V3_UNIFORM_EDGES",
    "V2_TO_V5_CHILDREN",
    "V5_BAND_NAMES",
    "V5_EDGES",
    "V5_FAST_CUTOFF_DAYS",
    "V5_LAYERING_UNIQUE_MIN",
    "V5_SLOW_PARENTS",
    "V5_SPLIT_PARENTS",
    "V6_BAND_NAMES",
    "V6_EDGES",
    "V6_NEW_SLOW_BANDS",
    "V6_SLOW_EXTENSION_EDGES",
    "V6_SLOW_PARENTS",
    "CURRENT_V4_BAND_NAMES",
    "CURRENT_V4_EDGES",
    "CURRENT_V4_SPLIT_PARENTS",
    "V2_TO_CURRENT_V4_CHILDREN",
    "YEARS",
    "BARS_PER_TRADING_DAY",
    "UNBOUNDED_BANDS",
    "MATCHED_HORIZON_CYCLES",
    "band_period_bounds_bars",
    "matched_lookback_bars",
    "rolling_matched_rms",
    "yearly_matched_rms",
    "log_split_points",
    "refine_parent_edges_into",
    "band_edges_with_ends",
    "brickwall_components",
    "compression_ratio",
    "era_mean",
    "geometric_midpoint",
    "half_octave_edges",
    "refine_parent_edges",
    "identity_max_abs",
    "monthly_rms",
    "orthogonality_max_abs_corr",
    "padded_components",
    "yearly_rms",
]
