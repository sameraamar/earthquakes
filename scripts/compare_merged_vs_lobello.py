"""Apples-to-apples: does merging GAURAV2025 improve July-2023 forecasts vs LOBELLO-only?

Both models:
  - cap data at 2023-06 (so July 2023 is held-out / forecast target)
  - same features, same algorithm, same hyperparameters
  - same set of cells (intersection)
Compare predictions for July 2023 against actual July 2023 counts.
"""

from __future__ import annotations

import pandas as pd

from earthquakes.data_loader import load
from earthquakes.predict import (
    GRID_DEG,
    LAGS,
    _build_feature_panel,
    _bin_grid,
    aggregate,
)
from sklearn.ensemble import GradientBoostingRegressor

CAP = pd.Timestamp("2023-06-01")  # last training month
TARGET_MONTH = pd.Timestamp("2023-07-01")  # what we predict


def _train_predict_for_month(df: pd.DataFrame) -> pd.DataFrame:
    """Train on data up to CAP, return per-cell forecast for TARGET_MONTH."""
    agg = aggregate(df)
    agg = agg[agg["month"] <= CAP]
    feats = _build_feature_panel(agg, target="count")
    train = feats[feats["month"] <= CAP]
    feat_cols = [c for c in feats.columns if c.endswith(tuple(f"lag{l}" for l in LAGS))]
    feat_cols += ["lat_bin", "lon_bin"]

    model = GradientBoostingRegressor(random_state=42)
    model.fit(train[feat_cols], train["target"])

    # Latest input row per cell that is <= CAP
    latest = (
        train.sort_values("month")
        .groupby(["lat_bin", "lon_bin"], as_index=False)
        .tail(1)
        .copy()
    )
    # Only forecast cells whose lag-1 input is May or June 2023 (so target = July 2023)
    latest = latest[latest["month"] == CAP]
    latest["pred"] = model.predict(latest[feat_cols])
    return latest[["lat_bin", "lon_bin", "pred"]]


def _actuals_for_july_2023(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["lat_bin"] = _bin_grid(work["latitude"], GRID_DEG)
    work["lon_bin"] = _bin_grid(work["longitude"], GRID_DEG)
    work["month"] = (
        work["time"].dt.tz_convert("UTC").dt.tz_localize(None).dt.to_period("M").dt.to_timestamp()
    )
    actual = (
        work[work["month"] == TARGET_MONTH]
        .groupby(["lat_bin", "lon_bin"], as_index=False)
        .size()
        .rename(columns={"size": "actual"})
    )
    return actual


def main() -> None:
    df_full = load()  # merged
    df_lobello = df_full[df_full["source"].str.contains("LOBELLO")].copy()

    print(f"merged rows  : {len(df_full):,}")
    print(f"LOBELLO rows : {len(df_lobello):,}")
    print()

    pred_merged = _train_predict_for_month(df_full).rename(columns={"pred": "pred_merged"})
    pred_lobello = _train_predict_for_month(df_lobello).rename(columns={"pred": "pred_lobello"})
    actual = _actuals_for_july_2023(df_full)

    merged = (
        pred_merged.merge(pred_lobello, on=["lat_bin", "lon_bin"], how="inner")
        .merge(actual, on=["lat_bin", "lon_bin"], how="left")
        .fillna({"actual": 0})
    )
    merged["err_merged"]  = merged["pred_merged"]  - merged["actual"]
    merged["err_lobello"] = merged["pred_lobello"] - merged["actual"]

    n = len(merged)
    mae_merged  = merged["err_merged"].abs().mean()
    mae_lobello = merged["err_lobello"].abs().mean()

    # Top-50 by actual activity (only meaningful cells)
    top = merged.sort_values("actual", ascending=False).head(50)
    mae_merged_top  = top["err_merged"].abs().mean()
    mae_lobello_top = top["err_lobello"].abs().mean()

    print(f"Cells compared (intersection): {n:,}")
    print()
    print("Forecast July 2023 -- MAE (events/month, lower is better):")
    print(f"  All cells          | LOBELLO-only: {mae_lobello:8.3f}   merged: {mae_merged:8.3f}   delta: {mae_merged-mae_lobello:+.3f}")
    print(f"  Top-50 by actual   | LOBELLO-only: {mae_lobello_top:8.3f}   merged: {mae_merged_top:8.3f}   delta: {mae_merged_top-mae_lobello_top:+.3f}")
    print()

    print("Top 10 cells by actual July-2023 activity:")
    show = (
        merged.sort_values("actual", ascending=False)
        .head(10)[["lat_bin", "lon_bin", "actual", "pred_lobello", "pred_merged"]]
        .round(1)
    )
    show["abs_err_lobello"] = (show["pred_lobello"] - show["actual"]).abs().round(1)
    show["abs_err_merged"]  = (show["pred_merged"]  - show["actual"]).abs().round(1)
    print(show.to_string(index=False))


if __name__ == "__main__":
    main()
