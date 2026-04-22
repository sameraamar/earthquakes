"""One-off check: compare earlier forecasts vs. actuals from merged dataset."""
import pandas as pd
from earthquakes.data_loader import load
from earthquakes.predict import _bin_grid, GRID_DEG

df = load()
df["lat_bin"] = _bin_grid(df["latitude"], GRID_DEG)
df["lon_bin"] = _bin_grid(df["longitude"], GRID_DEG)
df["month"] = (
    df["time"].dt.tz_convert("UTC").dt.tz_localize(None).dt.to_period("M").dt.to_timestamp()
)

# Top-10 forecasts from the LOBELLO-only run, all targeting July 2023.
FORECASTS = [
    (35.0, -125.0, "2023-07-01", 1711.34, "6 km W of Cobb, California"),
    (60.0, -155.0, "2023-07-01", 1102.56, "Central Alaska"),
    (30.0, -120.0, "2023-07-01", 1043.34, "9km NE of Aguanga, CA"),
    (35.0, -120.0, "2023-07-01",  845.07, "45 km ESE of Beatty, Nevada"),
    (55.0, -160.0, "2023-07-01",  777.26, "85 km NW of Karluk, Alaska"),
    (15.0, -160.0, "2023-07-01",  737.14, "6 km SW of Volcano, Hawaii"),
    (60.0, -150.0, "2023-07-01",  713.05, "Central Alaska"),
    (55.0, -155.0, "2023-07-01",  502.98, "Southern Alaska"),
    (50.0, -180.0, "2023-07-01",  474.70, "Andreanof Islands, Aleutian Islands, Alaska"),
    (15.0,  -70.0, "2023-07-01",  373.69, "Puerto Rico region"),
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
