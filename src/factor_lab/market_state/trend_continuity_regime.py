# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportDeprecated=false, reportMissingTypeStubs=false, reportReturnType=false
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnusedCallResult=false
"""Causal market trend-continuity regime for timing-strategy diagnostics.

The headline series is the rolling lag-one autocorrelation of completed daily
log returns over one trading year.  A trailing 20-day mean is published for
monitoring, while the unsmoothed W250 value remains the factual authority.
Neither series is a trading signal or proof that a strategy captured all
available opportunities.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final, cast

import numpy as np
import pandas as pd

from factor_lab.cloudridge.paper_kernel import (
    PAPER_KERNEL_ANNUALIZATION,
    build_paper_kernel_panel,
    paper_kernel_return_column_name,
)
from factor_lab.core.errors import ValidationError

SCHEMA_ID: Final[str] = "market_state_trend_continuity_regime@1.0"
DEFAULT_PRICE_PATH: Final[Path] = Path(
    "output/baylum-data-update/current/cloudridge_1d_qfq_service_confirmed_19940307_20260626_levels.csv"
)
DEFAULT_OUTPUT_DIR: Final[Path] = Path(
    "output/market-state-foundation/trend-continuity-regime/current"
)
CANONICAL_ENTRYPOINT: Final[str] = (
    "docs/user/market_state_trend_continuity_regime_workflow.md"
)
AUTHORITY_WINDOW_DAYS: Final[int] = 250
DISPLAY_SMOOTH_DAYS: Final[int] = 20
ROBUST_WINDOWS_DAYS: Final[tuple[int, ...]] = (100, 150, 200, 250, 300, 400, 500)
SURFACE_WINDOWS_DAYS: Final[tuple[int, ...]] = (
    20,
    30,
    40,
    50,
    60,
    80,
    100,
    120,
    150,
    180,
    200,
    240,
    250,
    300,
    350,
    400,
    450,
    500,
    600,
    750,
)
SURFACE_SMOOTH_DAYS: Final[tuple[int, ...]] = (1, 5, 10, 20, 40, 60)
PHASES: Final[tuple[tuple[str, int, int], ...]] = (
    ("development_2009_2017", 2009, 2017),
    ("audit_2018_2020", 2018, 2020),
    ("external_2021_2026", 2021, 2026),
)


def build_trend_continuity_panel(daily_bars: pd.DataFrame) -> pd.DataFrame:
    """Build the point-in-time daily trend-continuity state surface."""

    daily = _validated_daily(daily_bars)
    log_return = np.log(daily["close"] / daily["close"].shift(1))
    result = daily[["timestamp", "close"]].copy()
    result["log_return"] = log_return
    lag_columns: list[str] = []
    for window in ROBUST_WINDOWS_DAYS:
        column = f"lag1_autocorr_w{window}"
        result[column] = log_return.rolling(window, min_periods=window).corr(
            log_return.shift(1)
        )
        lag_columns.append(column)
    result["trend_continuity_w250"] = result[
        f"lag1_autocorr_w{AUTHORITY_WINDOW_DAYS}"
    ]
    result["trend_continuity_w250_ma20"] = result[
        "trend_continuity_w250"
    ].rolling(DISPLAY_SMOOTH_DAYS, min_periods=DISPLAY_SMOOTH_DAYS).mean()
    result["trend_continuity_multiscale_median"] = result[lag_columns].median(
        axis=1, skipna=False
    )
    result["trend_continuity_multiscale_median_ma20"] = result[
        "trend_continuity_multiscale_median"
    ].rolling(DISPLAY_SMOOTH_DAYS, min_periods=DISPLAY_SMOOTH_DAYS).mean()
    result["positive_scale_share"] = result[lag_columns].gt(0.0).sum(axis=1) / len(
        lag_columns
    )
    all_scales_valid = result[lag_columns].notna().all(axis=1)
    result.loc[~all_scales_valid, "positive_scale_share"] = np.nan
    result["regime_state"] = _regime_state(
        result["trend_continuity_multiscale_median"],
        result["positive_scale_share"],
    )
    result["decision_eligible_timestamp"] = result["timestamp"].shift(-1)
    return result


def build_annual_summary(panel: pd.DataFrame) -> pd.DataFrame:
    """Return calendar-year summaries without using them as fitted thresholds."""

    data = panel.copy()
    data["year"] = pd.to_datetime(data["timestamp"]).dt.year
    rows: list[dict[str, object]] = []
    for year, group in data.loc[data["year"].between(2009, 2026)].groupby("year"):
        valid = group["trend_continuity_w250"].notna()
        states = group.loc[valid, "regime_state"]
        rows.append(
            {
                "year": int(year),
                "observation_count": int(valid.sum()),
                "trend_continuity_w250_mean": _mean(group.loc[valid, "trend_continuity_w250"]),
                "trend_continuity_w250_ma20_mean": _mean(
                    group.loc[valid, "trend_continuity_w250_ma20"]
                ),
                "multiscale_median_mean": _mean(
                    group.loc[valid, "trend_continuity_multiscale_median"]
                ),
                "positive_scale_share_mean": _mean(
                    group.loc[valid, "positive_scale_share"]
                ),
                "continuation_state_share": float((states == "continuation").mean()),
                "mixed_state_share": float((states == "mixed").mean()),
                "reversal_state_share": float((states == "reversal").mean()),
                "calendar_status": "partial_current_year" if int(year) == 2026 else "complete_year",
            }
        )
    return pd.DataFrame(rows)


def build_phase_summary(panel: pd.DataFrame) -> pd.DataFrame:
    """Summarize the three user-requested non-overlapping periods."""

    years = pd.to_datetime(panel["timestamp"]).dt.year
    rows: list[dict[str, object]] = []
    for phase_id, start_year, end_year in PHASES:
        selected = panel.loc[years.between(start_year, end_year)]
        rows.append(
            {
                "phase_id": phase_id,
                "start_year": start_year,
                "end_year": end_year,
                "observation_count": int(selected["trend_continuity_w250"].notna().sum()),
                "trend_continuity_w250_mean": _mean(selected["trend_continuity_w250"]),
                "trend_continuity_w250_ma20_mean": _mean(
                    selected["trend_continuity_w250_ma20"]
                ),
                "multiscale_median_mean": _mean(
                    selected["trend_continuity_multiscale_median"]
                ),
                "positive_scale_share_mean": _mean(selected["positive_scale_share"]),
                "continuation_state_share": float(
                    (selected["regime_state"] == "continuation").mean()
                ),
                "reversal_state_share": float(
                    (selected["regime_state"] == "reversal").mean()
                ),
            }
        )
    return pd.DataFrame(rows)


def build_candidate_comparison(daily_bars: pd.DataFrame) -> pd.DataFrame:
    """Challenge LAG1 against the main existing market-state candidates."""

    daily = _validated_daily(daily_bars)
    returns = np.log(daily["close"] / daily["close"].shift(1))
    sign = np.sign(returns).replace(0.0, np.nan)
    valid_pair = sign.notna() & sign.shift(1).notna()
    switch = valid_pair & sign.ne(sign.shift(1))
    denominator = valid_pair.astype(float).rolling(AUTHORITY_WINDOW_DAYS).sum()
    path_abs = returns.abs().rolling(AUTHORITY_WINDOW_DAYS).sum()
    candidate = pd.DataFrame({"timestamp": daily["timestamp"]})
    candidate["lag1_autocorr_w250"] = returns.rolling(
        AUTHORITY_WINDOW_DAYS
    ).corr(returns.shift(1))
    candidate["lag4_autocorr_w250"] = returns.rolling(
        AUTHORITY_WINDOW_DAYS
    ).corr(returns.shift(4))
    candidate["path_efficiency_w250"] = (
        returns.rolling(AUTHORITY_WINDOW_DAYS).sum().abs()
        / path_abs.replace(0.0, np.nan)
    )
    candidate["bdci_w250"] = 100.0 * (
        1.0
        - switch.astype(float).rolling(AUTHORITY_WINDOW_DAYS).sum()
        / denominator.replace(0.0, np.nan)
    )
    paper = build_paper_kernel_panel(daily, spans=(5, 10, 15, 20, 100, 200, 300, 400, 500))
    fast_columns = [paper_kernel_return_column_name(span) for span in (5, 10, 15, 20)]
    long_columns = [
        paper_kernel_return_column_name(span) for span in (100, 200, 300, 400, 500)
    ]
    candidate["paper_kernel_fast_annualized"] = (
        paper[fast_columns].mean(axis=1) * PAPER_KERNEL_ANNUALIZATION
    )
    candidate["paper_kernel_long_annualized"] = (
        paper[long_columns].mean(axis=1) * PAPER_KERNEL_ANNUALIZATION
    )
    years = pd.to_datetime(candidate["timestamp"]).dt.year
    rows: list[dict[str, object]] = []
    for column in candidate.columns.drop("timestamp"):
        phase_values = []
        for _, start_year, end_year in PHASES:
            phase_values.append(_mean(candidate.loc[years.between(start_year, end_year), column]))
        early, middle, late = phase_values
        denominator_recovery = early - middle
        rows.append(
            {
                "candidate_id": column,
                "development_2009_2017_mean": early,
                "audit_2018_2020_mean": middle,
                "external_2021_2026_mean": late,
                "middle_is_trough": bool(middle < early and middle < late),
                "late_recovers_from_middle": bool(late > middle),
                "late_recovery_fraction": (
                    (late - middle) / denominator_recovery
                    if denominator_recovery > 0.0
                    else math.nan
                ),
                "selected_as_headline": column == "lag1_autocorr_w250",
            }
        )
    return pd.DataFrame(rows)


def build_window_smoothing_surface(daily_bars: pd.DataFrame) -> pd.DataFrame:
    """Expose whether the three-period shape is a plateau or a fitted point."""

    daily = _validated_daily(daily_bars)
    returns = np.log(daily["close"] / daily["close"].shift(1))
    years = daily["timestamp"].dt.year
    rows: list[dict[str, object]] = []
    for window in SURFACE_WINDOWS_DAYS:
        raw = returns.rolling(window, min_periods=window).corr(returns.shift(1))
        for smooth in SURFACE_SMOOTH_DAYS:
            values = raw if smooth == 1 else raw.rolling(smooth, min_periods=smooth).mean()
            phase_values = [
                _mean(values.loc[years.between(start_year, end_year)])
                for _, start_year, end_year in PHASES
            ]
            early, middle, late = phase_values
            denominator_recovery = early - middle
            rows.append(
                {
                    "measurement_window_days": window,
                    "display_smooth_days": smooth,
                    "development_2009_2017_mean": early,
                    "audit_2018_2020_mean": middle,
                    "external_2021_2026_mean": late,
                    "middle_is_trough": bool(middle < early and middle < late),
                    "late_recovery_fraction": (
                        (late - middle) / denominator_recovery
                        if denominator_recovery > 0.0
                        else math.nan
                    ),
                    "is_selected_authority": bool(
                        window == AUTHORITY_WINDOW_DAYS and smooth == 1
                    ),
                    "is_selected_display": bool(
                        window == AUTHORITY_WINDOW_DAYS
                        and smooth == DISPLAY_SMOOTH_DAYS
                    ),
                }
            )
    return pd.DataFrame(rows)


def run_trend_continuity_regime(
    *,
    project_root: Path,
    output_dir: Path,
    price_path: Path | None = None,
) -> dict[str, object]:
    """Materialize and validate the trend-continuity diagnostic package."""

    root = project_root.resolve()
    source = (price_path or root / DEFAULT_PRICE_PATH).resolve()
    if not source.exists():
        raise ValidationError(f"trend-continuity source does not exist: {source}")
    raw = pd.read_csv(source)
    panel = build_trend_continuity_panel(raw)
    annual = build_annual_summary(panel)
    phases = build_phase_summary(panel)
    candidates = build_candidate_comparison(raw)
    surface = build_window_smoothing_surface(raw)
    validation = _build_validation(panel, annual, phases, candidates, surface, source, root)
    report = _build_report(phases, candidates, surface)

    output = output_dir.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="trend-continuity-", dir=output.parent) as tmp:
        staging = Path(tmp)
        panel.to_csv(staging / "trend_continuity_timeseries.csv", index=False, float_format="%.12g")
        annual.to_csv(staging / "annual_summary.csv", index=False, float_format="%.12g")
        phases.to_csv(staging / "phase_summary.csv", index=False, float_format="%.12g")
        candidates.to_csv(staging / "candidate_comparison.csv", index=False, float_format="%.12g")
        surface.to_csv(staging / "window_smoothing_surface.csv", index=False, float_format="%.12g")
        _write_timeseries_chart(panel, staging / "trend_continuity_timeseries.png")
        (staging / "validation.json").write_text(
            json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (staging / "report_zh.md").write_text(report, encoding="utf-8")
        manifest = _build_manifest(staging, validation, source, root)
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if output.exists():
            shutil.rmtree(output)
        shutil.copytree(staging, output)
    validate_persisted_trend_continuity(output)
    return cast(dict[str, object], json.loads((output / "manifest.json").read_text(encoding="utf-8")))


def validate_persisted_trend_continuity(output_dir: Path) -> None:
    """Fail closed when persisted values or authority boundaries drift."""

    required = {
        "trend_continuity_timeseries.csv",
        "annual_summary.csv",
        "phase_summary.csv",
        "candidate_comparison.csv",
        "window_smoothing_surface.csv",
        "trend_continuity_timeseries.png",
        "validation.json",
        "report_zh.md",
        "manifest.json",
    }
    missing = sorted(name for name in required if not (output_dir / name).exists())
    if missing:
        raise ValidationError(f"trend-continuity output missing files: {missing}")
    validation = json.loads((output_dir / "validation.json").read_text(encoding="utf-8"))
    if validation.get("schema_id") != SCHEMA_ID:
        raise ValidationError("trend-continuity schema id drifted")
    authority = validation.get("authority", {})
    if not isinstance(authority, Mapping):
        raise ValidationError("trend-continuity authority contract is missing")
    if authority.get("production_authority") is not False:
        raise ValidationError("trend-continuity must not self-grant production authority")
    if authority.get("opportunity_capture_proof") is not False:
        raise ValidationError("trend-continuity must not claim opportunity capture proof")
    phases = pd.read_csv(output_dir / "phase_summary.csv").set_index("phase_id")
    early = float(phases.loc["development_2009_2017", "trend_continuity_w250_mean"])
    middle = float(phases.loc["audit_2018_2020", "trend_continuity_w250_mean"])
    late = float(phases.loc["external_2021_2026", "trend_continuity_w250_mean"])
    if not (middle < early and middle < late):
        raise ValidationError("headline trend-continuity line no longer reproduces the middle trough")
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    artifacts = cast(Sequence[Mapping[str, object]], manifest.get("artifacts", []))
    for item in artifacts:
        path = output_dir / str(item["path"])
        if _sha256(path) != item["sha256"]:
            raise ValidationError(f"trend-continuity artifact hash mismatch: {path.name}")


def _validated_daily(frame: pd.DataFrame) -> pd.DataFrame:
    timestamp_column = "timestamp" if "timestamp" in frame.columns else "trading_day"
    required = {timestamp_column, "close"}
    missing = required - set(frame.columns)
    if missing:
        raise ValidationError(f"trend-continuity daily panel missing columns: {sorted(missing)}")
    daily = frame.loc[:, [timestamp_column, "close"]].copy()
    daily.columns = ["timestamp", "close"]
    daily["timestamp"] = pd.to_datetime(daily["timestamp"], errors="coerce")
    daily["close"] = pd.to_numeric(daily["close"], errors="coerce")
    daily = daily.dropna().sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    if len(daily) <= max(SURFACE_WINDOWS_DAYS):
        raise ValidationError("trend-continuity daily panel lacks long-window history")
    if bool((daily["close"] <= 0.0).any()):
        raise ValidationError("trend-continuity close values must be positive")
    return daily


def _regime_state(median: pd.Series, agreement: pd.Series) -> pd.Series:
    state = pd.Series("unavailable", index=median.index, dtype="object")
    valid = median.notna() & agreement.notna()
    state.loc[valid] = "mixed"
    state.loc[valid & median.gt(0.0) & agreement.ge(5.0 / 7.0)] = "continuation"
    state.loc[valid & median.lt(0.0) & agreement.le(2.0 / 7.0)] = "reversal"
    return state


def _mean(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    return float(clean.mean()) if len(clean) else math.nan


def _build_validation(
    panel: pd.DataFrame,
    annual: pd.DataFrame,
    phases: pd.DataFrame,
    candidates: pd.DataFrame,
    surface: pd.DataFrame,
    source: Path,
    root: Path,
) -> dict[str, object]:
    selected_surface = surface.loc[surface["is_selected_display"]].iloc[0]
    return {
        "schema_id": SCHEMA_ID,
        "status": "diagnostic_timeseries_materialized",
        "source": {
            "path": _relative_or_absolute(source, root),
            "sha256": _sha256(source),
        },
        "formula": {
            "return": "r_t = log(close_t / close_{t-1})",
            "headline": "rolling_corr(r_t, r_{t-1}, 250 completed daily returns)",
            "display": "trailing_mean(headline, 20 completed trading days)",
            "robustness": "median of lag1 correlations at W100/W150/W200/W250/W300/W400/W500",
            "state_thresholds": "zero axis plus at least 5/7 scale agreement; no fitted performance threshold",
        },
        "selection_evidence": {
            "authority_window_days": AUTHORITY_WINDOW_DAYS,
            "display_smooth_days": DISPLAY_SMOOTH_DAYS,
            "selected_display_middle_is_trough": bool(selected_surface["middle_is_trough"]),
            "selected_display_late_recovery_fraction": float(selected_surface["late_recovery_fraction"]),
            "candidate_count": len(candidates),
            "surface_point_count": len(surface),
        },
        "summary": {
            "daily_row_count": len(panel),
            "annual_row_count": len(annual),
            "phase_row_count": len(phases),
            "start_date": str(panel["timestamp"].min().date()),
            "end_date": str(panel["timestamp"].max().date()),
        },
        "field_labels_zh": {
            "trend_continuity_w250": "250个已完成交易日的一阶收益自相关；权威事实线",
            "trend_continuity_w250_ma20": "权威事实线的20交易日后向均值；仅用于监控展示",
            "trend_continuity_multiscale_median": "W100至W500七尺度一阶自相关中位数；稳健性复核",
            "positive_scale_share": "七个尺度中一阶自相关大于零的比例",
            "regime_state": "由零轴和尺度一致度得到的延续、混合、反转状态",
            "decision_eligible_timestamp": "当日收盘完成后，最早可用于决策的下一交易日",
        },
        "authority": {
            "diagnostic_authority": True,
            "production_authority": False,
            "tool_routing_authority": False,
            "dynamic_parameter_authority": False,
            "causal_root_proven": False,
            "opportunity_capture_proof": False,
            "requires_strategy_specific_opportunity_ledger": True,
        },
    }


def _write_timeseries_chart(panel: pd.DataFrame, output_path: Path) -> None:
    """Persist the headline raw/display series as an auditable visual."""

    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    timestamps = pd.to_datetime(panel["timestamp"])
    figure, axis = plt.subplots(figsize=(14, 5.5))
    axis.plot(
        timestamps,
        panel["trend_continuity_w250"],
        color="#8da0cb",
        linewidth=0.7,
        alpha=0.55,
        label="W250 LAG1 raw",
    )
    axis.plot(
        timestamps,
        panel["trend_continuity_w250_ma20"],
        color="#1b4f72",
        linewidth=1.5,
        label="W250 LAG1 MA20",
    )
    axis.axhline(0.0, color="#333333", linewidth=0.8)
    axis.axvspan(pd.Timestamp("2018-01-01"), pd.Timestamp("2020-12-31"), color="#f4a582", alpha=0.18)
    axis.set_title("CloudRidge trend-continuity regime")
    axis.set_ylabel("lag-one return autocorrelation")
    axis.grid(alpha=0.2)
    axis.legend(loc="upper right")
    figure.tight_layout()
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def _build_report(
    phases: pd.DataFrame,
    candidates: pd.DataFrame,
    surface: pd.DataFrame,
) -> str:
    indexed = phases.set_index("phase_id")
    early = float(indexed.loc["development_2009_2017", "trend_continuity_w250_mean"])
    middle = float(indexed.loc["audit_2018_2020", "trend_continuity_w250_mean"])
    late = float(indexed.loc["external_2021_2026", "trend_continuity_w250_mean"])
    selected = surface.loc[surface["is_selected_display"]].iloc[0]
    rejected = candidates.loc[~candidates["middle_is_trough"], "candidate_id"].tolist()
    return f"""# 趋势连续性市场状态报告

