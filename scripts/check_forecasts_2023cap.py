"""Compare the --max=202312 forecasts vs actuals."""
import pandas as pd
from earthquakes.data_loader import load
from earthquakes.predict import _bin_grid, GRID_DEG

df = load()
df["lat_bin"] = _bin_grid(df["latitude"], GRID_DEG)
df["lon_bin"] = _bin_grid(df["longitude"], GRID_DEG)
df["month"] = (
    df["time"].dt.tz_convert("UTC").dt.tz_localize(None).dt.to_period("M").dt.to_timestamp()
)

FORECASTS = [
    (35.0, -125.0, "2023-07-01", 1663.10, "6 km W of Cobb, California"),
    (30.0, -120.0, "2023-08-01", 1052.20, "9km NE of Aguanga, CA"),
    (55.0, -160.0, "2023-07-01",  717.40, "85 km NW of Karluk, Alaska"),
    (60.0, -155.0, "2023-12-01",  545.64, "Central Alaska"),
    (60.0, -150.0, "2024-01-01",  494.65, "Central Alaska"),
    (35.0, -120.0, "2024-01-01",  382.37, "45 km ESE of Beatty, Nevada"),
    (50.0, -180.0, "2024-01-01",  275.53, "Andreanof Islands, Aleutian Islands, Alaska"),
    (15.0, -160.0, "2024-01-01",  271.59, "6 km SW of Volcano, Hawaii"),
    (55.0, -155.0, "2024-01-01",  224.62, "Southern Alaska"),
    (40.0, -115.0, "2023-07-01",  212.78, "Wyoming"),
]

rows = []
for lat, lon, m, pred, region in FORECASTS:
    mask = (df["lat_bin"] == lat) & (df["lon_bin"] == lon) & (df["month"] == pd.Timestamp(m))
    actual = int(mask.sum())
    err = pred - actual
    pct = (abs(err) / actual * 100) if actual else float("inf")
    rows.append(
        dict(region=region, lat=lat, lon=lon, month=m,
             pred=round(pred, 1), actual=actual,
             err=round(err, 1), abs_err_pct=round(pct, 1))
    )

out = pd.DataFrame(rows)
print(out.to_string(index=False))

abs_err = (out["pred"] - out["actual"]).abs()
print()
print(f"MAE  on these top-10 : {abs_err.mean():.1f} events/month")
finite = out[out["actual"] > 0]
mape = (abs_err.loc[finite.index] / finite["actual"]).mean() * 100
print(f"MAPE on these top-10 : {mape:.1f}%")
