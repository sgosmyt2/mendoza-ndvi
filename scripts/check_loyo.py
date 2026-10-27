import argparse

import numpy as np
import pandas as pd

from mendoza_ndvi.zonal import leave_one_year_out


def expected_noise(n_base, draws=400_000, seed=0):
    """z sd and % beyond |z|>2 for a new draw against n_base draws, with no change at all."""
    rng = np.random.default_rng(seed)
    base = rng.standard_normal((draws, n_base))
    new = rng.standard_normal(draws)
    z = (new - base.mean(axis=1)) / base.std(axis=1, ddof=1)
    return float(z.std()), float((np.abs(z) > 2).mean() * 100)


def summarise(d):
    g = d.groupby("stratum")
    return pd.DataFrame(
        {
            "n": g["z"].size(),
            "mean_diff": g["diff"].mean(),
            "rms_diff": g["diff"].agg(lambda s: float(np.sqrt((s**2).mean()))),
            "z_mean": g["z"].mean(),
            "z_sd": g["z"].std(),
            "pct_abs_z_gt2": g["z"].agg(lambda s: float((s.abs() > 2).mean() * 100)),
        }
    ).round(3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="outputs/stratum_series.csv")
    ap.add_argument("--baseline", default="2018-2022")
    args = ap.parse_args()

    b0, b1 = (int(v) for v in args.baseline.split("-"))
    years = list(range(b0, b1 + 1))
    df = pd.read_csv(args.csv)
    df = df[df["stratum"] != "all"]

    loo = leave_one_year_out(df, years)
    loo = loo[~loo["low_conf"]].dropna(subset=["z"])
    late = df[(~df["in_baseline"]) & (~df["low_conf"])].dropna(subset=["z"])

    print(
        f"Baseline years scored against the other {len(years) - 1} (leave-one-year-out):"
    )
    print(summarise(loo).to_string())
    print(f"\nAnalysis period scored against all {len(years)} baseline years:")
    print(summarise(late).to_string())
    for n in (len(years) - 1, len(years)):
        sd, share = expected_noise(n)
        print(
            f"\nPure noise, baseline of {n} years: {share:.1f}% beyond |z| > 2; "
            f"z sd {sd:.2f} (lower if the std floor binds)"
        )


if __name__ == "__main__":
    main()
