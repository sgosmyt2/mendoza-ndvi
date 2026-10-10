import argparse
from datetime import date
from pathlib import Path
from sched import scheduler

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


def load_items(items, bbox, res, workers):
    ds = odc.stac.load(
        items,
        bands=["red", "nir", "scl"],
        bbox=bbox,
        crs=UTM_CRS,
        resolution=res,
        groupby="id",
        chunks={"x": 1024, "y": 1024},
        resampling="nearest",
    )
    with dask.config.set(scheduler="threas", num_workers=workers):
        return ds.compute()


def measure(item, sl, min_pixels):
    """Median red/NIR of bare soil pixels in one scene, or None if too few."""
    red = sl.red.values.astype("float64")
    nir = sl.nir.values.astype("float64")
    ok = (sl.scl.values == BARE_SOIL) & (red > 0) & (nir > 0)
    n = int(ok.sum())
    if n < min_pixels:
        return None
    scale, offset = scale_offset(item)
    red_dn, nir_dn = np.median(red[ok]), np.median(nir[ok])
    return {
        "date": item.datetime.date(),
        "tile": item.properties.get("grid:code"),
        "baseline": item.properties.get("s2:processing_baseline"),
        "boa_flag": item.properties.get("earthsearch:boa_offset_applied"),
        "offset": offset,
        "n_px": n,
        "red_dn": round(red_dn),
        "nir_dn": round(nir_dn),
        "red_item_offset": round(red_dn * (scale or 1e-4) + (offset or 0), 3),
        "red_scale_only": round(red_dn * 1e-4, 3),
    }


def process_month(items, bbox, res, workers, min_pixels, failures):
    pairs = None
    try:  # This attempts to to process the entire month at once
        ds = load_items(items, bbox, res, workers)
        by_time = {pd.Timestamp(i.datetime).tz_convert(None): i for i in items}
        if len(by_time) == len(items) == ds.sizes["time"]:
            pairs = [
                (by_time[pd.Timestamp(t)], ds.isel(time=i))
                for i, t in enumerate(ds.time.values)
            ]
    except Exception as err:  # noqa: BLE001
        print(f"    month failed: {type(err).__name__}, retrying per scene")

    if pairs is None:
        pairs = []
        for i in items:
            for attempt in range(2):
                try:
                    sl = load_items([i], bbox, res, workers).isel(time=0)
                    pairs.append((i, sl))
                    break
                except Exception as err:  # noqa: BLE001
                    if attempt == 1:
                        msg = str(err).replace("\n", " ")[:150]
                        failures.append(
                            {"id": i.id, "error": f"{type(err).__name__}: {msg}"}
                        )
    rows = [measure(i, sl, min_pixels) for i, sl in pairs]
    return [r for r in rows if r is not None]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default=date.today().isoformat())  # noqa: DTZ011
    ap.add_argument("--res", type=int, default=120)
    ap.add_argument("--min-pixels", type=int, default=100)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--out", default="data/offset_all")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "offset_check.csv"
    fail_path = out / "failures.csv"
    done_path = out / "done_months.txt"
    done = set(done_path.read_text().split()) if done_path.exists() else set()

    geom = load_aoi()
    bbox = aoi_bbox(geom)
    items = search_items(geom, args.start, args.end)
    by_month = {}
    for i in items:
        by_month.setdefault((i.datetime.year, i.datetime.month), []).append(i)

    odc.stac.configure_rio(cloud_defaults=True, aws={"aws_unsigned": True})

    for (y, m), month_items in sorted(by_month.items()):
        key = f"{y}-{m:02d}"
        if key in done:
            continue
        failures = []
        rows = process_month(
            month_items, bbox, args.res, args.workers, args.min_pixels, failures
        )
        if rows:
            pd.DataFrame(rows).to_csv(
                csv_path, mode="a", header=not csv_path.exists(), index=False
            )
        if failures:
            pd.DataFrame(failures).to_csv(
                fail_path, mode="a", header=not fail_path.exists(), index=False
            )
        with done_path.open("a") as f:
            f.write(key + "\n")
        print(
            f"{key}: {len(month_items)} scenes, {len(rows)} measured, "
            f"{len(failures)} failed"
        )

    print(f"\nDone. Results: {csv_path}  Failures: {fail_path}")


if __name__ == "__main__":
    main()
