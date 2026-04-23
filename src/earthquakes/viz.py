"""Interactive HTML visualizations: leaflet map + plotly timeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd

from .data_loader import REPO_ROOT, SOURCES, load

OUTPUT_DIR = REPO_ROOT / "outputs"


def _ensure_outputs() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


# --- map color scale (kept for reference / used by template legend) ---
_MAG_BANDS = [
    (7.0, "#7a0177", "M \u2265 7"),
    (6.0, "#c51b8a", "6 \u2264 M < 7"),
    (5.0, "#f768a1", "5 \u2264 M < 6"),
    (4.0, "#fbb4b9", "4 \u2264 M < 5"),
    (-99.0, "#feebe2", "M < 4"),
]


def _mag_color(mag: float) -> str:
    for thr, color, _ in _MAG_BANDS:
        if mag >= thr:
            return color
    return _MAG_BANDS[-1][1]


_MAP_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Earthquakes map</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/nouislider@15.7.1/dist/nouislider.min.css" />
<style>
 html, body { margin:0; height:100%; font-family: system-ui, sans-serif; }
 #app { display:flex; height:100vh; }
 #map { flex:1; }
 #panel {
   width: 320px; padding: 14px 16px; overflow-y:auto;
   background:#fafafa; border-left:1px solid #ddd; box-sizing:border-box;
 }
 #panel h2 { margin:0 0 6px 0; font-size:18px; }
 #panel h3 { margin:18px 0 6px 0; font-size:13px; text-transform:uppercase; letter-spacing:.05em; color:#555; }
 .row { font-size:12px; color:#333; margin-bottom: 6px; }
 .slider { margin: 36px 10px 6px 10px; }
 .legend-item { display:flex; align-items:center; gap:8px; font-size:12px; margin:2px 0; }
 .legend-swatch { width:14px; height:14px; border-radius:50%; border:1px solid #999; }
 .src-row { display:flex; align-items:flex-start; gap:6px; font-size:12px; margin: 4px 0; }
 .src-row .src-meta { display:flex; flex-direction:column; line-height:1.25; }
 .src-row .src-code { font-weight:600; }
 .src-row .src-title { color:#555; font-size:11px; }
 .src-row a { color:#1565c0; text-decoration:none; }
 .src-row a:hover { text-decoration:underline; }
 .stats { font-size:12px; color:#666; }
 button.reset { margin-top:10px; padding:6px 10px; font-size:12px; cursor:pointer; }
 /* colored magnitude track */
 #mag-slider .noUi-connects { background: transparent; }
 #mag-slider .noUi-connect  { background: transparent; }
 #mag-slider .noUi-base     { background: var(--mag-gradient, #ccc); border-radius:3px; }
 #mag-slider .noUi-handle   { box-shadow: 0 0 0 1px #555; }
</style>
</head>
<body>
<div id="app">
 <div id="map"></div>
 <div id="panel">
   <h2>Earthquakes</h2>
   <div class="stats">
     Showing <b id="visible-count">0</b> of <b id="total-count">0</b> events.
   </div>

   <h3>Magnitude</h3>
   <div id="mag-slider" class="slider"></div>
   <div class="row">Range: <span id="mag-range"></span></div>

   <h3>Time range</h3>
   <div id="time-slider" class="slider"></div>
   <div class="row">From <span id="time-from"></span> to <span id="time-to"></span></div>
   <div class="row">
     Quick: <a href="#" data-window="1y">1y</a> ·
     <a href="#" data-window="5y">5y</a> ·
     <a href="#" data-window="10y">10y</a> ·
     <a href="#" data-window="all">all</a>
   </div>

   <h3>Sources</h3>
   <div id="sources"></div>

   <h3>Magnitude legend</h3>
   <div id="legend"></div>

   <button class="reset" id="reset-btn">Reset filters</button>
 </div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/nouislider@15.7.1/dist/nouislider.min.js"></script>
<script>
const EQ_DATA   = __DATA__;
const SOURCES   = __SOURCES__;
const MAG_BANDS = __BANDS__;
const META      = __META__;

function magColor(m) {
  for (const b of MAG_BANDS) { if (m >= b.thr) return b.color; }
  return MAG_BANDS[MAG_BANDS.length-1].color;
}
function fmtDate(ms) {
  const d = new Date(ms);
  return d.toISOString().slice(0,10);
}

const map = L.map('map', { worldCopyJump:true }).setView([20,0], 2);
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png', {
  attribution:'&copy; OpenStreetMap, &copy; CARTO', subdomains:'abcd', maxZoom:19
}).addTo(map);

const layer = L.layerGroup().addTo(map);

// ---- legend ----
const legendEl = document.getElementById('legend');
MAG_BANDS.forEach(b => {
  const div = document.createElement('div');
  div.className = 'legend-item';
  div.innerHTML = `<span class="legend-swatch" style="background:${b.color}"></span>${b.label}`;
  legendEl.appendChild(div);
});

// ---- source checkboxes ----
const srcContainer = document.getElementById('sources');
const srcState = {};
SOURCES.forEach(s => {
  srcState[s.code] = true;
  const row = document.createElement('label');
  row.className = 'src-row';
  const link = s.url
    ? ` <a href="${s.url}" target="_blank" rel="noopener" title="Open dataset page">source \u2197</a>`
    : '';
  const titleLine = s.title
    ? `<span class="src-title">${s.title}${link}</span>`
    : (link ? `<span class="src-title">${link.trim()}</span>` : '');
  row.innerHTML = `
    <input type="checkbox" data-code="${s.code}" checked>
    <span class="src-meta">
      <span class="src-code">${s.code} <span style="color:#888;font-weight:normal">(${s.count.toLocaleString()})</span></span>
      ${titleLine}
    </span>`;
  srcContainer.appendChild(row);
});
srcContainer.addEventListener('change', e => {
  if (e.target && e.target.matches('input[type=checkbox]')) {
    srcState[e.target.dataset.code] = e.target.checked;
    refresh();
  }
});

// ---- magnitude slider ----
const magSlider = document.getElementById('mag-slider');
noUiSlider.create(magSlider, {
  start: [META.mag_min, META.mag_max],
  connect: true, range: { min: META.mag_min, max: META.mag_max }, step: 0.1,
  tooltips: [{ to: v => Number(v).toFixed(1) }, { to: v => Number(v).toFixed(1) }]
});

// paint the magnitude track with the legend colors as a gradient
(function paintMagTrack() {
  const lo = META.mag_min, hi = META.mag_max, span = hi - lo;
  // sort bands ascending by threshold so we walk left->right
  const bands = MAG_BANDS.slice().sort((a,b) => a.thr - b.thr);
  // build [start, color] stops; clamp first threshold to lo
  const stops = [];
  for (let i = 0; i < bands.length; i++) {
    const start = Math.max(lo, bands[i].thr);
    const end   = (i+1 < bands.length) ? Math.max(lo, bands[i+1].thr) : hi;
    if (end <= lo) continue;
    const p1 = ((start - lo) / span) * 100;
    const p2 = ((end   - lo) / span) * 100;
    stops.push(`${bands[i].color} ${p1.toFixed(2)}%`);
    stops.push(`${bands[i].color} ${p2.toFixed(2)}%`);
  }
  magSlider.style.setProperty('--mag-gradient', `linear-gradient(to right, ${stops.join(', ')})`);
})();

// ---- time slider ----
const timeSlider = document.getElementById('time-slider');
noUiSlider.create(timeSlider, {
  start: [META.time_min, META.time_max],
  connect: true, range: { min: META.time_min, max: META.time_max }
});

// ---- quick time windows ----
document.querySelectorAll('a[data-window]').forEach(a => {
  a.addEventListener('click', e => {
    e.preventDefault();
    const w = a.dataset.window;
    if (w === 'all') {
      timeSlider.noUiSlider.set([META.time_min, META.time_max]);
    } else {
      const years = parseInt(w);
      const end = META.time_max;
      const start = end - years * 365.25 * 86400 * 1000;
      timeSlider.noUiSlider.set([Math.max(start, META.time_min), end]);
    }
  });
});

// ---- refresh ----
const visibleCount = document.getElementById('visible-count');
const totalCount   = document.getElementById('total-count');
totalCount.textContent = EQ_DATA.length.toLocaleString();
const magRange  = document.getElementById('mag-range');
const timeFromEl= document.getElementById('time-from');
const timeToEl  = document.getElementById('time-to');

function refresh() {
  const [mLo, mHi] = magSlider.noUiSlider.get().map(Number);
  const [tLo, tHi] = timeSlider.noUiSlider.get().map(Number);
  magRange.textContent = `${mLo.toFixed(1)} \u2013 ${mHi.toFixed(1)}`;
  timeFromEl.textContent = fmtDate(tLo);
  timeToEl.textContent   = fmtDate(tHi);

  layer.clearLayers();
  let n = 0;
  for (const e of EQ_DATA) {
    if (e.m < mLo || e.m > mHi) continue;
    if (e.t < tLo || e.t > tHi) continue;
    let srcOk = false;
    for (const c of e.s) { if (srcState[c]) { srcOk = true; break; } }
    if (!srcOk) continue;
    n++;
    L.circleMarker([e.lat, e.lon], {
      radius: Math.max(1, e.m * 0.6),
      color: magColor(e.m), weight: 1, fillOpacity: 0.6
    }).bindPopup(
      `<b>M ${e.m.toFixed(1)}</b><br>${fmtDate(e.t)}<br>` +
      (e.d != null ? `depth: ${e.d.toFixed(1)} km<br>` : '') +
      (e.p ? e.p : '') +
      `<br><small>source: ${e.s.join(', ')}</small>`
    ).addTo(layer);
  }
  visibleCount.textContent = n.toLocaleString();
}

magSlider.noUiSlider.on('update', refresh);
timeSlider.noUiSlider.on('update', refresh);

document.getElementById('reset-btn').addEventListener('click', () => {
  magSlider.noUiSlider.set([META.mag_min, META.mag_max]);
  timeSlider.noUiSlider.set([META.time_min, META.time_max]);
  SOURCES.forEach(s => { srcState[s.code] = true; });
  document.querySelectorAll('#sources input').forEach(i => { i.checked = true; });
  refresh();
});

refresh();
</script>
</body>
</html>
"""


