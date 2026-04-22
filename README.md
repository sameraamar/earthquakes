# Earthquakes

Explore the Kaggle dataset
[`alessandrolobello/the-ultimate-earthquake-dataset-from-1990-2023`](https://www.kaggle.com/datasets/alessandrolobello/the-ultimate-earthquake-dataset-from-1990-2023),
visualize earthquakes on an interactive map + timeline, and run a baseline
"next earthquake" prediction.

> Documentation-first project. Start with [docs/START_HERE.md](docs/START_HERE.md).

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
- `map.html` — folium map with magnitude-scaled markers
- `timeline.html` — plotly magnitude-over-time chart

## Project layout
```
.github/copilot-instructions.md
docs/                # source of truth (read first)
src/earthquakes/     # implementation
data/                # cached parquet (gitignored)
outputs/             # generated HTML (gitignored)
```
