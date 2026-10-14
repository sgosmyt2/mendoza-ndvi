from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from mendoza_ndvi.anomaly import MIN_VALID, climatology, load_month

STRATA = {0: "bare", 1: "mixed", 2: "vegetated"}
UNKNOWN = 255
MIN_STD = 0.01


def make_strata(comp_dir, years, months=(1, 2, 3), edges=(0.3, 0.4)):
    """Static stratum map from the baseline mean of NDVI of the given calendar months.

    0 = bare or spares, 1 = mixed, 2 = vegetation and 255 = unknown
    """
    means = [climatology(comp_dir, years, m)["mean"] for m in months]
    base = xr.concat(means, dim="m").mean("m", skipna=True)
    codes = np.digitize(base.values, edges).astype("uint8")
    codes[np.isnan(base.values)] = UNKNOWN
    return base.copy(data=codes)
