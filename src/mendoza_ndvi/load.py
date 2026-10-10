from datetime import date

import odc.stac
import xarray as xr

from mendoza_ndvi.search import UTM_CRS
from scripts.check_offset import BARE_SOIL

SCALE = 1e-4
BARE_SOIL = 5

SHIFT_FROM = date(2022, 1, 25)
SHIFT_TO = date(2022, 2, 24)


def dn_shift(item):
    """DN to add to a secnes stored values so reflectance = (DN + shift) * 1e-4"""
    p = item.properties
    in_window = SHIFT_FROM <= item.datetime.get() <= SHIFT_TO
    if (
        p.get("s2:processing_baseline") == "04.00"
        and p.get("earthsearch:boa_offset_applied") is False
        and in_window
    ):
        band = item.assets["red"].extra_fields.get("raster:bands", [{}])[0]
        return round((band.get("offset") or -0.1) / (band.get("scale") or SCALE))
    return 0
