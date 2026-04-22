# Tasks

## Purpose
Authoritative, ordered list of work for this project.
AI agents must read this before implementing and update it after completing work.

## Maintenance
- Updated by: Humans or AI after every meaningful change.
- Use checkboxes and the per-task metadata block below.

---

## Phase 1 — Bootstrap & data exploration

### 1.1 Project scaffolding
- Status: [x]
- Started: 2026-04-22
- Completed: 2026-04-22
- Included in version: 0.1.0
- Acceptance criteria:
    - Documentation-first structure exists under `docs/`
    - `.github/copilot-instructions.md` present
    - Python package scaffold under `src/earthquakes/`
    - `requirements.txt` and `README.md` present
- Validation: Repo tree matches design.md.
- Notes:
- Dependencies: None

### 1.2 Load Kaggle earthquake dataset
- Status: [x]
- Started: 2026-04-22
- Completed: 2026-04-22
- Included in version: 0.1.0
- Acceptance criteria:
    - `kagglehub` loads the dataset into a pandas DataFrame
    - Loader caches to local parquet for fast re-runs
    - Function returns a typed, cleaned DataFrame
- Validation: `python -m earthquakes.cli info` prints schema + row count.
- Notes: Kaggle credentials required (`KAGGLE_USERNAME`, `KAGGLE_KEY`).
- Dependencies: 1.1

### 1.3 Interactive map + timeline (HTML)
- Status: [x]
- Started: 2026-04-22
- Completed: 2026-04-22
- Included in version: 0.1.0
- Acceptance criteria:
    - Generates `outputs/map.html` (folium) with magnitude-scaled markers
    - Generates `outputs/timeline.html` (plotly) of magnitude over time
    - Both openable directly in a browser
- Validation: Files exist and render in browser.
- Notes:
- Dependencies: 1.2

### 1.4 Baseline "next earthquake" prediction
- Status: [x]
- Started: 2026-04-22
- Completed: 2026-04-22
- Included in version: 0.1.0
- Acceptance criteria:
    - Region-binned (lat/lon grid) monthly count + max-magnitude forecast
    - Simple model (e.g., rolling mean / gradient-boosted regressor) as baseline
    - Reports MAE on a held-out tail of the timeseries
- Validation: `python -m earthquakes.cli predict` prints metrics.
- Notes: This is a *baseline*; true earthquake prediction is an open problem.
- Dependencies: 1.2

## Phase 2 — Refinement (planned)

### 2.1 Improve model
- Status: [ ]
- Acceptance criteria: TBD
- Dependencies: 1.4

### 2.2 Tests
- Status: [ ]
- Acceptance criteria: pytest suite for loader + features
- Dependencies: 1.2

## Discovered tasks
<!-- Add new tasks here as they emerge. -->
