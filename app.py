"""Streamlit entrypoint for the WishWish gacha simulator."""
from __future__ import annotations

import streamlit as st

from simulator.config import SimConfig, config_hash, load_preset
from simulator.engine import SimResult, run_simulation
from ui.compare import render_compare
from ui.dashboard import render_dashboard
from ui.export import render_export
from ui.sidebar import render_sidebar


st.set_page_config(
    page_title="WishWish Gacha Simulator",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------------------------------- #
# Cached simulation runner.
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner="Running simulation…", max_entries=16)
def _cached_run(cfg_hash: str, cfg_json: str) -> SimResult:
    cfg = SimConfig.model_validate_json(cfg_json)
    return run_simulation(cfg)


def cached_run_simulation(cfg: SimConfig) -> SimResult:
    return _cached_run(config_hash(cfg), cfg.model_dump_json())


# --------------------------------------------------------------------------- #
# Main app
# --------------------------------------------------------------------------- #
def main() -> None:
    # Load default preset once.
    if "default_cfg" not in st.session_state:
        st.session_state["default_cfg"] = load_preset("mengjing_v1")
    default_cfg: SimConfig = st.session_state["default_cfg"]

    candidate, run_clicked, _save_name = render_sidebar(default_cfg)

    st.title("WishWish gacha economy simulator")
    st.caption(
        "Monte Carlo simulation of series-level pulls, pity, and player segments. "
        "Tune parameters in the sidebar, hit **Run simulation**, and watch the "
        "distributions shift."
    )

    tab_single, tab_compare, tab_export = st.tabs(["Single Run", "A/B Compare", "Export"])

    if run_clicked and candidate is not None:
        st.session_state["last_result_hash"] = config_hash(candidate)
        st.session_state["last_cfg"] = candidate

    # Decide what to render on the Single Run tab.
    with tab_single:
        active_cfg: SimConfig | None = st.session_state.get("last_cfg", candidate)
        if active_cfg is None:
            st.info("Fix the sidebar errors, then hit **Run simulation**.")
        else:
            if "last_cfg" not in st.session_state:
                st.info("Hit **Run simulation** in the sidebar to render the dashboard.")
            else:
                result = cached_run_simulation(active_cfg)
                render_dashboard(result)

    with tab_compare:
        render_compare(candidate)

    with tab_export:
        last_cfg: SimConfig | None = st.session_state.get("last_cfg")
        if last_cfg is None:
            st.info("Run a simulation first.")
        else:
            render_export(cached_run_simulation(last_cfg))


if __name__ == "__main__":
    main()
