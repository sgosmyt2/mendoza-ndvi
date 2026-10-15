import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from mendoza_ndvi.anomaly import MIN_VALID
from mendoza_ndvi.zonal import STRATA, add_anomalies, build_series, make_strata


def plot(df, strata, path):
    names = list(STRATA.values())
    fig, axes = plt.subplots(len(names), 1, figsize=(11, 3.2 * len(names)), sharex=True)
    for ax, name in zip(axes, names):
        d = df[df["stratum"] == name].sort_values("date")
        share = (
            float(
                (
                    strata.values
                    == [k for k, v in STRATA.items() if v == name][0]  # noqa: RUF015
                ).mean()
            )
            * 100
        )
        ax.fill_between(
            d["date"],
            d["clim_mean"] - d["clim_std"],
            d["clim_mean"] + d["clim_std"],
            color="tab:blue",
            alpha=0.2,
            label="baseline mean +- 1 std",
        )
        ax.plot(d["date"], d["mean_ndvi"], color="k", lw=1.2, label="monthly mean NDVI")
        thin = d[d["low_conf"]]
        ax.scatter(
            thin["date"],
            thin["mean_ndvi"],
            facecolors="white",
            edgecolors="tab:red",
            zorder=3,
            s=28,
            label="low confidence (thin month)",
        )
        ax.axvline(
            d.loc[~d["in_baseline"], "date"].min(), color="grey", ls="--", lw=0.8
        )
        ax.set_title(f"{name} ({share:.0f}% of AOI)")
        ax.set_ylabel("NDVI")
    axes[0].legend(loc="upper right", fontsize=8, ncol=3)
    fig.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--comp-dir", default="outputs/composites")
    ap.add_argument("--baseline", default="2018-2022")
    ap.add_argument("--edges", type=float, nargs=2, default=[0.3, 0.4])
    ap.add_argument("--min-valid", type=int, default=MIN_VALID)
    ap.add_argument("--csv", default="outputs/stratum_series.csv")
    ap.add_argument("--fig", default="docs/images/stratum_series.png")
    args = ap.parse_args()

    b0, b1 = (int(v) for v in args.baseline.split("-"))
    years = range(b0, b1 + 1)
    strata = make_strata(args.comp_dir, years, edges=tuple(args.edges))
    print(
        "stratum shares of AOI (%):",
        {
            name: round(float((strata.values == k).mean()) * 100, 1)
            for k, name in STRATA.items()
        },
        "| unknown:",
        round(float((strata.values == 255).mean()) * 100, 1),
    )

    df = add_anomalies(build_series(args.comp_dir, strata, args.min_valid), years)
    Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.csv, index=False)

    late = df[(~df["in_baseline"]) & (df["stratum"] != "all")]
    print("\nanalysis-period z by stratum (low-confidence months excluded):")
    print(
        late[~late["low_conf"]].groupby("stratum")["z"].describe().round(2).to_string()
    )
    print(
        f"\nlow-confidence months (all strata, analysis period): "
        f"{int(late[late['stratum'] == 'vegetated']['low_conf'].sum())} of "
        f"{int((late['stratum'] == 'vegetated').sum())}"
    )

    plot(df[df["stratum"] != "all"], strata, args.fig)
    print(f"\nSaved {args.csv} and {args.fig}")


if __name__ == "__main__":
    main()
