"""Sanity tests for the vectorized simulation engine.

Philosophy: at small N with a fixed seed, run-to-run determinism is
bit-identical; at larger N (few thousand), Monte Carlo estimates match
closed-form expectations to a few percent.
"""
from __future__ import annotations

import numpy as np
import pytest

from simulator.config import (
    DrawConfig,
    PopulationConfig,
    RarityTier,
    SeriesConfig,
    SimConfig,
    UserSegment,
    config_hash,
    load_preset,
)
from simulator.engine import run_simulation


def _single_segment_cfg(
    *,
    total_users: int,
    duration: int,
    free_per_day: int,
    paid_min: int,
    paid_max: int,
    rare_p: float = 0.04,
    pity_threshold: int = 10,
    seed: int = 42,
    active_rate: float = 1.0,
) -> SimConfig:
    return SimConfig(
        name="test",
        series=SeriesConfig(
            duration_days=duration,
            tiers=[
                RarityTier(
                    name="Common",
                    character_count=8,
                    probability=1.0 - rare_p,
                    character_names=[f"C{i}" for i in range(8)],
                ),
                RarityTier(
                    name="Rare",
                    character_count=1,
                    probability=rare_p,
                    character_names=["R"],
                ),
            ],
        ),
        draw=DrawConfig(
            daily_free_draws=free_per_day,
            single_pull_cost_wish=80,
            ten_pull_cost_wish=720,
            wish_per_usd=100,
            pity_threshold=pity_threshold,
            pity_guarantee="unowned_any",
        ),
        population=PopulationConfig(
            total_users=total_users,
            segments=[
                UserSegment(
                    name="Solo",
                    population_share=1.0,
                    daily_active_rate=active_rate,
                    extra_paid_pulls_min=paid_min,
                    extra_paid_pulls_max=paid_max,
                    stop_rule="never_stop",
                )
            ],
            random_seed=seed,
        ),
    )


def test_determinism_same_seed_bit_identical():
    cfg = _single_segment_cfg(
        total_users=500, duration=30, free_per_day=1, paid_min=0, paid_max=0
    )
    r1 = run_simulation(cfg)
    r2 = run_simulation(cfg)
    assert r1.config_hash == r2.config_hash
    assert (r1.users["spend_wish"] == r2.users["spend_wish"]).all()
    assert (r1.users["owned_mask"] == r2.users["owned_mask"]).all()
    assert (r1.users["total_pulls"] == r2.users["total_pulls"]).all()


def test_determinism_hash_matches_config():
    cfg = _single_segment_cfg(
        total_users=100, duration=10, free_per_day=1, paid_min=0, paid_max=0
    )
    r = run_simulation(cfg)
    assert r.config_hash == config_hash(cfg)


def test_bundle_pricing():
    """Paid pulls use bundle rate when >= 10 per day."""
    cfg = _single_segment_cfg(
        total_users=200,
        duration=1,
        free_per_day=0,
        paid_min=10,
        paid_max=10,  # exactly 10 paid pulls => 1 bundle of 720
        pity_threshold=1000,  # don't interfere
    )
    r = run_simulation(cfg)
    # Every user made exactly 10 paid pulls -> 720 wish (one bundle), no remainder.
    assert (r.users["spend_wish"] == 720).all()

    # Now 12 paid -> 1 bundle (720) + 2 singles (160) = 880
    cfg = _single_segment_cfg(
        total_users=200,
        duration=1,
        free_per_day=0,
        paid_min=12,
        paid_max=12,
        pity_threshold=1000,
    )
    r = run_simulation(cfg)
    assert (r.users["spend_wish"] == 880).all()

    # 5 paid -> 5 singles = 400 wish
    cfg = _single_segment_cfg(
        total_users=200,
        duration=1,
        free_per_day=0,
        paid_min=5,
        paid_max=5,
        pity_threshold=1000,
    )
    r = run_simulation(cfg)
    assert (r.users["spend_wish"] == 400).all()


def test_rare_frequency_matches_base_probability():
    """Disable pity; empirical rare rate should be ~4%."""
    cfg = _single_segment_cfg(
        total_users=2000,
        duration=30,
        free_per_day=10,  # 300 pulls per user
        paid_min=0,
        paid_max=0,
        rare_p=0.04,
        pity_threshold=10**9,  # effectively disable pity
        active_rate=1.0,
    )
    r = run_simulation(cfg)
    ev = r.events
    rare_mask = ev["char_idx"] == 8  # rare tier is the 9th character
    empirical = float(rare_mask.mean())
    # 2000 * 300 pulls = 600k Bernoulli(0.04) draws; tolerance ~1% absolute.
    assert abs(empirical - 0.04) < 0.005, f"empirical rare rate {empirical}"


def test_collection_coupon_collector_small():
    """With pity disabled, many pulls, expect near-100% completion."""
    cfg = _single_segment_cfg(
        total_users=500,
        duration=1,
        free_per_day=200,  # way more than enough
        paid_min=0,
        paid_max=0,
        pity_threshold=10**9,
    )
    r = run_simulation(cfg)
    completion = (r.users["owned_count"] == 9).mean()
    assert completion > 0.95, f"completion {completion}"


def test_preset_loads_and_runs_fast():
    """Default preset — correctness check on overall shape."""
    cfg = load_preset("mengjing_v1")
    r = run_simulation(cfg)
    assert r.n_users == cfg.population.total_users
    # Whales and dolphins should complete at very high rate.
    whale_complete = (
        r.users[r.users["segment"] == "Whale"]["owned_count"].mean() / 9
    )
    assert whale_complete > 0.95
