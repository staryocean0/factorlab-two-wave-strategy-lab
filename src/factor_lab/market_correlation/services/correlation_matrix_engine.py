# pyright: reportAny=false, reportMissingTypeStubs=false
# pyright: reportUnreachable=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnusedCallResult=false
"""Reusable pairwise-correlation engine for CloudRidge market structure.

The engine deliberately owns matrix computation and factual summaries only.
It does not select securities, infer market direction, or mutate factor state.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from types import ModuleType
from typing import Literal, cast

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError

ComputeBackend = Literal["cpu", "cupy"]
FISHER_CLIP = 0.999999


@dataclass(frozen=True, slots=True)
class CorrelationMatrixSummary:
    """Three physical attributes plus matrix-quality diagnostics."""

    group_corr_level: float
    group_corr_dispersion: float
    group_common_mode_share: float
    pairwise_corr_median: float
    pairwise_corr_iqr: float
    corr_ge_030_ratio: float
    corr_ge_050_ratio: float
    corr_ge_070_ratio: float
    effective_rank: float
    negative_eigen_mass_ratio: float
    negative_eigen_diagnostic_asset_count: int
    common_mode_estimator: str
    matrix_condition_number: float | None
    eligible_asset_count: int
    pair_count_total: int
    pair_count_evaluated: int
    pair_count_skipped: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def compute_correlation_matrix(
    lookback_returns: pd.DataFrame,
    *,
    min_periods: int,
    backend: ComputeBackend = "cpu",
    cupy_module: ModuleType | None = None,
) -> np.ndarray:
    """Compute a pairwise-complete Pearson matrix with a NaN diagonal."""

    if min_periods < 2:
        raise ValidationError("min_periods must be at least 2")
    if lookback_returns.shape[1] < 2:
        raise ValidationError("at least two assets are required")
    if backend == "cpu":
        matrix = _compute_correlation_matrix_cpu_hybrid(
            lookback_returns,
            min_periods=min_periods,
        )
    elif backend == "cupy":
        if cupy_module is None:
            raise RuntimeError("CuPy backend requires a visible CuPy module")
        matrix = _compute_correlation_matrix_cupy(
            lookback_returns,
            min_periods=min_periods,
            cupy_module=cupy_module,
        )
    else:
        raise ValidationError(f"unsupported compute backend: {backend}")
    if matrix.size:
        np.fill_diagonal(matrix, np.nan)
    return matrix


def _compute_correlation_matrix_cpu_hybrid(
    lookback_returns: pd.DataFrame,
    *,
    min_periods: int,
) -> np.ndarray:
    """Compute exact pairwise Pearson while exploiting mostly-complete panels.

    A daily A-share panel usually has a large complete core plus a much
    smaller set of suspended/newly-listed columns.  The complete block needs
    only one standardized matrix product.  Correlations touching an
    incomplete column retain the exact pairwise-complete sufficient-statistic
    formula, but their matrix products are ``N x M`` where ``M`` is the small
    incomplete set instead of ``N x N``.
    """

    values = lookback_returns.to_numpy(dtype=np.float64, copy=True)
    valid = np.isfinite(values)
    complete_mask = valid.all(axis=0)
    incomplete_indices = np.flatnonzero(~complete_mask)
    asset_count = values.shape[1]
    # When missingness is broad, pandas' specialized pairwise kernel avoids
    # allocating six full N x N sufficient-statistic matrices.
    if incomplete_indices.size > max(64, asset_count // 3):
        return lookback_returns.corr(
            method="pearson", min_periods=min_periods
        ).to_numpy(dtype=np.float64, copy=True)

    result = np.full((asset_count, asset_count), np.nan, dtype=np.float64)
    complete_indices = np.flatnonzero(complete_mask)
    if complete_indices.size:
        complete = values[:, complete_indices]
        centered = complete - complete.mean(axis=0)
        norms = np.sqrt(np.sum(centered * centered, axis=0))
        standardized = np.divide(
            centered,
            norms,
            out=np.zeros_like(centered),
            where=norms > 0.0,
        )
        block = standardized.T @ standardized
        zero_variance = norms <= 0.0
        if zero_variance.any():
            block[zero_variance, :] = np.nan
            block[:, zero_variance] = np.nan
        result[np.ix_(complete_indices, complete_indices)] = block

    if incomplete_indices.size:
        valid_float = valid.astype(np.float64)
        filled = np.where(valid, values, 0.0)
        filled_square = filled * filled
        incomplete = filled[:, incomplete_indices]
        incomplete_valid = valid_float[:, incomplete_indices]
        incomplete_square = filled_square[:, incomplete_indices]
        pair_counts = valid_float.T @ incomplete_valid
        safe_counts = np.where(pair_counts > 0.0, pair_counts, 1.0)
        sums_left = filled.T @ incomplete_valid
        sums_right = valid_float.T @ incomplete
        sums_square_left = filled_square.T @ incomplete_valid
        sums_square_right = valid_float.T @ incomplete_square
        cross = filled.T @ incomplete
        covariance = cross - sums_left * sums_right / safe_counts
        variance_left = sums_square_left - sums_left * sums_left / safe_counts
        variance_right = sums_square_right - sums_right * sums_right / safe_counts
        denominator = np.sqrt(np.maximum(variance_left * variance_right, 0.0))
        usable = (pair_counts >= min_periods) & (denominator > 0.0)
        correlations = np.divide(
            covariance,
            denominator,
            out=np.full_like(covariance, np.nan),
            where=usable,
        )
        correlations = np.clip(correlations, -1.0, 1.0)
        result[:, incomplete_indices] = correlations
        result[incomplete_indices, :] = correlations.T
    return result


def summarize_correlation_matrix(
    matrix: np.ndarray,
    *,
    lookback_returns: pd.DataFrame | None = None,
    psd_diagnostic_max_assets: int = 64,
    consume_matrix: bool = False,
) -> CorrelationMatrixSummary:
    """Summarize one matrix without assigning a bullish/bearish direction.

    ``consume_matrix=True`` donates a matrix that the caller no longer needs,
    allowing the Fisher transform to run in place for large universes.
    """

    working = np.asarray(matrix, dtype=np.float64)
    if working.ndim != 2 or working.shape[0] != working.shape[1]:
        raise ValidationError("correlation matrix must be square")
    asset_count = int(working.shape[0])
    if asset_count < 2:
        raise ValidationError("correlation matrix needs at least two assets")
    if not consume_matrix:
        working = working.copy()
    np.fill_diagonal(working, np.nan)
    pair_total = asset_count * (asset_count - 1) // 2
    finite_upper = np.empty(pair_total, dtype=np.float64)
    upper_count = 0
    for row_index in range(asset_count - 1):
        row = working[row_index, row_index + 1 :]
        finite = row[np.isfinite(row)]
        if finite.size:
            next_count = upper_count + finite.size
            finite_upper[upper_count:next_count] = finite
            upper_count = next_count
    finite_upper = finite_upper[:upper_count]
    if finite_upper.size == 0:
        raise ValidationError("correlation matrix has no evaluated pairs")
    if lookback_returns is not None:
        eigenvalues = _standardized_return_gram_eigenvalues(lookback_returns)
        common_mode_estimator = "standardized_return_gram_psd_v1"
    else:
        psd_matrix, _ = project_to_correlation_psd(working)
        eigenvalues = np.linalg.eigvalsh(psd_matrix)
        eigenvalues = np.clip(eigenvalues, 0.0, None)
        common_mode_estimator = "pairwise_matrix_full_psd_projection_v1"
    diagnostic_count = min(asset_count, max(2, psd_diagnostic_max_assets))
    if diagnostic_count < asset_count:
        positions = np.linspace(0, asset_count - 1, diagnostic_count, dtype=int)
        diagnostic_matrix = working[np.ix_(positions, positions)]
    else:
        diagnostic_matrix = working
    _, negative_mass = project_to_correlation_psd(diagnostic_matrix)
    eigen_sum = float(np.sum(eigenvalues))
    common_mode = float(eigenvalues[-1] / eigen_sum) if eigen_sum > 0 else 0.0
    positive = eigenvalues[eigenvalues > 1e-12]
    if positive.size:
        probabilities = positive / float(np.sum(positive))
        effective_rank = float(np.exp(-np.sum(probabilities * np.log(probabilities))))
        condition_number: float | None = float(positive[-1] / positive[0])
    else:
        effective_rank = 0.0
        condition_number = None

    q25, q75 = np.quantile(finite_upper, [0.25, 0.75])
    pairwise_median = float(np.median(finite_upper))
    ratio_030 = float(np.mean(finite_upper >= 0.30))
    ratio_050 = float(np.mean(finite_upper >= 0.50))
    ratio_070 = float(np.mean(finite_upper >= 0.70))
    np.clip(finite_upper, -FISHER_CLIP, FISHER_CLIP, out=finite_upper)
    np.arctanh(finite_upper, out=finite_upper)
    group_corr_level = float(np.tanh(np.mean(finite_upper)))

    np.clip(working, -FISHER_CLIP, FISHER_CLIP, out=working)
    np.arctanh(working, out=working)
    finite_counts = np.isfinite(working).sum(axis=1)
    per_asset_fisher = np.divide(
        np.nansum(working, axis=1),
        finite_counts,
        out=np.full(asset_count, np.nan, dtype=np.float64),
        where=finite_counts > 0,
    )
    finite_strength = per_asset_fisher[np.isfinite(per_asset_fisher)]
    if finite_strength.size == 0:
        raise ValidationError("correlation matrix has no per-asset strengths")
    strength_q25, strength_q75 = np.quantile(finite_strength, [0.25, 0.75])
    return CorrelationMatrixSummary(
        group_corr_level=group_corr_level,
        group_corr_dispersion=float(strength_q75 - strength_q25),
        group_common_mode_share=common_mode,
        pairwise_corr_median=pairwise_median,
        pairwise_corr_iqr=float(q75 - q25),
        corr_ge_030_ratio=ratio_030,
        corr_ge_050_ratio=ratio_050,
        corr_ge_070_ratio=ratio_070,
        effective_rank=effective_rank,
        negative_eigen_mass_ratio=negative_mass,
        negative_eigen_diagnostic_asset_count=diagnostic_count,
        common_mode_estimator=common_mode_estimator,
        matrix_condition_number=condition_number,
        eligible_asset_count=asset_count,
        pair_count_total=pair_total,
        pair_count_evaluated=int(finite_upper.size),
        pair_count_skipped=pair_total - int(finite_upper.size),
    )


def summarize_group_metrics_only(
    matrix: np.ndarray,
    *,
    lookback_returns: pd.DataFrame,
    consume_matrix: bool = False,
) -> dict[str, float]:
    """Compute only the three registered metrics for sensitivity audits."""

    working = np.asarray(matrix, dtype=np.float64)
    if working.ndim != 2 or working.shape[0] != working.shape[1]:
        raise ValidationError("correlation matrix must be square")
    if working.shape[0] < 2:
        raise ValidationError("correlation matrix needs at least two assets")
    if not consume_matrix:
        working = working.copy()
    np.fill_diagonal(working, np.nan)
    # The Fisher summaries are N x N elementwise work, while the common-mode
    # spectrum is a small T x T Gram calculation.  They are independent and
    # NumPy releases the GIL, so overlap them without changing either formula.
    with ThreadPoolExecutor(max_workers=2) as executor:
        eigen_future = executor.submit(
            _standardized_return_gram_eigenvalues, lookback_returns
        )
        fisher_future = executor.submit(_parallel_fisher_row_summaries, working)
        row_sums, row_counts = fisher_future.result()
        eigenvalues = eigen_future.result()
    evaluated_twice = int(row_counts.sum())
    if evaluated_twice == 0:
        raise ValidationError("correlation matrix has no evaluated pairs")
    per_asset = np.divide(
        row_sums,
        row_counts,
        out=np.full(working.shape[0], np.nan, dtype=np.float64),
        where=row_counts > 0,
    )
    per_asset = per_asset[np.isfinite(per_asset)]
    q25, q75 = np.quantile(per_asset, [0.25, 0.75])
    eigen_sum = float(eigenvalues.sum())
    common_mode = float(eigenvalues[-1] / eigen_sum) if eigen_sum > 0.0 else 0.0
    return {
        "group_corr_level": float(np.tanh(float(row_sums.sum()) / evaluated_twice)),
        "group_corr_dispersion": float(q75 - q25),
        "group_common_mode_share": common_mode,
    }


def _parallel_fisher_row_summaries(
    matrix: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Transform large donated matrices by disjoint rows in native threads.

    The registered metrics tolerate the float32 transform error by contract
    (well below 1e-6 in parity tests), while retaining float64 accumulation.
    The matrix engine itself remains exact float64.  NumPy ufuncs release the
    GIL, so four/eight bounded workers avoid a new dependency and prevent the
    now-fast BLAS correlation kernel from making summaries the bottleneck.
    """

    asset_count = int(matrix.shape[0])
    if asset_count < 1800:
        np.clip(matrix, -FISHER_CLIP, FISHER_CLIP, out=matrix)
        np.arctanh(matrix, out=matrix)
        finite = np.isfinite(matrix)
        sums = cast(np.ndarray, np.nansum(matrix, axis=1, dtype=np.float64))
        counts = cast(np.ndarray, finite.sum(axis=1, dtype=np.int64))
        return sums, counts
    working = matrix.astype(np.float32, copy=True)
    workers = 4 if asset_count < 3500 else 8
    boundaries = np.linspace(0, asset_count, workers + 1, dtype=int)

    def summarize_rows(bounds: tuple[int, int]) -> tuple[int, int, np.ndarray, np.ndarray]:
        start, stop = bounds
        rows = working[start:stop]
        np.clip(rows, -FISHER_CLIP, FISHER_CLIP, out=rows)
        np.arctanh(rows, out=rows)
        finite = np.isfinite(rows)
        sums = cast(np.ndarray, np.nansum(rows, axis=1, dtype=np.float64))
        counts = cast(np.ndarray, finite.sum(axis=1, dtype=np.int64))
        return (
            start,
            stop,
            sums,
            counts,
        )

    row_sums = np.empty(asset_count, dtype=np.float64)
    row_counts = np.empty(asset_count, dtype=np.int64)
    tasks = list(zip(boundaries[:-1], boundaries[1:], strict=True))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for start, stop, sums, counts in executor.map(summarize_rows, tasks):
            row_sums[start:stop] = sums
            row_counts[start:stop] = counts
    return row_sums, row_counts


