# Version Log

This log tracks the Bhopal AlphaEarth app versions and the artifacts retained in the canonical repository.

## v1.1.2 - Streamlit Startup Reliability

Date: 2026-08-27

- Stopped the app from auto-running remote AlphaEarth COG analysis on initial page load.
- Added explicit run-time error handling so source connectivity issues are shown in the UI instead of breaking startup.
- Added GDAL HTTP retry, timeout, and COG extension settings for remote raster reads.

## v1.1.1 - Streamlit Cloud Deployment Hardening

Date: 2026-08-25

- Added `runtime.txt` to pin Streamlit Cloud to Python 3.11 for stable rasterio/GDAL wheel support.
- Added `.streamlit/config.toml` with headless server configuration and disabled Streamlit usage telemetry.

## v1.1.0 - Consolidated Project Structure

Date: 2026-08-11

- Established `outputs/bhopal-alphaearth-app` as the single canonical local project folder.
- Moved the earlier Google Earth Engine pilot script into `docs/references/`.
- Removed the large scratch-only global AlphaEarth manifest from `work/`; the app retains the compact Bhopal tile index in `data/bhopal_alphaearth_index.json`.
- Added artifact and version tracking documents.

## v1.0.0 - Streamlit Real-Data App

Date: 2026-08-11

- Published the Streamlit implementation to `Prashannajeet/GEOAI`.
- Reads real public AlphaEarth COGs from Source Cooperative.
- Computes 64-band embedding change scores for Bhopal.
- Displays hotspot polygons with pydeck.
- Exports GeoJSON and CSV.
- Verified default run:

```text
comparison: 2017-2024
hotspots: 6
mean change: 0.088
max change: 0.3403
```

## v0.3.0 - Local Node/Rasterio Prototype

Date: 2026-08-11

- Built a backend-driven local app that used Node for the API and Python/rasterio for COG reads.
- Confirmed `geotiff.js` could not decode AlphaEarth Zstandard-compressed COGs.
- Switched real raster access to rasterio/GDAL.
- Superseded by the Streamlit app.

## v0.2.0 - Browser UI Prototype

Date: 2026-08-11

- Built an initial browser UI for controls, map/table layout, and exports.
- Removed from the canonical published repo because it used a local demo hotspot layer.
- Superseded by real COG-based processing.

## v0.1.0 - Earth Engine Pilot Script

Date: 2026-08-11

- Created a Google Earth Engine script for Bhopal AlphaEarth change analysis.
- Retained as a reference in `docs/references/bhopal_alphaearth_pilot_gee.js`.
- Superseded for app hosting by the Streamlit implementation.
