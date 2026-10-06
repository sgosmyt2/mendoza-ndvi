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


def search_items(geom, start, end):
    """All L2A items intersecting the AOI between start and end dates"""
    client = Client.open(STAC_URL)
    search = client.search(
        collections=[COLLECTION],
        intersects=geom,
        datetime=f"{start}/{end}",
        limit=500,
    )
    return list(search.items())


def items_to_frame(items):
    """Flatten STAC items into a table"""
    cols = ["id", "datetime", "cloud_cover", "tile", "baseline", "nodata_pct"]
    rows = []
    for i in items:
        p = i.properties
        rows.append(
            {
                "id": i.id,
                "datetime": i.datetime,
                "cloud_cover": p.get("eo:cloud_cover"),
                "tile": p.get("grid:code"),
                "baseline": p.get("s2:processing_baseline"),
                "nodata_pct": p.get("s2:nodata_pixel_percentage"),
            }
        )
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return df
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df["date"] = df["datetime"].dt.date
    df["year"] = df["datetime"].dt.year
    df["month"] = df["datetime"].dt.month

    return df.sort_values("datetime").reset_index(drop=True)
