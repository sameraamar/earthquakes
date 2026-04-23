# Prediction Notes

## Purpose
Detailed notes for the current earthquake prediction attempt.
This supplements `docs/design/design.md` with implementation details,
feature-engineering notes, evaluation results, and current limitations.

## Current scope
The repository's prediction path is a local, illustrative baseline.
It is not an operational earthquake forecasting system.

Implementation entry points:
- `src/earthquakes/predict.py`
- `src/earthquakes/cli.py` (`python -m earthquakes.cli predict`)

## Dataset access note
The Kaggle datasets used by this repo are public and were downloaded from
Kaggle.

## Problem framing
Current target:
- Aggregate earthquakes into `(lat_bin, lon_bin, month)` cells on a 5 degree grid.
- Predict next-month `count` or `max_mag` for each cell.

Current CLI supports:
- `--target {count,max_mag}`
- `--max yyyyMM` to cap training data and forecast the immediately following month
- `--sources` to choose input datasets

## Current features
The current GBM uses a shared monthly panel per grid cell and leakage-safe
features derived only from prior months.

Included features:
- Target lags: `lag1`, `lag3`, `lag6`, `lag12`
- Count lags: `count_lag1`, `count_lag3`, `count_lag6`, `count_lag12`
- Max-magnitude lags: `max_mag_lag1`, `max_mag_lag3`, `max_mag_lag6`, `max_mag_lag12`
- Rolling means: count over 3/6/12 months
- Rolling volatility: count std over 6 months
- Rolling max-magnitude means over 3/6 months
- Trend deltas:
  - `count_lag1 - count_lag3`
  - `count_lag1 - count_lag12`
  - `max_mag_lag1 - max_mag_lag3`
- Seasonality:
  - month-of-year sine/cosine
- Cell age:
  - months since the cell first appears in the panel
- Spatial coordinates:
  - `lat_bin`, `lon_bin`

## Baselines
The CLI reports three naive baselines for holdout comparison:
- `last_month`
- `seasonal_12m`
- `mean_lags`

These are important because the current GBM frequently looks plausible in the
Top 10 forecast table while still underperforming trivial baselines.

## Evaluation used so far
There are two evaluation styles currently discussed in the repo.

### 1. CLI holdout
`predict` reports MAE on the last 12 months of the training panel.
This is useful as a quick regression check but can hide month-specific failure
modes.

### 2. One-month backtests
We also ran direct month-to-month checks:
- Train through `2023-07`, forecast `2023-08`, compare to actual `2023-08`
- Train through `2024-07`, forecast `2024-08`, compare to actual `2024-08`

These tests are more concrete for asking: "if we stopped here, how good would
next month have been?"

## Results so far
Using default merged Kaggle sources: `LOBELLO,GAURAV2025`

### Backtest: forecast 2023-08
Train through `2023-07`, score against `2023-08`.

Summary:
- Cells scored: `716`
- Active cells in actual month: `70`
- Actual total: `106`
- GBM predicted total: `12113.3`

MAE across all cells:
- GBM: `16.7869`
- last_month: `16.3506`
- seasonal_12m: `16.1885`
- mean_lags: `16.2811`

MAE across active cells only:
- GBM: `26.6362`
- last_month: `26.4143`
- seasonal_12m: `27.4143`
- mean_lags: `27.5036`

Interpretation:
- This attempt was not successful.
- The GBM badly overpredicted total activity.
- It did not beat even the simple baselines.

### Backtest: forecast 2024-08
Train through `2024-07`, score against `2024-08`.

Summary:
- Cells scored: `716`
- Active cells in actual month: `63`
- Actual total: `105`
- GBM predicted total: `1687.3`

MAE across all cells:
- GBM: `3.1215`
- last_month: `0.2053`
- seasonal_12m: `14.3841`
- mean_lags: `3.7235`

MAE across active cells only:
- GBM: `1.3203`
- last_month: `1.3810`
- seasonal_12m: `14.9206`
- mean_lags: `4.4206`

Interpretation:
- Better than the 2023-08 run, but still not a success overall.
- On active cells only, GBM is slightly better than `last_month`.
- Across all cells, `last_month` is dramatically better because the problem is
  sparse and zero-heavy.
- The GBM still overpredicts total activity.

## Current diagnosis
The present model's main issues are:
- Count target is heavy-tailed and sparse.
- Most cells are zero in most months.
- The GBM tends to overpredict large counts.
- A plausible-looking Top 10 forecast does not imply good overall accuracy.
- The simple `last_month` baseline is currently stronger on overall MAE for the
  merged Kaggle sources.

## Tests and gaps
Current state:
- No dedicated pytest coverage for prediction features or backtests yet.
- Validation has mostly been CLI runs and one-off backtest scripts.

Recommended future tests:
- Unit tests for feature-panel construction
- Tests asserting no leakage from future months
- Regression tests for `--max yyyyMM` behavior
- Tests for one-month backtest helpers against small synthetic data

## Current conclusion
This prediction path should be treated as an exploratory try, not a successful
forecasting result.

It is useful because it:
- establishes a reproducible baseline,
- exposes where the model fails,
- gives us concrete benchmarks to beat.

It is not yet good enough to claim meaningful next-month earthquake-count
prediction on the merged Kaggle sources.

## Likely next improvements
Most promising directions:
- model `log1p(count)` instead of raw count,
- test a binary target such as "any event next month",
- use rolling/expanding backtests instead of one final holdout only,
- try models better suited to sparse count data,
- compare grid sizes or alternative regional definitions.
