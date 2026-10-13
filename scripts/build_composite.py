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


def write_month(comp, out_dir, key):
    """Write count_<key>.tif then ndvi_<key>.tif. The NDVI file goes last, so
    its existence means the month finished."""
    comp = comp.rio.write_crs(UTM_CRS)
    count = comp["n_valid"].rio.write_nodata(None)
    count.rio.to_raster(
        out_dir / f"count_{key}.tif", driver="GTiff", tiled=True, compress="deflate"
    )
    ndvi = comp["ndvi"].rio.write_nodata(np.nan)
    ndvi.rio.to_raster(
        out_dir / f"ndvi_{key}.tif", driver="GTiff", tiled=True, compress="deflate"
    )


def month_stats(key, comp, n_dates):
    count = comp["n_valid"]
    return {
        "month": key,
        "n_dates": n_dates,
        "pct_no_valid": round(float((count == 0).mean()) * 100, 1),
        "pct_under_3": round(float((count < 3).mean()) * 100, 1),
        "median_count": float(count.median()),
        "ndvi_median": round(float(comp["ndvi"].median(skipna=True)), 3),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default=full_last_month().isoformat())
    ap.add_argument("--res", type=int, default=20)
    ap.add_argument("--dilate", type=int, default=2)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--out", default="outputs/composites")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    summary_path = out / "summary.csv"

    geom = load_aoi()
    bbox = aoi_bbox(geom)
    items = search_items(geom, args.start, args.end)
    by_month = {}
    for i in items:
        by_month.setdefault(i.datetime.strftime("%Y_%m"), []).append(i)

    failed_in_a_row = 0
    for key, month_items in sorted(by_month.items()):
        if (out / f"ndvi_{key}.tif").exists():
            continue
        t0 = time.perf_counter()
        try:
            ds = load_reflectance(month_items, bbox, args.res)
            with dask.config.set(scheduler="threads", num_workers=args.workers):
                ds = ds.compute()
            comp = monthly_composite(ds, dilate_px=args.dilate)
            row = month_stats(key, comp, ds.sizes["time"])
            write_month(comp, out, key)
        except Exception as err:  # noqa: BLE001
            failed_in_a_row += 1
            msg = f"{type(err).__name__}: {str(err)[:200]}"
            print(f"{key}: failed {msg}")
            with (out / "failures.txt").open("a") as f:
                f.write(f"{key}\t{msg}\n")
            if failed_in_a_row >= 3:
                raise SystemExit(
                    "Three months in a row failed: probably a code or setup "
                ) from err
            continue

        failed_in_a_row = 0
        new_file = not summary_path.exists()
        with summary_path.open("a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(row))
            if new_file:
                w.writeheader()
            w.writerow(row)
        print(
            f"{key}: {row['n_dates']} dates, {row['pct_no_valid']}% no valid, "
            f"{row['pct_under_3']}% under 3 obs, {time.perf_counter() - t0:.0f}s"
        )

    print(f"\nDone, Composites in {out}")


if __name__ == "__main__":
    main()
