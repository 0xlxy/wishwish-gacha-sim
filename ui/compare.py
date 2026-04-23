"""A/B comparison view."""
from __future__ import annotations

from typing import Callable

import streamlit as st

from simulator.config import SimConfig
from simulator.engine import SimResult

from viz import (
    kpi_cards,
    collection,
    rare_analysis,
    revenue,
    pity as pity_viz,
    narrative,
)


def render_compare(
    current_cfg: SimConfig | None,
    runner: Callable[[SimConfig], SimResult],
) -> None:
    st.markdown("### A/B compare")
    st.caption(
        "Snapshot the current sidebar config into slot A or B, then compare "
        "two scenarios side-by-side."
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save current as Scenario A", use_container_width=True, disabled=current_cfg is None):
            st.session_state["scenario_a_cfg"] = current_cfg
    with c2:
        if st.button("Save current as Scenario B", use_container_width=True, disabled=current_cfg is None):
            st.session_state["scenario_b_cfg"] = current_cfg

    cfg_a: SimConfig | None = st.session_state.get("scenario_a_cfg")
    cfg_b: SimConfig | None = st.session_state.get("scenario_b_cfg")

    if cfg_a is None or cfg_b is None:
        st.info("Set both Scenario A and Scenario B to compare.")
        return

    result_a = runner(cfg_a)
    result_b = runner(cfg_b)

    st.markdown("#### Diff summary")
    st.markdown("\n".join(narrative.diff_summary(result_a, result_b)))
    st.divider()

    left, right = st.columns(2)
    with left:
        st.markdown(f"##### Scenario A: {cfg_a.name}")
        kpi_cards.render_kpi_row(result_a)
    with right:
        st.markdown(f"##### Scenario B: {cfg_b.name}")
        kpi_cards.render_kpi_row(result_b)
    st.divider()

    st.markdown("##### Collection")
    l, r = st.columns(2)
    with l:
        st.plotly_chart(collection.collection_histogram_fig(result_a), use_container_width=True)
        st.plotly_chart(collection.completion_funnel_fig(result_a), use_container_width=True)
    with r:
        st.plotly_chart(collection.collection_histogram_fig(result_b), use_container_width=True)
        st.plotly_chart(collection.completion_funnel_fig(result_b), use_container_width=True)
    st.divider()

    st.markdown("##### Rare")
    l, r = st.columns(2)
    with l:
        st.plotly_chart(rare_analysis.pulls_to_first_rare_cdf_fig(result_a), use_container_width=True)
    with r:
        st.plotly_chart(rare_analysis.pulls_to_first_rare_cdf_fig(result_b), use_container_width=True)
    st.divider()

    st.markdown("##### Revenue")
    l, r = st.columns(2)
    with l:
        st.plotly_chart(revenue.lorenz_fig(result_a), use_container_width=True)
        st.plotly_chart(revenue.cumulative_revenue_fig(result_a), use_container_width=True)
    with r:
        st.plotly_chart(revenue.lorenz_fig(result_b), use_container_width=True)
        st.plotly_chart(revenue.cumulative_revenue_fig(result_b), use_container_width=True)
    st.divider()

    st.markdown("##### Pity")
    l, r = st.columns(2)
    with l:
        st.plotly_chart(pity_viz.pity_trigger_histogram_fig(result_a), use_container_width=True)
    with r:
        st.plotly_chart(pity_viz.pity_trigger_histogram_fig(result_b), use_container_width=True)

    st.divider()
    st.markdown("##### Narrative")
    l, r = st.columns(2)
    with l:
        st.markdown(narrative.narrative_markdown(result_a))
    with r:
        st.markdown(narrative.narrative_markdown(result_b))
