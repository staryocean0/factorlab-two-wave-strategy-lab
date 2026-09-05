# ruff: noqa: E501
# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportMissingTypeStubs=false
# pyright: reportImplicitStringConcatenation=false
# pyright: reportUnnecessaryCast=false
# pyright: reportUnusedCallResult=false
"""Render artifacts for filter timing strategy backtests.

The strategy workflow is intentionally research-oriented, but the final
backtest stage must leave a visual artifact that explains *why* trades happened:
price K-line, execution-period filter, higher-period filter, and buy/sell
markers are shown together under the same no-lookahead protocol used by the
backtest.
"""

from __future__ import annotations

import csv
import html
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, cast

import numpy as np
import pandas as pd

from factor_lab.filtering.costs import (
    DEFAULT_COMMISSION_BPS,
    DEFAULT_STAMP_TAX_BPS,
    resolve_long_cash_cost_model,
)
from factor_lab.filtering.timing_validation import BACKTEST_FIELD_LABELS_ZH

PriceScale = Literal["linear", "log"]
CoordinateMapper = Callable[[int], float]
ValueMapper = Callable[[float], float]


@dataclass(frozen=True, slots=True)
class FilterTimingStrategyRenderArtifacts:
    """Files produced by the final strategy-backtest render stage."""

    strategy_svg: str
    report_html: str
    signal_csv: str
    signal_row_count: int
    chart_bar_count: int
    chart_scope: str
    price_scale: str
    render_protocol: str
    render_protocol_zh: str
    signal_field_labels_zh: dict[str, str]
    backtest_field_labels_zh: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


SIGNAL_FIELD_LABELS_ZH: dict[str, str] = {
    "timestamp": "K线时间",
    "open": "展示用开盘价：上一根收盘价",
    "high": "展示用最高价：本根与上一根收盘价较大者",
    "low": "展示用最低价：本根与上一根收盘价较小者",
    "close": "收盘价/指数点位",
    "execution_filter": "本级别滤波值",
    "higher_filter": "上一级可用滤波值，已滞后一根上级K线再前向填充；单周期模板为空",
    "gate_signal": "上一级门禁信号，1=允许做多；单周期模板恒为1",
    "trigger_signal": "本级别触发信号，分量K线方向向上为1、向下为0",
    "composite_signal": "复合信号，执行前的目标持仓状态",
    "position": "实际持仓，上一根信号在本根执行后的持仓",
    "strategy_nav": "策略净值",
    "trade_marker": "交易标记：buy=买入执行点，sell=卖出执行点",
}


