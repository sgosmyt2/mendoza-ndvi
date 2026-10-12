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
