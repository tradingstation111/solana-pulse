"""Inline SVG chart primitives.

The dashboard must be a single self-contained file that opens from disk with no
network access, so no charting library is used - every chart here is SVG text
generated from the data.  All functions return an SVG fragment string and are
pure, which makes them straightforward to unit-test.
"""

from __future__ import annotations

import html
import math
from typing import Sequence

ACCENT = "#14f195"
ACCENT_ALT = "#9945ff"
MUTED = "#5b6478"

PALETTE = (
    "#14f195", "#9945ff", "#38bdf8", "#f59e0b", "#f472b6",
    "#4ade80", "#818cf8", "#fb7185", "#2dd4bf", "#facc15",
)


def _scale(values: Sequence[float], size: float, pad: float, invert: bool = False
           ) -> tuple[list[float], float, float]:
    """Map ``values`` onto ``[pad, size - pad]``; returns points and the range."""
    low, high = min(values), max(values)
    if math.isclose(low, high):
        low, high = low - 1, high + 1
    span = high - low
    usable = size - 2 * pad
    scaled = [pad + (v - low) / span * usable for v in values]
    if invert:
        scaled = [size - s for s in scaled]
    return scaled, low, high


def sparkline(values: Sequence[float], *, width: int = 160, height: int = 40,
              color: str = ACCENT, fill: bool = True) -> str:
    """Small trend line with an optional gradient fill and an end-point dot."""
    values = [float(v) for v in values if isinstance(v, (int, float))]
    if len(values) < 2:
        return (f'<svg class="spark" viewBox="0 0 {width} {height}" preserveAspectRatio="none" '
                f'role="img" aria-label="not enough history"><text x="4" y="{height // 2 + 4}" '
                f'fill="{MUTED}" font-size="10">collecting history…</text></svg>')
    ys, low, high = _scale(values, height, 4, invert=True)
    step = width / (len(values) - 1)
    pts = " ".join(f"{i * step:.2f},{y:.2f}" for i, y in enumerate(ys))
    uid = f"g{abs(hash((tuple(values[:6]), color, width))) % 10**8}"
    area = ""
    if fill:
        area = (f'<defs><linearGradient id="{uid}" x1="0" y1="0" x2="0" y2="1">'
                f'<stop offset="0%" stop-color="{color}" stop-opacity="0.35"/>'
                f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>'
                f'<polygon points="0,{height} {pts} {width},{height}" fill="url(#{uid})"/>')
    last_x, last_y = (len(values) - 1) * step, ys[-1]
    return (
        f'<svg class="spark" viewBox="0 0 {width} {height}" preserveAspectRatio="none" role="img" '
        f'aria-label="trend from {low:.4g} to {high:.4g}">{area}'
        f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.6" '
        f'stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>'
        f'<circle cx="{last_x:.2f}" cy="{last_y:.2f}" r="2.2" fill="{color}"/></svg>'
    )


def area_chart(points: Sequence[Sequence[float]], *, width: int = 640, height: int = 190,
               color: str = ACCENT, value_format: str = "num", label: str = "",
               x_labels: tuple[str, str] | None = None) -> str:
    """Time-series area chart with gridlines and axis annotations.

    ``points`` is a sequence of ``[x, value]`` pairs.  By default ``x`` is read
    as unix seconds and the axis is dated; pass ``x_labels`` to caption the
    first and last points directly, which is what index-based series use.
    """
    series = [(float(t), float(v)) for t, v in points if v is not None]
    if len(series) < 2:
        return f'<div class="chart-empty">No history available for {html.escape(label)}.</div>'
    values = [v for _, v in series]
    pad_l, pad_r, pad_t, pad_b = 52, 10, 14, 22
    plot_w, plot_h = width - pad_l - pad_r, height - pad_t - pad_b
    low, high = min(values), max(values)
    if math.isclose(low, high):
        low, high = low * 0.99 or -1, high * 1.01 or 1
    span = high - low

    def x_of(i: int) -> float:
        return pad_l + i * plot_w / (len(series) - 1)

    def y_of(v: float) -> float:
        return pad_t + plot_h - (v - low) / span * plot_h

    pts = " ".join(f"{x_of(i):.1f},{y_of(v):.1f}" for i, (_, v) in enumerate(series))
    uid = f"a{abs(hash((label, color, len(series)))) % 10**8}"
    grid, ticks = [], []
    for frac in (0, 0.25, 0.5, 0.75, 1):
        value = low + span * (1 - frac)
        y = pad_t + plot_h * frac
        grid.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width - pad_r}" y2="{y:.1f}" '
                    f'stroke="#1c2130" stroke-width="1"/>')
        ticks.append(f'<text x="{pad_l - 6}" y="{y + 3.5:.1f}" text-anchor="end" fill="{MUTED}" '
                     f'font-size="9.5">{_fmt_axis(value, value_format)}</text>')
    if x_labels:
        first_label, last_label = x_labels
    else:
        first_label, last_label = _fmt_date(series[0][0]), _fmt_date(series[-1][0])
    first_label, last_label = html.escape(first_label), html.escape(last_label)
    return (
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{html.escape(label)} over time">'
        f'<defs><linearGradient id="{uid}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity="0.30"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0.02"/></linearGradient></defs>'
        + "".join(grid) +
        f'<polygon points="{pad_l},{pad_t + plot_h} {pts} {width - pad_r},{pad_t + plot_h}" '
        f'fill="url(#{uid})"/>'
        f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.8" '
        f'stroke-linejoin="round"/>'
        f'<circle cx="{x_of(len(series) - 1):.1f}" cy="{y_of(values[-1]):.1f}" r="3" fill="{color}"/>'
        + "".join(ticks) +
        f'<text x="{pad_l}" y="{height - 6}" fill="{MUTED}" font-size="9.5">{first_label}</text>'
        f'<text x="{width - pad_r}" y="{height - 6}" text-anchor="end" fill="{MUTED}" '
        f'font-size="9.5">{last_label}</text></svg>'
    )


