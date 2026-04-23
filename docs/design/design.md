# Design

## Purpose of this Document
This document is part of the modular project design documentation.
It captures the current understanding of this domain area.
Content may be incomplete early in the project.
Keep this document up-to-date as implementation evolves.
AI agents must read this before implementing related tasks and update it after completing them.

## Maintenance
- Updated by: Humans or AI after design-affecting changes.
- Split into subfolders only when a domain grows large.

---

## Product vision
A small, reproducible Python project to explore the global earthquake
dataset (1990–2023), produce **interactive HTML visualizations**, and
provide a **baseline predictive model** for region-level seismic activity.

## Personas
- Owner / learner exploring the dataset.
- Future AI agents extending the analysis.

## Functional requirements
- Load dataset via `kagglehub` (Pandas adapter).
- Cache locally as parquet under `data/`.
- Produce:
  - `outputs/map.html` — interactive folium map (magnitude-scaled markers, popups).
  - `outputs/timeline.html` — interactive plotly timeline (magnitude vs. time, color = depth).
- Baseline prediction: aggregate to (lat-lon grid cell × month), forecast
  next-month event count and max magnitude using a simple model.
- Detailed prediction notes and evaluation status live in
  [prediction.md](prediction.md).

## Non-functional requirements
- Reproducible: pinned-ish dependencies in `requirements.txt`.
- Cheap re-runs: parquet cache.
- Runs locally on Windows + PowerShell.

## Architecture
Single Python package `earthquakes` under `src/`:

```
src/earthquakes/
    __init__.py
    data_loader.py   # download + cache + clean
    viz.py           # folium map + plotly timeline
    predict.py       # feature engineering + baseline model
    cli.py           # `python -m earthquakes.cli <command>`
```

CLI commands:
- `info`     — schema + summary stats
- `viz`      — generate `outputs/map.html` and `outputs/timeline.html`
- `predict`  — train baseline model, report MAE, and forecast one shared next month;
               optional `--max yyyyMM` caps training data to that month and forecasts
               the immediately following month; optional `--sources` selects the
               input datasets; output includes naive baseline MAEs for comparison.
               Current features include lags, rolling means/std, simple trend
               deltas, month-of-year seasonality, and cell age. Current detailed
               status and findings are documented in [prediction.md](prediction.md).

## Tech stack
- Python 3.11+
- pandas, numpy, pyarrow
- kagglehub[pandas-datasets]
- folium (map)
- plotly (timeline)
- scikit-learn (baseline regressor)

## Data
- Sources (each row carries a `source` column with one or more codes,
  comma-separated when an event appears in multiple sources):
  - `LOBELLO` — Kaggle `alessandrolobello/the-ultimate-earthquake-dataset-from-1990-2023` (1990–2023).
  - `GAURAV2025` — Kaggle `gauravkumar2525/global-earthquake-dataset-2015-2025` (2015–2025).
  - `NOAA_SIG` — NOAA NCEI/WDS Global Significant Earthquake Database (2150 BC–present).
- Source codes: short, uppercase, alphanumeric, ≤10 characters.
- Schema is discovered at load time; loader normalizes common columns
  (`time`, `latitude`, `longitude`, `depth`, `magnitude`, `place`).
- Deduplication key when merging sources: `(time floored to second,
  latitude rounded to 0.01°, longitude rounded to 0.01°)`.
- `NOAA_SIG` is the historical/impact source; it adds socio-economic fields
  (deaths, damage $, houses destroyed) and tsunami linkage. It is registered
  in the multi-source registry in `src/earthquakes/data_loader.py`; opt-in via
  `load(sources=("LOBELLO", "GAURAV2025", "NOAA_SIG"))`. See task D.1.

## Constraints / edge cases
- Dataset is large; sample for the map (configurable, default 20k rows).
- Earthquake prediction is scientifically hard — model is illustrative,
  not operational.

## Testing
- Tests deferred to Phase 2 task 2.2; will live under `/tests/` using `pytest`.
- Prediction-specific testing gaps and backtest findings are tracked in
  [prediction.md](prediction.md).

## Decisions
See [../decisions/ADR-0001-initial-architecture.md](../decisions/ADR-0001-initial-architecture.md).
