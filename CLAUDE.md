# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands

```bash
make install          # Create .venv (Python 3.12) and install deps
make data             # Download comuna GeoJSON + generate synthetic Excel data
make run              # Start dashboard at http://localhost:8050
make clean            # Remove .venv and generated data
```

First-time setup: `make data && make run`. The `install` target is a dependency of both `data` and `run`, so it runs automatically.

The venv lives at `.venv/` and uses Python 3.12. No test suite exists yet.

## Architecture

ARIA is a **Dash** (Flask-based) criminal intelligence dashboard for Chile's Metropolitan Region (Santiago). It runs 100% locally — no data leaves the machine (Ley 19.628 compliance).

### Data flow

1. **`config.py`** — Central constants: coordinate ranges, crime type normalization map, CRS codes (EPSG:32719 for calculations, EPSG:4326 for display), classification thresholds.
2. **`ingesta.py`** — Reads monthly `.xlsx`/`.csv` files from `data/` (named `mes_año.xlsx`, e.g. `enero_2025.xlsx`), validates coordinates, normalizes crime types via `config.MAPA_NORMALIZACION`, assigns comunas via GeoPandas spatial join against `data/comunas_santiago.geojson`.
3. **`calculos.py`** — Spatial analysis: mean center, Standard Deviational Ellipse (SDE), KDE density, displacement (distance + azimuth between period centroids), Jaccard overlap between ellipses, area variation. All math in EPSG:32719 (meters), output in WGS84.
4. **`app.py`** — Entry point. Loads data into `DF_GLOBAL` at module level, creates the Dash app, renders the shell (topbar, sidebar nav, bottombar), and delegates to modules. Also contains the executive summary ("Panorama") layout and all navigation callbacks.

### Module pattern

Each module in `modules/` follows the same contract:
- `get_layout()` → returns a Dash `html.Div` component tree
- `registrar_callbacks(app, ...)` → registers Dash callbacks on the app instance

Modules receive shared state (e.g. `DF_GLOBAL`, `PERIODOS`, `FENOMENOS`) as arguments to `registrar_callbacks`. The active module is tracked via a `dcc.Store(id="active-module")`.

**Active modules:** movilidad (spatial mobility), emergentes (emerging crime detection), analisis_avanzado (Near Repeat / NNI / Network KDE), agrupador_casos (Claude API case grouping), policy_brief_ia (Claude API policy brief generation).

**Placeholder modules** (planned, not implemented): defined in `modules/placeholder.py` as a dictionary of metadata rendered with a generic "coming soon" layout.

### Claude API integration

`agrupador_casos.py` and `policy_brief_ia.py` call the Claude API with a privacy protocol: Level 2 pseudonymization — no direct identifiers (names, RUT, addresses) may be sent. API key comes from `.env` file (`ANTHROPIC_API_KEY`). Both modules gracefully degrade if the key is missing.

### Scripts

`scripts/` contains one-time utilities, not part of the running app:
- `descargar_comunas.py` — Downloads Santiago comuna boundaries from OpenStreetMap (Nominatim → osmnx → Overpass fallback chain)
- `generar_sinteticos_v2.py` — Generates 12 months of realistic synthetic crime data with per-comuna weighting, hourly distributions, and spatial drift
- `convertir_comunas.py` — Converts official BCN shapefile to GeoJSON (alternative to downloading)
- `generar_sinteticos.py` — Simpler v1 data generator (superseded by v2)

### Styling

`assets/style.css` is auto-served by Dash. SIRAC v1 aesthetic: dark palette with amber accent, IBM Plex Sans/Mono + Fraunces fonts. CSS variables defined in `:root`. Python files also define color constants inline (these should match the CSS variables).

## Key Conventions

- **Language:** Code (variables, functions, docstrings) must be in English. UI-facing strings (labels, tooltips, narratives) remain in Spanish.
- All coordinates are stored as `(latitud, longitud)` in WGS84. Internal spatial calculations convert to EPSG:32719 (UTM 19S) for metric distances.
- Crime type normalization: raw input → `config.MAPA_NORMALIZACION` lookup → canonical category from `config.TIPOS_PENALES_VALIDOS`. Unrecognized values map to "Otro".
- GeoJSON from OSM may contain `Point` geometries for some comunas (known issue with Santiago). Non-polygon geometries are skipped in the choropleth renderer.
