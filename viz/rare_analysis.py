"""Rare deep-dive charts (PRD §4.3.3)."""
from __future__ import annotations

import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from simulator.engine import SimResult
from simulator import metrics as m

from .theme import SEGMENT_COLORS, SEGMENT_ORDER, apply_layout


def _add_percentile_markers(fig: go.Figure, values: np.ndarray, label: str, y_max: float) -> None:
    if values.size == 0:
        return
    vals_sorted = np.sort(values)
    for pct, color in ((50, "#10B981"), (90, "#F59E0B"), (99, "#EF4444")):
        idx = int(np.ceil(pct / 100.0 * len(vals_sorted))) - 1
        idx = max(0, min(idx, len(vals_sorted) - 1))
        x = float(vals_sorted[idx])
        fig.add_vline(
            x=x,
            line_dash="dash",
            line_color=color,
            annotation_text=f"P{pct} {label} {x:.0f}",
            annotation_position="top",
        )


def pulls_to_first_rare_cdf_fig(result: SimResult) -> go.Figure:
    df = m.pulls_to_first_rare_cdf(result)
    fig = px.line(
        df,
        x="x",
        y="cdf",
        color="segment",
        color_discrete_map=SEGMENT_COLORS,
        category_orders={"segment": ["All"] + SEGMENT_ORDER},
        labels={"x": "Pulls (1-indexed)", "cdf": "Cumulative fraction"},
    )
    fig.update_traces(mode="lines")
    fig.update_yaxes(tickformat=".0%", range=[0, 1.05])

    overall = result.users["first_rare_pull"].to_numpy() + 1
    overall = overall[overall > 0]
    _add_percentile_markers(fig, overall, "pulls", y_max=1.0)

    return apply_layout(fig, title="Pulls to first Rare — CDF (by segment)", height=380)


def days_to_first_rare_cdf_fig(result: SimResult) -> go.Figure:
    df = m.days_to_first_rare_cdf(result)
    fig = px.line(
        df,
        x="day",
        y="cdf",
        color="segment",
        color_discrete_map=SEGMENT_COLORS,
        category_orders={"segment": ["All"] + SEGMENT_ORDER},
        labels={"day": "Day (1-indexed)", "cdf": "Cumulative fraction"},
    )
    fig.update_yaxes(tickformat=".0%", range=[0, 1.05])
    return apply_layout(fig, title="Days to first Rare — CDF (by segment)", height=380)


def rare_ownership_by_segment_fig(result: SimResult) -> go.Figure:
    df = m.rare_ownership_by_segment(result)
    df = df.set_index("segment").reindex(SEGMENT_ORDER).reset_index()
    fig = go.Figure(
        data=go.Bar(
            x=df["segment"],
            y=df["pct_with_rare"] * 100.0,
            marker_color=[SEGMENT_COLORS.get(s, "#374151") for s in df["segment"]],
            text=[f"{p * 100:.1f}%" for p in df["pct_with_rare"]],
            textposition="outside",
        )
    )
    fig.update_layout(
        yaxis_title="% with Rare",
        yaxis_range=[0, 110],
        showlegend=False,
    )
    return apply_layout(fig, title="Rare ownership by segment")


def rare_source_fig(result: SimResult) -> go.Figure:
    df = m.rare_source_breakdown(result)
    fig = go.Figure(
        data=go.Pie(
            labels=df["source"],
            values=df["users"],
            marker_colors=["#F59E0B", "#10B981"],
            textinfo="label+percent",
            hole=0.5,
        )
    )
    return apply_layout(fig, title="First Rare: pity vs natural source")
