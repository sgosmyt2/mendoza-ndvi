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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2021-11-01")
    ap.add_argument("--end", default="2022-03-31")
    ap.add_argument("--res", type=int, default=60)
    ap.add_argument("--min-pixels", type=int, default=500)
    ap.add_argument("--out", default="data")
    args = ap.parse_args()

    geom = load_aoi()
    items = search_items(geom, args.start, args.end)

    odc.stac.configure_rio(cloud_defaults=True, aws={"aws_unsigned": True})
    ds = odc.stac.load(
        items,
        bands=["red", "nir", "scl"],
        bbox=aoi_bbox(geom),
        crs=UTM_CRS,
        resolution=args.res,
        groupby="id",
        chunks={"x": 1024, "y": 1024},
        resampling="nearest",
    )
    print(f"red dtype: {ds.red.dtype}, attrs: {ds.red.attrs}")
    with dask.config.set(scheduler="threads", num_workers=16):
        ds = ds.compute()

    by_time = {pd.Timestamp(it.datetime).tz_convert(None): it for it in items}
    if len(by_time) != len(items) or ds.sizes["time"] != len(items):
        raise SystemExit(
            f"Could not map time slices to items: {len(items)} items, "
            f"{len(by_time)} unique times, {ds.sizes['time']} slices."
        )

    rows = []
    for i, t in enumerate(pd.to_datetime(ds.time.values)):
        it = by_time[t]
        red = ds.red.isel(time=i).values.astype("float64")
        nir = ds.nir.isel(time=i).values.astype("float64")
        scl = ds.scl.isel(time=i).values
        ok = (scl == BARE_SOIL) & (red > 0) & (nir > 0)
        n = int(ok.sum())
        if n < args.min_pixels:
            continue
        scale, offset = scale_offset(it)
        red_dn, nir_dn = np.median(red[ok]), np.median(nir[ok])
        rows.append(
            {
                "date": t.date(),
                "tile": it.properties.get("grid:code"),
                "baseline": it.properties.get("s2:processing_baseline"),
                "boa_flag": it.properties.get("earthsearch:boa_offset_applied"),
                "offset": offset,
                "n_px": n,
                "red_dn": round(red_dn),
                "nir_dn": round(nir_dn),
                "red_item_offset": round(red_dn * (scale or 1e-4) + (offset or 0), 3),
                "red_scale_only": round(red_dn * 1e-4, 3),
            }
        )

    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "offset_check.csv", index=False)

    df["offset"] = df["offset"].astype(str)
    df["boa_flag"] = df["boa_flag"].astype(str)
    print("\nMeans by group (bare-soil pixels, red band):")
    print(
        df.groupby(["baseline", "boa_flag", "offset"])[
            ["red_dn", "nir_dn", "red_item_offset", "red_scale_only"]
        ]
        .agg(["mean"])
        .round(3)
        .assign(n_scenes=df.groupby(["baseline", "boa_flag", "offset"]).size())
        .to_string()
    )

    near = df[
        (pd.to_datetime(df["date"]) - pd.Timestamp(SWITCH)).abs()
        <= pd.Timedelta(days=21)
    ]
    print("\nScenes within 3 weeks of the switch:")
    print(near.drop(columns=["tile"]).to_string())
    print(f"\nSaved {out / 'offset_check.csv'}")


if __name__ == "__main__":
    main()
