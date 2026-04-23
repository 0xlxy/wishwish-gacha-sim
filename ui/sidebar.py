"""Compact sidebar — globals only.

Per-section tuning (tier weights, segments, draw mechanics) lives inline in
the main dashboard sections, so the sidebar stays dense and scannable.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from simulator.config import (
    SimConfig,
    list_presets,
    load_preset,
    save_preset,
)


def render_sidebar(default_cfg: SimConfig) -> None:
    """Render sidebar globals. All editing writes into ``st.session_state``
    under the key ``current_config``; the main area reads that key.
    """
    st.sidebar.markdown("#### WishWish Simulator")

    # Load a preset.
    preset_names = list_presets()
    choice = st.sidebar.selectbox(
        "Preset",
        options=preset_names,
        index=(preset_names.index(default_cfg.name) if default_cfg.name in preset_names else 0) if preset_names else 0,
        key="preset_select",
    )
    if st.sidebar.button("Load preset", use_container_width=True):
        try:
            st.session_state["current_config"] = load_preset(choice)
            st.rerun()
        except Exception as e:  # noqa: BLE001
            st.sidebar.error(f"Load failed: {e}")

    cfg: SimConfig = st.session_state.get("current_config", default_cfg)

    st.sidebar.markdown("#### Globals")

    # Config name.
    new_name = st.sidebar.text_input("Config name", value=cfg.name, key="cfg_name")

    # Duration.
    duration = st.sidebar.number_input(
        "Duration (days)",
        min_value=1,
        max_value=365,
        value=cfg.series.duration_days,
        step=1,
    )

    # Total users.
    total_users = st.sidebar.number_input(
        "Total users",
        min_value=100,
        max_value=1_000_000,
        value=cfg.population.total_users,
        step=1000,
    )

    # Random seed.
    seed_str = st.sidebar.text_input(
        "Random seed (blank = random)",
        value="" if cfg.population.random_seed is None else str(cfg.population.random_seed),
    )
    try:
        seed = int(seed_str) if seed_str.strip() else None
    except ValueError:
        seed = None
        st.sidebar.warning("Seed must be int or blank.")

    # Write globals back into the live config.
    updated = cfg.model_copy(deep=True)
    updated.name = new_name
    updated.series.duration_days = int(duration)
    updated.population.total_users = int(total_users)
    updated.population.random_seed = seed
    st.session_state["current_config"] = updated

    st.sidebar.markdown("#### Save")
    save_name = st.sidebar.text_input("Preset name", key="save_preset_name")
    if st.sidebar.button("Save as preset", use_container_width=True, disabled=not save_name):
        try:
            p = save_preset(updated, save_name)
            st.sidebar.success(f"Saved {Path(p).name}")
        except Exception as e:  # noqa: BLE001
            st.sidebar.error(f"Save failed: {e}")

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Parameters tune inline — edit tiers, segments, and draw mechanics "
        "next to the charts they affect. Results re-compute automatically."
    )
