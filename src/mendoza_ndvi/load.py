from datetime import date

import odc.stac
import xarray as xr

from mendoza_ndvi.search import UTM_CRS

SCALE = 1e-4
BARE_SOIL = 5

SHIFT_FROM = date(2022, 1, 25)
SHIFT_TO = date(2022, 2, 24)


def dn_shift(item):
    """DN to add to a secnes stored values so reflectance = (DN + shift) * 1e-4"""
    p = item.properties
    in_window = SHIFT_FROM <= item.datetime.date() <= SHIFT_TO
    if (
        p.get("s2:processing_baseline") == "04.00"
        and p.get("earthsearch:boa_offset_applied") is False
        and in_window
    ):
        band = item.assets["red"].extra_fields.get("raster:bands", [{}])[0]
        return round((band.get("offset") or -0.1) / (band.get("scale") or SCALE))
    return 0


def load_group(items, shift, bbox, res):
    """Load scenes that need the same DN shift. return float32 reflectance (NaN = no data)."""
    raw = odc.stac.load(
        items,
        bands=["red", "nir", "scl"],
        bbox=bbox,
        crs=UTM_CRS,
        resolution=res,
        groupby="solar_day",
        chunks={"x": 1024, "y": 1024},
        resampling="nearest",
    )
    out = xr.Dataset()
    for band in ("red", "nir"):
        dn = raw[band].astype("float32")
        refl = ((dn + shift) * SCALE).clip(min=0)
        out[band] = refl.where(raw[band] != 0)
    out["scl"] = raw["scl"].astype("float32").where(raw["scl"] != 0)
    return out.assign_coords(time=raw.time.dt.floor("D"))


def load_reflectance(items, bbox, res=20):
    """Lazy dataset of red, nir, and scl. one slice per date"""
    odc.stac.configure_rio(cloud_defaults=True, aws={"aws_unsigned": True})
    groups = {}
    for i in items:
        groups.setdefault(dn_shift(i), []).append(i)

    parts = [load_group(g, shift, bbox, res) for shift, g in groups.items()]
    ds = parts[0]
    for part in parts[1:]:
        ds = ds.combine_first(part)
    return ds.sortby("time")


def bare_soil_red(ds):
    """Median red reflectance of SCL not vegetated pixels, per date"""
    return ds.red.where(ds.scl == BARE_SOIL).median(dim=("y", "x"), skipna=True)
