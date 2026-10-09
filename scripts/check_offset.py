import argparse
from pathlib import Path

import dask
import numpy as np
import odc.stac
import pandas as pd

from mendoza_ndvi.search import UTM_CRS, aoi_bbox, load_aoi, search_items

BARE_SOIL = 5
SWITCH = pd.Timestamp("2022-01-25").date()  # Date where baseline changes


def scale_offset(item, band="red"):
    """Scale and offset recorded in the item's own metadata (None if absent)."""
    rb = item.assets[band].extra_fields.get("raster:bands", [{}])[0]
    return rb.get("scale"), rb.get("offset")
