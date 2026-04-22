"""Load + cache the Kaggle earthquake dataset as a tidy pandas DataFrame."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

DATASET_SLUG = "alessandrolobello/the-ultimate-earthquake-dataset-from-1990-2023"
DEFAULT_FILE_PATH = ""  # empty -> auto-discover the largest tabular file in the dataset
_SUPPORTED_EXTS = (".csv", ".tsv", ".parquet", ".feather", ".json", ".jsonl")

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
CACHE_PARQUET = DATA_DIR / "earthquakes.parquet"

# Common column-name variants we want to normalize.
_COLUMN_ALIASES = {
    "time": ["time", "date_time", "datetime", "date", "origin_time"],
    "latitude": ["latitude", "lat"],
    "longitude": ["longitude", "lon", "lng", "long"],
    "depth": ["depth", "depth_km"],
    "magnitude": ["magnitude", "mag", "magnitudo"],
    "place": ["place", "location", "region", "country", "place_description"],
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename known column variants to a stable canonical schema."""
    lower_map = {c.lower(): c for c in df.columns}
    rename: dict[str, str] = {}
    for canonical, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_map and lower_map[alias] != canonical:
                rename[lower_map[alias]] = canonical
                break
    if rename:
        df = df.rename(columns=rename)
    return df


def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], errors="coerce", utc=True)
    for col in ("latitude", "longitude", "depth", "magnitude"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _discover_local_file() -> Path:
    """Download the dataset locally and return the largest supported tabular file."""
    import kagglehub

    local_dir = Path(kagglehub.dataset_download(DATASET_SLUG))
    candidates = [
        p for p in local_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in _SUPPORTED_EXTS
    ]
    if not candidates:
        raise RuntimeError(
            f"No supported tabular files found in dataset at {local_dir}. "
            f"Supported extensions: {_SUPPORTED_EXTS}"
        )
    return max(candidates, key=lambda p: p.stat().st_size)


def _read_local(path: Path) -> pd.DataFrame:
    ext = path.suffix.lower()
    if ext == ".csv":
        return pd.read_csv(path)
    if ext == ".tsv":
        return pd.read_csv(path, sep="\t")
    if ext == ".parquet":
        return pd.read_parquet(path)
    if ext == ".feather":
        return pd.read_feather(path)
    if ext in (".json", ".jsonl"):
        return pd.read_json(path, lines=ext == ".jsonl")
    raise ValueError(f"Unsupported extension: {ext}")


def load_raw(file_path: str = DEFAULT_FILE_PATH) -> pd.DataFrame:
    """Load the dataset from Kaggle via kagglehub (no caching).

    If `file_path` is empty, the dataset is downloaded locally via
    `kagglehub.dataset_download` and the largest supported tabular file
    is read directly with pandas (avoids the pandas-adapter re-download path).
    """
    import kagglehub
    from kagglehub import KaggleDatasetAdapter

    if not file_path:
        local = _discover_local_file()
        return _read_local(local)

    return kagglehub.load_dataset(
        KaggleDatasetAdapter.PANDAS,
        DATASET_SLUG,
        file_path,
    )


def load(
    file_path: str = DEFAULT_FILE_PATH,
    *,
    use_cache: bool = True,
    refresh: bool = False,
) -> pd.DataFrame:
    """Load + clean + cache the dataset.

    - On first run (or `refresh=True`) downloads via kagglehub, normalizes
      columns / dtypes, and writes a parquet cache to `data/earthquakes.parquet`.
    - Subsequent runs read the parquet directly.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if use_cache and CACHE_PARQUET.exists() and not refresh:
        return pd.read_parquet(CACHE_PARQUET)

    df = load_raw(file_path)
    df = _normalize_columns(df)
    df = _coerce_types(df)

    # Drop rows without the bare essentials for downstream steps.
    required = [c for c in ("time", "latitude", "longitude", "magnitude") if c in df.columns]
    if required:
        df = df.dropna(subset=required).reset_index(drop=True)

    if "time" in df.columns:
        df = df.sort_values("time").reset_index(drop=True)

    if use_cache:
        df.to_parquet(CACHE_PARQUET, index=False)

    return df


def summary(df: Optional[pd.DataFrame] = None) -> dict:
    """Return a small dict summary suitable for the CLI `info` command."""
    if df is None:
        df = load()
    info: dict = {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
    }
    if "time" in df.columns and len(df):
        info["time_min"] = str(df["time"].min())
        info["time_max"] = str(df["time"].max())
    if "magnitude" in df.columns and len(df):
        info["magnitude_min"] = float(df["magnitude"].min())
        info["magnitude_max"] = float(df["magnitude"].max())
        info["magnitude_mean"] = float(df["magnitude"].mean())
    return info
