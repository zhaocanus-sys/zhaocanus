# -*- coding: utf-8 -*-
"""迷你趋势曲线生成器 — 纯SVG内联，零依赖，适用于所有报告的KPI卡片"""


def sparkline_svg(values, width=60, height=22, color="#3b82f6", fill=True):
    """生成内联SVG迷你趋势线

    Args:
        values: 数值列表（按时间正序，最后一个是今日）
        width/height: SVG尺寸
        color: 线条颜色
        fill: 是否填充曲线下方区域
    Returns:
        HTML字符串（SVG标签），无数据时返回空字符串
    """
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return ""
    mn, mx = min(vals), max(vals)
    rng = mx - mn or 1
    n = len(vals)
    pad = 1
    pts = []
    for i, v in enumerate(vals):
        x = pad + i / (n - 1) * (width - 2 * pad)
        y = pad + (1 - (v - mn) / rng) * (height - 2 * pad)
        pts.append((x, y))

    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    last_x, last_y = pts[-1]
    dot_r = 2

    last_val = vals[-1]
    prev_val = vals[-2] if len(vals) >= 2 else last_val
    trend_up = last_val >= prev_val
    dot_color = "#16a34a" if trend_up else "#dc2626"

    svg = f'<svg width="{width}" height="{height}" style="display:block;margin-top:3px">'
    if fill:
        fill_pts = polyline + f" {pts[-1][0]:.1f},{height} {pts[0][0]:.1f},{height}"
        svg += f'<polygon points="{fill_pts}" fill="{color}" opacity="0.1"/>'
    svg += f'<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="1.5" '
    svg += f'stroke-linecap="round" stroke-linejoin="round"/>'
    svg += f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="{dot_r}" fill="{dot_color}"/>'
    svg += '</svg>'
    return svg


def extract_trend_values(history_episodes, key, today_val=None, prev_val=None):
    """从情景记忆历史数据中提取某指标的趋势值列表

    Args:
        history_episodes: ReportMemory.recall() 返回的列表 [{date, metrics}, ...]
        key: 指标键名
        today_val: 今日值（追加到末尾）
        prev_val: 昨日值（当记忆为空时作为保底基线，确保至少2个点）
    Returns:
        数值列表（时间正序）
    """
    vals = []
    for ep in reversed(history_episodes):
        v = ep.get("metrics", {}).get(key, 0)
        if v is None:
            v = 0
        vals.append(float(v))
    if not vals and prev_val is not None:
        vals.append(float(prev_val))
    if today_val is not None:
        vals.append(float(today_val))
    return vals
