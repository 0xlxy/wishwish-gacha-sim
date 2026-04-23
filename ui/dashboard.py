"""Minimal dashboard: KPIs, simulation animation, holdings + behavior
distributions. Everything else moved to an Advanced expander.
"""
from __future__ import annotations

from typing import Callable

import streamlit as st

from simulator.config import SimConfig
from simulator.engine import SimResult
from simulator import metrics as m

from viz import behavior as beh_viz
from viz.animation import simulation_animation_fig

from .param_bar import inline_params
from .section_editors import (
    tiers_editor,
    segments_editor,
    draw_mechanics_editor,
)


def _kpi_row(result: SimResult) -> None:
    k = m.kpi_summary(result)
    cols = st.columns(4)
    with cols[0]:
        st.metric("Users", f"{k['users']:,}")
    with cols[1]:
        st.metric(
            "Completion rate",
            f"{k['completion_rate'] * 100:.1f}%",
            help=f"% of users owning all {result.num_chars} characters",
        )
    with cols[2]:
        v = k["median_pulls_to_first_rare"]
        v_str = f"{v:.0f}" if v == v else "—"  # NaN guard
        st.metric("Median pulls → 1st Rare", v_str)
    with cols[3]:
        st.metric("Median holdings", f"{k['median_owned']:.0f} / {result.num_chars}")


_BEHAVIOR_OPTIONS = [
    ("total_pulls", "Total pulls"),
    ("paid_pulls", "Paid pulls"),
    ("spend_usd", "Spend (USD)"),
    ("first_rare_day", "Day of first Rare"),
    ("days_to_complete", "Day of completion"),
    ("pity_triggers", "Pity triggers"),
]


def render_dashboard(
    cfg: SimConfig,
    runner: Callable[[SimConfig], SimResult],
) -> None:
    # Inline params — edits re-compute the sim automatically via cache.
    cfg = inline_params(cfg)
    result = runner(cfg)

    _kpi_row(result)

    # Simulation process — day-by-day animated histogram.
    st.markdown(
        '<span class="section-pill">Process</span>'
        '<span style="font-size:15px;font-weight:600;color:rgba(0,0,0,0.88);">'
        'Simulation process</span>',
        unsafe_allow_html=True,
    )
    st.caption("Scrub the day slider or press ▶ to see the collection size distribution evolve.")
    st.plotly_chart(simulation_animation_fig(result), use_container_width=True)

    # Final distributions — holdings and chosen behavior metric.
    st.markdown(
        '<span class="section-pill">End state</span>'
        '<span style="font-size:15px;font-weight:600;color:rgba(0,0,0,0.88);">'
        'Distributions</span>',
        unsafe_allow_html=True,
    )
    col_l, col_r = st.columns(2)
    with col_l:
        st.plotly_chart(beh_viz.holdings_fig(result), use_container_width=True)
    with col_r:
        metric_key = st.selectbox(
            "Behavior metric",
            options=[o[0] for o in _BEHAVIOR_OPTIONS],
            format_func=dict(_BEHAVIOR_OPTIONS).get,
            index=0,
            key="behavior_metric",
        )
        st.plotly_chart(beh_viz.behavior_fig(result, metric_key), use_container_width=True)

    # Advanced config — tucked away for power users.
    with st.expander("Advanced configuration (tiers, segments, draw mechanics)", expanded=False):
        st.caption("Rarity tiers")
        cfg = tiers_editor(cfg)
        st.caption("Draw mechanics")
        cfg = draw_mechanics_editor(cfg)
        st.caption("Population segments")
        cfg = segments_editor(cfg)
