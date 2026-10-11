import argparse
import calendar
from pathlib import Path

import dask
import matplotlib.pyplot as plt
import numpy as np

from mendoza_ndvi.load import bare_soil_red, load_reflectance
from mendoza_ndvi.mask import valid_mask
from mendoza_ndvi.search import aoi_bbox, load_aoi, search_items


def summarise(ds, dilate_px, mask_snow, path):
    """Prints per date mask statistics and saves a figure"""
    valid = valid_mask(ds.scl, dilate_px=dilate_px, mask_snow=mask_snow)
    masked = ds.where(valid)
    pct = (valid.mean(dim=("y", "x")) * 100).to_series()
    before = bare_soil_red(ds).to_series()
    after = bare_soil_red(masked).to_series()

    print("\ndate   valid% baresoil red: before -> after")
    for t in pct.index:
        print(f"{t.date()}  {pct[t]:6.1f}   {before[t]:.3f} -> {after[t]:.3f}")

    n = ds.sizes["time"]
    fig, axes = plt.subplots(1, n, figsize=(2.6 * n, 3.2), squeeze=False)
    for ax, t in zip(axes[0], ds.time.values):
        ax.imshow(ds.red.sel(time=t).values, vmin=0, vmax=0.3, cmap="gray")
        v = valid.sel(time=t).values
        ax.imshow(
            np.ma.masked_where(v, np.ones(v.shape)),
            cmap="autumn",
            alpha=0.6,
            vmin=0,
            vmax=0.3,
        )
        ax.set_title(f"{str(t)[:10]}    valid {pct[t]:.0f}%", fontsize=8)
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=120)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2023)
    ap.add_argument("--month", type=int, default=3)
    ap.add_argument("--res", type=int, default=20)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--dilate", type=int, default=2)
    ap.add_argument("--keep-snow", action="store_true")
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

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"mask_check_{args.year}_{args.month:02d}_d{args.dilate}.png"
    summarise(ds, args.dilate, not args.keep_snow, path)
    print(f"\nSaved {path}")


if __name__ == "__main__":
    main()
