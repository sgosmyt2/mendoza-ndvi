import json
from pathlib import Path

import pandas as pd
from pystac_client import Client

STAC_URL = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-12a"
AOI_PATH = Path(__file__).resolve().parents[2] / "aoi" / "uco_valley.geojson"
UTM_CRS = "EPSG:32719"


def load_aoi(aoi_path):
    """Return the first polygon geometry of AOI geojson"""
    gj = json.loads(Path(aoi_path).read_text())
    return gj["features"][0]["geometry"] if gj["type"] == "FeatureCollection" else gj


def aoi_bbox(geom):
    pts = [pt for ring in geom["coordinates"] for pt in ring]
    xs, ys = zip(*pts)
    return min(xs), min(ys), max(xs), max(ys)
