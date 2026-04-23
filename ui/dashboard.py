"""Single-run dashboard. Auto-runs on current config and shows results immediately.

Section-local tuning controls are embedded next to the charts they affect,
so the sidebar stays compact and the right-hand area is always full.
"""
from __future__ import annotations

from typing import Callable

import streamlit as st

from simulator.config import SimConfig
from simulator.engine import SimResult
from simulator import metrics as m

from viz import (
    kpi_cards,
    collection,
    rare_analysis,
    revenue,
    persona as persona_viz,
    pity as pity_viz,
    narrative,
)

from .section_editors import (
    tiers_editor,
    segments_editor,
    draw_mechanics_editor,
)


def _section_header(pill: str, title: str, caption: str = "") -> None:
    st.markdown(
        f'<div style="margin-top:1.5rem;"><span class="section-pill">{pill}</span>'
        f'<span style="font-size:1.1rem;font-weight:600;color:#111827;">{title}</span></div>',
        unsafe_allow_html=True,
    )
    if caption:
        st.caption(caption)


def render_dashboard(
    cfg: SimConfig,
    runner: Callable[[SimConfig], SimResult],
) -> None:
    # 1. KPIs — run the current (possibly just-edited) cfg.
    result = runner(cfg)

    _section_header(
        "Overview",
        "Headline metrics",
        f"{result.n_users:,} users over {result.meta['duration_days']} days.",
    )
    kpi_cards.render_kpi_row(result)

    # 2. Collection — put tier editor inline.
    _section_header("Series", "Collection distribution",
                    "Edit rarity tiers below — probabilities must sum to 1.0.")
    with st.expander("Edit rarity tiers", expanded=False):
        cfg = tiers_editor(cfg)
        result = runner(cfg)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(collection.collection_histogram_fig(result), use_container_width=True)
    with col2:
        st.plotly_chart(collection.completion_funnel_fig(result), use_container_width=True)
    st.plotly_chart(collection.ownership_heatmap_fig(result), use_container_width=True)
    st.plotly_chart(collection.duplicates_violin_fig(result), use_container_width=True)

    # 3. Rare deep-dive — draw mechanics editor here.
    _section_header("Rare", "Rare deep-dive",
                    "Tune pull costs, pity threshold and guarantee rule.")
    with st.expander("Edit draw mechanics", expanded=False):
        cfg = draw_mechanics_editor(cfg)
        result = runner(cfg)

    st.plotly_chart(rare_analysis.pulls_to_first_rare_cdf_fig(result), use_container_width=True)
    st.plotly_chart(rare_analysis.days_to_first_rare_cdf_fig(result), use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(rare_analysis.rare_ownership_by_segment_fig(result), use_container_width=True)
    with col2:
        st.plotly_chart(rare_analysis.rare_source_fig(result), use_container_width=True)

    # 4. Revenue — no editor; already covered by draw mechanics above.
    _section_header("Revenue", "Spend & revenue",
                    f"Gini-style concentration across segments.")
    st.plotly_chart(revenue.spend_distribution_fig(result), use_container_width=True)
    col1, col2 = st.columns([2, 1])
    with col1:
        st.plotly_chart(revenue.lorenz_fig(result), use_container_width=True)
    with col2:
        st.plotly_chart(revenue.revenue_share_pie_fig(result), use_container_width=True)
    st.plotly_chart(revenue.cumulative_revenue_fig(result), use_container_width=True)

    mlot = m.money_left_on_table(result)
    if mlot["segments"]:
        with st.expander("Money left on the table"):
            for s in mlot["segments"]:
                st.markdown(
                    f"- **{s['segment']}** ({s['completed_users']} completed): "
                    f"avg completion at day {s['avg_day_completed']:.1f}; "
                    f"{s['days_unused']:.1f} unused days."
                )

    # 5. Persona — with segment editor inline.
    _section_header("Persona", "Persona Journey Explorer",
                    "Ranked within segment by final collection then spend (desc).")
    with st.expander("Edit population segments", expanded=False):
        cfg = segments_editor(cfg)
        result = runner(cfg)

    col1, col2 = st.columns([1, 3])
    with col1:
        segment = st.selectbox(
            "Segment",
            options=result.segment_names,
            index=result.segment_names.index("F2P") if "F2P" in result.segment_names else 0,
            key="persona_segment",
        )
    with col2:
        pct = st.slider("Percentile", min_value=0, max_value=100, value=50, step=1, key="persona_pct")

    try:
        persona = m.get_persona(result, segment, pct)
        st.markdown(persona.narrative)
        st.plotly_chart(persona_viz.persona_cumulative_fig(persona), use_container_width=True)
        st.plotly_chart(persona_viz.persona_pull_strip_fig(persona, result), use_container_width=True)
    except ValueError as e:
        st.warning(str(e))

    # 6. Pity diagnostics.
    _section_header("Pity", "Pity diagnostics")
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(pity_viz.pity_trigger_histogram_fig(result), use_container_width=True)
    with col2:
        st.plotly_chart(pity_viz.pulls_between_pity_fig(result), use_container_width=True)
    st.markdown(pity_viz.pity_utility_card(result))

    # 7. Narrative auto-summary.
    _section_header("Summary", "Narrative summary",
                    "Auto-generated blocks — screenshot-ready.")
    st.markdown(narrative.narrative_markdown(result))
