# Research Notes

## Purpose
Scratchpad for findings, dataset quirks, modeling experiments, and links.
Read before starting work that touches the data or model.

## Maintenance
- Updated by: Anyone (Human or AI) who learns something worth keeping.
- Append-only style; date each entry.

---

## 2026-04-22 — Dataset
- Source: Kaggle `alessandrolobello/the-ultimate-earthquake-dataset-from-1990-2023`.
- Loader: `kagglehub` with `KaggleDatasetAdapter.PANDAS`.
- Expected fields (based on similar USGS-derived datasets): time, latitude,
  longitude, depth, magnitude, place. Confirm at load time and update
  `data_loader._normalize_columns` if names differ.

## Open questions
- Which file inside the dataset is canonical? `file_path=""` loads default;
  confirm with `kagglehub` listing if multiple files exist.
- Magnitude type (Mw vs ML vs mb) handling.
