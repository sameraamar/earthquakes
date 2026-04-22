"""Load + cache earthquake datasets from multiple sources as one tidy pandas DataFrame.

Data sources (each row in the output carries a `source` column tagging its
origin; if a row is matched in multiple datasets the codes are joined with
commas, e.g. ``"LOBELLO,GAURAV2025"``):

- ``LOBELLO``    — Alessandro Lobello, "The Ultimate Earthquake Dataset
                    from 1990-2023", Kaggle.
                    https://www.kaggle.com/datasets/alessandrolobello/the-ultimate-earthquake-dataset-from-1990-2023
- ``GAURAV2025`` — Gaurav Kumar, "Global Earthquake Dataset 2015-2025",
                    Kaggle.
                    https://www.kaggle.com/datasets/gauravkumar2525/global-earthquake-dataset-2015-2025
- ``NOAA_SIG``   — NOAA NCEI/WDS Global Significant Earthquake Database
                    (2150 BC → present, ~5,700 events). Opt-in (not in
                    ``DEFAULT_SOURCES``) because it overlaps the others only
                    at high magnitudes and pre-1678 rows have ``time = NaT``.
                    https://www.ngdc.noaa.gov/hazel/view/hazards/earthquake/search
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

_SUPPORTED_EXTS = (".csv", ".tsv", ".parquet", ".feather", ".json", ".jsonl")

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
CACHE_PARQUET = DATA_DIR / "earthquakes.parquet"


@dataclass(frozen=True)
class DataSource:
    code: str            # short uppercase ref name, <= 10 chars
    slug: str            # kaggle dataset slug ("" for non-Kaggle sources)
    citation: str        # human-readable citation for README / output
    # Optional custom fetcher for non-Kaggle sources. Returns a raw DataFrame.
    fetcher: Optional[Callable[[], pd.DataFrame]] = field(default=None, repr=False)

    def __post_init__(self) -> None:  # pragma: no cover - simple guard
        if not self.code.replace("_", "").isalnum() or len(self.code) > 10 or not self.code.isupper():
            raise ValueError(f"Invalid source code: {self.code!r}")


SOURCES: dict[str, DataSource] = {
    "LOBELLO": DataSource(
        code="LOBELLO",
        slug="alessandrolobello/the-ultimate-earthquake-dataset-from-1990-2023",
        citation=(
            "Alessandro Lobello, 'The Ultimate Earthquake Dataset from 1990-2023', "
            "Kaggle. "
            "https://www.kaggle.com/datasets/alessandrolobello/the-ultimate-earthquake-dataset-from-1990-2023"
        ),
    ),
    "GAURAV2025": DataSource(
        code="GAURAV2025",
        slug="gauravkumar2525/global-earthquake-dataset-2015-2025",
        citation=(
            "Gaurav Kumar, 'Global Earthquake Dataset 2015-2025', Kaggle. "
            "https://www.kaggle.com/datasets/gauravkumar2525/global-earthquake-dataset-2015-2025"
        ),
    ),
    "NOAA_SIG": DataSource(
        code="NOAA_SIG",
        slug="",
        citation=(
            "NOAA National Centers for Environmental Information (NCEI/WDS), "
            "'Global Significant Earthquake Database, 2150 BC to Present'. "
            "https://www.ngdc.noaa.gov/hazel/view/hazards/earthquake/search"
        ),
        fetcher=lambda: _fetch_noaa_significant(),
    ),
}

DEFAULT_SOURCES: tuple[str, ...] = ("LOBELLO", "GAURAV2025")

# Common column-name variants we want to normalize.
_COLUMN_ALIASES = {
    "time": ["time", "date_time", "datetime", "date", "origin_time", "time (utc)"],
    "latitude": ["latitude", "lat"],
    "longitude": ["longitude", "lon", "lng", "long"],
    "depth": ["depth", "depth_km", "depth (km)"],
    "magnitude": ["magnitude", "mag", "magnitudo", "earthquake magnitude"],
    "place": ["place", "location", "region", "country", "place_description", "city"],
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename known column variants to a stable canonical schema.

    After renaming the first matching alias to its canonical name, any
    remaining columns that are aliases of an already-canonical column are
    dropped — this prevents stale duplicates like ``"Time (UTC)"`` from
    coexisting with the canonical ``"time"`` column.
    """
    lower_map = {c.lower(): c for c in df.columns}
    rename: dict[str, str] = {}
    for canonical, aliases in _COLUMN_ALIASES.items():
        # Skip only when the *exact* canonical name already exists -- a column
        # like "Latitude" must still be renamed to "latitude".
        if canonical in df.columns:
            continue
        for alias in aliases:
            if alias in lower_map:
                rename[lower_map[alias]] = canonical
                break
    if rename:
        df = df.rename(columns=rename)

    # Drop orphan alias columns whose canonical column already exists.
    drop: list[str] = []
    cols_lower = {c.lower(): c for c in df.columns}
    for canonical, aliases in _COLUMN_ALIASES.items():
        if canonical not in df.columns:
            continue
        for alias in aliases:
            if alias == canonical:
                continue
            orig = cols_lower.get(alias)
            if orig and orig != canonical:
                drop.append(orig)
    if drop:
        df = df.drop(columns=list(dict.fromkeys(drop)))
    return df


