"""Aggregations and summary statistics derived from a SimResult.

Pure functions, no plotting. Keeps viz modules thin.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .engine import SimResult


# --------------------------------------------------------------------------- #
# KPI row (PRD §4.3.1)
# --------------------------------------------------------------------------- #
def kpi_summary(result: SimResult) -> dict[str, Any]:
    u = result.users
    num_chars = result.num_chars
    spend_usd = u["spend_usd"]
    paying = u[u["paid_pulls"] > 0]

    completion_rate = float((u["owned_count"] == num_chars).mean())
    median_spend = float(spend_usd.median())
    median_owned = float(u["owned_count"].median())
    avg_pity = float(u["pity_triggers"].mean())

    # Pulls to first rare (users who got one).
    frp = u["first_rare_pull"]
    with_rare = frp[frp >= 0]
    median_pulls_rare = (
        float(with_rare.median()) + 1.0 if len(with_rare) else float("nan")
    )

    total_revenue = float(spend_usd.sum())
    arpu = total_revenue / max(len(u), 1)
    arppu = total_revenue / max(len(paying), 1) if len(paying) else 0.0

    # Per-segment breakdown for hover context.
    per_segment = (
        u.groupby("segment")
        .agg(
            users=("user_idx", "count"),
            completion_rate=("owned_count", lambda s: float((s == num_chars).mean())),
            median_spend_usd=("spend_usd", "median"),
            total_revenue_usd=("spend_usd", "sum"),
            median_owned=("owned_count", "median"),
            avg_pity_triggers=("pity_triggers", "mean"),
        )
        .reset_index()
    )

    return {
        "users": len(u),
        "completion_rate": completion_rate,
        "median_pulls_to_first_rare": median_pulls_rare,
        "median_spend_usd": median_spend,
        "total_revenue_usd": total_revenue,
        "arpu_usd": arpu,
        "arppu_usd": arppu,
        "median_owned": median_owned,
        "avg_pity_triggers": avg_pity,
        "per_segment": per_segment,
    }


# --------------------------------------------------------------------------- #
# Collection (PRD §4.3.2)
# --------------------------------------------------------------------------- #
def collection_histogram(result: SimResult) -> pd.DataFrame:
    """Count of users by owned_count, stacked by segment.

    Returns long-form DataFrame: segment, owned_count, users.
    """
    u = result.users
    num_chars = result.num_chars
    counts = (
        u.groupby(["segment", "owned_count"])
        .size()
        .rename("users")
        .reset_index()
    )
    # Ensure every (segment, k) pair in 0..num_chars exists.
    full = pd.MultiIndex.from_product(
        [result.segment_names, range(num_chars + 1)],
        names=["segment", "owned_count"],
    ).to_frame(index=False)
    out = full.merge(counts, on=["segment", "owned_count"], how="left").fillna(
        {"users": 0}
    )
    out["users"] = out["users"].astype(int)
    return out


def completion_funnel(result: SimResult) -> pd.DataFrame:
    """% of users who own at least k characters for k in 1..num_chars."""
    u = result.users
    n = len(u)
    num_chars = result.num_chars
    owned = u["owned_count"].to_numpy()
    pct_at_least = np.array(
        [(owned >= k).mean() for k in range(1, num_chars + 1)]
    )
    return pd.DataFrame({"k": range(1, num_chars + 1), "pct": pct_at_least, "n": n})


def ownership_heatmap(result: SimResult) -> pd.DataFrame:
    """% of users owning each character by day 0..D.

    Returns long-form: character, day, pct.
    """
    fd = result.first_day  # [N, num_chars]
    N = fd.shape[0]
    D = result.meta["duration_days"]
    # For each (char, day), pct = fraction of users with 0 <= first_day <= day.
    # Build cumulative ownership matrix [num_chars, D+1].
    num_chars = fd.shape[1]
    # Count how many users acquired char c by day d:
    # cum[c, d] = sum_i (0 <= fd[i,c] <= d)
    # Equivalent: sort fd per char then searchsorted.
    pct = np.zeros((num_chars, D + 1))
    for c in range(num_chars):
        col = fd[:, c]
        acquired = col[col >= 0]
        if acquired.size:
            # For each day d, count acquired <= d.
            acquired_sorted = np.sort(acquired)
            for d in range(D + 1):
                pct[c, d] = np.searchsorted(acquired_sorted, d, side="right") / N
    rows: list[dict[str, Any]] = []
    for c, cname in enumerate(result.character_names):
        for d in range(D + 1):
            rows.append({"character": cname, "day": d, "pct": float(pct[c, d])})
    return pd.DataFrame(rows)


def duplicates_per_character(result: SimResult) -> pd.DataFrame:
    """Duplicates per user per character (count of acquisitions minus 1).

    Returns long-form: character, user_idx, duplicates.
    """
    ev = result.events
    if ev.empty:
        return pd.DataFrame(columns=["character", "user_idx", "duplicates"])
    counts = (
        ev.groupby(["user_idx", "char_idx"]).size().rename("hits").reset_index()
    )
    counts["duplicates"] = counts["hits"] - 1
    counts["character"] = counts["char_idx"].map(
        dict(enumerate(result.character_names))
    )
    return counts[["character", "user_idx", "duplicates"]]


# --------------------------------------------------------------------------- #
# Rare analysis (PRD §4.3.3)
# --------------------------------------------------------------------------- #
def rare_indices(result: SimResult) -> np.ndarray:
    tier_idx = result.meta["char_tier_idx"]
    return np.flatnonzero(tier_idx != 0)


def pulls_to_first_rare_cdf(result: SimResult) -> pd.DataFrame:
    """CDF rows: segment ('All' or segment name), x (pull count), cdf (0..1)."""
    u = result.users
    out_rows: list[dict[str, Any]] = []

    def _cdf(values: np.ndarray, label: str, denom: int) -> list[dict[str, Any]]:
        # Include users who never got one: treat their "x" as infinity.
        # CDF = P(X <= x | user exists). We normalize by `denom` so "never obtained"
        # shows as an asymptote below 1.0.
        got = values[values >= 0]
        got_sorted = np.sort(got + 1)  # 1-indexed pull count
        if got_sorted.size == 0:
            return [{"segment": label, "x": 0, "cdf": 0.0}]
        rows = []
        rows.append({"segment": label, "x": 0, "cdf": 0.0})
        ys = np.arange(1, len(got_sorted) + 1) / denom
        # Step-plot points: x, old_cdf then x, new_cdf
        prev = 0.0
        for xi, yi in zip(got_sorted, ys):
            rows.append({"segment": label, "x": int(xi), "cdf": float(prev)})
            rows.append({"segment": label, "x": int(xi), "cdf": float(yi)})
            prev = yi
        return rows

    out_rows.extend(_cdf(u["first_rare_pull"].to_numpy(), "All", len(u)))
    for seg in result.segment_names:
        mask = u["segment"] == seg
        denom = int(mask.sum())
        if denom == 0:
            continue
        out_rows.extend(
            _cdf(u.loc[mask, "first_rare_pull"].to_numpy(), seg, denom)
        )
    return pd.DataFrame(out_rows)


def days_to_first_rare_cdf(result: SimResult) -> pd.DataFrame:
    u = result.users
    rows: list[dict[str, Any]] = []

    def _cdf(values: np.ndarray, label: str, denom: int) -> list[dict[str, Any]]:
        got = values[values >= 0]
        got_sorted = np.sort(got + 1)
        if got_sorted.size == 0:
            return [{"segment": label, "day": 0, "cdf": 0.0}]
        ys = np.arange(1, len(got_sorted) + 1) / denom
        out = [{"segment": label, "day": 0, "cdf": 0.0}]
        prev = 0.0
        for xi, yi in zip(got_sorted, ys):
            out.append({"segment": label, "day": int(xi), "cdf": float(prev)})
            out.append({"segment": label, "day": int(xi), "cdf": float(yi)})
            prev = yi
        return out

    rows.extend(_cdf(u["first_rare_day"].to_numpy(), "All", len(u)))
    for seg in result.segment_names:
        mask = u["segment"] == seg
        rows.extend(_cdf(u.loc[mask, "first_rare_day"].to_numpy(), seg, int(mask.sum())))
    return pd.DataFrame(rows)


def rare_ownership_by_segment(result: SimResult) -> pd.DataFrame:
    u = result.users
    rare_cols_idx = rare_indices(result)
    rare_mask = 0
    for ci in rare_cols_idx:
        rare_mask |= 1 << int(ci)
    u = u.copy()
    u["has_rare"] = (u["owned_mask"].to_numpy().astype(np.int64) & rare_mask) != 0
    out = (
        u.groupby("segment")
        .agg(users=("user_idx", "count"), pct_with_rare=("has_rare", "mean"))
        .reset_index()
    )
    return out


def rare_source_breakdown(result: SimResult) -> pd.DataFrame:
    """Pity-sourced vs natural-sourced first Rare acquisitions."""
    ev = result.events
    rare_cols_idx = rare_indices(result)
    if ev.empty or rare_cols_idx.size == 0:
        return pd.DataFrame({"source": ["Pity", "Natural"], "users": [0, 0]})
    rare_set = set(int(c) for c in rare_cols_idx)
    rare_ev = ev[ev["char_idx"].isin(rare_set) & ev["was_new"]]
    # First per user.
    first = rare_ev.sort_values(["user_idx", "day"]).drop_duplicates("user_idx")
    pity_ct = int(first["was_pity"].sum())
    nat_ct = int((~first["was_pity"]).sum())
    return pd.DataFrame({"source": ["Pity", "Natural"], "users": [pity_ct, nat_ct]})


# --------------------------------------------------------------------------- #
# Revenue (PRD §4.3.4)
# --------------------------------------------------------------------------- #
def lorenz_curve(values: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Return x (cum % of users), y (cum % of revenue), and Gini coefficient."""
    v = np.sort(values.astype(np.float64))
    n = v.size
    if n == 0 or v.sum() == 0:
        return np.array([0.0, 1.0]), np.array([0.0, 1.0]), 0.0
    cum = np.cumsum(v) / v.sum()
    x = np.arange(1, n + 1) / n
    # Prepend 0,0 for a clean origin.
    x = np.insert(x, 0, 0.0)
    y = np.insert(cum, 0, 0.0)
    # Gini = 1 - 2 * AUC(Lorenz).
    auc = np.trapezoid(y, x)
    gini = float(1.0 - 2.0 * auc)
    return x, y, gini


