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
- `predict`  — train baseline model and print metrics

## Tech stack
- Python 3.11+
- pandas, numpy, pyarrow
- kagglehub[pandas-datasets]
- folium (map)
- plotly (timeline)
- scikit-learn (baseline regressor)

## Data
- Source: Kaggle dataset
  `alessandrolobello/the-ultimate-earthquake-dataset-from-1990-2023`.
- Auth: `KAGGLE_USERNAME` + `KAGGLE_KEY` env vars (or `~/.kaggle/kaggle.json`).
- Schema is discovered at load time; loader normalizes common columns
  (`time`, `latitude`, `longitude`, `depth`, `magnitude`).

## Constraints / edge cases
- Dataset is large; sample for the map (configurable, default 20k rows).
- Earthquake prediction is scientifically hard — model is illustrative,
  not operational.

## Testing
- Tests deferred to Phase 2 task 2.2; will live under `/tests/` using `pytest`.

## Decisions
See [../decisions/ADR-0001-initial-architecture.md](../decisions/ADR-0001-initial-architecture.md).
