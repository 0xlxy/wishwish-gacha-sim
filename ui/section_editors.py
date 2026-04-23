"""Inline config editors embedded next to each dashboard section.

Each returns the updated SimConfig (or the original if the edits don't parse).
Writes are persisted via ``st.session_state['current_config']``.
"""
from __future__ import annotations

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
)


STOP_RULES = ["never_stop", "stop_on_complete", "stop_on_rare"]
PITY_RULES = ["unowned_any", "unowned_rare_or_above", "rare_or_above"]


def _tiers_df(series: SeriesConfig) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "name": t.name,
                "count": t.character_count,
                "probability": t.probability,
                "pity_pool": t.in_pity_pool,
                "characters": ", ".join(t.character_names),
            }
            for t in series.tiers
        ]
    )


def _tiers_from_df(df: pd.DataFrame) -> list[RarityTier]:
    tiers: list[RarityTier] = []
    for _, row in df.iterrows():
        if pd.isna(row.get("name")) or str(row["name"]).strip() == "":
            continue
        names_raw = str(row.get("characters", "") or "")
        names = [s.strip() for s in names_raw.split(",") if s.strip()]
        tiers.append(
            RarityTier(
                name=str(row["name"]),
                character_count=int(row["count"]),
                probability=float(row["probability"]),
                in_pity_pool=bool(row["pity_pool"]),
                character_names=names,
            )
        )
    return tiers


def _segments_df(pop: PopulationConfig) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "name": s.name,
                "share": s.population_share,
                "dau_rate": s.daily_active_rate,
                "paid_min": s.extra_paid_pulls_min,
                "paid_max": s.extra_paid_pulls_max,
                "stop_rule": s.stop_rule,
            }
            for s in pop.segments
        ]
    )


def _segments_from_df(df: pd.DataFrame) -> list[UserSegment]:
    segs: list[UserSegment] = []
    for _, row in df.iterrows():
        if pd.isna(row.get("name")) or str(row["name"]).strip() == "":
            continue
        segs.append(
            UserSegment(
                name=str(row["name"]),
                population_share=float(row["share"]),
                daily_active_rate=float(row["dau_rate"]),
                extra_paid_pulls_min=int(row["paid_min"]),
                extra_paid_pulls_max=int(row["paid_max"]),
                stop_rule=str(row["stop_rule"]),
            )
        )
    return segs


def _apply(cfg: SimConfig, **patches: Any) -> SimConfig | None:
    """Patch fields on a deep-copy of cfg. Returns None on validation fail."""
    try:
        series_kwargs = {}
        draw_kwargs = {}
        pop_kwargs = {}
        for k, v in patches.items():
            if k.startswith("series."):
                series_kwargs[k.removeprefix("series.")] = v
            elif k.startswith("draw."):
                draw_kwargs[k.removeprefix("draw.")] = v
            elif k.startswith("population."):
                pop_kwargs[k.removeprefix("population.")] = v

        new_series = cfg.series.model_copy(update=series_kwargs)
        new_draw = cfg.draw.model_copy(update=draw_kwargs)
        new_pop = cfg.population.model_copy(update=pop_kwargs)

        # Trigger revalidation by constructing fresh.
        return SimConfig(
            name=cfg.name,
            series=SeriesConfig(**new_series.model_dump()),
            draw=DrawConfig(**new_draw.model_dump()),
            population=PopulationConfig(**new_pop.model_dump()),
        )
    except (ValidationError, ValueError) as e:
        st.warning(f"Invalid edit: {e}")
        return None


# --------------------------------------------------------------------------- #
# Public editors
# --------------------------------------------------------------------------- #
def tiers_editor(cfg: SimConfig, key: str = "tiers_editor") -> SimConfig:
    """Rarity tiers editor. Renders inline."""
    df = _tiers_df(cfg.series)
    edited = st.data_editor(
        df,
        key=key,
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        column_config={
            "name": st.column_config.TextColumn("Tier", width="small"),
            "count": st.column_config.NumberColumn("# chars", min_value=1, step=1, width="small"),
            "probability": st.column_config.NumberColumn(
                "Probability", format="%.4f", min_value=0.0, max_value=1.0, width="small"
            ),
            "pity_pool": st.column_config.CheckboxColumn("In pity pool", width="small"),
            "characters": st.column_config.TextColumn(
                "Character names (comma-separated)", width="large"
            ),
        },
    )
    try:
        new_tiers = _tiers_from_df(edited)
        new = _apply(cfg, **{"series.tiers": new_tiers})
        if new is not None:
            st.session_state["current_config"] = new
            return new
    except (ValidationError, ValueError) as e:
        st.warning(f"Tier edit rejected: {e}")
    return cfg