## 结论

当前最合适的公共状态线是 **W250 一阶收益自相关（LAG1）**。它在三个阶段的均值为：

- 2009—2017：`{early:.4f}`；
- 2018—2020：`{middle:.4f}`；
- 2021—2026：`{late:.4f}`。

这复现了“强—谷底—恢复”，但只代表市场收益的连续性环境，不等于任何具体策略的收益，
也不证明策略已经抓住全部机会。

## 为什么不是5日或20日重新估计

真正决定结构的是相关性的测量记忆。W100—W500形成宽平台，W250取一个交易年这一自然尺度，
不是从单点峰值选出的参数。20日只对W250结果做后向展示平滑；当前三段恢复比例为
`{float(selected['late_recovery_fraction']):.3f}`。5日平滑也保留结构，但噪声更大；更长平滑只增加延迟。

## 被排除的单一权威候选

以下候选没有同时复现中段谷底与后段恢复：`{', '.join(rejected)}`。
尤其是论文核收益包含漂移收益，2018—2020的短核反而更强；路径效率和BDCI在2021年后没有同幅恢复。

## 使用边界

这条线回答“当前是否处在有利于方向延续的公共环境”。要回答“某个策略低收益是否正常”，
还必须接该策略独立定义的机会账本，分别比较机会供给、捕获率和单位能力。禁止把本指标直接用于
路由、动态调参或生产交易。
"""


def _build_manifest(
    staging: Path,
    validation: Mapping[str, object],
    source: Path,
    root: Path,
) -> dict[str, object]:
    names = sorted(path.name for path in staging.iterdir() if path.name != "manifest.json")
    return {
        "schema_id": "market_state_trend_continuity_regime_manifest@1.0",
        "status": validation["status"],
        "canonical_entrypoint": CANONICAL_ENTRYPOINT,
        "source_path": _relative_or_absolute(source, root),
        "authority": validation["authority"],
        "artifacts": [
            {"path": name, "sha256": _sha256(staging / name), "size_bytes": (staging / name).stat().st_size}
            for name in names
        ],
    }


def _relative_or_absolute(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "AUTHORITY_WINDOW_DAYS",
    "CANONICAL_ENTRYPOINT",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_PRICE_PATH",
    "DISPLAY_SMOOTH_DAYS",
    "ROBUST_WINDOWS_DAYS",
    "build_annual_summary",
    "build_candidate_comparison",
    "build_phase_summary",
    "build_trend_continuity_panel",
    "build_window_smoothing_surface",
    "run_trend_continuity_regime",
    "validate_persisted_trend_continuity",
]
