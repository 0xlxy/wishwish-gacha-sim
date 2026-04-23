"""Streamlit sidebar — editable configuration UI."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from simulator.config import (
    DrawConfig,
    PopulationConfig,
    RarityTier,
    SeriesConfig,
    SimConfig,
    UserSegment,
    list_presets,
    load_preset,
    save_preset,
)


STOP_RULES = ["never_stop", "stop_on_complete", "stop_on_rare"]
PITY_RULES = ["unowned_any", "unowned_rare_or_above", "rare_or_above"]


def _tier_df(series: SeriesConfig) -> pd.DataFrame:
    rows = []
    for t in series.tiers:
        rows.append(
            {
                "name": t.name,
                "character_count": t.character_count,
                "probability": t.probability,
                "in_pity_pool": t.in_pity_pool,
                "character_names": ", ".join(t.character_names),
            }
        )
    return pd.DataFrame(rows)


def _segments_df(pop: PopulationConfig) -> pd.DataFrame:
    rows = []
    for s in pop.segments:
        rows.append(
            {
                "name": s.name,
                "population_share": s.population_share,
                "daily_active_rate": s.daily_active_rate,
                "extra_paid_pulls_min": s.extra_paid_pulls_min,
                "extra_paid_pulls_max": s.extra_paid_pulls_max,
                "stop_rule": s.stop_rule,
            }
        )
    return pd.DataFrame(rows)


def _tiers_from_df(df: pd.DataFrame) -> list[RarityTier]:
    tiers = []
    for _, row in df.iterrows():
        names_raw = str(row.get("character_names", "") or "")
        names = [s.strip() for s in names_raw.split(",") if s.strip()]
        tiers.append(
            RarityTier(
                name=str(row["name"]),
                character_count=int(row["character_count"]),
                probability=float(row["probability"]),
                in_pity_pool=bool(row["in_pity_pool"]),
                character_names=names,
            )
        )
    return tiers


def _segments_from_df(df: pd.DataFrame) -> list[UserSegment]:
    segs = []
    for _, row in df.iterrows():
        segs.append(
            UserSegment(
                name=str(row["name"]),
                population_share=float(row["population_share"]),
                daily_active_rate=float(row["daily_active_rate"]),
                extra_paid_pulls_min=int(row["extra_paid_pulls_min"]),
                extra_paid_pulls_max=int(row["extra_paid_pulls_max"]),
                stop_rule=str(row["stop_rule"]),
            )
        )
    return segs


def _build_config(
    name: str,
    duration_days: int,
    tiers_df: pd.DataFrame,
    draw_vals: dict[str, Any],
    total_users: int,
    random_seed: int | None,
    segments_df: pd.DataFrame,
) -> tuple[SimConfig | None, list[str]]:
    errors: list[str] = []
    try:
        series = SeriesConfig(duration_days=duration_days, tiers=_tiers_from_df(tiers_df))
    except (ValidationError, ValueError) as e:
        errors.append(f"Series: {e}")
        series = None
    try:
        draw = DrawConfig(**draw_vals)
    except (ValidationError, ValueError) as e:
        errors.append(f"Draw: {e}")
        draw = None
    try:
        population = PopulationConfig(
            total_users=total_users,
            segments=_segments_from_df(segments_df),
            random_seed=random_seed,
        )
    except (ValidationError, ValueError) as e:
        errors.append(f"Population: {e}")
        population = None

    if series is None or draw is None or population is None:
        return None, errors
    try:
        cfg = SimConfig(name=name, series=series, draw=draw, population=population)
    except (ValidationError, ValueError) as e:
        errors.append(str(e))
        return None, errors
    return cfg, errors


def render_sidebar(default_cfg: SimConfig) -> tuple[SimConfig | None, bool, str]:
    """Render sidebar. Returns (config_or_None, run_clicked, save_name)."""
    st.sidebar.header("Gacha Simulator")

    # Preset loader.
    presets = list_presets()
    preset_sel = st.sidebar.selectbox(
        "Load preset",
        options=["(current)"] + presets,
        index=0,
    )
    if preset_sel != "(current)" and st.sidebar.button(f"Load {preset_sel}"):
        try:
            loaded = load_preset(preset_sel)
            st.session_state["current_config"] = loaded
            st.rerun()
        except Exception as e:  # noqa: BLE001
            st.sidebar.error(f"Failed to load preset: {e}")

    cfg: SimConfig = st.session_state.get("current_config", default_cfg)

    with st.sidebar.expander("Series config", expanded=True):
        name = st.text_input("Config name", value=cfg.name, key="cfg_name")
        duration_days = st.number_input(
            "Duration (days)", min_value=1, max_value=365, value=cfg.series.duration_days, step=1
        )
        st.caption(
            "Rarity tiers. Probabilities must sum to 1.0. Per-tier names are comma-separated."
        )
        tiers_df = st.data_editor(
            _tier_df(cfg.series),
            key="tiers_df",
            num_rows="dynamic",
            column_config={
                "probability": st.column_config.NumberColumn(format="%.4f", min_value=0.0, max_value=1.0),
                "character_count": st.column_config.NumberColumn(min_value=1, step=1),
            },
            use_container_width=True,
        )

    with st.sidebar.expander("Draw mechanics", expanded=True):
        daily_free_draws = st.number_input(
            "Daily free pulls", min_value=0, max_value=20, value=cfg.draw.daily_free_draws
        )
        single_cost = st.number_input(
            "Single-pull cost (wish)", min_value=0, value=cfg.draw.single_pull_cost_wish, step=10
        )
        ten_cost = st.number_input(
            "10-pull cost (wish)", min_value=0, value=cfg.draw.ten_pull_cost_wish, step=10
        )
        wish_per_usd = st.number_input(
            "Wish per USD", min_value=1, value=cfg.draw.wish_per_usd, step=1
        )
        pity_threshold = st.number_input(
            "Pity threshold", min_value=1, max_value=200, value=cfg.draw.pity_threshold
        )
        pity_rule = st.selectbox(
            "Pity guarantee",
            options=PITY_RULES,
            index=PITY_RULES.index(cfg.draw.pity_guarantee),
        )
        soft_enabled = st.checkbox(
            "Soft pity (linear ramp)", value=(cfg.draw.soft_pity_start is not None)
        )
        soft_start: int | None = None
        soft_full: int | None = None
        if soft_enabled:
            col1, col2 = st.columns(2)
            with col1:
                soft_start = st.number_input(
                    "Soft start",
                    min_value=0,
                    max_value=pity_threshold - 1,
                    value=cfg.draw.soft_pity_start or 0,
                )
            with col2:
                soft_full = st.number_input(
                    "Soft full",
                    min_value=max(1, int(soft_start) + 1),
                    max_value=pity_threshold,
                    value=cfg.draw.soft_pity_full or pity_threshold,
                )

    draw_vals = {
        "daily_free_draws": int(daily_free_draws),
        "single_pull_cost_wish": int(single_cost),
        "ten_pull_cost_wish": int(ten_cost),
        "wish_per_usd": int(wish_per_usd),
        "pity_threshold": int(pity_threshold),
        "pity_guarantee": pity_rule,
        "soft_pity_start": int(soft_start) if soft_enabled else None,
        "soft_pity_full": int(soft_full) if soft_enabled else None,
    }

    with st.sidebar.expander("Population & behavior", expanded=True):
        total_users = st.number_input(
            "Total simulated users",
            min_value=100,
            max_value=1_000_000,
            value=cfg.population.total_users,
            step=1000,
        )
        seed_str = st.text_input(
            "Random seed (blank = random)",
            value="" if cfg.population.random_seed is None else str(cfg.population.random_seed),
        )
        try:
            random_seed = int(seed_str) if seed_str.strip() else None
        except ValueError:
            random_seed = None
            st.warning("Seed must be an integer or blank.")
        segments_df = st.data_editor(
            _segments_df(cfg.population),
            key="segments_df",
            num_rows="dynamic",
            column_config={
                "population_share": st.column_config.NumberColumn(format="%.4f", min_value=0.0, max_value=1.0),
                "daily_active_rate": st.column_config.NumberColumn(format="%.3f", min_value=0.0, max_value=1.0),
                "stop_rule": st.column_config.SelectboxColumn(options=STOP_RULES),
            },
            use_container_width=True,
        )

    candidate, errors = _build_config(
        name=name,
        duration_days=int(duration_days),
        tiers_df=tiers_df,
        draw_vals=draw_vals,
        total_users=int(total_users),
        random_seed=random_seed,
        segments_df=segments_df,
    )

    if errors:
        for e in errors:
            st.sidebar.error(e)

    run_clicked = st.sidebar.button(
        "Run simulation",
        type="primary",
        disabled=candidate is None,
        use_container_width=True,
    )

    st.sidebar.divider()
    save_name = st.sidebar.text_input("Preset name", key="save_preset_name")
    save_clicked = st.sidebar.button("Save as preset", disabled=(candidate is None or not save_name))
    if save_clicked and candidate is not None:
        try:
            p = save_preset(candidate, save_name)
            st.sidebar.success(f"Saved to {Path(p).name}")
        except Exception as e:  # noqa: BLE001
            st.sidebar.error(f"Save failed: {e}")

    # Persist the last valid config in session for subsequent reruns.
    if candidate is not None:
        st.session_state["current_config"] = candidate

    return candidate, run_clicked, save_name
