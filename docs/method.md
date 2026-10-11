# Methods and findings (draft)

## Data
- Sentinel-2 L2A, AWS Earth Search STAC (`sentinel-2-l2a`).
- The AOI touches four MGRS tiles (19HDC, 19HDD, 19HEC, 19HED). One overpass every 5 days appears as four items, merged into one image per date by `groupby="solar_day"`.
- 2017-01 to 2026-10: 3850 items. Removed 20 non COG items and 901 superseded duplicates, leaving 2933.
- Considered `sentinel-2-c1-l2a` (no duplicates) but rejected it because no 2017 data, only 28 items in 2022, and 20 baseline months with fewer than 2 usable dates.

## Reflectance offset
- Survey: median red of SCL "not vegetated" pixels per scene, 2018-2026, at 120 m (2245 scenes measured). Unshifted scenes read ~1000-1250 DN raw (~0.11 reflectance).
- Only 24 scenes read ~1750-2250 DN: baseline 04.00, boa_offset_applied=False, acquired 2022-01-25 to 2022-02-24. These get -1000 DN before scaling.
- 92 other scenes with flag False and offset -0.1 are NOT shifted. The metadata alone would have miscorrected them.
- Not explained: why the shift is limited to that window.

## Masking
- SCL classes masked: 0, 1, 3, 8, 9, 10, and 11.
- Dilation of 2px (40 m) at 20 m resolution, chosen by eye. Not yet tested quantitatively, thinking about potentially doing so but 2px seems best.
- Classes 2 (dark areas) and 7 (unclassified) are kept; to be revisited.

## Performance
Streaming one month (7 dates, red + NIR + SCL, ~28 x 30km AOI) from AWS Earth Search to a laptop in Buenos Aires. Throughput is limited by network latency and bandwidth, not CPU.

| Resolution | Grid (y x x) | Workers | Time per month |
|---|---|---|---|
| 20m | 1498 x 1395 | 16 | 23s |
| 10m | 2996 x 2789 | 8 | 96s |

Worker sweep at 20m (March 2023): 4 workers 72s, 8 workers 38s, 16 workers 23s, 32 workers 27s. The speedup flattens beyond 16, so 16 is the default.

Extrapolated from one month, a full 2017-2026 run should take well under 2 hours locally, so no cloud VM was needed. (Estimate will be replaced with the measured total.)

## Limitations
- Scene level cloud cover describes a 110 km tile, not the AOI, so the usable dates heatmap is optimistic. Valid pixel counts are the real measure.
- The offset rule is empirical.
