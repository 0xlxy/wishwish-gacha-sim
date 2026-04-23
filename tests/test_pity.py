"""Pity-system correctness tests."""
from __future__ import annotations

import numpy as np

from simulator.config import (
    DrawConfig,
    PopulationConfig,
    RarityTier,
    SeriesConfig,
    SimConfig,
    UserSegment,
)
from simulator.engine import run_simulation


def _adversarial_cfg(
    *,
    total_users: int = 200,
    pity_threshold: int = 5,
    pity_rule: str = "unowned_any",
    duration: int = 5,
    rare_p: float = 0.04,
    char_count_common: int = 8,
    seed: int = 123,
) -> SimConfig:
    return SimConfig(
        name="pity-test",
        series=SeriesConfig(
            duration_days=duration,
            tiers=[
                RarityTier(
                    name="Common",
                    character_count=char_count_common,
                    probability=1.0 - rare_p,
                ),
                RarityTier(
                    name="Rare",
                    character_count=1,
                    probability=rare_p,
                ),
            ],
        ),
        draw=DrawConfig(
            daily_free_draws=1,
            single_pull_cost_wish=80,
            ten_pull_cost_wish=720,
            wish_per_usd=100,
            pity_threshold=pity_threshold,
            pity_guarantee=pity_rule,
        ),
        population=PopulationConfig(
            total_users=total_users,
            segments=[
                UserSegment(
                    name="Only",
                    population_share=1.0,
                    daily_active_rate=1.0,
                    extra_paid_pulls_min=pity_threshold * 3,
                    extra_paid_pulls_max=pity_threshold * 3,
                    stop_rule="never_stop",
                )
            ],
            random_seed=seed,
        ),
    )


def _assert_pity_window_invariant(result, threshold: int) -> None:
    """For every user, every `threshold`-pull window must contain >=1 new char,
    unless the user had already collected every character in the pity pool
    before the window began (in which case pity cannot deliver anything new)."""
    num_chars = result.meta["num_chars"]
    pity_pool_mask = int(result.meta["pity_pool_mask"])
    all_pity_owned = pity_pool_mask  # target mask == pool mask when fully owned
    ev = result.events.sort_values(["user_idx", "day"]).reset_index(drop=True)
    ev["pull_idx"] = ev.groupby("user_idx").cumcount()
    for user_idx, grp in ev.groupby("user_idx"):
        new_flags = grp["was_new"].to_numpy().astype(np.int8)
        char_idx = grp["char_idx"].to_numpy().astype(np.int64)
        n = len(new_flags)
        if n < threshold:
            continue
        # Reconstruct per-pull owned-mask (ownership AFTER the pull).
        owned_after = np.zeros(n, dtype=np.int64)
        cur = 0
        for i, c in enumerate(char_idx):
            cur |= (1 << int(c))
            owned_after[i] = cur
        # owned_before[i] == owned_after[i-1] (or 0 for i==0)
        owned_before = np.concatenate([[0], owned_after[:-1]])
        csum = np.cumsum(new_flags)
        pref = np.concatenate([[0], csum])
        for i in range(threshold - 1, n):
            start = i - threshold + 1
            window_new = pref[i + 1] - pref[start]
            if window_new >= 1:
                continue
            # Window has zero new pulls. Acceptable only if user was already
            # complete-pool at the start of the window.
            if (owned_before[start] & all_pity_owned) != all_pity_owned:
                raise AssertionError(
                    f"user {user_idx}: {threshold}-pull window starting at "
                    f"pull {start} has 0 new chars but user was not complete"
                )


def test_pity_invariant_unowned_any_small_threshold():
    cfg = _adversarial_cfg(pity_threshold=5, total_users=300, duration=4)
    r = run_simulation(cfg)
    _assert_pity_window_invariant(r, 5)


def test_pity_invariant_default_threshold_on_preset():
    from simulator.config import load_preset

    cfg = load_preset("mengjing_v1")
    r = run_simulation(cfg)
    _assert_pity_window_invariant(r, cfg.draw.pity_threshold)


def test_pity_trigger_flagged_at_threshold():
    """When pity_ctr >= threshold-1, trigger flag must be true on that pull."""
    cfg = _adversarial_cfg(pity_threshold=3, total_users=50, duration=2)
    r = run_simulation(cfg)
    ev = r.events.sort_values(["user_idx", "day"]).reset_index(drop=True)
    # Replay pity_ctr per user; check every pull's was_pity matches expectation.
    for uid, grp in ev.groupby("user_idx"):
        pity_ctr = 0
        for _, row in grp.iterrows():
            expected = pity_ctr >= (cfg.draw.pity_threshold - 1)
            assert bool(row["was_pity"]) == expected, (
                f"user {uid}: pity flag mismatch (ctr={pity_ctr}, got {row['was_pity']})"
            )
            if row["was_new"]:
                pity_ctr = 0
            else:
                pity_ctr += 1


def test_pity_rare_or_above_always_rare_on_trigger():
    """Under rare_or_above, every pity trigger must deliver a rare-tier character."""
    cfg = _adversarial_cfg(pity_threshold=3, pity_rule="rare_or_above", duration=3)
    r = run_simulation(cfg)
    tier_idx = r.meta["char_tier_idx"]
    ev = r.events
    pity_pulls = ev[ev["was_pity"]]
    if len(pity_pulls) == 0:
        return  # nothing to assert
    tier_of_pity = tier_idx[pity_pulls["char_idx"].to_numpy()]
    assert (tier_of_pity != 0).all(), "rare_or_above rule gave a common on pity"


def test_pity_unowned_rare_or_above_prefers_rare_unowned():
    """unowned_rare_or_above: when user hasn't got rare yet, pity must deliver rare."""
    cfg = _adversarial_cfg(
        pity_threshold=3, pity_rule="unowned_rare_or_above", duration=2
    )
    r = run_simulation(cfg)
    tier_idx = r.meta["char_tier_idx"]
    ev = r.events.sort_values(["user_idx", "day"]).reset_index(drop=True)
    ev["pull_idx"] = ev.groupby("user_idx").cumcount()

    for uid, grp in ev.groupby("user_idx"):
        owned = 0
        rare_mask = 0
        for c, ti in enumerate(tier_idx):
            if ti != 0:
                rare_mask |= 1 << c
        for _, row in grp.iterrows():
            if bool(row["was_pity"]):
                # If user has no rare yet, this pity MUST deliver a rare.
                has_rare = bool(owned & rare_mask)
                if not has_rare:
                    assert int(tier_idx[int(row["char_idx"])]) != 0, (
                        f"user {uid} had no rare and pity delivered common"
                    )
            owned |= 1 << int(row["char_idx"])
