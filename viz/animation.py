"""Simulation-process animation.

Day-by-day animated holdings histogram. Shows how the population's collection
size evolves over the series, with play/pause and a day slider built in by
Plotly — no Streamlit re-runs needed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from simulator.engine import SimResult, popcount64

from .theme import SEGMENT_COLORS, SEGMENT_ORDER, apply_layout


def _holdings_by_day(result: SimResult) -> pd.DataFrame:
    """Long-form: one row per (day, segment, owned_count)."""
    owned_by_day = result.owned_by_day  # [N, D+1] uint64
    seg_idx_arr = result.users["segment_idx"].to_numpy()
    D = result.meta["duration_days"]
    num_chars = result.num_chars

    popcnt = popcount64(owned_by_day.ravel()).reshape(owned_by_day.shape)

    # Per-day, per-segment histogram over 0..num_chars.
    rows: list[dict] = []
    for d in range(D + 1):
        col = popcnt[:, d]
        for si, sname in enumerate(result.segment_names):
            mask = seg_idx_arr == si
            if not mask.any():
                continue
            hist = np.bincount(col[mask], minlength=num_chars + 1)
            for k in range(num_chars + 1):
                rows.append(
                    {
                        "day": int(d),
                        "segment": sname,
                        "owned_count": int(k),
                        "users": int(hist[k]),
                    }
                )
    return pd.DataFrame(rows)


def simulation_animation_fig(result: SimResult) -> go.Figure:
    df = _holdings_by_day(result)
    if df.empty:
        return apply_layout(go.Figure(), title="Simulation process", height=420)

    # Stacked bar max across all frames for a stable y-axis.
    stacked_max = (
        df.groupby(["day", "owned_count"])["users"].sum().max() * 1.1
    )

    fig = px.bar(
        df,
        x="owned_count",
        y="users",
        color="segment",
        color_discrete_map=SEGMENT_COLORS,
        category_orders={"segment": SEGMENT_ORDER},
        animation_frame="day",
        animation_group="segment",
        range_y=[0, stacked_max],
        labels={"owned_count": "Characters owned", "users": "Users"},
    )
    fig.update_layout(barmode="stack", bargap=0.15)

    # Pace the auto-play so the evolution is readable.
    if fig.layout.updatemenus:
        for menu in fig.layout.updatemenus:
            for btn in menu.buttons:
                if btn.args and isinstance(btn.args[1], dict):
                    btn.args[1].setdefault("frame", {}).update(
                        {"duration": 500, "redraw": True}
                    )
                    btn.args[1].setdefault("transition", {}).update(
                        {"duration": 250}
                    )
    # Nicer slider label.
    if fig.layout.sliders:
        for s in fig.layout.sliders:
            s.currentvalue.prefix = "Day "

    return apply_layout(
        fig,
        title=f"Simulation process — holdings over {result.meta['duration_days']} days",
        height=440,
    )
