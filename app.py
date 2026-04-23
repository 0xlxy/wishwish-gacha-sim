"""Streamlit entrypoint for the WishWish gacha simulator."""
from __future__ import annotations

import streamlit as st

from simulator.config import SimConfig, config_hash, load_preset
from simulator.engine import SimResult, run_simulation

from ui.dashboard import render_dashboard
from ui.export import render_export
from ui.sidebar import render_sidebar
from ui.style import inject as inject_css


st.set_page_config(
    page_title="WishWish Gacha Simulator",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()


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

    # Sidebar updates st.session_state["current_config"] in place.
    render_sidebar(default_cfg)
    cfg: SimConfig = st.session_state.get("current_config", default_cfg)

    st.markdown("# WishWish gacha economy simulator")
    st.caption(
        "Monte Carlo over pulls, pity, and segments. Edit parameters inline — "
        "the dashboard re-computes automatically."
    )

    tab_single, tab_export = st.tabs(["Dashboard", "Export"])

    with tab_single:
        render_dashboard(cfg, cached_run_simulation)

    with tab_export:
        render_export(cached_run_simulation(cfg))


if __name__ == "__main__":
    main()
