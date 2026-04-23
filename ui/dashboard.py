"""Single-run dashboard (PRD §4.3)."""
from __future__ import annotations

import streamlit as st

from simulator.engine import SimResult
from simulator import metrics as m

from viz import kpi_cards, collection, rare_analysis, revenue, persona as persona_viz, pity as pity_viz, narrative


def render_dashboard(result: SimResult) -> None:
    # §4.3.1 KPI row
    st.subheader("Headline metrics")
    kpi_cards.render_kpi_row(result)
    st.divider()

    # §4.3.2 Collection distribution
    st.subheader("Collection distribution")
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(collection.collection_histogram_fig(result), use_container_width=True)
    with col2:
        st.plotly_chart(collection.completion_funnel_fig(result), use_container_width=True)
    st.plotly_chart(collection.ownership_heatmap_fig(result), use_container_width=True)
    st.plotly_chart(collection.duplicates_violin_fig(result), use_container_width=True)
    st.divider()

    # §4.3.3 Rare deep dive
    st.subheader("Rare deep-dive")
    st.plotly_chart(rare_analysis.pulls_to_first_rare_cdf_fig(result), use_container_width=True)
    st.plotly_chart(rare_analysis.days_to_first_rare_cdf_fig(result), use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(rare_analysis.rare_ownership_by_segment_fig(result), use_container_width=True)
    with col2:
        st.plotly_chart(rare_analysis.rare_source_fig(result), use_container_width=True)
    st.divider()

    # §4.3.4 Revenue analytics
    st.subheader("Spend & revenue")
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
    st.divider()

    # §4.3.5 Persona Journey Explorer
    st.subheader("Persona Journey Explorer")
    st.caption(
        "Pick a segment and percentile (0 = unluckiest, 100 = luckiest — ranked by "
        "collection size then tiebroken by spend descending)."
    )
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
    st.divider()

    # §4.3.6 Pity diagnostics
    st.subheader("Pity diagnostics")
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(pity_viz.pity_trigger_histogram_fig(result), use_container_width=True)
    with col2:
        st.plotly_chart(pity_viz.pulls_between_pity_fig(result), use_container_width=True)
    st.markdown(pity_viz.pity_utility_card(result))
    st.divider()

    # §4.3.7 Narrative summary
    st.subheader("Narrative summary")
    st.markdown(narrative.narrative_markdown(result))
