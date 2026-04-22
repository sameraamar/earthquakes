"""Baseline 'next earthquake' forecasting.

Approach (intentionally simple — earthquake prediction is an open problem):

1. Bin events into a coarse lat/lon grid (default 5° x 5°) and into months.
2. For each (cell, month) compute event count and max magnitude.
3. Build lag features (last 1, 3, 6, 12 months) per cell.
4. Train a GradientBoostingRegressor to predict next-month event count
   and next-month max magnitude.
5. Evaluate with MAE on the last 12 months held out.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from .data_loader import load

GRID_DEG = 5.0
LAGS = (1, 3, 6, 12)
HOLDOUT_MONTHS = 12


@dataclass
class PredictionReport:
    target: str
    mae: float
    n_train: int
    n_test: int
    top_predictions: pd.DataFrame  # next-month forecast per cell, top 10


def _bin_grid(value: pd.Series, step: float) -> pd.Series:
    return (np.floor(value / step) * step).astype(float)


def aggregate(df: pd.DataFrame, *, grid_deg: float = GRID_DEG) -> pd.DataFrame:
    """Return one row per (cell, month) with count and max magnitude."""
    needed = {"time", "latitude", "longitude", "magnitude"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"Dataset missing required columns: {sorted(missing)}")

    work = df.dropna(subset=list(needed)).copy()
    work["lat_bin"] = _bin_grid(work["latitude"], grid_deg)
    work["lon_bin"] = _bin_grid(work["longitude"], grid_deg)
    work["month"] = work["time"].dt.tz_convert("UTC").dt.to_period("M").dt.to_timestamp()

    agg = (
        work.groupby(["lat_bin", "lon_bin", "month"], as_index=False)
        .agg(count=("magnitude", "size"), max_mag=("magnitude", "max"))
        .sort_values(["lat_bin", "lon_bin", "month"])
        .reset_index(drop=True)
    )
    return agg


def _add_lag_features(agg: pd.DataFrame, target: str) -> pd.DataFrame:
    """For each cell, build a complete monthly index and add lag features."""
    frames = []
    for (lat, lon), group in agg.groupby(["lat_bin", "lon_bin"], sort=False):
        if group["month"].nunique() < max(LAGS) + 2:
            continue
        idx = pd.date_range(group["month"].min(), group["month"].max(), freq="MS")
        g = (
            group.set_index("month")
            .reindex(idx)
            .assign(lat_bin=lat, lon_bin=lon)
            .fillna({"count": 0, "max_mag": 0.0})
        )
        for lag in LAGS:
            g[f"{target}_lag{lag}"] = g[target].shift(lag)
            g[f"count_lag{lag}"] = g["count"].shift(lag)
        g["target"] = g[target].shift(-1)  # next month
        g = g.dropna()
        g["month"] = g.index
        frames.append(g.reset_index(drop=True))

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def train_and_evaluate(
    df: Optional[pd.DataFrame] = None,
    *,
    target: str = "count",
    holdout_months: int = HOLDOUT_MONTHS,
) -> PredictionReport:
    """Train a GBM on lag features and report MAE on the last `holdout_months`."""
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.metrics import mean_absolute_error

    if target not in {"count", "max_mag"}:
        raise ValueError("target must be 'count' or 'max_mag'")

    if df is None:
        df = load()

    agg = aggregate(df)
    feats = _add_lag_features(agg, target=target)
    if feats.empty:
        raise RuntimeError("Not enough history to build lag features.")

    cutoff = feats["month"].max() - pd.DateOffset(months=holdout_months)
    train = feats[feats["month"] <= cutoff]
    test = feats[feats["month"] > cutoff]

    feature_cols = [c for c in feats.columns if c.endswith(tuple(f"lag{l}" for l in LAGS))]
    feature_cols += ["lat_bin", "lon_bin"]

    model = GradientBoostingRegressor(random_state=42)
    model.fit(train[feature_cols], train["target"])
    preds = model.predict(test[feature_cols])
    mae = float(mean_absolute_error(test["target"], preds))

    # Forecast for the most recent month available -> "next month" per cell
    latest = (
        feats.sort_values("month")
        .groupby(["lat_bin", "lon_bin"], as_index=False)
        .tail(1)
        .copy()
    )
    latest["forecast_next_month"] = model.predict(latest[feature_cols])
    top = (
        latest.sort_values("forecast_next_month", ascending=False)
        .head(10)[["lat_bin", "lon_bin", "month", "forecast_next_month"]]
        .reset_index(drop=True)
    )

    return PredictionReport(
        target=target,
        mae=mae,
        n_train=len(train),
        n_test=len(test),
        top_predictions=top,
    )
