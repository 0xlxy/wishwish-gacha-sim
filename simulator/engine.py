"""NumPy-vectorized Monte Carlo engine for the gacha simulator.

Budget (PRD §4.2): 10k users × 30 days <= 10 s. No per-user Python loops.

Semantics (clarified during planning):
- Pity counter = pulls since last newly-acquired character. Resets on any pull
  that adds a new character (regardless of rarity). Otherwise increments.
- Pity triggers when pity_ctr >= pity_threshold - 1 before a pull, so the
  invariant "every `threshold`-pull window contains >= 1 new character"
  holds under the `unowned_any` rule.
- Soft pity: linearly ramps the combined probability of rare-and-above tiers
  (tiers[1:]) from base at soft_pity_start to 1.0 at soft_pity_full, holding
  the internal ratio between rare+ tiers fixed and pushing common probability
  down proportionally.
- Auto-bundle pricing: when a user's paid pulls for a day >= 10, each full
  block of 10 is priced at `ten_pull_cost_wish`; the remainder at
  `single_pull_cost_wish` each. The free pull is, well, free.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .config import SimConfig, config_hash
from .population import (
    Population,
    STOP_NEVER,
    STOP_ON_COMPLETE,
    STOP_ON_RARE,
    build_population,
)

OWNED_DTYPE = np.uint64  # supports up to 64 characters


# --------------------------------------------------------------------------- #
# Result container
# --------------------------------------------------------------------------- #
@dataclass
class SimResult:
    config: SimConfig
    config_hash: str
    users: pd.DataFrame            # one row per user
    events: pd.DataFrame           # one row per pull
    first_day: np.ndarray          # [N, num_chars], -1 if never obtained
    owned_by_day: np.ndarray       # [N, duration_days+1] ownership bitmask per day end
    spend_by_day: np.ndarray       # [N, duration_days] wish spent that day
    character_names: list[str]
    segment_names: list[str]
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def n_users(self) -> int:
        return len(self.users)

    @property
    def num_chars(self) -> int:
        return len(self.character_names)


# --------------------------------------------------------------------------- #
# Rarity-plan helpers
# --------------------------------------------------------------------------- #
def _build_rarity_plan(cfg: SimConfig) -> dict[str, Any]:
    series = cfg.series
    tiers = series.tiers
    char_tier_idx: list[int] = []
    tier_char_ranges: list[tuple[int, int]] = []
    tier_masks: list[int] = []
    pity_pool_mask = 0
    offset = 0
    for ti, t in enumerate(tiers):
        tier_char_ranges.append((offset, offset + t.character_count))
        mask = 0
        for j in range(t.character_count):
            char_tier_idx.append(ti)
            mask |= 1 << (offset + j)
        tier_masks.append(mask)
        if t.in_pity_pool:
            pity_pool_mask |= mask
        offset += t.character_count

    tier_probs = np.array([t.probability for t in tiers], dtype=np.float64)
    rare_plus_mask = 0
    for m in tier_masks[1:]:
        rare_plus_mask |= m
    # Rare-plus base probability (sum of tiers[1:])
    base_rare_plus_p = float(tier_probs[1:].sum()) if len(tiers) > 1 else 0.0
    # Within rare+, ratios stay constant under soft pity.
    if base_rare_plus_p > 0.0 and len(tiers) > 1:
        rare_plus_ratios = tier_probs[1:] / base_rare_plus_p
    else:
        rare_plus_ratios = np.array([], dtype=np.float64)

    return {
        "tier_probs": tier_probs,
        "tier_masks": np.array(tier_masks, dtype=OWNED_DTYPE),
        "tier_char_ranges": tier_char_ranges,
        "char_tier_idx": np.array(char_tier_idx, dtype=np.int8),
        "pity_pool_mask": OWNED_DTYPE(pity_pool_mask),
        "rare_plus_mask": OWNED_DTYPE(rare_plus_mask),
        "base_rare_plus_p": base_rare_plus_p,
        "rare_plus_ratios": rare_plus_ratios,
        "num_chars": offset,
        "num_tiers": len(tiers),
    }


# --------------------------------------------------------------------------- #
# Vectorized pull resolution
# --------------------------------------------------------------------------- #
def popcount64(x: np.ndarray) -> np.ndarray:
    """Vectorized 64-bit popcount — used both for owned-count rollups and
    by viz modules to derive per-day holdings from owned_by_day masks."""
    # SWAR trick on uint64.
    x = x.astype(np.uint64, copy=True)
    x = x - ((x >> np.uint64(1)) & np.uint64(0x5555555555555555))
    x = (x & np.uint64(0x3333333333333333)) + (
        (x >> np.uint64(2)) & np.uint64(0x3333333333333333)
    )
    x = (x + (x >> np.uint64(4))) & np.uint64(0x0F0F0F0F0F0F0F0F)
    x = (x * np.uint64(0x0101010101010101)) >> np.uint64(56)
    return x.astype(np.int32)


# Keep the old private alias so no internal caller breaks.
_popcount64 = popcount64


def _kth_set_bit(
    masks: np.ndarray, ks: np.ndarray, num_chars: int
) -> np.ndarray:
    """For each row, return the char index of the k-th set bit (0-indexed).

    masks: uint64 [M]; ks: int [M] with 0 <= ks[i] < popcount(masks[i]).
    Returns int16 [M].
    """
    # Build per-bit set indicator [M, num_chars].
    bit_idx = np.arange(num_chars, dtype=np.uint64)
    bits = ((masks[:, None] >> bit_idx[None, :]) & np.uint64(1)).astype(np.int8)
    cum = np.cumsum(bits, axis=1)  # 1-indexed count of set bits
    # We want the smallest col where cum == ks+1.
    target = ks + 1
    # Set non-matching to a large value; argmin along axis=1 of (cum < target)
    # equivalently: the first column with cum >= target and bit set.
    found = (cum == target[:, None]) & (bits == 1)
    # Guarantee at least one hit per row (caller ensures).
    idx = found.argmax(axis=1).astype(np.int16)
    return idx


# --------------------------------------------------------------------------- #
# Main entrypoint
# --------------------------------------------------------------------------- #
def run_simulation(cfg: SimConfig) -> SimResult:
    series = cfg.series
    draw = cfg.draw
    pop_cfg = cfg.population

    seed = pop_cfg.random_seed
    rng = np.random.default_rng(seed)

    plan = _build_rarity_plan(cfg)
    num_chars = plan["num_chars"]
    if num_chars > 64:
        raise ValueError("v1 supports up to 64 characters total")

    tier_probs = plan["tier_probs"]
    tier_masks = plan["tier_masks"]                 # [T] uint64
    rare_plus_mask = np.uint64(plan["rare_plus_mask"])
    pity_pool_mask = np.uint64(plan["pity_pool_mask"])
    base_rare_plus_p = plan["base_rare_plus_p"]
    rare_plus_ratios = plan["rare_plus_ratios"]
    num_tiers = plan["num_tiers"]

    all_char_mask = OWNED_DTYPE((1 << num_chars) - 1)
    population = build_population(pop_cfg, rng)
    N = population.n_users
    D = series.duration_days

    # Per-user state.
    owned = np.zeros(N, dtype=OWNED_DTYPE)
    pity_ctr = np.zeros(N, dtype=np.int32)
    spend_wish = np.zeros(N, dtype=np.int64)
    spend_by_day = np.zeros((N, D), dtype=np.int64)
    active = np.ones(N, dtype=bool)
    first_day = np.full((N, num_chars), -1, dtype=np.int32)
    owned_by_day = np.zeros((N, D + 1), dtype=OWNED_DTYPE)  # index 0 = start (empty)

    # Per-segment vectors broadcast to per-user for fast lookups.
    seg_idx = population.segment_idx.astype(np.int32)
    active_rate_u = population.daily_active_rate[seg_idx]
    paid_min_u = population.paid_min[seg_idx]
    paid_max_u = population.paid_max[seg_idx]
    stop_rule_u = population.stop_rule[seg_idx]

    # Event log buffers (chunked).
    ev_day: list[np.ndarray] = []
    ev_user: list[np.ndarray] = []
    ev_char: list[np.ndarray] = []
    ev_pity: list[np.ndarray] = []
    ev_new: list[np.ndarray] = []
    ev_paid: list[np.ndarray] = []  # whether this pull was paid (for pricing sanity)

    pity_threshold = int(draw.pity_threshold)
    soft_s = draw.soft_pity_start
    soft_f = draw.soft_pity_full
    has_soft = soft_s is not None and soft_f is not None

    free_per_day = int(draw.daily_free_draws)

    for day in range(D):
        # 1. Activation.
        active_today = active & (rng.random(N) < active_rate_u)

        # 2. Free + paid pull counts.
        free_today = np.where(active_today, free_per_day, 0).astype(np.int32)

        # Paid pulls: uniform int in [min, max] per user's segment range.
        span = np.maximum(paid_max_u - paid_min_u + 1, 1)
        paid_today = (rng.integers(0, span) + paid_min_u).astype(np.int32)
        # Mask: inactive, stopped, or segment has no paid range -> 0.
        zero_paid = (~active_today) | (paid_max_u == 0)
        paid_today[zero_paid] = 0

        pulls_today = free_today + paid_today
        # End-of-day bundle pricing.
        bundle_price = int(draw.ten_pull_cost_wish)
        single_price = int(draw.single_pull_cost_wish)
        bundles = paid_today // 10
        remainder = paid_today % 10
        day_spend = bundles * bundle_price + remainder * single_price
        spend_by_day[:, day] = day_spend
        spend_wish += day_spend

        max_pulls = int(pulls_today.max()) if pulls_today.size else 0
        remaining = pulls_today.copy()
        # Track which pulls within a day are paid (indexes 0..free-1 are free).
        # paid_this_pull[i] = True if current pull index i for this user is paid.
        # The k-th pull index (0-based) is paid iff k >= free_per_day.

        for k in range(max_pulls):
            pull_mask = remaining > 0
            if not pull_mask.any():
                break
            users = np.flatnonzero(pull_mask)
            M = users.shape[0]

            u_owned = owned[users]
            u_pity = pity_ctr[users]

            # Effective rare-plus probability per user (soft pity).
            if has_soft and num_tiers > 1:
                # Linear ramp from base at soft_s to 1.0 at soft_f, inclusive.
                t = np.clip(
                    (u_pity - soft_s) / max(soft_f - soft_s, 1),
                    0.0, 1.0,
                )
                # Only ramp once ctr >= soft_s.
                t = np.where(u_pity >= soft_s, t, 0.0)
                eff_rare_p = base_rare_plus_p + (1.0 - base_rare_plus_p) * t
            else:
                eff_rare_p = np.full(M, base_rare_plus_p, dtype=np.float64)

            # 1. Sample tier for non-pity pulls.
            r_tier = rng.random(M)
            is_rare_plus = r_tier < eff_rare_p

            # Among rare+, choose which specific rare+ tier using ratios.
            if num_tiers > 2:
                r_sub = rng.random(M)
                cum = np.cumsum(rare_plus_ratios)
                # For each user, find first cum >= r_sub.
                sub_tier = (cum[None, :] >= r_sub[:, None]).argmax(axis=1)
            else:
                sub_tier = np.zeros(M, dtype=np.int64)  # only one rare tier

            # Tier index per user (0 = common; 1+ = rare+).
            chosen_tier = np.where(is_rare_plus, 1 + sub_tier, 0).astype(np.int32)

            # 2. Pity trigger check.
            trigger = u_pity >= (pity_threshold - 1)

            # Build the candidate mask per pull (what characters could be sampled).
            # Default: the chosen tier's mask.
            cand_mask = tier_masks[chosen_tier]

            if trigger.any():
                trig_idx = np.flatnonzero(trigger)
                trig_owned = u_owned[trig_idx]
                # Apply guarantee rule.
                if draw.pity_guarantee == "unowned_any":
                    target = pity_pool_mask & ~trig_owned & all_char_mask
                    # Fallback if user owns everything in pity pool: use pity pool anyway.
                    empty = target == 0
                    target = np.where(empty, pity_pool_mask & all_char_mask, target)
                elif draw.pity_guarantee == "unowned_rare_or_above":
                    target = rare_plus_mask & ~trig_owned & all_char_mask
                    # Fallback: unowned from anywhere, then any rare+.
                    empty = target == 0
                    fb1 = pity_pool_mask & ~trig_owned & all_char_mask
                    target = np.where(empty, fb1, target)
                    empty = target == 0
                    target = np.where(empty, rare_plus_mask & all_char_mask, target)
                elif draw.pity_guarantee == "rare_or_above":
                    target = np.full(trig_idx.shape[0], rare_plus_mask, dtype=OWNED_DTYPE)
                else:
                    raise ValueError(draw.pity_guarantee)
                cand_mask[trig_idx] = target
                # Override chosen_tier for trigger users so accounting is consistent:
                # set tier to the highest bit tier represented (rare+ for rare_or_above,
                # otherwise leave unchanged — character-to-tier lookup resolves it later).
                # We don't actually need chosen_tier for anything downstream, so skip.

            # 3. Sample one character uniformly within cand_mask.
            popcnt = _popcount64(cand_mask)
            # cand_mask should never be empty because tiers have >=1 char each
            # and pity fallbacks ensure a non-empty mask.
            if (popcnt == 0).any():
                raise RuntimeError("empty candidate mask during pull resolution")
            k_sel = (rng.random(M) * popcnt).astype(np.int32)  # 0 <= k < popcount
            char_idx = _kth_set_bit(cand_mask, k_sel, num_chars)

            # 4. Update owned/pity.
            bit = (np.uint64(1) << char_idx.astype(np.uint64))
            was_new = ((u_owned & bit) == 0).astype(np.int8)
            new_owned = u_owned | bit
            owned[users] = new_owned

            # Record first_day where was_new.
            new_mask_users = users[was_new == 1]
            new_mask_chars = char_idx[was_new == 1]
            # Only set if -1 currently (should always be -1 for was_new==1, but safe).
            fd_slice = first_day[new_mask_users, new_mask_chars]
            unset = fd_slice == -1
            if unset.any():
                first_day[
                    new_mask_users[unset], new_mask_chars[unset]
                ] = day

            # Reset / increment pity.
            new_pity = np.where(was_new == 1, 0, u_pity + 1)
            pity_ctr[users] = new_pity

            # 5. Track paid flag for event log.
            # Free pulls come first: index k < free_today[user] is free.
            user_free = free_today[users]
            is_paid = (k >= user_free).astype(np.int8)

            # 6. Append to event log.
            ev_day.append(np.full(M, day, dtype=np.int16))
            ev_user.append(users.astype(np.int32))
            ev_char.append(char_idx.astype(np.int16))
            ev_pity.append(trigger.astype(np.int8))
            ev_new.append(was_new)
            ev_paid.append(is_paid)

            remaining[users] -= 1

        # End-of-day stop-rule evaluation.
        owned_by_day[:, day + 1] = owned
        if (stop_rule_u == STOP_ON_COMPLETE).any():
            complete = owned == all_char_mask
            stop_mask = (stop_rule_u == STOP_ON_COMPLETE) & complete
            active[stop_mask] = False
        if (stop_rule_u == STOP_ON_RARE).any():
            has_rare = (owned & rare_plus_mask) != 0
            stop_mask = (stop_rule_u == STOP_ON_RARE) & has_rare
            active[stop_mask] = False

    # Stitch event log.
    if ev_day:
        events = pd.DataFrame({
            "day": np.concatenate(ev_day),
            "user_idx": np.concatenate(ev_user),
            "char_idx": np.concatenate(ev_char),
            "was_pity": np.concatenate(ev_pity).astype(bool),
            "was_new": np.concatenate(ev_new).astype(bool),
            "was_paid": np.concatenate(ev_paid).astype(bool),
        })
        # Sort by (user, day, pull order) — concatenation already respects day/k order per user.
        events = events.sort_values(
            ["user_idx", "day"], kind="stable"
        ).reset_index(drop=True)
    else:
        events = pd.DataFrame(
            columns=["day", "user_idx", "char_idx", "was_pity", "was_new", "was_paid"]
        )

    # Per-user summary.
    owned_count = _popcount64(owned)
    total_pulls = events.groupby("user_idx").size().reindex(range(N), fill_value=0).to_numpy()
    paid_pulls = (
        events[events["was_paid"]].groupby("user_idx").size().reindex(range(N), fill_value=0).to_numpy()
    )
    pity_triggers = (
        events[events["was_pity"]].groupby("user_idx").size().reindex(range(N), fill_value=0).to_numpy()
    )

    # First-rare day per user.
    first_rare_day = np.full(N, -1, dtype=np.int32)
    days_to_complete = np.full(N, -1, dtype=np.int32)
    if num_tiers > 1:
        rare_cols = np.where(plan["char_tier_idx"] != 0)[0]
        # First day any rare char obtained.
        rare_days = first_day[:, rare_cols]
        rare_days_masked = np.where(rare_days < 0, 10**9, rare_days)
        min_rare = rare_days_masked.min(axis=1)
        first_rare_day = np.where(min_rare >= 10**9, -1, min_rare).astype(np.int32)

    # Day of completion.
    first_day_masked = np.where(first_day < 0, 10**9, first_day)
    max_first_day = first_day_masked.max(axis=1)
    days_to_complete = np.where(max_first_day >= 10**9, -1, max_first_day).astype(np.int32)

    # First-rare pull (pull index in ordered events).
    first_rare_pull = np.full(N, -1, dtype=np.int32)
    if num_tiers > 1:
        rare_event_mask = events["char_idx"].isin(rare_cols.tolist()) & events["was_new"]
        if rare_event_mask.any():
            rare_events = events[rare_event_mask].copy()
            rare_events["pull_order"] = rare_events.groupby("user_idx").cumcount()
            first_rare_events = rare_events[rare_events["pull_order"] == 0]
            # Need pull-index-within-user. Compute cumcount on the full events.
            full_order = events.groupby("user_idx").cumcount()
            first_rare_events = first_rare_events.assign(
                pull_idx=full_order.loc[first_rare_events.index].to_numpy()
            )
            first_rare_pull[first_rare_events["user_idx"].to_numpy()] = (
                first_rare_events["pull_idx"].to_numpy().astype(np.int32)
            )

    users_df = pd.DataFrame({
        "user_idx": np.arange(N),
        "segment": np.array(population.segment_names, dtype=object)[seg_idx],
        "segment_idx": seg_idx,
        "owned_count": owned_count,
        "owned_mask": owned.astype(np.int64),  # DataFrame-friendly
        "total_pulls": total_pulls,
        "paid_pulls": paid_pulls,
        "pity_triggers": pity_triggers,
        "spend_wish": spend_wish,
        "spend_usd": spend_wish / draw.wish_per_usd,
        "first_rare_day": first_rare_day,
        "first_rare_pull": first_rare_pull,
        "days_to_complete": days_to_complete,
    })
    # One boolean column per character for CSV export convenience.
    for ci, cname in enumerate(series.all_character_names):
        bit = np.uint64(1) << np.uint64(ci)
        users_df[f"owns_{cname}"] = ((owned & bit) != 0)

    return SimResult(
        config=cfg,
        config_hash=config_hash(cfg),
        users=users_df,
        events=events,
        first_day=first_day,
        owned_by_day=owned_by_day,
        spend_by_day=spend_by_day,
        character_names=series.all_character_names,
        segment_names=[s.name for s in pop_cfg.segments],
        meta={
            "tier_names": [t.name for t in series.tiers],
            "char_tier_idx": plan["char_tier_idx"],
            "rare_plus_mask": int(rare_plus_mask),
            "pity_pool_mask": int(pity_pool_mask),
            "num_chars": num_chars,
            "duration_days": D,
        },
    )