def revenue_lorenz(result: SimResult) -> tuple[pd.DataFrame, float]:
    x, y, gini = lorenz_curve(result.users["spend_usd"].to_numpy())
    return pd.DataFrame({"x": x, "y": y}), gini


def cumulative_revenue_by_day(result: SimResult) -> pd.DataFrame:
    spend = result.spend_by_day  # [N, D], wish
    seg = result.users["segment"].to_numpy()
    usd_rate = result.config.draw.wish_per_usd
    D = spend.shape[1]
    rows: list[dict[str, Any]] = []
    for seg_name in result.segment_names:
        mask = seg == seg_name
        cum = np.cumsum(spend[mask].sum(axis=0)) / usd_rate
        for d in range(D):
            rows.append({"segment": seg_name, "day": d + 1, "cum_usd": float(cum[d])})
    return pd.DataFrame(rows)


def revenue_by_segment(result: SimResult) -> pd.DataFrame:
    out = (
        result.users.groupby("segment")
        .agg(users=("user_idx", "count"), revenue_usd=("spend_usd", "sum"))
        .reset_index()
    )
    total = out["revenue_usd"].sum()
    out["pct"] = out["revenue_usd"] / total if total > 0 else 0.0
    return out


def money_left_on_table(result: SimResult) -> dict[str, Any]:
    """Among Whales with stop_on_complete, avg day they stopped (completed)."""
    u = result.users
    segs = {
        s.name: s for s in result.config.population.segments
    }
    out: dict[str, Any] = {"segments": []}
    for seg_name, seg in segs.items():
        if seg.stop_rule == "stop_on_complete":
            sub = u[(u["segment"] == seg_name) & (u["days_to_complete"] >= 0)]
            if len(sub):
                avg_day = float(sub["days_to_complete"].mean()) + 1.0  # 1-indexed
                out["segments"].append(
                    {
                        "segment": seg_name,
                        "completed_users": int(len(sub)),
                        "avg_day_completed": avg_day,
                        "days_unused": result.meta["duration_days"] - avg_day,
                    }
                )
    return out