def write_filter_timing_strategy_render_artifacts(
    *,
    output_prefix: str | Path,
    index_ref: str,
    higher_period: str | None,
    execution_period: str,
    higher_filter_name: str | None,
    execution_filter_name: str,
    execution_close: pd.Series,
    execution_filtered: pd.Series,
    higher_filtered_available: pd.Series | None,
    aligned_gate: pd.Series | None,
    aligned_trigger: pd.Series,
    composite_signal: pd.Series,
    cost_bps: float | None = None,
    commission_bps: float = DEFAULT_COMMISSION_BPS,
    stamp_tax_bps: float = DEFAULT_STAMP_TAX_BPS,
    price_scale: str = "linear",
    max_chart_bars: int = 1600,
) -> FilterTimingStrategyRenderArtifacts:
    """Write CSV, HTML, and SVG artifacts for a strategy backtest.

    The CSV contains the full aligned backtest surface.  The SVG may plot only
    the latest `max_chart_bars` bars to keep the artifact readable for intraday
    workflows; this scope is reported in the returned artifact metadata.
    """

    resolved_scale = normalize_strategy_price_scale(price_scale)
    if max_chart_bars < 50:
        raise ValueError("max_chart_bars must be >= 50")
    rows = _strategy_render_rows(
        execution_close=execution_close,
        execution_filtered=execution_filtered,
        higher_filtered_available=higher_filtered_available,
        aligned_gate=aligned_gate,
        aligned_trigger=aligned_trigger,
        composite_signal=composite_signal,
        cost_bps=cost_bps,
        commission_bps=commission_bps,
        stamp_tax_bps=stamp_tax_bps,
    )
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    signal_csv = prefix.with_suffix(".signals.csv")
    strategy_svg = prefix.with_suffix(".strategy.svg")
    report_html = prefix.with_suffix(".html")

    _write_rows_csv(signal_csv, rows)
    chart_rows = rows[-max_chart_bars:]
    chart_scope = "full" if len(rows) <= max_chart_bars else f"tail_{max_chart_bars}"
    write_filter_timing_strategy_svg(
        strategy_svg,
        chart_rows,
        title=f"{index_ref} filter timing backtest",
        higher_period=higher_period,
        execution_period=execution_period,
        higher_filter_name=higher_filter_name,
        execution_filter_name=execution_filter_name,
        price_scale=resolved_scale,
        chart_scope=chart_scope,
    )
    write_filter_timing_strategy_report_html(
        report_html,
        index_ref=index_ref,
        strategy_svg=strategy_svg,
        signal_csv=signal_csv,
        higher_period=higher_period,
        execution_period=execution_period,
        higher_filter_name=higher_filter_name,
        execution_filter_name=execution_filter_name,
        signal_row_count=len(rows),
        chart_bar_count=len(chart_rows),
        chart_scope=chart_scope,
        price_scale=resolved_scale,
    )
    return FilterTimingStrategyRenderArtifacts(
        strategy_svg=str(strategy_svg),
        report_html=str(report_html),
        signal_csv=str(signal_csv),
        signal_row_count=len(rows),
        chart_bar_count=len(chart_rows),
        chart_scope=chart_scope,
        price_scale=resolved_scale,
        render_protocol=(
            "close_to_close_execution_period_candles; higher filter is shifted "
            "one higher-period bar then forward-filled when the template uses "
            "a higher-period gate; markers show executed position changes on "
            "the next execution bar"
        ),
        render_protocol_zh=(
            "执行周期使用收盘到收盘K线；双周期模板中上一级滤波值先滞后一根"
            "上级K线再前向填充；单周期模板不使用上一级门禁；买卖标记画在"
            "下一根K线实际执行后的持仓变化点。"
        ),
        signal_field_labels_zh=dict(SIGNAL_FIELD_LABELS_ZH),
        backtest_field_labels_zh=dict(BACKTEST_FIELD_LABELS_ZH),
    )


def normalize_strategy_price_scale(price_scale: str) -> PriceScale:
    value = str(price_scale or "linear").strip().lower()
    if value not in {"linear", "log"}:
        raise ValueError("price_scale must be 'linear' or 'log'")
    return cast(PriceScale, value)


def write_filter_timing_strategy_report_html(
    path: Path,
    *,
    index_ref: str,
    strategy_svg: Path,
    signal_csv: Path,
    higher_period: str | None,
    execution_period: str,
    higher_filter_name: str | None,
    execution_filter_name: str,
    signal_row_count: int,
    chart_bar_count: int,
    chart_scope: str,
    price_scale: str,
) -> None:
    escaped_index = html.escape(index_ref)
    higher_period_label = _higher_label(higher_period)
    higher_filter_label = _higher_label(higher_filter_name)
    higher_policy = (
        "本模板不使用上一级方向门禁；方向识别和买卖触发都来自本级别滤波分量。"
        if higher_period is None or higher_filter_name is None
        else "上一级滤波指标先滞后一根上一级K线，再向执行周期 forward-fill。"
    )
    path.write_text(
        "\n".join(
            [
                "<!doctype html><html><head><meta charset='utf-8'>",
                f"<title>{escaped_index} 滤波择时回测</title>",
                "<style>body{font-family:sans-serif;margin:24px;}img{max-width:100%;}"
                "code{background:#f3f4f6;padding:2px 4px;border-radius:3px;}"
                "table{border-collapse:collapse;}td,th{border:1px solid #d1d5db;padding:4px 8px;}"
                "</style>",
                "</head><body>",
                f"<h1>{escaped_index} 滤波择时回测图</h1>",
                "<p>图中展示执行周期K线、买入/卖出点、本级别滤波指标；双周期模板还展示上一级滤波指标。</p>",
                "<ul>",
                f"<li>执行周期：{html.escape(execution_period)}；上一级周期：{html.escape(higher_period_label)}</li>",
                f"<li>本级别滤波器：{html.escape(execution_filter_name)}</li>",
                f"<li>上一级滤波器：{html.escape(higher_filter_label)}</li>",
                f"<li>价格坐标：{html.escape(price_scale)}；图表范围：{html.escape(chart_scope)}</li>",
                f"<li>信号CSV行数：{signal_row_count}；图上K线数：{chart_bar_count}</li>",
                "</ul>",
                (
                    "<p><b>防未来函数口径：</b>"
                    f"{html.escape(higher_policy)}"
                    " 策略信号在执行周期 t 观察，在 t+1 执行。</p>"
                ),
                (
                    "<p><b>买卖点口径：</b>本级别滤波分量按自身K线涨跌方向切换；"
                    "分量K线由下跌转为上涨后下一根K线买入，"
                    "由上涨转为下跌后下一根K线卖出。"
                    "图上的 buy/sell 是执行后的持仓变化点，不是信号生成点。</p>"
                ),
                _field_dictionary_html(SIGNAL_FIELD_LABELS_ZH),
                f"<p><a href='{html.escape(signal_csv.name)}'>下载逐K线信号CSV</a></p>",
                f"<p><img src='{html.escape(strategy_svg.name)}' alt='filter timing strategy chart'></p>",
                "</body></html>",
            ]
        ),
        encoding="utf-8",
    )