def bar_chart(rows: Sequence[tuple[str, float]], *, width: int = 320, bar_height: int = 22,
              color: str = ACCENT_ALT, value_format: str = "num") -> str:
    """Horizontal bars with labels inside the row - compact and readable."""
    rows = [(str(k), float(v)) for k, v in rows if isinstance(v, (int, float))]
    if not rows:
        return '<div class="chart-empty">No data.</div>'
    top = max(v for _, v in rows) or 1
    height = len(rows) * (bar_height + 6) + 6
    out = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="bar chart">']
    for index, (label, value) in enumerate(rows):
        y = 6 + index * (bar_height + 6)
        bar_w = max(2.0, value / top * (width - 4))
        shade = PALETTE[index % len(PALETTE)] if color == "palette" else color
        out.append(
            f'<rect x="0" y="{y}" width="{bar_w:.1f}" height="{bar_height}" rx="4" '
            f'fill="{shade}" fill-opacity="0.22" stroke="{shade}" stroke-opacity="0.5"/>'
            f'<text x="8" y="{y + bar_height / 2 + 3.6:.1f}" fill="#e6e9f2" font-size="11">'
            f'{html.escape(label[:26])}</text>'
            f'<text x="{width - 4}" y="{y + bar_height / 2 + 3.6:.1f}" text-anchor="end" '
            f'fill="{shade}" font-size="11" font-weight="600">{_fmt_axis(value, value_format)}</text>'
        )
    out.append("</svg>")
    return "".join(out)


def donut(rows: Sequence[tuple[str, float]], *, size: int = 170, thickness: int = 22,
          centre_label: str = "", centre_value: str = "") -> str:
    """Donut chart for share-of-total breakdowns, with an inline legend."""
    rows = [(str(k), float(v)) for k, v in rows if isinstance(v, (int, float)) and v > 0]
    if not rows:
        return '<div class="chart-empty">No data.</div>'
    total = sum(v for _, v in rows) or 1
    radius = size / 2 - thickness / 2
    centre = size / 2
    circumference = 2 * math.pi * radius
    offset = 0.0
    segments = []
    for index, (_, value) in enumerate(rows):
        length = value / total * circumference
        segments.append(
            f'<circle cx="{centre}" cy="{centre}" r="{radius:.2f}" fill="none" '
            f'stroke="{PALETTE[index % len(PALETTE)]}" stroke-width="{thickness}" '
            f'stroke-dasharray="{length:.2f} {circumference - length:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {centre} {centre})"/>'
        )
        offset += length
    legend = "".join(
        f'<li><span class="dot" style="background:{PALETTE[i % len(PALETTE)]}"></span>'
        f'<span class="k">{html.escape(k[:22])}</span>'
        f'<span class="v">{v / total * 100:.1f}%</span></li>'
        for i, (k, v) in enumerate(rows[:8])
    )
    return (
        f'<div class="donut-wrap"><svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" '
        f'role="img" aria-label="share breakdown">{"".join(segments)}'
        f'<text x="{centre}" y="{centre - 2}" text-anchor="middle" fill="#e6e9f2" font-size="17" '
        f'font-weight="600">{html.escape(centre_value)}</text>'
        f'<text x="{centre}" y="{centre + 14}" text-anchor="middle" fill="{MUTED}" font-size="9.5">'
        f'{html.escape(centre_label)}</text></svg>'
        f'<ul class="legend">{legend}</ul></div>'
    )


def gauge(percent: float | None, *, label: str = "", width: int = 260) -> str:
    """Horizontal progress bar used for epoch progress and similar ratios."""
    if not isinstance(percent, (int, float)):
        return '<div class="chart-empty">No data.</div>'
    value = max(0.0, min(100.0, float(percent)))
    return (
        f'<div class="gauge" role="progressbar" aria-valuenow="{value:.1f}" aria-valuemin="0" '
        f'aria-valuemax="100" aria-label="{html.escape(label)}">'
        f'<div class="gauge-fill" style="width:{value:.2f}%"></div>'
        f'<span class="gauge-text">{value:.1f}%</span></div>'
    )


def _fmt_axis(value: float, kind: str) -> str:
    """Compact axis labels: 1.2B, 3.4M, 56K, 78.9."""
    if kind == "usd":
        prefix = "$"
    else:
        prefix = ""
    magnitude = abs(value)
    for divisor, unit in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if magnitude >= divisor:
            return f"{prefix}{value / divisor:.1f}{unit}"
    if magnitude < 1:
        return f"{prefix}{value:.3g}"
    return f"{prefix}{value:,.0f}" if magnitude >= 100 else f"{prefix}{value:,.2f}"


def _fmt_date(unix_seconds: float) -> str:
    """Short YYYY-MM-DD label for a chart axis."""
    from datetime import datetime, timezone
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc).strftime("%Y-%m-%d")