# --------------------------------------------------------------------------- #
# Persona (PRD §4.3.5)
# --------------------------------------------------------------------------- #
@dataclass
class Persona:
    user_idx: int
    segment: str
    percentile: int
    owned_count: int
    total_pulls: int
    paid_pulls: int
    pity_triggers: int
    spend_wish: int
    spend_usd: float
    first_rare_day: int
    first_rare_pull: int
    days_to_complete: int
    owned_names: list[str]
    never_obtained: list[str]
    cumulative_owned: np.ndarray       # [D+1]
    cumulative_spend_usd: np.ndarray   # [D+1]
    events: pd.DataFrame               # this user's events
    narrative: str


def _persona_rank(sub: pd.DataFrame) -> pd.DataFrame:
    """Sort users within segment from unluckiest (P0) to luckiest (P100)."""
    return sub.sort_values(
        by=["owned_count", "spend_usd"],
        ascending=[True, False],
        kind="stable",
    ).reset_index(drop=True)


def get_persona(result: SimResult, segment: str, percentile: int) -> Persona:
    u = result.users
    sub = u[u["segment"] == segment]
    if sub.empty:
        raise ValueError(f"no users in segment {segment!r}")
    ranked = _persona_rank(sub)
    n = len(ranked)
    p = max(0, min(100, int(percentile)))
    idx = min(n - 1, int(round(p / 100.0 * (n - 1))))
    row = ranked.iloc[idx]

    user_idx = int(row["user_idx"])
    ev = result.events
    ue = ev[ev["user_idx"] == user_idx].copy()
    ue = ue.sort_values(["day"], kind="stable").reset_index(drop=True)
    ue["pull_idx_within_user"] = np.arange(len(ue))
    ue["character"] = ue["char_idx"].map(dict(enumerate(result.character_names)))
    tier_idx = result.meta["char_tier_idx"]
    tier_names = result.meta["tier_names"]
    ue["tier"] = ue["char_idx"].map(lambda c: tier_names[int(tier_idx[int(c)])])

    D = result.meta["duration_days"]
    cum_owned = np.zeros(D + 1, dtype=np.int32)
    # Replay from first_day matrix for simplicity.
    fd = result.first_day[user_idx]
    for d in range(D + 1):
        cum_owned[d] = int(((fd >= 0) & (fd <= d - 1)).sum()) if d > 0 else 0

    spend_day = result.spend_by_day[user_idx]
    cum_spend_usd = np.concatenate(
        [[0.0], np.cumsum(spend_day) / result.config.draw.wish_per_usd]
    )

    owned_names = [
        n for i, n in enumerate(result.character_names) if fd[i] >= 0
    ]
    never = [n for i, n in enumerate(result.character_names) if fd[i] < 0]

    persona = Persona(
        user_idx=user_idx,
        segment=segment,
        percentile=p,
        owned_count=int(row["owned_count"]),
        total_pulls=int(row["total_pulls"]),
        paid_pulls=int(row["paid_pulls"]),
        pity_triggers=int(row["pity_triggers"]),
        spend_wish=int(row["spend_wish"]),
        spend_usd=float(row["spend_usd"]),
        first_rare_day=int(row["first_rare_day"]),
        first_rare_pull=int(row["first_rare_pull"]),
        days_to_complete=int(row["days_to_complete"]),
        owned_names=owned_names,
        never_obtained=never,
        cumulative_owned=cum_owned,
        cumulative_spend_usd=cum_spend_usd,
        events=ue,
        narrative="",
    )
    persona.narrative = _persona_narrative(persona, result)
    return persona


