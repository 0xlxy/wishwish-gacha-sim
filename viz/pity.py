"""Pity diagnostics charts (PRD §4.3.6)."""
from __future__ import annotations

import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from simulator import metrics as m
from simulator.engine import SimResult

from .theme import SEGMENT_COLORS, SEGMENT_ORDER, apply_layout


def pity_trigger_histogram_fig(result: SimResult) -> go.Figure:
    df = m.pity_trigger_histogram(result)
    fig = px.bar(
        df,
        x="pity_triggers",
        y="users",
        color="segment",
        color_discrete_map=SEGMENT_COLORS,
        category_orders={"segment": SEGMENT_ORDER},
        labels={"pity_triggers": "Pity triggers per user", "users": "Users"},
    )
    fig.update_layout(barmode="stack")
    return apply_layout(fig, title="Pity triggers per user")


def pulls_between_pity_fig(result: SimResult) -> go.Figure:
    df = m.pulls_between_pity(result)
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            annotations=[
                dict(
                    text="No users experienced 2+ pity triggers",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                )
            ]
        )
        return apply_layout(fig, title="Pulls between pity events", height=300)
    fig = px.histogram(
        df,
        x="gap",
        nbins=30,
        labels={"gap": "Pulls between successive pity triggers"},
    )
    fig.update_traces(marker_color="#2563EB")
    return apply_layout(fig, title="Pulls between pity events")


def pity_utility_card(result: SimResult) -> str:
    rate = m.pity_utility_rate(result)
    return (
        f"Pity utility rate: **{rate * 100:.1f}%** "
        f"(fraction of pity triggers that delivered a character the user didn't already own)."
    )
