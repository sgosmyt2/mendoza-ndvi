import json
import time
from pathlib import Path

import pandas as pd
from pystac_client import Client
from pystac_client.exceptions import APIError

STAC_URL = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-l2a"
AOI_PATH = Path(__file__).resolve().parents[2] / "aoi" / "uco_valley.geojson"
UTM_CRS = "EPSG:32719"


def load_aoi(aoi_path=AOI_PATH):
    """Return the first polygon geometry of AOI geojson"""
    gj = json.loads(Path(aoi_path).read_text())
    return gj["features"][0]["geometry"] if gj["type"] == "FeatureCollection" else gj


def aoi_bbox(geom):
    pts = [pt for ring in geom["coordinates"] for pt in ring]
    xs, ys = zip(*pts)
    return min(xs), min(ys), max(xs), max(ys)


def year_chunks(start, end):
    """Split [start, end] into calendar year pieces, as YYYY-MM-DD string pairs"""
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    chunks = []
    cur = s
    while cur <= e:
        stop = min(pd.Timestamp(year=cur.year, month=12, day=31), e)
        chunks.append((cur.strftime("%Y-%m-%d"), stop.strftime("%Y-%m-%d")))
        cur = stop + pd.Timedelta(days=1)
    return chunks


def search_items(geom, start, end, collection=COLLECTION, retries=4):
    """All L2A items intersecting the AOI between start and end dates"""
    client = Client.open(STAC_URL)
    items = []
    for a, b in year_chunks(start, end):
        for attempt in range(retries):
            try:
                search = client.search(
                    collections=[collection],
                    intersects=geom,
                    datetime=f"{a}/{b}",
                    limit=100,
                )
                chunk = list(search.items())
                break
            except APIError as err:
                if attempt == retries - 1:
                    raise
                wait = 2 ** (attempt + 1)
                print(f"    server error for {a}/{b} ({err}); retrying in {wait}s")
                time.sleep(wait)
        print(f"    {a} -> {b}: {len(chunk)} items")
        items.extend(chunk)
    return items


def items_to_frame(items):
    """Flatten STAC items into a table"""
    cols = [
        "id",
        "datetime",
        "cloud_cover",
        "tile",
        "baseline",
        "nodata_pct",
        "boa_offset_applied",
    ]
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
                "boa_offset_applied": p.get("earthsearch:boa_offset_applied"),
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


def usable_dates_table(df, max_cloud):
    """Year x month table: distinct dates with at least one scene under max_cloud.

    Scene cloud cover is only a rough guide, the real mask is pixel level (SCL).
    """
    ok = df[df["cloud_cover"] <= max_cloud]
    table = ok.groupby(["year", "month"])["date"].nunique().unstack(fill_value=0)
    years = range(int(df["year"].min()), int(df["year"].max()) + 1)
    return table.reindex(index=years, columns=range(1, 13), fill_value=0)
