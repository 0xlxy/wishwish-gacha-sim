"""Export tab (CSV + PNG-ZIP)."""
from __future__ import annotations

import io
import zipfile

import streamlit as st

from simulator.engine import SimResult
from viz import collection, rare_analysis, revenue, pity as pity_viz


def render_export(result: SimResult | None) -> None:
    if result is None:
        st.info("Run a simulation first.")
        return

    st.subheader("Export")

    # CSV — per-user rows with one owns_<char> column per character.
    csv_bytes = result.users.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download per-user CSV",
        data=csv_bytes,
        file_name=f"{result.config.name}_users.csv",
        mime="text/csv",
        use_container_width=True,
    )

    events_bytes = result.events.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download events CSV",
        data=events_bytes,
        file_name=f"{result.config.name}_events.csv",
        mime="text/csv",
        use_container_width=True,
    )

    if st.button("Build charts ZIP", use_container_width=True):
        with st.spinner("Rendering PNGs…"):
            figs = {
                "collection_histogram": collection.collection_histogram_fig(result),
                "completion_funnel": collection.completion_funnel_fig(result),
                "ownership_heatmap": collection.ownership_heatmap_fig(result),
                "duplicates_violin": collection.duplicates_violin_fig(result),
                "pulls_to_first_rare_cdf": rare_analysis.pulls_to_first_rare_cdf_fig(result),
                "days_to_first_rare_cdf": rare_analysis.days_to_first_rare_cdf_fig(result),
                "rare_ownership_by_segment": rare_analysis.rare_ownership_by_segment_fig(result),
                "rare_source": rare_analysis.rare_source_fig(result),
                "spend_distribution": revenue.spend_distribution_fig(result),
                "lorenz": revenue.lorenz_fig(result),
                "cumulative_revenue": revenue.cumulative_revenue_fig(result),
                "revenue_share": revenue.revenue_share_pie_fig(result),
                "pity_trigger_histogram": pity_viz.pity_trigger_histogram_fig(result),
                "pulls_between_pity": pity_viz.pulls_between_pity_fig(result),
            }
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for name, fig in figs.items():
                    try:
                        png = fig.to_image(format="png", width=1000, height=500)
                    except Exception as e:  # noqa: BLE001
                        st.warning(f"{name}: PNG export failed ({e}). Install kaleido.")
                        return
                    zf.writestr(f"{name}.png", png)
            st.session_state["charts_zip"] = buf.getvalue()

    if "charts_zip" in st.session_state:
        st.download_button(
            "Download charts ZIP",
            data=st.session_state["charts_zip"],
            file_name=f"{result.config.name}_charts.zip",
            mime="application/zip",
            use_container_width=True,
        )
