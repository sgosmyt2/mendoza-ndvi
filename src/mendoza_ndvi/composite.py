import xarray as xr

from mendoza_ndvi.mask import valid_mask


def ndvi(ds):
    """(NIR - red) / (NIR + red), NAN where the denominator is not positive"""
    den = ds.nir + ds.red
    return (ds.nir - ds.red) / den.where(den > 0)


def monthly_composite(ds, dilate_px=2, mask_snow=True):
    """Collapse one month of dates into a median NVDI map and a validity map.

    ds: Dataset wiith red, nir, and scl. dims (time, y, x).
    """
    valid = valid_mask(ds.scl, dilate_px=dilate_px, mask_snow=mask_snow)
    nd = ndvi(ds).where(valid)

    median = nd.median(dim="time", skipna=True)
    count = nd.count(dim="time")
    return xr.Dataset(
        {"ndvi": median.astype("float32"), "n_valid": count.astype("uint8")}
    )