def _standardized_return_gram_eigenvalues(
    lookback_returns: pd.DataFrame,
) -> np.ndarray:
    """Return nonzero PSD-correlation eigenvalues through the small T x T Gram.

    Each asset is centered on its finite observations and normalized to unit
    Euclidean norm. Missing standardized entries are neutral zero. The
    resulting asset correlation estimator is ``X.T @ X`` while the identical
    nonzero spectrum is obtained from ``X @ X.T``. With 20/60/120-day windows
    this avoids an O(N^3) decomposition across thousands of stocks.
    """

    values = lookback_returns.to_numpy(dtype=np.float64, copy=True)
    valid = np.isfinite(values)
    counts = valid.sum(axis=0)
    sums = np.nansum(values, axis=0)
    means = np.divide(
        sums,
        counts,
        out=np.zeros(values.shape[1], dtype=np.float64),
        where=counts > 0,
    )
    centered = np.where(valid, values - means, 0.0)
    norms = np.sqrt(np.sum(centered * centered, axis=0))
    normalized = np.divide(
        centered,
        norms,
        out=np.zeros_like(centered),
        where=norms > 1e-12,
    )
    gram = normalized @ normalized.T
    eigenvalues = np.linalg.eigvalsh((gram + gram.T) / 2.0)
    return np.clip(eigenvalues, 0.0, None)


