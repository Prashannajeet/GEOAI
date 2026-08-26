import json
import math
import os
from collections import deque
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).parent
PROJ_DATA = ROOT / ".venv" / "Lib" / "site-packages" / "rasterio" / "proj_data"
if PROJ_DATA.exists():
    os.environ["PROJ_LIB"] = str(PROJ_DATA)
    os.environ["PROJ_DATA"] = str(PROJ_DATA)

import numpy as np
import pandas as pd
import pydeck as pdk
import rasterio
import streamlit as st
from rasterio.enums import Resampling
from rasterio.warp import transform, transform_bounds
from rasterio.windows import Window


ATTRIBUTION = "The AlphaEarth Foundations Satellite Embedding dataset is produced by Google and Google DeepMind."
INDEX_CSV = "https://data.source.coop/tge-labs/aef/v1/annual/aef_index.csv"
INDEX_CACHE = ROOT / "data" / "bhopal_alphaearth_index.json"
BBOX_WGS84 = {
    "west": 77.12,
    "south": 23.03,
    "east": 77.72,
    "north": 23.52,
}


def intersects(a, b):
    return (
        a["west"] <= b["east"]
        and a["east"] >= b["west"]
        and a["south"] <= b["north"]
        and a["north"] >= b["south"]
    )


def intersection_area(a, b):
    if not intersects(a, b):
        return 0
    return (min(a["east"], b["east"]) - max(a["west"], b["west"])) * (
        min(a["north"], b["north"]) - max(a["south"], b["south"])
    )


def parse_index_line(line):
    if not line.startswith('"'):
        return None
    close = line.find('",')
    if close < 0:
        return None
    rest = line[close + 2 :].strip().split(",")
    if len(rest) < 12:
        return None
    return {
        "crs": rest[0],
        "path": rest[1],
        "year": int(rest[2]),
        "utmZone": rest[3],
        "utm": {
            "west": float(rest[4]),
            "south": float(rest[5]),
            "east": float(rest[6]),
            "north": float(rest[7]),
        },
        "wgs84": {
            "west": float(rest[8]),
            "south": float(rest[9]),
            "east": float(rest[10]),
            "north": float(rest[11]),
        },
        "url": rest[1].replace("s3://us-west-2.opendata.source.coop/", "https://data.source.coop/"),
    }


@st.cache_data(show_spinner=False)
def load_bhopal_index():
    if INDEX_CACHE.exists():
        return json.loads(INDEX_CACHE.read_text())

    INDEX_CACHE.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with urlopen(INDEX_CSV) as response:
        for raw in response:
            line = raw.decode("utf-8", errors="ignore")
            if ",43N," not in line:
                continue
            row = parse_index_line(line)
            if not row or row["crs"] != "EPSG:32643":
                continue
            if row["year"] < 2017 or row["year"] > 2025:
                continue
            if intersects(row["wgs84"], BBOX_WGS84):
                rows.append(row)

    if not rows:
        raise RuntimeError("No Bhopal-intersecting AlphaEarth COGs found in the public index.")

    INDEX_CACHE.write_text(json.dumps(rows, indent=2))
    return rows


def select_tile(index, year):
    candidates = [row for row in index if row["year"] == year]
    candidates.sort(key=lambda row: intersection_area(row["wgs84"], BBOX_WGS84), reverse=True)
    if not candidates:
        raise RuntimeError(f"No AlphaEarth COG found for {year} over Bhopal.")
    return candidates[0]


def dequantize(array):
    data = array.astype("float32")
    invalid = data == -128
    data = data / 127.5
    data = data * data * np.sign(data)
    data[invalid] = np.nan
    return data


def read_window(url, width):
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff",
        GDAL_HTTP_MAX_RETRY="3",
        GDAL_HTTP_RETRY_DELAY="2",
        GDAL_HTTP_TIMEOUT="60",
    ):
        with rasterio.open(url) as src:
            bbox = transform_bounds(
                "EPSG:4326",
                src.crs,
                BBOX_WGS84["west"],
                BBOX_WGS84["south"],
                BBOX_WGS84["east"],
                BBOX_WGS84["north"],
                densify_pts=21,
            )
            aspect = abs((bbox[3] - bbox[1]) / (bbox[2] - bbox[0]))
            height = max(64, int(round(width * aspect)))
            affine = src.transform
            col_a = (bbox[0] - affine.c) / affine.a
            col_b = (bbox[2] - affine.c) / affine.a
            row_a = (bbox[1] - affine.f) / affine.e
            row_b = (bbox[3] - affine.f) / affine.e
            window = Window(
                math.floor(min(col_a, col_b)),
                math.floor(min(row_a, row_b)),
                math.ceil(max(col_a, col_b)) - math.floor(min(col_a, col_b)),
                math.ceil(max(row_a, row_b)) - math.floor(min(row_a, row_b)),
            )
            data = src.read(
                indexes=list(range(1, 65)),
                window=window,
                out_shape=(64, height, width),
                boundless=True,
                fill_value=-128,
                resampling=Resampling.bilinear,
            )
            return data, bbox, src.crs.to_string(), width, height


