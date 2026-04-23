"""Collection-distribution charts (PRD §4.3.2)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from simulator.engine import SimResult
from simulator import metrics as m

from .theme import SEGMENT_COLORS, SEGMENT_ORDER, apply_layout


def collection_histogram_fig(result: SimResult) -> go.Figure:
    df = m.collection_histogram(result)
    fig = px.bar(
        df,
        x="owned_count",
        y="users",
        color="segment",
        color_discrete_map=SEGMENT_COLORS,
        category_orders={"segment": SEGMENT_ORDER},
        labels={"owned_count": "Unique characters owned", "users": "Users"},
    )
    fig.update_layout(barmode="stack")
    return apply_layout(fig, title="Collection size distribution")


def completion_funnel_fig(result: SimResult) -> go.Figure:
    df = m.completion_funnel(result)
    fig = go.Figure(
        data=go.Bar(
            x=df["k"],
            y=df["pct"] * 100.0,
            marker_color="#2563EB",
            text=[f"{p * 100:.1f}%" for p in df["pct"]],
            textposition="outside",
        )
    )
    fig.update_layout(
        xaxis_title="≥ k characters owned",
        yaxis_title="% of users",
        yaxis_range=[0, 105],
        showlegend=False,
    )
    return apply_layout(fig, title="Completion funnel")


def ownership_heatmap_fig(result: SimResult) -> go.Figure:
    df = m.ownership_heatmap(result)
    pivot = df.pivot(index="character", columns="day", values="pct")
    # Preserve character order as defined in config (series.all_character_names).
    pivot = pivot.reindex(result.character_names)
    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values * 100.0,
            x=pivot.columns,
            y=pivot.index,
            colorscale="Viridis",
            colorbar=dict(title="%"),
            hovertemplate="Day %{x}<br>%{y}<br>%{z:.1f}% owned<extra></extra>",
        )
    )
    fig.update_layout(
        xaxis_title="Day",
        yaxis_title="Character",
        yaxis=dict(autorange="reversed"),
    )
    return apply_layout(fig, title="Per-character ownership over time", height=380)


def duplicates_violin_fig(result: SimResult) -> go.Figure:
    df = m.duplicates_per_character(result)
    if df.empty:
        return apply_layout(go.Figure(), title="Duplicates per character")
    # Only common-tier characters (rare are rare by definition).
    tier_idx = result.meta["char_tier_idx"]
    common_names = [
        n for i, n in enumerate(result.character_names) if tier_idx[i] == 0
    ]
    df = df[df["character"].isin(common_names)]
    fig = go.Figure()
    for name in common_names:
        sub = df[df["character"] == name]
        fig.add_trace(
            go.Violin(
                x=[name] * len(sub),
                y=sub["duplicates"],
                name=name,
                showlegend=False,
                line_color="#2563EB",
                box_visible=True,
                meanline_visible=True,
                points=False,
            )
        )
    fig.update_layout(
        yaxis_title="Duplicates per user",
        xaxis_title="",
    )
    return apply_layout(fig, title="Duplicate distribution (commons)", height=380)
