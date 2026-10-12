import argparse
import calendar
from pathlib import Path

import dask
import matplotlib.pyplot as plt
import numpy as np

from mendoza_ndvi.composite import monthly_composite
from mendoza_ndvi.load import load_reflectance
from mendoza_ndvi.search import aoi_bbox, load_aoi, search_items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2023)
    ap.add_argument("--month", type=int, default=3)
    ap.add_argument("--res", type=int, default=20)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--dilate", type=int, default=2)
    ap.add_argument("--out", default="data")
    args = ap.parse_args()

    last = calendar.monthrange(args.year, args.month)[1]
    start = f"{args.year}-{args.month:02d}-01"
    end = f"{args.year}-{args.month:02d}-{last}"

    geom = load_aoi()
    items = search_items(geom, start, end)
    ds = load_reflectance(items, aoi_bbox(geom), args.res)
    with dask.config.set(scheduler="threads", num_workers=args.workers):
        ds = ds.compute()
    n_dates = ds.sizes["time"]

    comp = monthly_composite(ds)
    ndvi, count = comp.ndvi, comp.n_valid

    print(f"\n{n_dates} dates loaded")
    print(f"pixels with no valid observation: {float((count == 0).mean()) * 100:.1f}%")
    print(f"median valid observations per pixel: {float(count.median()):.0f}")
    print(
        f"pixels with only 1 valid observation: {float((count == 1).mean()) * 100:.1f}%"
    )
    print(
        f"NDVI percentiles (5, 50, 95): "
        f"{np.round(np.nanpercentile(ndvi.values, [5, 50, 95]), 2)}"
    )

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 5))
    im1 = a1.imshow(ndvi.values, cmap="RdYlGn", vmin=-0.1, vmax=0.9)
    a1.set_title(f"Median NDVI {args.year}-{args.month:02d}")
    fig.colorbar(im1, ax=a1, shrink=0.8)
    im2 = a2.imshow(count.values, cmap="viridis", vmin=0, vmax=n_dates)
    a2.set_title("Valid observations per pixel")
    fig.colorbar(im2, ax=a2, shrink=0.8)
    for ax in (a1, a2):
        ax.axis("off")
    fig.tight_layout()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"composite_check_{args.year}_{args.month:02d}.png"
    fig.savefig(path, dpi=120)
    print(f"\nSaved {path}")


if __name__ == "__main__":
    main()
