# Bhopal AlphaEarth Change Analysis

Streamlit app for real AlphaEarth satellite embedding change detection over Bhopal, Madhya Pradesh, India.

This app does not use synthetic or fallback hotspot data. It reads public AlphaEarth COGs, computes 64-band embedding change scores, polygonizes high-change areas, and exports the detected hotspots.

## Data Source

- AlphaEarth public COGs: https://data.source.coop/tge-labs/aef/v1/annual/
- Earth Engine catalog page: https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL

Required attribution:

> The AlphaEarth Foundations Satellite Embedding dataset is produced by Google and Google DeepMind.

## Run Locally

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m streamlit run streamlit_app.py
```

On macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## App Workflow

1. Load the public AlphaEarth tile index.
2. Select Bhopal-intersecting COGs in UTM zone `43N`.
3. Read 64 embedding bands for the selected year pair.
4. Dequantize AlphaEarth int8 embeddings.
5. Compute dot-product similarity and convert it to a change score.
6. Threshold high-change pixels.
7. Polygonize connected hotspots.
8. Display results on a pydeck map and export GeoJSON/CSV.

## Default Pilot

- City: Bhopal, Madhya Pradesh, India
- AOI bounds: `77.12,23.03,77.72,23.52`
- Default comparison: `2017` to `2024`
- Default threshold: `0.18`

Verified default run:

```text
hotspots: 6
mean change: 0.088
max change: 0.3403
```

## Deploy On Streamlit Community Cloud

1. Push this repository to GitHub.
2. Open https://share.streamlit.io/
3. Choose this repository.
4. Set the app file to `streamlit_app.py`.
5. Deploy.

No API key is required for the public Source Cooperative COG path.

