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
                (strata.values == [k for k, v in STRATA.items() if v == name][0]).mean()
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
