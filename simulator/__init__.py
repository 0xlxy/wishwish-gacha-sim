"""Monte Carlo gacha simulator core."""
from .config import (
    SimConfig,
    SeriesConfig,
    DrawConfig,
    PopulationConfig,
    UserSegment,
    RarityTier,
    load_preset,
    save_preset,
    config_hash,
)
from .engine import run_simulation, SimResult

__all__ = [
    "SimConfig",
    "SeriesConfig",
    "DrawConfig",
    "PopulationConfig",
    "UserSegment",
    "RarityTier",
    "load_preset",
    "save_preset",
    "config_hash",
    "run_simulation",
    "SimResult",
]