def segments_editor(cfg: SimConfig, key: str = "segments_editor") -> SimConfig:
    """Population-segment editor."""
    df = _segments_df(cfg.population)
    edited = st.data_editor(
        df,
        key=key,
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        column_config={
            "name": st.column_config.TextColumn("Segment", width="small"),
            "share": st.column_config.NumberColumn(
                "Pop. share", format="%.3f", min_value=0.0, max_value=1.0, width="small"
            ),
            "dau_rate": st.column_config.NumberColumn(
                "DAU rate", format="%.2f", min_value=0.0, max_value=1.0, width="small"
            ),
            "paid_min": st.column_config.NumberColumn("Paid min/day", min_value=0, step=1, width="small"),
            "paid_max": st.column_config.NumberColumn("Paid max/day", min_value=0, step=1, width="small"),
            "stop_rule": st.column_config.SelectboxColumn(
                "Stop rule", options=STOP_RULES, width="medium"
            ),
        },
    )
    try:
        new_segs = _segments_from_df(edited)
        new = _apply(cfg, **{"population.segments": new_segs})
        if new is not None:
            st.session_state["current_config"] = new
            return new
    except (ValidationError, ValueError) as e:
        st.warning(f"Segment edit rejected: {e}")
    return cfg


def draw_mechanics_editor(cfg: SimConfig, key: str = "draw_editor") -> SimConfig:
    """Inline editor for pull costs + pity rules."""
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        free = st.number_input(
            "Daily free pulls",
            min_value=0, max_value=20,
            value=cfg.draw.daily_free_draws,
            key=f"{key}_free",
        )
    with c2:
        single = st.number_input(
            "Single pull (wish)",
            min_value=0, value=cfg.draw.single_pull_cost_wish, step=10,
            key=f"{key}_single",
        )
    with c3:
        ten = st.number_input(
            "10-pull (wish)",
            min_value=0, value=cfg.draw.ten_pull_cost_wish, step=10,
            key=f"{key}_ten",
        )
    with c4:
        rate = st.number_input(
            "Wish / USD",
            min_value=1, value=cfg.draw.wish_per_usd, step=1,
            key=f"{key}_rate",
        )

    c1, c2, c3 = st.columns([1, 2, 2])
    with c1:
        thr = st.number_input(
            "Pity threshold",
            min_value=1, max_value=200,
            value=cfg.draw.pity_threshold,
            key=f"{key}_thr",
        )
    with c2:
        rule = st.selectbox(
            "Pity guarantee",
            options=PITY_RULES,
            index=PITY_RULES.index(cfg.draw.pity_guarantee),
            key=f"{key}_rule",
        )
    with c3:
        soft_on = st.checkbox(
            "Soft pity (linear ramp)",
            value=(cfg.draw.soft_pity_start is not None),
            key=f"{key}_soft_on",
        )

    soft_s = cfg.draw.soft_pity_start
    soft_f = cfg.draw.soft_pity_full
    if soft_on:
        sc1, sc2 = st.columns(2)
        with sc1:
            soft_s = st.number_input(
                "Soft start",
                min_value=0, max_value=int(thr) - 1,
                value=soft_s or 0,
                key=f"{key}_soft_s",
            )
        with sc2:
            soft_f = st.number_input(
                "Soft full",
                min_value=int(soft_s) + 1, max_value=int(thr),
                value=soft_f or int(thr),
                key=f"{key}_soft_f",
            )
    else:
        soft_s = None
        soft_f = None

    patches = {
        "draw.daily_free_draws": int(free),
        "draw.single_pull_cost_wish": int(single),
        "draw.ten_pull_cost_wish": int(ten),
        "draw.wish_per_usd": int(rate),
        "draw.pity_threshold": int(thr),
        "draw.pity_guarantee": rule,
        "draw.soft_pity_start": soft_s,
        "draw.soft_pity_full": soft_f,
    }
    new = _apply(cfg, **patches)
    if new is not None:
        st.session_state["current_config"] = new
        return new
    return cfg