def write_filter_timing_strategy_svg(
    path: Path,
    rows: Sequence[Mapping[str, object]],
    *,
    title: str,
    higher_period: str | None,
    execution_period: str,
    higher_filter_name: str | None,
    execution_filter_name: str,
    price_scale: str = "linear",
    chart_scope: str = "full",
) -> None:
    resolved_scale = normalize_strategy_price_scale(price_scale)
    width = 1500
    height = 980
    left = 82
    right = 42
    top = 60
    price_height = 440
    exec_top = top + price_height + 42
    indicator_height = 150
    higher_top = exec_top + indicator_height + 48
    bottom = 70
    plot_width = width - left - right
    values = [_as_render_row(row) for row in rows]
    values = [row for row in values if row["close"] is not None]
    if not values:
        path.write_text(_empty_svg(width, height, title, "No backtest rows to chart"), encoding="utf-8")
        return
    if resolved_scale == "log" and any(_required_float(row["low"]) <= 0.0 for row in values):
        raise ValueError("log price scale requires positive prices")

    count = len(values)
    step = plot_width / max(count - 1, 1)
    body_width = min(8.0, max(1.4, plot_width / max(count, 1) * 0.62))

    def x_at(index: int) -> float:
        return left + step * index if count > 1 else left + plot_width / 2

    price_scale_bounds = _scaled_bounds(
        [_required_float(row["low"]) for row in values if row["low"] is not None]
        + [_required_float(row["high"]) for row in values if row["high"] is not None],
        price_scale=resolved_scale,
    )

    def y_price(value: float) -> float:
        scaled = _scale_value(value, resolved_scale)
        y_min, y_max = price_scale_bounds
        return top + (y_max - scaled) / (y_max - y_min) * price_height

    exec_bounds = _linear_bounds([_optional_float(row["execution_filter"]) for row in values])
    higher_bounds = _linear_bounds([_optional_float(row["higher_filter"]) for row in values])

    def y_exec(value: float) -> float:
        y_min, y_max = exec_bounds
        return exec_top + (y_max - value) / (y_max - y_min) * indicator_height

    def y_higher(value: float) -> float:
        y_min, y_max = higher_bounds
        return higher_top + (y_max - value) / (y_max - y_min) * indicator_height

    lines = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<rect width='100%' height='100%' fill='white'/>",
        (
            f"<text x='{width / 2:.0f}' y='32' text-anchor='middle' "
            "font-family='sans-serif' font-size='22'>"
            f"{html.escape(title)} — {html.escape(chart_scope)} ({html.escape(resolved_scale)})</text>"
        ),
    ]
    _append_panel_grid(lines, left, top, plot_width, price_height, label="价格K线 + 买卖点 / K-line + trades")
    _append_panel_grid(lines, left, exec_top, plot_width, indicator_height, label="本级别滤波 / Execution filter")
    higher_panel_label = (
        "无上一级门禁 / Single-period direction source"
        if higher_period is None or higher_filter_name is None
        else "上一级滤波 / Higher filter"
    )
    _append_panel_grid(
        lines,
        left,
        higher_top,
        plot_width,
        indicator_height,
        label=higher_panel_label,
    )
    _append_price_axis(lines, left, top, price_height, price_scale_bounds, resolved_scale)
    _append_indicator_axis(lines, left, exec_top, indicator_height, exec_bounds)
    _append_indicator_axis(lines, left, higher_top, indicator_height, higher_bounds)
    _append_time_axis(lines, values, x_at=x_at, left=left, top=top, width=plot_width, height=height, bottom=bottom)

    for index, row in enumerate(values):
        x = x_at(index)
        open_ = _required_float(row["open"])
        high = _required_float(row["high"])
        low = _required_float(row["low"])
        close = _required_float(row["close"])
        color = "#dc2626" if close >= open_ else "#16a34a"
        y_open = y_price(open_)
        y_close = y_price(close)
        body_top = min(y_open, y_close)
        body_height = max(abs(y_close - y_open), 1.0)
        lines.append(
            f"<line x1='{x:.2f}' y1='{y_price(high):.2f}' x2='{x:.2f}' y2='{y_price(low):.2f}' "
            f"stroke='{color}' stroke-width='1.1'/>"
        )
        lines.append(
            f"<rect x='{x - body_width / 2:.2f}' y='{body_top:.2f}' width='{body_width:.2f}' "
            f"height='{body_height:.2f}' fill='{color}' stroke='{color}' opacity='0.82'/>"
        )
        marker = str(row.get("trade_marker") or "")
        if marker == "buy":
            y = y_price(low) + 16
            lines.append(
                f"<polygon points='{x:.2f},{y - 14:.2f} {x - 7:.2f},{y:.2f} {x + 7:.2f},{y:.2f}' "
                "fill='#2563eb' stroke='white' stroke-width='1'><title>Buy</title></polygon>"
            )
        elif marker == "sell":
            y = y_price(high) - 16
            lines.append(
                f"<polygon points='{x:.2f},{y + 14:.2f} {x - 7:.2f},{y:.2f} {x + 7:.2f},{y:.2f}' "
                "fill='#f97316' stroke='white' stroke-width='1'><title>Sell</title></polygon>"
            )

    lines.append(_polyline(_indicator_points(values, "execution_filter", x_at=x_at, y_at=y_exec), "#7c3aed", 2.0))
    lines.append(_polyline(_indicator_points(values, "higher_filter", x_at=x_at, y_at=y_higher), "#0f766e", 2.0))
    _append_zero_line(lines, exec_bounds, left, exec_top, plot_width, indicator_height)
    _append_zero_line(lines, higher_bounds, left, higher_top, plot_width, indicator_height)
    _append_legend(
        lines,
        width=width,
        execution_period=execution_period,
        higher_period=higher_period,
        execution_filter_name=execution_filter_name,
        higher_filter_name=higher_filter_name,
    )
    lines.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(line for line in lines if line), encoding="utf-8")


