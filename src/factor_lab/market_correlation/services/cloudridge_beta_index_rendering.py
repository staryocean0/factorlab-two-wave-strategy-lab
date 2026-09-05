# pyright: reportAny=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportArgumentType=false, reportImplicitStringConcatenation=false
# pyright: reportUnusedCallResult=false
"""Static render artifacts for the CloudRidge Beta Index.

The API/UI already exposes tabular data and live Vega-Lite charts.  This module
is intentionally dependency-free so the CLI and service render paths can always
produce a shareable chart artifact without adding plotting packages.
"""

from __future__ import annotations

import csv
import html
import math
from collections.abc import Callable, Mapping, Sequence
from datetime import date
from pathlib import Path


def write_cloudridge_beta_index_render_artifacts(
    *,
    index_id: str,
    level_rows: Sequence[Mapping[str, object]],
    constituent_rows: Sequence[Mapping[str, object]],
    output_prefix: str | Path,
    chart_png: str | None = None,
    price_scale: str = "linear",
) -> dict[str, object]:
    """Write CSV, HTML, and K-line SVG artifacts for a CloudRidge index."""

    resolved_price_scale = normalize_price_scale(price_scale)
    rows = [dict(row) for row in level_rows]
    constituents = [dict(row) for row in constituent_rows]
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    levels_csv = prefix.with_suffix(".levels.csv")
    constituents_csv = prefix.with_suffix(".constituents.csv")
    report_html = prefix.with_suffix(".html")
    kline_svg = prefix.with_suffix(".kline.svg")
    weekly_rows = weekly_ohlc_rows(rows)

    write_rows_csv(levels_csv, rows)
    write_rows_csv(constituents_csv, constituents)
    write_kline_svg(
        kline_svg,
        weekly_rows,
        title=f"CloudRidge Beta Index {index_id}",
        price_scale=resolved_price_scale,
    )
    write_report_html(
        report_html,
        index_id=index_id,
        level_rows=rows,
        kline_svg=kline_svg,
        chart_png=Path(chart_png) if chart_png else None,
        latest_level=rows[-1].get("index_level") if rows else "",
        weekly_kline_count=len(weekly_rows),
        price_scale=resolved_price_scale,
    )
    return {
        "index_id": index_id,
        "levels_csv": str(levels_csv),
        "constituents_csv": str(constituents_csv),
        "report_html": str(report_html),
        "chart_png": chart_png,
        "kline_svg": str(kline_svg),
        "level_row_count": len(rows),
        "constituent_row_count": len(constituents),
        "weekly_kline_count": len(weekly_rows),
        "latest_level": rows[-1].get("index_level") if rows else None,
        "price_scale": resolved_price_scale,
    }


def normalize_price_scale(price_scale: str) -> str:
    value = str(price_scale or "linear").strip().lower()
    if value not in {"linear", "log"}:
        raise ValueError("price_scale must be 'linear' or 'log'")
    return value


