# WishWish Gacha Economy Simulator

Internal Monte Carlo tool for tuning WishWish series economics pre-launch.
See the PRD for full scope; this README covers running it.

## Setup

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run the dashboard

```bash
.venv/bin/streamlit run app.py
```

Then open http://localhost:8501. Default preset `mengjing_v1` auto-loads; hit
**Run simulation** in the sidebar to render the dashboard.

## Run the tests

```bash
.venv/bin/python -m pytest -q
```

## Project layout

```
app.py                # Streamlit entrypoint
simulator/
  config.py           # Pydantic config models + preset IO
  engine.py           # NumPy-vectorized Monte Carlo core
  population.py       # Segment sampling
  metrics.py          # Aggregations, persona, narrative text
viz/                  # Plotly figure builders, one module per dashboard section
ui/                   # Streamlit sidebar, dashboard, A/B compare, export
presets/mengjing_v1.json
tests/                # pytest suites (engine, pity, metrics)
```

## Key parameters (editable in the sidebar)

- Series: duration, rarity tiers (name, count, probability, pity-pool flag, names)
- Draw: daily free, single/10-pull cost, wish/USD, pity threshold + rule, soft pity
- Population: total users, four segments with daily-active rate, paid-pull range,
  stop rule (never_stop | stop_on_complete | stop_on_rare), random seed

## Clarified semantics (v1)

- **Pity counter** = pulls since the last newly-acquired character. Resets on any
  new-character pull, regardless of rarity. Pity fires when `pity_ctr >= pity_threshold - 1`.
- **Auto-bundle pricing.** When daily paid pulls >= 10, each full block of 10 is
  priced at `ten_pull_cost_wish`; remainder at `single_pull_cost_wish`.
- **Soft pity.** Linear ramp of rare-and-above combined probability from base at
  `soft_pity_start` to 1.0 at `soft_pity_full` (inclusive).
- **Determinism.** Fixing `random_seed` produces bit-identical results across runs.
