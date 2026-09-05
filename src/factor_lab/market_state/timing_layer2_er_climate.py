# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportIndexIssue=false, reportMissingTypeStubs=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
"""Average path-efficiency climate: followable slow means, shorter windows, purer buckets."""

from __future__ import annotations

from typing import Final

import numpy as np
import pandas as pd

from factor_lab.core.errors import ValidationError
from factor_lab.market_state.lat_kline_attribute_atlas import _rolling_efficiency

ER_CLIMATE_ID: Final[str] = "timing_layer2_er_climate@1.0"
NATIVE_ER_BARS: Final[int] = 16
CLIMATE_WINDOWS: Final[tuple[int, ...]] = (20, 40, 60, 80, 120, 180, 252)
FOLLOWABLE_RANK_IC: Final[float] = 0.20


def native_efficiency_ratio(close: pd.Series, *, window: int = NATIVE_ER_BARS) -> pd.Series:
    values = pd.to_numeric(close, errors="raise").astype(float)
    if values.le(0.0).any() or window < 2:
        raise ValidationError("native ER requires positive prices and window>=2")
    level = np.log(values.to_numpy(float))
    er = _rolling_efficiency(level, window)
    aligned = np.full(len(values), np.nan)
    aligned[window:] = er
    return pd.Series(aligned, index=close.index, name=f"er_{window}")


def climate_mean(native_er: pd.Series, *, window: int) -> pd.Series:
    if window < 2:
        raise ValidationError("climate window must be at least 2")
    return native_er.rolling(window, min_periods=window).mean().rename(f"er_climate_{window}")


def future_climate(climate: pd.Series, *, window: int) -> pd.Series:
    future = climate.shift(-window)
    future.iloc[-window:] = np.nan
    return future.rename(f"future_{climate.name}")


