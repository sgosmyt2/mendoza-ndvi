import numpy as np
import xarray as xr

# All these SCL classes will be treated as invalid being no data, saturated, shadow, cloud, or cirrus
INVALID_CLASSES = (0, 1, 3, 8, 9, 10)
SNOW = 11


def dilate(mask, px):
    """Grow true regions of a (time, y, x) boolean array by px pixels"""
    if px <= 0:
        return mask
    padded = np.pad(mask, ((0, 0), (px, px), (px, px)))
    h, w = mask.shape[-2:]
    out = np.zeros_like(mask)
    for dy in range(2 * px + 1):
        for dx in range(2 * px + 1):
            out |= padded[:, dy : dy + h, dx : dx + w]
    return out


def valid_mask(scl, dilate_px=2, mask_snow=True):
    """True where a pixel is usable. scl is a (time, y, x) datarray"""
    scl = scl.transpose("time", "y", "x")
    vals = scl.values
    classes = INVALID_CLASSES + ((SNOW,) if mask_snow else ())
    invalid = np.isin(vals, classes) | np.isnan(vals)
    invalid = dilate(invalid, dilate_px)
    return xr.DataArray(~invalid, coords=scl.coords, dims=scl.dims)
