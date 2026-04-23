"""Persona Journey Explorer charts (PRD §4.3.5)."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from simulator import metrics as m
from simulator.engine import SimResult

from .theme import RARITY_COLORS, apply_layout


def persona_cumulative_fig(persona: m.Persona) -> go.Figure:
    fig = go.Figure()
    x = list(range(len(persona.cumulative_owned)))
    fig.add_trace(
        go.Scatter(
            x=x,
            y=persona.cumulative_owned,
            mode="lines",
            name="Unique characters",
            line=dict(color="#2563EB", width=3, shape="hv"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=persona.cumulative_spend_usd,
            mode="lines",
            name="Cumulative spend (USD)",
            yaxis="y2",
            line=dict(color="#F59E0B", width=3),
        )
    )
    fig.update_layout(
        xaxis_title="Day",
        yaxis=dict(title="Unique characters owned", rangemode="tozero"),
        yaxis2=dict(
            title="Cumulative spend (USD)",
            overlaying="y",
            side="right",
            rangemode="tozero",
        ),
    )
    return apply_layout(fig, title="Cumulative collection & spend", height=320)


def persona_pull_strip_fig(persona: m.Persona, result: SimResult) -> go.Figure:
    ev = persona.events
    if ev.empty:
        fig = go.Figure()
        fig.update_layout(annotations=[
            dict(text="No pulls for this user", showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5),
        ])
        return apply_layout(fig, title="Per-pull timeline", height=180)
    tier_names = result.meta["tier_names"]
    tier_idx = result.meta["char_tier_idx"]
    # Color per event: if was_pity, use highlight; else base tier color.
    def _color(row: dict) -> str:
        base = tier_names[int(tier_idx[int(row["char_idx"])])]
        return RARITY_COLORS.get(base, "#9CA3AF")

    # One marker per pull, x=pull index within user, y=day for a mild stagger.
    custom = ev.assign(
        hover=ev.apply(
            lambda r: (
                f"Day {int(r['day']) + 1}, pull #{int(r['pull_idx_within_user']) + 1}<br>"
                f"{r['character']} ({r['tier']})<br>"
                f"{'PITY' if r['was_pity'] else 'normal'}"
                f"{' • NEW' if r['was_new'] else ''}"
            ),
            axis=1,
        )
    )
    colors = [_color(r) for _, r in ev.iterrows()]
    # Outline pity-triggered pulls with a red border.
    line_widths = [2.5 if p else 0 for p in ev["was_pity"]]
    line_colors = ["#DC2626" if p else "rgba(0,0,0,0)" for p in ev["was_pity"]]

    fig = go.Figure(
        data=go.Scatter(
            x=ev["pull_idx_within_user"] + 1,
            y=ev["day"] + 1,
            mode="markers",
            marker=dict(
                size=[12 if n else 8 for n in ev["was_new"]],
                color=colors,
                line=dict(color=line_colors, width=line_widths),
                symbol=["star" if n else "circle" for n in ev["was_new"]],
            ),
            text=custom["hover"],
            hovertemplate="%{text}<extra></extra>",
        )
    )
    fig.update_layout(
        xaxis_title="Pull # (this user)",
        yaxis_title="Day",
        yaxis=dict(autorange="reversed"),
    )
    return apply_layout(fig, title="Per-pull timeline (★ = new, red outline = pity)", height=320)
