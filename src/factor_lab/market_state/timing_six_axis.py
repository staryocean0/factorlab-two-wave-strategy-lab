# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false, reportCallIssue=false
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Causal six-axis market-state measurements for timing-strategy research.

This module measures the market; it does not select a strategy, fit a return
threshold, or grant production routing authority.  The six axes deliberately
remain separate so downstream research can test which dimensions matter.
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

from factor_lab.core.errors import ValidationError

SCHEMA_ID: Final[str] = "market_state_timing_six_axis@1.0"
CODE_VERSION: Final[str] = "timing-six-axis-20260806-r1"
DEFAULT_PRICE_PATH: Final[Path] = Path(
    "output/baylum-data-update/current/cloudridge_1d_qfq_service_confirmed_19940307_20260626_levels.csv"
)
DEFAULT_GROUP_MANIFEST_PATH: Final[Path] = Path(
    "output/market-state-foundation/group-correlation/current_manifest.json"
)
DEFAULT_OUTPUT_DIR: Final[Path] = Path(
    "output/market-state-foundation/timing-six-axis/current"
)
CANONICAL_ENTRYPOINT: Final[str] = "docs/user/market_state_timing_six_axis_workflow.md"

AXIS_IDS: Final[tuple[str, ...]] = (
    "direction",
    "directional_memory",
    "volatility_level",
    "volatility_memory",
    "path_tail",
    "cross_sectional_coherence",
)
DIRECTION_WINDOWS: Final[tuple[int, ...]] = (20, 60, 120)
MEMORY_WINDOWS: Final[tuple[int, ...]] = (50, 100, 250, 500)
MEMORY_LAGS: Final[tuple[int, ...]] = (*range(1, 13), 20, 40, 60)
EXPONENTIAL_SPANS: Final[tuple[int, ...]] = (5, 20, 60)
VOLATILITY_WINDOWS: Final[tuple[int, ...]] = (20, 60, 120)
PARAMETER_SPANS: Final[tuple[int, ...]] = (5, 10, 15, 20, 30, 60, 100, 150, 200, 300, 400, 500)


