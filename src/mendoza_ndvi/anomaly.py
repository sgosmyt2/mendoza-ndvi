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


def climatology(comp_dir, years, month, min_valid=MIN_VALID, min_years=MIN_YEARS):
    """Per pixel mean and std of one calendar month across the baseline years"""
    layers = [load_month(comp_dir, y, month, min_valid)[0] for y in years]
    stack = xr.concat(layers, dim=pd.Index(list(years), name="year"))
    n = stack.count("year")
    ok = n >= min_years
    return xr.Dataset(
        {
            "mean": stack.mean("year", skipna=True).where(ok),
            "std": stack.std("year", skipna=True, ddof=1).where(ok),
            "n_years": n.astype("uint8"),
        }
    )