def write_rows_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(str(key))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def weekly_ohlc_rows(
    level_rows: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Collapse level rows to weekly OHLC rows.

    If the persisted index only has one point per rebalance, the candle still
    represents that week.  If it has daily rows, each candle spans all rows in
    the ISO week.
    """

    points: list[tuple[date, float]] = []
    for row in level_rows:
        row_date = _parse_date(row.get("date") or row.get("effective_date"))
        level = _finite_float(row.get("index_level"))
        if row_date is not None and level is not None:
            points.append((row_date, level))
    points.sort(key=lambda item: item[0])
    grouped: dict[tuple[int, int], list[tuple[date, float]]] = {}
    for row_date, level in points:
        iso = row_date.isocalendar()
        grouped.setdefault((iso.year, iso.week), []).append((row_date, level))

    candles: list[dict[str, object]] = []
    for values in grouped.values():
        values.sort(key=lambda item: item[0])
        levels = [level for _row_date, level in values]
        candles.append(
            {
                "date": values[-1][0].isoformat(),
                "open": levels[0],
                "high": max(levels),
                "low": min(levels),
                "close": levels[-1],
            }
        )
    return candles


def write_report_html(
    path: Path,
    *,
    index_id: str,
    level_rows: Sequence[Mapping[str, object]],
    kline_svg: Path,
    chart_png: Path | None,
    latest_level: object,
    weekly_kline_count: int,
    price_scale: str,
) -> None:
    chart_path = chart_png or kline_svg
    chart_name = html.escape(chart_path.name)
    chart_kind = "PNG" if chart_png else "SVG"
    escaped_index = html.escape(index_id)
    table_rows = "\n".join(
        "<tr>"
        + "".join(
            f"<td>{html.escape(str(row.get(column, '')))}</td>"
            for column in ("date", "daily_return", "index_level", "coverage_ratio")
        )
        + "</tr>"
        for row in level_rows
    )
    path.write_text(
        "\n".join(
            [
                "<!doctype html><html><head><meta charset='utf-8'>",
                f"<title>CloudRidge Beta Index {escaped_index}</title>",
                "<style>body{font-family:sans-serif;margin:24px;}img{max-width:100%;}"
                "table{border-collapse:collapse;}td,th{padding:4px 8px;"
                "border:1px solid #ddd;}"
                "</style>",
                "</head><body>",
                f"<h1>CloudRidge Beta Index {escaped_index}</h1>",
                (
                    "<p><b>Latest level:</b> "
                    f"{html.escape(str(latest_level))} &nbsp; "
                    f"<b>Weekly candles:</b> {weekly_kline_count} &nbsp; "
                    f"<b>Price scale:</b> {html.escape(price_scale)}</p>"
                ),
                (
                    f"<p><b>Chart:</b> {chart_kind} &nbsp; "
                    f"<a href='{chart_name}'>{chart_name}</a></p>"
                ),
                f"<p><img src='{chart_name}' alt='CloudRidge weekly K-line'></p>",
                "<table><thead><tr><th>Date</th><th>Return</th>",
                "<th>Level</th><th>Coverage</th></tr></thead><tbody>",
                table_rows,
                "</tbody></table>",
                "</body></html>",
            ]
        ),
        encoding="utf-8",
    )


def write_kline_svg(
    path: Path,
    rows: Sequence[Mapping[str, object]],
    *,
    title: str,
    price_scale: str = "linear",
) -> None:
    resolved_price_scale = normalize_price_scale(price_scale)
    width = 1400
    height = 620
    left = 76
    right = 28
    top = 58
    bottom = 92
    plot_width = width - left - right
    plot_height = height - top - bottom
    values: list[dict[str, object]] = []
    for row in rows:
        open_ = _finite_float(row.get("open"))
        high = _finite_float(row.get("high"))
        low = _finite_float(row.get("low"))
        close = _finite_float(row.get("close"))
        label = str(row.get("date") or "")
        if None not in (open_, high, low, close):
            values.append(
                {
                    "date": label,
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": close,
                }
            )
    if not values:
        path.write_text(
            _empty_svg(width, height, title, "No level rows to chart"),
            encoding="utf-8",
        )
        return

    lows = [float(row["low"]) for row in values]
    highs = [float(row["high"]) for row in values]
    if resolved_price_scale == "log" and min(lows) <= 0.0:
        raise ValueError("log price scale requires positive index levels")
    scaled_lows = [_scale_level(value, resolved_price_scale) for value in lows]
    scaled_highs = [_scale_level(value, resolved_price_scale) for value in highs]
    min_scaled_level = min(scaled_lows)
    max_scaled_level = max(scaled_highs)
    if math.isclose(min_scaled_level, max_scaled_level):
        pad = max(abs(min_scaled_level) * 0.01, 0.01)
    else:
        pad = (max_scaled_level - min_scaled_level) * 0.08
    y_min = min_scaled_level - pad
    y_max = max_scaled_level + pad
    count = len(values)
    step = plot_width / max(count - 1, 1)
    body_width = min(9.0, max(2.0, plot_width / max(count, 1) * 0.55))

    def x_at(index: int) -> float:
        return left + step * index if count > 1 else left + plot_width / 2

    def y_at(level: float) -> float:
        scaled_level = _scale_level(level, resolved_price_scale)
        return top + (y_max - scaled_level) / (y_max - y_min) * plot_height

    def polyline(points: list[tuple[float, float]], color: str) -> str:
        if len(points) < 2:
            return ""
        data = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
        return (
            f"<polyline points='{data}' fill='none' stroke='{color}' "
            "stroke-width='2.2' opacity='0.9'/>"
        )

    lines: list[str] = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        (
            f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' "
            f"height='{height}' "
            f"viewBox='0 0 {width} {height}'>"
        ),
        "<rect width='100%' height='100%' fill='white'/>",
        (
            f"<text x='{width / 2:.0f}' y='30' text-anchor='middle' "
            "font-family='sans-serif' font-size='22'>"
            f"{html.escape(title)} — weekly K-line ({resolved_price_scale})</text>"
        ),
    ]

    for tick in range(6):
        frac = tick / 5
        y = top + plot_height * frac
        level = _unscale_level(y_max - (y_max - y_min) * frac, resolved_price_scale)
        lines.append(
            f"<line x1='{left}' y1='{y:.2f}' x2='{left + plot_width}' y2='{y:.2f}' "
            "stroke='#e5e7eb' stroke-width='1'/>"
        )
        lines.append(
            f"<text x='{left - 8}' y='{y + 4:.2f}' text-anchor='end' "
            "font-family='sans-serif' font-size='12' fill='#374151'>"
            f"{level:.0f}</text>"
        )

    tick_count = min(8, count)
    tick_indexes = sorted(
        {round(i * (count - 1) / max(tick_count - 1, 1)) for i in range(tick_count)}
    )
    for index in tick_indexes:
        x = x_at(index)
        label = html.escape(str(values[index]["date"]))
        lines.append(
            f"<line x1='{x:.2f}' y1='{top}' x2='{x:.2f}' y2='{top + plot_height}' "
            "stroke='#f3f4f6' stroke-width='1'/>"
        )
        lines.append(
            f"<text x='{x:.2f}' y='{height - 28}' text-anchor='end' "
            "font-family='sans-serif' font-size='12' fill='#374151' "
            f"transform='rotate(-35 {x:.2f} {height - 28})'>{label}</text>"
        )

    lines.append(
        f"<rect x='{left}' y='{top}' width='{plot_width}' height='{plot_height}' "
        "fill='none' stroke='#111827' stroke-width='1'/>"
    )

    closes = [float(row["close"]) for row in values]
    ma5 = _moving_average_points(closes, window=5, x_at=x_at, y_at=y_at)
    ma20 = _moving_average_points(closes, window=20, x_at=x_at, y_at=y_at)

    for index, row in enumerate(values):
        x = x_at(index)
        open_ = float(row["open"])
        high = float(row["high"])
        low = float(row["low"])
        close = float(row["close"])
        color = "#dc2626" if close >= open_ else "#16a34a"
        y_open = y_at(open_)
        y_close = y_at(close)
        body_top = min(y_open, y_close)
        body_height = max(abs(y_close - y_open), 1.2)
        lines.append(
            f"<line x1='{x:.2f}' y1='{y_at(high):.2f}' "
            f"x2='{x:.2f}' y2='{y_at(low):.2f}' "
            f"stroke='{color}' stroke-width='1.4'/>"
        )
        lines.append(
            f"<rect x='{x - body_width / 2:.2f}' y='{body_top:.2f}' "
            f"width='{body_width:.2f}' height='{body_height:.2f}' fill='{color}' "
            f"stroke='{color}' opacity='0.88'/>"
        )

    lines.append(polyline(ma5, "#2563eb"))
    lines.append(polyline(ma20, "#f97316"))
    lines.append("<g font-family='sans-serif' font-size='13' fill='#111827'>")
    lines.append(
        f"<rect x='{width - 210}' y='46' width='170' height='58' "
        "fill='white' stroke='#d1d5db'/>"
    )
    lines.append(
        f"<line x1='{width - 196}' y1='65' x2='{width - 162}' y2='65' "
        "stroke='#2563eb' stroke-width='2.2'/>"
        f"<text x='{width - 152}' y='69'>MA5 close</text>"
    )
    lines.append(
        f"<line x1='{width - 196}' y1='88' x2='{width - 162}' y2='88' "
        "stroke='#f97316' stroke-width='2.2'/>"
        f"<text x='{width - 152}' y='92'>MA20 close</text>"
    )
    lines.append("</g>")
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def render_cloudridge_beta_index_chart_png(
    *,
    index_id: str,
    level_rows: Sequence[Mapping[str, object]],
    output_path: str | Path,
    price_scale: str = "linear",
) -> str | None:
    """Render a PNG K-line chart when matplotlib is available.

    SVG is the dependency-free guaranteed artifact. PNG is an optional
    convenience output for local review in environments that already have
    matplotlib installed.
    """

    resolved_price_scale = normalize_price_scale(price_scale)
    candles = weekly_ohlc_rows(level_rows)
    if not candles:
        return None
    if resolved_price_scale == "log" and any(
        float(row["low"]) <= 0.0 for row in candles
    ):
        raise ValueError("log price scale requires positive index levels")
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
        from matplotlib.patches import Rectangle
    except Exception:
        return None

    chart_path = Path(output_path)
    chart_path.parent.mkdir(parents=True, exist_ok=True)
    fig, price_ax = plt.subplots(figsize=(16, 7))
    x_values = list(range(len(candles)))
    body_width = 0.62
    for index, row in enumerate(candles):
        open_ = float(row["open"])
        high = float(row["high"])
        low = float(row["low"])
        close = float(row["close"])
        color = "#d62728" if close >= open_ else "#2ca02c"
        price_ax.vlines(index, low, high, color=color, linewidth=1.0)
        lower = min(open_, close)
        height = abs(close - open_)
        if height <= max(abs(close), 1.0) * 1e-6:
            price_ax.hlines(
                close,
                index - body_width / 2,
                index + body_width / 2,
                color=color,
                linewidth=1.2,
            )
        else:
            price_ax.add_patch(
                Rectangle(
                    (index - body_width / 2, lower),
                    body_width,
                    height,
                    facecolor=color,
                    edgecolor=color,
                    alpha=0.82,
                )
            )
    close_values = [float(row["close"]) for row in candles]
    if len(close_values) >= 5:
        ma5 = [
            sum(close_values[max(0, index - 4) : index + 1])
            / len(close_values[max(0, index - 4) : index + 1])
            for index in range(len(close_values))
        ]
        price_ax.plot(x_values, ma5, color="#1f77b4", lw=1.2, label="MA5")
    if len(close_values) >= 20:
        ma20 = [
            sum(close_values[max(0, index - 19) : index + 1])
            / len(close_values[max(0, index - 19) : index + 1])
            for index in range(len(close_values))
        ]
        price_ax.plot(x_values, ma20, color="#ff7f0e", lw=1.2, label="MA20")
    tick_step = max(1, len(candles) // 10)
    price_ax.set_xticks(x_values[::tick_step])
    price_ax.set_xticklabels(
        [str(row["date"]) for row in candles[::tick_step]],
        rotation=45,
        ha="right",
    )
    price_ax.set_title(f"CloudRidge Beta Index K-line — {index_id}")
    price_ax.set_ylabel("Index level")
    if resolved_price_scale == "log":
        price_ax.set_yscale("log")
    price_ax.grid(True, alpha=0.25)
    handles, _labels = price_ax.get_legend_handles_labels()
    if handles:
        price_ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(chart_path, dpi=150)
    plt.close(fig)
    return str(chart_path)


def _scale_level(value: float, price_scale: str) -> float:
    return math.log(value) if price_scale == "log" else value


def _unscale_level(value: float, price_scale: str) -> float:
    return math.exp(value) if price_scale == "log" else value


def _moving_average_points(
    values: Sequence[float],
    *,
    window: int,
    x_at: Callable[[int], float],
    y_at: Callable[[float], float],
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for index in range(window - 1, len(values)):
        average = sum(values[index - window + 1 : index + 1]) / window
        points.append((x_at(index), y_at(average)))
    return points


def _parse_date(raw: object) -> date | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _finite_float(raw: object) -> float | None:
    if isinstance(raw, bool):
        return None
    try:
        value = float(str(raw))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _empty_svg(width: int, height: int, title: str, message: str) -> str:
    return "\n".join(
        [
            "<?xml version='1.0' encoding='UTF-8'?>",
            (
                f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' "
                f"height='{height}'>"
            ),
            "<rect width='100%' height='100%' fill='white'/>",
            (
                f"<text x='{width / 2:.0f}' y='36' text-anchor='middle' "
                "font-family='sans-serif' font-size='22'>"
                f"{html.escape(title)}</text>"
            ),
            (
                f"<text x='{width / 2:.0f}' y='{height / 2:.0f}' text-anchor='middle' "
                "font-family='sans-serif' font-size='16' fill='#6b7280'>"
                f"{html.escape(message)}</text>"
            ),
            "</svg>",
        ]
    )
