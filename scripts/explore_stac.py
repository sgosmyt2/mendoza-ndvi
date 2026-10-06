import argparse
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt

from mendoza_ndvi.search import (
    items_to_frame,
    load_aoi,
    search_items,
    usable_dates_table,
)


def plot_usable(table, max_cloud, path):
    fig, ax = plt.subplots(figsize=(9, 0.5 * len(table) + 1.5))
    im = ax.imshow(table.values, cmap="YlGn", aspect="auto")
    ax.set_xticks(
        range(12), ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
    )
    ax.set_yticks(range(len(table)), table.index)
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            ax.text(j, i, int(table.iat[i, j]), ha="center", va="center", fontsize=8)
    ax.set_title(f"Distinct dates per month with a scene <= {max_cloud:.0f}% cloud")
    fig.colorbar(im, ax=ax, shrink=0.8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def report(df, max_cloud, baseline, out):
    print(
        f"\n{len(df)} items, {df['date'].nunique()} distinct dates, "
        f"{df['datetime'].min().date()} -> {df['datetime'].max().date()}"
    )
    print("\nItems per MGRS tile:\n", df["tile"].value_counts(dropna=False).to_string())

    print("\nProcessing baseline by year:")
    print(df.groupby(["year", "baseline"]).size().unstack(fill_value=0).to_string())

    print("\nBOA offset applied by Earth Search, by year:")
    flag = df["boa_offset_applied"].astype(str).rename("boa_offset_applied")
    print(df.groupby(["year", flag]).size().unstack(fill_value=0).to_string())

    print("\nMedian scene cloud cover by year (%):")
    print(df.groupby("year")["cloud_cover"].median().round(1).to_string())

    table = usable_dates_table(df, max_cloud)
    print(f"\nUsable dates per month (<= {max_cloud:.0f}% cloud):")
    print(table.to_string())

    b0, b1 = (int(x) for x in baseline.split("-"))
    base = table.loc[b0:b1]
    weak = [
        (int(y), int(m), int(base.at[y, m]))
        for y in base.index
        for m in base.columns
        if base.at[y, m] < 2
    ]
    print(f"\nBaseline months ({b0}-{b1}) with fewer than 2 usable dates: {len(weak)}")
    for y, m, n in weak:
        print(f"  {y}-{m:02d}: {n}")

    plot_usable(table, max_cloud, out / "usable_dates.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2017-01-01")
    ap.add_argument("--end", default=date.today().isoformat())
    ap.add_argument("--max-cloud", type=float, default=30.0)
    ap.add_argument("--baseline", default="2018-2022")
    ap.add_argument("--out", default="data")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    df = items_to_frame(search_items(load_aoi(), args.start, args.end))
    if df.empty:
        raise SystemExit("No items found. Check dates/AOI/endpoint.")
    df.drop(columns=["date"]).to_csv(out / "scenes.csv", index=False)

    report(df, args.max_cloud, args.baseline, out)
    print(f"\nSaved {out/'scenes.csv'} and {out/'usable_dates.png'}")


if __name__ == "__main__":
    main()