def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    if "time" in df.columns:
        s = df["time"]
        # Numeric epoch (this dataset uses milliseconds) vs string timestamps.
        if pd.api.types.is_numeric_dtype(s):
            # Heuristic: large values (>= ~year 2001 in ms) are milliseconds,
            # smaller numeric epochs are seconds.
            unit = "ms" if s.dropna().abs().median() > 1e11 else "s"
            df["time"] = pd.to_datetime(s, unit=unit, errors="coerce", utc=True)
        else:
            df["time"] = pd.to_datetime(s, errors="coerce", utc=True)
    for col in ("latitude", "longitude", "depth", "magnitude"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _discover_local_file(slug: str) -> Path:
    """Download the dataset locally and return the largest supported tabular file."""
    import kagglehub

    local_dir = Path(kagglehub.dataset_download(slug))
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
        try:
            return pd.read_csv(path)
        except Exception:
            # Fallback for files the fast C engine can't tokenize.
            return pd.read_csv(path, engine="python")
    if ext == ".tsv":
        return pd.read_csv(path, sep="\t")
    if ext == ".parquet":
        return pd.read_parquet(path)
    if ext == ".feather":
        return pd.read_feather(path)
    if ext in (".json", ".jsonl"):
        return pd.read_json(path, lines=ext == ".jsonl")
    raise ValueError(f"Unsupported extension: {ext}")


def _preprocess_gaurav2025(df: pd.DataFrame) -> pd.DataFrame:
    """Combine the split ``Date`` + ``Time (UTC)`` columns into a single timestamp."""
    if "Date" in df.columns and "Time (UTC)" in df.columns:
        combined = df["Date"].astype(str).str.strip() + " " + df["Time (UTC)"].astype(str).str.strip()
        df = df.drop(columns=["Date", "Time (UTC)"]).assign(time=pd.to_datetime(combined, errors="coerce", utc=True))
    return df


# --- NOAA NCEI/WDS Significant Earthquake Database -------------------------

_NOAA_API_URL = "https://www.ngdc.noaa.gov/hazel/hazard-service/api/v1/earthquakes"
_NOAA_FIELD_RENAME = {
    "eqDepth": "depth",
    "eqMagnitude": "magnitude",
    "country": "place",
}


def _fetch_noaa_significant(timeout: float = 60.0) -> pd.DataFrame:
    """Fetch all pages of the NOAA significant-earthquake list as a raw DataFrame."""
    import requests

    frames: list[pd.DataFrame] = []
    page = 1
    while True:
        resp = requests.get(_NOAA_API_URL, params={"page": page}, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
        items = payload.get("items", []) if isinstance(payload, dict) else payload
        if not items:
            break
        frames.append(pd.DataFrame(items))
        total_pages = payload.get("totalPages", page) if isinstance(payload, dict) else page
        if page >= total_pages:
            break
        page += 1
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def _preprocess_noaa_significant(df: pd.DataFrame) -> pd.DataFrame:
    """Build a canonical `time` from year/month/day fields and rename columns.

    pandas datetimes can't represent BC or pre-1678 timestamps; those rows
    get ``time = NaT`` and will be dropped by the standard `dropna(subset=...)`
    in `_load_one`. The original year/month/day columns are preserved.
    """
    df = df.rename(columns={k: v for k, v in _NOAA_FIELD_RENAME.items() if k in df.columns})
    if "time" not in df.columns:
        n = len(df)
        zeros = pd.Series([0] * n, index=df.index)

        def _num(col: str, default: pd.Series) -> pd.Series:
            if col not in df.columns:
                return default
            return pd.to_numeric(df[col], errors="coerce").fillna(default)

        parts = pd.DataFrame({
            "year": _num("year", pd.Series([pd.NA] * n, index=df.index)),
            "month": _num("month", zeros + 1),
            "day": _num("day", zeros + 1),
            "hour": _num("hour", zeros),
            "minute": _num("minute", zeros),
            "second": _num("second", zeros).astype(int),
        })
        safe = parts["year"].between(1678, 2261)
        out = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")
        if safe.any():
            out.loc[safe] = pd.to_datetime(parts.loc[safe], errors="coerce", utc=True)
        df = df.assign(time=out)
    return df


_SOURCE_PREPROCESSORS = {
    "GAURAV2025": _preprocess_gaurav2025,
    "NOAA_SIG": _preprocess_noaa_significant,
}


def load_raw(source_code: str) -> pd.DataFrame:
    """Download (or read from cache) one source dataset, raw — no normalization."""
    if source_code not in SOURCES:
        raise KeyError(f"Unknown source code: {source_code!r}. Known: {list(SOURCES)}")
    src = SOURCES[source_code]
    if src.fetcher is not None:
        return src.fetcher()
    local = _discover_local_file(src.slug)
    return _read_local(local)


def _load_one(source_code: str) -> pd.DataFrame:
    """Load + normalize + tag one source with its `source` code."""
    df = load_raw(source_code)
    pre = _SOURCE_PREPROCESSORS.get(source_code)
    if pre is not None:
        df = pre(df)
    df = _normalize_columns(df)
    df = _coerce_types(df)
    required = [c for c in ("time", "latitude", "longitude", "magnitude") if c in df.columns]
    if required:
        df = df.dropna(subset=required).reset_index(drop=True)
    df["source"] = source_code
    return df


def _merge_sources(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Concat sources and dedup on (time-second, lat 0.01°, lon 0.01°).

    For matched rows, the `source` codes are concatenated with commas
    (sorted, unique) so the provenance of every kept row is preserved.
    """
    if not frames:
        return pd.DataFrame()
    if len(frames) == 1:
        return frames[0]

    df = pd.concat(frames, ignore_index=True, sort=False)
    if not {"time", "latitude", "longitude"}.issubset(df.columns):
        return df

    # Deduplication key: rounded to reduce float jitter / sub-second drift
    # between different aggregators of the same USGS / catalogue events.
    df["_key_t"] = df["time"].dt.floor("s")
    df["_key_lat"] = df["latitude"].round(2)
    df["_key_lon"] = df["longitude"].round(2)

    merged_sources = (
        df.groupby(["_key_t", "_key_lat", "_key_lon"])["source"]
        .agg(lambda s: ",".join(sorted(set(s))))
        .rename("source")
    )
    df = (
        df.drop(columns=["source"])
        .drop_duplicates(subset=["_key_t", "_key_lat", "_key_lon"], keep="first")
        .merge(merged_sources, on=["_key_t", "_key_lat", "_key_lon"], how="left")
        .drop(columns=["_key_t", "_key_lat", "_key_lon"])
    )
    return df


def load(
    *,
    sources: tuple[str, ...] = DEFAULT_SOURCES,
    use_cache: bool = True,
    refresh: bool = False,
) -> pd.DataFrame:
    """Load + clean + cache the configured sources as a single DataFrame.

    - On first run (or `refresh=True`) downloads each source via kagglehub,
      normalizes columns / dtypes, tags each row with a `source` code,
      merges duplicates across sources, and writes a parquet cache.
    - Subsequent runs read the parquet directly.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if use_cache and CACHE_PARQUET.exists() and not refresh:
        return pd.read_parquet(CACHE_PARQUET)

    frames = [_load_one(code) for code in sources]
    df = _merge_sources(frames)

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
    if "source" in df.columns and len(df):
        info["sources"] = df["source"].value_counts().to_dict()
    info["citations"] = {code: src.citation for code, src in SOURCES.items()}
    return info
