"""Segment sampling for the population.

Assigns each of `total_users` to exactly one segment in proportion to each
segment's `population_share`. Uses a deterministic stride-based allocation
(seeded shuffle) so that share rounding is exact and runs are reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import PopulationConfig, UserSegment


@dataclass(frozen=True)
class Population:
    segment_idx: np.ndarray           # shape [N], int8, value in [0, num_segments)
    segment_names: list[str]
    daily_active_rate: np.ndarray     # shape [num_segments]
    paid_min: np.ndarray              # shape [num_segments], int
    paid_max: np.ndarray              # shape [num_segments], int
    stop_rule: np.ndarray             # shape [num_segments], int8 (see StopRuleCode)

    @property
    def n_users(self) -> int:
        return int(self.segment_idx.shape[0])


# Stop-rule integer codes shared with engine.
STOP_NEVER = 0
STOP_ON_COMPLETE = 1
STOP_ON_RARE = 2

_STOP_CODE = {
    "never_stop": STOP_NEVER,
    "stop_on_complete": STOP_ON_COMPLETE,
    "stop_on_rare": STOP_ON_RARE,
}


def _exact_counts(total: int, shares: list[float]) -> list[int]:
    """Allocate `total` integers to buckets so sums match total exactly."""
    raw = [total * s for s in shares]
    floored = [int(x) for x in raw]
    remainder = total - sum(floored)
    # Give leftover units to segments with largest fractional parts.
    fracs = sorted(
        range(len(shares)), key=lambda i: raw[i] - floored[i], reverse=True
    )
    for i in fracs[:remainder]:
        floored[i] += 1
    return floored


def build_population(cfg: PopulationConfig, rng: np.random.Generator) -> Population:
    segments: list[UserSegment] = cfg.segments
    counts = _exact_counts(cfg.total_users, [s.population_share for s in segments])

    seg_idx = np.empty(cfg.total_users, dtype=np.int8)
    pos = 0
    for i, n in enumerate(counts):
        seg_idx[pos : pos + n] = i
        pos += n
    # Shuffle so segment ordering is random; rng is shared with engine for determinism.
    rng.shuffle(seg_idx)

    return Population(
        segment_idx=seg_idx,
        segment_names=[s.name for s in segments],
        daily_active_rate=np.array([s.daily_active_rate for s in segments], dtype=np.float64),
        paid_min=np.array([s.extra_paid_pulls_min for s in segments], dtype=np.int32),
        paid_max=np.array([s.extra_paid_pulls_max for s in segments], dtype=np.int32),
        stop_rule=np.array([_STOP_CODE[s.stop_rule] for s in segments], dtype=np.int8),
    )
