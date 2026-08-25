# Artifact Manifest

Canonical project location:

```text
outputs/bhopal-alphaearth-app
```

Online repository:

```text
https://github.com/Prashannajeet/GEOAI
```

## Canonical App Files

| Path | Purpose | Status |
| --- | --- | --- |
| `streamlit_app.py` | Main Streamlit application and real AlphaEarth COG processing pipeline. | Active |
| `requirements.txt` | Python dependency list for local and Streamlit Cloud deployment. | Active |
| `data/bhopal_alphaearth_index.json` | Compact Bhopal-intersecting AlphaEarth tile index. | Active |
| `README.md` | Project overview, local run instructions, deployment notes, and attribution. | Active |
| `.gitignore` | Keeps local runtimes, caches, logs, and secrets out of version control. | Active |
| `VERSION_LOG.md` | Human-readable version history. | Active |
| `ARTIFACT_MANIFEST.md` | Canonical file inventory and consolidation notes. | Active |
| `runtime.txt` | Pins Streamlit Cloud to Python 3.11 for rasterio/GDAL compatibility. | Active |
| `.streamlit/config.toml` | Streamlit deployment/runtime configuration. | Active |

## Reference Artifacts

| Path | Purpose | Status |
| --- | --- | --- |
| `docs/references/bhopal_alphaearth_pilot_gee.js` | Earlier Earth Engine pilot script retained for reference. | Historical |

## Removed Or Excluded Local Artifacts

| Path | Reason |
| --- | --- |
| `.venv/` | Local Python runtime; reproducible from `requirements.txt`. |
| `node_modules/` | Legacy Node prototype runtime; excluded from repo. |
| `__pycache__/` | Python bytecode cache; excluded from repo. |
| `work/alphaearth_manifest.txt` | Large scratch-only global AlphaEarth manifest. Replaced by compact Bhopal index. |

## Versioning Rule

Use semantic versions in `VERSION_LOG.md`:

- Patch: documentation, manifest, or metadata-only updates.
- Minor: new app feature, new AOI, new export type, or UI improvement.
- Major: processing pipeline rewrite or breaking deployment change.

Every future app change should update:

1. `VERSION_LOG.md`
2. `ARTIFACT_MANIFEST.md` if files are added, moved, or retired
3. `README.md` if user-facing behavior changes
