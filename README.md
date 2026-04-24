# WishWish Gacha Economy Simulator

Monte Carlo simulator for tuning **WishWish** series economics before launch.
Designed to answer questions today's gut-feel parameter setting can't:

- Can a typical F2P player complete the 9-character collection in 30 days?
- What does the **P99 unlucky** experience look like?
- What ARPU / total revenue should we expect from a series?
- How does the experience and revenue shift if we drop Rare from **4% → 3%**?

The dashboard is built around one loop: **tune a parameter → watch
distributions shift live**.

---

## Quick start

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

Open http://localhost:8501 — the `mengjing_v1` preset (the first series, 梦境)
auto-loads and the dashboard renders immediately.

Run the test suite:

```bash
.venv/bin/python -m pytest -q
```

---

## What you see

1. **Inline parameter row** — Rare probability, pity threshold, daily free pulls,
   duration. Edit any of these and the dashboard recomputes (cached, so the
   second hit on the same config is instant).
2. **KPI row** — users, completion rate, median pulls to first Rare, median
   holdings.
3. **Simulation process animation** — day-by-day animated holdings histogram,
   stacked by segment. Press ▶ or scrub the day slider to watch the population
   roll up the collection size axis over the series.
4. **End-state distributions** — final holdings per user (left) and a switchable
   behavior metric (right): pulls, paid pulls, spend USD, day of first Rare,
   day of completion, or pity triggers. All stacked by segment.
5. **Advanced configuration** — collapsible expander for power users to edit
   rarity tiers, draw mechanics, and population segments directly. Probability
   sums and segment-share sums are validated inline.

The four user segments (Whale / Dolphin / Minnow / F2P) carry consistent colors
across every chart so cross-referencing is unambiguous.

---

## Project layout

```
app.py                      # Streamlit entrypoint, cached runner, tabs
simulator/
  config.py                 # Pydantic config models + preset IO + cache hash
  engine.py                 # NumPy-vectorized Monte Carlo core
  population.py             # Segment sampling
  metrics.py                # Aggregations + persona + narrative templates
viz/
  theme.py                  # Shared palette + Plotly layout defaults
  animation.py              # Simulation-process animated histogram
  behavior.py               # Holdings + behavior-metric distributions
  collection.py             # Funnel, ownership heatmap, duplicates
  rare_analysis.py          # CDFs, segment bars, pity-vs-natural source
  revenue.py                # Lorenz curve, cumulative revenue, share pie
  persona.py                # Persona Journey Explorer charts
  pity.py                   # Pity-trigger histograms
  narrative.py              # Auto-summary text + A/B diff bullets
  kpi_cards.py              # st.metric tiles
ui/
  style.py                  # CSS injection (Work Sans + Ant-Design tokens)
  sidebar.py                # Globals: preset, name, duration, total users, seed
  param_bar.py              # Inline rare/pity/free-pulls/duration controls
  section_editors.py        # Tier / segment / draw-mechanics data editors
  dashboard.py              # Single-run view (the simplified main page)
  export.py                 # CSV + chart-PNG ZIP downloads
presets/mengjing_v1.json    # Default series 1 config (4% Rare, pity 10)
tests/
  test_engine.py            # Determinism, bundle pricing, rare frequency
  test_pity.py              # Window invariants, trigger flag correctness
  test_metrics.py           # Lorenz/Gini, kpi consistency, persona ranking
```

---

## Engine semantics

All Pydantic-validated; see [`simulator/config.py`](simulator/config.py).

**Pity counter** = pulls since the last newly-acquired character. Resets on
*any* pull that adds a new character (regardless of rarity), increments
otherwise. The pity guarantee fires when `pity_ctr >= pity_threshold - 1`,
selecting from a candidate pool defined by `pity_guarantee`:

- `unowned_any` — any unowned character (default; guarantees every
  `threshold`-pull window contains ≥1 new character).
- `unowned_rare_or_above` — unowned in Rare+ tiers, falling back to other
  unowned, then any Rare+.
- `rare_or_above` — any Rare+ tier (allows duplicates).

**Auto-bundle pricing.** When a user's paid pulls in a day reach 10 or more,
each full block of 10 is charged `ten_pull_cost_wish`; the remainder at
`single_pull_cost_wish` per pull. Defaults: 80 wish single, 720 wish for 10.

**Soft pity.** Optional linear ramp of the combined probability of all Rare+
tiers from base at `soft_pity_start` to 1.0 at `soft_pity_full`, inclusive.
Off by default. Internal ratios between Rare-and-above tiers stay constant.

**Activation.** Each user rolls Bernoulli(`daily_active_rate`) per day. Free
and paid pulls only happen on active days. Default DAU rates: Whale 90 / Dolphin
70 / Minnow 50 / F2P 40 — so the median F2P player simulates ~12 active days
out of 30, which is the binding constraint on F2P completion.

**Stop rules.** Per segment: `never_stop`, `stop_on_complete` (stop once all
characters owned), `stop_on_rare` (stop after first Rare).

**Determinism.** A fixed `random_seed` produces bit-identical user / event
DataFrames across runs (verified in [`tests/test_engine.py`](tests/test_engine.py)).

**Cache.** Streamlit caches simulation runs by `sha256(SimConfig JSON)`, so
identical configs reuse cached results.

---

## Performance

10,000 users × 30 days runs in ~0.1 s on a laptop (M-series Mac), well under
the 10 s budget set by the PRD. Scales linearly to ~100k users without leaving
NumPy.

---

## Deploying

This is a stateful Streamlit app, so serverless platforms like Vercel won't
work. Recommended targets:

**Streamlit Community Cloud** (free, zero config)

1. Sign in at https://streamlit.io/cloud with the GitHub account that owns this
   repo.
2. **New app** → repo `0xlxy/wishwish-gacha-sim`, branch `master`, main file
   `app.py`.
3. Advanced settings: pin Python 3.13 (or 3.11 if not available).
4. Deploy.

**Railway / Render** — both have first-class Python web service support. Use:

```
streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

as the start command and the platform's Python 3.13 image.

---

## Tech stack

- **Python 3.13**, **NumPy 1.26+** (vectorized engine), **pandas 2.1+**
- **Pydantic 2.5+** (config models + validation)
- **Plotly 5.18+** (interactive charts; `kaleido` for PNG export)
- **Streamlit 1.30+** (UI, caching, session state)
- **pytest 7.4+**

---

## License

Internal Kaiju Labs / WishWish project. Not for redistribution.
