"""Narrative auto-summary panel (PRD §4.3.7) and A/B diff summary (§4.4)."""
from __future__ import annotations

from typing import Any

import numpy as np

from simulator.engine import SimResult
from simulator import metrics as m


def narrative_markdown(result: SimResult) -> str:
    blocks = m.narrative_blocks(result)
    return "\n\n".join(
        blocks[k]
        for k in ("typical_f2p", "p99_unlucky_paying", "lucky_f2p", "last_character", "whale_ceiling")
    )


def _delta_fmt(a: float, b: float, as_pct_pts: bool = False, unit: str = "") -> str:
    d = b - a
    sign = "+" if d >= 0 else ""
    if as_pct_pts:
        return f"{sign}{d * 100:.1f} pp"
    if unit == "usd":
        return f"{sign}${d:,.2f}"
    if unit == "pct_change":
        if a == 0:
            return f"{sign}{d:.0f}"
        return f"{sign}{(d / a) * 100:.1f}%"
    return f"{sign}{d:.1f}"


def diff_summary(a: SimResult, b: SimResult) -> list[str]:
    ka = m.kpi_summary(a)
    kb = m.kpi_summary(b)

    def _line(label: str, av: float, bv: float, fmt: str) -> str:
        if fmt == "pct":
            return (
                f"- **{label}:** {av * 100:.1f}% → {bv * 100:.1f}% "
                f"({_delta_fmt(av, bv, as_pct_pts=True)})"
            )
        if fmt == "usd":
            return (
                f"- **{label}:** ${av:,.0f} → ${bv:,.0f} "
                f"({_delta_fmt(av, bv, unit='pct_change')})"
            )
        if fmt == "pulls":
            return (
                f"- **{label}:** {av:.1f} → {bv:.1f} "
                f"({_delta_fmt(av, bv)})"
            )
        return f"- **{label}:** {av} → {bv}"

    lines = [
        _line("Collection rate", ka["completion_rate"], kb["completion_rate"], "pct"),
        _line("Total revenue", ka["total_revenue_usd"], kb["total_revenue_usd"], "usd"),
        _line("ARPU", ka["arpu_usd"], kb["arpu_usd"], "usd"),
        _line("Median pulls → 1st Rare", ka["median_pulls_to_first_rare"], kb["median_pulls_to_first_rare"], "pulls"),
        _line("Median owned", ka["median_owned"], kb["median_owned"], "pulls"),
        _line("Avg pity triggers", ka["avg_pity_triggers"], kb["avg_pity_triggers"], "pulls"),
    ]

    # P99 pulls to first rare.
    def _p99(res: SimResult) -> float:
        vals = res.users["first_rare_pull"].to_numpy()
        vals = vals[vals >= 0]
        return float(np.percentile(vals + 1, 99)) if vals.size else float("nan")

    p99a = _p99(a)
    p99b = _p99(b)
    lines.append(
        f"- **P99 pulls → 1st Rare:** {p99a:.0f} → {p99b:.0f} "
        f"({_delta_fmt(p99a, p99b)})"
    )
    return lines
