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
- Notes: `predict --max` now requires strict `yyyyMM` and forecasts a single
  global next month; remaining model-quality improvements still open.
- Dependencies: 1.4

### 2.2 Tests
- Status: [ ]
- Acceptance criteria: pytest suite for loader + features
- Dependencies: 1.2

## Discovered tasks
<!-- Add new tasks here as they emerge. -->

### D.1 Add second data source (`GAURAV2025`)
- Status: [x]
- Started: 2026-04-22
- Completed: 2026-04-22
- Acceptance criteria:
    - `data_loader` loads multiple Kaggle datasets and tags each row with a
      short uppercase `source` code (≤10 chars).
    - When the same event appears in multiple sources, codes are joined with
      commas (e.g. `LOBELLO,GAURAV2025`).
    - README cites both sources.
- Notes: dedup key = (time floored to second, lat 0.01°, lon 0.01°).
- Dependencies: 1.2

### D.1 Add NOAA significant-earthquake dataset as secondary source
- Status: [x]
- Started: 2026-04-22
- Completed: 2026-04-22
- Acceptance criteria:
    - NOAA NCEI/WDS Significant Earthquake Database (2150 BC -> present,
      ~5,700 events) is registered in the existing multi-source registry
      (`SOURCES["NOAA_SIG"]`) and fetched via the public Hazel API.
    - Loaded rows are normalized to the canonical schema
      (`time, latitude, longitude, depth, magnitude, place, source`) and
      flow through the same `_load_one` / `_merge_sources` pipeline as the
      Kaggle sources, so per-row provenance via `source` is preserved.
    - Pre-1678 rows are dropped (their `time` is `NaT`) by the standard
      required-column filter in `_load_one`.
- Validation: `load(sources=("NOAA_SIG",), refresh=True)` returns a
  non-empty DataFrame whose `source` column equals `"NOAA_SIG"`.
- Notes: Opt-in — not in `DEFAULT_SOURCES` to keep the existing parquet
  cache stable. CLI flag for selecting sources, viz overlay for impact
  fields (deaths/damage/tsunami), and tests remain follow-up work (D.2).
- Dependencies: 1.2

### D.2 Wire NOAA source into CLI + viz overlay
- Status: [ ]
- Acceptance criteria:
    - `info` / `viz` / `predict` accept a `--sources` flag selecting any
      subset of `SOURCES` (default unchanged).
    - `viz` optionally overlays NOAA impact fields (deaths, damage,
      tsunami flag) when `NOAA_SIG` is present.
    - pytest coverage for `_preprocess_noaa_significant` (BC handling,
      column renames).
- Dependencies: D.1