def _field_dictionary_html(labels: Mapping[str, str]) -> str:
    rows = [
        "<details><summary><b>CSV字段说明</b></summary>",
        "<table><thead><tr><th>字段</th><th>中文解释</th></tr></thead><tbody>",
    ]
    for field, label in labels.items():
        rows.append(
            "<tr>"
            f"<td><code>{html.escape(field)}</code></td>"
            f"<td>{html.escape(label)}</td>"
            "</tr>"
        )
    rows.append("</tbody></table></details>")
    return "".join(rows)


def _strategy_render_rows(
    *,
    execution_close: pd.Series,
    execution_filtered: pd.Series,
    higher_filtered_available: pd.Series | None,
    aligned_gate: pd.Series | None,
    aligned_trigger: pd.Series,
    composite_signal: pd.Series,
    cost_bps: float | None = None,
    commission_bps: float = DEFAULT_COMMISSION_BPS,
    stamp_tax_bps: float = DEFAULT_STAMP_TAX_BPS,
) -> list[dict[str, object]]:
    signal = cast(pd.Series, composite_signal.dropna().astype(float).clip(0.0, 1.0))
    if signal.empty:
        return []
    close = cast(pd.Series, execution_close.sort_index().astype(float).reindex(signal.index).ffill())
    close = cast(pd.Series, close[close > 0.0])
    signal = cast(pd.Series, signal.reindex(close.index).fillna(0.0).clip(0.0, 1.0))
    previous_close = cast(pd.Series, close.shift(1).fillna(close))
    raw_returns = pd.Series(
        np.log(close.to_numpy(dtype=np.float64)),
        index=close.index,
    ).diff().fillna(0.0)
    position = cast(pd.Series, signal.shift(1).fillna(0.0).clip(0.0, 1.0))
    position_change = cast(pd.Series, position.diff().fillna(position))
    buy_turnover = position_change.clip(lower=0.0)
    sell_turnover = (-position_change).clip(lower=0.0)
    cost_model = resolve_long_cash_cost_model(
        cost_bps=cost_bps,
        commission_bps=commission_bps,
        stamp_tax_bps=stamp_tax_bps,
    )
    strategy_returns = cast(
        pd.Series,
        position * raw_returns
        - buy_turnover * (cost_model.buy_cost_bps / 10000.0)
        - sell_turnover * (cost_model.sell_cost_bps / 10000.0),
    )
    nav = pd.Series(np.exp(strategy_returns.cumsum().to_numpy(dtype=np.float64)), index=strategy_returns.index)
    position_change = cast(pd.Series, position.diff().fillna(position))
    execution_indicator = cast(pd.Series, execution_filtered.reindex(close.index).ffill())
    if higher_filtered_available is None:
        higher_indicator = pd.Series(np.nan, index=close.index, dtype=float)
    else:
        higher_indicator = cast(
            pd.Series,
            higher_filtered_available.reindex(close.index).ffill(),
        )
    if aligned_gate is None:
        gate = pd.Series(1.0, index=close.index, dtype=float)
    else:
        gate = cast(
            pd.Series,
            aligned_gate.reindex(close.index).fillna(0.0).clip(0.0, 1.0),
        )
    trigger = cast(pd.Series, aligned_trigger.reindex(close.index).fillna(0.0).clip(0.0, 1.0))

    rows: list[dict[str, object]] = []
    for timestamp in close.index:
        open_ = float(previous_close.loc[timestamp])
        close_value = float(close.loc[timestamp])
        high = max(open_, close_value)
        low = min(open_, close_value)
        marker = ""
        change = float(position_change.loc[timestamp])
        if change > 0.0:
            marker = "buy"
        elif change < 0.0:
            marker = "sell"
        rows.append(
            {
                "timestamp": _timestamp_iso(timestamp),
                "open": open_,
                "high": high,
                "low": low,
                "close": close_value,
                "execution_filter": _finite_or_blank(execution_indicator.loc[timestamp]),
                "higher_filter": _finite_or_blank(higher_indicator.loc[timestamp]),
                "gate_signal": float(gate.loc[timestamp]),
                "trigger_signal": float(trigger.loc[timestamp]),
                "composite_signal": float(signal.loc[timestamp]),
                "position": float(position.loc[timestamp]),
                "strategy_nav": float(nav.loc[timestamp]),
                "trade_marker": marker,
            }
        )
    return rows


