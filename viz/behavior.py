"""The two distributions the user actually cares about:
holdings-per-user and a chosen behavior metric (pulls, spend, days-to-rare).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from simulator.engine import SimResult

from .theme import SEGMENT_COLORS, SEGMENT_ORDER, apply_layout


# Supported behavior metrics.
BEHAVIOR_METRICS: dict[str, dict] = {
    "total_pulls": {"label": "Total pulls / user", "nbins": 40, "log_x": False},
    "paid_pulls": {"label": "Paid pulls / user", "nbins": 40, "log_x": False},
    "spend_usd": {"label": "Spend / user (USD, log scale)", "nbins": 40, "log_x": True},
    "first_rare_day": {"label": "Day of first Rare", "nbins": 31, "log_x": False},
    "days_to_complete": {"label": "Day of completion", "nbins": 31, "log_x": False},
    "pity_triggers": {"label": "Pity triggers / user", "nbins": 30, "log_x": False},
}


def holdings_fig(result: SimResult) -> go.Figure:
    """End-state holdings distribution, stacked by segment."""
    u = result.users
    num_chars = result.num_chars
    counts = (
        u.groupby(["segment", "owned_count"])
        .size()
        .rename("users")
        .reset_index()
    )
    full = pd.MultiIndex.from_product(
        [result.segment_names, range(num_chars + 1)],
        names=["segment", "owned_count"],
    ).to_frame(index=False)
    df = full.merge(counts, on=["segment", "owned_count"], how="left").fillna({"users": 0})
    df["users"] = df["users"].astype(int)

    fig = px.bar(
        df,
        x="owned_count",
        y="users",
        color="segment",
        color_discrete_map=SEGMENT_COLORS,
        category_orders={"segment": SEGMENT_ORDER},
        labels={"owned_count": "Characters owned", "users": "Users"},
    )
    fig.update_layout(barmode="stack", bargap=0.15)
    return apply_layout(fig, title="Holdings per user", height=380)


def behavior_fig(result: SimResult, metric: str) -> go.Figure:
    spec = BEHAVIOR_METRICS[metric]
    u = result.users.copy()
    if metric not in u.columns:
        raise KeyError(f"unknown behavior column: {metric}")
    # Drop sentinel values (e.g. -1 for "never obtained").
    df = u[u[metric] >= 0][[metric, "segment"]].copy()
    if metric == "spend_usd":
        # Log-scale histogram: replace zeros with a tiny value so they land in the first bin.
        df[metric] = df[metric].replace(0, 0.01)

    fig = px.histogram(
        df,
        x=metric,
        color="segment",
        nbins=spec["nbins"],
        color_discrete_map=SEGMENT_COLORS,
        category_orders={"segment": SEGMENT_ORDER},
        labels={metric: spec["label"]},
        log_x=spec["log_x"],
    )
    fig.update_layout(barmode="stack", bargap=0.15)
    return apply_layout(fig, title=spec["label"], height=380)