def bucket_purity(climate: pd.Series) -> dict[str, float]:
    values = pd.to_numeric(climate, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(values) < 30:
        raise ValidationError("climate purity support is insufficient")
    q1, q2, q3 = (float(values.quantile(q)) for q in (1.0 / 3.0, 0.5, 2.0 / 3.0))
    low = values[values <= q1]
    high = values[values >= q3]
    iqr = float(values.quantile(0.75) - values.quantile(0.25))
    tertile_gap = float(high.mean() - low.mean()) if len(low) and len(high) else float("nan")
    total_var = float(values.var(ddof=1))
    assigned = pd.Series(1, index=values.index)
    assigned.loc[values <= q1] = 0
    assigned.loc[values >= q3] = 2
    between = float(
        np.average(
            [
                (low.mean() - values.mean()) ** 2 if len(low) else 0.0,
                (values[(values > q1) & (values < q3)].mean() - values.mean()) ** 2
                if ((values > q1) & (values < q3)).any()
                else 0.0,
                (high.mean() - values.mean()) ** 2 if len(high) else 0.0,
            ]
        )
    )
    return {
        "n": float(len(values)),
        "mean": float(values.mean()),
        "std": float(values.std(ddof=1)),
        "iqr": iqr,
        "q1": q1,
        "median": q2,
        "q3": q3,
        "tertile_gap": tertile_gap,
        "between_share": float(between / total_var) if total_var > 0 else float("nan"),
        "middle_share": float(((values > q1) & (values < q3)).mean()),
    }




def climate_pairs(
    climate: pd.Series,
    *,
    window: int,
    start: pd.Timestamp,
    end: pd.Timestamp,
    stride: int,
) -> tuple[pd.Series, pd.Series]:
    block = climate.loc[(climate.index >= start) & (climate.index <= end)]
    block = block.replace([np.inf, -np.inf], np.nan).dropna()
    if stride < 1:
        raise ValidationError("climate stride must be positive")
    if len(block) < window + 30:
        raise ValidationError("climate pair support is insufficient")
    now = block.iloc[:-window]
    future = block.shift(-window).iloc[:-window]
    if stride > 1:
        now = now.iloc[::stride]
        future = future.reindex(now.index)
    joined = pd.concat({"now": now, "future": future}, axis=1).dropna()
    if len(joined) < 8:
        raise ValidationError("climate pair support after stride is insufficient")
    return joined["now"], joined["future"]


def _bucket(values: pd.Series, q1: float, q3: float) -> pd.Series:
    out = pd.Series(1, index=values.index, dtype=int)
    out.loc[values <= q1] = 0
    out.loc[values >= q3] = 2
    return out


def two_path_reversal_scores(
    climate: pd.Series,
    *,
    window: int,
    start: pd.Timestamp,
    end: pd.Timestamp,
    q1: float,
    q3: float,
    low_mean: float,
    high_mean: float,
    stride: int,
) -> dict[str, float]:
    now, future = climate_pairs(climate, window=window, start=start, end=end, stride=stride)
    now_b = _bucket(now, q1, q3)
    fut_b = _bucket(future, q1, q3)
    extreme = now_b.ne(1)
    n_ext = int(extreme.sum())
    if n_ext < 8:
        raise ValidationError("two-path reversal needs enough extreme stages")
    predict_opp = now_b.map({0: 2, 2: 0})
    path1_hit = fut_b.loc[extreme].eq(predict_opp.loc[extreme])
    path1_not_same = fut_b.loc[extreme].ne(now_b.loc[extreme])
    dest = now_b.map({0: high_mean, 2: low_mean})
    path1_mae = float((future.loc[extreme] - dest.loc[extreme]).abs().mean())
    high_now = now_b.eq(2)
    low_now = now_b.eq(0)
    fut_high = float(future.loc[high_now].mean()) if int(high_now.sum()) else float("nan")
    fut_low = float(future.loc[low_now].mean()) if int(low_now.sum()) else float("nan")
    fut_std = float(future.std(ddof=1)) if len(future) > 1 else float("nan")
    gap = abs(fut_high - fut_low) if np.isfinite(fut_high) and np.isfinite(fut_low) else float("nan")
    path2_hit = fut_b.ne(now_b)
    # destination concentration of path2: max future-bucket share given current extreme bucket
    conc = []
    for bucket in (0, 2):
        part = fut_b.loc[now_b.eq(bucket)]
        if len(part):
            conc.append(float(part.value_counts(normalize=True).max()))
    return {
        "n": float(len(now)),
        "n_extreme": float(n_ext),
        "path1_opposite_hit": float(path1_hit.mean()),
        "path1_not_same_hit": float(path1_not_same.mean()),
        "path1_mae_to_opposite_mean": path1_mae,
        "path1_future_gap": gap,
        "path1_gap_over_std": float(gap / fut_std) if fut_std and fut_std > 0 and np.isfinite(gap) else float("nan"),
        "path2_not_here_hit": float(path2_hit.mean()),
        "path2_extreme_not_here_hit": float(path2_hit.loc[extreme].mean()),
        "path2_max_destination_share": float(np.mean(conc)) if conc else float("nan"),
        "future_std": fut_std,
    }

def reversal_scores(
    climate: pd.Series,
    *,
    window: int,
    start: pd.Timestamp,
    end: pd.Timestamp,
    threshold: float,
) -> dict[str, float]:
    block = climate.loc[(climate.index >= start) & (climate.index <= end)]
    block = block.replace([np.inf, -np.inf], np.nan).dropna()
    if len(block) < window + 30:
        raise ValidationError("climate reversal support is insufficient")
    if not np.isfinite(threshold):
        raise ValidationError("climate reversal threshold must be finite")
    now = block.iloc[:-window]
    future = block.shift(-window).iloc[:-window]
    side = now - float(threshold)
    moved = future - now
    usable = side.ne(0.0)
    toward = (moved * side) < 0.0
    crossed = (now - float(threshold)) * (future - float(threshold)) < 0.0
    high = now > float(threshold)
    low = now < float(threshold)
    n = int(usable.sum())
    if n < 30:
        raise ValidationError("climate reversal usable support is insufficient")
    return {
        "n": float(n),
        "threshold": float(threshold),
        "toward_hit": float(toward.loc[usable].mean()),
        "cross_median_hit": float(crossed.loc[usable].mean()),
        "high_n": float(high.sum()),
        "high_toward_hit": float(toward.loc[high].mean()) if int(high.sum()) else float("nan"),
        "low_n": float(low.sum()),
        "low_toward_hit": float(toward.loc[low].mean()) if int(low.sum()) else float("nan"),
    }

def followability_scores(climate: pd.Series, *, window: int, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, float]:
    block = climate.loc[(climate.index >= start) & (climate.index <= end)]
    block = block.replace([np.inf, -np.inf], np.nan).dropna()
    if len(block) < window + 30:
        raise ValidationError("climate followability support is insufficient")
    now = block.iloc[:-window]
    future = block.shift(-window).iloc[:-window]
    error = now - future
    rank_ic = float(now.corr(future, method="spearman"))
    return {
        "n": float(len(now)),
        "mae": float(error.abs().mean()),
        "rmse": float(np.sqrt(np.square(error).mean())),
        "rank_ic": rank_ic,
        "followable": float(rank_ic >= FOLLOWABLE_RANK_IC),
    }


__all__ = [
    "CLIMATE_WINDOWS",
    "ER_CLIMATE_ID",
    "FOLLOWABLE_RANK_IC",
    "NATIVE_ER_BARS",
    "bucket_purity",
    "climate_mean",
    "followability_scores",
    "future_climate",
    "native_efficiency_ratio",
    "reversal_scores",
    "climate_pairs",
    "two_path_reversal_scores",
]