# --------------------------------------------------------------------------- #
# Narrative generation (shared with viz/narrative.py)
# --------------------------------------------------------------------------- #
def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def _persona_narrative(p: Persona, result: SimResult) -> str:
    pct = p.percentile
    seg = p.segment
    d_total = result.meta["duration_days"]
    free_pulls = p.total_pulls - p.paid_pulls
    money = f"(total spend ${p.spend_usd:.2f})"
    rare_line = ""
    if p.first_rare_pull >= 0:
        src_row = result.events[
            (result.events["user_idx"] == p.user_idx)
            & result.events["was_new"]
        ]
        # Find the first rare new event.
        rare_cols = set(int(c) for c in rare_indices(result))
        first_rare_event = src_row[src_row["char_idx"].isin(rare_cols)].head(1)
        source = "a pity trigger" if (
            not first_rare_event.empty
            and bool(first_rare_event["was_pity"].iloc[0])
        ) else "natural luck"
        rare_line = (
            f" First Rare on day {p.first_rare_day + 1} (pull "
            f"#{p.first_rare_pull + 1}), from {source}."
        )
    else:
        rare_line = " Never obtained any Rare."

    if p.never_obtained:
        missing = ", ".join(p.never_obtained)
        miss_line = f" Never obtained: {missing}."
    else:
        miss_line = " Completed the collection."

    return (
        f"This user is a {seg} at the {pct}th percentile. "
        f"Across {d_total} days they made {_plural(free_pulls, 'free pull')} "
        f"and {_plural(p.paid_pulls, 'paid pull')} {money}. "
        f"They collected {_plural(p.owned_count, 'character')}.{rare_line}"
        f"{miss_line}"
    )


