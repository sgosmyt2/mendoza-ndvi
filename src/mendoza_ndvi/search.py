import json
from pathlib import Path

import pandas as pd
from pystac_client import Client

STAC_URL = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-12a"
AOI_PATH = Path(__file__).resolve().parents[2] / "aoi" / "uco_valley.geojson"
UTM_CRS = "EPSG:32719"
