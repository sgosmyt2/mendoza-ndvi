import argparse
import csv
import time
from datetime import date, timedelta
from pathlib import Path

import dask
import numpy as np
import rioxarray

from mendoza_ndvi.composite import monthly_composite
from mendoza_ndvi.load import load_reflectance
from mendoza_ndvi.search import UTM_CRS, aoi_bbox, load_aoi, search_items


def full_last_month():
    return date.today().replace(day=1) - timedelta(days=1)


def write_month(comp, out_dir, key):
    """Write count_<key>.tif then ndvi_<key>.tif. The NDVI file goes last, so
    its existence means the month finished."""
    comp = comp.rio.write_crs(UTM_CRS)
    comp["n_valid"].rio.to_raster(
        out_dir / f"count_{key}.tif", driver="GTiff", tiled=True, compress="deflate"
    )
    ndvi = comp["ndvi"].rio.write_nodata(np.nan)
    ndvi.rio.to_raster(
        out_dir / f"ndvi_{key}.tif", driver="GTiff", tiled=True, compress="deflate"
    )
