import argparse
import calendar
import time

import dask
import odc.stac

from mendoza_ndvi.search import UTM_CRS, aoi_bbox, load_aoi, search_items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2023)
    ap.add_argument("--month", type=int, default=3)
    ap.add_argument("--res", type=int, default=20)
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()

    last = calendar.monthrange(args.year, args.month)[1]
    start = f"{args.year}-{args.month:02d}-01"
    end = f"{args.year}-{args.month:02d}-{last}"

    geom = load_aoi()
    t0 = time.perf_counter()
    items = search_items(geom, start, end)
    print(f"STAC search: {len(items)} items in {time.perf_counter() - t0:.1f}s")
    if not items:
        raise SystemExit("No items for that month.")

    for it in (items[0], items[-1]):
        p = it.properties
        rb = it.assets["red"].extra_fields.get("raster:bands")
        print(
            f"  {it.datetime.date()} baseline={p.get('s2:processing_baseline')} "
            f"boa_offset_applied={p.get('earthsearch:boa_offset_applied')} "
            f"red raster:bands={rb}"
        )

    odc.stac.configure_rio(cloud_defaults=True, aws={"aws_unsigned": True})

    t0 = time.perf_counter()
    ds = odc.stac.load(
        items,
        bands=["red", "nir", "scl"],
        bbox=aoi_bbox(geom),
        crs=UTM_CRS,
        resolution=args.res,
        groupby="solar_day",
        chunks={"x": 1024, "y": 1024},
        resampling="nearest",
    )
    print(
        f"Lazy dataset built in {time.perf_counter() - t0:.1f}s: "
        f"dims={dict(ds.sizes)}, {ds.nbytes / 1e6:.0f} MB if fully loaded"
    )

    t0 = time.perf_counter()
    with dask.config.set(scheduler="threads", num_workers=args.workers):
        ds = ds.compute()
    t = time.perf_counter() - t0
    n = ds.sizes["time"]
    print(
        f"Streaming: {t:.1f}s total, {t / n:.1f}s per date, {ds.nbytes / 1e6 / t:.1f} MB/s"
    )
    print(
        f"\nSummary at {args.res} m: {n} dates in {t:.0f}s. Roughly 100 months to go."
    )


if __name__ == "__main__":
    main()
