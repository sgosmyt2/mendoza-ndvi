import argparse
import calendar
from pathlib import Path

import dask
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from mendoza_ndvi.load import bare_soil_red, load_reflectance
from mendoza_ndvi.search import aoi_bbox, load_aoi, search_items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2023)
    ap.add_argument("--month", type=int, default=3)
    ap.add_argument("--res", type=int, default=20)
    ap.add_argument("--workers", type=int, default=16)
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
    print(f"\ndims: {dict(ds.sizes)}")

    print("\nBare-soil red reflectance per date (expect about 0.10-0.13):")
    for t, v in bare_soil_red(ds).to_series().items():
        status = "ok" if 0.05 <= v <= 0.25 else "CHECK"
        print(f"  {t.date()}  {v:.3f}  {status}")

    n = ds.sizes["time"]
    fig, axes = plt.subplots(1, n, figsize=(2.6 * n, 3.2), squeeze=False)
    for ax, t in zip(axes[0], ds.time.values):
        ax.imshow(ds.red.sel(time=t).values, vmin=0, vmax=0.3, cmap="gray")
        ax.set_title(str(t)[:10], fontsize=8)
        ax.axis("off")
    fig.tight_layout()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"load_check_{args.year}_{args.month:02d}.png"
    fig.savefig(path, dpi=120)
    print(f"\nSaved {path}")


if __name__ == "__main__":
    main()
