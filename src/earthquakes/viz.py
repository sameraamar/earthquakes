"""Interactive HTML visualizations: folium map + plotly timeline."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from .data_loader import REPO_ROOT, load

OUTPUT_DIR = REPO_ROOT / "outputs"


def _ensure_outputs() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def build_map(
    df: Optional[pd.DataFrame] = None,
    *,
    sample: int = 20_000,
    min_magnitude: float = 4.5,
    out_path: Optional[Path] = None,
) -> Path:
    """Render a folium map of earthquakes to HTML.

    - Filters to `magnitude >= min_magnitude` to keep the map responsive.
    - Down-samples to `sample` rows if still larger.
    """
    import folium
    from folium.plugins import MarkerCluster

    if df is None:
        df = load()

    plot_df = df.copy()
    if "magnitude" in plot_df.columns:
        plot_df = plot_df[plot_df["magnitude"] >= min_magnitude]
    if len(plot_df) > sample:
        plot_df = plot_df.sample(sample, random_state=42)

    fmap = folium.Map(location=[20, 0], zoom_start=2, tiles="cartodbpositron")
    cluster = MarkerCluster().add_to(fmap)

    for row in plot_df.itertuples(index=False):
        mag = float(getattr(row, "magnitude", 0) or 0)
        radius = max(2.0, mag * 1.4)
        popup = (
            f"<b>M {mag:.1f}</b><br>"
            f"{getattr(row, 'time', '')}<br>"
            f"depth: {getattr(row, 'depth', 'n/a')} km<br>"
            f"{getattr(row, 'place', '')}"
        )
        folium.CircleMarker(
            location=(float(row.latitude), float(row.longitude)),
            radius=radius,
            color=_mag_color(mag),
            weight=1,
            fill=True,
            fill_opacity=0.6,
            popup=folium.Popup(popup, max_width=300),
        ).add_to(cluster)

    out = out_path or (_ensure_outputs() / "map.html")
    fmap.save(str(out))
    return out


def build_timeline(
    df: Optional[pd.DataFrame] = None,
    *,
    min_magnitude: float = 5.0,
    out_path: Optional[Path] = None,
) -> Path:
    """Render a plotly scatter timeline of magnitude over time to HTML."""
    import plotly.express as px

    if df is None:
        df = load()

    plot_df = df.copy()
    if "magnitude" in plot_df.columns:
        plot_df = plot_df[plot_df["magnitude"] >= min_magnitude]
    plot_df = plot_df.dropna(subset=["time", "magnitude"])

    fig = px.scatter(
        plot_df,
        x="time",
        y="magnitude",
        color="depth" if "depth" in plot_df.columns else None,
        color_continuous_scale="Viridis",
        hover_data=[c for c in ("place", "latitude", "longitude", "depth") if c in plot_df.columns],
        title=f"Earthquakes timeline (M ≥ {min_magnitude})",
        opacity=0.6,
    )
    fig.update_layout(template="plotly_white", height=600)

    out = out_path or (_ensure_outputs() / "timeline.html")
    fig.write_html(str(out), include_plotlyjs="cdn")
    return out


def _mag_color(mag: float) -> str:
    if mag >= 7.0:
        return "#7a0177"
    if mag >= 6.0:
        return "#c51b8a"
    if mag >= 5.0:
        return "#f768a1"
    if mag >= 4.0:
        return "#fbb4b9"
    return "#feebe2"


def build_all(df: Optional[pd.DataFrame] = None) -> dict[str, Path]:
    if df is None:
        df = load()
    return {
        "map": build_map(df),
        "timeline": build_timeline(df),
    }
