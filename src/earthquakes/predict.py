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


def _cell_region_labels(df: pd.DataFrame, *, grid_deg: float = GRID_DEG) -> pd.DataFrame:
    """Return one human-readable region label per (lat_bin, lon_bin) cell.

    Picks the most frequent non-empty `place` (or `state`) string seen in the
    dataset for each cell. Falls back to a coordinate description.
    """
    label_col = next((c for c in ("place", "state") if c in df.columns), None)
    if label_col is None:
        return pd.DataFrame(columns=["lat_bin", "lon_bin", "region"])

    work = df[["latitude", "longitude", label_col]].dropna().copy()
    work[label_col] = work[label_col].astype(str).str.strip()
    work = work[work[label_col] != ""]
    work["lat_bin"] = _bin_grid(work["latitude"], grid_deg)
    work["lon_bin"] = _bin_grid(work["longitude"], grid_deg)

    region = (
        work.groupby(["lat_bin", "lon_bin"])[label_col]
        .agg(lambda s: s.value_counts().idxmax())
        .reset_index()
        .rename(columns={label_col: "region"})
    )
    return region


def aggregate(df: pd.DataFrame, *, grid_deg: float = GRID_DEG) -> pd.DataFrame:
    """Return one row per (cell, month) with count and max magnitude."""
    needed = {"time", "latitude", "longitude", "magnitude"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"Dataset missing required columns: {sorted(missing)}")

    work = df.dropna(subset=list(needed)).copy()
    work["lat_bin"] = _bin_grid(work["latitude"], grid_deg)
    work["lon_bin"] = _bin_grid(work["longitude"], grid_deg)
    # Drop tz before period conversion to avoid pandas UserWarning.
    times = work["time"].dt.tz_convert("UTC").dt.tz_localize(None)
    work["month"] = times.dt.to_period("M").dt.to_timestamp()

    agg = (
        work.groupby(["lat_bin", "lon_bin", "month"], as_index=False)
        .agg(count=("magnitude", "size"), max_mag=("magnitude", "max"))
        .sort_values(["lat_bin", "lon_bin", "month"])
        .reset_index(drop=True)
    )
    return agg


def _build_feature_panel(agg: pd.DataFrame, target: str) -> pd.DataFrame:
    """For each cell, build lag features on a shared monthly horizon.

    Every cell is extended through the global maximum month in `agg`, so the
    latest feature rows all refer to the same forecast origin month.
    """
    if agg.empty:
        return pd.DataFrame()

    frames = []
    panel_end_month = agg["month"].max()
    for (lat, lon), group in agg.groupby(["lat_bin", "lon_bin"], sort=False):
        if group["month"].nunique() < max(LAGS) + 2:
            continue
        idx = pd.date_range(group["month"].min(), panel_end_month, freq="MS")
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
    max_month: Optional[pd.Timestamp] = None,
) -> PredictionReport:
    """Train a GBM on lag features and report MAE on the last `holdout_months`.

    If ``max_month`` is given, all data with ``month`` after that month is
    dropped *before* the train/test split. The forecast is then made for the
    single next month after ``max_month``.
    """
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.metrics import mean_absolute_error

    if target not in {"count", "max_mag"}:
        raise ValueError("target must be 'count' or 'max_mag'")

    if df is None:
        df = load()

    agg = aggregate(df)
    if max_month is not None:
        agg = agg[agg["month"] <= max_month]
        if agg.empty:
            raise RuntimeError(
                f"No samples remain after filtering to max_month={max_month.strftime('%Y%m')}."
            )

    panel = _build_feature_panel(agg, target=target)
    if panel.empty:
        raise RuntimeError("Not enough history to build lag features.")

    feature_cols = [c for c in panel.columns if c.endswith(tuple(f"lag{l}" for l in LAGS))]
    feature_cols += ["lat_bin", "lon_bin"]

    feats = panel.dropna(subset=feature_cols + ["target"])
    if feats.empty:
        raise RuntimeError("Not enough complete feature rows remain after lag construction.")

    cutoff = feats["month"].max() - pd.DateOffset(months=holdout_months)
    train = feats[feats["month"] <= cutoff]
    test = feats[feats["month"] > cutoff]

    model = GradientBoostingRegressor(random_state=42)
    model.fit(train[feature_cols], train["target"])
    preds = model.predict(test[feature_cols])
    mae = float(mean_absolute_error(test["target"], preds))

    forecast_origin = panel["month"].max()
    latest = panel[panel["month"] == forecast_origin].dropna(subset=feature_cols).copy()
    latest["forecast_next_month"] = model.predict(latest[feature_cols])
    latest["forecast_for"] = latest["month"] + pd.DateOffset(months=1)

    regions = _cell_region_labels(df)
    if not regions.empty:
        latest = latest.merge(regions, on=["lat_bin", "lon_bin"], how="left")
    else:
        latest["region"] = ""

    top = (
        latest.sort_values("forecast_next_month", ascending=False)
        .head(10)[
            ["region", "lat_bin", "lon_bin", "month", "forecast_for", "forecast_next_month"]
        ]
        .rename(columns={"month": "last_observed"})
        .reset_index(drop=True)
    )

    return PredictionReport(
        target=target,
        mae=mae,
        n_train=len(train),
        n_test=len(test),
        top_predictions=top,
    )
