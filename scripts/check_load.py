import argparse
import calendar
from pathlib import Path

import dask
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from mendoza_ndvi.load import bare_soil_red, load_reflectance
from mendoza_ndvi.search import aoi_bbox, load_aoi, search_items