def utm_to_wgs84(crs, xs, ys):
    lon, lat = transform(crs, "EPSG:4326", xs, ys)
    return [[round(x, 6), round(y, 6)] for x, y in zip(lon, lat)]


def polygonize(mask, scores, bbox, crs, threshold):
    height, width = mask.shape
    visited = np.zeros(mask.shape, dtype=bool)
    pixel_width = (bbox[2] - bbox[0]) / width
    pixel_height = (bbox[3] - bbox[1]) / height
    features = []

    for row in range(height):
        for col in range(width):
            if not mask[row, col] or visited[row, col]:
                continue

            queue = deque([(row, col)])
            visited[row, col] = True
            cells = []
            total = 0.0
            max_score = 0.0
            min_row = max_row = row
            min_col = max_col = col

            while queue:
                r, c = queue.pop()
                value = float(scores[r, c])
                cells.append((r, c))
                total += value
                max_score = max(max_score, value)
                min_row = min(min_row, r)
                max_row = max(max_row, r)
                min_col = min(min_col, c)
                max_col = max(max_col, c)

                for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                    if nr < 0 or nc < 0 or nr >= height or nc >= width:
                        continue
                    if mask[nr, nc] and not visited[nr, nc]:
                        visited[nr, nc] = True
                        queue.append((nr, nc))

            if len(cells) < 8:
                continue

            west = bbox[0] + min_col * pixel_width
            east = bbox[0] + (max_col + 1) * pixel_width
            north = bbox[3] - min_row * pixel_height
            south = bbox[3] - (max_row + 1) * pixel_height
            ring = utm_to_wgs84(crs, [west, east, east, west, west], [south, south, north, north, south])

            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [ring]},
                    "properties": {
                        "mean_change": total / len(cells),
                        "max_change": max_score,
                        "pixel_count": len(cells),
                        "area_ha": len(cells) * pixel_width * pixel_height / 10000,
                        "threshold": threshold,
                    },
                }
            )

    features.sort(key=lambda f: f["properties"]["mean_change"], reverse=True)
    for rank, feature in enumerate(features, start=1):
        feature["properties"]["rank"] = rank
    return features


@st.cache_data(show_spinner=False)
def analyze(start_year, end_year, threshold, resolution):
    index = load_bhopal_index()
    start_tile = select_tile(index, start_year)
    end_tile = select_tile(index, end_year)
    start_data, bbox, crs, width, height = read_window(start_tile["url"], resolution)
    end_data, _, _, _, _ = read_window(end_tile["url"], resolution)

    start_vec = dequantize(start_data)
    end_vec = dequantize(end_data)
    dot = np.nansum(start_vec * end_vec, axis=0)
    valid = np.all(np.isfinite(start_vec), axis=0) & np.all(np.isfinite(end_vec), axis=0)
    scores = np.clip(1 - dot, 0, 2)
    scores[~valid] = 0
    features = polygonize((scores >= threshold) & valid, scores, bbox, crs, threshold)
    valid_scores = scores[valid]

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "city": "Bhopal, Madhya Pradesh, India",
            "startYear": start_year,
            "endYear": end_year,
            "threshold": threshold,
            "resolution": {"width": width, "height": height},
            "validPixels": int(valid.sum()),
            "meanChange": float(valid_scores.mean()) if valid_scores.size else 0,
            "maxChange": float(valid_scores.max()) if valid_scores.size else 0,
            "startTile": start_tile["path"],
            "endTile": end_tile["path"],
            "attribution": ATTRIBUTION,
            "source": "https://data.source.coop/tge-labs/aef/v1/annual/",
        },
    }


