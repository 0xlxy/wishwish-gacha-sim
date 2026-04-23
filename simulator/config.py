"""Pydantic configuration models for the gacha simulator.

See PRD §5. Adds validators for probability sums, segment shares, and soft-pity
consistency.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator, field_validator

PROB_TOL = 1e-6

PityGuarantee = Literal["unowned_any", "unowned_rare_or_above", "rare_or_above"]
StopRule = Literal["never_stop", "stop_on_complete", "stop_on_rare"]


class RarityTier(BaseModel):
    name: str
    character_count: int = Field(..., ge=1)
    probability: float = Field(..., ge=0.0, le=1.0)
    in_pity_pool: bool = True
    character_names: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _names_match_count(self) -> "RarityTier":
        if self.character_names and len(self.character_names) != self.character_count:
            raise ValueError(
                f"tier '{self.name}': character_names length "
                f"({len(self.character_names)}) must equal character_count "
                f"({self.character_count})"
            )
        if not self.character_names:
            self.character_names = [
                f"{self.name} #{i + 1}" for i in range(self.character_count)
            ]
        return self


class SeriesConfig(BaseModel):
    duration_days: int = Field(30, ge=1)
    tiers: list[RarityTier]

    @model_validator(mode="after")
    def _check_tiers(self) -> "SeriesConfig":
        if not self.tiers:
            raise ValueError("SeriesConfig requires at least one tier")
        s = sum(t.probability for t in self.tiers)
        if abs(s - 1.0) > PROB_TOL:
            raise ValueError(
                f"tier probabilities must sum to 1.0 (got {s:.6f})"
            )
        # Unique tier names
        names = [t.name for t in self.tiers]
        if len(set(names)) != len(names):
            raise ValueError(f"tier names must be unique (got {names})")
        return self

    @property
    def total_characters(self) -> int:
        return sum(t.character_count for t in self.tiers)

    @property
    def all_character_names(self) -> list[str]:
        out: list[str] = []
        for t in self.tiers:
            out.extend(t.character_names)
        return out


class DrawConfig(BaseModel):
    daily_free_draws: int = Field(1, ge=0)
    single_pull_cost_wish: int = Field(80, ge=0)
    ten_pull_cost_wish: int = Field(720, ge=0)
    wish_per_usd: int = Field(100, ge=1)
    pity_threshold: int = Field(10, ge=1)
    pity_guarantee: PityGuarantee = "unowned_any"
    soft_pity_start: int | None = None
    soft_pity_full: int | None = None

    @model_validator(mode="after")
    def _check_soft_pity(self) -> "DrawConfig":
        has_s = self.soft_pity_start is not None
        has_f = self.soft_pity_full is not None
        if has_s != has_f:
            raise ValueError(
                "soft_pity_start and soft_pity_full must both be set or both None"
            )
        if has_s and has_f:
            if not (0 <= self.soft_pity_start < self.soft_pity_full):
                raise ValueError("soft_pity_start must be < soft_pity_full")
            if self.soft_pity_full > self.pity_threshold:
                raise ValueError("soft_pity_full must be <= pity_threshold")
        return self


class UserSegment(BaseModel):
    name: str
    population_share: float = Field(..., ge=0.0, le=1.0)
    daily_active_rate: float = Field(..., ge=0.0, le=1.0)
    extra_paid_pulls_min: int = Field(0, ge=0)
    extra_paid_pulls_max: int = Field(0, ge=0)
    stop_rule: StopRule = "never_stop"

    @model_validator(mode="after")
    def _check_range(self) -> "UserSegment":
        if self.extra_paid_pulls_min > self.extra_paid_pulls_max:
            raise ValueError(
                f"segment '{self.name}': extra_paid_pulls_min "
                f"({self.extra_paid_pulls_min}) > extra_paid_pulls_max "
                f"({self.extra_paid_pulls_max})"
            )
        return self


class PopulationConfig(BaseModel):
    total_users: int = Field(10_000, ge=1)
    segments: list[UserSegment]
    random_seed: int | None = None

    @model_validator(mode="after")
    def _check_shares(self) -> "PopulationConfig":
        if not self.segments:
            raise ValueError("PopulationConfig requires at least one segment")
        s = sum(seg.population_share for seg in self.segments)
        if abs(s - 1.0) > PROB_TOL:
            raise ValueError(
                f"segment population_share must sum to 1.0 (got {s:.6f})"
            )
        names = [seg.name for seg in self.segments]
        if len(set(names)) != len(names):
            raise ValueError(f"segment names must be unique (got {names})")
        return self


class SimConfig(BaseModel):
    name: str = "unnamed"
    series: SeriesConfig
    draw: DrawConfig
    population: PopulationConfig

    def json_blob(self) -> str:
        """Canonical JSON used for cache-key hashing."""
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, default=str)


def config_hash(cfg: SimConfig) -> str:
    return hashlib.sha256(cfg.json_blob().encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Preset IO
# --------------------------------------------------------------------------- #
PRESET_DIR = Path(__file__).resolve().parent.parent / "presets"


def load_preset(name_or_path: str | Path) -> SimConfig:
    p = Path(name_or_path)
    if not p.suffix:
        p = PRESET_DIR / f"{p.name}.json"
    elif not p.is_absolute():
        candidate = PRESET_DIR / p.name
        if candidate.exists():
            p = candidate
    with open(p, "r") as f:
        data = json.load(f)
    return SimConfig.model_validate(data)


_SLUG_RE = re.compile(r"[^a-zA-Z0-9_\-]+")


def _slugify(name: str) -> str:
    s = _SLUG_RE.sub("_", name.strip())
    s = s.strip("_")
    return s or "preset"


def save_preset(cfg: SimConfig, name: str) -> Path:
    PRESET_DIR.mkdir(parents=True, exist_ok=True)
    slug = _slugify(name)
    p = PRESET_DIR / f"{slug}.json"
    data = cfg.model_dump(mode="json")
    data["name"] = slug
    with open(p, "w") as f:
        json.dump(data, f, indent=2)
    return p


def list_presets() -> list[str]:
    if not PRESET_DIR.exists():
        return []
    return sorted(p.stem for p in PRESET_DIR.glob("*.json"))
