"""Compact always-visible row for the parameters the user tunes most often.

Rebalances rarity probabilities whenever the Rare slider moves so the tier
weights still sum to 1.0; keeps the rest of the config (segments, character
names, ...) intact.
"""
from __future__ import annotations

import streamlit as st
from pydantic import ValidationError

from simulator.config import SimConfig


def inline_params(cfg: SimConfig) -> SimConfig:
    c1, c2, c3, c4 = st.columns(4)

    # The "rarest" tier is conventionally the last one. Slider nudges it; all
    # other tiers are rescaled so probabilities still sum to 1. Integer-backed
    # (whole percent) to avoid Streamlit's float-step rounding.
    rarest = cfg.series.tiers[-1]
    with c1:
        rare_pct = st.slider(
            f"{rarest.name} probability",
            min_value=1,
            max_value=50,
            value=int(round(float(rarest.probability) * 100)),
            step=1,
            format="%d%%",
            key="pb_rare_p",
            help="Rarest-tier probability. For sub-percent tweaks, use the "
                 "Advanced configuration expander below.",
        )
    rare_p = rare_pct / 100.0
    with c2:
        pity_thr = st.number_input(
            "Pity threshold",
            min_value=1,
            max_value=200,
            value=int(cfg.draw.pity_threshold),
            step=1,
            key="pb_pity",
        )
    with c3:
        daily_free = st.number_input(
            "Daily free pulls",
            min_value=0,
            max_value=20,
            value=int(cfg.draw.daily_free_draws),
            step=1,
            key="pb_daily_free",
        )
    with c4:
        duration = st.number_input(
            "Duration (days)",
            min_value=1,
            max_value=365,
            value=int(cfg.series.duration_days),
            step=1,
            key="pb_duration",
        )

    # Rebuild config with the tweaks, rescaling other tiers proportionally.
    data = cfg.model_dump()
    tiers = data["series"]["tiers"]
    new_rare = float(rare_p)
    old_rare = float(tiers[-1]["probability"])
    tiers[-1]["probability"] = new_rare
    remaining = max(0.0, 1.0 - new_rare)
    head_sum = sum(t["probability"] for t in tiers[:-1])
    if head_sum > 0 and len(tiers) > 1:
        scale = remaining / head_sum
        for t in tiers[:-1]:
            t["probability"] = round(t["probability"] * scale, 10)
    # Last-mile rounding fix so the sum is exactly 1.
    s = sum(t["probability"] for t in tiers)
    if abs(s - 1.0) > 1e-9:
        tiers[-1]["probability"] = round(
            tiers[-1]["probability"] + (1.0 - s), 10
        )

    data["draw"]["pity_threshold"] = int(pity_thr)
    data["draw"]["daily_free_draws"] = int(daily_free)
    data["series"]["duration_days"] = int(duration)

    try:
        updated = SimConfig.model_validate(data)
        st.session_state["current_config"] = updated
        return updated
    except (ValidationError, ValueError) as e:
        st.warning(f"Invalid parameters: {e}")
        return cfg
