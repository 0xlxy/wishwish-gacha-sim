"""KPI row rendering (Streamlit-native st.metric tiles).

Not a Plotly module — it renders directly into Streamlit.
"""
from __future__ import annotations

from typing import Any

import streamlit as st

from simulator.engine import SimResult
from simulator import metrics as m


def _fmt_usd(v: float) -> str:
    return f"${v:,.2f}" if v < 1_000 else f"${v:,.0f}"


def _fmt_pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def render_kpi_row(result: SimResult, kpi: dict[str, Any] | None = None) -> None:
    kpi = kpi or m.kpi_summary(result)

    card_specs: list[tuple[str, str, str]] = [
        ("Users simulated", f"{kpi['users']:,}", ""),
        ("Completion rate", _fmt_pct(kpi["completion_rate"]), "own all characters"),
        (
            "Median pulls → 1st Rare",
            (
                f"{kpi['median_pulls_to_first_rare']:.0f}"
                if kpi["median_pulls_to_first_rare"] == kpi["median_pulls_to_first_rare"]  # NaN guard
                else "—"
            ),
            "across users who got one",
        ),
        ("Median spend", _fmt_usd(kpi["median_spend_usd"]), "per user (USD)"),
        ("Total revenue", _fmt_usd(kpi["total_revenue_usd"]), "simulated"),
        ("ARPU", _fmt_usd(kpi["arpu_usd"]), "all users"),
        ("ARPPU", _fmt_usd(kpi["arppu_usd"]), "paying users"),
        ("Median owned", f"{kpi['median_owned']:.0f}", f"of {result.num_chars}"),
    ]

    # Split into two rows of 4 for a cleaner layout.
    for i in range(0, len(card_specs), 4):
        cols = st.columns(4)
        for col, (label, value, caption) in zip(cols, card_specs[i : i + 4]):
            with col:
                st.metric(label, value, help=caption or None)

    with st.expander("Per-segment breakdown"):
        seg = kpi["per_segment"].copy()
        seg["completion_rate"] = seg["completion_rate"].map(_fmt_pct)
        seg["median_spend_usd"] = seg["median_spend_usd"].map(_fmt_usd)
        seg["total_revenue_usd"] = seg["total_revenue_usd"].map(_fmt_usd)
        seg["avg_pity_triggers"] = seg["avg_pity_triggers"].map(lambda v: f"{v:.2f}")
        st.dataframe(seg, hide_index=True, use_container_width=True)
