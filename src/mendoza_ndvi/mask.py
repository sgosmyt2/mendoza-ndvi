import numpy as np
import xarray as xr

# All these SCL classes will be treated as invalid being no data, saturated, shadow, cloud, or cirrus
INVALID_CLASSES = (0, 1, 3, 8, 9, 10)
SNOW = 11
