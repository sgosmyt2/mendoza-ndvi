import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from mendoza_ndvi.anomaly import MIN_STD, MIN_VALID, climatology, load_month, zscore


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2024)
    ap.add_argument("--month", type=int, default=6)
    ap.add_argument("--baseline", default="2018-2022")
    ap.add_argument("--min-valid", type=int, default=MIN_VALID)
    ap.add_argument("--comp-dir", default="outputs/composites")
    ap.add_argument("--out", default="data")
    args = ap.parse_args()

    b0, b1 = (int(v) for v in args.baseline.split("-"))
    clim = climatology(args.comp_dir, range(b0, b1 + 1), args.month, args.min_valid)
    ndvi, count = load_month(args.comp_dir, args.year, args.month, args.min_valid)
    z = zscore(ndvi, clim)

    std = clim["std"].values
    print(
        f"\nBaseline {b0}-{b1}, calendar month {args.month}, min_valid={args.min_valid}"
    )
    print(
        f"pixels with no climatology (< min years): {float(clim['mean'].isnull().mean()) * 100:.1f}%"
    )
    print(
        "baseline std percentiles (5, 25, 50, 75, 95): "
        f"{np.round(np.nanpercentile(std, [5, 25, 50, 75, 95]), 3)}"
    )
    print(
        f"pixels where std < floor {MIN_STD}: {float(np.nanmean(std < MIN_STD)) * 100:.1f}%"
    )

    zv = z.values
    print(
        f"\n{args.year}-{args.month:02d}: median valid observations {float(count.median()):.0f}"
    )
    print(f"pixels with a zscore: {float(np.isfinite(zv).mean()) * 100:.1f}%")
    print(
        f"z percentiles (5, 50, 95): {np.round(np.nanpercentile(zv, [5, 50, 95]), 2)}"
    )
    print(f"share with |z| > 2: {float(np.nanmean(np.abs(zv) > 2)) * 100:.1f}%")
    print(
        f"AOI mean NDVI {float(ndvi.mean()):.3f} vs climatology {float(clim['mean'].mean()):.3f}"
        f"  (mean z {np.nanmean(zv):.2f})"
    )

    fig, ax = plt.subplots(1, 3, figsize=(14, 4.8))
    panels = [
        (clim["mean"].values, "Baseline mean NDVI", "RdYlGn", -0.1, 0.9),
        (ndvi.values, f"NDVI {args.year}-{args.month:02d}", "RdYlGn", -0.1, 0.9),
        (zv, "z-score", "RdBu", -3, 3),
    ]
    for a, (arr, title, cmap, lo, hi) in zip(ax, panels):
        im = a.imshow(arr, cmap=cmap, vmin=lo, vmax=hi)
        a.set_title(title)
        a.axis("off")
        fig.colorbar(im, ax=a, shrink=0.75)
    fig.tight_layout()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"anomaly_check_{args.year}_{args.month:02d}.png"
    fig.savefig(path, dpi=110)
    print(f"\nSaved {path}")


if __name__ == "__main__":
    main()
