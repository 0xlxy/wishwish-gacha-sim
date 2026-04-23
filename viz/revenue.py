"""Spend & revenue analytics charts (PRD §4.3.4)."""
from __future__ import annotations

import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from simulator.engine import SimResult
from simulator import metrics as m

from .theme import SEGMENT_COLORS, SEGMENT_ORDER, apply_layout


def spend_distribution_fig(result: SimResult) -> go.Figure:
    u = result.users.copy()
    # Log scale: replace 0 with a tiny value so it shows in a "0" bin at far left.
    u["spend_usd_plot"] = u["spend_usd"].replace(0, 0.01)
    fig = px.histogram(
        u,
        x="spend_usd_plot",
        color="segment",
        color_discrete_map=SEGMENT_COLORS,
        category_orders={"segment": SEGMENT_ORDER},
        log_x=True,
        nbins=50,
        labels={"spend_usd_plot": "Total spend (USD, log scale)"},
    )
    fig.update_layout(barmode="stack")
    return apply_layout(fig, title="Spend distribution (log scale)", height=360)


def lorenz_fig(result: SimResult) -> go.Figure:
    df, gini = m.revenue_lorenz(result)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["x"],
            y=df["y"],
            mode="lines",
            name="Lorenz",
            line=dict(color="#2563EB", width=3),
            fill="tozeroy",
            fillcolor="rgba(37,99,235,0.15)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[0, 1],
            y=[0, 1],
            mode="lines",
            name="Equality",
            line=dict(color="#9CA3AF", dash="dash"),
        )
    )
    fig.update_layout(
        xaxis_title="Cumulative % of users",
        yaxis_title="Cumulative % of revenue",
        xaxis_tickformat=".0%",
        yaxis_tickformat=".0%",
    )
    return apply_layout(fig, title=f"Revenue Lorenz curve (Gini = {gini:.3f})", height=380)


def cumulative_revenue_fig(result: SimResult) -> go.Figure:
    df = m.cumulative_revenue_by_day(result)
    fig = px.area(
        df,
        x="day",
        y="cum_usd",
        color="segment",
        color_discrete_map=SEGMENT_COLORS,
        category_orders={"segment": SEGMENT_ORDER},
        labels={"day": "Day", "cum_usd": "Cumulative revenue (USD)"},
    )
    return apply_layout(fig, title="Cumulative revenue over time (stacked by segment)", height=360)


def revenue_share_pie_fig(result: SimResult) -> go.Figure:
    df = m.revenue_by_segment(result)
    df = df.set_index("segment").reindex(SEGMENT_ORDER).reset_index()
    fig = go.Figure(
        data=go.Pie(
            labels=df["segment"],
            values=df["revenue_usd"],
            marker_colors=[SEGMENT_COLORS.get(s, "#374151") for s in df["segment"]],
            textinfo="label+percent",
            hole=0.4,
        )
    )
    return apply_layout(fig, title="Revenue share by segment")
