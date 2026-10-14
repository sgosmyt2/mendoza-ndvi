from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from mendoza_ndvi.anomaly import MIN_VALID, climatology, load_month

STRATA = {0: "bare", 1: "mixed", 2: "vegetated"}
UNKNOWN = 255
MIN_STD = 0.01


def make_strata(comp_dir, years, months=(1, 2, 3), edges=(0.3, 0.4)):
    """Static stratum map from the baseline mean of NDVI of the given calendar months.

    0 = bare or spares, 1 = mixed, 2 = vegetation and 255 = unknown
    """
    means = [climatology(comp_dir, years, m)["mean"] for m in months]
    base = xr.concat(means, dim="m").mean("m", skipna=True)
    codes = np.digitize(base.values, edges).astype("uint8")
    codes[np.isnan(base.values)] = UNKNOWN
    return base.copy(data=codes)


def list_months(comp_dir):
    """(year, month) for every ndvi_YYYY_mm.tif in the folder, sorted"""
    files = sorted(Path(comp_dir).glob("ndvi_*.tif"))
    return [tuple(int(p) for p in f.stem[5:].split("_")) for f in files]


def stratum_stats(ndvi, count, strat):
    """Mean NDVI, valid fraction and mean count for each stratum"""
    v, c, s = ndvi.values, count.values, strat.values
    groups = {"all": s != UNKNOWN}
    groups.update({name: s == code for code, name in STRATA.items()})
    out = {}
    for name, g in groups.items():
        n = int(g.sum())
        sel = g & np.isfinite(v)
        out[name] = {
            "mean_ndvi": float(v[sel].mean()) if sel.any() else np.nan,
            "valid_frac": float(sel.sum() / n) if n else np.nan,
            "mean_count": float(c[g].mean()) if n else np.nan,
        }
    return out


def build_series(comp_dir, strata, min_valid=MIN_VALID):
    """Long table, one row per month and stratum"""
    rows = []
    for year, mon in list_months(comp_dir):
        ndvi, count = load_month(comp_dir, year, mon, min_valid)
        for name, st in stratum_stats(ndvi, count, strata).items():
            rows.append(
                {
                    "date": pd.Timestamp(year, mon, 1),
                    "year": year,
                    "mon": mon,
                    "stratum": name,
                    **st,
                }
            )
    return pd.DataFrame(rows)


def add_anomalies(df, base_years, min_frac=0.8, min_count=3, min_std=MIN_STD):
    """Add baseline climatology, difference, zscore and a low confidence flag."""
    base = df[df["year"].isin(base_years)]
    clim = (
        base.groupby(["stratum", "mon"])["mean_ndvi"]
        .agg(clim_mean="mean", clim_std="std")
        .reset_index()
    )
    out = df.merge(clim, on=["stratum", "mon"], how="left")
    out["diff"] = out["mean_ndvi"] - out["clim_mean"]
    out["z"] = out["diff"] / out["clim_std"].clip(lower=min_std)
    out["in_baseline"] = out["year"].isin(base_years)
    out["low_conf"] = (out["valid_frac"] < min_frac) | (out["mean_count"] < min_count)
    return out