def feature_table(geojson):
    rows = []
    for feature in geojson["features"]:
        props = feature["properties"]
        rows.append(
            {
                "rank": props["rank"],
                "area_ha": round(props["area_ha"], 2),
                "mean_change": round(props["mean_change"], 3),
                "max_change": round(props["max_change"], 3),
                "pixel_count": props["pixel_count"],
            }
        )
    return pd.DataFrame(rows)


def pydeck_data(geojson):
    rows = []
    for feature in geojson["features"]:
        props = feature["properties"]
        score = props["mean_change"]
        color = [111, 76, 163, 130] if score >= 0.24 else [216, 101, 45, 120] if score >= 0.20 else [214, 164, 49, 115]
        rows.append(
            {
                "polygon": feature["geometry"]["coordinates"][0],
                "rank": props["rank"],
                "mean_change": props["mean_change"],
                "area_ha": props["area_ha"],
                "color": color,
            }
        )
    return pd.DataFrame(rows)


st.set_page_config(page_title="Bhopal AlphaEarth", layout="wide")
st.title("Bhopal AlphaEarth Change Analysis")
st.caption("Real AlphaEarth COG-based embedding change detection. No synthetic hotspot layer.")

with st.sidebar:
    st.header("Run analysis")
    start_year = st.selectbox("Start year", [2017, 2018, 2019, 2020, 2021, 2022, 2023], index=0)
    end_year = st.selectbox("End year", [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025], index=6)
    threshold = st.slider("Change threshold", 0.05, 0.45, 0.18, 0.01)
    resolution = st.slider("Processing grid width", 120, 420, 220, 20)
    run = st.button("Run real analysis", type="primary", use_container_width=True)
    st.divider()
    index = load_bhopal_index()
    st.write(f"{len(index)} Bhopal tile records indexed")
    st.write(ATTRIBUTION)

if end_year <= start_year:
    st.error("End year must be later than start year.")
    st.stop()

if "latest_geojson" not in st.session_state:
    st.session_state.latest_geojson = None

if run:
    with st.spinner("Reading AlphaEarth COG pixels and computing 64-band change scores..."):
        try:
            st.session_state.latest_geojson = analyze(start_year, end_year, threshold, resolution)
        except Exception as exc:
            st.session_state.latest_geojson = None
            st.error(f"Real AlphaEarth analysis failed: {exc}")
            st.stop()

geojson = st.session_state.latest_geojson
if geojson is None:
    st.info("Choose a year pair and click Run real analysis to read AlphaEarth COGs and compute Bhopal hotspots.")
    st.stop()

metadata = geojson["metadata"]

metric_cols = st.columns(4)
metric_cols[0].metric("Hotspots", len(geojson["features"]))
metric_cols[1].metric("Valid pixels", f"{metadata['validPixels']:,}")
metric_cols[2].metric("Mean change", f"{metadata['meanChange']:.3f}")
metric_cols[3].metric("Max change", f"{metadata['maxChange']:.3f}")

map_df = pydeck_data(geojson)
if not map_df.empty:
    layer = pdk.Layer(
        "PolygonLayer",
        map_df,
        get_polygon="polygon",
        get_fill_color="color",
        get_line_color=[24, 35, 31],
        get_line_width=45,
        line_width_min_pixels=1,
        pickable=True,
    )
    st.pydeck_chart(
        pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            initial_view_state=pdk.ViewState(latitude=23.2599, longitude=77.4126, zoom=10.5),
            layers=[layer],
            tooltip={
                "html": "<b>Rank {rank}</b><br/>Mean change: {mean_change}<br/>Area: {area_ha} ha",
                "style": {"backgroundColor": "#18231f", "color": "white"},
            },
        ),
        use_container_width=True,
    )
else:
    st.info("No hotspots crossed the selected threshold.")

table = feature_table(geojson)
st.dataframe(table, use_container_width=True, hide_index=True)

download_cols = st.columns([1, 1, 4])
download_cols[0].download_button(
    "Download GeoJSON",
    data=json.dumps(geojson, indent=2),
    file_name=f"bhopal-alphaearth-{metadata['startYear']}-{metadata['endYear']}.geojson",
    mime="application/geo+json",
    use_container_width=True,
)
download_cols[1].download_button(
    "Download CSV",
    data=table.to_csv(index=False),
    file_name=f"bhopal-alphaearth-{metadata['startYear']}-{metadata['endYear']}.csv",
    mime="text/csv",
    use_container_width=True,
)

with st.expander("Run metadata"):
    st.json(metadata)
