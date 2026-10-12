import xarray as xr

from mendoza_ndvi.mask import valid_mask


def ndvi(ds):
    """(NIR - red) / (NIR + red), NAN where the denominator is not positive"""
    den = ds.nir + ds.red
    return (ds.nir - ds.red) / den.where(den > 0)