def _write_rows_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "execution_filter",
        "higher_filter",
        "gate_signal",
        "trigger_signal",
        "composite_signal",
        "position",
        "strategy_nav",
        "trade_marker",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _as_render_row(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "timestamp": row.get("timestamp"),
        "open": _optional_float(row.get("open")),
        "high": _optional_float(row.get("high")),
        "low": _optional_float(row.get("low")),
        "close": _optional_float(row.get("close")),
        "execution_filter": _optional_float(row.get("execution_filter")),
        "higher_filter": _optional_float(row.get("higher_filter")),
        "trade_marker": row.get("trade_marker"),
    }


def _append_panel_grid(
    lines: list[str],
    left: float,
    top: float,
    width: float,
    height: float,
    *,
    label: str,
) -> None:
    for tick in range(5):
        y = top + height * tick / 4
        lines.append(
            f"<line x1='{left}' y1='{y:.2f}' x2='{left + width}' y2='{y:.2f}' stroke='#e5e7eb' stroke-width='1'/>"
        )
    lines.append(
        f"<rect x='{left}' y='{top}' width='{width}' height='{height}' fill='none' stroke='#111827' stroke-width='1'/>"
    )
    lines.append(
        f"<text x='{left + 8}' y='{top + 20}' font-family='sans-serif' font-size='13' fill='#374151'>{html.escape(label)}</text>"
    )


