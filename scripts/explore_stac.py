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
