import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import rasterio.shutil
import xarray as xr
from shapely.geometry import box

from mendoza_ndvi.anomaly import MIN_VALID, load_month, zscore
from mendoza_ndvi.search import UTM_CRS
from mendoza_ndvi.zonal import STRATA, add_anomalies, list_months

BAND_NAMES = ("ndvi_diff", "z", "n_valid")


def anomaly_layers(ndvi, clim):
    """Pixel difference from the baseline mean and z score"""
    return ndvi - clim["mean"], zscore(ndvi, clim)


def write_anomaly_cog(path, diff, z, count):
    """3 band float32 COG: ndvi_diff, z, n_valid"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    layers = [diff, z, count.astype("float32")]
    stack = xr.concat(layers, dim=pd.Index([1, 2, 3], name="band")).transpose(
        "band", "y", "x"
    )
    stack = stack.rio.write_crs(UTM_CRS).rio.write_nodata(np.nan)
    tmp = path.with_suffix(".tmp.tif")
    stack.rio.to_raster(tmp, driver="GTiff", tiled=True, compress="deflate")
    with rasterio.open(tmp, "r+") as ds:
        for i, name in enumerate(BAND_NAMES, 1):
            ds.set_band_description(i, name)
    rasterio.shutil.copy(
        tmp,
        path,
        driver="COG",
        compress="DEFLATE",
        predictor=3,
        overview_resampling="AVERAGE",
    )
    tmp.unlink()


def blocks(a, k):
    """Rehsape a 2d array into (cells_y, k, cells_x, k) and padding the edges with NaN"""
    ny, nx = a.shape
    py, px = (-ny) % k, (-nx) % k
    a = np.pad(a.astype("float64"), ((0, py), (0, px)), constant_values=np.nan)
    return a.reshape((ny + py) // k, k, (nx + px) // k, k)


def cell_stats(ndvi, count, k):
    """output per cell mean NDVI, valid fraction and mean count"""
    nd, ct = blocks(ndvi, k), blocks(count, k)
    real = np.isfinite(blocks(np.ones(ndvi.shape), k)).sum(axis=(1, 3))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        mean_ndvi = np.nanmean(nd, axis=(1, 3))
        mean_count = np.nanmean(ct, axis=(1, 3))
    valid_frac = np.isfinite(nd).sum(axis=(1, 3)) / real
    return mean_ndvi, valid_frac, mean_count


def cell_geometry(template, k):
    """Cell ids and polygons for a k * k grid"""
    t = template.rio.transform()
    res = abs(t.a)
    ny, nx = template.shape
    x0, y0 = t.c, t.f
    ids, geoms = [], []
    for iy in range(-(-ny // k)):
        for ix in range(-(-nx // k)):
            xmin, xmax = x0 + ix * k * res, min(x0 + (ix + 1) * k * res, x0 + nx * res)
            ymax, ymin = y0 - iy * k * res, max(y0 - (iy + 1) * k * res, y0 - ny * res)
            ids.append(f"r{iy:02d}c{ix:02d}")
            geoms.append(box(xmin, ymin, xmax, ymax))
    return ids, geoms


def majority_stratum(strata, k):
    """Name of the most common stratum in each cell."""
    fracs = []
    for code in STRATA:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            share = blocks((strata.values == code).astype("float64"), k)
            fracs.append(np.nanmean(share, axis=(1, 3)))
    best = np.argmax(np.stack(fracs), axis=0)
    return np.array(list(STRATA.values()))[best]
