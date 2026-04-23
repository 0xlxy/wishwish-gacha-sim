"""Simulation-process animation.

Day-by-day animated holdings histogram. Built directly with plotly.graph_objects
so we control exactly how each frame replaces trace data — px.bar's animation
wrapper leaves `redraw` off on slider steps, which causes the chart to stop
updating past day 0.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from simulator.engine import SimResult, popcount64

from .theme import SEGMENT_COLORS, SEGMENT_ORDER, apply_layout


def _holdings_matrix(result: SimResult) -> tuple[np.ndarray, list[str]]:
    """Return a [D+1, num_segments, num_chars+1] int array of user counts."""
    owned_by_day = result.owned_by_day  # [N, D+1] uint64
    seg_idx_arr = result.users["segment_idx"].to_numpy()
    D = result.meta["duration_days"]
    num_chars = result.num_chars

    popcnt = popcount64(owned_by_day.ravel()).reshape(owned_by_day.shape)
    ordered_segments = [s for s in SEGMENT_ORDER if s in result.segment_names] + [
        s for s in result.segment_names if s not in SEGMENT_ORDER
    ]
    seg_to_idx = {name: i for i, name in enumerate(result.segment_names)}

    counts = np.zeros((D + 1, len(ordered_segments), num_chars + 1), dtype=np.int32)
    for d in range(D + 1):
        col = popcnt[:, d]
        for out_si, sname in enumerate(ordered_segments):
            src_si = seg_to_idx[sname]
            mask = seg_idx_arr == src_si
            if not mask.any():
                continue
            hist = np.bincount(col[mask], minlength=num_chars + 1)
            counts[d, out_si, : num_chars + 1] = hist[: num_chars + 1]
    return counts, ordered_segments


def _holdings_by_day(result: SimResult) -> pd.DataFrame:
    """Long-form counts, kept for any other callers (tests/exports)."""
    counts, seg_names = _holdings_matrix(result)
    D, S, K = counts.shape
    rows: list[dict] = []
    for d in range(D):
        for si, sname in enumerate(seg_names):
            for k in range(K):
                rows.append({"day": d, "segment": sname, "owned_count": k, "users": int(counts[d, si, k])})
    return pd.DataFrame(rows)


def simulation_animation_fig(result: SimResult) -> go.Figure:
    counts, seg_names = _holdings_matrix(result)
    if counts.size == 0:
        return apply_layout(go.Figure(), title="Simulation process", height=420)

    D_plus_1, S, K = counts.shape
    x_vals = list(range(K))
    # Stable y-axis: max stacked height across all days.
    stacked_max = int(counts.sum(axis=1).max() * 1.1) or 1

    def _traces_for_day(d: int) -> list[go.Bar]:
        return [
            go.Bar(
                x=x_vals,
                y=counts[d, si].tolist(),
                name=sname,
                marker_color=SEGMENT_COLORS.get(sname, "rgba(0,0,0,0.45)"),
            )
            for si, sname in enumerate(seg_names)
        ]

    # Base figure = day 0.
    fig = go.Figure(data=_traces_for_day(0))
    # Frames for days 0..D.
    fig.frames = [
        go.Frame(name=str(d), data=_traces_for_day(d)) for d in range(D_plus_1)
    ]

    # Play / pause buttons.
    play_args = [
        None,
        {
            "frame": {"duration": 500, "redraw": True},
            "fromcurrent": True,
            "transition": {"duration": 250, "easing": "linear"},
            "mode": "immediate",
        },
    ]
    pause_args = [
        [None],
        {
            "frame": {"duration": 0, "redraw": False},
            "mode": "immediate",
            "transition": {"duration": 0},
        },
    ]

    fig.update_layout(
        barmode="stack",
        bargap=0.15,
        yaxis=dict(range=[0, stacked_max], title="Users"),
        xaxis=dict(
            title="Characters owned",
            tickmode="array",
            tickvals=x_vals,
            range=[-0.5, K - 0.5],
        ),
        updatemenus=[
            dict(
                type="buttons",
                direction="left",
                showactive=False,
                x=0,
                xanchor="left",
                y=-0.2,
                yanchor="top",
                pad=dict(t=0, r=6),
                buttons=[
                    dict(label="▶", method="animate", args=play_args),
                    dict(label="❚❚", method="animate", args=pause_args),
                ],
            )
        ],
        sliders=[
            dict(
                active=0,
                x=0.08,
                xanchor="left",
                y=-0.2,
                yanchor="top",
                len=0.92,
                currentvalue=dict(prefix="Day ", xanchor="right", font=dict(size=12)),
                pad=dict(t=0, b=0),
                steps=[
                    dict(
                        method="animate",
                        label=str(d),
                        args=[
                            [str(d)],
                            {
                                "frame": {"duration": 0, "redraw": True},
                                "mode": "immediate",
                                "transition": {"duration": 0},
                            },
                        ],
                    )
                    for d in range(D_plus_1)
                ],
            )
        ],
    )

    return apply_layout(
        fig,
        title=f"Simulation process — holdings over {result.meta['duration_days']} days",
        height=460,
    )
