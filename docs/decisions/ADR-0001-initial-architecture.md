# ADR-0001 — Initial architecture

## Purpose
Record the first architectural decisions for the earthquakes project.

## Maintenance
- ADRs are immutable once accepted. Supersede with a new ADR.

---

- Status: Accepted
- Date: 2026-04-22

## Context
We need to explore a Kaggle earthquake dataset, produce interactive HTML
visualizations, and build a baseline predictive model. The project is
small, exploratory, and single-developer.

## Decision
- Use a single Python package `earthquakes` under `src/` layout.
- Use `kagglehub` to fetch data; cache as parquet in `data/`.
- Use `folium` for the map and `plotly` for the timeline (both emit HTML).
- Use `scikit-learn` for the baseline model; aggregate to lat/lon grid × month.
- Provide a thin CLI: `python -m earthquakes.cli {info,viz,predict}`.

## Consequences
- Easy to iterate; minimal infra.
- Heavy dependencies (plotly, folium) are acceptable for a local exploratory tool.
- Deferred: tests, packaging, a notebook UI.