def _append_price_axis(
    lines: list[str],
    left: float,
    top: float,
    height: float,
    bounds: tuple[float, float],
    price_scale: str,
) -> None:
    y_min, y_max = bounds
    for tick in range(5):
        frac = tick / 4
        scaled_value = y_max - (y_max - y_min) * frac
        value = _unscale_value(scaled_value, price_scale)
        y = top + height * frac
        lines.append(
            f"<text x='{left - 8}' y='{y + 4:.2f}' text-anchor='end' font-family='sans-serif' font-size='12' fill='#374151'>{value:.2f}</text>"
        )


def _append_indicator_axis(
    lines: list[str],
    left: float,
    top: float,
    height: float,
    bounds: tuple[float, float],
) -> None:
    y_min, y_max = bounds
    for tick in range(3):
        frac = tick / 2
        value = y_max - (y_max - y_min) * frac
        y = top + height * frac
        lines.append(
            f"<text x='{left - 8}' y='{y + 4:.2f}' text-anchor='end' font-family='sans-serif' font-size='12' fill='#374151'>{value:.4g}</text>"
        )


def _append_time_axis(
    lines: list[str],
    values: Sequence[Mapping[str, object]],
    *,
    x_at: CoordinateMapper,
    left: float,
    top: float,
    width: float,
    height: float,
    bottom: float,
) -> None:
    tick_count = min(8, len(values))
    indexes = sorted({round(i * (len(values) - 1) / max(tick_count - 1, 1)) for i in range(tick_count)})
    for index in indexes:
        x = x_at(index)
        label = html.escape(str(values[index].get("timestamp", ""))[:16])
        lines.append(
            f"<line x1='{x:.2f}' y1='{top}' x2='{x:.2f}' y2='{height - bottom}' stroke='#f3f4f6' stroke-width='1'/>"
        )
        lines.append(
            f"<text x='{x:.2f}' y='{height - 30}' text-anchor='end' font-family='sans-serif' font-size='12' fill='#374151' transform='rotate(-35 {x:.2f} {height - 30})'>{label}</text>"
        )
    lines.append(
        f"<line x1='{left}' y1='{height - bottom}' x2='{left + width}' y2='{height - bottom}' stroke='#111827'/>"
    )


def _append_zero_line(
    lines: list[str],
    bounds: tuple[float, float],
    left: float,
    top: float,
    width: float,
    height: float,
) -> None:
    y_min, y_max = bounds
    if y_min <= 0.0 <= y_max:
        y = top + (y_max - 0.0) / (y_max - y_min) * height
        lines.append(
            f"<line x1='{left}' y1='{y:.2f}' x2='{left + width}' y2='{y:.2f}' stroke='#9ca3af' stroke-dasharray='4 4'/>"
        )