def build_map(
    df: Optional[pd.DataFrame] = None,
    *,
    sample: int = 20_000,
    min_magnitude: float = 4.5,
    out_path: Optional[Path] = None,
    cluster: bool = False,  # kept for CLI back-compat; ignored by Leaflet template
) -> Path:
    """Render an interactive Leaflet map with magnitude/time/source filters.

    - Filters to ``magnitude >= min_magnitude`` to keep the page responsive.
    - Down-samples to ``sample`` rows if still larger.
    - The output HTML is self-contained (CDN-hosted Leaflet + noUiSlider) and
      provides three live filters: magnitude range, time range, and per-source
      checkboxes.
    """
    del cluster  # accepted for CLI back-compat; not used here

    if df is None:
        df = load()

    plot_df = df.copy()
    if "magnitude" in plot_df.columns:
        plot_df = plot_df[plot_df["magnitude"] >= min_magnitude]
    plot_df = plot_df.dropna(subset=["time", "latitude", "longitude", "magnitude"])
    if len(plot_df) > sample:
        plot_df = plot_df.sample(sample, random_state=42)

    # Source counts (each row's `source` field can be a comma-joined list).
    source_codes: dict[str, int] = {}
    for s in plot_df["source"].fillna("").astype(str):
        for code in (c for c in s.split(",") if c):
            source_codes[code] = source_codes.get(code, 0) + 1
    sources_payload = []
    for code, count in sorted(source_codes.items(), key=lambda x: -x[1]):
        meta = SOURCES.get(code)
        title = ""
        url = ""
        if meta is not None:
            # Pull the human-readable title from the citation (text before the
            # first " Kaggle" / " https" marker).
            cit = meta.citation
            for marker in (", Kaggle", ". Kaggle", ". https", " https"):
                idx = cit.find(marker)
                if idx > 0:
                    title = cit[:idx].strip().strip(",")
                    break
            if not title:
                title = cit
            if meta.slug:
                url = f"https://www.kaggle.com/datasets/{meta.slug}"
            else:
                # Pull the first http(s) URL out of the citation.
                for token in cit.split():
                    if token.startswith("http"):
                        url = token.rstrip(".,)")
                        break
        sources_payload.append(
            {"code": code, "count": count, "title": title, "url": url}
        )

    epoch_ms = (plot_df["time"].astype("datetime64[ns, UTC]").astype("int64") // 10**6).tolist()
    payload = []
    has_depth = "depth" in plot_df.columns
    has_place = "place" in plot_df.columns
    for i, row in enumerate(plot_df.itertuples(index=False)):
        srcs = [c for c in str(getattr(row, "source", "") or "").split(",") if c]
        depth = float(row.depth) if has_depth and pd.notna(row.depth) else None
        place = (str(row.place) if has_place and pd.notna(row.place) else "")[:120]
        payload.append({
            "lat": round(float(row.latitude), 4),
            "lon": round(float(row.longitude), 4),
            "m":   round(float(row.magnitude), 2),
            "d":   None if depth is None else round(depth, 1),
            "p":   place,
            "t":   epoch_ms[i],
            "s":   srcs,
        })

    bands_payload = [{"thr": thr, "color": color, "label": label} for thr, color, label in _MAG_BANDS]
    meta = {
        "mag_min": float(plot_df["magnitude"].min()),
        "mag_max": float(plot_df["magnitude"].max()),
        "time_min": int(min(epoch_ms)),
        "time_max": int(max(epoch_ms)),
    }

    html = (
        _MAP_TEMPLATE
        .replace("__DATA__", json.dumps(payload, separators=(",", ":")))
        .replace("__SOURCES__", json.dumps(sources_payload))
        .replace("__BANDS__", json.dumps(bands_payload))
        .replace("__META__", json.dumps(meta))
    )

    out = out_path or (_ensure_outputs() / "map.html")
    out.write_text(html, encoding="utf-8")
    return out


_TIMELINE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Earthquakes timeline</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/nouislider@15.7.1/dist/nouislider.min.css" />
<style>
 html, body { margin:0; height:100%; font-family: system-ui, sans-serif; }
 #app { display:flex; height:100vh; }
 #plot { flex:1; min-width:0; }
 #panel {
   width: 320px; padding: 14px 16px; overflow-y:auto;
   background:#fafafa; border-left:1px solid #ddd; box-sizing:border-box;
 }
 #panel h2 { margin:0 0 6px 0; font-size:18px; }
 #panel h3 { margin:18px 0 6px 0; font-size:13px; text-transform:uppercase; letter-spacing:.05em; color:#555; }
 .row { font-size:12px; color:#333; margin-bottom: 6px; }
 .slider { margin: 36px 10px 6px 10px; }
 .src-row { display:flex; align-items:flex-start; gap:6px; font-size:12px; margin: 4px 0; }
 .src-row .src-meta { display:flex; flex-direction:column; line-height:1.25; }
 .src-row .src-code { font-weight:600; }
 .src-row .src-title { color:#555; font-size:11px; }
 .src-row a { color:#1565c0; text-decoration:none; }
 .src-row a:hover { text-decoration:underline; }
 .stats { font-size:12px; color:#666; }
 button.reset { margin-top:10px; padding:6px 10px; font-size:12px; cursor:pointer; }
 #mag-slider .noUi-base { background: var(--mag-gradient, #ccc); border-radius:3px; }
 #mag-slider .noUi-connects, #mag-slider .noUi-connect { background: transparent; }
 #mag-slider .noUi-handle { box-shadow: 0 0 0 1px #555; }
</style>
</head>
<body>
<div id="app">
 <div id="plot"></div>
 <div id="panel">
   <h2>Earthquakes timeline</h2>
   <div class="stats">Showing <b id="visible-count">0</b> of <b id="total-count">0</b> events.</div>

   <h3>Magnitude</h3>
   <div id="mag-slider" class="slider"></div>
   <div class="row">Range: <span id="mag-range"></span></div>

   <h3>Depth (km)</h3>
   <div id="depth-slider" class="slider"></div>
   <div class="row">Range: <span id="depth-range"></span></div>

   <h3>Time range</h3>
   <div id="time-slider" class="slider"></div>
   <div class="row">From <span id="time-from"></span> to <span id="time-to"></span></div>
   <div class="row">
     Quick: <a href="#" data-window="1y">1y</a> ·
     <a href="#" data-window="5y">5y</a> ·
     <a href="#" data-window="10y">10y</a> ·
     <a href="#" data-window="all">all</a>
   </div>

   <h3>Sources</h3>
   <div id="sources"></div>

   <button class="reset" id="reset-btn">Reset filters</button>
 </div>
</div>

<script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/nouislider@15.7.1/dist/nouislider.min.js"></script>
<script>
const EQ_DATA   = __DATA__;
const SOURCES   = __SOURCES__;
const META      = __META__;
const MAG_BANDS = __BANDS__;
const HAS_DEPTH = __HAS_DEPTH__;

function fmtDate(ms){ return new Date(ms).toISOString().slice(0,10); }

// ---- magnitude track gradient (matches map legend) ----
function paintMagTrack() {
  const lo = META.mag_min, hi = META.mag_max, span = hi - lo;
  const bands = MAG_BANDS.slice().sort((a,b) => a.thr - b.thr);
  const stops = [];
  for (let i = 0; i < bands.length; i++) {
    const start = Math.max(lo, bands[i].thr);
    const end   = (i+1 < bands.length) ? Math.max(lo, bands[i+1].thr) : hi;
    if (end <= lo) continue;
    const p1 = ((start - lo) / span) * 100;
    const p2 = ((end   - lo) / span) * 100;
    stops.push(`${bands[i].color} ${p1.toFixed(2)}%`);
    stops.push(`${bands[i].color} ${p2.toFixed(2)}%`);
  }
  document.getElementById('mag-slider').style.setProperty(
    '--mag-gradient', `linear-gradient(to right, ${stops.join(', ')})`);
}

// ---- source rows ----
const srcContainer = document.getElementById('sources');
const srcState = {};
SOURCES.forEach(s => {
  srcState[s.code] = true;
  const row = document.createElement('label');
  row.className = 'src-row';
  const link = s.url
    ? ` <a href="${s.url}" target="_blank" rel="noopener" title="Open dataset page">source \u2197</a>`
    : '';
  const titleLine = s.title
    ? `<span class="src-title">${s.title}${link}</span>`
    : (link ? `<span class="src-title">${link.trim()}</span>` : '');
  row.innerHTML = `
    <input type="checkbox" data-code="${s.code}" checked>
    <span class="src-meta">
      <span class="src-code">${s.code} <span style="color:#888;font-weight:normal">(${s.count.toLocaleString()})</span></span>
      ${titleLine}
    </span>`;
  srcContainer.appendChild(row);
});
srcContainer.addEventListener('change', e => {
  if (e.target && e.target.matches('input[type=checkbox]')) {
    srcState[e.target.dataset.code] = e.target.checked;
    refresh();
  }
});

// ---- sliders ----
const magSlider = document.getElementById('mag-slider');
noUiSlider.create(magSlider, {
  start: [META.mag_min, META.mag_max],
  connect: true, range: { min: META.mag_min, max: META.mag_max }, step: 0.1,
  tooltips: [{ to: v => Number(v).toFixed(1) }, { to: v => Number(v).toFixed(1) }],
});
paintMagTrack();

const depthSlider = document.getElementById('depth-slider');
if (HAS_DEPTH) {
  noUiSlider.create(depthSlider, {
    start: [META.depth_min, META.depth_max],
    connect: true, range: { min: META.depth_min, max: META.depth_max },
    tooltips: [{ to: v => Number(v).toFixed(0) }, { to: v => Number(v).toFixed(0) }],
  });
} else {
  depthSlider.style.display = 'none';
  document.getElementById('depth-range').parentElement.style.display = 'none';
  depthSlider.previousElementSibling.style.display = 'none';
}

const timeSlider = document.getElementById('time-slider');
noUiSlider.create(timeSlider, {
  start: [META.time_min, META.time_max],
  connect: true, range: { min: META.time_min, max: META.time_max },
});

document.querySelectorAll('a[data-window]').forEach(a => {
  a.addEventListener('click', e => {
    e.preventDefault();
    const w = a.dataset.window;
    if (w === 'all') {
      timeSlider.noUiSlider.set([META.time_min, META.time_max]);
    } else {
      const years = parseInt(w);
      const end = META.time_max;
      const start = end - years * 365.25 * 86400 * 1000;
      timeSlider.noUiSlider.set([Math.max(start, META.time_min), end]);
    }
  });
});

document.getElementById('reset-btn').addEventListener('click', () => {
  magSlider.noUiSlider.set([META.mag_min, META.mag_max]);
  if (HAS_DEPTH) depthSlider.noUiSlider.set([META.depth_min, META.depth_max]);
  timeSlider.noUiSlider.set([META.time_min, META.time_max]);
  SOURCES.forEach(s => { srcState[s.code] = true; });
  document.querySelectorAll('#sources input').forEach(i => { i.checked = true; });
  refresh();
});

// ---- plot ----
const visibleCount = document.getElementById('visible-count');
const totalCount   = document.getElementById('total-count');
totalCount.textContent = EQ_DATA.length.toLocaleString();
const magRangeEl   = document.getElementById('mag-range');
const depthRangeEl = document.getElementById('depth-range');
const timeFromEl   = document.getElementById('time-from');
const timeToEl     = document.getElementById('time-to');

const plotEl = document.getElementById('plot');
let plotInited = false;

function selectedRows() {
  const [mLo, mHi] = magSlider.noUiSlider.get().map(Number);
  const [tLo, tHi] = timeSlider.noUiSlider.get().map(Number);
  const [dLo, dHi] = HAS_DEPTH ? depthSlider.noUiSlider.get().map(Number) : [null, null];
  const x = [], y = [], color = [], text = [];
  for (const e of EQ_DATA) {
    if (e.m < mLo || e.m > mHi) continue;
    if (e.t < tLo || e.t > tHi) continue;
    if (HAS_DEPTH && e.d != null && (e.d < dLo || e.d > dHi)) continue;
    let srcOk = false;
    for (const c of e.s) { if (srcState[c]) { srcOk = true; break; } }
    if (!srcOk) continue;
    x.push(new Date(e.t));
    y.push(e.m);
    color.push(e.d == null ? null : e.d);
    text.push(`${e.p || ''}<br>M ${e.m.toFixed(1)}` + (e.d == null ? '' : `, depth ${e.d.toFixed(0)} km`) + `<br>${fmtDate(e.t)}<br>src: ${e.s.join(',')}`);
  }
  return { x, y, color, text, mLo, mHi, tLo, tHi, dLo, dHi };
}

function refresh() {
  const r = selectedRows();
  magRangeEl.textContent = `${r.mLo.toFixed(1)} \u2013 ${r.mHi.toFixed(1)}`;
  if (HAS_DEPTH) depthRangeEl.textContent = `${r.dLo.toFixed(0)} \u2013 ${r.dHi.toFixed(0)} km`;
  timeFromEl.textContent = fmtDate(r.tLo);
  timeToEl.textContent   = fmtDate(r.tHi);
  visibleCount.textContent = r.x.length.toLocaleString();

  const trace = {
    x: r.x, y: r.y, text: r.text, hoverinfo: 'text',
    mode: 'markers', type: 'scattergl',
    marker: {
      size: 6, opacity: 0.6,
      color: HAS_DEPTH ? r.color : r.y,
      colorscale: 'Viridis',
      showscale: true,
      colorbar: { title: HAS_DEPTH ? 'depth (km)' : 'magnitude' },
    },
  };
  const layout = {
    margin: { l: 50, r: 10, t: 30, b: 40 },
    xaxis: { title: 'time' },
    yaxis: { title: 'magnitude' },
    hovermode: 'closest',
    template: 'plotly_white',
  };
  if (!plotInited) {
    Plotly.newPlot(plotEl, [trace], layout, { responsive: true, displaylogo: false });
    plotInited = true;
  } else {
    Plotly.react(plotEl, [trace], layout);
  }
}

magSlider.noUiSlider.on('update', refresh);
if (HAS_DEPTH) depthSlider.noUiSlider.on('update', refresh);
timeSlider.noUiSlider.on('update', refresh);
window.addEventListener('resize', () => { if (plotInited) Plotly.Plots.resize(plotEl); });
refresh();
</script>
</body>
</html>
"""


def build_timeline(
    df: Optional[pd.DataFrame] = None,
    *,
    min_magnitude: float = 5.0,
    sample: int = 30_000,
    out_path: Optional[Path] = None,
) -> Path:
    """Render an interactive timeline with magnitude/depth/time/source filters."""
    if df is None:
        df = load()

    plot_df = df.copy()
    if "magnitude" in plot_df.columns:
        plot_df = plot_df[plot_df["magnitude"] >= min_magnitude]
    plot_df = plot_df.dropna(subset=["time", "magnitude"])
    if len(plot_df) > sample:
        plot_df = plot_df.sample(sample, random_state=42)

    has_depth = "depth" in plot_df.columns and plot_df["depth"].notna().any()
    has_place = "place" in plot_df.columns

    # Source counts + payload (mirrors build_map).
    source_codes: dict[str, int] = {}
    for s in plot_df["source"].fillna("").astype(str):
        for code in (c for c in s.split(",") if c):
            source_codes[code] = source_codes.get(code, 0) + 1
    sources_payload = []
    for code, count in sorted(source_codes.items(), key=lambda x: -x[1]):
        meta = SOURCES.get(code)
        title = ""
        url = ""
        if meta is not None:
            cit = meta.citation
            for marker in (", Kaggle", ". Kaggle", ". https", " https"):
                idx = cit.find(marker)
                if idx > 0:
                    title = cit[:idx].strip().strip(",")
                    break
            if not title:
                title = cit
            if meta.slug:
                url = f"https://www.kaggle.com/datasets/{meta.slug}"
            else:
                for token in cit.split():
                    if token.startswith("http"):
                        url = token.rstrip(".,)")
                        break
        sources_payload.append(
            {"code": code, "count": count, "title": title, "url": url}
        )

    epoch_ms = (plot_df["time"].astype("datetime64[ns, UTC]").astype("int64") // 10**6).tolist()
    payload = []
    for i, row in enumerate(plot_df.itertuples(index=False)):
        srcs = [c for c in str(getattr(row, "source", "") or "").split(",") if c]
        depth = float(row.depth) if has_depth and pd.notna(row.depth) else None
        place = str(row.place) if has_place and pd.notna(row.place) else ""
        payload.append({
            "m": float(row.magnitude),
            "d": depth,
            "p": place,
            "t": int(epoch_ms[i]),
            "s": srcs,
        })

    meta = {
        "mag_min": float(plot_df["magnitude"].min()),
        "mag_max": float(plot_df["magnitude"].max()),
        "time_min": int(min(epoch_ms)) if epoch_ms else 0,
        "time_max": int(max(epoch_ms)) if epoch_ms else 0,
    }
    if has_depth:
        meta["depth_min"] = float(plot_df["depth"].min())
        meta["depth_max"] = float(plot_df["depth"].max())

    bands_payload = [
        {"thr": float(thr), "color": color, "label": label}
        for thr, color, label in _MAG_BANDS
    ]

    html = (
        _TIMELINE_TEMPLATE
        .replace("__DATA__", json.dumps(payload))
        .replace("__SOURCES__", json.dumps(sources_payload))
        .replace("__META__", json.dumps(meta))
        .replace("__BANDS__", json.dumps(bands_payload))
        .replace("__HAS_DEPTH__", "true" if has_depth else "false")
    )

    out = out_path or (_ensure_outputs() / "timeline.html")
    out.write_text(html, encoding="utf-8")
    return out


def build_all(
    df: Optional[pd.DataFrame] = None,
    *,
    cluster: bool = True,
    sample: int = 20_000,
    min_magnitude: float = 4.5,
) -> dict[str, Path]:
    if df is None:
        df = load()
    return {
        "map": build_map(df, cluster=cluster, sample=sample, min_magnitude=min_magnitude),
        "timeline": build_timeline(df),
    }