def project_to_correlation_psd(matrix: np.ndarray) -> tuple[np.ndarray, float]:
    """Return a deterministic PSD correlation matrix and repair diagnostic.

    Pairwise-complete matrices can be non-PSD. Missing pairs are neutralized to
    zero before a symmetric eigenvalue projection; the diagonal is then
    normalized back to one.
    """

    working = np.asarray(matrix, dtype=np.float64)
    if working.ndim != 2 or working.shape[0] != working.shape[1]:
        raise ValidationError("correlation matrix must be square")
    filled = np.where(np.isfinite(working), working, 0.0)
    filled = (filled + filled.T) / 2.0
    np.fill_diagonal(filled, 1.0)
    values, vectors = np.linalg.eigh(filled)
    absolute_mass = float(np.sum(np.abs(values)))
    negative_mass = float(np.sum(np.abs(values[values < 0.0])))
    negative_ratio = negative_mass / absolute_mass if absolute_mass > 0 else 0.0
    projected = (vectors * np.clip(values, 0.0, None)) @ vectors.T
    diagonal = np.sqrt(np.clip(np.diag(projected), 1e-12, None))
    projected = projected / np.outer(diagonal, diagonal)
    projected = np.clip((projected + projected.T) / 2.0, -1.0, 1.0)
    np.fill_diagonal(projected, 1.0)
    return projected, negative_ratio