def _append_legend(
    lines: list[str],
    *,
    width: int,
    execution_period: str,
    higher_period: str | None,
    execution_filter_name: str,
    higher_filter_name: str | None,
) -> None:
    x = width - 425
    higher_period_label = _higher_label(higher_period)
    higher_filter_label = _higher_label(higher_filter_name)
    lines.extend(
        [
            f"<rect x='{x}' y='46' width='380' height='112' fill='white' stroke='#d1d5db'/>",
            f"<polygon points='{x + 18},72 {x + 11},86 {x + 25},86' fill='#2563eb'/><text x='{x + 36}' y='85' font-family='sans-serif' font-size='13'>开仓执行点 / Buy</text>",
            f"<polygon points='{x + 18},115 {x + 11},101 {x + 25},101' fill='#f97316'/><text x='{x + 36}' y='108' font-family='sans-serif' font-size='13'>平仓执行点 / Sell</text>",
            f"<line x1='{x + 12}' y1='130' x2='{x + 30}' y2='130' stroke='#7c3aed' stroke-width='2'/><text x='{x + 36}' y='134' font-family='sans-serif' font-size='13'>本级别 {html.escape(execution_period)}: {html.escape(execution_filter_name)}</text>",
            f"<line x1='{x + 12}' y1='148' x2='{x + 30}' y2='148' stroke='#0f766e' stroke-width='2'/><text x='{x + 36}' y='152' font-family='sans-serif' font-size='13'>上一级 {html.escape(higher_period_label)}: {html.escape(higher_filter_label)}</text>",
        ]
    )


def _higher_label(value: str | None) -> str:
    return value if value else "无（单周期模板）"


def _indicator_points(
    values: Sequence[Mapping[str, object]],
    key: str,
    *,
    x_at: CoordinateMapper,
    y_at: ValueMapper,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for index, row in enumerate(values):
        value = _optional_float(row.get(key))
        if value is not None:
            points.append((x_at(index), y_at(value)))
    return points


def _polyline(points: Sequence[tuple[float, float]], color: str, width: float) -> str:
    if len(points) < 2:
        return ""
    data = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return f"<polyline points='{data}' fill='none' stroke='{color}' stroke-width='{width:.1f}' opacity='0.92'/>"


def _scaled_bounds(values: Sequence[float], *, price_scale: str) -> tuple[float, float]:
    finite = [_scale_value(value, price_scale) for value in values if math.isfinite(value)]
    if not finite:
        return (0.0, 1.0)
    y_min = min(finite)
    y_max = max(finite)
    return _pad_bounds(y_min, y_max)


def _linear_bounds(values: Sequence[float | None]) -> tuple[float, float]:
    finite = [value for value in values if value is not None and math.isfinite(value)]
    if not finite:
        return (-1.0, 1.0)
    return _pad_bounds(min(finite), max(finite))


def _pad_bounds(y_min: float, y_max: float) -> tuple[float, float]:
    if math.isclose(y_min, y_max):
        pad = max(abs(y_min) * 0.01, 0.01)
    else:
        pad = (y_max - y_min) * 0.08
    return y_min - pad, y_max + pad


def _scale_value(value: float, price_scale: str) -> float:
    return math.log(value) if price_scale == "log" else value


def _unscale_value(value: float, price_scale: str) -> float:
    return math.exp(value) if price_scale == "log" else value


def _optional_float(raw: object) -> float | None:
    if isinstance(raw, bool) or raw is None or raw == "":
        return None
    try:
        value = float(str(raw))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _required_float(raw: object) -> float:
    value = _optional_float(raw)
    if value is None:
        raise ValueError("expected a finite numeric render value")
    return value


def _timestamp_iso(raw: object) -> str:
    if raw is None or raw == "":
        return ""
    if isinstance(raw, pd.Timestamp):
        return "" if pd.isna(raw) else raw.isoformat()
    return str(raw)


def _finite_or_blank(raw: object) -> float | str:
    value = _optional_float(raw)
    return "" if value is None else value


def _empty_svg(width: int, height: int, title: str, message: str) -> str:
    return "\n".join(
        [
            "<?xml version='1.0' encoding='UTF-8'?>",
            f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}'>",
            "<rect width='100%' height='100%' fill='white'/>",
            f"<text x='{width / 2:.0f}' y='36' text-anchor='middle' font-family='sans-serif' font-size='22'>{html.escape(title)}</text>",
            f"<text x='{width / 2:.0f}' y='{height / 2:.0f}' text-anchor='middle' font-family='sans-serif' font-size='16' fill='#6b7280'>{html.escape(message)}</text>",
            "</svg>",
        ]
    )
