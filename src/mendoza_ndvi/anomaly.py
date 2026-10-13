from pathlib import Path

import pandas as pd
import rioxarray
import xarray as xr

MIN_VALID = 2
MIN_YEARS = 4
MIN_STD = 0.02


def load_month(comp_dir, year, month, min_valid=MIN_VALID):
    """(ndvi, count) for one month, NDVI is NaN where count < min_valid"""
    comp_dir = Path(comp_dir)
    key = f"{year}_{month:02d}"
    ndvi = rioxarray.open_rasterio(comp_dir / f"ndvi_{key}.tif", masked=True)
    count = rioxarray.open_rasterio(comp_dir / f"count_{key}.tif")
    ndvi = ndvi.squeeze("band", drop=True)
    count = count.squeeze("band", drop=True)
    return ndvi.where(count >= min_valid), count