def build_timing_six_axis_panel(
    daily_bars: pd.DataFrame,
    *,
    group_attributes: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build strictly trailing daily measurements and optional group context."""

    daily = _validated_daily(daily_bars)
    result = daily[["timestamp", "close"]].copy()
    returns = np.log(daily["close"] / daily["close"].shift(1))
    result["log_return"] = returns

    # Axis 1: signed direction, separated from persistence.
    for window in DIRECTION_WINDOWS:
        signed_path = returns.rolling(window, min_periods=window).sum()
        gross_path = returns.abs().rolling(window, min_periods=window).sum()
        result[f"direction_wbi_w{window}"] = signed_path / gross_path.replace(0.0, np.nan)
        result[f"direction_cumulative_log_return_w{window}"] = signed_path
    result["axis_direction"] = result["direction_wbi_w60"]

    # Axis 2: full selected ACF term structure. W250 LAG1 is one coordinate,
    # not an authority over the other axes.
    acf_cache: dict[tuple[int, int], pd.Series] = {}
    for window in MEMORY_WINDOWS:
        for lag in MEMORY_LAGS:
            values = returns.rolling(window, min_periods=window).corr(returns.shift(lag))
            acf_cache[(window, lag)] = values
            result[f"return_acf_lag{lag}_w{window}"] = values
    for span in EXPONENTIAL_SPANS:
        result[f"directional_memory_exp_s{span}_w250"] = _exponential_acf_projection(
            returns, span=span, window=250
        )
    result["axis_directional_memory"] = result["directional_memory_exp_s20_w250"]

    # Axis 3: current movement amplitude, independent of direction.
    for window in VOLATILITY_WINDOWS:
        result[f"realized_volatility_w{window}"] = (
            returns.rolling(window, min_periods=window).std(ddof=0) * math.sqrt(260.0)
        )
        result[f"mean_absolute_return_w{window}"] = returns.abs().rolling(
            window, min_periods=window
        ).mean()
    result["axis_volatility_level"] = result["realized_volatility_w60"]

    # Axis 4: clustering of volatility, not the volatility level itself.
    for window in (60, 250):
        result[f"abs_return_acf_lag1_w{window}"] = returns.abs().rolling(
            window, min_periods=window
        ).corr(returns.abs().shift(1))
        result[f"squared_return_acf_lag1_w{window}"] = returns.pow(2).rolling(
            window, min_periods=window
        ).corr(returns.pow(2).shift(1))
    result["axis_volatility_memory"] = (
        result["abs_return_acf_lag1_w250"] + result["squared_return_acf_lag1_w250"]
    ) / 2.0

    # Axis 5: route shape and tail concentration. The exact alias to |WBI| is
    # intentionally materialized and tested instead of being treated as new information.
    for window in (20, 60, 120):
        net = returns.rolling(window, min_periods=window).sum().abs()
        gross = returns.abs().rolling(window, min_periods=window).sum()
        result[f"path_efficiency_w{window}"] = net / gross.replace(0.0, np.nan)
    for window in (20, 60):
        abs_returns = returns.abs()
        result[f"tail_energy_concentration_w{window}"] = (
            abs_returns.rolling(window, min_periods=window).max()
            / abs_returns.rolling(window, min_periods=window).sum().replace(0.0, np.nan)
        )
        result[f"return_skewness_w{window}"] = returns.rolling(
            window, min_periods=window
        ).skew()
    result["axis_path_tail"] = result["path_efficiency_w60"]

    # Axis 6: independent group behaviour. Missing optional input remains
    # explicit rather than being imputed from the index itself.
    result = _merge_group_axis(result, group_attributes)

    result["available_at"] = result["timestamp"].dt.strftime("%Y-%m-%dT15:30:00+08:00")
    result["decision_eligible_date"] = result["timestamp"].shift(-1).dt.strftime("%Y-%m-%d")
    for axis in AXIS_IDS:
        column = "axis_path_tail" if axis == "path_tail" else f"axis_{axis}"
        result[f"{axis}_valid"] = result[column].notna()
    return result


def build_axis_catalog() -> list[dict[str, object]]:
    """Return the six-axis contract and prevent category collapse."""

    return [
        {
            "axis_id": "direction",
            "label_zh": "方向",
            "headline": "axis_direction",
            "question": "市场净向上还是净向下？",
            "components": ["direction_wbi_w20", "direction_wbi_w60", "direction_wbi_w120"],
            "orthogonality": "与方向记忆分开；强自相关既可能上涨也可能下跌。",
        },
        {
            "axis_id": "directional_memory",
            "label_zh": "方向记忆",
            "headline": "axis_directional_memory",
            "question": "收益方向是否延续，以及延续发生在哪些滞后和尺度？",
            "components": ["return_acf_lag{k}_w{W}", "directional_memory_exp_s{S}_w250"],
            "orthogonality": "ACF、VR、论文指数核和Hurst属于同一根系的不同投影，不重复计票。",
        },
        {
            "axis_id": "volatility_level",
            "label_zh": "波动水平",
            "headline": "axis_volatility_level",
            "question": "市场当前动得多大？",
            "components": ["realized_volatility_w20", "realized_volatility_w60", "realized_volatility_w120"],
            "orthogonality": "只度量振幅，不度量方向或波动聚集。",
        },
        {
            "axis_id": "volatility_memory",
            "label_zh": "波动记忆",
            "headline": "axis_volatility_memory",
            "question": "大波动是否成簇持续？",
            "components": ["abs_return_acf_lag1_w250", "squared_return_acf_lag1_w250"],
            "orthogonality": "同样的波动水平可以有完全不同的波动聚集结构。",
        },
        {
            "axis_id": "path_tail",
            "label_zh": "路径与尾部",
            "headline": "axis_path_tail",
            "question": "净位移是否由平顺路径完成，还是由少数跳变主导？",
            "components": ["path_efficiency_w60", "tail_energy_concentration_w60", "return_skewness_w60"],
            "orthogonality": "headline只代表路径效率；尾部集中和偏度仍须独立读取。",
        },
        {
            "axis_id": "cross_sectional_coherence",
            "label_zh": "截面共振",
            "headline": "axis_cross_sectional_coherence",
            "question": "全市场股票是否共同运动？",
            "components": ["group_corr_level_60d", "group_corr_dispersion_60d", "group_common_mode_share_60d"],
            "orthogonality": "来自股票截面，不能由单一云脊价格路径替代。",
        },
    ]


def build_information_topology() -> dict[str, object]:
    """Machine-readable identity, mapping and non-mapping rules."""

    return {
        "schema_id": "market_state_timing_six_axis_information_topology@1.0",
        "exact_aliases": [
            {
                "left": "path_efficiency_wN",
                "right": "abs(direction_wbi_wN)",
                "formula": "abs(sum(r_t)) / sum(abs(r_t))",
            },
            {
                "left": "noise_ratio_wN",
                "right": "1 - path_efficiency_wN",
                "formula": "1 - abs(sum(r_t)) / sum(abs(r_t))",
            },
        ],
        "same_root_projections": [
            {
                "family": "directional_memory",
                "members": ["ACF", "variance_ratio", "exponential_paper_kernel_projection", "Hurst", "BDCI"],
                "rules": [
                    "VR(q)=1+2*sum_{k=1}^{q-1}(1-k/q)*rho(k)",
                    "EXP(S)=weighted_mean(nu(S)^k*rho(k)); nu=(S-1)/(S+1)",
                    "VR(q) is proportional to q^(2H-1) under scaling assumptions",
                    "BDCI is approximately 50+100/pi*asin(rho1) under elliptical sign symmetry",
                ],
                "restriction": "同根投影可互证，禁止当成多个独立因子重复投票。",
            }
        ],
        "orthogonal_axes": [
            "volatility_level",
            "volatility_memory",
            "path_tail_residual_beyond_abs_wbi",
            "cross_sectional_coherence",
        ],
        "forbidden_mapping": {
            "rule": "禁止把单一LAG k稳定映射为唯一的路径窗口q。",
            "reason": "滞后相关描述局部时间间隔，路径效率聚合整段净位移；两者不是一一对应。",
        },
    }


def build_parameter_mapping_catalog() -> list[dict[str, object]]:
    """Expose the stable paper-span to triangular-kernel scale mapping."""

    mapped = (6, 13, 19, 25, 37, 75, 124, 186, 247, 371, 494, 618)
    return [
        {
            "paper_span_s": span,
            "triangular_vr_path_q": q,
            "mapping_rule": "q ~= 1.24*S; nearest integer from normalized-kernel total-variation fit",
            "mapping_status": "stable_same_root_scale_correspondence",
            "strategy_authority": False,
        }
        for span, q in zip(PARAMETER_SPANS, mapped, strict=True)
    ]


def run_timing_six_axis(
    *,
    project_root: Path,
    output_dir: Path,
    price_path: Path | None = None,
    group_manifest_path: Path | None = None,
) -> dict[str, object]:
    """Materialize an auditable package and validate it before publication."""

    root = project_root.resolve()
    source = (price_path or root / DEFAULT_PRICE_PATH).resolve()
    group_manifest = (group_manifest_path or root / DEFAULT_GROUP_MANIFEST_PATH).resolve()
    if not source.exists():
        raise ValidationError(f"six-axis price source does not exist: {source}")
    if not group_manifest.exists():
        raise ValidationError(f"six-axis group manifest does not exist: {group_manifest}")
    bars = pd.read_csv(source)
    group, group_artifact = _load_group_attributes(group_manifest)
    panel = build_timing_six_axis_panel(bars, group_attributes=group)
    catalog = build_axis_catalog()
    topology = build_information_topology()
    mappings = build_parameter_mapping_catalog()
    validation = _build_validation(panel, catalog, source, group_manifest, group_artifact, root)

    output = output_dir.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="timing-six-axis-", dir=output.parent) as tmp:
        staging = Path(tmp)
        panel.to_csv(staging / "six_axis_timeseries.csv", index=False, float_format="%.12g")
        _write_json(staging / "axis_catalog.json", {"schema_id": SCHEMA_ID, "axes": catalog})
        _write_json(staging / "information_topology.json", topology)
        _write_json(staging / "parameter_mapping_catalog.json", {"mappings": mappings})
        _write_json(staging / "validation.json", validation)
        _ = (staging / "report_zh.md").write_text(_build_report(panel), encoding="utf-8")
        manifest = _build_manifest(staging, validation, source, group_manifest, root)
        _write_json(staging / "manifest.json", manifest)
        if output.exists():
            shutil.rmtree(output)
        _ = shutil.copytree(staging, output)
    validate_persisted_timing_six_axis(output)
    return _read_json(output / "manifest.json")


def validate_persisted_timing_six_axis(output_dir: Path) -> None:
    """Fail closed on missing axes, authority escalation or artifact drift."""

    required = {
        "six_axis_timeseries.csv",
        "axis_catalog.json",
        "information_topology.json",
        "parameter_mapping_catalog.json",
        "validation.json",
        "report_zh.md",
        "manifest.json",
    }
    missing = sorted(name for name in required if not (output_dir / name).exists())
    if missing:
        raise ValidationError(f"six-axis output missing files: {missing}")
    validation = _read_json(output_dir / "validation.json")
    if validation.get("schema_id") != SCHEMA_ID:
        raise ValidationError("six-axis schema id drifted")
    authority = validation.get("authority")
    if not isinstance(authority, Mapping) or any(
        authority.get(key) is not False
        for key in ("production_authority", "tool_routing_authority", "dynamic_parameter_authority")
    ):
        raise ValidationError("six-axis measurements must not self-grant strategy authority")
    catalog = _read_json(output_dir / "axis_catalog.json")
    axes = cast(Sequence[Mapping[str, object]], catalog.get("axes", []))
    if tuple(item.get("axis_id") for item in axes) != AXIS_IDS:
        raise ValidationError("six-axis catalog no longer contains the canonical six axes")
    panel = pd.read_csv(output_dir / "six_axis_timeseries.csv")
    if panel["timestamp"].duplicated().any():
        raise ValidationError("six-axis time series contains duplicate timestamps")
    if not np.allclose(
        panel["path_efficiency_w60"], panel["direction_wbi_w60"].abs(), equal_nan=True
    ):
        raise ValidationError("path efficiency and abs(WBI) exact alias drifted")
    manifest = _read_json(output_dir / "manifest.json")
    artifacts = cast(Sequence[Mapping[str, object]], manifest.get("artifacts", []))
    for item in artifacts:
        path = output_dir / str(item["path"])
        if _sha256(path) != item["sha256"]:
            raise ValidationError(f"six-axis artifact hash mismatch: {path.name}")


def _exponential_acf_projection(returns: pd.Series, *, span: int, window: int) -> pd.Series:
    nu = (span - 1.0) / (span + 1.0)
    max_lag = min(3 * span, window // 2)
    weighted_sum = pd.Series(0.0, index=returns.index)
    total_weight = 0.0
    validity = pd.Series(True, index=returns.index)
    for lag in range(1, max_lag + 1):
        weight = nu**lag
        rho = returns.rolling(window, min_periods=window).corr(returns.shift(lag))
        weighted_sum = weighted_sum.add(rho * weight)
        validity &= rho.notna()
        total_weight += weight
    projected = weighted_sum / total_weight
    return projected.where(validity)


def _merge_group_axis(result: pd.DataFrame, group: pd.DataFrame | None) -> pd.DataFrame:
    output = result.copy()
    expected = [
        f"{attribute}_{scale}"
        for scale in ("20d", "60d", "120d")
        for attribute in ("group_corr_level", "group_corr_dispersion", "group_common_mode_share")
    ]
    if group is None or group.empty:
        for column in expected:
            output[column] = np.nan
        output["axis_cross_sectional_coherence"] = np.nan
        return output
    data = group.loc[group["carrier_id"].astype(str).eq("cn_a_all_market")].copy()
    data["timestamp"] = pd.to_datetime(data["observation_time"], errors="coerce", utc=True).dt.tz_convert(
        "Asia/Shanghai"
    ).dt.tz_localize(None).dt.normalize()
    data["column"] = data["physical_attribute_id"].astype(str) + "_" + data["measurement_scale_id"].astype(str)
    wide = data.pivot_table(index="timestamp", columns="column", values="raw_value", aggfunc="last").reset_index()
    output = output.merge(wide[["timestamp", *[c for c in expected if c in wide.columns]]], on="timestamp", how="left")
    for column in expected:
        if column not in output:
            output[column] = np.nan
    output["axis_cross_sectional_coherence"] = output["group_corr_level_60d"]
    return output


def _load_group_attributes(manifest_path: Path) -> tuple[pd.DataFrame, Path]:
    manifest = _read_json(manifest_path)
    bundle_id = str(manifest.get("bundle_id", ""))
    if not bundle_id:
        raise ValidationError("group-correlation manifest lacks bundle_id")
    bundle_dir = manifest_path.parent / "versions" / bundle_id if manifest_path.name == "current_manifest.json" else manifest_path.parent
    artifact = bundle_dir / "market_attributes.parquet"
    if not artifact.exists():
        raise ValidationError(f"group-correlation market attributes not found: {artifact}")
    return pd.read_parquet(artifact), artifact


def _validated_daily(frame: pd.DataFrame) -> pd.DataFrame:
    timestamp_column = "timestamp" if "timestamp" in frame.columns else "trading_day"
    missing = {timestamp_column, "close"} - set(frame.columns)
    if missing:
        raise ValidationError(f"six-axis daily panel missing columns: {sorted(missing)}")
    daily = frame[[timestamp_column, "close"]].copy()
    daily.columns = ["timestamp", "close"]
    daily["timestamp"] = pd.to_datetime(daily["timestamp"], errors="coerce").dt.tz_localize(None).dt.normalize()
    daily["close"] = pd.to_numeric(daily["close"], errors="coerce")
    daily = daily.dropna()
    daily = daily.sort_values(by=["timestamp"])
    daily = daily.drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    if len(daily) <= max(MEMORY_WINDOWS) + max(MEMORY_LAGS):
        raise ValidationError("six-axis daily panel lacks long-window history")
    if bool((daily["close"] <= 0.0).any()):
        raise ValidationError("six-axis close values must be positive")
    return daily


def _build_validation(
    panel: pd.DataFrame,
    catalog: Sequence[Mapping[str, object]],
    source: Path,
    group_manifest: Path,
    group_artifact: Path,
    root: Path,
) -> dict[str, object]:
    headline_columns = [str(item["headline"]) for item in catalog]
    return {
        "schema_id": SCHEMA_ID,
        "code_version": CODE_VERSION,
        "status": "six_axis_measurement_timeseries_materialized",
        "sources": {
            "price": {"path": _relative_or_absolute(source, root), "sha256": _sha256(source)},
            "group_manifest": {"path": _relative_or_absolute(group_manifest, root), "sha256": _sha256(group_manifest)},
            "group_attributes": {"path": _relative_or_absolute(group_artifact, root), "sha256": _sha256(group_artifact)},
        },
        "summary": {
            "axis_count": len(catalog),
            "row_count": len(panel),
            "start_date": str(panel["timestamp"].min().date()),
            "end_date": str(panel["timestamp"].max().date()),
            "headline_non_null_counts": {column: int(panel[column].notna().sum()) for column in headline_columns},
        },
        "causality": {
            "strictly_trailing_windows": True,
            "same_close_not_actionable": True,
            "decision_eligible_from_next_trading_day": True,
            "future_strategy_returns_used": False,
            "performance_fitted_thresholds": False,
        },
        "authority": {
            "measurement_authority": True,
            "production_authority": False,
            "tool_routing_authority": False,
            "dynamic_parameter_authority": False,
            "strategy_effectiveness_claim": False,
        },
    }


def _build_report(panel: pd.DataFrame) -> str:
    valid = {axis: int(panel[f"{axis}_valid"].sum()) for axis in AXIS_IDS}
    return f"""# 择时策略六轴市场状态生成报告

## 结论

六条状态轴已生成：方向、方向记忆、波动水平、波动记忆、路径与尾部、截面共振。
时序覆盖 `{panel['timestamp'].min().date()}` 至 `{panel['timestamp'].max().date()}`，共 `{len(panel)}` 个交易日。

## 有效观测数

- 方向：`{valid['direction']}`
- 方向记忆：`{valid['directional_memory']}`
- 波动水平：`{valid['volatility_level']}`
- 波动记忆：`{valid['volatility_memory']}`
- 路径与尾部：`{valid['path_tail']}`
- 截面共振：`{valid['cross_sectional_coherence']}`

## 边界

这是市场测量层，不是交易信号。不根据策略收益选阈值，不对工具排序，不动态切换参数，
不授予生产权。W250-LAG1只是“方向记忆”轴中的一个坐标，不再代表全部市场状态。
"""


def _build_manifest(
    staging: Path,
    validation: Mapping[str, object],
    source: Path,
    group_manifest: Path,
    root: Path,
) -> dict[str, object]:
    names = sorted(path.name for path in staging.iterdir() if path.name != "manifest.json")
    return {
        "schema_id": "market_state_timing_six_axis_manifest@1.0",
        "code_version": CODE_VERSION,
        "canonical_entrypoint": CANONICAL_ENTRYPOINT,
        "price_source": _relative_or_absolute(source, root),
        "group_manifest_source": _relative_or_absolute(group_manifest, root),
        "authority": validation["authority"],
        "artifacts": [
            {"path": name, "sha256": _sha256(staging / name), "size_bytes": (staging / name).stat().st_size}
            for name in names
        ],
    }


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValidationError(f"JSON object required: {path}")
    return {str(key): value for key, value in payload.items()}


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    _ = path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    "AXIS_IDS",
    "CANONICAL_ENTRYPOINT",
    "DEFAULT_GROUP_MANIFEST_PATH",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_PRICE_PATH",
    "SCHEMA_ID",
    "build_axis_catalog",
    "build_information_topology",
    "build_parameter_mapping_catalog",
    "build_timing_six_axis_panel",
    "run_timing_six_axis",
    "validate_persisted_timing_six_axis",
]
