"""Metric aggregation tests."""
from __future__ import annotations

import numpy as np
import pandas as pd

from simulator import metrics as m
from simulator.config import load_preset
from simulator.engine import run_simulation


def test_lorenz_and_gini_all_equal():
    # All users spend $1 -> Lorenz is the 45-degree line; Gini == 0.
    vals = np.ones(100)
    x, y, gini = m.lorenz_curve(vals)
    assert abs(gini) < 1e-9
    assert np.allclose(x, y, atol=1e-9)


def test_lorenz_and_gini_single_spender():
    # One user has all the spend; near-maximal inequality.
    vals = np.zeros(100)
    vals[-1] = 100.0
    x, y, gini = m.lorenz_curve(vals)
    # For n=100, Gini_max = (n-1)/n = 0.99
    assert 0.95 < gini < 1.0


def test_completion_funnel_monotone_decreasing():
    cfg = load_preset("mengjing_v1")
    r = run_simulation(cfg)
    fun = m.completion_funnel(r)
    vals = fun["pct"].to_numpy()
    assert (np.diff(vals) <= 1e-9).all(), "funnel must be monotone non-increasing"


def test_collection_histogram_sums_to_n():
    cfg = load_preset("mengjing_v1")
    r = run_simulation(cfg)
    df = m.collection_histogram(r)
    assert int(df["users"].sum()) == r.n_users


def test_persona_rank_ordering():
    cfg = load_preset("mengjing_v1")
    r = run_simulation(cfg)
    p0 = m.get_persona(r, "F2P", 0)
    p100 = m.get_persona(r, "F2P", 100)
    # P0 (unluckiest) should have <= owned_count than P100 (luckiest).
    assert p0.owned_count <= p100.owned_count


def test_rare_source_breakdown_sums_to_rare_owners():
    cfg = load_preset("mengjing_v1")
    r = run_simulation(cfg)
    rs = m.rare_source_breakdown(r)
    total = int(rs["users"].sum())
    expected = int((r.users["first_rare_pull"] >= 0).sum())
    assert total == expected


def test_revenue_by_segment_sums_to_total():
    cfg = load_preset("mengjing_v1")
    r = run_simulation(cfg)
    rbs = m.revenue_by_segment(r)
    total = float(rbs["revenue_usd"].sum())
    overall = float(r.users["spend_usd"].sum())
    assert abs(total - overall) < 1e-6


def test_kpi_summary_consistency():
    cfg = load_preset("mengjing_v1")
    r = run_simulation(cfg)
    k = m.kpi_summary(r)
    # Rebuild completion rate manually.
    assert abs(k["completion_rate"] - (r.users["owned_count"] == 9).mean()) < 1e-9
    # ARPU check.
    arpu = r.users["spend_usd"].sum() / r.n_users
    assert abs(k["arpu_usd"] - arpu) < 1e-6


def test_pity_utility_rate_bounded_01():
    cfg = load_preset("mengjing_v1")
    r = run_simulation(cfg)
    rate = m.pity_utility_rate(r)
    assert 0.0 <= rate <= 1.0
