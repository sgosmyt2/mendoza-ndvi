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
