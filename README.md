# Earthquakes

Explore Kaggle earthquake datasets, visualize earthquakes on an interactive
map + timeline, and run a baseline "next earthquake" prediction.

> Documentation-first project. Start with [docs/START_HERE.md](docs/START_HERE.md).

## Data sources

Each row in the loaded DataFrame carries a `source` column tagging its
origin. When the same event appears in more than one source, the codes are
joined with commas (e.g. `LOBELLO,GAURAV2025`).

| Code | Range | Citation |
|------|-------|----------|
| `LOBELLO` | 1990–2023 | Alessandro Lobello, *The Ultimate Earthquake Dataset from 1990-2023*, Kaggle. <https://www.kaggle.com/datasets/alessandrolobello/the-ultimate-earthquake-dataset-from-1990-2023> |
| `GAURAV2025` | 2015–2025 | Gaurav Kumar, *Global Earthquake Dataset 2015-2025*, Kaggle. <https://www.kaggle.com/datasets/gauravkumar2525/global-earthquake-dataset-2015-2025> |

## Setup (Windows / PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Kaggle credentials
Either set environment variables:

```powershell
$env:KAGGLE_USERNAME = "your_username"
$env:KAGGLE_KEY      = "your_api_key"
```

…or place `kaggle.json` at `%USERPROFILE%\.kaggle\kaggle.json`.

## Usage

```powershell
# 1. Inspect the dataset (downloads + caches on first run)
python -m earthquakes.cli info

# 2. Build interactive HTML map + timeline -> outputs/
python -m earthquakes.cli viz

# 3. Train baseline forecasting model and print metrics
python -m earthquakes.cli predict
```

Outputs land in `outputs/`:
- `map.html` — self-contained Leaflet map with magnitude-scaled markers and a
  right-side filter panel (magnitude range slider, time range slider with
  1y/5y/10y/all quick-windows, per-source checkboxes, magnitude legend, reset
  button)
- `timeline.html` — plotly magnitude-over-time chart

### Screenshots

Interactive map ([`outputs/map-sample.html`](outputs/map-sample.html)) — one marker per earthquake, colour
scaled by magnitude band, with live filtering on magnitude range, time range,
and source:

![Map screenshot](docs/images/map.png)

Magnitude-over-time scatter ([`outputs/timeline-sample.html`](outputs/timeline-sample.html)) — colour = depth (km):

![Timeline screenshot](docs/images/timeline.png)

## Project layout
```
.github/copilot-instructions.md
docs/                # source of truth (read first)
src/earthquakes/     # implementation
data/                # cached parquet (gitignored)
outputs/             # generated HTML (gitignored)
```
