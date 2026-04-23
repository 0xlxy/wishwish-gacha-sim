"""Shared color palette and chart defaults.

Tokens align with ui/style.py so Streamlit chrome and Plotly charts feel
visually unified. Palette matches the reference design
(https://codereview.withmartian.com/).
"""
from __future__ import annotations

import plotly.graph_objects as go

# Keep segment identity colors vivid — purple accent reserved for "Whale"
# so it reads as the most-paying tier under the Martian palette.
SEGMENT_COLORS: dict[str, str] = {
    "Whale": "#563FFF",
    "Dolphin": "#3B82F6",
    "Minnow": "#55C89F",
    "F2P": "rgba(0, 0, 0, 0.45)",
    "All": "rgba(0, 0, 0, 0.88)",
}

RARITY_COLORS: dict[str, str] = {
    "Common": "rgba(0, 0, 0, 0.45)",
    "Rare": "#FFD24D",
    "Epic": "#EE412B",
    "Legendary": "#563FFF",
}

SEGMENT_ORDER: list[str] = ["Whale", "Dolphin", "Minnow", "F2P"]

_FONT_STACK = (
    'Work Sans, -apple-system, BlinkMacSystemFont, "Segoe UI", '
    'Helvetica, Arial, sans-serif'
)
_TEXT_PRIMARY = "rgba(0, 0, 0, 0.88)"
_TEXT_SECONDARY = "rgba(0, 0, 0, 0.65)"
_BORDER = "#E5DFDF"


def apply_layout(fig: go.Figure, title: str = "", height: int = 360) -> go.Figure:
    fig.update_layout(
        title=dict(
            text=title or None,
            font=dict(
                family=_FONT_STACK,
                size=14,
                color=_TEXT_PRIMARY,
                weight=600,
            ),
            x=0,
            xanchor="left",
            pad=dict(l=4, t=6),
        ),
        margin=dict(l=48, r=16, t=44 if title else 16, b=40),
        height=height,
        font=dict(family=_FONT_STACK, size=12, color=_TEXT_SECONDARY),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(family=_FONT_STACK, size=11, color=_TEXT_SECONDARY),
            bgcolor="rgba(0,0,0,0)",
        ),
        colorway=[
            SEGMENT_COLORS["Whale"],
            SEGMENT_COLORS["Dolphin"],
            SEGMENT_COLORS["Minnow"],
            SEGMENT_COLORS["F2P"],
            RARITY_COLORS["Rare"],
            RARITY_COLORS["Epic"],
        ],
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor=_BORDER,
        gridwidth=1,
        zeroline=False,
        linecolor=_BORDER,
        tickfont=dict(family=_FONT_STACK, size=11, color=_TEXT_SECONDARY),
        title_font=dict(family=_FONT_STACK, size=12, color=_TEXT_SECONDARY),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=_BORDER,
        gridwidth=1,
        zeroline=False,
        linecolor=_BORDER,
        tickfont=dict(family=_FONT_STACK, size=11, color=_TEXT_SECONDARY),
        title_font=dict(family=_FONT_STACK, size=12, color=_TEXT_SECONDARY),
    )
    return fig


def segment_color(name: str) -> str:
    return SEGMENT_COLORS.get(name, "rgba(0,0,0,0.45)")
