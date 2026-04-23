"""Shared color palette and chart defaults."""
from __future__ import annotations

import plotly.graph_objects as go

SEGMENT_COLORS: dict[str, str] = {
    "Whale": "#8B5CF6",
    "Dolphin": "#3B82F6",
    "Minnow": "#10B981",
    "F2P": "#6B7280",
    "All": "#111827",
}

RARITY_COLORS: dict[str, str] = {
    "Common": "#9CA3AF",
    "Rare": "#F59E0B",
    "Epic": "#EF4444",
    "Legendary": "#A855F7",
}

SEGMENT_ORDER: list[str] = ["Whale", "Dolphin", "Minnow", "F2P"]


def apply_layout(fig: go.Figure, title: str = "", height: int = 360) -> go.Figure:
    fig.update_layout(
        title=title or None,
        margin=dict(l=40, r=20, t=50 if title else 20, b=40),
        height=height,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def segment_color(name: str) -> str:
    return SEGMENT_COLORS.get(name, "#374151")