def _compute_correlation_matrix_cupy(
    lookback_returns: pd.DataFrame,
    *,
    min_periods: int,
    cupy_module: ModuleType,
) -> np.ndarray:
    cp = cupy_module
    values = lookback_returns.to_numpy(dtype=np.float64, copy=True)
    matrix = cp.asarray(values, dtype=cp.float64)  # type: ignore[attr-defined]
    valid = cp.isfinite(matrix)
    valid_float = valid.astype(cp.float64)  # type: ignore[attr-defined]
    filled = cp.where(valid, matrix, 0.0)
    filled_square = filled * filled
    pair_counts = valid_float.T @ valid_float
    safe_counts = cp.where(pair_counts > 0, pair_counts, 1.0)
    sums_left = filled.T @ valid_float
    sums_right = sums_left.T
    sums_square_left = filled_square.T @ valid_float
    sums_square_right = sums_square_left.T
    cross = filled.T @ filled
    covariance = cross - (sums_left * sums_right / safe_counts)
    variance_left = sums_square_left - (sums_left * sums_left / safe_counts)
    variance_right = sums_square_right - (sums_right * sums_right / safe_counts)
    denominator = cp.sqrt(variance_left * variance_right)
    valid_corr = (pair_counts >= min_periods) & (denominator > 0.0)
    corr = cp.where(
        valid_corr,
        covariance / cp.where(valid_corr, denominator, 1.0),
        cp.nan,
    )
    if corr.size:
        cp.fill_diagonal(corr, cp.nan)
    result = cp.asnumpy(corr)
    try:
        cp.get_default_memory_pool().free_all_blocks()
    except Exception:
        pass
    return np.asarray(cast(object, result), dtype=np.float64)


__all__ = [
    "ComputeBackend",
    "CorrelationMatrixSummary",
    "compute_correlation_matrix",
    "project_to_correlation_psd",
    "summarize_correlation_matrix",
    "summarize_group_metrics_only",
]