# --------------------------------------------------------------------------- #
# Top-level narrative blocks (PRD §4.3.7)
# --------------------------------------------------------------------------- #
def narrative_blocks(result: SimResult) -> dict[str, str]:
    u = result.users
    num_chars = result.num_chars
    D = result.meta["duration_days"]

    def _segment_persona(seg: str, pct: int) -> str:
        try:
            return get_persona(result, seg, pct).narrative
        except ValueError:
            return f"No users in segment {seg}."

    blocks: dict[str, str] = {}

    # Typical F2P
    blocks["typical_f2p"] = "**Typical F2P player** — " + _segment_persona("F2P", 50)

    # P99 unlucky paying user (worst-case paying)
    paying = u[u["paid_pulls"] > 0]
    if len(paying):
        worst = paying.sort_values(["owned_count", "spend_usd"], ascending=[True, False]).iloc[0]
        seg = str(worst["segment"])
        blocks["p99_unlucky_paying"] = (
            "**P99 unlucky paying user** — " + _segment_persona(seg, 1)
        )
    else:
        blocks["p99_unlucky_paying"] = "**P99 unlucky paying user** — no paying users in this run."

    # Lucky F2P (P5 as best-case within F2P ranking — P95 in percentile sense)
    blocks["lucky_f2p"] = "**Lucky F2P (P95)** — " + _segment_persona("F2P", 95)

    # Last-character bottleneck
    fd = result.first_day
    never_by_char = (fd < 0).mean(axis=0)  # fraction of users who never got each char
    if fd.shape[0] > 0:
        c = int(np.argmax(never_by_char))
        cname = result.character_names[c]
        pct_never = float(never_by_char[c])
        # Completion-rank: among users missing this char, what fraction have otherwise 8/9?
        owned_masks = u["owned_mask"].to_numpy().astype(np.int64)
        char_bit = 1 << c
        missing_c = (owned_masks & char_bit) == 0
        almost_done = missing_c & (u["owned_count"].to_numpy() == num_chars - 1)
        almost_pct = float(almost_done.mean())
        blocks["last_character"] = (
            f"**The last-character bottleneck** — {cname} was never obtained by "
            f"{pct_never * 100:.1f}% of users. "
            f"{almost_pct * 100:.1f}% of all users are stuck at {num_chars - 1}/"
            f"{num_chars} with {cname} as the only missing piece."
        )
    else:
        blocks["last_character"] = "**The last-character bottleneck** — no users in run."

    # Whale ceiling
    whale = u[u["segment"] == "Whale"]
    if len(whale):
        complete_whales = whale[whale["owned_count"] == num_chars]
        avg_spend = float(whale["spend_usd"].mean())
        avg_pulls = float(whale["total_pulls"].mean())
        extra_pulls_msg = ""
        if len(complete_whales):
            extra = complete_whales["total_pulls"].to_numpy() - num_chars
            extra_pulls_msg = (
                f" Completing whales continued on average "
                f"{float(extra.mean()):.1f} pulls past their 9th unique character "
                f"(never_stop rule)."
            )
        blocks["whale_ceiling"] = (
            f"**The whale ceiling** — avg Whale spend ${avg_spend:.2f}, "
            f"avg {avg_pulls:.0f} total pulls over {D} days.{extra_pulls_msg}"
        )
    else:
        blocks["whale_ceiling"] = "**The whale ceiling** — no whales in run."

    return blocks



# --------------------------------------------------------------------------- #
# Pity diagnostics (PRD §4.3.6)
# --------------------------------------------------------------------------- #
def pity_trigger_histogram(result: SimResult) -> pd.DataFrame:
    return (
        result.users.groupby(["segment", "pity_triggers"])
        .size()
        .rename("users")
        .reset_index()
    )


def pulls_between_pity(result: SimResult) -> pd.DataFrame:
    """For each user, the gaps between successive pity triggers (in pulls)."""
    ev = result.events
    if ev.empty:
        return pd.DataFrame(columns=["gap"])
    ev = ev.sort_values(["user_idx", "day"]).reset_index(drop=True)
    ev["pull_idx"] = ev.groupby("user_idx").cumcount()
    triggers = ev[ev["was_pity"]]
    gaps: list[int] = []
    for _, grp in triggers.groupby("user_idx"):
        if len(grp) < 2:
            continue
        idxs = grp["pull_idx"].to_numpy()
        gaps.extend(np.diff(idxs).tolist())
    return pd.DataFrame({"gap": gaps})


def pity_utility_rate(result: SimResult) -> float:
    ev = result.events
    if ev.empty:
        return 0.0
    pity = ev[ev["was_pity"]]
    if pity.empty:
        return 0.0
    return float(pity["was_new"].mean())
